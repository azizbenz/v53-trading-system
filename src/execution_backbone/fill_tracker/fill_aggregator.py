"""
Build-3 / fill_tracker / fill_aggregator
Aggregate multiple fills from the same order.

Invariant: all fills must link to an order. Partial fills must never be ignored.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from interface_contracts import (
    decimal_to_canonical_str,
    decimal_to_float64,
    divide_exact_or_zero,
    multiply_exact,
    sum_exact,
)


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
    total_filled_qty_exact: str
    average_price: float
    average_price_exact: str
    total_notional: float
    total_notional_exact: str
    total_fees: float
    total_fees_exact: str
    fill_count: int
    first_fill_time: float
    last_fill_time: float
    fills: tuple[FillEvent, ...] = ()


class FillAggregator:
    """Aggregate fills per order."""

    def __init__(self) -> None:
        self._fills: dict[str, list[FillEvent]] = {}  # order_id -> fills
        self._seen_fill_ids: set[str] = set()

    def record_fill(self, fill: FillEvent) -> AggregatedFill:
        """Record a fill and return updated aggregation."""
        if fill.fill_id in self._seen_fill_ids:
            aggregated = self.get_aggregated(fill.order_id)
            if aggregated is None:
                raise RuntimeError(f"Duplicate fill {fill.fill_id} seen before aggregation exists")
            return aggregated
        if fill.order_id not in self._fills:
            self._fills[fill.order_id] = []
        else:
            first = self._fills[fill.order_id][0]
            if first.pair != fill.pair or first.side != fill.side:
                raise ValueError(
                    f"Fill {fill.fill_id} conflicts with existing order aggregation for {fill.order_id}",
                )
        self._seen_fill_ids.add(fill.fill_id)
        self._fills[fill.order_id].append(fill)
        aggregated = self.get_aggregated(fill.order_id)
        if aggregated is None:
            raise RuntimeError(f"Aggregation unexpectedly missing for order {fill.order_id}")
        return aggregated

    def get_aggregated(self, order_id: str) -> AggregatedFill | None:
        fills = self._fills.get(order_id)
        if not fills:
            return None

        total_qty_exact = sum_exact(f.quantity for f in fills)
        total_notional_exact = sum_exact(
            multiply_exact(f.price, f.quantity) for f in fills
        )
        avg_price_exact = divide_exact_or_zero(total_notional_exact, total_qty_exact)
        total_fees_exact = sum_exact(f.fee for f in fills)

        return AggregatedFill(
            order_id=order_id,
            pair=fills[0].pair,
            side=fills[0].side,
            total_filled_qty=decimal_to_float64(total_qty_exact),
            total_filled_qty_exact=decimal_to_canonical_str(total_qty_exact),
            average_price=decimal_to_float64(avg_price_exact),
            average_price_exact=decimal_to_canonical_str(avg_price_exact),
            total_notional=decimal_to_float64(total_notional_exact),
            total_notional_exact=decimal_to_canonical_str(total_notional_exact),
            total_fees=decimal_to_float64(total_fees_exact),
            total_fees_exact=decimal_to_canonical_str(total_fees_exact),
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
