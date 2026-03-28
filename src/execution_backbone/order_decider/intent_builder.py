"""
Build-3 / order_decider / intent_builder
Construct ExecutionIntent from a validated signal candidate.

Invariant: every order has a justification. No order departs without estimated ex ante cost.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class OrderType(StrEnum):
    MARKET = "market"
    LIMIT = "limit"
    NO_TRADE = "no_trade"


class ExecutionIntent(BaseModel, frozen=True):
    """A fully-justified execution intention.

    Contains everything needed to send an order or explain why no order was sent.
    """

    intent_id: str
    pair: str
    engine_id: str
    side: str  # "buy" | "sell"
    order_type: OrderType
    quantity: float
    price_limit: float | None = None  # only for LIMIT orders
    expected_cost: float = 0.0  # ex ante estimated total cost
    expected_gain: float = 0.0  # expected signal gain
    score: float = 0.0  # final signal score
    justification: str = ""
    timeout_s: float = 0.0  # 0 = no timeout
    profile: str = "LIGHT"
    metadata: dict[str, object] = Field(default_factory=dict)


class NoTradeReason(StrEnum):
    COST_EXCEEDS_GAIN = "cost_exceeds_gain"
    PAIR_SUSPENDED = "pair_suspended"
    RISK_BUDGET_EXHAUSTED = "risk_budget_exhausted"
    INFRASTRUCTURE_DOWN = "infrastructure_down"
    HARD_BLOCKER = "hard_blocker"
    SCORE_TOO_LOW = "score_too_low"


class NoTradeDecision(BaseModel, frozen=True):
    """Explicit no-trade decision with reason."""

    pair: str
    engine_id: str
    reason: NoTradeReason
    detail: str = ""
    expected_cost: float = 0.0
    expected_gain: float = 0.0
    score: float = 0.0


def build_intent(
    intent_id: str,
    pair: str,
    engine_id: str,
    side: str,
    order_type: OrderType,
    quantity: float,
    expected_cost: float,
    expected_gain: float,
    score: float,
    justification: str,
    price_limit: float | None = None,
    timeout_s: float = 0.0,
    profile: str = "LIGHT",
) -> ExecutionIntent:
    """Build a validated ExecutionIntent."""
    return ExecutionIntent(
        intent_id=intent_id,
        pair=pair,
        engine_id=engine_id,
        side=side,
        order_type=order_type,
        quantity=quantity,
        price_limit=price_limit,
        expected_cost=expected_cost,
        expected_gain=expected_gain,
        score=score,
        justification=justification,
        timeout_s=timeout_s,
        profile=profile,
    )
