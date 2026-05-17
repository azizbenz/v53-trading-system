from __future__ import annotations

from local_replay_runtime.raw_data_processing_contracts import BronzeMarketIndexManifest
from local_replay_runtime.silver_market_synchronizer import (
    build_silver_quality_report,
    build_silver_synchronized_market_manifest,
)
from local_replay_runtime.strategy_ladder_data_factory_models import (
    StrategyLadderSilverIndexEntry,
)


def _entry(
    *,
    data_type: str,
    schema_status: str,
    path: str,
    depth_source_status: str = "BOOK_DEPTH_NOT_PROVEN",
    min_timestamp_ms: int | None = 1_745_884_800_000,
    max_timestamp_ms: int | None = 1_745_884_860_000,
    row_count: int = 2,
) -> StrategyLadderSilverIndexEntry:
    return StrategyLadderSilverIndexEntry(
        source_id=f"{data_type}-source",
        source_root="L:/fixture",
        source_priority=10,
        exchange="bybit",
        market_type="spot",
        data_type=data_type,
        pair="BTCUSDT",
        timeframe="1m" if data_type == "ohlcv" else "",
        date="2025-04-29",
        path=path,
        storage_format="jsonl-gz",
        min_timestamp_ms=min_timestamp_ms,
        max_timestamp_ms=max_timestamp_ms,
        row_count=row_count,
        file_hash=f"hash-{data_type}",
        depth_source_status=depth_source_status,
        schema_status=schema_status,
    )


def test_build_silver_synchronized_market_manifest_is_ready_with_shared_book_trade_dates() -> None:
    bronze = BronzeMarketIndexManifest(
        symbol="BTCUSDT",
        source_types_present=("trades", "orderbook_snapshot", "orderbook_delta", "klines"),
        source_types_missing=("metadata",),
        index_status="BRONZE_INDEX_PARTIAL",
    )
    manifest = build_silver_synchronized_market_manifest(
        symbol="BTCUSDT",
        bronze_index=bronze,
        silver_index=(
            _entry(data_type="trades", schema_status="TRADE_SCHEMA_READY", path="trades.jsonl.gz"),
            _entry(data_type="ohlcv", schema_status="KLINE_SCHEMA_READY", path="ohlcv.jsonl.gz"),
            _entry(
                data_type="orderbook_snapshot",
                schema_status="ORDERBOOK_SCHEMA_READY",
                path="book_snapshot.jsonl.gz",
                depth_source_status="BOOK_DEPTH20_AVAILABLE",
            ),
            _entry(
                data_type="orderbook_delta",
                schema_status="ORDERBOOK_SCHEMA_READY",
                path="book_delta.jsonl.gz",
                depth_source_status="BOOK_DEPTH20_AVAILABLE",
            ),
        ),
    )
    report = build_silver_quality_report(manifest, bronze_index=bronze)
    assert manifest.silver_sync_status == "SILVER_SYNC_READY"
    assert manifest.book_trade_alignment_status == "BOOK_TRADE_ALIGNMENT_READY"
    assert manifest.depth20_status == "DEPTH20_READY"
    assert report["silver_sync_status"] == "SILVER_SYNC_READY"


def test_build_silver_synchronized_market_manifest_surfaces_missing_trade_blocker() -> None:
    bronze = BronzeMarketIndexManifest(
        symbol="BTCUSDT",
        source_types_present=("orderbook_snapshot", "klines"),
        source_types_missing=("trades", "orderbook_delta", "metadata"),
        index_status="BRONZE_INDEX_PARTIAL",
    )
    manifest = build_silver_synchronized_market_manifest(
        symbol="BTCUSDT",
        bronze_index=bronze,
        silver_index=(
            _entry(data_type="ohlcv", schema_status="KLINE_SCHEMA_READY", path="ohlcv.jsonl.gz"),
            _entry(
                data_type="orderbook_snapshot",
                schema_status="ORDERBOOK_SCHEMA_READY",
                path="book_snapshot.jsonl.gz",
                depth_source_status="BOOK_LIMITED_DEPTH_AVAILABLE",
            ),
        ),
    )
    assert manifest.silver_sync_status == "SILVER_SYNC_PARTIAL"
    assert "SILVER_MISSING_TRADES" in manifest.blocker_codes
