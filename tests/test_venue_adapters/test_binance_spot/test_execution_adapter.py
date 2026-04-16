import asyncio

import httpx

from execution_backbone import RemoteExecutionState, VenueOrderEvent, VenueOrderEventType
from execution_backbone.order_decider.intent_builder import ExecutionIntent, OrderType, VenueConstraintSnapshot
from venue_adapters.binance_spot.execution_adapter import BinanceSpotExecutionAdapter
from venue_adapters.binance_spot.rest_client import BinanceRestClient
from venue_adapters.binance_spot.time_sync import BinanceAdapterConfig
from venue_adapters.binance_spot.order_translator import build_binance_client_order_id
from venue_adapters.binance_spot.user_data_events import BufferedBinanceUserDataEventSource
from interface_contracts.binance_contracts import BinanceCredentials


def _rest_client(handler) -> BinanceRestClient:
    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(base_url="https://api.binance.com", transport=transport)
    return BinanceRestClient(
        credentials=BinanceCredentials(api_key="api-key", secret_key="secret-key", label="testnet"),
        client=client,
        clock_ms=lambda: 1_710_000_000_123,
    )


def _intent(
    *,
    intent_id: str = "intent-1",
    price_limit_exact: str | None = "50000.1",
) -> ExecutionIntent:
    return ExecutionIntent(
        intent_id=intent_id,
        pair="BTCUSDT",
        engine_id="engine_a",
        side="buy",
        order_type=OrderType.LIMIT,
        quantity=0.25,
        quantity_exact="0.25",
        price_limit=50000.1,
        price_limit_exact=price_limit_exact,
        expected_cost=0.001,
        expected_gain=0.01,
        score=0.8,
        justification="test",
        timeout_s=30.0,
        profile="COMPLETE",
        venue_constraints=VenueConstraintSnapshot(
            tick_size="0.1",
            step_size="0.001",
            min_notional="10",
        ),
    )


class FakeVenueConstraintProvider:
    def fetch_venue_constraints(self, pair: str) -> VenueConstraintSnapshot | None:
        if pair.upper() != "BTCUSDT":
            return None
        return VenueConstraintSnapshot(tick_size="0.1", step_size="0.001", min_notional="10")


def test_execution_adapter_submit_order_returns_submit_receipt():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/api/v3/order"
        return httpx.Response(
            200,
            json={
                "symbol": "BTCUSDT",
                "orderId": 123456,
                "clientOrderId": build_binance_client_order_id(engine_id="engine_a", pair_id="BTCUSDT", intent_id="intent-1"),
                "transactTime": 1_710_000_000_555,
                "price": "50000.10000000",
                "origQty": "0.25000000",
                "executedQty": "0.00000000",
                "status": "NEW",
                "timeInForce": "GTC",
                "type": "LIMIT",
                "side": "BUY",
            },
        )

    rest_client = _rest_client(handler)
    adapter = BinanceSpotExecutionAdapter(
        rest_client=rest_client,
        config=BinanceAdapterConfig(),
        venue_constraint_provider=FakeVenueConstraintProvider(),
    )
    try:
        receipt = adapter.submit_order(_intent(), now=10.0)
        assert receipt.order_id == "123456"
        assert receipt.submitted_at == 1_710_000_000.555
    finally:
        asyncio.run(rest_client.aclose())


def test_execution_adapter_replace_order_cancels_then_submits():
    requests: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append((request.method, request.url.path))
        if request.method == "DELETE":
            return httpx.Response(200, json={"status": "CANCELED"})
        return httpx.Response(
            200,
            json={
                "symbol": "BTCUSDT",
                "orderId": 234567,
                "clientOrderId": build_binance_client_order_id(
                    engine_id="engine_a",
                    pair_id="BTCUSDT",
                    intent_id="intent-1:replace:123456:1",
                ),
                "transactTime": 1_710_000_000_777,
                "price": "49990.00000000",
                "origQty": "0.25000000",
                "executedQty": "0.00000000",
                "status": "NEW",
                "timeInForce": "GTC",
                "type": "LIMIT",
                "side": "BUY",
            },
        )

    rest_client = _rest_client(handler)
    adapter = BinanceSpotExecutionAdapter(
        rest_client=rest_client,
        config=BinanceAdapterConfig(),
        venue_constraint_provider=FakeVenueConstraintProvider(),
    )
    try:
        replacement = adapter.replace_order(
            "123456",
            _intent(intent_id="intent-1:replace:123456:1", price_limit_exact="49990"),
            now=20.0,
        )
        assert replacement.original_order_id == "123456"
        assert replacement.replacement_order_id == "234567"
        assert requests == [
            ("DELETE", "/api/v3/order"),
            ("POST", "/api/v3/order"),
        ]
    finally:
        asyncio.run(rest_client.aclose())


def test_execution_adapter_cancel_order_uses_cached_pair():
    requests: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append((request.method, request.url.path))
        if request.method == "POST":
            return httpx.Response(
                200,
                json={
                    "symbol": "BTCUSDT",
                    "orderId": 123456,
                    "clientOrderId": build_binance_client_order_id(engine_id="engine_a", pair_id="BTCUSDT", intent_id="intent-1"),
                    "transactTime": 1_710_000_000_555,
                    "price": "50000.10000000",
                    "origQty": "0.25000000",
                    "executedQty": "0.00000000",
                    "status": "NEW",
                    "timeInForce": "GTC",
                    "type": "LIMIT",
                    "side": "BUY",
                },
            )
        return httpx.Response(200, json={"status": "CANCELED"})

    rest_client = _rest_client(handler)
    adapter = BinanceSpotExecutionAdapter(
        rest_client=rest_client,
        config=BinanceAdapterConfig(),
        venue_constraint_provider=FakeVenueConstraintProvider(),
    )
    try:
        adapter.submit_order(_intent(), now=10.0)
        adapter.cancel_order("123456", now=15.0, reason="timeout")
        assert requests == [
            ("POST", "/api/v3/order"),
            ("DELETE", "/api/v3/order"),
        ]
    finally:
        asyncio.run(rest_client.aclose())


def test_execution_adapter_fetch_remote_state_maps_orders_and_balances():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v3/openOrders":
            return httpx.Response(
                200,
                json=[
                    {
                        "symbol": "BTCUSDT",
                        "orderId": 123456,
                        "clientOrderId": "v53_engine_a_intent-1",
                        "price": "50000.10000000",
                        "origQty": "0.25000000",
                        "executedQty": "0.02500000",
                        "status": "PARTIALLY_FILLED",
                        "timeInForce": "GTC",
                        "type": "LIMIT",
                        "side": "BUY",
                        "updateTime": 1_710_000_000_777,
                    }
                ],
            )
        return httpx.Response(
            200,
            json={
                "makerCommission": 10,
                "takerCommission": 10,
                "buyerCommission": 0,
                "sellerCommission": 0,
                "canTrade": True,
                "canWithdraw": False,
                "canDeposit": True,
                "accountType": "SPOT",
                "updateTime": 1_710_000_000_999,
                "balances": [
                    {"asset": "BTC", "free": "0.20000000", "locked": "0.05000000"},
                    {"asset": "USDT", "free": "0.00000000", "locked": "0.00000000"},
                ],
            },
        )

    rest_client = _rest_client(handler)
    adapter = BinanceSpotExecutionAdapter(
        rest_client=rest_client,
        config=BinanceAdapterConfig(),
        venue_constraint_provider=FakeVenueConstraintProvider(),
    )
    try:
        state = adapter.fetch_remote_state()
        assert state == RemoteExecutionState(
            orders={"123456": "partially_filled"},
            fills={},
            positions={"BTC": 0.25},
        )
    finally:
        asyncio.run(rest_client.aclose())


def test_execution_adapter_polls_and_drains_user_data_execution_events():
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("REST should not be called while draining buffered user-data events")

    rest_client = _rest_client(handler)
    user_data_source = BufferedBinanceUserDataEventSource(
        (
            {
                "e": "executionReport",
                "E": 1_710_000_001_000,
                "s": "BTCUSDT",
                "c": "v53_engine_a_intent-1",
                "S": "BUY",
                "o": "LIMIT",
                "f": "GTC",
                "q": "0.25000000",
                "p": "50000.10000000",
                "x": "NEW",
                "X": "NEW",
                "i": 123456,
                "l": "0.00000000",
                "z": "0.00000000",
                "L": "0.00000000",
                "n": "0",
                "N": None,
                "t": -1,
                "r": "NONE",
            },
            {
                "e": "executionReport",
                "E": 1_710_000_001_500,
                "s": "BTCUSDT",
                "c": "v53_engine_a_intent-1",
                "S": "BUY",
                "o": "LIMIT",
                "f": "GTC",
                "q": "0.25000000",
                "p": "50000.10000000",
                "x": "TRADE",
                "X": "PARTIALLY_FILLED",
                "i": 123456,
                "l": "0.05000000",
                "z": "0.05000000",
                "L": "50010.00000000",
                "n": "0.01000000",
                "N": "BNB",
                "t": 99,
                "r": "NONE",
            },
        )
    )
    adapter = BinanceSpotExecutionAdapter(
        rest_client=rest_client,
        config=BinanceAdapterConfig(),
        venue_constraint_provider=FakeVenueConstraintProvider(),
        user_data_event_source=user_data_source,
    )
    try:
        assert adapter.poll_order_events() == (
            VenueOrderEvent(
                order_id="123456",
                event_type=VenueOrderEventType.ACK,
                timestamp=1_710_000_001.0,
            ),
            VenueOrderEvent(
                order_id="123456",
                event_type=VenueOrderEventType.FILL,
                timestamp=1_710_000_001.5,
                fill_id="99",
                fill_quantity=0.05,
                fill_price=50010.0,
                fee_amount=0.01,
                fee_asset="BNB",
            ),
        )
        assert adapter.poll_order_events() == ()
    finally:
        asyncio.run(rest_client.aclose())
