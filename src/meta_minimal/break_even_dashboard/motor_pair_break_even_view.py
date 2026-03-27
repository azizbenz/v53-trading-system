"""
Build-9 / break_even_dashboard / motor_pair_break_even_view
View break-even by engine / pair / period.

BE_{k,j} = E[c | engine=k, pair=j]
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from meta_minimal.break_even_dashboard.realized_break_even_calculator import RealizedBreakEven


class BreakEvenView(BaseModel, frozen=True):
    """Break-even view for a specific engine/pair scope."""

    scope: str  # "engine_a", "BTC/USDT", "engine_a:BTC/USDT"
    sample_size: int = 0
    mean_realized_cost: float = 0.0
    mean_expected_cost: float = 0.0
    mean_cost_drift: float = 0.0
    profitable_rate: float = 0.0  # fraction of profitable trades


def build_break_even_view(
    scope: str,
    records: tuple[RealizedBreakEven, ...],
) -> BreakEvenView:
    """Build break-even view for a scope from realized records."""
    if not records:
        return BreakEvenView(scope=scope)

    n = len(records)
    mean_rc = sum(r.realized_cost for r in records) / n
    mean_ec = sum(r.expected_cost for r in records) / n
    mean_drift = sum(r.cost_drift for r in records) / n
    profitable = sum(1 for r in records if r.was_profitable)

    return BreakEvenView(
        scope=scope,
        sample_size=n,
        mean_realized_cost=mean_rc,
        mean_expected_cost=mean_ec,
        mean_cost_drift=mean_drift,
        profitable_rate=profitable / n,
    )


def build_views_by_engine_and_pair(
    records: tuple[RealizedBreakEven, ...],
) -> tuple[BreakEvenView, ...]:
    """Build break-even views grouped by engine and by pair."""
    by_engine: dict[str, list[RealizedBreakEven]] = {}
    by_pair: dict[str, list[RealizedBreakEven]] = {}

    for r in records:
        by_engine.setdefault(r.engine_id, []).append(r)
        by_pair.setdefault(r.pair, []).append(r)

    views: list[BreakEvenView] = []
    for scope, group in by_engine.items():
        views.append(build_break_even_view(scope, tuple(group)))
    for scope, group in by_pair.items():
        views.append(build_break_even_view(scope, tuple(group)))

    return tuple(views)
