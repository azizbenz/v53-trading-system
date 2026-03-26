"""
Build-4 / exposure_budgeter / exposure_reporter
Report exposure consumption, refusals, remaining capacity.

GrossUtil = GrossExp / X_gross,max
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ExposureEvent(BaseModel, frozen=True):
    """A single exposure event (acceptance or refusal)."""

    pair: str
    candidate_size: float
    accepted: bool
    reason: str = ""
    gross_after: float = 0.0
    timestamp: float = 0.0


class ExposureStats(BaseModel, frozen=True):
    """Aggregate exposure statistics."""

    current_gross: float = 0.0
    gross_cap: float = 0.0
    utilization: float = 0.0  # GrossUtil = GrossExp / X_gross,max
    remaining_capacity: float = 0.0
    total_accepted: int = 0
    total_refused: int = 0
    refusal_rate: float = 0.0


class ExposureReporter:
    """Track and report exposure events."""

    def __init__(self, gross_cap: float) -> None:
        self._gross_cap = gross_cap
        self._events: list[ExposureEvent] = []
        self._current_gross: float = 0.0
        self._accepted: int = 0
        self._refused: int = 0

    def record_accepted(self, pair: str, size: float, timestamp: float = 0.0) -> None:
        self._current_gross += size
        self._accepted += 1
        self._events.append(ExposureEvent(
            pair=pair, candidate_size=size, accepted=True,
            gross_after=self._current_gross, timestamp=timestamp,
        ))

    def record_refused(self, pair: str, size: float, reason: str, timestamp: float = 0.0) -> None:
        self._refused += 1
        self._events.append(ExposureEvent(
            pair=pair, candidate_size=size, accepted=False,
            reason=reason, gross_after=self._current_gross, timestamp=timestamp,
        ))

    def record_position_closed(self, size: float) -> None:
        self._current_gross = max(0.0, self._current_gross - size)

    def get_stats(self) -> ExposureStats:
        total = self._accepted + self._refused
        return ExposureStats(
            current_gross=self._current_gross,
            gross_cap=self._gross_cap,
            utilization=self._current_gross / self._gross_cap if self._gross_cap > 0 else 0.0,
            remaining_capacity=max(0.0, self._gross_cap - self._current_gross),
            total_accepted=self._accepted,
            total_refused=self._refused,
            refusal_rate=self._refused / total if total > 0 else 0.0,
        )

    def get_events(self, pair: str | None = None) -> tuple[ExposureEvent, ...]:
        if pair is None:
            return tuple(self._events)
        return tuple(e for e in self._events if e.pair == pair)
