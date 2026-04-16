"""Bridge injected WebSocket streams into canonical historical snapshot batches."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from data_backbone.event_normalizer.invalid_message_guard import validate_raw_message
from data_backbone.event_normalizer.message_classifier import MessageClass, classify_message
from data_backbone.event_normalizer.schema_mapper import (
    DepthEvent as NormalizedDepthEvent,
    EventType,
    HeartbeatEvent as NormalizedHeartbeatEvent,
    KlineEvent as NormalizedKlineEvent,
    MappingError,
    NormalizedEvent,
    SnapshotEvent as NormalizedSnapshotEvent,
    TradeEvent as NormalizedTradeEvent,
    map_raw_to_event,
)
from data_backbone.websocket_gateway.runtime_gateway import (
    AdapterMessage,
    WebSocketGatewayAdapter,
    WebSocketGatewayRuntime,
)
from data_backbone.websocket_gateway.injected_stream_loader import (
    InjectedWebSocketFrame,
    load_injected_websocket_frames,
)
from interface_contracts import DepthEvent, DepthLevel, KlineEvent, Side, SnapshotEvent, Timeframe, TradeEvent
from interface_contracts.atomic_io import atomic_write_json
from local_replay_runtime import HistoricalMarketEventEnvelope, HistoricalSnapshotBatch, ReplayRouteHint

NormalizedObservedEvent = (
    NormalizedTradeEvent
    | NormalizedDepthEvent
    | NormalizedKlineEvent
    | NormalizedSnapshotEvent
    | NormalizedHeartbeatEvent
)
MarketEvent = TradeEvent | DepthEvent | KlineEvent | SnapshotEvent


class ObservedWebSocketMessage(BaseModel, frozen=True):
    """Single observed websocket message plus routing metadata."""

    pair: str = Field(..., min_length=1)
    stream_type: str = Field(..., min_length=1)
    payload: dict[str, object] = Field(default_factory=dict)
    recv_time: float = Field(..., gt=0.0)
    source: str = Field(default="websocket", min_length=1)
    sequence: int | None = None
    route_hint: dict[str, object] = Field(default_factory=dict)


class ShadowWebsocketSnapshotBuildResult(BaseModel, frozen=True):
    """Audit-ready result of injected WebSocket ingestion for Shadow VPS."""

    stream_path: str = Field(..., min_length=1)
    snapshot_batch_path: str = Field(..., min_length=1)
    summary_path: str = Field(..., min_length=1)
    emitted_message_count: int = Field(default=0, ge=0)
    accepted_message_count: int = Field(default=0, ge=0)
    ignored_message_count: int = Field(default=0, ge=0)
    rejected_message_count: int = Field(default=0, ge=0)
    route_count: int = Field(default=0, ge=0)
    pair_scope: tuple[str, ...] = ()
    event_types: tuple[str, ...] = ()
    rejection_reasons: tuple[str, ...] = ()


class _InjectedWebSocketAdapter(WebSocketGatewayAdapter):
    """File-backed adapter that replays injected WebSocket frames deterministically."""

    def __init__(self, frames: tuple[InjectedWebSocketFrame, ...]) -> None:
        self._frames_by_endpoint: dict[str, list[InjectedWebSocketFrame]] = {}
        for frame in sorted(
            frames,
            key=lambda item: (item.endpoint, item.recv_time, item.sequence or 0, item.pair, item.stream_type),
        ):
            self._frames_by_endpoint.setdefault(frame.endpoint, []).append(frame)
        self._connected: set[str] = set()

    def connect(self, endpoint: str) -> None:
        self._connected.add(endpoint)

    def disconnect(self, endpoint: str) -> None:
        self._connected.discard(endpoint)

    def subscribe(self, endpoint: str, pair: str, stream_type: str) -> None:
        return None

    def recv(self, endpoint: str) -> AdapterMessage | None:
        if endpoint not in self._connected:
            return None
        queue = self._frames_by_endpoint.get(endpoint, [])
        if not queue:
            return None
        frame = queue.pop(0)
        return AdapterMessage(
            pair=frame.pair,
            stream_type=frame.stream_type,
            payload=dict(frame.payload),
            recv_time=frame.recv_time,
            source=frame.source,
            sequence=frame.sequence,
        )

def _resolve_side(value: str) -> Side:
    lowered = value.strip().lower()
    if lowered == Side.BUY.value:
        return Side.BUY
    if lowered == Side.SELL.value:
        return Side.SELL
    raise ValueError(f"Unsupported trade side: {value}")


def _resolve_timeframe(value: str) -> Timeframe:
    lowered = value.strip().lower()
    for timeframe in Timeframe:
        if timeframe.value == lowered:
            return timeframe
    raise ValueError(f"Unsupported kline interval/timeframe: {value}")


def _to_trade_event(event: NormalizedTradeEvent) -> TradeEvent:
    trade_id = event.trade_id.strip() or f"{event.pair}:{int(round(event.recv_time * 1000.0))}"
    return TradeEvent(
        timestamp_ms=int(round(event.recv_time * 1000.0)),
        pair=event.pair,
        price=event.price,
        quantity=event.quantity,
        side=_resolve_side(event.side or "buy"),
        trade_id=trade_id,
        is_maker=bool(event.data.get("is_maker", False)),
    )


def _build_levels(raw_levels: list[list[float]], *, side: str) -> list[DepthLevel]:
    levels = [
        DepthLevel(price=float(level[0]), quantity=float(level[1]))
        for level in raw_levels
        if len(level) >= 2 and float(level[0]) > 0.0 and float(level[1]) >= 0.0
    ]
    if not levels:
        raise ValueError(f"Depth payload requires at least one {side} level")
    return levels


def _to_depth_event(event: NormalizedDepthEvent) -> DepthEvent:
    return DepthEvent(
        timestamp_ms=int(round(event.recv_time * 1000.0)),
        pair=event.pair,
        bids=_build_levels(event.bids, side="bid"),
        asks=_build_levels(event.asks, side="ask"),
        last_update_id=(
            int(event.data["last_update_id"])
            if "last_update_id" in event.data and event.data["last_update_id"] is not None
            else None
        ),
    )


def _to_kline_event(event: NormalizedKlineEvent) -> KlineEvent:
    return KlineEvent(
        timestamp_ms=int(round(event.recv_time * 1000.0)),
        pair=event.pair,
        timeframe=_resolve_timeframe(event.interval or "1m"),
        open_price=event.open,
        high_price=event.high,
        low_price=event.low,
        close_price=event.close,
        volume=event.volume,
        close_time_ms=(
            int(event.data["close_time_ms"])
            if "close_time_ms" in event.data and event.data["close_time_ms"] is not None
            else None
        ),
        trade_count=(
            int(event.data["trade_count"])
            if "trade_count" in event.data and event.data["trade_count"] is not None
            else None
        ),
        is_closed=bool(event.data.get("is_closed", False)),
    )


def _read_float(payload: dict[str, object], key: str) -> float:
    value = payload.get(key)
    if isinstance(value, bool):
        return float(int(value))
    if isinstance(value, (int, float, str)):
        return float(value)
    raise ValueError(f"Snapshot payload field {key} is required")


def _read_optional_float(payload: dict[str, object], key: str) -> float | None:
    value = payload.get(key)
    if value in (None, ""):
        return None
    if isinstance(value, bool):
        return float(int(value))
    if isinstance(value, (int, float, str)):
        return float(value)
    raise ValueError(f"Snapshot payload field {key} must be numeric when present")


def _to_snapshot_event(event: NormalizedSnapshotEvent) -> SnapshotEvent:
    payload = dict(event.data)
    return SnapshotEvent(
        timestamp_ms=int(round(event.recv_time * 1000.0)),
        pair=event.pair,
        last_price=_read_float(payload, "last_price"),
        bid=_read_float(payload, "bid"),
        ask=_read_float(payload, "ask"),
        volume_24h=_read_float(payload, "volume_24h"),
        high_24h=_read_optional_float(payload, "high_24h"),
        low_24h=_read_optional_float(payload, "low_24h"),
        funding_rate=_read_optional_float(payload, "funding_rate"),
    )


def _to_market_event(
    mapped_event: NormalizedObservedEvent,
) -> tuple[str, MarketEvent] | None:
    if getattr(mapped_event, "event_type", None) == EventType.HEARTBEAT:
        return None
    if isinstance(mapped_event, NormalizedTradeEvent):
        return ("trade", _to_trade_event(mapped_event))
    if isinstance(mapped_event, NormalizedDepthEvent):
        return ("depth", _to_depth_event(mapped_event))
    if isinstance(mapped_event, NormalizedKlineEvent):
        return ("kline", _to_kline_event(mapped_event))
    if isinstance(mapped_event, NormalizedSnapshotEvent):
        return ("snapshot", _to_snapshot_event(mapped_event))
    raise ValueError(f"Unsupported normalized event type: {type(mapped_event).__name__}")


def _default_route_hint(
    route_hint_payload: dict[str, object],
    *,
    pair: str,
    index: int,
    timestamp_ms: int,
) -> ReplayRouteHint:
    payload = dict(route_hint_payload)
    payload.setdefault("route_id", f"shadow_ws:{pair}:{timestamp_ms}:{index}")
    payload.setdefault("engine_id", "engine_a")
    return ReplayRouteHint.model_validate(payload)


def build_snapshot_batch_from_observed_websocket_messages(
    messages: tuple[ObservedWebSocketMessage, ...],
    *,
    stream_path: str,
    snapshot_batch_path: Path,
    summary_path: Path,
    source: str = "shadow_vps_websocket",
) -> ShadowWebsocketSnapshotBuildResult:
    """Build a canonical snapshot batch from already observed websocket messages."""

    if not messages:
        raise ValueError("Observed websocket ingestion requires at least one message")

    envelopes: list[HistoricalMarketEventEnvelope] = []
    ignored_count = 0
    rejected_reasons: list[str] = []
    for index, message in enumerate(messages, start=1):
        validation = validate_raw_message(
            message.payload,
            message.pair,
            message.source,
            message.recv_time,
            message.stream_type,
        )
        if not validation.valid:
            rejected_reasons.extend(rejection.reason.value for rejection in validation.rejections)
            continue
        classification = classify_message(message.payload, stream_type_hint=message.stream_type)
        if classification.message_class == MessageClass.UNKNOWN:
            rejected_reasons.append("unknown_message_class")
            continue
        mapped = map_raw_to_event(
            message.payload,
            message.stream_type,
            message.pair,
            message.source,
            message.recv_time or 0.0,
        )
        if isinstance(mapped, MappingError):
            rejected_reasons.append(mapped.reason)
            continue
        converted = _to_market_event(mapped)
        if converted is None:
            ignored_count += 1
            continue
        event_type, market_event = converted
        envelopes.append(
            HistoricalMarketEventEnvelope(
                event_type=event_type,
                event=market_event,
                route_hint=_default_route_hint(
                    message.route_hint,
                    pair=message.pair,
                    index=index,
                    timestamp_ms=market_event.timestamp_ms,
                ),
            )
        )

    if not envelopes:
        raise ValueError("Injected websocket ingestion produced no replay-compatible events")

    snapshot_batch = HistoricalSnapshotBatch.from_records(
        source_path=stream_path,
        records=tuple(envelopes),
        source=source,
    )
    snapshot_batch_path.parent.mkdir(parents=True, exist_ok=True)
    records = [
        {
            "event_type": envelope.event_type,
            "event": envelope.event.model_dump(mode="json"),
            "route_hint": envelope.route_hint.model_dump(mode="json"),
        }
        for envelope in snapshot_batch.events
    ]
    atomic_write_json(snapshot_batch_path, records)

    result = ShadowWebsocketSnapshotBuildResult(
        stream_path=stream_path,
        snapshot_batch_path=str(snapshot_batch_path.resolve()),
        summary_path=str(summary_path.resolve()),
        emitted_message_count=len(messages),
        accepted_message_count=len(snapshot_batch.events),
        ignored_message_count=ignored_count,
        rejected_message_count=len(rejected_reasons),
        route_count=len(snapshot_batch.route_scope),
        pair_scope=snapshot_batch.pair_scope,
        event_types=snapshot_batch.event_types,
        rejection_reasons=tuple(rejected_reasons),
    )
    atomic_write_json(summary_path, result.model_dump(mode="json"))
    return result


def build_snapshot_batch_from_injected_websocket_stream(
    stream_path: Path,
    *,
    snapshot_batch_path: Path,
    summary_path: Path,
) -> ShadowWebsocketSnapshotBuildResult:
    """Replay injected websocket frames through Build-2 and emit a snapshot batch."""

    frames = load_injected_websocket_frames(stream_path)
    if not frames:
        raise ValueError("Injected websocket stream must contain at least one frame")

    adapter = _InjectedWebSocketAdapter(frames)
    runtime = WebSocketGatewayRuntime(adapter)
    for frame in {
        (item.endpoint, item.pair, item.stream_type): item for item in frames
    }.values():
        runtime.subscribe(frame.pair, frame.stream_type, frame.endpoint)
    for endpoint in sorted({frame.endpoint for frame in frames}):
        first_recv_time = min(
            frame.recv_time for frame in frames if frame.endpoint == endpoint
        )
        runtime.connect(endpoint, now=first_recv_time)

    observed_messages: list[ObservedWebSocketMessage] = []
    frame_by_message_key: dict[tuple[str, float, str, str, int | None], InjectedWebSocketFrame] = {}
    for frame in frames:
        frame_by_message_key[
            (frame.endpoint, frame.recv_time, frame.pair, frame.stream_type, frame.sequence)
        ] = frame

    for endpoint in sorted({frame.endpoint for frame in frames}):
        endpoint_frames = [frame for frame in frames if frame.endpoint == endpoint]
        for frame in endpoint_frames:
            result = runtime.poll_once(endpoint, now=frame.recv_time)
            if result.raw_message is None:
                continue
            key = (
                endpoint,
                result.raw_message.recv_time,
                result.raw_message.pair,
                result.raw_message.stream_type,
                result.raw_message.sequence,
            )
            original = frame_by_message_key.get(key)
            if original is None:
                raise ValueError("Unable to map emitted raw message back to injected frame")
            observed_messages.append(
                ObservedWebSocketMessage(
                    pair=result.raw_message.pair,
                    stream_type=result.raw_message.stream_type,
                    payload=dict(result.raw_message.payload),
                    recv_time=result.raw_message.recv_time,
                    source=result.raw_message.source,
                    sequence=result.raw_message.sequence,
                    route_hint=dict(original.route_hint),
                )
            )

    return build_snapshot_batch_from_observed_websocket_messages(
        tuple(observed_messages),
        stream_path=str(stream_path.resolve()),
        snapshot_batch_path=snapshot_batch_path,
        summary_path=summary_path,
        source="shadow_vps_injected_websocket",
    )


__all__ = [
    "InjectedWebSocketFrame",
    "ObservedWebSocketMessage",
    "ShadowWebsocketSnapshotBuildResult",
    "load_injected_websocket_frames",
    "build_snapshot_batch_from_observed_websocket_messages",
    "build_snapshot_batch_from_injected_websocket_stream",
]
