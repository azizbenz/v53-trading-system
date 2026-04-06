"""Tests for exchange-facing venue constraint providers."""

import json
from pathlib import Path
import shutil

import pytest

from execution_backbone.order_decider.intent_builder import VenueConstraintSnapshot
from execution_backbone.venue_constraints_provider import (
    BinanceExchangeInfoVenueConstraintProvider,
    parse_binance_exchange_info_payload,
)


pytestmark = pytest.mark.build3


def _binance_exchange_info_payload(*, min_notional_filter: str = "MIN_NOTIONAL") -> dict[str, object]:
    return {
        "timezone": "UTC",
        "serverTime": 1710000000000,
        "symbols": [
            {
                "symbol": "BTCUSDT",
                "status": "TRADING",
                "filters": [
                    {
                        "filterType": "PRICE_FILTER",
                        "tickSize": "0.10",
                    },
                    {
                        "filterType": "LOT_SIZE",
                        "stepSize": "0.00100000",
                    },
                    {
                        "filterType": min_notional_filter,
                        "minNotional": "10.00000000",
                    },
                ],
            }
        ],
    }


class TestVenueConstraintProvider:
    def test_parse_binance_exchange_info_payload_normalizes_constraints(self):
        constraints = parse_binance_exchange_info_payload(
            _binance_exchange_info_payload(),
            pair="BTCUSDT",
        )

        assert constraints == VenueConstraintSnapshot(
            tick_size="0.1",
            step_size="0.001",
            min_notional="10",
        )

    def test_parse_binance_exchange_info_payload_accepts_notional_filter(self):
        constraints = parse_binance_exchange_info_payload(
            _binance_exchange_info_payload(min_notional_filter="NOTIONAL"),
            pair="BTCUSDT",
        )

        assert constraints is not None
        assert constraints.min_notional == "10"

    def test_provider_fetches_then_persists_cache(self):
        call_count = 0

        def fake_http_get(url: str, timeout_s: float) -> bytes:
            nonlocal call_count
            call_count += 1
            assert "symbol=BTCUSDT" in url
            assert timeout_s == pytest.approx(2.5)
            return json.dumps(_binance_exchange_info_payload()).encode("utf-8")

        cache_root = Path("build/test_execution_backbone_venue_constraints_provider")
        cache_path = cache_root / "venue_constraints.json"
        shutil.rmtree(cache_root, ignore_errors=True)
        try:
            provider = BinanceExchangeInfoVenueConstraintProvider(
                timeout_s=2.5,
                cache_path=cache_path,
                http_get=fake_http_get,
                clock=lambda: 1234.5,
            )

            first = provider.fetch_venue_constraints("BTCUSDT")
            second = provider.fetch_venue_constraints("BTCUSDT")

            assert first is not None
            assert second == first
            assert call_count == 1
            assert cache_path.exists()

            reloaded = BinanceExchangeInfoVenueConstraintProvider(
                cache_path=cache_path,
                http_get=lambda *_: (_ for _ in ()).throw(AssertionError("cache should be used")),
            )
            cached = reloaded.fetch_venue_constraints("BTCUSDT")
            assert cached == first
        finally:
            shutil.rmtree(cache_root, ignore_errors=True)
