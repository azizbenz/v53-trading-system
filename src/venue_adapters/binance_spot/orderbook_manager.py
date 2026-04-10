"""Snapshot + delta replay manager for Binance Spot order-book streams."""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, Field

from data_backbone.freshness_checker.venue_stream_freshness import (
    VenueStreamFreshnessStatus,
    evaluate_venue_stream_freshness,
)
from interface_contracts import decimal_to_canonical_str, execution_decimal


def _canonical_level(value: str | float | int) -> str:
    return decimal_to_canonical_str(execution_decimal(value))


class OrderBookSyncState(StrEnum):
    BOOTSTRAPPING = "bootstrapping"
    SYNCED = "synced"
    STALE = "stale"


class BinanceDepthSnapshot(BaseModel, frozen=True):
    pair: str = Field(..., min_length=1)
    last_update_id: int = Field(..., ge=0)
    bids: tuple[tuple[str, str], ...] = ()
    asks: tuple[tuple[str, str], ...] = ()
    recv_time_s: float = Field(..., ge=0.0)


class BinanceDepthDelta(BaseModel, frozen=True):
    pair: str = Field(..., min_length=1)
    first_update_id: int = Field(..., ge=0)
    final_update_id: int = Field(..., ge=0)
    bids: tuple[tuple[str, str], ...] = ()
    asks: tuple[tuple[str, str], ...] = ()
    recv_time_s: float = Field(..., ge=0.0)


class BinanceOrderBookStatus(BaseModel, frozen=True):
    pair: str = Field(..., min_length=1)
    state: OrderBookSyncState
    last_update_id: int = Field(default=0, ge=0)
    top_bid: str = ""
    top_ask: str = ""
    requires_resync: bool = False
    reason: str = ""
    freshness: VenueStreamFreshnessStatus | None = None


class BinanceOrderBookManager:
    """Bounded order-book replay state for one pair."""

    def __init__(self, *, pair: str, gap_threshold_s: float, silence_threshold_s: float) -> None:
        if gap_threshold_s < 0.0:
            raise ValueError("gap_threshold_s must be >= 0")
        if silence_threshold_s < 0.0:
            raise ValueError("silence_threshold_s must be >= 0")
        self._pair = pair.upper()
        self._gap_threshold_s = gap_threshold_s
        self._silence_threshold_s = silence_threshold_s
        self._state = OrderBookSyncState.BOOTSTRAPPING
        self._last_update_id = 0
        self._last_recv_time: float | None = None
        self._reason = "snapshot_required"
        self._bids: dict[str, str] = {}
        self._asks: dict[str, str] = {}

    def apply_snapshot(self, snapshot: BinanceDepthSnapshot) -> BinanceOrderBookStatus:
        if snapshot.pair.upper() != self._pair:
            raise ValueError(f"snapshot pair {snapshot.pair!r} does not match manager pair {self._pair!r}")
        self._bids = { _canonical_level(price): _canonical_level(qty) for price, qty in snapshot.bids if execution_decimal(qty) > 0 }
        self._asks = { _canonical_level(price): _canonical_level(qty) for price, qty in snapshot.asks if execution_decimal(qty) > 0 }
        self._last_update_id = snapshot.last_update_id
        self._last_recv_time = snapshot.recv_time_s
        self._state = OrderBookSyncState.SYNCED
        self._reason = ""
        return self.build_status(now=snapshot.recv_time_s)

    def apply_delta(self, delta: BinanceDepthDelta) -> BinanceOrderBookStatus:
        if delta.pair.upper() != self._pair:
            raise ValueError(f"delta pair {delta.pair!r} does not match manager pair {self._pair!r}")
        if self._state == OrderBookSyncState.BOOTSTRAPPING:
            self._state = OrderBookSyncState.STALE
            self._reason = "snapshot_required"
            return self.build_status(now=delta.recv_time_s)
        if self._last_recv_time is not None and delta.recv_time_s - self._last_recv_time > self._gap_threshold_s:
            self._state = OrderBookSyncState.STALE
            self._reason = "time_gap"
            self._last_recv_time = delta.recv_time_s
            return self.build_status(now=delta.recv_time_s)
        if delta.final_update_id <= self._last_update_id:
            self._last_recv_time = delta.recv_time_s
            return self.build_status(now=delta.recv_time_s)
        if delta.first_update_id > self._last_update_id + 1:
            self._state = OrderBookSyncState.STALE
            self._reason = "sequence_gap"
            self._last_recv_time = delta.recv_time_s
            return self.build_status(now=delta.recv_time_s)
        if delta.final_update_id < self._last_update_id + 1:
            self._last_recv_time = delta.recv_time_s
            return self.build_status(now=delta.recv_time_s)
        self._apply_levels(self._bids, delta.bids)
        self._apply_levels(self._asks, delta.asks)
        self._last_update_id = delta.final_update_id
        self._last_recv_time = delta.recv_time_s
        self._state = OrderBookSyncState.SYNCED
        self._reason = ""
        return self.build_status(now=delta.recv_time_s)

    def mark_stale(self, *, reason: str, now: float) -> BinanceOrderBookStatus:
        self._state = OrderBookSyncState.STALE
        self._reason = reason
        self._last_recv_time = now
        return self.build_status(now=now)

    def build_status(self, *, now: float) -> BinanceOrderBookStatus:
        freshness = evaluate_venue_stream_freshness(
            last_update_time=self._last_recv_time,
            now=now,
            stale_threshold_s=self._silence_threshold_s,
        )
        state = self._state
        reason = self._reason
        if state == OrderBookSyncState.SYNCED and freshness.is_stale:
            state = OrderBookSyncState.STALE
            reason = freshness.reason
        return BinanceOrderBookStatus(
            pair=self._pair,
            state=state,
            last_update_id=self._last_update_id,
            top_bid=self._top_bid(),
            top_ask=self._top_ask(),
            requires_resync=state != OrderBookSyncState.SYNCED,
            reason=reason,
            freshness=freshness,
        )

    def _apply_levels(self, side: dict[str, str], levels: tuple[tuple[str, str], ...]) -> None:
        for price, qty in levels:
            normalized_price = _canonical_level(price)
            normalized_qty = _canonical_level(qty)
            if execution_decimal(normalized_qty) <= 0:
                side.pop(normalized_price, None)
            else:
                side[normalized_price] = normalized_qty

    def _top_bid(self) -> str:
        if not self._bids:
            return ""
        return max(self._bids, key=lambda value: Decimal(value))

    def _top_ask(self) -> str:
        if not self._asks:
            return ""
        return min(self._asks, key=lambda value: Decimal(value))


__all__ = [
    "BinanceDepthDelta",
    "BinanceDepthSnapshot",
    "BinanceOrderBookManager",
    "BinanceOrderBookStatus",
    "OrderBookSyncState",
]
