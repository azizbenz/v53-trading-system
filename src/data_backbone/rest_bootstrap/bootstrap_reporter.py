"""
5.5.5 — Bootstrap Reporter: report on REST bootstrap / resync operations.

Invariant: every REST usage is explicitly logged with outcome and timing.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class BootstrapOutcome(StrEnum):
    SUCCESS = "success"
    SNAPSHOT_TOO_OLD = "snapshot_too_old"
    RATE_LIMITED = "rate_limited"
    GAP_TOO_LARGE = "gap_too_large"
    FETCH_ERROR = "fetch_error"


class BootstrapEvent(BaseModel, frozen=True):
    """Single REST bootstrap/resync event."""

    pair: str
    operation: str  # "bootstrap" | "recovery" | "gap_fill"
    outcome: BootstrapOutcome
    timestamp: float
    duration_s: float = 0.0
    message: str = ""


class BootstrapSummary(BaseModel, frozen=True):
    """Aggregate summary of REST bootstrap activity."""

    total_operations: int = 0
    successful: int = 0
    failed: int = 0
    by_outcome: dict[str, int] = Field(default_factory=dict)
    by_pair: dict[str, int] = Field(default_factory=dict)


class BootstrapReporter:
    """Collect and report REST bootstrap/resync events.

    Tracks all REST usage for auditability. REST must not become the
    real-time feed — this reporter makes usage patterns visible.
    """

    def __init__(self) -> None:
        self._events: list[BootstrapEvent] = []

    def record(self, event: BootstrapEvent) -> None:
        self._events.append(event)

    def get_events(
        self, pair: str | None = None, operation: str | None = None,
    ) -> tuple[BootstrapEvent, ...]:
        events = self._events
        if pair is not None:
            events = [e for e in events if e.pair == pair]
        if operation is not None:
            events = [e for e in events if e.operation == operation]
        return tuple(events)

    def summarize(self) -> BootstrapSummary:
        by_outcome: dict[str, int] = {}
        by_pair: dict[str, int] = {}
        successful = 0
        failed = 0

        for e in self._events:
            by_outcome[e.outcome] = by_outcome.get(e.outcome, 0) + 1
            by_pair[e.pair] = by_pair.get(e.pair, 0) + 1
            if e.outcome == BootstrapOutcome.SUCCESS:
                successful += 1
            else:
                failed += 1

        return BootstrapSummary(
            total_operations=len(self._events),
            successful=successful,
            failed=failed,
            by_outcome=by_outcome,
            by_pair=by_pair,
        )

    @property
    def total_events(self) -> int:
        return len(self._events)

    @property
    def failure_rate(self) -> float:
        if not self._events:
            return 0.0
        failures = sum(1 for e in self._events if e.outcome != BootstrapOutcome.SUCCESS)
        return failures / len(self._events)
