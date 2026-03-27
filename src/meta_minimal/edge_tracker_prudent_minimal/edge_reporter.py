"""
Build-9 / edge_tracker_prudent_minimal / edge_reporter
Expose edge results to UI, monitoring, and governance.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from meta_minimal.edge_tracker_prudent_minimal.edge_status_classifier import (
    EdgeClassification,
    EdgeStatus,
)


class EdgeReport(BaseModel, frozen=True):
    """Full edge tracking report."""

    classifications: tuple[EdgeClassification, ...] = ()
    total_scopes: int = 0
    credible_count: int = 0
    degraded_count: int = 0
    insufficient_count: int = 0
    surveillance_count: int = 0
    has_drift_warning: bool = False
    drift_scopes: tuple[str, ...] = ()


def build_edge_report(
    classifications: tuple[EdgeClassification, ...],
) -> EdgeReport:
    """Build the final edge report from all scope classifications."""
    counts = {s: 0 for s in EdgeStatus}
    drift_scopes: list[str] = []

    for c in classifications:
        counts[c.status] += 1
        if c.status == EdgeStatus.DEGRADED:
            drift_scopes.append(c.scope)

    return EdgeReport(
        classifications=classifications,
        total_scopes=len(classifications),
        credible_count=counts[EdgeStatus.CREDIBLE],
        degraded_count=counts[EdgeStatus.DEGRADED],
        insufficient_count=counts[EdgeStatus.INSUFFICIENT],
        surveillance_count=counts[EdgeStatus.UNDER_SURVEILLANCE],
        has_drift_warning=len(drift_scopes) > 0,
        drift_scopes=tuple(drift_scopes),
    )
