"""
Build-9 / break_even_dashboard / break_even_reporter
Final break-even report for UI and monitoring.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from meta_minimal.break_even_dashboard.cost_distribution_aggregator import CostDistribution
from meta_minimal.break_even_dashboard.motor_pair_break_even_view import BreakEvenView


class BreakEvenReport(BaseModel, frozen=True):
    """Full break-even report."""

    views: tuple[BreakEvenView, ...] = ()
    cost_distributions: tuple[CostDistribution, ...] = ()
    global_mean_cost: float = 0.0
    global_profitable_rate: float = 0.0
    has_cost_drift_alert: bool = False
    cost_drift_alert_scopes: tuple[str, ...] = ()


_DRIFT_ALERT_THRESHOLD = 0.20  # 20% cost drift triggers alert


def build_break_even_report(
    views: tuple[BreakEvenView, ...],
    cost_distributions: tuple[CostDistribution, ...] = (),
    drift_threshold: float = _DRIFT_ALERT_THRESHOLD,
) -> BreakEvenReport:
    """Build final break-even report.

    Flags scopes where mean cost drift exceeds threshold.
    """
    total_cost = 0.0
    total_profitable = 0.0
    total_n = 0
    drift_scopes: list[str] = []

    for v in views:
        if v.sample_size > 0:
            total_cost += v.mean_realized_cost * v.sample_size
            total_profitable += v.profitable_rate * v.sample_size
            total_n += v.sample_size

            # Check cost drift relative to expected
            if v.mean_expected_cost > 0.0:
                relative_drift = abs(v.mean_cost_drift) / v.mean_expected_cost
                if relative_drift > drift_threshold:
                    drift_scopes.append(v.scope)

    global_mean = total_cost / total_n if total_n > 0 else 0.0
    global_profit_rate = total_profitable / total_n if total_n > 0 else 0.0

    return BreakEvenReport(
        views=views,
        cost_distributions=cost_distributions,
        global_mean_cost=global_mean,
        global_profitable_rate=global_profit_rate,
        has_cost_drift_alert=len(drift_scopes) > 0,
        cost_drift_alert_scopes=tuple(drift_scopes),
    )
