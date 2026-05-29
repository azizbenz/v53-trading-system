from __future__ import annotations

import json
from pathlib import Path

from local_replay_runtime.b2_label_store_ml_training_audit import (
    B2_LABEL_STORE_BLOCKED_BY_LABEL_LEAKAGE,
    B2_LABEL_STORE_BLOCKED_BY_MISSING_POST_WINDOW,
    B2_LABEL_STORE_ML_TRAINING_AUDIT_FILENAME,
    B2_LABEL_STORE_TRAINING_READY,
    FEATURE_POST_DECISION_LEAKAGE_BLOCKED,
    LABEL_BLOCKED_BY_MISSING_POST_WINDOW,
    ML_FEATURE_LABEL_LEAKAGE_REPORT_FILENAME,
    ML_TRAINING_LABEL_FIDELITY_REPORT_FILENAME,
    ML_TRAINING_ROW_ELIGIBILITY_REPORT_FILENAME,
    TRAINING_ROW_BLOCKED,
    TRAINING_ROW_ELIGIBLE,
    write_b2_label_store_ml_training_audit_reports,
)


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )


def _training_dates() -> dict[str, str]:
    return {
        "train_start": "2025-01-01",
        "train_end": "2025-01-31",
        "validation_start": "2025-02-01",
        "validation_end": "2025-02-28",
        "backtest_start": "2025-03-01",
        "backtest_end": "2025-03-31",
    }


def _base_row(**updates: object) -> dict[str, object]:
    row: dict[str, object] = {
        "candidate_id": "cand-1",
        "engine_id": "engine_a",
        "pair": "BTCUSDT",
        "timeframe": "15m",
        "capital_bucket": 400,
        "decision_timestamp_ms": 1_735_689_600_000,
        "feature_timestamp_ms": 1_735_689_540_000,
        "raw_window_ref": "fixture://raw-window",
        "replay_ref": "fixture://replay",
        "replay_record_id": "cand-1:400",
        "feature_vector_ref": "fixture://a2-feature",
        "executed_only_net_return": 0.0012,
        "expected_ce_net": None,
        "label_net_positive": True,
        "label_break_even_cleared": True,
        "label_survived_mae": True,
        "label_forward_return_h1": 6.0,
        "mfe_bps": 12.0,
        "mae_bps": -4.0,
        "evidence_class": "REPLAY_EXECUTED_ONLY_NET_RETURN",
        "label_quality_status": "LABEL_QUALITY_PROMOTION_GRADE_CANDIDATE",
        "replay_grounded_status": "REPLAY_GROUNDED_PROMOTION_GRADE_CANDIDATE",
        "replay_quality_status": "REPLAY_READY",
        "execution_fidelity_status": "EXECUTION_FIDELITY_READY",
        "entry_reference_status": "ENTRY_REFERENCE_EXECUTED_FILL_MEASURED",
        "mfe_mae_status": "MFE_MAE_AVAILABLE",
        "proxy_execution_label_flag": False,
        "replay_grounded_label_flag": True,
        "feature_values": {
            "close_return": 0.001,
            "high_low_range": 0.002,
            "volume": 10.0,
        },
    }
    row.update(updates)
    return row


def _seed_run(tmp_path: Path, rows: list[dict[str, object]]) -> Path:
    run_dir = tmp_path / "b2_run"
    _write_jsonl(
        run_dir / "fast_candidates" / "candidate_events.jsonl",
        [
            {
                "candidate_id": "cand-1",
                "pair": "BTCUSDT",
                "timeframe": "15m",
                "engine_id": "engine_a",
            }
        ],
    )
    _write_jsonl(
        run_dir / "ml_label_store" / "strategy_ladder_replay_label_store.jsonl",
        rows,
    )
    return run_dir


def test_training_ready_row_requires_clean_ex_ante_features_and_grounded_label(tmp_path: Path) -> None:
    run_dir = _seed_run(tmp_path, [_base_row()])

    report = write_b2_label_store_ml_training_audit_reports(run_dir, **_training_dates())

    assert report["final_verdict"] == B2_LABEL_STORE_TRAINING_READY
    assert report["training_row_eligible_count"] == 1
    assert report["scientifically_valid_for_training"] is True
    eligibility = json.loads(
        (run_dir / "reports" / ML_TRAINING_ROW_ELIGIBILITY_REPORT_FILENAME).read_text(
            encoding="utf-8"
        )
    )
    assert eligibility["rows"][0]["eligibility_status"] == TRAINING_ROW_ELIGIBLE


def test_feature_timestamp_after_decision_is_blocked(tmp_path: Path) -> None:
    run_dir = _seed_run(
        tmp_path,
        [_base_row(feature_timestamp_ms=1_735_689_700_000)],
    )

    report = write_b2_label_store_ml_training_audit_reports(run_dir, **_training_dates())

    assert report["final_verdict"] == B2_LABEL_STORE_BLOCKED_BY_LABEL_LEAKAGE
    assert report["feature_leakage_count"] == 3
    leakage = json.loads(
        (run_dir / "reports" / ML_FEATURE_LABEL_LEAKAGE_REPORT_FILENAME).read_text(
            encoding="utf-8"
        )
    )
    assert all(
        row["status"] == FEATURE_POST_DECISION_LEAKAGE_BLOCKED
        for row in leakage["rows"]
    )


def test_mfe_bps_as_feature_is_blocked_but_mfe_label_is_reported(tmp_path: Path) -> None:
    row = _base_row(
        feature_values={
            "close_return": 0.001,
            "mfe_bps": 12.0,
        }
    )
    run_dir = _seed_run(tmp_path, [row])

    report = write_b2_label_store_ml_training_audit_reports(run_dir, **_training_dates())

    assert report["final_verdict"] == B2_LABEL_STORE_BLOCKED_BY_LABEL_LEAKAGE
    leakage = json.loads(
        (run_dir / "reports" / ML_FEATURE_LABEL_LEAKAGE_REPORT_FILENAME).read_text(
            encoding="utf-8"
        )
    )
    assert any(
        item["feature_name"] == "mfe_bps"
        and item["status"] == FEATURE_POST_DECISION_LEAKAGE_BLOCKED
        for item in leakage["rows"]
    )
    fidelity = json.loads(
        (run_dir / "reports" / ML_TRAINING_LABEL_FIDELITY_REPORT_FILENAME).read_text(
            encoding="utf-8"
        )
    )
    assert "mfe_bps" in fidelity["rows"][0]["labels_present"]


def test_missing_post_window_blocks_row_without_fabricating_label(tmp_path: Path) -> None:
    row = _base_row(
        executed_only_net_return=None,
        expected_ce_net=None,
        label_net_positive=None,
        label_break_even_cleared=None,
        label_survived_mae=None,
        label_forward_return_h1=None,
        mfe_bps=None,
        mae_bps=None,
        replay_grounded_label_flag=False,
        label_quality_status="LABEL_QUALITY_BLOCKED",
    )
    run_dir = _seed_run(tmp_path, [row])

    report = write_b2_label_store_ml_training_audit_reports(run_dir, **_training_dates())

    assert report["final_verdict"] == B2_LABEL_STORE_BLOCKED_BY_MISSING_POST_WINDOW
    assert report["missing_post_window_count"] == 1
    fidelity = json.loads(
        (run_dir / "reports" / ML_TRAINING_LABEL_FIDELITY_REPORT_FILENAME).read_text(
            encoding="utf-8"
        )
    )
    assert fidelity["rows"][0]["label_truth_status"] == LABEL_BLOCKED_BY_MISSING_POST_WINDOW
    eligibility = json.loads(
        (run_dir / "reports" / ML_TRAINING_ROW_ELIGIBILITY_REPORT_FILENAME).read_text(
            encoding="utf-8"
        )
    )
    assert eligibility["rows"][0]["eligibility_status"] == TRAINING_ROW_BLOCKED


def test_audit_does_not_modify_existing_replay_artifact(tmp_path: Path) -> None:
    run_dir = _seed_run(tmp_path, [_base_row()])
    replay_path = run_dir / "detailed_replay" / "cand-1.json"
    replay_path.parent.mkdir(parents=True, exist_ok=True)
    replay_path.write_text('{"candidate_id":"cand-1"}', encoding="utf-8")
    before = replay_path.read_text(encoding="utf-8")

    write_b2_label_store_ml_training_audit_reports(run_dir, **_training_dates())

    assert replay_path.read_text(encoding="utf-8") == before
    assert (run_dir / "reports" / B2_LABEL_STORE_ML_TRAINING_AUDIT_FILENAME).is_file()
