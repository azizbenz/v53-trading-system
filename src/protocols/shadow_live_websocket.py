"""Native live websocket capture for the autonomous VPS Shadow service."""

from __future__ import annotations

import json
import time
from datetime import date
from pathlib import Path
from typing import Any, Callable, Protocol

from data_backbone.websocket_gateway.connection_manager import ConnectionState
from data_backbone.websocket_gateway.runtime_gateway import AdapterMessage, WebSocketGatewayAdapter, WebSocketGatewayRuntime
from protocols.shadow_vps_service import (
    ShadowLiveWebSocketCaptureResult,
    ShadowLiveWebSocketConfig,
)
from protocols.shadow_websocket_ingest import (
    ObservedWebSocketMessage,
    build_snapshot_batch_from_observed_websocket_messages,
)


class NativeWebSocketClient(Protocol):
    """Minimal client surface required by the native websocket adapter."""

    def settimeout(self, timeout: float) -> None:
        ...

    def send(self, payload: str) -> None:
        ...

    def recv(self) -> str | bytes | None:
        ...

    def close(self) -> None:
        ...


SocketFactory = Callable[[str, float, float], NativeWebSocketClient]


def _default_socket_factory(
    endpoint: str,
    connect_timeout_s: float,
    recv_timeout_s: float,
) -> NativeWebSocketClient:
    try:
        import websocket  # type: ignore[import-not-found]
    except ImportError as exc:
        raise RuntimeError(
            "Native live_websocket mode requires the 'websocket-client' package."
        ) from exc
    client = websocket.create_connection(endpoint, timeout=connect_timeout_s)
    client.settimeout(recv_timeout_s)
    return client


class BinanceSpotLiveWebSocketAdapter(WebSocketGatewayAdapter):
    """Minimal native Binance Spot websocket adapter for the Build-2 gateway runtime."""

    def __init__(
        self,
        config: ShadowLiveWebSocketConfig,
        *,
        socket_factory: SocketFactory | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._config = config
        self._socket_factory = socket_factory or _default_socket_factory
        self._clock = clock
        self._clients: dict[str, NativeWebSocketClient] = {}
        self._request_id = 0

    def connect(self, endpoint: str) -> None:
        client = self._socket_factory(
            endpoint,
            self._config.connect_timeout_s,
            self._config.recv_timeout_s,
        )
        self._clients[endpoint] = client

    def disconnect(self, endpoint: str) -> None:
        client = self._clients.pop(endpoint, None)
        if client is None:
            return
        try:
            client.close()
        except Exception:
            return

    def subscribe(self, endpoint: str, pair: str, stream_type: str) -> None:
        client = self._clients.get(endpoint)
        if client is None:
            return
        self._request_id += 1
        client.send(
            json.dumps(
                {
                    "method": "SUBSCRIBE",
                    "params": [self._subscription_param(pair, stream_type)],
                    "id": self._request_id,
                }
            )
        )

    def recv(self, endpoint: str) -> AdapterMessage | None:
        client = self._clients.get(endpoint)
        if client is None:
            return None
        try:
            raw_payload = client.recv()
        except Exception as exc:
            if exc.__class__.__name__ in {"WebSocketTimeoutException", "TimeoutError"}:
                return None
            raise
        if raw_payload in (None, "", b""):
            return None
        if isinstance(raw_payload, bytes):
            text_payload = raw_payload.decode("utf-8", errors="replace")
        else:
            text_payload = raw_payload
        payload = json.loads(text_payload)
        if not isinstance(payload, dict):
            return None
        if "result" in payload and "id" in payload:
            return None
        return self._parse_message(payload)

    def _subscription_param(self, pair: str, stream_type: str) -> str:
        symbol = pair.lower()
        lowered = stream_type.lower()
        if lowered == "trade":
            return f"{symbol}@trade"
        if lowered == "depth":
            return f"{symbol}@depth"
        if lowered == "ticker":
            return f"{symbol}@ticker"
        if lowered == "book_ticker":
            return f"{symbol}@bookTicker"
        if lowered == "kline":
            return f"{symbol}@kline_1m"
        if lowered.startswith("kline_"):
            return f"{symbol}@{lowered}"
        raise ValueError(f"Unsupported native live websocket stream_type: {stream_type}")

    def _parse_message(self, payload: dict[str, Any]) -> AdapterMessage | None:
        stream_name = str(payload.get("stream", ""))
        data = payload.get("data", payload)
        if not isinstance(data, dict):
            return None
        event_type = str(data.get("e", "")).strip()
        now = self._clock()

        if event_type == "trade" or stream_name.endswith("@trade"):
            pair = str(data.get("s", "")).upper()
            if not pair:
                raise ValueError("Live trade message is missing pair symbol")
            is_maker = bool(data.get("m", False))
            return AdapterMessage(
                pair=pair,
                stream_type="trade",
                payload={
                    "price": data.get("p", 0.0),
                    "quantity": data.get("q", 0.0),
                    "side": "sell" if is_maker else "buy",
                    "trade_id": str(data.get("t", "")),
                    "is_maker": is_maker,
                },
                recv_time=now,
                source="binance_live",
                sequence=int(data["t"]) if data.get("t") is not None else None,
            )

        if event_type == "depthUpdate" or stream_name.endswith("@depth"):
            pair = str(data.get("s", "")).upper()
            if not pair:
                raise ValueError("Live depth message is missing pair symbol")
            return AdapterMessage(
                pair=pair,
                stream_type="depth",
                payload={
                    "bids": data.get("b", []),
                    "asks": data.get("a", []),
                    "last_update_id": data.get("u"),
                },
                recv_time=now,
                source="binance_live",
                sequence=int(data["u"]) if data.get("u") is not None else None,
            )

        if event_type == "kline" or "@kline_" in stream_name:
            kline = data.get("k", data)
            if not isinstance(kline, dict):
                raise ValueError("Live kline message is missing nested kline payload")
            pair = str(data.get("s", kline.get("s", ""))).upper()
            if not pair:
                raise ValueError("Live kline message is missing pair symbol")
            return AdapterMessage(
                pair=pair,
                stream_type="kline",
                payload={
                    "interval": kline.get("i", "1m"),
                    "open": kline.get("o", 0.0),
                    "high": kline.get("h", 0.0),
                    "low": kline.get("l", 0.0),
                    "close": kline.get("c", 0.0),
                    "volume": kline.get("v", 0.0),
                    "close_time_ms": kline.get("T"),
                    "trade_count": kline.get("n"),
                    "is_closed": bool(kline.get("x", False)),
                },
                recv_time=now,
                source="binance_live",
                sequence=int(kline["T"]) if kline.get("T") is not None else None,
            )

        if event_type == "24hrTicker" or stream_name.endswith("@ticker"):
            pair = str(data.get("s", "")).upper()
            if not pair:
                raise ValueError("Live ticker message is missing pair symbol")
            return AdapterMessage(
                pair=pair,
                stream_type="snapshot",
                payload={
                    "snapshot_type": "ticker",
                    "last_price": data.get("c", 0.0),
                    "bid": data.get("b", 0.0),
                    "ask": data.get("a", 0.0),
                    "volume_24h": data.get("v", 0.0),
                    "high_24h": data.get("h"),
                    "low_24h": data.get("l"),
                },
                recv_time=now,
                source="binance_live",
            )

        if event_type == "bookTicker" or stream_name.endswith("@bookTicker"):
            pair = str(data.get("s", "")).upper()
            if not pair:
                raise ValueError("Live bookTicker message is missing pair symbol")
            bid = float(data.get("b", 0.0))
            ask = float(data.get("a", 0.0))
            last_price = round((bid + ask) / 2.0, 8) if bid > 0.0 and ask > 0.0 else 0.0
            return AdapterMessage(
                pair=pair,
                stream_type="snapshot",
                payload={
                    "snapshot_type": "book_ticker",
                    "last_price": last_price,
                    "bid": bid,
                    "ask": ask,
                    "volume_24h": 0.0,
                },
                recv_time=now,
                source="binance_live",
                sequence=int(data["u"]) if data.get("u") is not None else None,
            )

        return None


def _session_date(config: ShadowLiveWebSocketConfig) -> str:
    if config.session_date_override:
        return config.session_date_override
    return date.today().isoformat()


def _route_hint_payload(
    config: ShadowLiveWebSocketConfig,
    *,
    pair: str,
    index: int,
    timestamp_ms: int,
) -> dict[str, object]:
    pair_key = pair.upper()
    payload = dict(config.route_hints_by_pair.get(pair_key, {}))
    payload.setdefault("route_id", f"live_ws:{pair_key}:{timestamp_ms}:{index}")
    payload.setdefault("engine_id", "engine_a")
    return payload


def capture_live_websocket_snapshot_batch(
    config: ShadowLiveWebSocketConfig,
    *,
    output_dir: Path,
    adapter_factory: Callable[[ShadowLiveWebSocketConfig], WebSocketGatewayAdapter] | None = None,
    clock: Callable[[], float] = time.time,
) -> ShadowLiveWebSocketCaptureResult:
    """Capture a bounded native live websocket window and materialize a snapshot batch."""

    session_date = _session_date(config)
    output_dir.mkdir(parents=True, exist_ok=True)
    snapshot_batch_path = output_dir / "live_websocket_snapshot_batch.json"
    summary_path = output_dir / "live_websocket_capture_summary.json"
    endpoint = config.endpoint
    adapter = (
        adapter_factory(config)
        if adapter_factory is not None
        else BinanceSpotLiveWebSocketAdapter(config, clock=clock)
    )
    runtime = WebSocketGatewayRuntime(adapter)
    for pair in config.pairs:
        for stream_type in config.stream_types:
            runtime.subscribe(pair, stream_type, endpoint)
    status = runtime.connect(endpoint, now=clock())
    if status.state != ConnectionState.CONNECTED:
        raise RuntimeError("Native live_websocket adapter failed to connect")

    observed_messages: list[ObservedWebSocketMessage] = []
    idle_polls = 0
    started_at = clock()
    try:
        while (
            len(observed_messages) < config.capture_frame_limit
            and idle_polls < config.idle_poll_limit
            and (clock() - started_at) <= config.capture_timeout_s
        ):
            now = clock()
            result = runtime.poll_once(endpoint, now=now)
            if result.raw_message is None:
                idle_polls += 1
                continue
            idle_polls = 0
            timestamp_ms = int(round(result.raw_message.recv_time * 1000.0))
            observed_messages.append(
                ObservedWebSocketMessage(
                    pair=result.raw_message.pair,
                    stream_type=result.raw_message.stream_type,
                    payload=dict(result.raw_message.payload),
                    recv_time=result.raw_message.recv_time,
                    source=result.raw_message.source or "binance_live",
                    sequence=result.raw_message.sequence,
                    route_hint=_route_hint_payload(
                        config,
                        pair=result.raw_message.pair,
                        index=len(observed_messages) + 1,
                        timestamp_ms=timestamp_ms,
                    ),
                )
            )
    finally:
        runtime.disconnect(endpoint, now=clock(), error="capture_complete")

    build_result = build_snapshot_batch_from_observed_websocket_messages(
        tuple(observed_messages),
        stream_path=config.endpoint,
        snapshot_batch_path=snapshot_batch_path,
        summary_path=summary_path,
        source="shadow_vps_live_websocket",
    )
    return ShadowLiveWebSocketCaptureResult(
        session_date=session_date,
        live_capture_dir_ref=str(output_dir.resolve()),
        snapshot_batch_path_ref=str(snapshot_batch_path.resolve()),
        summary_path_ref=str(summary_path.resolve()),
        emitted_message_count=build_result.emitted_message_count,
        accepted_message_count=build_result.accepted_message_count,
        ignored_message_count=build_result.ignored_message_count,
        rejected_message_count=build_result.rejected_message_count,
        pair_scope=build_result.pair_scope,
        event_types=build_result.event_types,
    )


__all__ = [
    "NativeWebSocketClient",
    "SocketFactory",
    "BinanceSpotLiveWebSocketAdapter",
    "capture_live_websocket_snapshot_batch",
]
