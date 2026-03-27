"""
Build-9 / edge_tracker_prudent_minimal / return_aggregator
Aggregate net returns observed.

r_i = g_i - c_i
mu_hat = (1/N) * sum(r_i)
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ReturnAggregate(BaseModel, frozen=True):
    """Aggregated returns for a scope."""

    scope: str  # engine, pair, or engine:pair
    sample_size: int = 0
    gross_returns: tuple[float, ...] = ()
    net_returns: tuple[float, ...] = ()
    mean_gross: float = 0.0
    mean_net: float = 0.0
    mean_cost: float = 0.0


def aggregate_returns(
    scope: str,
    gross_returns: tuple[float, ...],
    costs: tuple[float, ...],
) -> ReturnAggregate:
    """Aggregate gross returns minus costs into net returns.

    r_i = g_i - c_i
    """
    if not gross_returns or len(gross_returns) != len(costs):
        return ReturnAggregate(scope=scope)

    net = tuple(g - c for g, c in zip(gross_returns, costs))
    n = len(net)
    mean_g = sum(gross_returns) / n
    mean_n = sum(net) / n
    mean_c = sum(costs) / n

    return ReturnAggregate(
        scope=scope,
        sample_size=n,
        gross_returns=gross_returns,
        net_returns=net,
        mean_gross=mean_g,
        mean_net=mean_n,
        mean_cost=mean_c,
    )
