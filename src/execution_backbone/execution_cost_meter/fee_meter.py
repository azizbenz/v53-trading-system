"""
Build-3 / execution_cost_meter / fee_meter
Calculate exact explicit fees per trade.

Invariant: no execution is "free" by default. Explicit cost always measurable.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class FeeBreakdown(BaseModel, frozen=True):
    """Explicit fee breakdown for a single trade."""

    order_id: str
    pair: str
    gross_value: float  # price * quantity
    fee_amount: float
    fee_rate: float  # fee / gross_value
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
    gross_value = price * quantity
    fee_rate = fee_amount / gross_value if gross_value > 0 else 0.0

    return FeeBreakdown(
        order_id=order_id,
        pair=pair,
        gross_value=gross_value,
        fee_amount=fee_amount,
        fee_rate=fee_rate,
        fee_asset=fee_asset,
        maker=maker,
    )


def estimate_fee(
    price: float,
    quantity: float,
    fee_rate: float = 0.001,  # default 10bps taker
) -> float:
    """Estimate fee from rate (ex ante)."""
    return price * quantity * fee_rate
