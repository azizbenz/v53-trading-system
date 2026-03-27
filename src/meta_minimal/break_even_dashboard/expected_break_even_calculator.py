"""
Build-9 / break_even_dashboard / expected_break_even_calculator
Calculate break-even ex ante (before execution).

Simple: g_BE = c_i
Prudent: g_BE_cons = f_i + s_p90 + q_p90 + a_p90
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ExpectedBreakEven(BaseModel, frozen=True):
    """Expected break-even result for a trade."""

    pair: str
    engine_id: str
    simple_be: float  # g_BE = expected total cost
    prudent_be: float  # g_BE_cons = fee + spread_p90 + slippage_p90 + adverse_p90


def compute_expected_break_even(
    pair: str,
    engine_id: str,
    expected_fee: float = 0.0,
    expected_spread: float = 0.0,
    expected_slippage: float = 0.0,
    expected_adverse: float = 0.0,
    spread_p90: float = 0.0,
    slippage_p90: float = 0.0,
    adverse_p90: float = 0.0,
) -> ExpectedBreakEven:
    """Compute expected break-even.

    Simple: total expected cost.
    Prudent: fee + p90 components (conservative).
    """
    simple = expected_fee + expected_spread + expected_slippage + expected_adverse
    prudent = expected_fee + spread_p90 + slippage_p90 + adverse_p90

    return ExpectedBreakEven(
        pair=pair,
        engine_id=engine_id,
        simple_be=simple,
        prudent_be=prudent,
    )
