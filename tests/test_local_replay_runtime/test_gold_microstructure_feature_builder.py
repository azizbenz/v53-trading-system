from __future__ import annotations

import json
from pathlib import Path
import shutil

from local_replay_runtime.gold_microstructure_feature_builder import (
    build_gold_feature_quality_report,
    build_gold_microstructure_feature_manifest,
    write_gold_feature_reports,
)
from tests.support_paths import make_repo_scratch_dir


def _scratch_dir(label: str) -> Path:
    return make_repo_scratch_dir("gold_microstructure_feature_builder_tests", label)


def _write_jsonl(path: Path, rows: tuple[dict[str, object], ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n",
        encoding="utf-8",
    )


def test_gold_manifest_reports_generated_and_missing_feature_groups() -> None:
    scratch = _scratch_dir("gold_manifest")
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
        manifest = build_gold_microstructure_feature_manifest(
            gold_root=gold_root,
            pairs=("BTCUSDT",),
            timeframes=("1m",),
            start="2025-04-29",
            end="2025-04-29",
        )
        report = build_gold_feature_quality_report(manifest)
        write_gold_feature_reports(scratch, manifest)
        assert manifest.feature_status == "GOLD_FEATURE_STORE_PARTIAL"
        assert "price_return_features" in manifest.feature_groups_generated
        assert "book_liquidity_features" in manifest.feature_groups_generated
        assert "flow_microstructure_features" in manifest.feature_groups_generated
        assert "cost_context_features" in manifest.feature_groups_generated
        assert "fragility_false_breakout_features" in manifest.feature_groups_missing
        assert manifest.feature_hash is not None
        assert report["feature_status"] == "GOLD_FEATURE_STORE_PARTIAL"
        assert (scratch / "gold_microstructure_feature_manifest.json").is_file()
        assert (scratch / "gold_feature_quality_report.json").is_file()
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
