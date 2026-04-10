import asyncio

import httpx

from data_backbone.websocket_gateway.runtime_gateway import AdapterMessage, WebSocketGatewayAdapter
from venue_adapters.binance_spot.orderbook_manager import BinanceDepthSnapshot, OrderBookSyncState
from venue_adapters.binance_spot.rest_client import BinanceRestClient
from venue_adapters.binance_spot.ws_client import (
    BinanceDepthWebSocketClient,
    BinanceWsClientConfig,
    build_rest_depth_snapshot_provider,
)


class _FakeDepthAdapter(WebSocketGatewayAdapter):
    def __init__(self, messages: list[AdapterMessage] | None = None, *, fail_once: bool = False) -> None:
        self._messages = list(messages or [])
        self._fail_once = fail_once
        self.calls: list[str] = []

    def connect(self, endpoint: str) -> None:
        self.calls.append(f"connect:{endpoint}")

    def disconnect(self, endpoint: str) -> None:
        self.calls.append(f"disconnect:{endpoint}")

    def subscribe(self, endpoint: str, pair: str, stream_type: str) -> None:
        self.calls.append(f"subscribe:{endpoint}:{pair}:{stream_type}")

    def recv(self, endpoint: str) -> AdapterMessage | None:
        self.calls.append(f"recv:{endpoint}")
        if self._fail_once:
            self._fail_once = False
            raise RuntimeError("socket_drop")
        if not self._messages:
            return None
        return self._messages.pop(0)


def test_ws_client_bootstraps_snapshot_before_connect_and_subscribe():
    events: list[str] = []

    def snapshot_provider(pair: str) -> BinanceDepthSnapshot:
        events.append("snapshot")
        return BinanceDepthSnapshot(
            pair=pair,
            last_update_id=100,
            bids=(("100.0", "1.0"),),
            asks=(("101.0", "2.0"),),
            recv_time_s=10.0,
        )

    adapter = _FakeDepthAdapter()
    client = BinanceDepthWebSocketClient(
        pair="BTCUSDT",
        snapshot_provider=snapshot_provider,
        adapter=adapter,
        config=BinanceWsClientConfig(gap_threshold_s=5.0, silence_threshold_s=30.0),
        clock=lambda: 10.0,
    )

    status = client.start(now=10.0)

    assert status.state == OrderBookSyncState.SYNCED
    assert events == ["snapshot"]
    assert adapter.calls[:2] == [
        "connect:wss://stream.binance.com:9443/ws",
        "subscribe:wss://stream.binance.com:9443/ws:BTCUSDT:depth",
    ]


def test_ws_client_replays_depth_delta_after_snapshot():
    def snapshot_provider(pair: str) -> BinanceDepthSnapshot:
        return BinanceDepthSnapshot(
            pair=pair,
            last_update_id=100,
            bids=(("100.0", "1.0"),),
            asks=(("101.0", "2.0"),),
            recv_time_s=10.0,
        )

    adapter = _FakeDepthAdapter(
        [
            AdapterMessage(
                pair="BTCUSDT",
                stream_type="depth",
                payload={
                    "first_update_id": 101,
                    "final_update_id": 102,
                    "bids": [["100.5", "1.5"]],
                    "asks": [["101.0", "0"], ["101.5", "2.0"]],
                },
                recv_time=11.0,
                source="binance_live",
                sequence=102,
            )
        ]
    )
    client = BinanceDepthWebSocketClient(
        pair="BTCUSDT",
        snapshot_provider=snapshot_provider,
        adapter=adapter,
        config=BinanceWsClientConfig(gap_threshold_s=5.0, silence_threshold_s=30.0),
        clock=lambda: 11.0,
    )
    client.start(now=10.0)

    result = client.poll_once(now=11.0)

    assert result.status.state == OrderBookSyncState.SYNCED
    assert result.status.top_bid == "100.5"
    assert result.status.top_ask == "101.5"
    assert result.raw_message_seen is True


def test_ws_client_marks_reconnect_as_requiring_resync():
    snapshot_calls = 0

    def snapshot_provider(pair: str) -> BinanceDepthSnapshot:
        nonlocal snapshot_calls
        snapshot_calls += 1
        return BinanceDepthSnapshot(
            pair=pair,
            last_update_id=100,
            bids=(("100.0", "1.0"),),
            asks=(("101.0", "2.0"),),
            recv_time_s=10.0 + snapshot_calls,
        )

    adapter = _FakeDepthAdapter(fail_once=True)
    client = BinanceDepthWebSocketClient(
        pair="BTCUSDT",
        snapshot_provider=snapshot_provider,
        adapter=adapter,
        config=BinanceWsClientConfig(gap_threshold_s=5.0, silence_threshold_s=30.0),
        clock=lambda: 20.0,
    )
    client.start(now=10.0)

    poll_result = client.poll_once(now=20.0)

    assert poll_result.reconnected is True
    assert poll_result.reconnect_requires_resync is True
    assert poll_result.status.state == OrderBookSyncState.STALE
    assert poll_result.status.reason == "reconnect_resync_required"

    status = client.resync(now=21.0)
    assert snapshot_calls == 2
    assert status.state == OrderBookSyncState.SYNCED


def test_build_rest_depth_snapshot_provider_uses_rest_client():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v3/depth"
        assert request.url.params["symbol"] == "BTCUSDT"
        assert request.url.params["limit"] == "1000"
        return httpx.Response(
            200,
            json={
                "lastUpdateId": 12345,
                "bids": [["100.10000000", "1.25000000"]],
                "asks": [["100.20000000", "2.50000000"]],
            },
        )

    async def close_client(client: httpx.AsyncClient) -> None:
        await client.aclose()

    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(base_url="https://api.binance.com", transport=transport)
    rest_client = BinanceRestClient(client=client, clock_ms=lambda: 1_710_000_000_000)
    provider = build_rest_depth_snapshot_provider(rest_client, snapshot_limit=1000)
    try:
        snapshot = provider("BTCUSDT")
        assert snapshot.last_update_id == 12345
        assert snapshot.bids == (("100.1", "1.25"),)
    finally:
        asyncio.run(close_client(client))
