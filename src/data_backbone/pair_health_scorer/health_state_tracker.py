"""
10.5.4 - Health State Tracker: track active / degraded / suspended / recovery states.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel


class PairHealthState(StrEnum):
    ACTIVE = "active"
    DEGRADED = "degraded"
    SUSPENDED = "suspended"
    RECOVERING = "recovering"


class StateTransition(BaseModel, frozen=True):
    """A state transition event."""

    pair: str
    from_state: PairHealthState
    to_state: PairHealthState
    reason: str
    timestamp: float


class HealthStateTracker:
    """Track pair health states and explicit quarantine."""

    _QUARANTINE_STATES = frozenset({
        PairHealthState.SUSPENDED,
        PairHealthState.RECOVERING,
    })

    def __init__(self) -> None:
        self._states: dict[str, PairHealthState] = {}
        self._transitions: list[StateTransition] = []
        self._consecutive_healthy: dict[str, int] = {}

    def get_state(self, pair: str) -> PairHealthState:
        return self._states.get(pair, PairHealthState.ACTIVE)

    def set_state(
        self,
        pair: str,
        new_state: PairHealthState,
        reason: str,
        timestamp: float,
    ) -> StateTransition | None:
        current = self.get_state(pair)
        if current == new_state:
            return None

        transition = StateTransition(
            pair=pair,
            from_state=current,
            to_state=new_state,
            reason=reason,
            timestamp=timestamp,
        )
        self._states[pair] = new_state
        self._transitions.append(transition)
        return transition

    def suspend(self, pair: str, reason: str, timestamp: float) -> StateTransition | None:
        self._consecutive_healthy[pair] = 0
        return self.set_state(pair, PairHealthState.SUSPENDED, reason, timestamp)

    def start_recovery(self, pair: str, timestamp: float) -> StateTransition | None:
        return self.set_state(pair, PairHealthState.RECOVERING, "recovery started", timestamp)

    def activate(self, pair: str, reason: str, timestamp: float) -> StateTransition | None:
        return self.set_state(pair, PairHealthState.ACTIVE, reason, timestamp)

    def degrade(self, pair: str, reason: str, timestamp: float) -> StateTransition | None:
        return self.set_state(pair, PairHealthState.DEGRADED, reason, timestamp)

    def get_consecutive_healthy(self, pair: str) -> int:
        return self._consecutive_healthy.get(pair, 0)

    def increment_consecutive_healthy(self, pair: str) -> int:
        count = self._consecutive_healthy.get(pair, 0) + 1
        self._consecutive_healthy[pair] = count
        return count

    def reset_consecutive_healthy(self, pair: str) -> None:
        self._consecutive_healthy[pair] = 0

    def get_transitions(self, pair: str | None = None) -> tuple[StateTransition, ...]:
        if pair is None:
            return tuple(self._transitions)
        return tuple(t for t in self._transitions if t.pair == pair)

    def get_all_states(self) -> dict[str, PairHealthState]:
        return dict(self._states)

    def get_suspended_pairs(self) -> frozenset[str]:
        return frozenset(
            pair for pair, state in self._states.items()
            if state == PairHealthState.SUSPENDED
        )

    def is_quarantined(self, pair: str) -> bool:
        return self.get_state(pair) in self._QUARANTINE_STATES

    def get_quarantined_pairs(self) -> frozenset[str]:
        return frozenset(
            pair for pair, state in self._states.items()
            if state in self._QUARANTINE_STATES
        )

    def can_receive_signals(self, pair: str) -> bool:
        return not self.is_quarantined(pair)
