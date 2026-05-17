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
