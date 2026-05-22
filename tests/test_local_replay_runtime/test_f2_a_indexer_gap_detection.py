"""Tests F2-A (2026-05-21) — indexer gap detection root cause fix.

Vérifie :
1. `_extract_kline_timeframe` extrait correctement depuis filename + path dir
2. `_gap_group_key` groupe klines par timeframe, autres source_types globalement
3. `_effective_end_timestamp_ms` ajoute interval pour klines
4. `build_bronze_market_index` détecte les VRAIS gaps (group by timeframe)
   pas les artefacts de mesure entre timeframes différents
5. Sur le pattern réel f9bb2bdc, expose le vrai gap 7h21min au lieu du faux 60s
"""

from __future__ import annotations

from datetime import UTC, datetime

from local_replay_runtime.raw_data_processing_contracts import (
    BronzeMarketIndexManifest,
    RawMarketFileManifest,
    finalize_hashed_model,
)
from local_replay_runtime.raw_market_data_indexer import (
    _effective_end_timestamp_ms,
    _extract_kline_timeframe,
    _gap_group_key,
    build_bronze_market_index,
)


def _make_kline(
    *,
    timeframe_dir: str,
    date_str: str,
    start_ms: int,
    end_ms: int,
    path_style: str = "directory",
) -> RawMarketFileManifest:
    """Build a fake kline RawMarketFileManifest with parseable path."""
    if path_style == "directory":
        path = f"L:\\klines\\BTCUSDT\\{timeframe_dir}\\2025\\BTCUSDT_{timeframe_dir}_{date_str}.csv"
    else:
        path = f"L:\\klines\\BTCUSDT\\BTCUSDT_{timeframe_dir}_{date_str}.csv"
    return finalize_hashed_model(
        RawMarketFileManifest(
            symbol="BTCUSDT",
            source_type="klines",
            path=path,
            format="csv",
            start_timestamp_ms=start_ms,
            end_timestamp_ms=end_ms,
            row_count=1000,
            file_size_bytes=100_000,
            sha256="a" * 64,
            compression="none",
            source_status="RAW_FILE_READY",
        )
    )


def _make_trade(
    *,
    date_str: str,
    start_ms: int,
    end_ms: int,
) -> RawMarketFileManifest:
    """Build a fake trades RawMarketFileManifest."""
    return finalize_hashed_model(
        RawMarketFileManifest(
            symbol="BTCUSDT",
            source_type="trades",
            path=f"L:\\trades\\BTCUSDT\\BTCUSDT_{date_str}.csv.gz",
            format="csv",
            start_timestamp_ms=start_ms,
            end_timestamp_ms=end_ms,
            row_count=10000,
            file_size_bytes=100_000,
            sha256="b" * 64,
            compression="gz",
            source_status="RAW_FILE_READY",
        )
    )


def test_extract_kline_timeframe_from_directory_path_2026_05_21() -> None:
    """Patch F2-A — extract '1m', '15m' depuis L:/klines/.../1/2025/...csv pattern."""
    assert _extract_kline_timeframe("L:\\klines\\BTCUSDT\\1\\2025\\BTCUSDT_1_2025-07-23.csv") == "1m"
    assert _extract_kline_timeframe("L:\\klines\\BTCUSDT\\15\\2025\\BTCUSDT_15_2025-07-24.csv") == "15m"
    assert _extract_kline_timeframe("L:\\klines\\BTCUSDT\\5\\BTCUSDT_5_2025-07-23.csv") == "5m"


def test_extract_kline_timeframe_from_filename_only_2026_05_21() -> None:
    """Patch F2-A — extract depuis filename BTCUSDT_10_2025-07-23.csv (sans dir)."""
    assert _extract_kline_timeframe("L:\\klines\\BTCUSDT\\10\\BTCUSDT_10_2025-07-24.csv") == "10m"


def test_extract_kline_timeframe_returns_none_for_unrelated_paths_2026_05_21() -> None:
    """Patch F2-A — None si pas un kline path."""
    assert _extract_kline_timeframe("L:\\trades\\BTCUSDT\\BTCUSDT_2025-07-23.csv.gz") is None
    assert _extract_kline_timeframe("") is None
    assert _extract_kline_timeframe("L:\\random\\path.csv") is None


def test_gap_group_key_klines_per_timeframe_2026_05_21() -> None:
    """Patch F2-A — klines groupées par timeframe pour éviter mélange artefactuel."""
    kl_1m = _make_kline(timeframe_dir="1", date_str="2025-07-23", start_ms=0, end_ms=100)
    kl_15m = _make_kline(timeframe_dir="15", date_str="2025-07-23", start_ms=0, end_ms=100)
    assert _gap_group_key(kl_1m) == "klines:1m"
    assert _gap_group_key(kl_15m) == "klines:15m"
    assert _gap_group_key(kl_1m) != _gap_group_key(kl_15m)


def test_gap_group_key_non_klines_unchanged_2026_05_21() -> None:
    """Patch F2-A — trades / orderbook gardent leur source_type comme key."""
    trade = _make_trade(date_str="2025-07-23", start_ms=0, end_ms=100)
    assert _gap_group_key(trade) == "trades"


def test_effective_end_timestamp_ms_adds_interval_for_klines_2026_05_21() -> None:
    """Patch F2-A — end_ms + interval_ms pour klines (la dernière barre couvre
    [start, start+interval[, donc le vrai end = last_start + interval)."""
    # Barre 1m à 23:59:00 → effective_end = 24:00:00 (1 min ajoutée)
    kl_1m = _make_kline(
        timeframe_dir="1",
        date_str="2025-07-23",
        start_ms=0,
        end_ms=1_753_315_140_000,  # 2025-07-23 23:59:00 UTC
    )
    effective = _effective_end_timestamp_ms(kl_1m)
    assert effective == 1_753_315_140_000 + 60_000  # +1min
    # Barre 15m à 23:45:00 → effective_end = 24:00:00 (15 min ajoutées)
    kl_15m = _make_kline(
        timeframe_dir="15",
        date_str="2025-07-23",
        start_ms=0,
        end_ms=1_753_314_300_000,  # 2025-07-23 23:45:00 UTC
    )
    assert _effective_end_timestamp_ms(kl_15m) == 1_753_314_300_000 + 15 * 60_000


def test_effective_end_timestamp_ms_unchanged_for_non_klines_2026_05_21() -> None:
    """Patch F2-A — trades / orderbook gardent leur end_ms inchangé."""
    trade = _make_trade(date_str="2025-07-23", start_ms=0, end_ms=12345)
    assert _effective_end_timestamp_ms(trade) == 12345


def test_run_f9bb2bdc_pattern_kline_natural_boundary_no_gap_2026_05_21() -> None:
    """Patch F2-A — pattern réel f9bb2bdc : pas de gap entre 1m_23 (end 23:59:00)
    et 15m_24 (start 00:00:00) car timeframes différents → groupes différents."""
    kl_1m_23 = _make_kline(
        timeframe_dir="1",
        date_str="2025-07-23",
        start_ms=1_753_255_200_000,  # 02:00:00 UTC
        end_ms=1_753_315_140_000,  # 23:59:00 UTC
    )
    kl_15m_24 = _make_kline(
        timeframe_dir="15",
        date_str="2025-07-24",
        start_ms=1_753_315_200_000,  # 00:00:00 UTC (next day)
        end_ms=1_753_400_700_000,
    )
    bronze = build_bronze_market_index(
        manifests=(kl_1m_23, kl_15m_24),
        symbol="BTCUSDT",
    )
    # Avant F2-A : gap_count=1 (60s artefact)
    # Après F2-A : gap_count=0 (timeframes différents = groupes différents)
    assert bronze.gap_count == 0, (
        f"AVANT F2-A : gap_count=1 (60s artefact). APRÈS : timeframes "
        f"différents = groupes différents = gap_count=0. Got: {bronze.gap_count}"
    )


def test_run_f9bb2bdc_pattern_exposes_real_kline_truncation_gap_2026_05_21() -> None:
    """Patch F2-A — fichiers 1m tronqués Bybit 1000-cap exposent vrai gap 7h21min."""
    # 1m fichier 2025-07-23 : tronqué à 1000 rows (02:00:00 → 18:39:00 UTC)
    kl_1m_23 = _make_kline(
        timeframe_dir="1",
        date_str="2025-07-23",
        start_ms=1_753_255_200_000,  # 02:00:00 UTC
        end_ms=1_753_315_140_000,  # 18:39:00 UTC (tronqué)
    )
    # 1m fichier 2025-07-24 : démarre aussi à 02:00 (pareil truncation pattern)
    kl_1m_24 = _make_kline(
        timeframe_dir="1",
        date_str="2025-07-24",
        start_ms=1_753_341_600_000,  # 2025-07-24 02:00:00 UTC
        end_ms=1_753_401_540_000,
    )
    bronze = build_bronze_market_index(
        manifests=(kl_1m_23, kl_1m_24),
        symbol="BTCUSDT",
    )
    # Avec F2-A : groupés sous "klines:1m", end effective = 18:39 + 1min = 18:40
    # Gap = 02:00 (jour 24) - 18:40 (jour 23) = 7h20min = 26_400_000 ms
    assert bronze.gap_count == 1
    # Vrai gap exposé : ~7h20min entre fin tronquée jour 23 et début jour 24
    assert bronze.largest_gap_ms >= 7 * 60 * 60_000  # ≥ 7h
    assert bronze.largest_gap_ms <= 8 * 60 * 60_000  # ≤ 8h


def test_kline_boundary_within_same_timeframe_no_gap_2026_05_21() -> None:
    """Patch F2-A — fichiers consécutifs même timeframe avec boundary naturelle = pas de gap."""
    # 1m fichier 23 : ENTIER (couvre 24h, end à 23:59:00 = la dernière barre 23:59)
    kl_1m_23 = _make_kline(
        timeframe_dir="1",
        date_str="2025-07-23",
        start_ms=1_753_228_800_000,  # 00:00:00 UTC
        end_ms=1_753_315_140_000,  # 23:59:00 UTC (dernière barre 1m)
    )
    # 1m fichier 24 : ENTIER, commence à 00:00:00
    kl_1m_24 = _make_kline(
        timeframe_dir="1",
        date_str="2025-07-24",
        start_ms=1_753_315_200_000,  # 2025-07-24 00:00:00 UTC
        end_ms=1_753_401_540_000,
    )
    bronze = build_bronze_market_index(
        manifests=(kl_1m_23, kl_1m_24),
        symbol="BTCUSDT",
    )
    # Vraie continuité : effective_end_23 = 23:59 + 1min = 24:00 = start_24 → pas de gap
    assert bronze.gap_count == 0
    assert bronze.largest_gap_ms == 0


def test_trades_micro_gap_still_detected_2026_05_21() -> None:
    """Patch F2-A — trades ne sont pas affectés (pas de timeframe), micro-gap exposé tel quel."""
    trade_23 = _make_trade(
        date_str="2025-07-23",
        start_ms=1_753_228_800_333,
        end_ms=1_753_315_197_671,  # 23:59:57.671 UTC
    )
    trade_24 = _make_trade(
        date_str="2025-07-24",
        start_ms=1_753_315_200_779,  # 00:00:00.779 UTC
        end_ms=1_753_401_599_644,
    )
    bronze = build_bronze_market_index(
        manifests=(trade_23, trade_24),
        symbol="BTCUSDT",
    )
    # 3.1s gap entre les 2 fichiers trades
    assert bronze.gap_count == 1
    assert 3_000 <= bronze.largest_gap_ms <= 4_000  # ≈ 3.1s gap
