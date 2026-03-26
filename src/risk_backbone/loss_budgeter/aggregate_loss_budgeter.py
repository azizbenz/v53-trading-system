"""
Build-4 / loss_budgeter / aggregate_loss_budgeter
Aggregate L_i across all active positions.

LossBudget = Σ L_i
LossUtil = LossBudget / LB_max
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from .position_loss_estimator import PositionLossEstimate


class AggregateLossBudget(BaseModel, frozen=True):
    """Aggregate loss budget across all active positions."""

    total_loss_budget: float  # LossBudget = Σ L_i
    position_count: int
    loss_cap: float  # LB_max
    utilization: float  # LossUtil = LossBudget / LB_max
    remaining_capacity: float  # LB_max - LossBudget
    by_pair: dict[str, float] = Field(default_factory=dict)
    by_engine: dict[str, float] = Field(default_factory=dict)


def aggregate_loss_budget(
    estimates: tuple[PositionLossEstimate, ...],
    loss_cap: float,
) -> AggregateLossBudget:
    """Aggregate L_i across all positions.

    LossBudget = Σ L_i
    LossUtil = LossBudget / LB_max
    """
    by_pair: dict[str, float] = {}
    by_engine: dict[str, float] = {}

    for e in estimates:
        by_pair[e.pair] = by_pair.get(e.pair, 0.0) + e.loss_amount
        by_engine[e.engine_id] = by_engine.get(e.engine_id, 0.0) + e.loss_amount

    total = sum(e.loss_amount for e in estimates)

    return AggregateLossBudget(
        total_loss_budget=total,
        position_count=len(estimates),
        loss_cap=loss_cap,
        utilization=total / loss_cap if loss_cap > 0 else 0.0,
        remaining_capacity=loss_cap - total,
        by_pair=by_pair,
        by_engine=by_engine,
    )
