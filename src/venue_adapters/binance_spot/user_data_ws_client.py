"""Bounded authenticated Binance user-data websocket source for execution runtime."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from collections.abc import Callable
from typing import Protocol

from interface_contracts.binance_contracts import BinanceCredentials
from pydantic import BaseModel, Field
from venue_adapters.binance_spot.user_data_events import BinanceUserDataEventSource


class NativeWebSocketClient(Protocol):
    """Minimal websocket client surface required by the bounded user-data source."""

    def settimeout(self, timeout: float) -> None:
        ...

    def send(self, payload: str) -> None:
        ...

    def recv(self) -> str | bytes | None:
        ...

    def close(self) -> None:
        ...


UserDataSocketFactory = Callable[[str, float, float], NativeWebSocketClient]


class BinanceUserDataWebSocketConfig(BaseModel, frozen=True):
    """Bounded config for the authenticated Binance user-data websocket."""

    endpoint: str = Field(default="wss://ws-api.binance.com:443/ws-api/v3", min_length=1)
    connect_timeout_s: float = Field(default=5.0, gt=0.0)
    recv_timeout_s: float = Field(default=0.2, gt=0.0)
    recv_window_ms: int = Field(default=5000, ge=0)
    max_messages_per_poll: int = Field(default=32, ge=1)


def _is_timeout_exception(exc: BaseException) -> bool:
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
            "Authenticated Binance user-data websocket requires the 'websocket-client' package."
        ) from exc
    client = websocket.create_connection(endpoint, timeout=connect_timeout_s)
    client.settimeout(recv_timeout_s)
    return client


def build_user_data_subscribe_request(
    credentials: BinanceCredentials,
    *,
    recv_window_ms: int,
    timestamp_ms: int,
    request_id: str = "v53-user-data-subscribe",
) -> dict[str, object]:
    params: dict[str, object] = {
        "apiKey": credentials.api_key.get_secret_value(),
        "recvWindow": recv_window_ms,
        "timestamp": timestamp_ms,
    }
    signature_payload = "&".join(f"{key}={params[key]}" for key in sorted(params))
    params["signature"] = hmac.new(
        credentials.secret_key.get_secret_value().encode("utf-8"),
        signature_payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return {
        "id": request_id,
        "method": "userDataStream.subscribe.signature",
        "params": params,
    }


class BinanceUserDataWebSocketEventSource(BinanceUserDataEventSource):
    """Bounded read-only authenticated Binance user-data websocket source."""

    def __init__(
        self,
        *,
        credentials: BinanceCredentials,
        config: BinanceUserDataWebSocketConfig,
        socket_factory: UserDataSocketFactory | None = None,
        clock_ms: Callable[[], int] | None = None,
        request_id: str = "v53-user-data-subscribe",
    ) -> None:
        self._credentials = credentials
        self._config = config
        self._socket_factory = socket_factory or _default_socket_factory
        self._clock_ms = clock_ms or (lambda: time.time_ns() // 1_000_000)
        self._request_id = request_id
        self._client: NativeWebSocketClient | None = None
        self._subscription_id: int | None = None

    @property
    def authenticated(self) -> bool:
        return self._subscription_id is not None

    @property
    def subscription_id(self) -> int | None:
        return self._subscription_id

    def connect(self) -> None:
        if self._client is not None:
            return
        client = self._socket_factory(
            self._config.endpoint,
            self._config.connect_timeout_s,
            self._config.recv_timeout_s,
        )
        subscribe_request = build_user_data_subscribe_request(
            self._credentials,
            recv_window_ms=self._config.recv_window_ms,
            timestamp_ms=self._clock_ms(),
            request_id=self._request_id,
        )
        client.send(json.dumps(subscribe_request))
        self._client = client

    def close(self) -> None:
        client = self._client
        self._client = None
        self._subscription_id = None
        if client is None:
            return
        try:
            client.close()
        except Exception:
            return

    def poll_events(self) -> tuple[dict[str, object], ...]:
        if self._client is None:
            self.connect()
        collected: list[dict[str, object]] = []
        for _ in range(self._config.max_messages_per_poll):
            payload = self._recv_one()
            if payload is None:
                break
            if self._consume_control_message(payload):
                continue
            collected.append(payload)
        return tuple(collected)

    def _recv_one(self) -> dict[str, object] | None:
        if self._client is None:
            return None
        try:
            raw_payload = self._client.recv()
        except Exception as exc:
            if _is_timeout_exception(exc):
                return None
            raise
        if raw_payload in (None, "", b""):
            return None
        text_payload = (
            raw_payload.decode("utf-8", errors="replace")
            if isinstance(raw_payload, bytes)
            else raw_payload
        )
        payload = json.loads(text_payload)
        if not isinstance(payload, dict):
            return None
        return payload

    def _consume_control_message(self, payload: dict[str, object]) -> bool:
        if payload.get("id") != self._request_id:
            return False
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
            self._subscription_id = int(result["subscriptionId"])
        return True


__all__ = [
    "BinanceUserDataWebSocketConfig",
    "BinanceUserDataWebSocketEventSource",
    "NativeWebSocketClient",
    "UserDataSocketFactory",
    "build_user_data_subscribe_request",
]
