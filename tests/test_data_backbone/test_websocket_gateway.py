"""Tests for data_backbone.websocket_gateway — Build-2."""
import pytest

from data_backbone.websocket_gateway.connection_manager import (
    ConnectionManager,
    ConnectionState,
)
from data_backbone.websocket_gateway.subscription_manager import (
    Subscription,
    SubscriptionRegistry,
)
from data_backbone.websocket_gateway.heartbeat_monitor import (
    HeartbeatMonitor,
    HeartbeatStatus,
)
from data_backbone.websocket_gateway.reconnect_controller import (
    ReconnectController,
    ReconnectEvent,
)
from data_backbone.websocket_gateway.raw_message_emitter import (
    RawMessage,
    RawMessageEmitter,
)
from data_backbone.websocket_gateway.runtime_gateway import (
    AdapterMessage,
    WebSocketGatewayRuntime,
)


pytestmark = pytest.mark.build2

EP = "wss://stream.binance.com"


# --- ConnectionManager ---

class TestConnectionManager:
    def test_initial_state_disconnected(self):
        cm = ConnectionManager()
        cm.register_endpoint(EP)
        status = cm.get_status(EP)
        assert status.state == ConnectionState.DISCONNECTED

    def test_connect_transitions(self):
        cm = ConnectionManager()
        cm.register_endpoint(EP)
        cm.mark_connecting(EP)
        assert cm.get_status(EP).state == ConnectionState.CONNECTING
        cm.mark_connected(EP, 100.0)
        assert cm.get_status(EP).state == ConnectionState.CONNECTED

    def test_disconnect(self):
        cm = ConnectionManager()
        cm.register_endpoint(EP)
        cm.mark_connecting(EP)
        cm.mark_connected(EP, 100.0)
        cm.mark_disconnected(EP, 105.0)
        assert cm.get_status(EP).state == ConnectionState.DISCONNECTED

    def test_reconnecting_state(self):
        cm = ConnectionManager()
        cm.register_endpoint(EP)
        cm.mark_connecting(EP)
        cm.mark_connected(EP, 100.0)
        cm.mark_reconnecting(EP)
        assert cm.get_status(EP).state == ConnectionState.RECONNECTING

    def test_failed_state(self):
        cm = ConnectionManager()
        cm.register_endpoint(EP)
        cm.mark_failed(EP, "timeout")
        assert cm.get_status(EP).state == ConnectionState.FAILED

    def test_connect_count_increments(self):
        cm = ConnectionManager()
        cm.register_endpoint(EP)
        cm.mark_connecting(EP)
        cm.mark_connected(EP, 100.0)
        cm.mark_disconnected(EP, 105.0)
        cm.mark_connecting(EP)
        cm.mark_connected(EP, 110.0)
        assert cm.get_status(EP).connect_count == 2


# --- SubscriptionRegistry ---

class TestSubscriptionRegistry:
    def test_subscribe(self):
        reg = SubscriptionRegistry()
        sub = reg.subscribe("BTCUSDT", "trade", "wss://test")
        assert sub.pair == "BTCUSDT"
        assert reg.count == 1

    def test_no_duplicate(self):
        reg = SubscriptionRegistry()
        reg.subscribe("BTCUSDT", "trade", "wss://test")
        with pytest.raises(ValueError, match="Duplicate"):
            reg.subscribe("BTCUSDT", "trade", "wss://test")

    def test_unsubscribe(self):
        reg = SubscriptionRegistry()
        reg.subscribe("BTCUSDT", "trade", "wss://test")
        assert reg.unsubscribe("BTCUSDT", "trade") is True
        assert reg.count == 0

    def test_get_by_pair(self):
        reg = SubscriptionRegistry()
        reg.subscribe("BTCUSDT", "trade", "wss://a")
        reg.subscribe("BTCUSDT", "depth", "wss://b")
        reg.subscribe("ETHUSDT", "trade", "wss://c")
        assert len(reg.get_subscriptions_for_pair("BTCUSDT")) == 2

    def test_is_subscribed(self):
        reg = SubscriptionRegistry()
        reg.subscribe("BTCUSDT", "trade", "wss://a")
        assert reg.is_subscribed("BTCUSDT", "trade") is True
        assert reg.is_subscribed("BTCUSDT", "depth") is False


# --- HeartbeatMonitor ---

class TestHeartbeatMonitor:
    def test_alive(self):
        hm = HeartbeatMonitor(heartbeat_interval_s=5.0, late_threshold_s=10.0)
        hm.record_heartbeat("ep1", 100.0)
        state = hm.check_status("ep1", 102.0)
        assert state.status == HeartbeatStatus.ALIVE

    def test_late(self):
        hm = HeartbeatMonitor(heartbeat_interval_s=5.0, late_threshold_s=10.0)
        hm.record_heartbeat("ep1", 100.0)
        state = hm.check_status("ep1", 108.0)
        assert state.status == HeartbeatStatus.LATE

    def test_silent(self):
        hm = HeartbeatMonitor(heartbeat_interval_s=5.0, late_threshold_s=10.0)
        hm.record_heartbeat("ep1", 100.0)
        state = hm.check_status("ep1", 115.0)
        assert state.status == HeartbeatStatus.SILENT

    def test_no_heartbeat_is_silent(self):
        hm = HeartbeatMonitor()
        state = hm.check_status("ep1", 100.0)
        assert state.status == HeartbeatStatus.SILENT

    def test_heartbeat_resets_misses(self):
        hm = HeartbeatMonitor(heartbeat_interval_s=5.0, late_threshold_s=10.0)
        hm.record_heartbeat("ep1", 100.0)
        hm.check_status("ep1", 115.0)  # silent
        hm.record_heartbeat("ep1", 120.0)
        state = hm.check_status("ep1", 122.0)
        assert state.status == HeartbeatStatus.ALIVE


# --- ReconnectController ---

class TestReconnectController:
    def test_compute_delay_exponential(self):
        rc = ReconnectController(base_delay_s=1.0, max_delay_s=60.0)
        assert rc.compute_delay("ep1") == 1.0  # 2^0
        rc.record_attempt("ep1", 1.0, "test", False, 100.0)
        assert rc.compute_delay("ep1") == 2.0  # 2^1
        rc.record_attempt("ep1", 2.0, "test", False, 102.0)
        assert rc.compute_delay("ep1") == 4.0  # 2^2

    def test_max_delay_cap(self):
        rc = ReconnectController(base_delay_s=1.0, max_delay_s=10.0)
        for _ in range(10):
            rc.record_attempt("ep1", 1.0, "test", False, 100.0)
        assert rc.compute_delay("ep1") <= 10.0

    def test_success_resets(self):
        rc = ReconnectController()
        rc.record_attempt("ep1", 1.0, "test", False, 100.0)
        rc.record_attempt("ep1", 2.0, "test", True, 102.0)
        assert rc.get_attempt_count("ep1") == 0

    def test_should_retry_respects_max(self):
        rc = ReconnectController(max_attempts=2)
        rc.record_attempt("ep1", 1.0, "test", False, 100.0)
        rc.record_attempt("ep1", 2.0, "test", False, 102.0)
        assert rc.should_retry("ep1") is False

    def test_history(self):
        rc = ReconnectController()
        rc.record_attempt("ep1", 1.0, "test", False, 100.0)
        rc.record_attempt("ep2", 1.0, "test", True, 101.0)
        assert len(rc.get_history()) == 2
        assert len(rc.get_history("ep1")) == 1


# --- RawMessageEmitter ---

class TestRawMessageEmitter:
    def _msg(self, pair="BTCUSDT", recv_time=100.0):
        return RawMessage(
            pair=pair, stream_type="trade", payload={"price": "100"}, recv_time=recv_time,
        )

    def test_emit_and_consume(self):
        emitter = RawMessageEmitter()
        assert emitter.emit(self._msg()) is True
        msgs = emitter.consume()
        assert len(msgs) == 1
        assert emitter.backlog == 0

    def test_buffer_full_drops(self):
        emitter = RawMessageEmitter(max_buffer_size=2)
        emitter.emit(self._msg(recv_time=1.0))
        emitter.emit(self._msg(recv_time=2.0))
        assert emitter.emit(self._msg(recv_time=3.0)) is True
        assert emitter.total_dropped == 1
        assert emitter.high_water_mark == 2
        assert emitter.consume() == (
            self._msg(recv_time=2.0),
            self._msg(recv_time=3.0),
        )

    def test_consume_partial(self):
        emitter = RawMessageEmitter()
        for i in range(5):
            emitter.emit(self._msg(recv_time=float(i + 1)))
        msgs = emitter.consume(max_count=3)
        assert len(msgs) == 3
        assert emitter.backlog == 2

    def test_recv_time_required(self):
        with pytest.raises(ValueError, match="recv_time"):
            RawMessageEmitter().emit(
                RawMessage(pair="BTC", stream_type="trade", payload={}, recv_time=0.0)
            )

    def test_utilization(self):
        emitter = RawMessageEmitter(max_buffer_size=10)
        for i in range(5):
            emitter.emit(self._msg(recv_time=float(i + 1)))
        assert emitter.utilization == 0.5


class _FakeAdapter:
    def __init__(self) -> None:
        self.connected: set[str] = set()
        self.subscriptions: list[tuple[str, str, str]] = []
        self.frames: dict[str, list[AdapterMessage]] = {}
        self.recv_errors: dict[str, list[Exception]] = {}

    def connect(self, endpoint: str) -> None:
        self.connected.add(endpoint)

    def disconnect(self, endpoint: str) -> None:
        self.connected.discard(endpoint)

    def subscribe(self, endpoint: str, pair: str, stream_type: str) -> None:
        self.subscriptions.append((endpoint, pair, stream_type))

    def recv(self, endpoint: str) -> AdapterMessage | None:
        if endpoint in self.recv_errors and self.recv_errors[endpoint]:
            raise self.recv_errors[endpoint].pop(0)
        queue = self.frames.get(endpoint, [])
        if not queue:
            return None
        return queue.pop(0)


class TestWebSocketGatewayRuntime:
    def test_connect_and_resubscribe(self):
        adapter = _FakeAdapter()
        runtime = WebSocketGatewayRuntime(adapter)
        runtime.subscribe("BTCUSDT", "trade", EP)
        status = runtime.connect(EP, now=100.0)
        assert status.state == ConnectionState.CONNECTED
        assert (EP, "BTCUSDT", "trade") in adapter.subscriptions

    def test_poll_message_updates_backlog_and_heartbeat(self):
        adapter = _FakeAdapter()
        adapter.frames[EP] = [
            AdapterMessage(
                pair="BTCUSDT",
                stream_type="trade",
                payload={"price": "100"},
                recv_time=101.0,
                source="binance",
            )
        ]
        runtime = WebSocketGatewayRuntime(adapter, emitter=RawMessageEmitter(max_buffer_size=4))
        runtime.subscribe("BTCUSDT", "trade", EP)
        runtime.connect(EP, now=100.0)
        result = runtime.poll_once(EP, now=101.0)
        assert result.raw_message is not None
        assert result.raw_message.pair == "BTCUSDT"
        assert result.backlog == 1
        assert result.heartbeat_state.status == HeartbeatStatus.ALIVE

    def test_reconnect_on_recv_error(self):
        adapter = _FakeAdapter()
        adapter.recv_errors[EP] = [RuntimeError("socket lost")]
        runtime = WebSocketGatewayRuntime(adapter)
        runtime.subscribe("BTCUSDT", "trade", EP)
        runtime.connect(EP, now=100.0)
        result = runtime.poll_once(EP, now=101.0)
        assert result.reconnect_event is not None
        assert result.connection_status.state == ConnectionState.CONNECTED
        assert "socket lost" in result.error

    def test_poll_without_connection_is_visible(self):
        adapter = _FakeAdapter()
        runtime = WebSocketGatewayRuntime(adapter)
        runtime.register_endpoint(EP)
        result = runtime.poll_once(EP, now=100.0)
        assert result.connection_status.state == ConnectionState.DISCONNECTED
        assert result.error == "endpoint_not_connected"
