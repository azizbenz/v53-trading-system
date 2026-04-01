"""
7.5.5 — Routing Reporter: report on event distribution.

Invariant: dispatch success/fail, backpressure events, consumer lag all tracked.
"""

from __future__ import annotations

import logging
from pydantic import BaseModel, Field


logger = logging.getLogger(__name__)


class RoutingStats(BaseModel, frozen=True):
    """Aggregate routing statistics."""

    total_dispatched: int = 0
    total_dropped: int = 0
    backpressure_events: int = 0
    by_consumer: dict[str, int] = Field(default_factory=dict)
    drops_by_consumer: dict[str, int] = Field(default_factory=dict)


class RoutingReporter:
    """Track routing outcomes for observability."""

    def __init__(self) -> None:
        self._total_dispatched: int = 0
        self._total_dropped: int = 0
        self._backpressure_events: int = 0
        self._by_consumer: dict[str, int] = {}
        self._drops_by_consumer: dict[str, int] = {}

    def record_dispatch(self, consumer_id: str) -> None:
        self._total_dispatched += 1
        self._by_consumer[consumer_id] = self._by_consumer.get(consumer_id, 0) + 1
        logger.info(
            "routing_dispatch_recorded",
            extra={"consumer_id": consumer_id, "total_dispatched": self._total_dispatched},
        )

    def record_drop(self, consumer_id: str) -> None:
        self._total_dropped += 1
        self._drops_by_consumer[consumer_id] = (
            self._drops_by_consumer.get(consumer_id, 0) + 1
        )
        logger.warning(
            "routing_drop_recorded",
            extra={"consumer_id": consumer_id, "total_dropped": self._total_dropped},
        )

    def record_backpressure(self) -> None:
        self._backpressure_events += 1
        logger.warning(
            "routing_backpressure_recorded",
            extra={"backpressure_events": self._backpressure_events},
        )

    def get_stats(self) -> RoutingStats:
        return RoutingStats(
            total_dispatched=self._total_dispatched,
            total_dropped=self._total_dropped,
            backpressure_events=self._backpressure_events,
            by_consumer=dict(self._by_consumer),
            drops_by_consumer=dict(self._drops_by_consumer),
        )

    @property
    def drop_rate(self) -> float:
        total = self._total_dispatched + self._total_dropped
        if total == 0:
            return 0.0
        return self._total_dropped / total
