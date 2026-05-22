from __future__ import annotations

import csv
import gzip
import json
from pathlib import Path
import shutil
import zipfile

from local_replay_runtime.raw_market_data_indexer import (
    build_bronze_market_index,
    scan_bybit_raw_root,
)
from tests.support_paths import make_repo_scratch_dir


def _scratch_dir(label: str) -> Path:
    return make_repo_scratch_dir("raw_market_data_indexer_tests", label)


def _write_csv(path: Path, header: tuple[str, ...], rows: tuple[tuple[object, ...], ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)


def _write_csv_gz(path: Path, header: tuple[str, ...], rows: tuple[tuple[object, ...], ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)


def _write_orderbook_zip(path: Path) -> None:
    payload = "\n".join(
        [
            json.dumps(
                {
                    "topic": "orderbook.200.BTCUSDT",
                    "ts": 1_745_884_800_000,
                    "type": "snapshot",
                    "data": {"s": "BTCUSDT", "b": [["63000", "1.0"]], "a": [["63001", "1.2"]]},
                }
            ),
            json.dumps(
                {
                    "topic": "orderbook.200.BTCUSDT",
                    "ts": 1_745_884_860_000,
                    "type": "delta",
                    "data": {"s": "BTCUSDT", "b": [["63000", "0.9"]], "a": [["63001", "1.3"]]},
                }
            ),
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("2025-04-29_BTCUSDT_ob200.data", payload + "\n")


def test_scan_bybit_raw_root_detects_trades_klines_and_orderbook() -> None:
    scratch = _scratch_dir("scan_ok")
    shutil.rmtree(scratch, ignore_errors=True)
    try:
        raw_root = scratch / "raw"
        _write_csv_gz(
            raw_root / "trades" / "BTCUSDT_2025-04-29.csv.gz",
            ("id", "timestamp", "price", "volume", "side"),
            (
                ("1", "1745884800000", "63000.0", "0.1", "buy"),
                ("2", "1745884860000", "63010.0", "0.2", "sell"),
            ),
        )
        _write_csv(
            raw_root / "klines" / "BTCUSDT_1_2025-04-29.csv",
            ("startTime", "open", "high", "low", "close", "volume", "turnover"),
            (
                ("1745884800000", "63000", "63050", "62990", "63020", "12", "756240"),
                ("1745884860000", "63020", "63080", "63010", "63070", "14", "882980"),
            ),
        )
        _write_orderbook_zip(raw_root / "ordrebookpart1" / "BTCUSDT" / "2025-04-29_BTCUSDT_ob200.data.zip")

        manifests = scan_bybit_raw_root(
            raw_roots=(raw_root,),
            symbol="BTCUSDT",
            start="2025-04-29",
            end="2025-04-29",
            source_types=("trades", "klines", "orderbook"),
        )
        source_types = {item.source_type for item in manifests}
        assert source_types == {"trades", "klines", "orderbook_snapshot", "orderbook_delta"}
        assert all(item.source_status == "RAW_FILE_READY" for item in manifests)
        bronze = build_bronze_market_index(manifests, symbol="BTCUSDT")
        assert bronze.index_status == "BRONZE_INDEX_PARTIAL"
        assert bronze.source_types_missing == ("metadata",)
        manifests_repeat = scan_bybit_raw_root(
            raw_roots=(raw_root,),
            symbol="BTCUSDT",
            start="2025-04-29",
            end="2025-04-29",
            source_types=("trades", "klines", "orderbook"),
        )
        assert [item.sha256 for item in manifests] == [item.sha256 for item in manifests_repeat]
        assert [item.artifact_hash for item in manifests] == [item.artifact_hash for item in manifests_repeat]
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_bronze_index_blocks_missing_raw_scope() -> None:
    bronze = build_bronze_market_index((), symbol="BTCUSDT")
    assert bronze.index_status == "BRONZE_INDEX_BLOCKED_BY_MISSING_RAW"
    assert "trades" in bronze.source_types_missing


def test_scan_bybit_raw_root_emits_symbol_scoped_metadata_manifests_from_cache_file() -> None:
    scratch = _scratch_dir("scan_metadata")
    shutil.rmtree(scratch, ignore_errors=True)
    try:
        metadata_root = scratch / "metadata"
        _write_csv(
            metadata_root / "symbol_metadata.csv",
            (
                "venue",
                "exchange",
                "market_type",
                "symbol",
                "base_coin",
                "quote_coin",
                "status",
                "tick_size",
                "qty_step",
                "min_order_qty",
                "min_notional",
                "maker_fee_rate",
                "taker_fee_rate",
                "fee_source",
                "metadata_purpose",
                "proof_level",
                "source",
                "fetched_at_utc",
                "raw_payload_hash",
                "metadata_temporal_status",
            ),
            (
                ("bybit", "bybit", "spot", "BTCUSDT", "BTC", "USDT", "Trading", "0.1", "0.001", "0.001", "5", "0.001", "0.001", "cfg", "historical_replay", "research", "local", "2026-05-15T00:00:00+00:00", "h1", "CURRENT_METADATA_PROXY"),
                ("bybit", "bybit", "spot", "ETHUSDT", "ETH", "USDT", "Trading", "0.01", "0.001", "0.001", "5", "0.001", "0.001", "cfg", "historical_replay", "research", "local", "2026-05-15T00:00:00+00:00", "h2", "CURRENT_METADATA_PROXY"),
            ),
        )
        manifests = scan_bybit_raw_root(
            raw_roots=(metadata_root,),
            symbol="BTCUSDT",
            source_types=("metadata",),
        )
        assert len(manifests) == 1
        assert manifests[0].symbol == "BTCUSDT"
        assert manifests[0].source_type == "metadata"
        assert manifests[0].row_count == 1
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_metadata_jsonl_with_markers_does_not_trigger_schema_unknown_2026_05_21() -> None:
    """Patch D3 (2026-05-21) — metadata JSONL avec markers tick_size/qty_step
    NE doit PAS être classifié SCHEMA_UNKNOWN. Avant ce fix, symbol_metadata.jsonl
    (généré par bybit_historical_metadata.py) était systématiquement SCHEMA_UNKNOWN
    car les metadata n'ont pas de timestamps, ce qui déclenchait
    BRONZE_INDEX_BLOCKED_BY_SCHEMA en aval (silver_market_synchronizer.py:88).
    """
    scratch = _scratch_dir("metadata_jsonl_markers")
    shutil.rmtree(scratch, ignore_errors=True)
    try:
        metadata_root = scratch / "metadata"
        metadata_root.mkdir(parents=True, exist_ok=True)
        jsonl_path = metadata_root / "symbol_metadata.jsonl"
        records = [
            {
                "venue": "bybit",
                "exchange": "bybit",
                "market_type": "spot",
                "symbol": "BTCUSDT",
                "base_coin": "BTC",
                "quote_coin": "USDT",
                "status": "Trading",
                "tick_size": "0.1",
                "qty_step": "0.001",
                "min_order_qty": "0.001",
                "min_notional": "5",
                "maker_fee_rate": "0.001",
                "taker_fee_rate": "0.001",
                "fetched_at_utc": "2026-05-15T00:00:00+00:00",
            }
        ]
        with jsonl_path.open("w", encoding="utf-8") as handle:
            for record in records:
                handle.write(json.dumps(record) + "\n")

        manifests = scan_bybit_raw_root(
            raw_roots=(metadata_root,),
            symbol="BTCUSDT",
            source_types=("metadata",),
        )
        # Metadata JSONL avec markers détectés → status acceptable, PAS SCHEMA_UNKNOWN
        btc_entries = [m for m in manifests if m.symbol == "BTCUSDT"]
        assert btc_entries, "BTCUSDT metadata JSONL doit produire au moins 1 manifest"
        for entry in btc_entries:
            assert entry.source_status != "RAW_FILE_SCHEMA_UNKNOWN", (
                f"Metadata JSONL avec markers ne doit PAS être SCHEMA_UNKNOWN, "
                f"got status={entry.source_status}"
            )
        # Bronze index NE doit PAS être bloqué par schema sur ce metadata JSONL
        bronze = build_bronze_market_index(manifests, symbol="BTCUSDT")
        assert bronze.index_status != "BRONZE_INDEX_BLOCKED_BY_SCHEMA", (
            f"Bronze index NE doit PAS être SCHEMA-bloqué par metadata JSONL valide, "
            f"got status={bronze.index_status}"
        )
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_zip_and_extracted_orderbook_deduplicated_in_scan_2026_05_21() -> None:
    """Patch D4 (2026-05-21) — ZIP et son contenu extrait sont dédupliqués.

    Avant ce fix, un orderbook ob200.data.zip ET son extrait étaient tous deux
    indexés (paths différents) ce qui gonflait artificiellement
    duplicate_timestamp_count dans le bronze index. Maintenant on dédupplique
    par signature contenu (symbol, source_type, start_ts, end_ts, row_count)
    et on préfère la version non-zip pour faciliter le parsing downstream.
    """
    scratch = _scratch_dir("zip_extract_dedup")
    shutil.rmtree(scratch, ignore_errors=True)
    try:
        raw_root = scratch / "ordrebookpart1" / "BTCUSDT"
        # Le ZIP
        _write_orderbook_zip(raw_root / "2025-04-29_BTCUSDT_ob200.data.zip")
        # Le contenu extrait (même payload)
        extract_dir = raw_root / "2025-04-29_BTCUSDT_ob200.data"
        extract_dir.mkdir(parents=True, exist_ok=True)
        payload = "\n".join(
            [
                json.dumps(
                    {
                        "topic": "orderbook.200.BTCUSDT",
                        "ts": 1_745_884_800_000,
                        "type": "snapshot",
                        "data": {"s": "BTCUSDT", "b": [["63000", "1.0"]], "a": [["63001", "1.2"]]},
                    }
                ),
                json.dumps(
                    {
                        "topic": "orderbook.200.BTCUSDT",
                        "ts": 1_745_884_860_000,
                        "type": "delta",
                        "data": {"s": "BTCUSDT", "b": [["63000", "0.9"]], "a": [["63001", "1.3"]]},
                    }
                ),
            ]
        )
        (extract_dir / "2025-04-29_BTCUSDT_ob200.data").write_text(payload + "\n", encoding="utf-8")

        manifests = scan_bybit_raw_root(
            raw_roots=(raw_root.parent,),
            symbol="BTCUSDT",
            start="2025-04-29",
            end="2025-04-29",
            source_types=("orderbook",),
        )
        # Avant fix : 4 manifests (zip × 2 source_types + extract × 2 source_types)
        # Après fix : 2 manifests (1 par source_type, dedup par signature contenu)
        source_types = [m.source_type for m in manifests]
        assert source_types.count("orderbook_snapshot") == 1, (
            f"Doit y avoir exactement 1 manifest orderbook_snapshot après dedup, "
            f"got: {source_types}"
        )
        assert source_types.count("orderbook_delta") == 1, (
            f"Doit y avoir exactement 1 manifest orderbook_delta après dedup, "
            f"got: {source_types}"
        )
        # Préférence non-zip si extract dispo
        for manifest in manifests:
            assert (manifest.format or "").lower() != "zip", (
                f"Dedup doit préférer la version non-zip, got format={manifest.format}"
            )
        # Bronze index : duplicate_timestamp_count = 0 après dedup
        bronze = build_bronze_market_index(manifests, symbol="BTCUSDT")
        assert bronze.duplicate_timestamp_count == 0, (
            f"duplicate_timestamp_count doit être 0 après dedup, "
            f"got: {bronze.duplicate_timestamp_count}"
        )
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
