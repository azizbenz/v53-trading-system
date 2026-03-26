"""
10.5.5 — Health Reporter: detailed health reports per pair.

Invariant: health state is consultable. Suspension/recovery reasons are explicit.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from .health_state_tracker import PairHealthState


class PairHealthReport(BaseModel, frozen=True):
    """Detailed health report for a single pair."""

    pair: str
    state: PairHealthState
    health_score: float
    freshness_score: float = 1.0
    consistency_score: float = 1.0
    latency_score: float = 1.0
    recovery_score: float = 1.0
    suspension_reason: str = ""
    transition_count: int = 0


class HealthSummary(BaseModel, frozen=True):
    """Aggregate health summary across all pairs."""

    total_pairs: int = 0
    active_count: int = 0
    degraded_count: int = 0
    suspended_count: int = 0
    recovering_count: int = 0
    avg_health_score: float = 0.0
    min_health_score: float = 0.0
    reports: tuple[PairHealthReport, ...] = ()


class HealthReporter:
    """Collect and report pair health information."""

    def __init__(self) -> None:
        self._reports: dict[str, PairHealthReport] = {}

    def update_report(self, report: PairHealthReport) -> None:
        self._reports[report.pair] = report

    def get_report(self, pair: str) -> PairHealthReport | None:
        return self._reports.get(pair)

    def get_summary(self) -> HealthSummary:
        reports = tuple(self._reports.values())
        if not reports:
            return HealthSummary()

        scores = [r.health_score for r in reports]
        state_counts = {s: 0 for s in PairHealthState}
        for r in reports:
            state_counts[r.state] = state_counts.get(r.state, 0) + 1

        return HealthSummary(
            total_pairs=len(reports),
            active_count=state_counts.get(PairHealthState.ACTIVE, 0),
            degraded_count=state_counts.get(PairHealthState.DEGRADED, 0),
            suspended_count=state_counts.get(PairHealthState.SUSPENDED, 0),
            recovering_count=state_counts.get(PairHealthState.RECOVERING, 0),
            avg_health_score=sum(scores) / len(scores),
            min_health_score=min(scores),
            reports=reports,
        )

    def get_unhealthy_pairs(self, threshold: float = 0.5) -> tuple[PairHealthReport, ...]:
        return tuple(r for r in self._reports.values() if r.health_score < threshold)
