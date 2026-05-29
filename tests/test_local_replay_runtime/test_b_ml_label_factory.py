from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from local_replay_runtime.strategy_ladder_b_ml_label_factory import (
    BML_BLOCKED_LABEL_LEAKAGE,
    BML_BLOCKED_TRAIN_EVAL_OVERLAP,
    BML_READY_GOVERNED,
    LABEL_BLOCKED_BY_MISSING_POST_WINDOW,
    TRAINING_ROW_BLOCKED,
    TRAINING_ROW_ELIGIBLE,
    BmlLabelFactoryRequest,
    BmlLabelStoreRow,
    run_bml_label_factory,
)


def _ts(raw_value: str) -> int:
    parsed = datetime.fromisoformat(raw_value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return int(parsed.astimezone(UTC).timestamp() * 1000)


def _gold_row(timestamp_ms: int, close_price: float) -> dict[str, object]:
    return {
        "timestamp_ms": timestamp_ms,
        "pair": "BTCUSDT",
        "timeframe": "5m",
        "available_at_timestamp_ms": timestamp_ms,
        "close_price": close_price,
        "feature_values": {
            "close_return": 0.001,
            "high_low_range": 0.002,
            "volume": 100.0,
            "spread_bps": 1.0,
            "book_depth_levels": 20,
            "vpin": 0.12,
            "cumulative_ofi": 0.2,
            "queue_pressure": 0.3,
            "realized_vol_current": 0.01,
        },
        "spread_bps": 1.0,
        "spread_provenance": "MEASURED_FROM_BOOK_SNAPSHOT",
        "slippage_bps": 0.4,
        "slippage_provenance": "MEASURED_FROM_DEPTH20_BOOK_WALK",
        "latency_penalty_bps": 0.1,
        "taker_fee_rate": 0.001,
        "book_depth_levels": 20,
        "book_depth_source_status": "BOOK_DEPTH20_AVAILABLE",
        "feature_truth_boundary_status": "FEATURE_EX_ANTE_AVAILABLE_AT_DECISION",
        "feature_usage_policy": "A2_GOLD_EX_ANTE_FEATURES_ONLY_NOT_EXECUTION_TRUTH",
        "cost_feature_truth_status": (
            "A2_COST_FEATURES_MEASURED_EX_ANTE_NOT_EXECUTION_LABEL_TRUTH"
        ),
        "feature_sources_used": ["klines", "orderbook", "trades", "metadata"],
    }


def _write_a2_gold(root: Path, rows: list[dict[str, object]], *, pair: str = "BTCUSDT") -> Path:
    path = root / "gold" / "features_5m" / pair / "2025" / "04" / "features.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )
    return path


def test_b_ml_label_factory_builds_eligible_ex_ante_microstructure_rows(tmp_path: Path) -> None:
    a2_root = tmp_path / "a2"
    output_root = tmp_path / "b_ml"
    _write_a2_gold(
        a2_root,
        [
            _gold_row(_ts("2025-04-01T00:00:00Z"), 100.0),
            _gold_row(_ts("2025-04-01T00:05:00Z"), 101.0),
        ],
    )

    result = run_bml_label_factory(
        BmlLabelFactoryRequest(
            workflow_run_id="wf-bml",
            a2_run_root=a2_root,
            output_root=output_root,
            pair_list=("BTCUSDT",),
            timeframes=("5m",),
            start="2025-04-01",
            end="2025-04-01",
            label_horizons=("5m",),
            capital_buckets=(400,),
            feature_names=(
                "close_return",
                "high_low_range",
                "volume",
                "spread_bps",
                "book_depth_levels",
                "vpin",
                "cumulative_ofi",
                "queue_pressure",
                "realized_vol_current",
            ),
            max_candidates_per_day=1,
        )
    )

    assert result.final_verdict == BML_READY_GOVERNED
    assert result.training_row_eligible_count == 1
    payload = json.loads(Path(result.label_store_path).read_text(encoding="utf-8").splitlines()[0])
    assert payload["training_row_status"] == TRAINING_ROW_ELIGIBLE
    assert payload["feature_values"]["queue_pressure"] == pytest.approx(0.3)
    assert payload["feature_truth_boundary_status"] == "FEATURE_EX_ANTE_AVAILABLE_AT_DECISION"
    assert payload["feature_usage_policy"] == "A2_GOLD_EX_ANTE_FEATURES_ONLY_NOT_EXECUTION_TRUTH"
    assert (
        payload["cost_feature_truth_status"]
        == "A2_COST_FEATURES_MEASURED_EX_ANTE_NOT_EXECUTION_LABEL_TRUTH"
    )
    assert payload["forward_return_bps"] == pytest.approx(100.0)
    assert payload["label_value"] == pytest.approx(88.5)
    assert payload["promotion_allowed"] is False
    feature_matrix = (output_root / "features" / "b_ml_feature_matrix.jsonl").read_text(
        encoding="utf-8"
    )
    assert "feature_truth_boundary_status" in feature_matrix
    truth_report = json.loads(
        (output_root / "reports" / "b_ml_feature_label_truth_boundary_report.json").read_text(
            encoding="utf-8"
        )
    )
    assert truth_report["promotion_allowed"] is False
    assert truth_report["feature_to_label_truth_promotion_blocked_count"] == 1
    assert (output_root / "windows" / "raw_window_index.jsonl").read_text(encoding="utf-8").strip()
    assert (output_root / "windows" / "post_window_index.jsonl").read_text(encoding="utf-8").strip()
    tabular_index = json.loads(
        (output_root / "reports" / "b_ml_tabular_artifact_index.json").read_text(
            encoding="utf-8"
        )
    )
    assert set(tabular_index["artifacts"]) >= {
        "b_ml_label_store",
        "b_ml_candidate_events",
        "b_ml_feature_matrix",
        "raw_window_index",
        "post_window_index",
    }
    assert (
        tabular_index["artifacts"]["b_ml_label_store"]["status"]
        in {"TABULAR_MIRROR_PARQUET_READY", "TABULAR_MIRROR_COLUMNAR_JSON_READY"}
    )
    run_summary = json.loads((output_root / "b_ml_run_summary.json").read_text(encoding="utf-8"))
    assert "tabular_artifact_index_path" in run_summary
    event_log = (output_root / "reports" / "b_ml_event_log.jsonl").read_text(encoding="utf-8")
    assert "b_ml.final_verdict" in event_log


def test_b_ml_missing_post_window_blocks_training_row(tmp_path: Path) -> None:
    a2_root = tmp_path / "a2"
    output_root = tmp_path / "b_ml"
    _write_a2_gold(a2_root, [_gold_row(_ts("2025-04-01T00:00:00Z"), 100.0)])

    result = run_bml_label_factory(
        BmlLabelFactoryRequest(
            workflow_run_id="wf-bml",
            a2_run_root=a2_root,
            output_root=output_root,
            pair_list=("BTCUSDT",),
            timeframes=("5m",),
            start="2025-04-01",
            end="2025-04-01",
            label_horizons=("5m",),
            capital_buckets=(400,),
        )
    )

    payload = json.loads(Path(result.label_store_path).read_text(encoding="utf-8").splitlines()[0])
    assert payload["post_window_status"] == LABEL_BLOCKED_BY_MISSING_POST_WINDOW
    assert payload["training_row_status"] == TRAINING_ROW_BLOCKED


def test_b_ml_schema_rejects_label_outcome_feature_inputs() -> None:
    with pytest.raises(ValueError, match="label/outcome"):
        BmlLabelStoreRow(
            candidate_id="bad",
            candidate_source="TEST",
            pair="BTCUSDT",
            timeframe="5m",
            decision_timestamp_ms=_ts("2025-04-01T00:00:00Z"),
            horizon="5m",
            capital_bucket=400,
            feature_values={"mfe_bps": 1.0},
            entry_reference_price=100.0,
            post_window_status="POST_WINDOW_READY",
        )


def test_b_ml_blocks_feature_timestamp_after_decision(tmp_path: Path) -> None:
    a2_root = tmp_path / "a2"
    output_root = tmp_path / "b_ml"
    decision_ts = _ts("2025-04-01T00:00:00Z")
    future_ts = _ts("2025-04-01T00:05:00Z")
    leaking_row = _gold_row(decision_ts, 100.0)
    leaking_row["available_at_timestamp_ms"] = future_ts
    _write_a2_gold(
        a2_root,
        [
            leaking_row,
            _gold_row(future_ts, 101.0),
        ],
    )

    result = run_bml_label_factory(
        BmlLabelFactoryRequest(
            workflow_run_id="wf-bml",
            a2_run_root=a2_root,
            output_root=output_root,
            pair_list=("BTCUSDT",),
            timeframes=("5m",),
            start="2025-04-01",
            end="2025-04-01",
            label_horizons=("5m",),
            capital_buckets=(400,),
            max_candidates_per_day=1,
        )
    )

    assert result.final_verdict == BML_BLOCKED_LABEL_LEAKAGE
    payload = json.loads(Path(result.label_store_path).read_text(encoding="utf-8").splitlines()[0])
    assert payload["training_row_status"] == TRAINING_ROW_BLOCKED
    assert any(
        item.startswith("FEATURE_POST_DECISION_LEAKAGE")
        for item in payload["warnings"]
    )


def test_b_ml_blocks_train_eval_overlap(tmp_path: Path) -> None:
    a2_root = tmp_path / "a2"
    output_root = tmp_path / "b_ml"
    _write_a2_gold(
        a2_root,
        [
            _gold_row(_ts("2025-04-01T00:00:00Z"), 100.0),
            _gold_row(_ts("2025-04-01T00:05:00Z"), 101.0),
        ],
    )

    result = run_bml_label_factory(
        BmlLabelFactoryRequest(
            workflow_run_id="wf-bml",
            a2_run_root=a2_root,
            output_root=output_root,
            pair_list=("BTCUSDT",),
            timeframes=("5m",),
            start="2025-04-01",
            end="2025-04-01",
            train_start="2025-04-01",
            train_end="2025-04-02",
            allowed_backtest_start_after="2025-04-02",
            label_horizons=("5m",),
            capital_buckets=(400,),
            max_candidates_per_day=1,
        )
    )

    assert result.final_verdict == BML_BLOCKED_TRAIN_EVAL_OVERLAP
    audit = json.loads((output_root / "b_ml_run_summary.json").read_text(encoding="utf-8"))
    assert audit["train_eval_overlap_blocked"] is True
