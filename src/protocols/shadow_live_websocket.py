"""Native live websocket capture for the autonomous VPS Shadow service."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import os
import time
from datetime import date
from pathlib import Path
from typing import Any, Awaitable, Callable, Protocol

from data_backbone.websocket_gateway.connection_manager import ConnectionState
from data_backbone.websocket_gateway.runtime_gateway import AdapterMessage, WebSocketGatewayAdapter, WebSocketGatewayRuntime
from interface_contracts.binance_contracts import BinanceServerTime
from protocols.shadow_vps_service import (
    ShadowLiveUserDataCaptureSummary,
    ShadowLiveWebSocketCaptureResult,
    ShadowLiveWebSocketConfig,
)
from protocols.shadow_websocket_ingest import (
    ObservedWebSocketMessage,
    build_snapshot_batch_from_observed_websocket_messages,
)
from interface_contracts.atomic_io import atomic_write_json, atomic_write_text
from venue_adapters.binance_spot.rest_client import BinanceRestClient


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
ServerTimeReader = Callable[[], Awaitable[BinanceServerTime]]


def _is_timeout_exception(exc: BaseException) -> bool:
    """BS-2C: isinstance check replaces fragile __class__.__name__ string match.

    websocket-client is optional; guard the import so this helper works in all
    test environments where the library may not be installed.
    """
    if isinstance(exc, TimeoutError):
        return True
    try:
        import websocket as _ws  # type: ignore[import-not-found]
        return isinstance(exc, _ws.WebSocketTimeoutException)
    except ImportError:
        return False


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
        self._pending_subscriptions: dict[str, list[str]] = {}
        self._request_id = 0

    def connect(self, endpoint: str) -> None:
        stale_client = self._clients.get(endpoint)
        if stale_client is not None:
            try:
                stale_client.close()
            except Exception:
                pass
        client = self._socket_factory(
            endpoint,
            self._config.connect_timeout_s,
            self._config.recv_timeout_s,
        )
        self._clients[endpoint] = client
        self._pending_subscriptions[endpoint] = []

    def disconnect(self, endpoint: str) -> None:
        client = self._clients.pop(endpoint, None)
        self._pending_subscriptions.pop(endpoint, None)
        if client is None:
            return
        try:
            client.close()
        except Exception:
            return

    def subscribe(self, endpoint: str, pair: str, stream_type: str) -> None:
        if endpoint not in self._clients:
            return
        pending = self._pending_subscriptions.setdefault(endpoint, [])
        subscription = self._subscription_param(pair, stream_type)
        if subscription not in pending:
            pending.append(subscription)

    def recv(self, endpoint: str) -> AdapterMessage | None:
        client = self._clients.get(endpoint)
        if client is None:
            return None
        self._flush_pending_subscriptions(endpoint)
        try:
            raw_payload = client.recv()
        except Exception as exc:
            if _is_timeout_exception(exc):
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

    def _flush_pending_subscriptions(self, endpoint: str) -> None:
        client = self._clients.get(endpoint)
        pending = self._pending_subscriptions.get(endpoint, [])
        if client is None or not pending:
            return
        self._request_id += 1
        client.send(
            json.dumps(
                {
                    "method": "SUBSCRIBE",
                    "params": pending,
                    "id": self._request_id,
                }
            )
        )
        self._pending_subscriptions[endpoint] = []

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
                    "first_update_id": data.get("U"),
                    "final_update_id": data.get("u"),
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


def _binance_signed_params_payload(params: dict[str, object]) -> str:
    sorted_items = sorted(
        (key, value)
        for key, value in params.items()
        if value is not None and key != "signature"
    )
    return "&".join(f"{key}={value}" for key, value in sorted_items)


def _resolve_required_env(env_var_name: str) -> str:
    value = os.getenv(env_var_name, "").strip()
    if value:
        return value
    raise RuntimeError(
        f"Missing required environment variable for Binance user data stream: {env_var_name}"
    )


def _detect_user_data_event_type(payload: dict[str, Any]) -> str:
    event_payload = payload.get("event")
    if isinstance(event_payload, dict):
        event_type = str(event_payload.get("e", "")).strip()
        if event_type:
            return event_type
    event_type = str(payload.get("e", "")).strip()
    if event_type:
        return event_type
    status = payload.get("status")
    if status is not None:
        return "control_response"
    return "unknown"


def capture_live_user_data_stream(
    config: ShadowLiveWebSocketConfig,
    *,
    output_dir: Path,
    socket_factory: SocketFactory | None = None,
    clock: Callable[[], float] = time.time,
) -> ShadowLiveUserDataCaptureSummary:
    """Capture a bounded authenticated Binance user-data websocket sidecar."""

    api_key = _resolve_required_env(config.user_data_api_key_env_var)
    api_secret = _resolve_required_env(config.user_data_api_secret_env_var)
    client = (socket_factory or _default_socket_factory)(
        config.user_data_endpoint,
        config.connect_timeout_s,
        config.recv_timeout_s,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    session_date = _session_date(config)
    summary_path = output_dir / "live_user_data_capture_summary.json"
    events_path = output_dir / "live_user_data_events.jsonl"
    request_id = "shadow-user-data-subscribe"
    timestamp_ms = int(round(clock() * 1000.0))
    subscribe_params: dict[str, object] = {
        "apiKey": api_key,
        "recvWindow": config.user_data_recv_window_ms,
        "timestamp": timestamp_ms,
    }
    signature_payload = _binance_signed_params_payload(subscribe_params)
    subscribe_params["signature"] = hmac.new(
        api_secret.encode("utf-8"),
        signature_payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    subscribe_request = {
        "id": request_id,
        "method": "userDataStream.subscribe.signature",
        "params": subscribe_params,
    }
    client.send(json.dumps(subscribe_request))

    subscription_id: int | None = None
    observed_events: list[dict[str, Any]] = []
    event_types: set[str] = set()
    idle_polls = 0
    started_at = clock()
    try:
        while (
            idle_polls < config.user_data_idle_poll_limit
            and (clock() - started_at) <= config.user_data_capture_timeout_s
            and len(observed_events) < config.user_data_event_limit
        ):
            try:
                raw_payload = client.recv()
            except Exception as exc:
                if _is_timeout_exception(exc):
                    idle_polls += 1
                    continue
                raise
            if raw_payload in (None, "", b""):
                idle_polls += 1
                continue
            idle_polls = 0
            text_payload = (
                raw_payload.decode("utf-8", errors="replace")
                if isinstance(raw_payload, bytes)
                else raw_payload
            )
            payload = json.loads(text_payload)
            if not isinstance(payload, dict):
                continue
            if payload.get("id") == request_id:
                status = int(payload.get("status", 0))
                if status != 200:
                    error_payload = payload.get("error", {})
                    if isinstance(error_payload, dict):
                        message = str(error_payload.get("msg", "user-data subscription failed"))
                    else:
                        message = "user-data subscription failed"
                    raise RuntimeError(message)
                result = payload.get("result", {})
                if isinstance(result, dict) and result.get("subscriptionId") is not None:
                    subscription_id = int(result["subscriptionId"])
                continue
            event_type = _detect_user_data_event_type(payload)
            event_types.add(event_type)
            observed_events.append(payload)
    finally:
        try:
            client.close()
        except Exception:
            pass

    if subscription_id is None:
        raise RuntimeError("Binance user data stream subscription did not succeed")

    atomic_write_text(
        events_path,
        "\n".join(json.dumps(item, ensure_ascii=True) for item in observed_events),
        encoding="utf-8",
    )
    summary = ShadowLiveUserDataCaptureSummary(
        session_date=session_date,
        endpoint=config.user_data_endpoint,
        summary_path_ref=str(summary_path.resolve()),
        events_path_ref=str(events_path.resolve()),
        authenticated=True,
        subscription_id=subscription_id,
        emitted_event_count=len(observed_events),
        event_types=tuple(sorted(event_types)),
    )
    atomic_write_json(summary_path, summary.model_dump(mode="json"))
    return summary


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


async def _collect_time_sync_offsets_ms(
    config: ShadowLiveWebSocketConfig,
    *,
    clock_ms: Callable[[], int],
    server_time_reader: ServerTimeReader | None = None,
) -> tuple[float, ...]:
    async def _sample(reader: ServerTimeReader) -> tuple[float, ...]:
        offsets_ms: list[float] = []
        for index in range(config.time_sync_sample_count):
            server_time = await reader()
            offsets_ms.append(float(clock_ms() - server_time.server_time_ms))
            if (
                config.time_sync_sample_pause_s > 0.0
                and index + 1 < config.time_sync_sample_count
            ):
                await asyncio.sleep(config.time_sync_sample_pause_s)
        return tuple(offsets_ms)

    if server_time_reader is not None:
        return await _sample(server_time_reader)
    async with BinanceRestClient(
        base_url=config.time_sync_rest_base_url,
        timeout_s=config.time_sync_rest_timeout_s,
    ) as client:
        return await _sample(client.get_server_time)


def _write_time_sync_offsets_sidecar(
    config: ShadowLiveWebSocketConfig,
    *,
    output_dir: Path,
    session_date: str,
    clock_ms: Callable[[], int],
    server_time_reader: ServerTimeReader | None = None,
) -> tuple[str, int, str]:
    if not config.time_sync_probe_enabled:
        return "", 0, ""
    started_at = time.perf_counter()
    try:
        offsets_ms = asyncio.run(
            _collect_time_sync_offsets_ms(
                config,
                clock_ms=clock_ms,
                server_time_reader=server_time_reader,
            )
        )
    except Exception as exc:
        return "", 0, f"{type(exc).__name__}: {exc}"
    if not offsets_ms:
        return "", 0, "TIME_SYNC_PROBE_EMPTY"
    probe_duration_s = max(0.0, time.perf_counter() - started_at)
    observed_calls_per_minute = (
        (len(offsets_ms) / probe_duration_s) * 60.0 if probe_duration_s > 0.0 else None
    )
    path = output_dir / "live_time_sync_offsets.json"
    atomic_write_json(
        path,
        {
            "session_date": session_date,
            "time_sync_offsets_ms": list(offsets_ms),
            "sample_count": len(offsets_ms),
            "source": "shadow_vps_live_time_sync_probe",
            "rest_base_url": config.time_sync_rest_base_url,
            "rest_call_count": len(offsets_ms),
            "probe_duration_s": probe_duration_s,
            "rest_quota_window_s": 60.0,
            "rest_quota_max_calls_per_minute": config.time_sync_rest_quota_max_calls_per_minute,
            "observed_calls_per_minute": observed_calls_per_minute,
        },
    )
    return str(path.resolve()), len(offsets_ms), ""


def capture_live_websocket_snapshot_batch(
    config: ShadowLiveWebSocketConfig,
    *,
    output_dir: Path,
    adapter_factory: Callable[[ShadowLiveWebSocketConfig], WebSocketGatewayAdapter] | None = None,
    user_data_socket_factory: SocketFactory | None = None,
    time_sync_server_time_reader: ServerTimeReader | None = None,
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
        if status.error_message:
            raise RuntimeError(
                f"Native live_websocket adapter failed to connect to {endpoint}: "
                f"{status.error_message}"
            )
        raise RuntimeError(
            f"Native live_websocket adapter failed to connect to {endpoint} "
            f"(state={status.state.value})"
        )

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
    time_sync_offsets_path_ref, time_sync_sample_count, time_sync_probe_error = (
        _write_time_sync_offsets_sidecar(
            config,
            output_dir=output_dir,
            session_date=session_date,
            clock_ms=lambda: int(round(clock() * 1000.0)),
            server_time_reader=time_sync_server_time_reader,
        )
    )
    user_data_summary: ShadowLiveUserDataCaptureSummary | None = None
    if config.user_data_stream_enabled:
        user_data_summary = capture_live_user_data_stream(
            config,
            output_dir=output_dir,
            socket_factory=user_data_socket_factory,
            clock=clock,
        )
    result = ShadowLiveWebSocketCaptureResult(
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
        time_sync_offsets_path_ref=time_sync_offsets_path_ref,
        time_sync_sample_count=time_sync_sample_count,
        time_sync_probe_error=time_sync_probe_error,
        user_data_summary_path_ref=(
            user_data_summary.summary_path_ref if user_data_summary is not None else ""
        ),
        user_data_events_path_ref=(
            user_data_summary.events_path_ref if user_data_summary is not None else ""
        ),
        user_data_authenticated=(
            user_data_summary.authenticated if user_data_summary is not None else False
        ),
        user_data_subscription_id=(
            user_data_summary.subscription_id if user_data_summary is not None else None
        ),
        user_data_event_count=(
            user_data_summary.emitted_event_count if user_data_summary is not None else 0
        ),
        user_data_event_types=(
            user_data_summary.event_types if user_data_summary is not None else ()
        ),
    )
    atomic_write_json(summary_path, result.model_dump(mode="json"))
    return result


__all__ = [
    "NativeWebSocketClient",
    "SocketFactory",
    "BinanceSpotLiveWebSocketAdapter",
    "capture_live_user_data_stream",
    "capture_live_websocket_snapshot_batch",
]
