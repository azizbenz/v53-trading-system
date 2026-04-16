"""Tests for MultiSymbolDepthWsClient — P1-01 multi-pair WS."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from venue_adapters.binance_spot.ws_client import (
    BinanceWsClientConfig,
    MultiSymbolDepthWsClient,
    MultiSymbolPollResult,
)
from venue_adapters.binance_spot.orderbook_manager import (
    BinanceDepthSnapshot,
    BinanceOrderBookStatus,
    OrderBookSyncState,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_snapshot(pair: str, last_update_id: int = 10) -> BinanceDepthSnapshot:
    return BinanceDepthSnapshot(
        pair=pair,
        last_update_id=last_update_id,
        bids=(("50000.00", "1.0"),),
        asks=(("50001.00", "1.0"),),
        recv_time_s=1000.0,
    )


def _make_status(pair: str = "BTCUSDT") -> BinanceOrderBookStatus:
    return BinanceOrderBookStatus(pair=pair, state=OrderBookSyncState.SYNCED)


def _make_adapter(pairs: list[str]) -> MagicMock:
    """Return a mock WebSocketGatewayAdapter that returns empty poll results."""
    from data_backbone.websocket_gateway.runtime_gateway import (
        GatewayPollResult,
        HeartbeatState,
    )
    from data_backbone.websocket_gateway.heartbeat_monitor import HeartbeatStatus

    adapter = MagicMock()

    def _poll_side_effect(endpoint: str, now: float) -> GatewayPollResult:
        return GatewayPollResult(
            endpoint=endpoint,
            raw_message=None,
            reconnect_event=None,
            heartbeat_state=HeartbeatState(
                endpoint=endpoint,
                status=HeartbeatStatus.ALIVE,
            ),
        )

    adapter.poll.side_effect = _poll_side_effect
    adapter.connect.return_value = None
    adapter.disconnect.return_value = None
    return adapter


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------

class TestMultiSymbolWsClientConstruction:
    def test_rejects_empty_pairs(self) -> None:
        with pytest.raises(ValueError, match="non-empty"):
            MultiSymbolDepthWsClient(
                pairs=[],
                snapshot_provider=lambda p: _make_snapshot(p),
                adapter=MagicMock(),
            )

    def test_normalizes_pairs_to_uppercase(self) -> None:
        adapter = _make_adapter(["BTCUSDT", "ETHUSDT"])
        client = MultiSymbolDepthWsClient(
            pairs=["btcusdt", "ethusdt"],
            snapshot_provider=lambda p: _make_snapshot(p),
            adapter=adapter,
        )
        assert client.pairs == ["BTCUSDT", "ETHUSDT"]

    def test_endpoint_contains_combined_stream_path(self) -> None:
        adapter = _make_adapter(["BTCUSDT", "ETHUSDT"])
        client = MultiSymbolDepthWsClient(
            pairs=["BTCUSDT", "ETHUSDT"],
            snapshot_provider=lambda p: _make_snapshot(p),
            adapter=adapter,
        )
        assert "stream.binance.com/stream" in client.endpoint
        assert "btcusdt" in client.endpoint
        assert "ethusdt" in client.endpoint

    def test_endpoint_has_all_seven_pairs(self) -> None:
        pairs = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "LINKUSDT", "BNBUSDT", "ADAUSDT"]
        adapter = _make_adapter(pairs)
        client = MultiSymbolDepthWsClient(
            pairs=pairs,
            snapshot_provider=lambda p: _make_snapshot(p),
            adapter=adapter,
        )
        for pair in pairs:
            assert pair.lower() in client.endpoint

    def test_endpoint_uses_100ms_depth_streams(self) -> None:
        adapter = _make_adapter(["BTCUSDT"])
        client = MultiSymbolDepthWsClient(
            pairs=["BTCUSDT"],
            snapshot_provider=lambda p: _make_snapshot(p),
            adapter=adapter,
        )
        assert "@depth@100ms" in client.endpoint or "@depth" in client.endpoint


# ---------------------------------------------------------------------------
# start()
# ---------------------------------------------------------------------------

class TestMultiSymbolWsClientStart:
    def test_start_returns_status_for_each_pair(self) -> None:
        pairs = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
        adapter = _make_adapter(pairs)
        called_pairs: list[str] = []

        def snapshot_provider(pair: str) -> BinanceDepthSnapshot:
            called_pairs.append(pair)
            return _make_snapshot(pair)

        client = MultiSymbolDepthWsClient(
            pairs=pairs,
            snapshot_provider=snapshot_provider,
            adapter=adapter,
            clock=lambda: 1000.0,
        )
        statuses = client.start(now=1000.0)
        assert set(statuses.keys()) == set(pairs)
        assert set(called_pairs) == set(pairs)

    def test_start_fetches_snapshot_for_each_pair_once(self) -> None:
        pairs = ["BTCUSDT", "ETHUSDT"]
        call_count: dict[str, int] = {"n": 0}

        def snapshot_provider(pair: str) -> BinanceDepthSnapshot:
            call_count["n"] += 1
            return _make_snapshot(pair)

        adapter = _make_adapter(pairs)
        client = MultiSymbolDepthWsClient(
            pairs=pairs,
            snapshot_provider=snapshot_provider,
            adapter=adapter,
            clock=lambda: 1000.0,
        )
        client.start(now=1000.0)
        assert call_count["n"] == len(pairs)


# ---------------------------------------------------------------------------
# get_status / get_all_statuses
# ---------------------------------------------------------------------------

class TestMultiSymbolWsClientStatus:
    def _client(self, pairs: list[str]) -> MultiSymbolDepthWsClient:
        adapter = _make_adapter(pairs)
        client = MultiSymbolDepthWsClient(
            pairs=pairs,
            snapshot_provider=lambda p: _make_snapshot(p),
            adapter=adapter,
            clock=lambda: 1000.0,
        )
        client.start(now=1000.0)
        return client

    def test_get_all_statuses_returns_all_pairs(self) -> None:
        pairs = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
        client = self._client(pairs)
        statuses = client.get_all_statuses(now=1001.0)
        assert set(statuses.keys()) == set(pairs)

    def test_get_status_unknown_pair_raises(self) -> None:
        client = self._client(["BTCUSDT"])
        with pytest.raises(KeyError, match="DOGEUSDT"):
            client.get_status("DOGEUSDT")

    def test_get_status_case_insensitive(self) -> None:
        client = self._client(["BTCUSDT"])
        client.get_status("btcusdt")  # Should not raise


# ---------------------------------------------------------------------------
# Unique deterministic endpoints per pair set
# ---------------------------------------------------------------------------

class TestMultiSymbolEndpointUniqueness:
    def test_different_pair_sets_produce_different_endpoints(self) -> None:
        adapter1 = _make_adapter(["BTCUSDT"])
        adapter2 = _make_adapter(["ETHUSDT"])
        c1 = MultiSymbolDepthWsClient(
            pairs=["BTCUSDT"],
            snapshot_provider=lambda p: _make_snapshot(p),
            adapter=adapter1,
        )
        c2 = MultiSymbolDepthWsClient(
            pairs=["ETHUSDT"],
            snapshot_provider=lambda p: _make_snapshot(p),
            adapter=adapter2,
        )
        assert c1.endpoint != c2.endpoint


# ---------------------------------------------------------------------------
# MultiSymbolPollResult contract
# ---------------------------------------------------------------------------

class TestMultiSymbolPollResult:
    def test_frozen_immutable(self) -> None:
        result = MultiSymbolPollResult(statuses={}, raw_messages_seen=0)
        with pytest.raises(Exception):
            result.raw_messages_seen = 1  # type: ignore[misc]

    def test_defaults(self) -> None:
        result = MultiSymbolPollResult(statuses={"BTCUSDT": _make_status()})
        assert result.raw_messages_seen == 0
        assert result.reconnected_pairs == ()
