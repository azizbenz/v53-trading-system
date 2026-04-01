"""
Build-3 / execution_cost_meter / cost_aggregator
Aggregate cost by trade, pair, engine. Compare expected vs realized.

c_i = f_i + c_impl + AS_i + PF_i + MI_i
BE_{k,j} = E[c | engine=k, pair=j]

GEM-08: added market_impact term (MI_i) to cost model.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class TradeCost(BaseModel, frozen=True):
    """Total cost for a single trade.

    c_i = f_i + c_impl + AS_i + PF_i + MI_i
    GEM-08: market_impact added.
    """

    order_id: str
    pair: str
    engine_id: str
    explicit_fee: float  # f_i
    implicit_cost: float  # c_impl (ELW)
    adverse_selection: float  # AS_i
    partial_fill_cost: float  # PF_i
    market_impact: float = 0.0  # MI_i (GEM-08)
    total_cost: float  # c_i
    expected_cost: float = 0.0  # ex ante estimate
    cost_surprise: float = 0.0  # realized - expected


class CostAggregate(BaseModel, frozen=True):
    """Aggregated cost statistics."""

    count: int = 0
    avg_total_cost: float = 0.0
    avg_explicit_fee: float = 0.0
    avg_implicit_cost: float = 0.0
    avg_adverse_selection: float = 0.0
    p90_total_cost: float = 0.0
    avg_cost_surprise: float = 0.0
    by_engine: dict[str, float] = Field(default_factory=dict)  # engine -> avg total cost
    by_pair: dict[str, float] = Field(default_factory=dict)  # pair -> avg total cost


def compute_trade_cost(
    order_id: str,
    pair: str,
    engine_id: str,
    explicit_fee: float,
    implicit_cost: float,
    adverse_selection: float = 0.0,
    partial_fill_cost: float = 0.0,
    market_impact: float = 0.0,
    expected_cost: float = 0.0,
) -> TradeCost:
    """Compute total cost for a single trade.

    c_i = f_i + c_impl + AS_i + PF_i + MI_i
    GEM-08: market_impact included in total.
    """
    total = explicit_fee + implicit_cost + adverse_selection + partial_fill_cost + market_impact
    surprise = total - expected_cost

    return TradeCost(
        order_id=order_id,
        pair=pair,
        engine_id=engine_id,
        explicit_fee=explicit_fee,
        implicit_cost=implicit_cost,
        adverse_selection=adverse_selection,
        partial_fill_cost=partial_fill_cost,
        market_impact=market_impact,
        total_cost=total,
        expected_cost=expected_cost,
        cost_surprise=surprise,
    )


class CostAggregator:
    """Aggregate costs across trades, pairs, engines."""

    def __init__(self) -> None:
        self._costs: list[TradeCost] = []

    def record(self, cost: TradeCost) -> None:
        self._costs.append(cost)

    def get_aggregate(self) -> CostAggregate:
        if not self._costs:
            return CostAggregate()

        n = len(self._costs)
        totals = [c.total_cost for c in self._costs]

        # By engine
        by_engine: dict[str, list[float]] = {}
        for c in self._costs:
            by_engine.setdefault(c.engine_id, []).append(c.total_cost)

        # By pair
        by_pair: dict[str, list[float]] = {}
        for c in self._costs:
            by_pair.setdefault(c.pair, []).append(c.total_cost)

        sorted_totals = sorted(totals)
        p90_idx = min(int(n * 0.9), n - 1)

        return CostAggregate(
            count=n,
            avg_total_cost=sum(totals) / n,
            avg_explicit_fee=sum(c.explicit_fee for c in self._costs) / n,
            avg_implicit_cost=sum(c.implicit_cost for c in self._costs) / n,
            avg_adverse_selection=sum(c.adverse_selection for c in self._costs) / n,
            p90_total_cost=sorted_totals[p90_idx],
            avg_cost_surprise=sum(c.cost_surprise for c in self._costs) / n,
            by_engine={k: sum(v) / len(v) for k, v in by_engine.items()},
            by_pair={k: sum(v) / len(v) for k, v in by_pair.items()},
        )

    def get_break_even(self, engine_id: str, pair: str) -> float:
        """BE_{k,j} = E[c | engine=k, pair=j]."""
        costs = [c.total_cost for c in self._costs if c.engine_id == engine_id and c.pair == pair]
        return sum(costs) / len(costs) if costs else 0.0
