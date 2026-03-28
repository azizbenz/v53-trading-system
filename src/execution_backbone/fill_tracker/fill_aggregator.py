"""
Build-3 / fill_tracker / fill_aggregator
Aggregate multiple fills from the same order.

Invariant: all fills must link to an order. Partial fills must never be ignored.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class FillEvent(BaseModel, frozen=True):
    """A single fill event from the exchange."""

    fill_id: str
    order_id: str
    pair: str
    side: str
    quantity: float
    price: float
    fee: float = 0.0
    fee_asset: str = ""
    timestamp: float = 0.0


class AggregatedFill(BaseModel, frozen=True):
    """Aggregated fill state for a single order."""

    order_id: str
    pair: str
    side: str
    total_filled_qty: float
    average_price: float
    total_fees: float
    fill_count: int
    first_fill_time: float
    last_fill_time: float
    fills: tuple[FillEvent, ...] = ()


class FillAggregator:
    """Aggregate fills per order."""

    def __init__(self) -> None:
        self._fills: dict[str, list[FillEvent]] = {}  # order_id -> fills

    def record_fill(self, fill: FillEvent) -> AggregatedFill:
        """Record a fill and return updated aggregation."""
        if fill.order_id not in self._fills:
            self._fills[fill.order_id] = []
        self._fills[fill.order_id].append(fill)
        aggregated = self.get_aggregated(fill.order_id)
        if aggregated is None:
            raise RuntimeError(f"Aggregation unexpectedly missing for order {fill.order_id}")
        return aggregated

    def get_aggregated(self, order_id: str) -> AggregatedFill | None:
        fills = self._fills.get(order_id)
        if not fills:
            return None

        total_qty = sum(f.quantity for f in fills)
        if total_qty > 0:
            avg_price = sum(f.price * f.quantity for f in fills) / total_qty
        else:
            avg_price = 0.0

        return AggregatedFill(
            order_id=order_id,
            pair=fills[0].pair,
            side=fills[0].side,
            total_filled_qty=total_qty,
            average_price=avg_price,
            total_fees=sum(f.fee for f in fills),
            fill_count=len(fills),
            first_fill_time=fills[0].timestamp,
            last_fill_time=fills[-1].timestamp,
            fills=tuple(fills),
        )

    def get_fills_for_order(self, order_id: str) -> tuple[FillEvent, ...]:
        return tuple(self._fills.get(order_id, []))

    @property
    def total_fills(self) -> int:
        return sum(len(f) for f in self._fills.values())
