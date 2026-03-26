"""
Build-3 / order_decider / order_type_selector
Choose market/limit/no-trade based on cost, context, and expected gain.

Condition: E[g_i | F_i] > E[c_i | F_i] + δ_safe
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from .intent_builder import OrderType


class OrderTypeDecision(BaseModel, frozen=True):
    """Result of order type selection."""

    order_type: OrderType
    reason: str
    expected_cost: float
    expected_gain: float
    safety_margin: float  # δ_safe
    net_expected: float  # E[g] - E[c] - δ_safe


def select_order_type(
    expected_gain: float,
    expected_cost: float,
    safety_margin: float = 0.0005,
    spread_bps: float = 0.0,
    max_spread_for_market: float = 10.0,
    use_limit_threshold_bps: float = 5.0,
) -> OrderTypeDecision:
    """Select order type based on execution economics.

    E[g_i | F_i] > E[c_i | F_i] + δ_safe  →  trade authorized
    Otherwise → NO_TRADE

    Among authorized trades:
    - If spread is tight (< threshold) → MARKET
    - If spread is wide → LIMIT
    """
    net_expected = expected_gain - expected_cost - safety_margin

    if net_expected <= 0:
        return OrderTypeDecision(
            order_type=OrderType.NO_TRADE,
            reason=f"Expected net {net_expected:.6f} <= 0 (gain={expected_gain:.6f}, cost={expected_cost:.6f}, δ={safety_margin:.6f})",
            expected_cost=expected_cost,
            expected_gain=expected_gain,
            safety_margin=safety_margin,
            net_expected=net_expected,
        )

    if spread_bps > max_spread_for_market:
        return OrderTypeDecision(
            order_type=OrderType.NO_TRADE,
            reason=f"Spread {spread_bps:.1f} bps > max {max_spread_for_market:.1f} bps",
            expected_cost=expected_cost,
            expected_gain=expected_gain,
            safety_margin=safety_margin,
            net_expected=net_expected,
        )

    if spread_bps > use_limit_threshold_bps:
        return OrderTypeDecision(
            order_type=OrderType.LIMIT,
            reason=f"Spread {spread_bps:.1f} bps > limit threshold {use_limit_threshold_bps:.1f} bps → LIMIT preferred",
            expected_cost=expected_cost,
            expected_gain=expected_gain,
            safety_margin=safety_margin,
            net_expected=net_expected,
        )

    return OrderTypeDecision(
        order_type=OrderType.MARKET,
        reason=f"Net expected {net_expected:.6f} > 0, spread {spread_bps:.1f} bps tight → MARKET",
        expected_cost=expected_cost,
        expected_gain=expected_gain,
        safety_margin=safety_margin,
        net_expected=net_expected,
    )
