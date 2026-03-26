"""
Build-3 / order_decider / timeout_policy_selector
Define order time-to-live and cancellation policy.

Invariant: every order has an explicit lifetime. No order lives forever.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from .intent_builder import OrderType


class CancelPolicy(StrEnum):
    CANCEL_ON_TIMEOUT = "cancel_on_timeout"
    CONVERT_TO_MARKET = "convert_to_market"
    LEAVE_OPEN = "leave_open"  # only for special cases


class TimeoutPolicy(BaseModel, frozen=True):
    """Timeout and cancellation policy for an order."""

    timeout_s: float
    cancel_policy: CancelPolicy
    reason: str = ""


# Default timeout configurations per order type
_DEFAULT_TIMEOUTS: dict[OrderType, float] = {
    OrderType.MARKET: 5.0,  # market orders should fill fast
    OrderType.LIMIT: 30.0,  # limit orders get more time
    OrderType.NO_TRADE: 0.0,
}


def select_timeout_policy(
    order_type: OrderType,
    custom_timeout_s: float | None = None,
    cancel_policy: CancelPolicy | None = None,
) -> TimeoutPolicy:
    """Select timeout policy for an order type.

    Market → short timeout, cancel on timeout.
    Limit → longer timeout, cancel on timeout by default.
    """
    if order_type == OrderType.NO_TRADE:
        return TimeoutPolicy(
            timeout_s=0.0,
            cancel_policy=CancelPolicy.CANCEL_ON_TIMEOUT,
            reason="no-trade: no timeout needed",
        )

    timeout = custom_timeout_s if custom_timeout_s is not None else _DEFAULT_TIMEOUTS.get(order_type, 10.0)
    policy = cancel_policy if cancel_policy is not None else CancelPolicy.CANCEL_ON_TIMEOUT

    reason = f"{order_type.value} order: timeout={timeout}s, policy={policy.value}"

    return TimeoutPolicy(
        timeout_s=timeout,
        cancel_policy=policy,
        reason=reason,
    )
