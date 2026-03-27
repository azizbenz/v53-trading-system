"""
Build-9 / break_even_dashboard / cost_distribution_aggregator
Aggregate costs: mean, p90, p95.
"""

from __future__ import annotations

import math

from pydantic import BaseModel, Field


class CostDistribution(BaseModel, frozen=True):
    """Aggregated cost distribution."""

    scope: str  # e.g. "engine_a", "BTC/USDT", "engine_a:BTC/USDT"
    sample_size: int = 0
    mean_cost: float = 0.0
    p90_cost: float = 0.0
    p95_cost: float = 0.0
    min_cost: float = 0.0
    max_cost: float = 0.0


def _percentile(sorted_values: list[float], p: float) -> float:
    """Compute percentile from sorted list (linear interpolation)."""
    if not sorted_values:
        return 0.0
    n = len(sorted_values)
    idx = p * (n - 1)
    lo = int(math.floor(idx))
    hi = min(lo + 1, n - 1)
    frac = idx - lo
    return sorted_values[lo] * (1.0 - frac) + sorted_values[hi] * frac


def aggregate_costs(
    scope: str,
    costs: tuple[float, ...],
) -> CostDistribution:
    """Aggregate cost samples into distribution statistics."""
    if not costs:
        return CostDistribution(scope=scope)

    sorted_c = sorted(costs)
    n = len(sorted_c)
    mean = sum(sorted_c) / n

    return CostDistribution(
        scope=scope,
        sample_size=n,
        mean_cost=mean,
        p90_cost=_percentile(sorted_c, 0.90),
        p95_cost=_percentile(sorted_c, 0.95),
        min_cost=sorted_c[0],
        max_cost=sorted_c[-1],
    )
