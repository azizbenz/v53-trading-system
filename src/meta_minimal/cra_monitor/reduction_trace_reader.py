"""
Build-9 / cra_monitor / reduction_trace_reader
Read reduction traces from scoring/allocation pipeline.

Extracts: original size, final size, reduction multiplier, reduction causes.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ReductionTrace(BaseModel, frozen=True):
    """One reduction trace for a trade."""

    pair: str
    engine_id: str
    original_size: float
    final_size: float
    multiplier: float  # final / original
    reduction_causes: tuple[str, ...] = ()
    expected_cost: float = 0.0
    ce_expected: float = 0.0
    holding_hours: float = 0.0


def read_reduction(
    pair: str,
    engine_id: str,
    original_size: float,
    final_size: float,
    reduction_causes: tuple[str, ...] = (),
    expected_cost: float = 0.0,
    ce_expected: float = 0.0,
    holding_hours: float = 0.0,
) -> ReductionTrace:
    """Build a ReductionTrace from allocation pipeline outputs."""
    mult = final_size / original_size if original_size > 0.0 else 0.0
    return ReductionTrace(
        pair=pair,
        engine_id=engine_id,
        original_size=original_size,
        final_size=final_size,
        multiplier=mult,
        reduction_causes=reduction_causes,
        expected_cost=expected_cost,
        ce_expected=ce_expected,
        holding_hours=holding_hours,
    )
