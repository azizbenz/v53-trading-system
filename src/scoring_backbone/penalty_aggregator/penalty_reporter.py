"""
Build-5 / penalty_aggregator / penalty_reporter
Expose penalty detail and statistics.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class PenaltyEvent(BaseModel, frozen=True):
    engine_id: str
    pair: str
    score_penalty: float
    size_multiplier: float
    is_phantom: bool = False
    is_capped: bool = False
    timestamp: float = 0.0


class PenaltyStats(BaseModel, frozen=True):
    total_evaluated: int = 0
    phantom_count: int = 0
    capped_count: int = 0
    mean_score_penalty: float = 0.0
    mean_size_multiplier: float = 0.0


class PenaltyReporter:
    """Track and report penalty events."""

    def __init__(self) -> None:
        self._events: list[PenaltyEvent] = []
        self._phantom_count: int = 0
        self._capped_count: int = 0

    def record(self, event: PenaltyEvent) -> None:
        self._events.append(event)
        if event.is_phantom:
            self._phantom_count += 1
        if event.is_capped:
            self._capped_count += 1

    def get_stats(self) -> PenaltyStats:
        n = len(self._events)
        if n == 0:
            return PenaltyStats()

        mean_sp = sum(e.score_penalty for e in self._events) / n
        mean_sm = sum(e.size_multiplier for e in self._events) / n

        return PenaltyStats(
            total_evaluated=n,
            phantom_count=self._phantom_count,
            capped_count=self._capped_count,
            mean_score_penalty=mean_sp,
            mean_size_multiplier=mean_sm,
        )

    def get_events(self, pair: str | None = None) -> tuple[PenaltyEvent, ...]:
        if pair is None:
            return tuple(self._events)
        return tuple(e for e in self._events if e.pair == pair)
