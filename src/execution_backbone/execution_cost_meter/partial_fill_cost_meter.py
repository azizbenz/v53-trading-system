"""
Build-3 / execution_cost_meter / partial_fill_cost_meter
Measure additional cost of fragmented fills.

Invariant: partial fills have measurable extra cost vs single fill.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class PartialFillCost(BaseModel, frozen=True):
    """Cost impact of partial fills for an order."""

    order_id: str
    pair: str
    fill_count: int
    ordered_quantity: float
    filled_quantity: float
    fill_ratio: float
    price_variance: float  # variance of fill prices (fragmentation cost proxy)
    unfilled_cost: float  # opportunity cost of unfilled portion (estimated)


def compute_partial_fill_cost(
    order_id: str,
    pair: str,
    ordered_quantity: float,
    fill_prices: tuple[float, ...],
    fill_quantities: tuple[float, ...],
    current_mid: float = 0.0,
) -> PartialFillCost:
    """Compute cost impact of partial/fragmented fills.

    Price variance measures dispersion across fills.
    Unfilled cost = unfilled qty * |mid - avg_fill_price| (opportunity cost).
    """
    if not fill_prices or not fill_quantities:
        return PartialFillCost(
            order_id=order_id, pair=pair,
            fill_count=0, ordered_quantity=ordered_quantity,
            filled_quantity=0.0, fill_ratio=0.0,
            price_variance=0.0, unfilled_cost=0.0,
        )

    total_filled = sum(fill_quantities)
    fill_ratio = total_filled / ordered_quantity if ordered_quantity > 0 else 0.0

    # Weighted average price
    if total_filled > 0:
        avg_price = sum(p * q for p, q in zip(fill_prices, fill_quantities)) / total_filled
    else:
        avg_price = 0.0

    # Price variance across fills
    if len(fill_prices) > 1 and total_filled > 0:
        variance = sum(
            q * (p - avg_price) ** 2 for p, q in zip(fill_prices, fill_quantities)
        ) / total_filled
    else:
        variance = 0.0

    # Opportunity cost of unfilled portion
    unfilled_qty = max(0.0, ordered_quantity - total_filled)
    unfilled_cost = unfilled_qty * abs(current_mid - avg_price) if current_mid > 0 else 0.0

    return PartialFillCost(
        order_id=order_id,
        pair=pair,
        fill_count=len(fill_prices),
        ordered_quantity=ordered_quantity,
        filled_quantity=total_filled,
        fill_ratio=fill_ratio,
        price_variance=variance,
        unfilled_cost=unfilled_cost,
    )
