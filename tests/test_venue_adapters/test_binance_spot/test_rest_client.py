import asyncio
from urllib.parse import parse_qs

import httpx

from interface_contracts.binance_contracts import (
    BinanceCredentials,
    BinanceOrderRequest,
    BinanceOrderSide,
    BinanceSpotOrderType,
    BinanceTimeInForce,
)
from venue_adapters.binance_spot.rest_client import BinanceRestClient
from venue_adapters.binance_spot.rate_limiter import (
    BinanceApiRateLimiter,
    BinanceApiRateLimiterConfig,
    BinanceApiRateLimitExceededError,
)


def test_get_server_time_returns_typed_snapshot():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v3/time"
        return httpx.Response(200, json={"serverTime": 1_710_000_000_123})

    async def run() -> None:
        transport = httpx.MockTransport(handler)
        client = httpx.AsyncClient(base_url="https://api.binance.com", transport=transport)
        rest_client = BinanceRestClient(client=client)
        try:
            server_time = await rest_client.get_server_time()
            assert server_time.server_time_ms == 1_710_000_000_123
        finally:
            await client.aclose()

    asyncio.run(run())


def test_get_exchange_info_normalizes_symbol_filters():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v3/exchangeInfo"
        return httpx.Response(
            200,
            json={
                "timezone": "UTC",
                "serverTime": 1_710_000_000_456,
                "symbols": [
                    {
                        "symbol": "BTCUSDT",
                        "status": "TRADING",
                        "baseAsset": "BTC",
                        "quoteAsset": "USDT",
                        "isSpotTradingAllowed": True,
                        "filters": [
                            {"filterType": "PRICE_FILTER", "tickSize": "0.10"},
                            {"filterType": "LOT_SIZE", "stepSize": "0.00100000"},
                            {"filterType": "MIN_NOTIONAL", "minNotional": "10.00000000"},
                        ],
                    }
                ],
            },
        )

    async def run() -> None:
        transport = httpx.MockTransport(handler)
        client = httpx.AsyncClient(base_url="https://api.binance.com", transport=transport)
        rest_client = BinanceRestClient(client=client)
        try:
            exchange_info = await rest_client.get_exchange_info(pair="BTCUSDT")
            assert exchange_info.symbols[0].tick_size == "0.1"
            assert exchange_info.symbols[0].step_size == "0.001"
            assert exchange_info.symbols[0].min_notional == "10"
        finally:
            await client.aclose()

    asyncio.run(run())


def test_get_account_snapshot_signs_read_only_request():
    credentials = BinanceCredentials(api_key="api-key", secret_key="secret-key", label="testnet")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v3/account"
        assert request.headers["X-MBX-APIKEY"] == "api-key"
        params = parse_qs(request.url.query.decode("utf-8"))
        assert params["recvWindow"] == ["5000"]
        assert params["timestamp"] == ["1710000000123"]
        assert "signature" in params
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
                    {"asset": "USDT", "free": "123.45000000", "locked": "0.10000000"},
                ],
            },
        )

    async def run() -> None:
        transport = httpx.MockTransport(handler)
        client = httpx.AsyncClient(base_url="https://api.binance.com", transport=transport)
        rest_client = BinanceRestClient(
            credentials=credentials,
            client=client,
            clock_ms=lambda: 1_710_000_000_123,
        )
        try:
            snapshot = await rest_client.get_account_snapshot(recv_window_ms=5000)
            assert snapshot.can_trade is True
            assert snapshot.account_type == "SPOT"
            assert snapshot.balances[0].free == "123.45"
        finally:
            await client.aclose()

    asyncio.run(run())


def test_get_account_feature_payload_signs_whitelisted_request():
    credentials = BinanceCredentials(api_key="api-key", secret_key="secret-key", label="testnet")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/sapi/v1/margin/account"
        assert request.headers["X-MBX-APIKEY"] == "api-key"
        params = parse_qs(request.url.query.decode("utf-8"))
        assert params["recvWindow"] == ["5000"]
        assert params["timestamp"] == ["1710000000123"]
        assert "signature" in params
        return httpx.Response(200, json={"userAssets": []})

    async def run() -> None:
        transport = httpx.MockTransport(handler)
        client = httpx.AsyncClient(base_url="https://api.binance.com", transport=transport)
        rest_client = BinanceRestClient(
            credentials=credentials,
            client=client,
            clock_ms=lambda: 1_710_000_000_123,
        )
        try:
            payload = await rest_client.get_account_feature_payload(
                path="/sapi/v1/margin/account",
                recv_window_ms=5000,
            )
            assert payload == {"userAssets": []}
        finally:
            await client.aclose()

    asyncio.run(run())


def test_get_account_feature_payload_rejects_unknown_path():
    credentials = BinanceCredentials(api_key="api-key", secret_key="secret-key", label="testnet")

    async def run() -> None:
        client = httpx.AsyncClient(base_url="https://api.binance.com", transport=httpx.MockTransport(lambda _r: httpx.Response(200, json={})))
        rest_client = BinanceRestClient(credentials=credentials, client=client)
        try:
            try:
                await rest_client.get_account_feature_payload(
                    path="/api/v3/account",
                    recv_window_ms=5000,
                )
            except ValueError as exc:
                assert "Unsupported Binance account feature audit path" in str(exc)
            else:
                raise AssertionError("Expected unsupported path to fail")
        finally:
            await client.aclose()

    asyncio.run(run())


def test_get_depth_snapshot_returns_typed_orderbook_snapshot():
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

    async def run() -> None:
        transport = httpx.MockTransport(handler)
        client = httpx.AsyncClient(base_url="https://api.binance.com", transport=transport)
        rest_client = BinanceRestClient(client=client, clock_ms=lambda: 1_710_000_000_000)
        try:
            snapshot = await rest_client.get_depth_snapshot(pair="BTCUSDT", limit=1000)
            assert snapshot.last_update_id == 12345
            assert snapshot.bids == (("100.1", "1.25"),)
            assert snapshot.asks == (("100.2", "2.5"),)
            assert snapshot.recv_time_s == 1_710_000_000.0
        finally:
            await client.aclose()

    asyncio.run(run())


def test_submit_order_signs_post_request():
    credentials = BinanceCredentials(api_key="api-key", secret_key="secret-key", label="testnet")
    order_request = BinanceOrderRequest(
        symbol="BTCUSDT",
        side=BinanceOrderSide.BUY,
        order_type=BinanceSpotOrderType.LIMIT,
        quantity="0.125",
        price="50000.1",
        time_in_force=BinanceTimeInForce.GTC,
        client_order_id="v53_engine_a_intent-1",
    )

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/api/v3/order"
        assert request.headers["X-MBX-APIKEY"] == "api-key"
        params = parse_qs(request.url.query.decode("utf-8"))
        assert params["symbol"] == ["BTCUSDT"]
        assert params["side"] == ["BUY"]
        assert params["type"] == ["LIMIT"]
        assert params["quantity"] == ["0.125"]
        assert params["price"] == ["50000.1"]
        assert params["timeInForce"] == ["GTC"]
        assert params["newClientOrderId"] == ["v53_engine_a_intent-1"]
        assert params["recvWindow"] == ["5000"]
        assert params["timestamp"] == ["1710000000123"]
        assert "signature" in params
        return httpx.Response(
            200,
            json={
                "symbol": "BTCUSDT",
                "orderId": 123456,
                "clientOrderId": "v53_engine_a_intent-1",
                "transactTime": 1_710_000_000_555,
                "price": "50000.10000000",
                "origQty": "0.12500000",
                "executedQty": "0.00000000",
                "status": "NEW",
                "timeInForce": "GTC",
                "type": "LIMIT",
                "side": "BUY",
            },
        )

    async def run() -> None:
        transport = httpx.MockTransport(handler)
        client = httpx.AsyncClient(base_url="https://api.binance.com", transport=transport)
        rest_client = BinanceRestClient(
            credentials=credentials,
            client=client,
            clock_ms=lambda: 1_710_000_000_123,
        )
        try:
            ack = await rest_client.submit_order(order_request, recv_window_ms=5000)
            assert ack.order_id == 123456
            assert ack.client_order_id == "v53_engine_a_intent-1"
            assert ack.price == "50000.1"
            assert ack.orig_qty == "0.125"
        finally:
            await client.aclose()

    asyncio.run(run())


def test_get_open_orders_signs_authenticated_request():
    credentials = BinanceCredentials(api_key="api-key", secret_key="secret-key", label="testnet")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/api/v3/openOrders"
        assert request.headers["X-MBX-APIKEY"] == "api-key"
        params = parse_qs(request.url.query.decode("utf-8"))
        assert params["symbol"] == ["BTCUSDT"]
        assert params["recvWindow"] == ["5000"]
        assert params["timestamp"] == ["1710000000123"]
        assert "signature" in params
        return httpx.Response(
            200,
            json=[
                {
                    "symbol": "BTCUSDT",
                    "orderId": 123456,
                    "clientOrderId": "v53_engine_a_intent-1",
                    "price": "50000.10000000",
                    "origQty": "0.12500000",
                    "executedQty": "0.02500000",
                    "status": "PARTIALLY_FILLED",
                    "timeInForce": "GTC",
                    "type": "LIMIT",
                    "side": "BUY",
                    "updateTime": 1_710_000_000_777,
                }
            ],
        )

    async def run() -> None:
        transport = httpx.MockTransport(handler)
        client = httpx.AsyncClient(base_url="https://api.binance.com", transport=transport)
        rest_client = BinanceRestClient(
            credentials=credentials,
            client=client,
            clock_ms=lambda: 1_710_000_000_123,
        )
        try:
            orders = await rest_client.get_open_orders(pair="BTCUSDT", recv_window_ms=5000)
            assert len(orders) == 1
            assert orders[0].order_id == 123456
            assert orders[0].executed_qty == "0.025"
            assert orders[0].price == "50000.1"
        finally:
            await client.aclose()

    asyncio.run(run())


def test_cancel_order_signs_delete_request():
    credentials = BinanceCredentials(api_key="api-key", secret_key="secret-key", label="testnet")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "DELETE"
        assert request.url.path == "/api/v3/order"
        assert request.headers["X-MBX-APIKEY"] == "api-key"
        params = parse_qs(request.url.query.decode("utf-8"))
        assert params["symbol"] == ["BTCUSDT"]
        assert params["orderId"] == ["123456"]
        assert params["recvWindow"] == ["5000"]
        assert params["timestamp"] == ["1710000000123"]
        assert "signature" in params
        return httpx.Response(200, json={"status": "CANCELED"})

    async def run() -> None:
        transport = httpx.MockTransport(handler)
        client = httpx.AsyncClient(base_url="https://api.binance.com", transport=transport)
        rest_client = BinanceRestClient(
            credentials=credentials,
            client=client,
            clock_ms=lambda: 1_710_000_000_123,
        )
        try:
            await rest_client.cancel_order(pair="BTCUSDT", order_id=123456, recv_window_ms=5000)
        finally:
            await client.aclose()

    asyncio.run(run())


def test_rest_client_blocks_after_weight_header_reaches_preemptive_ceiling() -> None:
    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        assert request.url.path == "/api/v3/time"
        return httpx.Response(
            200,
            json={"serverTime": 1_710_000_000_123},
            headers={"X-MBX-USED-WEIGHT-1M": "800"},
        )

    async def run() -> None:
        transport = httpx.MockTransport(handler)
        client = httpx.AsyncClient(base_url="https://api.binance.com", transport=transport)
        rest_client = BinanceRestClient(client=client, clock_ms=lambda: 1_710_000_000_000)
        try:
            await rest_client.get_server_time()
            try:
                await rest_client.get_server_time()
            except BinanceApiRateLimitExceededError as exc:
                assert "request-weight budget exhausted" in str(exc)
            else:
                raise AssertionError("Expected preemptive quota block after header sync")
        finally:
            await client.aclose()

    asyncio.run(run())
    assert call_count == 1


def test_rest_client_blocks_for_60s_after_official_weight_header_reaches_95_percent() -> None:
    current_ms = 1_710_000_000_000
    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        assert request.url.path == "/api/v3/time"
        return httpx.Response(
            200,
            json={"serverTime": 1_710_000_000_123},
            headers={"X-MBX-USED-WEIGHT-1M": "1140"},
        )

    async def run() -> None:
        nonlocal current_ms
        transport = httpx.MockTransport(handler)
        client = httpx.AsyncClient(base_url="https://api.binance.com", transport=transport)
        limiter = BinanceApiRateLimiter(
            config=BinanceApiRateLimiterConfig(
                official_request_weight_limit_1m=1200,
                preemptive_request_weight_limit_1m=1200,
            ),
            clock_ms=lambda: current_ms,
        )
        rest_client = BinanceRestClient(
            client=client,
            clock_ms=lambda: current_ms,
            rate_limiter=limiter,
        )
        try:
            await rest_client.get_server_time()
            snapshot = limiter.snapshot(now_ms=current_ms)
            assert snapshot.official_request_weight_warn_active is True
            assert snapshot.official_request_weight_block_active is True
            assert snapshot.throttle_until_ms == current_ms + 60_000
            try:
                await rest_client.get_server_time()
            except BinanceApiRateLimitExceededError as exc:
                assert "official block threshold" in str(exc)
            else:
                raise AssertionError("Expected official request-weight block after 95% header sync")

            current_ms += 60_000
            await rest_client.get_server_time()
        finally:
            await client.aclose()

    asyncio.run(run())
    assert call_count == 2


def test_rest_client_enters_backoff_after_429_response() -> None:
    current_ms = 1_710_000_000_000
    call_count = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return httpx.Response(429, json={"code": -1003, "msg": "too many requests"})

    async def run() -> None:
        nonlocal current_ms
        transport = httpx.MockTransport(handler)
        client = httpx.AsyncClient(base_url="https://api.binance.com", transport=transport)
        rest_client = BinanceRestClient(client=client, clock_ms=lambda: current_ms)
        try:
            try:
                await rest_client.get_server_time()
            except httpx.HTTPStatusError:
                pass
            else:
                raise AssertionError("Expected 429 to propagate as HTTPStatusError")

            try:
                await rest_client.get_server_time()
            except BinanceApiRateLimitExceededError as exc:
                assert "throttled" in str(exc)
            else:
                raise AssertionError("Expected local backoff after 429")

            current_ms += 5_000
            try:
                await rest_client.get_server_time()
            except httpx.HTTPStatusError:
                pass
            else:
                raise AssertionError("Expected 429 to propagate again after backoff expiry")
        finally:
            await client.aclose()

    asyncio.run(run())
    assert call_count == 2
