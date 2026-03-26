"""
6.5.1 — Schema Mapper: map raw payloads to internal event contracts.

Invariant: no raw payload leaks into business modules. Every event has
type, pair, source, recv_time.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class EventType(StrEnum):
    TRADE = "trade"
    DEPTH = "depth"
    KLINE = "kline"
    HEARTBEAT = "heartbeat"
    SNAPSHOT = "snapshot"
    UNKNOWN = "unknown"


class NormalizedEvent(BaseModel, frozen=True):
    """Internal event contract — stable, versioned, typed."""

    event_type: EventType
    pair: str
    source: str
    recv_time: float
    exchange_time: float | None = None
    schema_version: str = "1.0"
    data: dict = Field(default_factory=dict)


class TradeEvent(NormalizedEvent):
    """Normalized trade event."""

    event_type: EventType = EventType.TRADE
    price: float = 0.0
    quantity: float = 0.0
    side: str = ""  # "buy" | "sell"
    trade_id: str = ""


class DepthEvent(NormalizedEvent):
    """Normalized order book depth event."""

    event_type: EventType = EventType.DEPTH
    bids: list[list[float]] = Field(default_factory=list)
    asks: list[list[float]] = Field(default_factory=list)


class KlineEvent(NormalizedEvent):
    """Normalized kline/candlestick event."""

    event_type: EventType = EventType.KLINE
    interval: str = ""
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    close: float = 0.0
    volume: float = 0.0


class HeartbeatEvent(NormalizedEvent):
    """Normalized heartbeat event."""

    event_type: EventType = EventType.HEARTBEAT


class SnapshotEvent(NormalizedEvent):
    """Normalized REST snapshot event."""

    event_type: EventType = EventType.SNAPSHOT
    snapshot_type: str = ""  # "orderbook" | "trades" | "ticker"


class MappingError(BaseModel, frozen=True):
    """Record of a failed mapping attempt."""

    raw_payload: dict
    reason: str
    timestamp: float


def map_raw_to_event(
    raw_payload: dict,
    stream_type: str,
    pair: str,
    source: str,
    recv_time: float,
    exchange_time: float | None = None,
) -> NormalizedEvent | MappingError:
    """Map a raw payload to a typed NormalizedEvent.

    Returns MappingError if the payload cannot be mapped.
    """
    event_type = _classify_stream_type(stream_type)

    if event_type == EventType.UNKNOWN:
        return MappingError(
            raw_payload=raw_payload,
            reason=f"Unknown stream type: {stream_type}",
            timestamp=recv_time,
        )

    base_kwargs = {
        "pair": pair,
        "source": source,
        "recv_time": recv_time,
        "exchange_time": exchange_time,
        "data": raw_payload,
    }

    if event_type == EventType.TRADE:
        return TradeEvent(
            **base_kwargs,
            price=float(raw_payload.get("price", 0.0)),
            quantity=float(raw_payload.get("quantity", raw_payload.get("qty", 0.0))),
            side=str(raw_payload.get("side", "")),
            trade_id=str(raw_payload.get("trade_id", raw_payload.get("id", ""))),
        )

    if event_type == EventType.DEPTH:
        return DepthEvent(
            **base_kwargs,
            bids=raw_payload.get("bids", []),
            asks=raw_payload.get("asks", []),
        )

    if event_type == EventType.KLINE:
        return KlineEvent(
            **base_kwargs,
            interval=str(raw_payload.get("interval", "")),
            open=float(raw_payload.get("open", 0.0)),
            high=float(raw_payload.get("high", 0.0)),
            low=float(raw_payload.get("low", 0.0)),
            close=float(raw_payload.get("close", 0.0)),
            volume=float(raw_payload.get("volume", 0.0)),
        )

    if event_type == EventType.HEARTBEAT:
        return HeartbeatEvent(**base_kwargs)

    if event_type == EventType.SNAPSHOT:
        return SnapshotEvent(
            **base_kwargs,
            snapshot_type=str(raw_payload.get("snapshot_type", "")),
        )

    return MappingError(
        raw_payload=raw_payload,
        reason=f"Unhandled event type: {event_type}",
        timestamp=recv_time,
    )


def _classify_stream_type(stream_type: str) -> EventType:
    """Map raw stream type string to EventType."""
    mapping = {
        "trade": EventType.TRADE,
        "depth": EventType.DEPTH,
        "kline": EventType.KLINE,
        "heartbeat": EventType.HEARTBEAT,
        "snapshot": EventType.SNAPSHOT,
    }
    return mapping.get(stream_type.lower(), EventType.UNKNOWN)
