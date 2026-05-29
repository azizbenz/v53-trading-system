from __future__ import annotations

import json
from pathlib import Path

from local_replay_runtime.b2_label_store_ml_training_audit import (
    B2_LABEL_STORE_BLOCKED_BY_TARGET_POLICY_MISMATCH,
    B2_LABEL_STORE_BLOCKED_BY_PROXY_LABELS,
    B2_LABEL_STORE_BLOCKED_BY_TRAIN_EVAL_OVERLAP,
    ML_TARGET_POLICY_CONSISTENCY_REPORT_FILENAME,
    TARGET_POLICY_MISMATCH_BLOCKED,
    TARGET_POLICY_UNSATISFIED_FOR_TRAINING,
    write_b2_label_store_ml_training_audit_reports,
)
from local_replay_runtime.strategy_ladder_expected_edge_training import (
    STRATEGY_LADDER_EXPECTED_EDGE_TARGET_POLICY,
)


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )


def _non_overlap_dates() -> dict[str, str]:
    return {
        "train_start": "2025-01-01",
        "train_end": "2025-01-31",
        "validation_start": "2025-02-01",
        "validation_end": "2025-02-28",
        "backtest_start": "2025-03-01",
        "backtest_end": "2025-03-31",
    }


def _seed(tmp_path: Path, row: dict[str, object]) -> Path:
    run_dir = tmp_path / "run"
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
        [row],
    )
    return run_dir


def _base_row(**updates: object) -> dict[str, object]:
    row: dict[str, object] = {
        "candidate_id": "cand-1",
        "engine_id": "engine_a",
        "pair": "BTCUSDT",
        "timeframe": "15m",
        "capital_bucket": 400,
        "decision_timestamp_ms": 1_735_689_600_000,
        "feature_timestamp_ms": 1_735_689_540_000,
        "raw_window_ref": "fixture://window",
        "replay_ref": "fixture://replay",
        "replay_record_id": "cand-1:400",
        "feature_vector_ref": "fixture://a2-feature",
        "executed_only_net_return": 0.001,
        "expected_ce_net": None,
        "label_net_positive": True,
        "label_break_even_cleared": True,
        "label_survived_mae": True,
        "mfe_bps": 10.0,
        "mae_bps": -3.0,
        "label_quality_status": "LABEL_QUALITY_PROMOTION_GRADE_CANDIDATE",
        "replay_quality_status": "REPLAY_READY",
        "execution_fidelity_status": "EXECUTION_FIDELITY_READY",
        "entry_reference_status": "ENTRY_REFERENCE_EXECUTED_FILL_MEASURED",
        "mfe_mae_status": "MFE_MAE_AVAILABLE",
        "proxy_execution_label_flag": False,
        "replay_grounded_label_flag": True,
        "feature_values": {"close_return": 0.001, "volume": 3.0},
    }
    row.update(updates)
    return row


def test_declared_execution_policy_marks_proxy_target_unsatisfied_not_mismatched(tmp_path: Path) -> None:
    run_dir = _seed(
        tmp_path,
        _base_row(
            executed_only_net_return=None,
            expected_ce_net=0.0004,
            proxy_execution_label_flag=True,
            replay_grounded_label_flag=False,
            execution_fidelity_status="EXECUTION_FIDELITY_PROXY_EXECUTION",
            label_quality_status="LABEL_QUALITY_RESEARCH_ONLY",
        ),
    )

    report = write_b2_label_store_ml_training_audit_reports(
        run_dir,
        target_policy_declared=STRATEGY_LADDER_EXPECTED_EDGE_TARGET_POLICY,
        **_non_overlap_dates(),
    )

    assert report["final_verdict"] == B2_LABEL_STORE_BLOCKED_BY_PROXY_LABELS
    assert report["target_policy_mismatch_count"] == 0
    assert report["target_policy_unsatisfied_count"] == 1
    target_report = json.loads(
        (run_dir / "reports" / ML_TARGET_POLICY_CONSISTENCY_REPORT_FILENAME).read_text(
            encoding="utf-8"
        )
    )
    assert target_report["rows"][0]["status"] == TARGET_POLICY_UNSATISFIED_FOR_TRAINING
    assert target_report["rows"][0]["target_policy_actual"] == "B2_REPLAY_EXPECTED_CE_NET_PROXY"


def test_declared_execution_policy_still_blocks_true_foreign_target(tmp_path: Path) -> None:
    run_dir = _seed(
        tmp_path,
        _base_row(
            executed_only_net_return=None,
            expected_ce_net=None,
            label_forward_return_h1=7.0,
            label_forward_return_h5=None,
            label_forward_return_h10=None,
            label_net_positive=None,
            label_break_even_cleared=None,
            label_survived_mae=None,
            mfe_bps=None,
            mae_bps=None,
            replay_grounded_label_flag=False,
            label_quality_status="LABEL_QUALITY_RESEARCH_ONLY",
        ),
    )

    report = write_b2_label_store_ml_training_audit_reports(
        run_dir,
        target_policy_declared=STRATEGY_LADDER_EXPECTED_EDGE_TARGET_POLICY,
        **_non_overlap_dates(),
    )

    assert report["final_verdict"] == B2_LABEL_STORE_BLOCKED_BY_TARGET_POLICY_MISMATCH
    assert report["target_policy_mismatch_count"] == 1
    target_report = json.loads(
        (run_dir / "reports" / ML_TARGET_POLICY_CONSISTENCY_REPORT_FILENAME).read_text(
            encoding="utf-8"
        )
    )
    assert target_report["rows"][0]["status"] == TARGET_POLICY_MISMATCH_BLOCKED
    assert target_report["rows"][0]["target_policy_actual"] == "ABS_FORWARD_CLOSE_RETURN"


def test_abs_forward_close_return_policy_can_match_but_not_promote_expected_edge(tmp_path: Path) -> None:
    run_dir = _seed(
        tmp_path,
        _base_row(
            executed_only_net_return=None,
            expected_ce_net=None,
            label_forward_return_h1=7.0,
            label_forward_return_h5=None,
            label_forward_return_h10=None,
            label_net_positive=None,
            label_break_even_cleared=None,
            label_survived_mae=None,
            mfe_bps=None,
            mae_bps=None,
            replay_grounded_label_flag=False,
            label_quality_status="LABEL_QUALITY_RESEARCH_ONLY",
        ),
    )

    report = write_b2_label_store_ml_training_audit_reports(
        run_dir,
        target_policy_declared="ABS_FORWARD_CLOSE_RETURN",
        **_non_overlap_dates(),
    )

    target_report = json.loads(
        (run_dir / "reports" / ML_TARGET_POLICY_CONSISTENCY_REPORT_FILENAME).read_text(
            encoding="utf-8"
        )
    )
    assert target_report["target_policy_mismatch_count"] == 0
    assert target_report["target_policy_actual"] == "ABS_FORWARD_CLOSE_RETURN"
    assert report["scientifically_valid_for_promotion"] is False


def test_train_eval_overlap_blocks_even_clean_label_rows(tmp_path: Path) -> None:
    run_dir = _seed(tmp_path, _base_row())

    report = write_b2_label_store_ml_training_audit_reports(
        run_dir,
        train_start="2025-01-01",
        train_end="2025-03-05",
        validation_start="2025-03-06",
        validation_end="2025-03-10",
        backtest_start="2025-03-01",
        backtest_end="2025-03-31",
    )

    assert report["final_verdict"] == B2_LABEL_STORE_BLOCKED_BY_TRAIN_EVAL_OVERLAP
    assert report["scientifically_valid_for_training"] is False
    assert report["train_eval_overlap_status"] == "TRAIN_EVAL_OVERLAP_BLOCKED"
