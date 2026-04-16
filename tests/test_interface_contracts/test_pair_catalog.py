"""Tests for PairCatalog — P1-03 multi-pair contract."""

from __future__ import annotations

import pytest
from decimal import Decimal

from interface_contracts.pair_catalog import PairCatalog, PairEntry, V53_PAIR_CATALOG


# ---------------------------------------------------------------------------
# V53_PAIR_CATALOG static defaults
# ---------------------------------------------------------------------------

class TestV53PairCatalogDefaults:
    def test_has_seven_entries(self) -> None:
        assert len(V53_PAIR_CATALOG.entries) == 7

    def test_contains_all_seven_canonical_symbols(self) -> None:
        expected = {"BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "LINKUSDT", "BNBUSDT", "ADAUSDT"}
        assert V53_PAIR_CATALOG.symbols == expected

    def test_symbols_property_returns_frozenset(self) -> None:
        assert isinstance(V53_PAIR_CATALOG.symbols, frozenset)

    def test_all_entries_have_positive_decimals(self) -> None:
        for entry in V53_PAIR_CATALOG.entries:
            assert Decimal(entry.tick_size) > 0
            assert Decimal(entry.step_size) > 0
            assert Decimal(entry.min_notional) > 0

    def test_btcusdt_specs(self) -> None:
        entry = V53_PAIR_CATALOG.require("BTCUSDT")
        assert entry.tick_size == "0.01"
        assert entry.step_size == "0.00001"
        assert entry.min_notional == "5"

    def test_xrpusdt_has_coarser_step(self) -> None:
        entry = V53_PAIR_CATALOG.require("XRPUSDT")
        assert Decimal(entry.step_size) >= Decimal("0.1")

    def test_adausdt_present(self) -> None:
        entry = V53_PAIR_CATALOG.require("ADAUSDT")
        assert entry.symbol == "ADAUSDT"


# ---------------------------------------------------------------------------
# PairCatalog lookup
# ---------------------------------------------------------------------------

class TestPairCatalogLookup:
    def test_get_existing_symbol_case_insensitive(self) -> None:
        entry = V53_PAIR_CATALOG.get("btcusdt")
        assert entry is not None
        assert entry.symbol == "BTCUSDT"

    def test_get_unknown_symbol_returns_none(self) -> None:
        assert V53_PAIR_CATALOG.get("DOGEUSDT") is None

    def test_require_existing_symbol(self) -> None:
        entry = V53_PAIR_CATALOG.require("ETHUSDT")
        assert entry.symbol == "ETHUSDT"

    def test_require_unknown_symbol_raises_key_error(self) -> None:
        with pytest.raises(KeyError, match="DOGEUSDT"):
            V53_PAIR_CATALOG.require("DOGEUSDT")

    def test_require_case_insensitive(self) -> None:
        entry = V53_PAIR_CATALOG.require("solusdt")
        assert entry.symbol == "SOLUSDT"


# ---------------------------------------------------------------------------
# PairEntry validation
# ---------------------------------------------------------------------------

class TestPairEntryValidation:
    def test_valid_entry_construction(self) -> None:
        entry = PairEntry(
            symbol="TESTUSDT",
            tick_size="0.001",
            step_size="0.01",
            min_notional="5",
        )
        assert entry.symbol == "TESTUSDT"

    def test_rejects_zero_tick_size(self) -> None:
        with pytest.raises(Exception):
            PairEntry(symbol="TESTUSDT", tick_size="0", step_size="0.01", min_notional="5")

    def test_rejects_negative_step_size(self) -> None:
        with pytest.raises(Exception):
            PairEntry(symbol="TESTUSDT", tick_size="0.01", step_size="-0.01", min_notional="5")

    def test_rejects_non_numeric_tick(self) -> None:
        with pytest.raises(Exception):
            PairEntry(symbol="TESTUSDT", tick_size="abc", step_size="0.01", min_notional="5")

    def test_frozen_immutable(self) -> None:
        entry = PairEntry(
            symbol="TESTUSDT",
            tick_size="0.001",
            step_size="0.01",
            min_notional="5",
        )
        with pytest.raises(Exception):
            entry.symbol = "OTHER"  # type: ignore[misc]

    def test_min_qty_zero_is_allowed(self) -> None:
        # "0" min_qty is a valid Binance value meaning "no minimum qty"
        entry = PairEntry(
            symbol="TESTUSDT",
            tick_size="0.001",
            step_size="0.01",
            min_notional="5",
            min_qty="0",
        )
        assert entry.min_qty == "0"


# ---------------------------------------------------------------------------
# PairCatalog.from_exchange_info
# ---------------------------------------------------------------------------

class TestPairCatalogFromExchangeInfo:
    def _make_symbol_info(
        self,
        symbol: str,
        tick: str,
        step: str,
        min_notional: str,
    ) -> object:
        from interface_contracts.binance_contracts import BinanceSymbolInfo
        return BinanceSymbolInfo(
            symbol=symbol,
            tick_size=tick,
            step_size=step,
            min_notional=min_notional,
        )

    def test_builds_from_exchange_info_overrides_defaults(self) -> None:
        from interface_contracts.binance_contracts import BinanceExchangeInfo
        sym_info = self._make_symbol_info("BTCUSDT", "0.1", "0.001", "10")
        ei = BinanceExchangeInfo(server_time_ms=0, symbols=(sym_info,))  # type: ignore[arg-type]
        catalog = PairCatalog.from_exchange_info(ei)
        btc = catalog.require("BTCUSDT")
        assert btc.tick_size == "0.1"
        assert btc.min_notional == "10"

    def test_falls_back_to_static_for_missing_pairs(self) -> None:
        from interface_contracts.binance_contracts import BinanceExchangeInfo
        sym_info = self._make_symbol_info("BTCUSDT", "0.01", "0.00001", "5")
        ei = BinanceExchangeInfo(server_time_ms=0, symbols=(sym_info,))  # type: ignore[arg-type]
        catalog = PairCatalog.from_exchange_info(ei)
        eth = catalog.require("ETHUSDT")
        assert eth == V53_PAIR_CATALOG.require("ETHUSDT")

    def test_ignores_non_canonical_symbols(self) -> None:
        from interface_contracts.binance_contracts import BinanceExchangeInfo
        sym_info = self._make_symbol_info("DOGEUSDT", "0.0001", "1", "5")
        ei = BinanceExchangeInfo(server_time_ms=0, symbols=(sym_info,))  # type: ignore[arg-type]
        catalog = PairCatalog.from_exchange_info(ei)
        assert catalog.get("DOGEUSDT") is None

    def test_catalog_still_has_seven_pairs_after_partial_exchange_info(self) -> None:
        from interface_contracts.binance_contracts import BinanceExchangeInfo
        ei = BinanceExchangeInfo(server_time_ms=0, symbols=())
        catalog = PairCatalog.from_exchange_info(ei)
        assert len(catalog.entries) == 7


# ---------------------------------------------------------------------------
# Frozen contract
# ---------------------------------------------------------------------------

class TestPairCatalogFrozen:
    def test_catalog_is_frozen(self) -> None:
        with pytest.raises(Exception):
            V53_PAIR_CATALOG.entries = ()  # type: ignore[misc]
