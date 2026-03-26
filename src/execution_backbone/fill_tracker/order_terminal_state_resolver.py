"""
Build-3 / fill_tracker / order_terminal_state_resolver
Define and resolve terminal states for orders.

Terminal states: FILLED, CANCELLED (partially_filled_cancelled), EXPIRED, REJECTED.
Invariant: terminal state must be explicit. Acked ≠ filled.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from .order_state_tracker import OrderState, TERMINAL_STATES


class TerminalCategory(StrEnum):
    FULL_FILL = "full_fill"
    PARTIAL_FILL_CANCELLED = "partial_fill_cancelled"
    ZERO_FILL_CANCELLED = "zero_fill_cancelled"
    EXPIRED_WITH_FILLS = "expired_with_fills"
    EXPIRED_NO_FILLS = "expired_no_fills"
    REJECTED = "rejected"


class TerminalResolution(BaseModel, frozen=True):
    """Resolved terminal state with category."""

    order_id: str
    state: OrderState
    category: TerminalCategory
    filled_quantity: float
    ordered_quantity: float
    fill_ratio: float  # filled / ordered
    has_residual: bool  # quantity left unfilled


def resolve_terminal(
    order_id: str,
    state: OrderState,
    ordered_quantity: float,
    filled_quantity: float,
) -> TerminalResolution:
    """Resolve terminal state into a precise category."""
    if state not in TERMINAL_STATES:
        raise ValueError(f"Order {order_id} is not in terminal state: {state}")

    fill_ratio = filled_quantity / ordered_quantity if ordered_quantity > 0 else 0.0
    has_residual = filled_quantity < ordered_quantity

    if state == OrderState.FILLED:
        category = TerminalCategory.FULL_FILL
    elif state == OrderState.REJECTED:
        category = TerminalCategory.REJECTED
    elif state == OrderState.CANCELLED:
        category = (
            TerminalCategory.PARTIAL_FILL_CANCELLED
            if filled_quantity > 0
            else TerminalCategory.ZERO_FILL_CANCELLED
        )
    elif state == OrderState.EXPIRED:
        category = (
            TerminalCategory.EXPIRED_WITH_FILLS
            if filled_quantity > 0
            else TerminalCategory.EXPIRED_NO_FILLS
        )
    else:
        category = TerminalCategory.REJECTED  # fallback

    return TerminalResolution(
        order_id=order_id,
        state=state,
        category=category,
        filled_quantity=filled_quantity,
        ordered_quantity=ordered_quantity,
        fill_ratio=fill_ratio,
        has_residual=has_residual,
    )
