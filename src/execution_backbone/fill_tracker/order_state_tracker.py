"""
Build-3 / fill_tracker / order_state_tracker
Maintain order lifecycle state: sent → ack → partial → filled / cancelled / expired / rejected.

Invariant: no order can exist without a current state. Terminal state must be explicit.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class OrderState(StrEnum):
    PENDING = "pending"        # intent created, not yet sent
    SENT = "sent"              # sent to exchange
    ACKED = "acked"            # exchange acknowledged (NOT filled)
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"          # terminal
    CANCELLED = "cancelled"    # terminal
    EXPIRED = "expired"        # terminal
    REJECTED = "rejected"      # terminal


TERMINAL_STATES: frozenset[OrderState] = frozenset({
    OrderState.FILLED,
    OrderState.CANCELLED,
    OrderState.EXPIRED,
    OrderState.REJECTED,
})


class OrderRecord(BaseModel, frozen=True):
    """Snapshot of an order's current state."""

    order_id: str
    pair: str
    engine_id: str
    side: str
    order_type: str
    quantity: float
    state: OrderState
    filled_quantity: float = 0.0
    average_fill_price: float = 0.0
    sent_time: float | None = None
    ack_time: float | None = None
    first_fill_time: float | None = None
    last_update_time: float | None = None
    cancel_reason: str = ""


class OrderStateTracker:
    """Track order lifecycle states."""

    def __init__(self) -> None:
        self._orders: dict[str, OrderRecord] = {}

    def register_order(
        self, order_id: str, pair: str, engine_id: str,
        side: str, order_type: str, quantity: float,
    ) -> OrderRecord:
        record = OrderRecord(
            order_id=order_id, pair=pair, engine_id=engine_id,
            side=side, order_type=order_type, quantity=quantity,
            state=OrderState.PENDING,
        )
        self._orders[order_id] = record
        return record

    def mark_sent(self, order_id: str, sent_time: float) -> OrderRecord:
        old = self._get(order_id)
        new = old.model_copy(update={"state": OrderState.SENT, "sent_time": sent_time, "last_update_time": sent_time})
        self._orders[order_id] = new
        return new

    def mark_acked(self, order_id: str, ack_time: float) -> OrderRecord:
        old = self._get(order_id)
        new = old.model_copy(update={"state": OrderState.ACKED, "ack_time": ack_time, "last_update_time": ack_time})
        self._orders[order_id] = new
        return new

    def mark_fill(
        self, order_id: str, fill_qty: float, fill_price: float, fill_time: float,
    ) -> OrderRecord:
        """Record a fill (partial or complete)."""
        old = self._get(order_id)
        new_filled = old.filled_quantity + fill_qty
        # Weighted average price
        if old.filled_quantity + fill_qty > 0:
            avg = (old.average_fill_price * old.filled_quantity + fill_price * fill_qty) / new_filled
        else:
            avg = fill_price

        is_full = new_filled >= old.quantity
        new_state = OrderState.FILLED if is_full else OrderState.PARTIALLY_FILLED
        first_fill = old.first_fill_time if old.first_fill_time is not None else fill_time

        new = old.model_copy(update={
            "state": new_state,
            "filled_quantity": new_filled,
            "average_fill_price": avg,
            "first_fill_time": first_fill,
            "last_update_time": fill_time,
        })
        self._orders[order_id] = new
        return new

    def mark_cancelled(self, order_id: str, time: float, reason: str = "") -> OrderRecord:
        old = self._get(order_id)
        state = OrderState.CANCELLED
        new = old.model_copy(update={"state": state, "cancel_reason": reason, "last_update_time": time})
        self._orders[order_id] = new
        return new

    def mark_expired(self, order_id: str, time: float) -> OrderRecord:
        old = self._get(order_id)
        new = old.model_copy(update={"state": OrderState.EXPIRED, "last_update_time": time})
        self._orders[order_id] = new
        return new

    def mark_rejected(self, order_id: str, time: float, reason: str = "") -> OrderRecord:
        old = self._get(order_id)
        new = old.model_copy(update={"state": OrderState.REJECTED, "cancel_reason": reason, "last_update_time": time})
        self._orders[order_id] = new
        return new

    def get(self, order_id: str) -> OrderRecord | None:
        return self._orders.get(order_id)

    def is_terminal(self, order_id: str) -> bool:
        rec = self._orders.get(order_id)
        return rec is not None and rec.state in TERMINAL_STATES

    def get_open_orders(self) -> tuple[OrderRecord, ...]:
        return tuple(r for r in self._orders.values() if r.state not in TERMINAL_STATES)

    def get_all(self) -> tuple[OrderRecord, ...]:
        return tuple(self._orders.values())

    def _get(self, order_id: str) -> OrderRecord:
        if order_id not in self._orders:
            raise KeyError(f"Order '{order_id}' not registered")
        return self._orders[order_id]
