"""Tests for exchange-facing venue constraint providers."""

import json
from pathlib import Path
import shutil

import pytest

from execution_backbone.order_decider.intent_builder import VenueConstraintSnapshot
from execution_backbone.venue_constraints_provider import (
    BinanceExchangeInfoVenueConstraintProvider,
    VenueConstraintCacheEntry,
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

    def test_pre_warm_fetches_then_persists_cache(self):
        """BS-66: HTTP is only made via pre_warm(), never via fetch_venue_constraints()."""
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

            # pre_warm does the HTTP fetch at startup
            warmed = provider.pre_warm(["BTCUSDT"])
            assert warmed == 1
            assert call_count == 1
            assert cache_path.exists()

            # fetch_venue_constraints is cache-only: no additional HTTP calls
            first = provider.fetch_venue_constraints("BTCUSDT")
            second = provider.fetch_venue_constraints("BTCUSDT")
            assert first is not None
            assert second == first
            assert call_count == 1  # still 1 â€” no HTTP during execution path

            reloaded = BinanceExchangeInfoVenueConstraintProvider(
                cache_path=cache_path,
                http_get=lambda *_: (_ for _ in ()).throw(AssertionError("cache should be used")),
                clock=lambda: 1234.5,
            )
            cached = reloaded.fetch_venue_constraints("BTCUSDT")
            assert cached == first
        finally:
            shutil.rmtree(cache_root, ignore_errors=True)

    def test_fetch_returns_none_on_cache_miss_no_http(self):
        """fetch_venue_constraints() never makes HTTP calls â€” returns None on miss."""
        def should_not_be_called(url: str, timeout_s: float) -> bytes:
            raise AssertionError("HTTP should not be called from fetch_venue_constraints")

        provider = BinanceExchangeInfoVenueConstraintProvider(
            http_get=should_not_be_called,
        )
        # No pre_warm â€” cache is empty â€” must return None without calling HTTP
        result = provider.fetch_venue_constraints("BTCUSDT")
        assert result is None
    def test_fetch_returns_none_when_cached_entry_is_expired(self):
        provider = BinanceExchangeInfoVenueConstraintProvider(
            cache_ttl_s=60.0,
            http_get=lambda *_: (_ for _ in ()).throw(AssertionError("HTTP should not be called")),
            clock=lambda: 5_000.0,
        )
        provider._cache_state.entries["BTCUSDT"] = VenueConstraintCacheEntry(
            pair="BTCUSDT",
            constraints=VenueConstraintSnapshot(
                tick_size="0.1",
                step_size="0.001",
                min_notional="10",
            ),
            fetched_at=4_900.0,
        )

        result = provider.fetch_venue_constraints("BTCUSDT")

        assert result is None

    def test_pre_warm_skips_fresh_cached_entries_within_ttl(self):
        http_count = 0

        def counting_http(url: str, timeout_s: float) -> bytes:
            nonlocal http_count
            http_count += 1
            return json.dumps(_binance_exchange_info_payload()).encode("utf-8")

        provider = BinanceExchangeInfoVenueConstraintProvider(
            cache_ttl_s=300.0,
            http_get=counting_http,
            clock=lambda: 1_200.0,
        )
        provider._cache_state.entries["BTCUSDT"] = VenueConstraintCacheEntry(
            pair="BTCUSDT",
            constraints=VenueConstraintSnapshot(
                tick_size="0.1",
                step_size="0.001",
                min_notional="10",
            ),
            fetched_at=1_000.0,
        )

        warmed = provider.pre_warm(["BTCUSDT"])

        assert warmed == 0
        assert http_count == 0

    def test_pre_warm_refreshes_expired_entries(self):
        clock_now = 5_000.0
        http_count = 0

        def counting_http(url: str, timeout_s: float) -> bytes:
            nonlocal http_count
            http_count += 1
            return json.dumps(_binance_exchange_info_payload()).encode("utf-8")

        provider = BinanceExchangeInfoVenueConstraintProvider(
            cache_ttl_s=60.0,
            http_get=counting_http,
            clock=lambda: clock_now,
        )
        provider._cache_state.entries["BTCUSDT"] = VenueConstraintCacheEntry(
            pair="BTCUSDT",
            constraints=VenueConstraintSnapshot(
                tick_size="0.1",
                step_size="0.001",
                min_notional="10",
            ),
            fetched_at=4_900.0,
        )

        warmed = provider.pre_warm(["BTCUSDT"])

        assert warmed == 1
        assert http_count == 1
        assert provider.fetch_venue_constraints("BTCUSDT") == VenueConstraintSnapshot(
            tick_size="0.1",
            step_size="0.001",
            min_notional="10",
        )
