"""
Build-3 / execution_cost_meter / adverse_selection_meter
Measure post-fill unfavorable movement (adverse selection).

AS_i(Δ) = sign(side) · (Mid_{t+Δ} - P_exec) / P_exec
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class AdverseSelectionMeasurement(BaseModel, frozen=True):
    """Adverse selection measurement for a single trade."""

    order_id: str
    pair: str
    side: str
    exec_price: float
    mid_after: float
    delay_s: float  # Δ — time after fill
    adverse_selection: float  # AS_i(Δ)


def compute_adverse_selection(
    order_id: str,
    pair: str,
    side: str,
    exec_price: float,
    mid_after: float,
    delay_s: float,
) -> AdverseSelectionMeasurement:
    """Compute adverse selection.

    AS_i(Δ) = sign(side) · (Mid_{t+Δ} - P_exec) / P_exec

    sign(buy) = +1, sign(sell) = -1.

    For a buy (sign=+1):
      - Mid rises after fill  → AS > 0 (favorable: bought before price went up)
      - Mid drops after fill   → AS < 0 (unfavorable: bought before price went down)
    For a sell (sign=-1):
      - Mid rises after fill  → AS < 0 (unfavorable: sold before price went up)
      - Mid drops after fill   → AS > 0 (favorable: sold before price went down)

    Positive AS = favorable post-fill movement. Negative AS = adverse movement.
    """
    if exec_price <= 0:
        as_value = 0.0
    else:
        sign = 1.0 if side.lower() == "buy" else -1.0
        as_value = sign * (mid_after - exec_price) / exec_price

    return AdverseSelectionMeasurement(
        order_id=order_id,
        pair=pair,
        side=side,
        exec_price=exec_price,
        mid_after=mid_after,
        delay_s=delay_s,
        adverse_selection=as_value,
    )
