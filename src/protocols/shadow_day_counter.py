"""
HARD STATEMENT §0.6 — Shadow Day Counter.

Non-negotiable rules:
1. Light must shadow trade 30 consecutive days before Complete activation.
2. Complete must shadow trade 30 consecutive days before going live.
3. A gap > 24h between shadow runs resets the counter to 0.
4. Counter is persisted to disk (survives restart).
5. Daily report is generated at each day increment.

This module tracks shadow day counts for both LIGHT and COMPLETE profiles.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from enum import StrEnum

from pydantic import BaseModel, Field

from interface_contracts.atomic_io import atomic_write_json


class ShadowProfile(StrEnum):
    LIGHT = "light"
    COMPLETE = "complete"


class ShadowDayRecord(BaseModel, frozen=True):
    """Record of a single shadow day."""

    day_number: int
    date: str  # ISO date
    timestamp: float
    profile: ShadowProfile
    passed_all_gates: bool
    metrics_summary: dict[str, float] = Field(default_factory=dict)


class ShadowCounterState(BaseModel):
    """Persisted counter state."""

    profile: ShadowProfile
    consecutive_days: int = 0
    required_days: int = 30
    last_shadow_timestamp: float | None = None
    started_at: float | None = None
    daily_records: list[ShadowDayRecord] = Field(default_factory=list)
    resets: int = 0  # number of times counter was reset due to gap

    @property
    def is_complete(self) -> bool:
        return self.consecutive_days >= self.required_days

    @property
    def remaining_days(self) -> int:
        return max(0, self.required_days - self.consecutive_days)


_MAX_GAP_SECONDS = 24 * 3600  # 24h — HARD STATEMENT
_STATE_FILENAME = "shadow_counter_{profile}.json"


class ShadowDayCounter:
    """Track consecutive shadow trading days with persistence.

    HARD STATEMENT compliance:
    - 30 consecutive days required.
    - > 24h gap resets to 0.
    - State persisted atomically to disk.
    """

    def __init__(self, state_dir: Path, profile: ShadowProfile) -> None:
        self._state_dir = state_dir
        self._profile = profile
        self._state_file = state_dir / _STATE_FILENAME.format(profile=profile.value)
        self._state = self._load_or_create()

    def _load_or_create(self) -> ShadowCounterState:
        """Load persisted state or create fresh."""
        if self._state_file.exists():
            try:
                data = json.loads(self._state_file.read_text(encoding="utf-8"))
                return ShadowCounterState(**data)
            except (json.JSONDecodeError, ValueError):
                pass  # corrupted — start fresh
        return ShadowCounterState(profile=self._profile)

    def _persist(self) -> None:
        """Atomically persist state to disk."""
        self._state_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_json(self._state_file, self._state.model_dump(mode="json"))

    def record_shadow_day(
        self,
        passed_all_gates: bool,
        metrics_summary: dict[str, float] | None = None,
        now: float | None = None,
    ) -> ShadowDayRecord:
        """Record a completed shadow trading day.

        Args:
            passed_all_gates: Whether all shadow validation gates passed.
            metrics_summary: Optional summary of key metrics for the day.
            now: Override timestamp (for testing).

        Returns:
            The ShadowDayRecord for this day.

        HARD STATEMENT rules applied:
        - If gap since last shadow > 24h → reset counter to 0.
        - If gates failed → day not counted (counter unchanged).
        """
        ts = now or time.time()

        # Check for 24h gap reset
        if self._state.last_shadow_timestamp is not None:
            gap = ts - self._state.last_shadow_timestamp
            if gap > _MAX_GAP_SECONDS:
                self._state.consecutive_days = 0
                self._state.resets += 1
                self._state.daily_records = []
                self._state.started_at = None

        # Update timestamp regardless (attempt was made)
        self._state.last_shadow_timestamp = ts

        if not passed_all_gates:
            # Day does not count, but we record the attempt
            record = ShadowDayRecord(
                day_number=self._state.consecutive_days,
                date=datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d"),
                timestamp=ts,
                profile=self._profile,
                passed_all_gates=False,
                metrics_summary=metrics_summary or {},
            )
            self._persist()
            return record

        # Successful day
        if self._state.started_at is None:
            self._state.started_at = ts

        self._state.consecutive_days += 1

        record = ShadowDayRecord(
            day_number=self._state.consecutive_days,
            date=datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d"),
            timestamp=ts,
            profile=self._profile,
            passed_all_gates=True,
            metrics_summary=metrics_summary or {},
        )
        self._state.daily_records.append(record)
        self._persist()
        return record

    def is_promotion_ready(self) -> bool:
        """Check if the required 30 consecutive days are met."""
        return self._state.is_complete

    def get_status(self) -> ShadowCounterState:
        """Return current counter state."""
        return self._state

    def generate_report(self) -> dict:
        """Generate a shadow validation report for promotion gate.

        HARD STATEMENT: this report is required before any promotion.
        """
        return {
            "profile": self._profile.value,
            "consecutive_days": self._state.consecutive_days,
            "required_days": self._state.required_days,
            "remaining_days": self._state.remaining_days,
            "is_complete": self._state.is_complete,
            "started_at": self._state.started_at,
            "last_shadow_timestamp": self._state.last_shadow_timestamp,
            "total_resets": self._state.resets,
            "daily_records_count": len(self._state.daily_records),
            "report_generated_at": time.time(),
        }

    def save_report(self, report_dir: Path | None = None) -> Path:
        """Persist the shadow report to disk."""
        target_dir = report_dir or self._state_dir
        target_dir.mkdir(parents=True, exist_ok=True)
        report = self.generate_report()
        ts = datetime.fromtimestamp(time.time(), tz=timezone.utc).strftime("%Y%m%d_%H%M%S")
        report_file = target_dir / f"shadow_report_{self._profile.value}_{ts}.json"
        atomic_write_json(report_file, report)
        return report_file
