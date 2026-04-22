"""Tests for the native live websocket Shadow capture path."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
from uuid import uuid4

import pytest

from interface_contracts.binance_contracts import BinanceServerTime
from local_replay_runtime import load_historical_snapshot_batch
from protocols import (
    BinanceSpotLiveWebSocketAdapter,
    ShadowLiveWebSocketConfig,
    capture_live_websocket_snapshot_batch,
)


class _FakeSocket:
    def __init__(self, payloads: list[str]) -> None:
        self.payloads = list(payloads)
        self.sent: list[str] = []
        self.timeout: float | None = None
        self.closed = False

    def settimeout(self, timeout: float) -> None:
        self.timeout = timeout

    def send(self, payload: str) -> None:
        self.sent.append(payload)

    def recv(self) -> str | bytes | None:
        if not self.payloads:
            raise TimeoutError("no more payloads")
        return self.payloads.pop(0)

    def close(self) -> None:
        self.closed = True


def _scratch_dir(label: str) -> Path:
    from tests.support_paths import make_repo_scratch_dir

    return make_repo_scratch_dir("shadow_live_websocket_tests", label)


def test_binance_live_adapter_subscribes_and_parses_trade_and_ticker():
    socket = _FakeSocket(
        [
            json.dumps({"result": None, "id": 1}),
            json.dumps(
                {
                    "stream": "btcusdt@trade",
                    "data": {
                        "e": "trade",
                        "s": "BTCUSDT",
                        "t": 101,
                        "p": "43250.1",
                        "q": "0.250",
                        "m": False,
                    },
                }
            ),
            json.dumps(
                {
                    "stream": "btcusdt@ticker",
                    "data": {
                        "e": "24hrTicker",
                        "s": "BTCUSDT",
                        "c": "43255.0",
                        "b": "43254.5",
                        "a": "43255.5",
                        "v": "125000.0",
                        "h": "44000.0",
                        "l": "42000.0",
                    },
                }
            ),
        ]
    )
    config = ShadowLiveWebSocketConfig(
        endpoint="wss://stream.binance.com:9443/ws",
        pairs=("BTCUSDT",),
        stream_types=("trade", "ticker"),
    )
    adapter = BinanceSpotLiveWebSocketAdapter(
        config,
        socket_factory=lambda endpoint, connect_timeout_s, recv_timeout_s: socket,
        clock=lambda: 1_700_000_000.0,
    )

    adapter.connect(config.endpoint)
    adapter.subscribe(config.endpoint, "BTCUSDT", "trade")
    adapter.subscribe(config.endpoint, "BTCUSDT", "ticker")

    assert adapter.recv(config.endpoint) is None
    trade_message = adapter.recv(config.endpoint)
    ticker_message = adapter.recv(config.endpoint)

    assert len(socket.sent) == 1
    subscribe_request = json.loads(socket.sent[0])
    assert subscribe_request["method"] == "SUBSCRIBE"
    assert subscribe_request["params"] == ["btcusdt@trade", "btcusdt@ticker"]
    assert trade_message is not None
    assert trade_message.stream_type == "trade"
    assert trade_message.pair == "BTCUSDT"
    assert trade_message.payload["side"] == "buy"
    assert ticker_message is not None
    assert ticker_message.stream_type == "snapshot"
    assert ticker_message.payload["last_price"] == "43255.0"


def test_capture_live_websocket_snapshot_batch_materializes_snapshot_batch():
    output_dir = _scratch_dir("capture")
    try:
        socket = _FakeSocket(
            [
                json.dumps({"result": None, "id": 1}),
                json.dumps(
                    {
                        "stream": "btcusdt@trade",
                        "data": {
                            "e": "trade",
                            "s": "BTCUSDT",
                            "t": 101,
                            "p": "43250.1",
                            "q": "0.250",
                            "m": False,
                        },
                    }
                ),
                json.dumps(
                    {
                        "stream": "btcusdt@ticker",
                        "data": {
                            "e": "24hrTicker",
                            "s": "BTCUSDT",
                            "c": "43255.0",
                            "b": "43254.5",
                            "a": "43255.5",
                            "v": "125000.0",
                            "h": "44000.0",
                            "l": "42000.0",
                        },
                    }
                ),
            ]
        )
        config = ShadowLiveWebSocketConfig(
            endpoint="wss://stream.binance.com:9443/ws",
            pairs=("BTCUSDT",),
            stream_types=("trade", "ticker"),
            capture_frame_limit=2,
            idle_poll_limit=3,
            capture_timeout_s=5.0,
            session_date_override="2026-04-02",
            route_hints_by_pair={
                "BTCUSDT": {
                    "route_id": "btc-live-1",
                    "engine_id": "engine_a",
                    "raw_score": 0.91,
                    "penalized_score": 0.88,
                    "final_score": 0.86,
                    "expected_edge_bps": 17.0,
                    "target_decision_state": "executed",
                    "production_decision_state": "executed",
                    "production_final_score": 0.86,
                    "production_expected_cost": 0.00086,
                    "candidate_size": 1.0,
                    "final_size": 1.0,
                    "gross_return_bps": 21.0,
                    "feature_values": {"spread_bps": 3.0},
                }
            },
        )

        result = capture_live_websocket_snapshot_batch(
            config,
            output_dir=output_dir,
            adapter_factory=lambda cfg: BinanceSpotLiveWebSocketAdapter(
                cfg,
                socket_factory=lambda endpoint, connect_timeout_s, recv_timeout_s: socket,
                clock=lambda: 1_700_000_000.0,
            ),
            clock=lambda: 1_700_000_000.0,
        )

        batch = load_historical_snapshot_batch(
            Path(result.snapshot_batch_path_ref)
        )

        assert result.session_date == "2026-04-02"
        assert result.emitted_message_count == 2
        assert result.accepted_message_count == 2
        assert batch.event_count == 2
        assert batch.pair_scope == ("BTCUSDT",)
        assert batch.event_types == ("snapshot", "trade")
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_capture_live_websocket_snapshot_batch_writes_time_sync_offsets_sidecar():
    output_dir = _scratch_dir("capture_time_sync")
    try:
        socket = _FakeSocket(
            [
                json.dumps({"result": None, "id": 1}),
                json.dumps(
                    {
                        "stream": "btcusdt@trade",
                        "data": {
                            "e": "trade",
                            "s": "BTCUSDT",
                            "t": 101,
                            "p": "43250.1",
                            "q": "0.250",
                            "m": False,
                        },
                    }
                ),
            ]
        )
        server_times = iter(
            (
                BinanceServerTime(server_time_ms=1_699_999_999_980),
                BinanceServerTime(server_time_ms=1_699_999_999_975),
                BinanceServerTime(server_time_ms=1_699_999_999_970),
            )
        )

        async def _fake_server_time_reader() -> BinanceServerTime:
            return next(server_times)

        config = ShadowLiveWebSocketConfig(
            endpoint="wss://stream.binance.com:9443/ws",
            pairs=("BTCUSDT",),
            stream_types=("trade",),
            capture_frame_limit=1,
            idle_poll_limit=2,
            capture_timeout_s=5.0,
            time_sync_probe_enabled=True,
            time_sync_sample_count=3,
            time_sync_rest_quota_max_calls_per_minute=120,
            session_date_override="2026-04-04",
        )

        result = capture_live_websocket_snapshot_batch(
            config,
            output_dir=output_dir,
            adapter_factory=lambda cfg: BinanceSpotLiveWebSocketAdapter(
                cfg,
                socket_factory=lambda endpoint, connect_timeout_s, recv_timeout_s: socket,
                clock=lambda: 1_700_000_000.0,
            ),
            time_sync_server_time_reader=_fake_server_time_reader,
            clock=lambda: 1_700_000_000.0,
        )

        time_sync_payload = json.loads(
            Path(result.time_sync_offsets_path_ref).read_text(encoding="utf-8")
        )

        assert result.time_sync_sample_count == 3
        assert result.time_sync_probe_error == ""
        assert time_sync_payload["session_date"] == "2026-04-04"
        assert time_sync_payload["sample_count"] == 3
        assert time_sync_payload["time_sync_offsets_ms"] == [20.0, 25.0, 30.0]
        assert time_sync_payload["rest_call_count"] == 3
        assert time_sync_payload["probe_duration_s"] >= 0.0
        assert time_sync_payload["rest_quota_window_s"] == 60.0
        assert time_sync_payload["rest_quota_max_calls_per_minute"] == 120
        assert time_sync_payload["observed_calls_per_minute"] is not None
        assert time_sync_payload["observed_calls_per_minute"] > 0.0
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_capture_live_websocket_snapshot_batch_reports_endpoint_and_root_cause_on_connect_failure():
    output_dir = _scratch_dir("capture_connect_failure")
    try:
        config = ShadowLiveWebSocketConfig(
            endpoint="wss://stream.binance.com:9443/ws",
            pairs=("BTCUSDT",),
            stream_types=("trade",),
            capture_frame_limit=1,
            idle_poll_limit=2,
            capture_timeout_s=5.0,
        )

        def _failing_socket_factory(
            endpoint: str,
            connect_timeout_s: float,
            recv_timeout_s: float,
        ) -> _FakeSocket:
            raise OSError("connection refused")

        with pytest.raises(RuntimeError, match="failed to connect to .*connection refused"):
            capture_live_websocket_snapshot_batch(
                config,
                output_dir=output_dir,
                adapter_factory=lambda cfg: BinanceSpotLiveWebSocketAdapter(
                    cfg,
                    socket_factory=_failing_socket_factory,
                    clock=lambda: 1_700_000_000.0,
                ),
                clock=lambda: 1_700_000_000.0,
            )
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_binance_live_adapter_batches_multi_pair_multi_stream_subscriptions():
    socket = _FakeSocket([json.dumps({"result": None, "id": 1})])
    config = ShadowLiveWebSocketConfig(
        endpoint="wss://stream.binance.com:9443/ws",
        pairs=("BTCUSDT", "ETHUSDT"),
        stream_types=("kline_1m", "book_ticker", "depth"),
    )
    adapter = BinanceSpotLiveWebSocketAdapter(
        config,
        socket_factory=lambda endpoint, connect_timeout_s, recv_timeout_s: socket,
        clock=lambda: 1_700_000_000.0,
    )

    adapter.connect(config.endpoint)
    for pair in config.pairs:
        for stream_type in config.stream_types:
            adapter.subscribe(config.endpoint, pair, stream_type)

    assert adapter.recv(config.endpoint) is None

    assert len(socket.sent) == 1
    subscribe_request = json.loads(socket.sent[0])
    assert subscribe_request["method"] == "SUBSCRIBE"
    assert subscribe_request["params"] == [
        "btcusdt@kline_1m",
        "btcusdt@bookTicker",
        "btcusdt@depth",
        "ethusdt@kline_1m",
        "ethusdt@bookTicker",
        "ethusdt@depth",
    ]


def test_binance_live_adapter_reconnect_closes_stale_client():
    first_socket = _FakeSocket([])
    second_socket = _FakeSocket([])
    sockets = [first_socket, second_socket]
    config = ShadowLiveWebSocketConfig(
        endpoint="wss://stream.binance.com:9443/ws",
        pairs=("BTCUSDT",),
        stream_types=("trade",),
    )

    def _socket_factory(endpoint: str, connect_timeout_s: float, recv_timeout_s: float) -> _FakeSocket:
        return sockets.pop(0)

    adapter = BinanceSpotLiveWebSocketAdapter(
        config,
        socket_factory=_socket_factory,
        clock=lambda: 1_700_000_000.0,
    )

    adapter.connect(config.endpoint)
    adapter.connect(config.endpoint)

    assert first_socket.closed is True
    assert adapter._clients[config.endpoint] is second_socket


def test_capture_live_websocket_snapshot_batch_captures_private_user_data_sidecar(
    monkeypatch,
):
    output_dir = _scratch_dir("capture_user_data")
    try:
        market_socket = _FakeSocket(
            [
                json.dumps({"result": None, "id": 1}),
                json.dumps(
                    {
                        "stream": "btcusdt@trade",
                        "data": {
                            "e": "trade",
                            "s": "BTCUSDT",
                            "t": 101,
                            "p": "43250.1",
                            "q": "0.250",
                            "m": False,
                        },
                    }
                ),
                json.dumps(
                    {
                        "stream": "ethusdt@ticker",
                        "data": {
                            "e": "24hrTicker",
                            "s": "ETHUSDT",
                            "c": "2280.0",
                            "b": "2279.8",
                            "a": "2280.2",
                            "v": "98000.0",
                            "h": "2350.0",
                            "l": "2200.0",
                        },
                    }
                ),
            ]
        )
        user_data_socket = _FakeSocket(
            [
                json.dumps(
                    {
                        "id": "shadow-user-data-subscribe",
                        "status": 200,
                        "result": {"subscriptionId": 7},
                    }
                ),
                json.dumps(
                    {
                        "subscriptionId": 7,
                        "event": {
                            "e": "executionReport",
                            "s": "BTCUSDT",
                        },
                    }
                ),
            ]
        )
        monkeypatch.setenv("BINANCE_API_KEY", "test-api-key")
        monkeypatch.setenv("BINANCE_API_SECRET", "test-api-secret")
        config = ShadowLiveWebSocketConfig(
            endpoint="wss://stream.binance.com:9443/ws",
            pairs=("BTCUSDT", "ETHUSDT"),
            stream_types=("trade", "ticker"),
            capture_frame_limit=2,
            idle_poll_limit=3,
            capture_timeout_s=5.0,
            user_data_stream_enabled=True,
            user_data_event_limit=2,
            user_data_idle_poll_limit=2,
            user_data_capture_timeout_s=5.0,
            session_date_override="2026-04-03",
            route_hints_by_pair={
                "BTCUSDT": {
                    "route_id": "btc-live-1",
                    "engine_id": "engine_a",
                    "raw_score": 0.91,
                    "penalized_score": 0.88,
                    "final_score": 0.86,
                    "expected_edge_bps": 17.0,
                    "target_decision_state": "executed",
                    "production_decision_state": "executed",
                    "production_final_score": 0.86,
                    "production_expected_cost": 0.00086,
                    "candidate_size": 1.0,
                    "final_size": 1.0,
                    "gross_return_bps": 21.0,
                    "feature_values": {"spread_bps": 3.0},
                },
                "ETHUSDT": {
                    "route_id": "eth-live-1",
                    "engine_id": "engine_b",
                    "raw_score": 0.81,
                    "penalized_score": 0.79,
                    "final_score": 0.76,
                    "expected_edge_bps": 7.0,
                    "target_decision_state": "rejected_ranking",
                    "production_decision_state": "rejected_ranking",
                    "production_final_score": 0.76,
                    "production_expected_cost": 0.00094,
                    "ranking_position": 3,
                    "gross_return_bps": -4.0,
                    "feature_values": {"spread_bps": 5.0},
                },
            },
        )

        result = capture_live_websocket_snapshot_batch(
            config,
            output_dir=output_dir,
            adapter_factory=lambda cfg: BinanceSpotLiveWebSocketAdapter(
                cfg,
                socket_factory=lambda endpoint, connect_timeout_s, recv_timeout_s: market_socket,
                clock=lambda: 1_700_000_000.0,
            ),
            user_data_socket_factory=lambda endpoint, connect_timeout_s, recv_timeout_s: user_data_socket,
            clock=lambda: 1_700_000_000.0,
        )

        batch = load_historical_snapshot_batch(Path(result.snapshot_batch_path_ref))

        assert batch.pair_scope == ("BTCUSDT", "ETHUSDT")
        assert result.user_data_authenticated is True
        assert result.user_data_subscription_id == 7
        assert result.user_data_event_count == 1
        assert result.user_data_event_types == ("executionReport",)
        assert Path(result.user_data_summary_path_ref).is_file()
        assert Path(result.user_data_events_path_ref).is_file()
        assert len(user_data_socket.sent) == 1
        subscribe_request = json.loads(user_data_socket.sent[0])
        assert subscribe_request["method"] == "userDataStream.subscribe.signature"
        assert subscribe_request["params"]["apiKey"] == "test-api-key"
        assert "signature" in subscribe_request["params"]
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
