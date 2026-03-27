"""
Build-9 / break_even_dashboard / realized_break_even_calculator
Calculate break-even ex post (after execution).

CostDrift = c_real - c_exp
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class RealizedBreakEven(BaseModel, frozen=True):
    """Realized break-even result for a completed trade."""

    pair: str
    engine_id: str
    realized_cost: float
    expected_cost: float
    cost_drift: float  # realized - expected
    gross_return: float  # raw return before costs
    net_return: float  # gross - realized_cost
    was_profitable: bool = False


def compute_realized_break_even(
    pair: str,
    engine_id: str,
    realized_cost: float,
    expected_cost: float,
    gross_return: float,
) -> RealizedBreakEven:
    """Compute realized break-even from actual execution data."""
    net = gross_return - realized_cost
    return RealizedBreakEven(
        pair=pair,
        engine_id=engine_id,
        realized_cost=realized_cost,
        expected_cost=expected_cost,
        cost_drift=realized_cost - expected_cost,
        gross_return=gross_return,
        net_return=net,
        was_profitable=net > 0.0,
    )
