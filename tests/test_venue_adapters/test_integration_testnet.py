"""Integration tests against Binance Spot testnet.

Skipped entirely if env vars BINANCE_TESTNET_API_KEY / BINANCE_TESTNET_SECRET are absent.
Base URL: https://testnet.binance.vision
"""

from __future__ import annotations

import asyncio
import os
import time

import pytest

from interface_contracts.binance_contracts import (
    BinanceOrderRequest,
    BinanceOrderSide,
    BinanceSpotOrderType,
    BinanceTimeInForce,
)
from venue_adapters.binance_spot.credential_loader import load_testnet_credentials
from venue_adapters.binance_spot.rest_client import BinanceRestClient


_TESTNET_CREDS_AVAILABLE = bool(
    os.environ.get("BINANCE_TESTNET_API_KEY") and os.environ.get("BINANCE_TESTNET_SECRET")
)

pytestmark = [
    pytest.mark.testnet,
    pytest.mark.skipif(
        not _TESTNET_CREDS_AVAILABLE,
        reason="BINANCE_TESTNET_API_KEY / BINANCE_TESTNET_SECRET not provided",
    ),
]


def test_server_time_sync() -> None:
    async def run() -> None:
        async with BinanceRestClient(base_url="https://testnet.binance.vision") as client:
            server_time = await client.get_server_time()
            local_ms = int(time.time() * 1000)
            assert abs(server_time.server_time_ms - local_ms) < 5_000

    asyncio.run(run())


def test_account_balance() -> None:
    async def run() -> None:
        async with BinanceRestClient(
            credentials=load_testnet_credentials(),
            base_url="https://testnet.binance.vision",
        ) as client:
            account = await client.get_account_snapshot(recv_window_ms=5_000)
            assert isinstance(account.balances, tuple)

    asyncio.run(run())


def test_limit_buy_then_cancel() -> None:
    async def run() -> None:
        async with BinanceRestClient(
            credentials=load_testnet_credentials(),
            base_url="https://testnet.binance.vision",
        ) as client:
            order = await client.submit_order(
                BinanceOrderRequest(
                    symbol="BTCUSDT",
                    side=BinanceOrderSide.BUY,
                    order_type=BinanceSpotOrderType.LIMIT,
                    time_in_force=BinanceTimeInForce.GTC,
                    quantity="0.01",
                    price="1000.00",
                    client_order_id=f"v53-testnet-{int(time.time())}",
                ),
                recv_window_ms=5_000,
            )
            assert order.status == "NEW"
            await client.cancel_order(
                pair="BTCUSDT",
                order_id=order.order_id,
                recv_window_ms=5_000,
            )

    asyncio.run(run())


def test_rate_limit_observed() -> None:
    async def run() -> None:
        async with BinanceRestClient(base_url="https://testnet.binance.vision") as client:
            await client.get_server_time()
            state = client.rate_limiter.snapshot()
            assert state.request_weight_tokens_remaining < 800
            assert state.throttle_until_ms == 0

    asyncio.run(run())


def test_auth_required_for_signed_endpoint() -> None:
    async def run() -> None:
        async with BinanceRestClient(base_url="https://testnet.binance.vision") as client:
            with pytest.raises(RuntimeError, match="Authenticated Binance credentials are required"):
                await client.get_account_snapshot(recv_window_ms=5_000)

    asyncio.run(run())
