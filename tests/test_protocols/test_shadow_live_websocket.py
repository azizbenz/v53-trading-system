"""Tests for the native live websocket Shadow capture path."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
from uuid import uuid4

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
    repo_root = Path(__file__).resolve().parents[2]
    base_dir = repo_root / "build" / "shadow_live_websocket_tests"
    base_dir.mkdir(parents=True, exist_ok=True)
    output_dir = base_dir / f"{label}_{uuid4().hex}"
    output_dir.mkdir(parents=True, exist_ok=False)
    return output_dir


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

    assert len(socket.sent) == 2
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
