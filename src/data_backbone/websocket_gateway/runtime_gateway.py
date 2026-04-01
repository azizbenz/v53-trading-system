"""
Minimal injectable runtime path for Build-2 WebSocket gateway.
"""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, Field

from .connection_manager import ConnectionManager, ConnectionState, ConnectionStatus
from .heartbeat_monitor import HeartbeatMonitor, HeartbeatState
from .raw_message_emitter import RawMessage, RawMessageEmitter
from .reconnect_controller import ReconnectController, ReconnectEvent
from .subscription_manager import SubscriptionRegistry


class AdapterMessage(BaseModel, frozen=True):
    """Single message returned by an injected adapter."""

    pair: str
    stream_type: str
    payload: dict[str, object] = Field(default_factory=dict)
    recv_time: float | None = None
    source: str = ""
    sequence: int | None = None


class WebSocketGatewayAdapter(Protocol):
    """Sync adapter interface used by the Build-2 gateway runtime."""

    def connect(self, endpoint: str) -> None:
        ...

    def disconnect(self, endpoint: str) -> None:
        ...

    def subscribe(self, endpoint: str, pair: str, stream_type: str) -> None:
        ...

    def recv(self, endpoint: str) -> AdapterMessage | None:
        ...


class GatewayPollResult(BaseModel, frozen=True):
    """Observable result of a single polling cycle."""

    endpoint: str
    connection_status: ConnectionStatus
    heartbeat_state: HeartbeatState
    backlog: int
    utilization: float
    raw_message: RawMessage | None = None
    reconnect_event: ReconnectEvent | None = None
    error: str = ""


class WebSocketGatewayRuntime:
    """Injectable runtime orchestrating the Build-2 gateway components."""

    def __init__(
        self,
        adapter: WebSocketGatewayAdapter,
        *,
        connection_manager: ConnectionManager | None = None,
        subscriptions: SubscriptionRegistry | None = None,
        heartbeat_monitor: HeartbeatMonitor | None = None,
        reconnect_controller: ReconnectController | None = None,
        emitter: RawMessageEmitter | None = None,
    ) -> None:
        self._adapter = adapter
        self._connections = connection_manager or ConnectionManager()
        self._subscriptions = subscriptions or SubscriptionRegistry()
        self._heartbeat = heartbeat_monitor or HeartbeatMonitor()
        self._reconnect = reconnect_controller or ReconnectController()
        self._emitter = emitter or RawMessageEmitter()

    def register_endpoint(self, endpoint: str) -> None:
        self._connections.register_endpoint(endpoint)

    def subscribe(self, pair: str, stream_type: str, endpoint: str) -> None:
        self._connections.register_endpoint(endpoint)
        self._subscriptions.subscribe(pair, stream_type, endpoint)

    def connect(self, endpoint: str, now: float) -> ConnectionStatus:
        self._connections.register_endpoint(endpoint)
        self._connections.mark_connecting(endpoint)
        try:
            self._adapter.connect(endpoint)
            status = self._connections.mark_connected(endpoint, now)
            self._resubscribe(endpoint)
            return status
        except Exception as exc:
            return self._connections.mark_failed(endpoint, str(exc))

    def disconnect(self, endpoint: str, now: float, error: str = "") -> ConnectionStatus:
        try:
            self._adapter.disconnect(endpoint)
        except Exception:
            pass
        return self._connections.mark_disconnected(endpoint, now, error=error)

    def poll_once(self, endpoint: str, now: float) -> GatewayPollResult:
        self._connections.register_endpoint(endpoint)
        status = self._connections.get_status(endpoint)
        if status is None:
            status = self._connections.mark_failed(endpoint, "endpoint_not_registered")
        heartbeat_state = self._heartbeat.check_status(endpoint, now)

        if status.state != ConnectionState.CONNECTED:
            return GatewayPollResult(
                endpoint=endpoint,
                connection_status=status,
                heartbeat_state=heartbeat_state,
                backlog=self._emitter.backlog,
                utilization=self._emitter.utilization,
                error="endpoint_not_connected",
            )

        try:
            message = self._adapter.recv(endpoint)
        except Exception as exc:
            return self._recover(endpoint, now, str(exc))

        if message is None:
            return GatewayPollResult(
                endpoint=endpoint,
                connection_status=self._connections.get_status(endpoint) or status,
                heartbeat_state=self._heartbeat.check_status(endpoint, now),
                backlog=self._emitter.backlog,
                utilization=self._emitter.utilization,
            )

        recv_time = message.recv_time if message.recv_time is not None else now
        raw_message = RawMessage(
            pair=message.pair,
            stream_type=message.stream_type,
            payload=dict(message.payload),
            recv_time=recv_time,
            source=message.source,
            sequence=message.sequence,
        )
        self._emitter.emit(raw_message)
        self._heartbeat.record_heartbeat(endpoint, recv_time)

        return GatewayPollResult(
            endpoint=endpoint,
            connection_status=self._connections.get_status(endpoint) or status,
            heartbeat_state=self._heartbeat.check_status(endpoint, now),
            backlog=self._emitter.backlog,
            utilization=self._emitter.utilization,
            raw_message=raw_message,
        )

    @property
    def backlog(self) -> int:
        return self._emitter.backlog

    @property
    def high_water_mark(self) -> int:
        return self._emitter.high_water_mark

    def _recover(self, endpoint: str, now: float, error: str) -> GatewayPollResult:
        status = self.disconnect(endpoint, now, error=error)
        if not self._reconnect.should_retry(endpoint):
            failed = self._connections.mark_failed(endpoint, error)
            return GatewayPollResult(
                endpoint=endpoint,
                connection_status=failed,
                heartbeat_state=self._heartbeat.check_status(endpoint, now),
                backlog=self._emitter.backlog,
                utilization=self._emitter.utilization,
                error=error,
            )

        self._connections.mark_reconnecting(endpoint)
        reconnect_event = self._reconnect.record_attempt(
            endpoint,
            delay_s=self._reconnect.compute_delay(endpoint),
            reason=error,
            success=False,
            timestamp=now,
        )
        reconnect_error = ""
        try:
            self._adapter.connect(endpoint)
            self._resubscribe(endpoint)
            self._connections.mark_connected(endpoint, now)
            reconnect_event = self._reconnect.record_attempt(
                endpoint,
                delay_s=0.0,
                reason="reconnect_success",
                success=True,
                timestamp=now,
            )
        except Exception as exc:
            reconnect_error = str(exc)
            self._connections.mark_failed(endpoint, reconnect_error)

        return GatewayPollResult(
            endpoint=endpoint,
            connection_status=self._connections.get_status(endpoint) or status,
            heartbeat_state=self._heartbeat.check_status(endpoint, now),
            backlog=self._emitter.backlog,
            utilization=self._emitter.utilization,
            reconnect_event=reconnect_event,
            error=reconnect_error or error,
        )

    def _resubscribe(self, endpoint: str) -> None:
        for subscription in self._subscriptions.get_all_subscriptions():
            if subscription.endpoint != endpoint:
                continue
            self._adapter.subscribe(endpoint, subscription.pair, subscription.stream_type)
