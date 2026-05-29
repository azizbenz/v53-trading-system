from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from local_replay_runtime import tabular_artifacts
from local_replay_runtime.strategy_ladder_b_ml_label_factory import (
    BML_TARGET_POLICY,
    BmlLabelFactoryRequest,
    project_bml_rows_to_ml_training_rows,
    run_bml_label_factory,
)
from local_replay_runtime.strategy_ladder_expected_edge_training import (
    StrategyLadderExpectedEdgeTrainingRequest,
    build_strategy_ladder_expected_edge_training_rows,
)


def _ts(raw_value: str) -> int:
    parsed = datetime.fromisoformat(raw_value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return int(parsed.astimezone(UTC).timestamp() * 1000)


def _write_rows(root: Path) -> None:
    path = root / "gold" / "features_5m" / "BTCUSDT" / "2025" / "04" / "features.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for timestamp_ms, close_price in (
        (_ts("2025-04-01T00:00:00Z"), 100.0),
        (_ts("2025-04-01T00:05:00Z"), 101.0),
        (_ts("2025-04-01T00:10:00Z"), 102.0),
    ):
        rows.append(
            {
                "timestamp_ms": timestamp_ms,
                "pair": "BTCUSDT",
                "timeframe": "5m",
                "close_price": close_price,
                "feature_values": {
                    "close_return": 0.001,
                    "high_low_range": 0.002,
                    "volume": 10.0,
                    "spread_bps": 1.0,
                },
                "spread_bps": 1.0,
                "spread_provenance": "MEASURED_FROM_BOOK_SNAPSHOT",
                "slippage_bps": 0.4,
                "slippage_provenance": "MEASURED_FROM_DEPTH20_BOOK_WALK",
                "latency_penalty_bps": 0.1,
                "taker_fee_rate": 0.001,
                "book_depth_source_status": "BOOK_DEPTH20_AVAILABLE",
                "feature_sources_used": ["klines", "orderbook", "trades", "metadata"],
            }
        )
    path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )


def test_b_ml_projection_returns_only_eligible_training_rows(tmp_path: Path) -> None:
    _write_rows(tmp_path / "a2")
    result = run_bml_label_factory(
        BmlLabelFactoryRequest(
            workflow_run_id="wf-training",
            a2_run_root=tmp_path / "a2",
            output_root=tmp_path / "b_ml",
            pair_list=("BTCUSDT",),
            timeframes=("5m",),
            start="2025-04-01",
            end="2025-04-01",
            label_horizons=("5m",),
            capital_buckets=(400,),
            max_candidates_per_day=2,
        )
    )

    rows = project_bml_rows_to_ml_training_rows(
        Path(result.label_store_path),
        pair="BTCUSDT",
        timeframe="5m",
        start="2025-04-01",
        end="2025-04-01",
        feature_names=("close_return", "high_low_range", "volume"),
    )

    assert len(rows) == 2
    assert rows[0].pair == "BTCUSDT"
    assert set(rows[0].features) == {"close_return", "high_low_range", "volume"}


def test_b_ml_projection_prefers_manifest_ready_parquet_mirror(tmp_path: Path) -> None:
    if not tabular_artifacts._pyarrow_available():
        pytest.skip("pyarrow not available")
    _write_rows(tmp_path / "a2")
    result = run_bml_label_factory(
        BmlLabelFactoryRequest(
            workflow_run_id="wf-training",
            a2_run_root=tmp_path / "a2",
            output_root=tmp_path / "b_ml",
            pair_list=("BTCUSDT",),
            timeframes=("5m",),
            start="2025-04-01",
            end="2025-04-01",
            label_horizons=("5m",),
            capital_buckets=(400,),
            max_candidates_per_day=2,
        )
    )
    label_store_path = Path(result.label_store_path)
    label_store_path.write_text("this is not valid jsonl\n", encoding="utf-8")

    rows = project_bml_rows_to_ml_training_rows(
        label_store_path,
        pair="BTCUSDT",
        timeframe="5m",
        start="2025-04-01",
        end="2025-04-01",
        feature_names=("close_return", "high_low_range", "volume"),
    )

    assert len(rows) == 2
    assert rows[0].features["volume"] == pytest.approx(10.0)


def test_b_ml_projection_falls_back_to_jsonl_when_manifest_not_ready(tmp_path: Path) -> None:
    _write_rows(tmp_path / "a2")
    result = run_bml_label_factory(
        BmlLabelFactoryRequest(
            workflow_run_id="wf-training",
            a2_run_root=tmp_path / "a2",
            output_root=tmp_path / "b_ml",
            pair_list=("BTCUSDT",),
            timeframes=("5m",),
            start="2025-04-01",
            end="2025-04-01",
            label_horizons=("5m",),
            capital_buckets=(400,),
            max_candidates_per_day=2,
        )
    )
    manifest_path = Path(result.label_store_path).with_name(
        "b_ml_label_store.tabular_manifest.json"
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["status"] = "TABULAR_MIRROR_NOT_READY"
    manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")

    rows = project_bml_rows_to_ml_training_rows(
        Path(result.label_store_path),
        pair="BTCUSDT",
        timeframe="5m",
        start="2025-04-01",
        end="2025-04-01",
        feature_names=("close_return", "high_low_range", "volume"),
    )

    assert len(rows) == 2


def test_expected_edge_training_rows_accept_b_ml_label_store_path(tmp_path: Path) -> None:
    _write_rows(tmp_path / "a2")
    result = run_bml_label_factory(
        BmlLabelFactoryRequest(
            workflow_run_id="wf-training",
            a2_run_root=tmp_path / "a2",
            output_root=tmp_path / "b_ml",
            pair_list=("BTCUSDT",),
            timeframes=("5m",),
            start="2025-04-01",
            end="2025-04-01",
            label_horizons=("5m",),
            capital_buckets=(400,),
            max_candidates_per_day=2,
        )
    )

    rows = build_strategy_ladder_expected_edge_training_rows(
        StrategyLadderExpectedEdgeTrainingRequest(
            artifact_id="bml-artifact",
            calibration_version="test",
            label_store_dataset_path=Path(result.label_store_path),
            output_dir=tmp_path / "training",
            pair="BTCUSDT",
            timeframe="5m",
            train_start="2025-04-01",
            train_end="2025-04-01",
            target_horizon_minutes=5,
            feature_names=("close_return", "high_low_range", "volume"),
        )
    )

    assert len(rows) == 2
    assert rows[0].target != 0.0


def test_expected_edge_training_blocks_b_ml_when_training_allowed_false(tmp_path: Path) -> None:
    _write_rows(tmp_path / "a2")
    result = run_bml_label_factory(
        BmlLabelFactoryRequest(
            workflow_run_id="wf-training",
            a2_run_root=tmp_path / "a2",
            output_root=tmp_path / "b_ml",
            pair_list=("BTCUSDT",),
            timeframes=("5m",),
            start="2025-04-01",
            end="2025-04-01",
            label_horizons=("5m",),
            capital_buckets=(400,),
            max_candidates_per_day=2,
        )
    )
    summary_path = Path(result.label_store_path).parent / "b_ml_label_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["training_allowed"] = False
    summary_path.write_text(json.dumps(summary, sort_keys=True), encoding="utf-8")

    with pytest.raises(ValueError, match="ML_TRAINING_BLOCKED_BY_BML_LABEL_STORE_NOT_READY"):
        build_strategy_ladder_expected_edge_training_rows(
            StrategyLadderExpectedEdgeTrainingRequest(
                artifact_id="bml-artifact",
                calibration_version="test",
                label_store_dataset_path=Path(result.label_store_path),
                output_dir=tmp_path / "training",
                pair="BTCUSDT",
                timeframe="5m",
                train_start="2025-04-01",
                train_end="2025-04-01",
                target_horizon_minutes=5,
                feature_names=("close_return", "high_low_range", "volume"),
            )
        )


def test_expected_edge_training_blocks_b_ml_target_policy_mismatch(tmp_path: Path) -> None:
    _write_rows(tmp_path / "a2")
    result = run_bml_label_factory(
        BmlLabelFactoryRequest(
            workflow_run_id="wf-training",
            a2_run_root=tmp_path / "a2",
            output_root=tmp_path / "b_ml",
            pair_list=("BTCUSDT",),
            timeframes=("5m",),
            start="2025-04-01",
            end="2025-04-01",
            label_horizons=("5m",),
            capital_buckets=(400,),
            max_candidates_per_day=2,
        )
    )
    target_report_path = Path(result.label_store_path).parent / "b_ml_target_policy_report.json"
    target_report = json.loads(target_report_path.read_text(encoding="utf-8"))
    target_report["target_policy_actual"] = "WRONG_POLICY"
    target_report_path.write_text(json.dumps(target_report, sort_keys=True), encoding="utf-8")

    with pytest.raises(ValueError, match="BML_TARGET_POLICY_REPORT_MISMATCH"):
        build_strategy_ladder_expected_edge_training_rows(
            StrategyLadderExpectedEdgeTrainingRequest(
                artifact_id="bml-artifact",
                calibration_version="test",
                label_store_dataset_path=Path(result.label_store_path),
                output_dir=tmp_path / "training",
                pair="BTCUSDT",
                timeframe="5m",
                train_start="2025-04-01",
                train_end="2025-04-01",
                target_horizon_minutes=5,
                feature_names=("close_return", "high_low_range", "volume"),
            )
        )


def test_b_ml_target_policy_is_distinct_from_profitability_backtest_claim() -> None:
    assert BML_TARGET_POLICY == "BML_COUNTERFACTUAL_EXECUTION_AWARE_NET_EDGE.v1"
