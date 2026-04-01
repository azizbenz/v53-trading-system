"""
8.5.5 — Freshness Reporter: report stale events and freshness metrics.

Invariant: all stale events are visible. No silent degradation.
"""

from __future__ import annotations

import logging
from pydantic import BaseModel, Field

from .stale_hard_guard import StaleVerdict


logger = logging.getLogger(__name__)


class FreshnessEvent(BaseModel, frozen=True):
    """A freshness state change event."""

    pair: str
    stream_type: str
    verdict: StaleVerdict
    age_s: float
    penalty: float = 0.0
    timestamp: float = 0.0


class FreshnessStats(BaseModel, frozen=True):
    """Aggregate freshness statistics."""

    total_checks: int = 0
    fresh_count: int = 0
    degraded_count: int = 0
    hard_stale_count: int = 0
    max_age_observed: float = 0.0
    by_pair: dict[str, str] = Field(default_factory=dict)  # pair -> latest verdict


class FreshnessReporter:
    """Track and report freshness events."""

    def __init__(self) -> None:
        self._events: list[FreshnessEvent] = []
        self._by_pair: dict[str, StaleVerdict] = {}
        self._max_age: float = 0.0

    def record(self, event: FreshnessEvent) -> None:
        self._events.append(event)
        self._by_pair[event.pair] = event.verdict
        if event.age_s > self._max_age:
            self._max_age = event.age_s
        level = logging.WARNING if event.verdict == StaleVerdict.HARD_STALE else logging.INFO
        logger.log(
            level,
            "freshness_event_recorded",
            extra={
                "pair": event.pair,
                "stream_type": event.stream_type,
                "verdict": event.verdict.value,
                "age_s": event.age_s,
                "penalty": event.penalty,
                "timestamp": event.timestamp,
            },
        )

    def get_stats(self) -> FreshnessStats:
        fresh = sum(1 for e in self._events if e.verdict == StaleVerdict.FRESH)
        degraded = sum(1 for e in self._events if e.verdict == StaleVerdict.DEGRADED)
        hard = sum(1 for e in self._events if e.verdict == StaleVerdict.HARD_STALE)

        return FreshnessStats(
            total_checks=len(self._events),
            fresh_count=fresh,
            degraded_count=degraded,
            hard_stale_count=hard,
            max_age_observed=self._max_age,
            by_pair={p: v.value for p, v in self._by_pair.items()},
        )

    def get_events(self, pair: str | None = None) -> tuple[FreshnessEvent, ...]:
        if pair is None:
            return tuple(self._events)
        return tuple(e for e in self._events if e.pair == pair)
