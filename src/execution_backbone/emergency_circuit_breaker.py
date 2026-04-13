"""
GEM-10 / QWEN-07 — Emergency Circuit Breaker with disk persistence.

P0 guardrail: kill switch must survive process restart.
- State persisted to disk via atomic write (GEM-19).
- External file flag: touching KILL_SWITCH_ACTIVE triggers halt.
- Once tripped, requires explicit human reset.

Invariant: if the process crashes while kill switch is active,
restart MUST find the persisted flag and refuse to trade.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from enum import StrEnum

from pydantic import BaseModel, Field

from interface_contracts.atomic_io import atomic_write_json


class KillSwitchState(StrEnum):
    ARMED = "armed"          # normal operation, ready to trip
    TRIPPED = "tripped"      # kill switch active, all trading halted
    DISARMED = "disarmed"    # manually reset by operator


class KillSwitchReason(StrEnum):
    CRITICAL_DIVERGENCE = "critical_divergence"
    LOSS_BUDGET_BREACH = "loss_budget_breach"
    DATA_CORRUPTION = "data_corruption"
    EXTERNAL_FILE_FLAG = "external_file_flag"
    OPERATOR_MANUAL = "operator_manual"
    UNKNOWN = "unknown"


class KillSwitchRecord(BaseModel, frozen=True):
    """Persisted kill switch state."""

    state: KillSwitchState
    reason: KillSwitchReason = KillSwitchReason.UNKNOWN
    tripped_at: float | None = None
    reset_at: float | None = None
    detail: str = ""


_DEFAULT_STATE_FILE = "kill_switch_state.json"
_DEFAULT_EXTERNAL_FLAG = "KILL_SWITCH_ACTIVE"


class EmergencyCircuitBreaker:
    """Persistent kill switch with external file flag support.

    On trip:
    1. State set to TRIPPED in memory.
    2. State atomically persisted to disk.
    3. All is_trading_allowed() calls return False.

    On startup:
    1. Check persisted state file — if TRIPPED, refuse to trade.
    2. Check external flag file — if present, trip immediately.
    """

    def __init__(
        self,
        state_dir: Path,
        state_filename: str = _DEFAULT_STATE_FILE,
        external_flag_filename: str = _DEFAULT_EXTERNAL_FLAG,
    ) -> None:
        self._state_dir = state_dir
        self._state_file = state_dir / state_filename
        self._external_flag = state_dir / external_flag_filename
        self._state = KillSwitchState.ARMED
        self._reason = KillSwitchReason.UNKNOWN
        self._tripped_at: float | None = None
        self._history: list[KillSwitchRecord] = []

        # Restore persisted state on init
        self._restore_from_disk()
        # Check external file flag
        self._check_external_flag()

    def _restore_from_disk(self) -> None:
        """Restore state from persisted file if it exists."""
        if not self._state_file.exists():
            return
        try:
            data = json.loads(self._state_file.read_text(encoding="utf-8"))
            persisted_state = KillSwitchState(data.get("state", "armed"))
            if persisted_state == KillSwitchState.TRIPPED:
                self._state = KillSwitchState.TRIPPED
                self._reason = KillSwitchReason(data.get("reason", "unknown"))
                self._tripped_at = data.get("tripped_at")
        except (json.JSONDecodeError, ValueError, OSError):
            # Corrupted state file = assume tripped for safety
            self._state = KillSwitchState.TRIPPED
            self._reason = KillSwitchReason.DATA_CORRUPTION
            self._tripped_at = time.time()
            self._persist()

    def _check_external_flag(self) -> None:
        """Check for external KILL_SWITCH_ACTIVE file flag."""
        if self._external_flag.exists():
            if self._state != KillSwitchState.TRIPPED:
                self.trip(KillSwitchReason.EXTERNAL_FILE_FLAG, "External flag file detected")

    def _persist(self) -> None:
        """Atomically persist current state to disk."""
        record = {
            "state": self._state.value,
            "reason": self._reason.value,
            "tripped_at": self._tripped_at,
            "persisted_at": time.time(),
        }
        self._state_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_json(self._state_file, record)

    def trip(self, reason: KillSwitchReason, detail: str = "") -> KillSwitchRecord:
        """Trip the kill switch. All trading stops immediately.

        Persists to disk so state survives restart.
        """
        now = time.time()
        self._state = KillSwitchState.TRIPPED
        self._reason = reason
        self._tripped_at = now
        self._persist()

        record = KillSwitchRecord(
            state=KillSwitchState.TRIPPED,
            reason=reason,
            tripped_at=now,
            detail=detail,
        )
        self._history.append(record)
        return record

    def reset(self, operator_detail: str = "") -> KillSwitchRecord:
        """Reset the kill switch. Requires explicit operator action.

        Also removes the external flag file if present.
        """
        now = time.time()
        self._state = KillSwitchState.ARMED
        self._reason = KillSwitchReason.OPERATOR_MANUAL
        self._tripped_at = None
        self._persist()

        # Remove external flag if present
        if self._external_flag.exists():
            self._external_flag.unlink()

        record = KillSwitchRecord(
            state=KillSwitchState.ARMED,
            reason=KillSwitchReason.OPERATOR_MANUAL,
            reset_at=now,
            detail=f"Operator reset: {operator_detail}",
        )
        self._history.append(record)
        return record

    def is_trading_allowed(self) -> bool:
        """Check if trading is allowed. Re-checks external flag."""
        self._check_external_flag()
        return self._state == KillSwitchState.ARMED

    @property
    def current_state(self) -> KillSwitchState:
        return self._state

    @property
    def current_reason(self) -> KillSwitchReason:
        return self._reason

    @property
    def tripped_at(self) -> float | None:
        return self._tripped_at

    def get_history(self) -> tuple[KillSwitchRecord, ...]:
        return tuple(self._history)
