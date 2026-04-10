"""
Build-4 / loss_budgeter / position_loss_estimator
Estimate L_i (planned max loss) for a single position.

L_i = x_i * |entry_price - stop_price| / entry_price
Invariant: every position must have an explicit L_i.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class PositionLossEstimate(BaseModel, frozen=True):
    """Estimated planned max loss for a single position."""

    pair: str
    engine_id: str
    size: float  # x_i
    entry_price: float
    stop_price: float
    loss_amount: float  # L_i (absolute)
    loss_pct: float  # L_i as percentage of notional


def estimate_position_loss(
    pair: str,
    engine_id: str,
    size: float,
    entry_price: float,
    stop_price: float,
) -> PositionLossEstimate:
    """Estimate L_i for a position.

    L_i = size * |entry_price - stop_price| / entry_price
    """
    if entry_price <= 0:
        raise ValueError(f"entry_price must be positive, got {entry_price}")
    if stop_price <= 0:
        raise ValueError(f"stop_price must be positive, got {stop_price}")

    loss_pct = abs(entry_price - stop_price) / entry_price
    loss_amount = size * loss_pct

    return PositionLossEstimate(
        pair=pair,
        engine_id=engine_id,
        size=size,
        entry_price=entry_price,
        stop_price=stop_price,
        loss_amount=loss_amount,
        loss_pct=loss_pct,
    )
