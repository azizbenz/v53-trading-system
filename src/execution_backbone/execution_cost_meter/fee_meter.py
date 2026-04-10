"""
Build-3 / execution_cost_meter / fee_meter
Calculate exact explicit fees per trade.

Invariant: no execution is "free" by default. Explicit cost always measurable.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from interface_contracts import (
    decimal_to_canonical_str,
    decimal_to_float64,
    divide_exact_or_zero,
    execution_decimal,
    multiply_exact,
)


class FeeBreakdown(BaseModel, frozen=True):
    """Explicit fee breakdown for a single trade."""

    order_id: str
    pair: str
    gross_value: float  # price * quantity
    gross_value_exact: str
    fee_amount: float
    fee_amount_exact: str
    fee_rate: float  # fee / gross_value
    fee_rate_exact: str
    fee_asset: str = ""
    maker: bool = False  # maker vs taker


def compute_fee(
    order_id: str,
    pair: str,
    price: float,
    quantity: float,
    fee_amount: float,
    fee_asset: str = "",
    maker: bool = False,
) -> FeeBreakdown:
    """Compute explicit fee breakdown."""
    gross_value_exact = multiply_exact(price, quantity)
    if gross_value_exact == 0:
        raise ValueError("gross_value must be > 0 to compute fee rate")
    fee_amount_decimal = execution_decimal(fee_amount, name="fee_amount")
    fee_rate_exact = divide_exact_or_zero(fee_amount_decimal, gross_value_exact)

    return FeeBreakdown(
        order_id=order_id,
        pair=pair,
        gross_value=decimal_to_float64(gross_value_exact),
        gross_value_exact=decimal_to_canonical_str(gross_value_exact),
        fee_amount=decimal_to_float64(fee_amount_decimal),
        fee_amount_exact=decimal_to_canonical_str(fee_amount_decimal),
        fee_rate=decimal_to_float64(fee_rate_exact),
        fee_rate_exact=decimal_to_canonical_str(fee_rate_exact),
        fee_asset=fee_asset,
        maker=maker,
    )


def estimate_fee(
    price: float,
    quantity: float,
    fee_rate: float = 0.001,  # default 10bps taker
) -> float:
    """Estimate fee from rate (ex ante)."""
    return decimal_to_float64(multiply_exact(multiply_exact(price, quantity), fee_rate))
