"""Tests pour venue_metadata_registry (Audit 2026-05-07 venue-aware)."""

from __future__ import annotations

import pytest

from local_replay_runtime.venue_metadata_registry import (
    BINANCE_SPOT_METADATA,
    BYBIT_SPOT_METADATA,
    UNKNOWN_VENUE_METADATA,
    VENUE_REGISTRY,
    detect_venue_from_path,
    get_venue_metadata,
    resolve_venue,
    venue_id_from_silver_exchange,
)


# ===========================================================================
# get_venue_metadata
# ===========================================================================


def test_get_venue_metadata_binance_aliases() -> None:
    assert get_venue_metadata("binance") is BINANCE_SPOT_METADATA
    assert get_venue_metadata("binance_spot") is BINANCE_SPOT_METADATA
    assert get_venue_metadata("BINANCE") is BINANCE_SPOT_METADATA  # case-insensitive
    assert get_venue_metadata("Binance_Spot") is BINANCE_SPOT_METADATA


def test_get_venue_metadata_bybit_aliases() -> None:
    assert get_venue_metadata("bybit") is BYBIT_SPOT_METADATA
    assert get_venue_metadata("bybit_spot") is BYBIT_SPOT_METADATA
    assert get_venue_metadata("BYBIT") is BYBIT_SPOT_METADATA


def test_get_venue_metadata_unknown_falls_back() -> None:
    assert get_venue_metadata("kraken") is UNKNOWN_VENUE_METADATA
    assert get_venue_metadata("") is UNKNOWN_VENUE_METADATA
    assert get_venue_metadata(None) is UNKNOWN_VENUE_METADATA


# ===========================================================================
# detect_venue_from_path
# ===========================================================================


def test_detect_venue_from_path_bybit_silver() -> None:
    assert detect_venue_from_path("K:/v5.3/silver/bybit/spot/trades.jsonl") == "bybit_spot"
    assert detect_venue_from_path("silver/bybit/spot/orderbook.jsonl") == "bybit_spot"
    # Backslashes Windows
    assert detect_venue_from_path("K:\\v5.3\\silver\\bybit\\spot\\book.jsonl") == "bybit_spot"


def test_detect_venue_from_path_binance_silver() -> None:
    assert detect_venue_from_path("E:/v5.3/silver/binance/spot/book.jsonl") == "binance_spot"
    assert detect_venue_from_path("silver/binance_spot/orderbook.jsonl") == "binance_spot"


def test_detect_venue_from_path_unknown_returns_none() -> None:
    assert detect_venue_from_path(None) is None
    assert detect_venue_from_path("") is None
    assert detect_venue_from_path("random/path/foo.json") is None
    assert detect_venue_from_path("E:/x/silver/kraken/spot/x.json") is None


# ===========================================================================
# resolve_venue priorité
# ===========================================================================


def test_resolve_venue_override_takes_priority() -> None:
    """Override explicite caller > auto-detect path."""
    venue_id, metadata, status = resolve_venue(
        venue_override="binance",
        raw_path_for_detection="K:/silver/bybit/spot/x.jsonl",  # bybit dans path
    )
    # Override binance prevaut
    assert venue_id == "binance"
    assert metadata is BINANCE_SPOT_METADATA
    assert status == "VENUE_OVERRIDE"


def test_resolve_venue_auto_detect_when_no_override() -> None:
    venue_id, metadata, status = resolve_venue(
        venue_override=None,
        raw_path_for_detection="K:/silver/binance/spot/x.jsonl",
    )
    assert venue_id == "binance_spot"
    assert metadata is BINANCE_SPOT_METADATA
    assert status == "VENUE_AUTO_DETECTED"


def test_resolve_venue_unknown_fallback() -> None:
    venue_id, metadata, status = resolve_venue()
    assert venue_id == "unknown"
    assert metadata is UNKNOWN_VENUE_METADATA
    assert status == "VENUE_UNKNOWN"


def test_resolve_venue_override_unknown_marks_status() -> None:
    """Override fourni mais venue inconnu → fallback metadata + status explicite."""
    venue_id, metadata, status = resolve_venue(venue_override="kraken_xyz")
    assert metadata is UNKNOWN_VENUE_METADATA
    assert status == "VENUE_OVERRIDE_UNKNOWN"


# ===========================================================================
# Sanity values
# ===========================================================================


def test_binance_spot_metadata_canonical_values() -> None:
    """Binance Spot canonical : 10 bps standard taker."""
    assert BINANCE_SPOT_METADATA.venue_id == "binance_spot"
    assert BINANCE_SPOT_METADATA.taker_fee_bps == 10.0
    assert BINANCE_SPOT_METADATA.maker_fee_bps == 10.0
    assert BINANCE_SPOT_METADATA.fee_provenance == "MEASURED_FROM_BINANCE_SPOT_PUBLIC_RATES"


def test_bybit_spot_metadata_canonical_values() -> None:
    """Bybit Spot canonical : 10 bps."""
    assert BYBIT_SPOT_METADATA.venue_id == "bybit_spot"
    assert BYBIT_SPOT_METADATA.taker_fee_bps == 10.0


def test_unknown_venue_uses_conservative_25bps() -> None:
    """Fallback degrade : 25 bps fee (signal de venue manquant au registry)."""
    assert UNKNOWN_VENUE_METADATA.taker_fee_bps == 25.0
    assert UNKNOWN_VENUE_METADATA.fee_provenance == "DEGRADED_FALLBACK_UNKNOWN_VENUE"


def test_venue_registry_lookup_case_insensitive() -> None:
    # Le dict VENUE_REGISTRY contient les keys en lowercase
    assert "binance" in VENUE_REGISTRY
    assert "binance_spot" in VENUE_REGISTRY
    assert "bybit" in VENUE_REGISTRY
    assert "bybit_spot" in VENUE_REGISTRY


# ===========================================================================
# Audit 2026-05-13 W1 fix : silver_exchange path
# ===========================================================================


def test_venue_id_from_silver_exchange_bybit_spot() -> None:
    """silver_index.entries[i].exchange='bybit' + market_type='spot' → bybit_spot."""
    assert venue_id_from_silver_exchange("bybit", market_type="spot") == "bybit_spot"
    assert venue_id_from_silver_exchange("BYBIT", market_type="SPOT") == "bybit_spot"


def test_venue_id_from_silver_exchange_binance_spot() -> None:
    assert venue_id_from_silver_exchange("binance", market_type="spot") == "binance_spot"


def test_venue_id_from_silver_exchange_unknown_returns_none() -> None:
    assert venue_id_from_silver_exchange("kraken", market_type="spot") is None
    assert venue_id_from_silver_exchange(None) is None
    assert venue_id_from_silver_exchange("") is None
    # market_type non supporte (ex. perpetual) → None tant que pas dans registry
    assert venue_id_from_silver_exchange("bybit", market_type="perpetual") is None


def test_resolve_venue_from_silver_exchange_takes_precedence_over_path() -> None:
    """silver_exchange='bybit' doit prendre precedence sur l'auto-detect path,
    meme si raw_path_for_detection contient un autre venue."""
    vid, meta, status = resolve_venue(
        silver_exchange="bybit",
        silver_market_type="spot",
        raw_path_for_detection="K:/silver/binance/spot/trades.jsonl",  # auto-detect binance
    )
    assert vid == "bybit_spot"
    assert meta is BYBIT_SPOT_METADATA
    assert status == "VENUE_FROM_SILVER_INDEX"


def test_resolve_venue_override_still_takes_precedence_over_silver_exchange() -> None:
    """venue_override (caller live) > silver_exchange (backtest silver)."""
    vid, meta, status = resolve_venue(
        venue_override="binance",
        silver_exchange="bybit",  # ignore car override prioritaire
    )
    assert vid == "binance"
    assert meta is BINANCE_SPOT_METADATA
    assert status == "VENUE_OVERRIDE"


def test_resolve_venue_silver_exchange_unknown_falls_through_to_path() -> None:
    """silver_exchange inconnu (ex. exchange typo) ne resoud pas, tombe sur path."""
    vid, meta, status = resolve_venue(
        silver_exchange="kraken",  # pas dans registry
        raw_path_for_detection="K:/silver/bybit/spot/trades.jsonl",
    )
    assert vid == "bybit_spot"
    assert status == "VENUE_AUTO_DETECTED"


def test_resolve_venue_b2_run_dossier_signature() -> None:
    """Signature de regression sur le run B2 reel : silver_index entries=
    bybit/spot → fee 10 bps, latency 1.5 bps, MEASURED_FROM_VENUE_METADATA_*.
    Avant W1 fix : DEGRADED_FALLBACK_UNKNOWN_VENUE sur 4000/4000 records."""
    vid, meta, status = resolve_venue(
        silver_exchange="bybit",
        silver_market_type="spot",
    )
    assert vid == "bybit_spot"
    assert status == "VENUE_FROM_SILVER_INDEX"
    assert meta.taker_fee_bps == 10.0
    assert meta.latency_bps_conservative == 1.5
    assert meta.fee_provenance == "MEASURED_FROM_VENUE_METADATA_BYBIT_RESEARCH"
    assert meta.latency_provenance == "STATIC_CONSERVATIVE_FROM_BYBIT_HISTORICAL"
