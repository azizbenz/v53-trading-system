"""
6.5.1 — Schema Mapper: map raw payloads to internal event contracts.

Invariant: no raw payload leaks into business modules. Every event has
type, pair, source, recv_time.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
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
    data: dict[str, object] = Field(default_factory=dict)


class TradeEvent(NormalizedEvent, frozen=True):
    """Normalized trade event."""

    event_type: EventType = EventType.TRADE
    price: float = 0.0
    quantity: float = 0.0
    side: str = ""  # "buy" | "sell"
    trade_id: str = ""


class DepthEvent(NormalizedEvent, frozen=True):
    """Normalized order book depth event."""

    event_type: EventType = EventType.DEPTH
    bids: list[list[float]] = Field(default_factory=list)
    asks: list[list[float]] = Field(default_factory=list)


class KlineEvent(NormalizedEvent, frozen=True):
    """Normalized kline/candlestick event."""

    event_type: EventType = EventType.KLINE
    interval: str = ""
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    close: float = 0.0
    volume: float = 0.0


class HeartbeatEvent(NormalizedEvent, frozen=True):
    """Normalized heartbeat event."""

    event_type: EventType = EventType.HEARTBEAT


class SnapshotEvent(NormalizedEvent, frozen=True):
    """Normalized REST snapshot event."""

    event_type: EventType = EventType.SNAPSHOT
    snapshot_type: str = ""  # "orderbook" | "trades" | "ticker"


class MappingError(BaseModel, frozen=True):
    """Record of a failed mapping attempt."""

    raw_payload: dict[str, object]
    reason: str
    timestamp: float


def map_raw_to_event(
    raw_payload: Mapping[str, object],
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
    payload = dict(raw_payload)

    if event_type == EventType.UNKNOWN:
        return MappingError(
            raw_payload=payload,
            reason=f"Unknown stream type: {stream_type}",
            timestamp=recv_time,
        )

    if event_type == EventType.TRADE:
        return TradeEvent(
            pair=pair,
            source=source,
            recv_time=recv_time,
            exchange_time=exchange_time,
            data=payload,
            price=_coerce_float(raw_payload.get("price", 0.0)),
            quantity=_coerce_float(raw_payload.get("quantity", raw_payload.get("qty", 0.0))),
            side=_coerce_str(raw_payload.get("side", "")),
            trade_id=_coerce_str(raw_payload.get("trade_id", raw_payload.get("id", ""))),
        )

    if event_type == EventType.DEPTH:
        return DepthEvent(
            pair=pair,
            source=source,
            recv_time=recv_time,
            exchange_time=exchange_time,
            data=payload,
            bids=_coerce_levels(raw_payload.get("bids")),
            asks=_coerce_levels(raw_payload.get("asks")),
        )

    if event_type == EventType.KLINE:
        return KlineEvent(
            pair=pair,
            source=source,
            recv_time=recv_time,
            exchange_time=exchange_time,
            data=payload,
            interval=_coerce_str(raw_payload.get("interval", "")),
            open=_coerce_float(raw_payload.get("open", 0.0)),
            high=_coerce_float(raw_payload.get("high", 0.0)),
            low=_coerce_float(raw_payload.get("low", 0.0)),
            close=_coerce_float(raw_payload.get("close", 0.0)),
            volume=_coerce_float(raw_payload.get("volume", 0.0)),
        )

    if event_type == EventType.HEARTBEAT:
        return HeartbeatEvent(
            pair=pair,
            source=source,
            recv_time=recv_time,
            exchange_time=exchange_time,
            data=payload,
        )

    if event_type == EventType.SNAPSHOT:
        return SnapshotEvent(
            pair=pair,
            source=source,
            recv_time=recv_time,
            exchange_time=exchange_time,
            data=payload,
            snapshot_type=_coerce_str(raw_payload.get("snapshot_type", "")),
        )

    return MappingError(
        raw_payload=payload,
        reason=f"Unhandled event type: {event_type}",
        timestamp=recv_time,
    )


def _coerce_str(value: object) -> str:
    return str(value)


def _coerce_float(value: object) -> float:
    if isinstance(value, bool):
        return float(int(value))
    if isinstance(value, (int, float, str)):
        return float(value)
    return 0.0


def _coerce_levels(value: object) -> list[list[float]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return []

    levels: list[list[float]] = []
    for level in value:
        if not isinstance(level, Sequence) or isinstance(level, (str, bytes, bytearray)):
            continue
        levels.append([_coerce_float(component) for component in level])
    return levels


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
