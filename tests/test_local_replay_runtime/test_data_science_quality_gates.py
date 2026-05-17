from __future__ import annotations

import json
from pathlib import Path
import shutil

from local_replay_runtime.backtest_replay_dataset_adapter import (
    build_backtest_replay_dataset_manifest,
)
from local_replay_runtime.data_science_quality_gates import (
    build_data_science_quality_report,
    build_runtime_feature_parity_manifest,
    write_quality_reports,
)
from local_replay_runtime.gold_microstructure_feature_builder import (
    build_gold_microstructure_feature_manifest,
)
from local_replay_runtime.ia_lab_feature_dataset_adapter import (
    EXPECTED_EDGE_FEATURE_MANIFEST_FILENAME,
    build_expected_edge_feature_dataset,
)
from local_replay_runtime.strategy_ladder_data_factory_models import StrategyLadderSilverIndexEntry
from tests.support_paths import make_repo_scratch_dir


def _scratch_dir(label: str) -> Path:
    return make_repo_scratch_dir("data_science_quality_gates_tests", label)


def _write_jsonl(path: Path, rows: tuple[dict[str, object], ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n",
        encoding="utf-8",
    )


def test_quality_gates_report_ready_for_research_when_all_groups_are_declared_and_refs_are_present() -> None:
    scratch = _scratch_dir("quality_ready")
    shutil.rmtree(scratch, ignore_errors=True)
    try:
        gold_root = scratch / "gold"
        _write_jsonl(
            gold_root / "features_1m" / "BTCUSDT" / "2025" / "04" / "29.jsonl",
            (
                {
                    "timestamp_ms": 1_745_884_800_000,
                    "pair": "BTCUSDT",
                    "timeframe": "1m",
                    "engine_id": "engine_a",
                    "feature_values": {
                        "close_return": 0.001,
                        "high_low_range": 0.002,
                        "volume": 12.0,
                        "fragility": 0.3,
                        "false_breakout_context": 0.1,
                    },
                    "source_ref": "gold/BTCUSDT/1m/2025-04-29",
                    "available_at_timestamp_ms": 1_745_884_800_000,
                    "spread_bps": 3.0,
                    "slippage_bps": 1.5,
                    "book_depth_levels": 20,
                    "trade_feature_status": "TRADE_FEATURE_STATUS_READY",
                    "kline_feature_status": "KLINE_FEATURE_STATUS_READY",
                    "orderbook_feature_status": "ORDERBOOK_FEATURE_STATUS_READY",
                },
            ),
        )
        gold_manifest = build_gold_microstructure_feature_manifest(
            gold_root=gold_root,
            pairs=("BTCUSDT",),
            timeframes=("1m",),
            start="2025-04-29",
            end="2025-04-29",
        )
        expected_edge_manifest = build_expected_edge_feature_dataset(
            gold_root=gold_root,
            output_dir=scratch,
            dataset_id="btcusdt.expected_edge",
            pairs=("BTCUSDT",),
            timeframes=("1m",),
            start="2025-04-29",
            end="2025-04-29",
            feature_names=("close_return", "high_low_range", "volume", "fragility", "false_breakout_context"),
            source_silver_index_ref=str((scratch / "silver_index.json").resolve()),
            gold_manifest=gold_manifest,
        )
        quality_report = build_data_science_quality_report(expected_edge_manifest=expected_edge_manifest)
        backtest_manifest = build_backtest_replay_dataset_manifest(
            pair_scope=("BTCUSDT",),
            timeframe_scope=("1m",),
            silver_index=(
                StrategyLadderSilverIndexEntry(
                    source_id="metadata",
                    source_root="fixture",
                    exchange="bybit",
                    market_type="spot",
                    data_type="metadata",
                    pair="BTCUSDT",
                    date="2025-04-29",
                    path="metadata.jsonl.gz",
                    storage_format="jsonl-gz",
                    row_count=1,
                    file_hash="metadata-hash",
                    depth_source_status="BOOK_DEPTH_NOT_PROVEN",
                    schema_status="METADATA_SCHEMA_READY",
                ),
            ),
            gold_manifest=gold_manifest,
        )
        runtime_parity_manifest = build_runtime_feature_parity_manifest(
            gold_manifest=gold_manifest,
            source_silver_index_ref=str((scratch / "silver_index.json").resolve()),
        )
        write_quality_reports(
            scratch,
            data_science_report=quality_report,
            runtime_parity_manifest=runtime_parity_manifest,
            raw_manifests=(),
            bronze_index=type("BronzeStub", (), {
                "source_types_present": (),
                "source_types_missing": (),
                "index_status": "BRONZE_INDEX_READY",
                "gap_count": 0,
                "largest_gap_ms": 0,
            })(),
            silver_manifest=type("SilverStub", (), {
                "silver_sync_status": "SILVER_SYNC_READY",
                "stale_book_count": 0,
                "missing_book_count": 0,
                "missing_trade_count": 0,
                "missing_ohlcv_count": 0,
                "blocker_codes": (),
            })(),
            gold_manifest=gold_manifest,
            expected_edge_manifest=expected_edge_manifest,
            backtest_manifest=backtest_manifest,
        )
        assert expected_edge_manifest.status == "EXPECTED_EDGE_FEATURE_DATASET_READY"
        assert quality_report.status == "DATA_SCIENCE_READY_FOR_RESEARCH"
        assert quality_report.feature_timestamp_aligned == "FEATURE_TIMESTAMP_ALIGNED"
        assert quality_report.source_refs_non_empty == "SOURCE_REFS_NON_EMPTY"
        assert (scratch / EXPECTED_EDGE_FEATURE_MANIFEST_FILENAME).is_file()
        assert (scratch / "data_science_quality_report.json").is_file()
        assert (scratch / "anti_leakage_precheck_report.json").is_file()
        assert (scratch / "runtime_feature_parity_manifest.json").is_file()
        assert (scratch / "raw_data_processing_report.md").is_file()
        assert (scratch / "raw_data_processing_report.json").is_file()
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
