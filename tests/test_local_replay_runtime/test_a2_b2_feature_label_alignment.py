from __future__ import annotations

import json
from pathlib import Path

from local_replay_runtime.b2_label_store_ml_training_audit import (
    A2_B2_FEATURE_LABEL_ALIGNMENT_REPORT_FILENAME,
    ML_TRAINING_ROW_ELIGIBILITY_REPORT_FILENAME,
    TRAINING_ROW_BLOCKED,
    write_b2_label_store_ml_training_audit_reports,
)


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )


def _dates() -> dict[str, str]:
    return {
        "train_start": "2025-01-01",
        "train_end": "2025-01-31",
        "validation_start": "2025-02-01",
        "validation_end": "2025-02-28",
        "backtest_start": "2025-03-01",
        "backtest_end": "2025-03-31",
    }


def _row(**updates: object) -> dict[str, object]:
    row: dict[str, object] = {
        "candidate_id": "cand-label",
        "engine_id": "engine_a",
        "pair": "BTCUSDT",
        "timeframe": "15m",
        "capital_bucket": 400,
        "decision_timestamp_ms": 1_735_689_600_000,
        "feature_timestamp_ms": 1_735_689_540_000,
        "raw_window_ref": "fixture://window",
        "replay_ref": "fixture://replay",
        "replay_record_id": "cand-label:400",
        "feature_vector_ref": "fixture://a2-feature",
        "executed_only_net_return": 0.001,
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
        "feature_values": {"close_return": 0.001, "volume": 4.0},
    }
    row.update(updates)
    return row


def test_candidate_id_missing_from_b1_blocks_alignment(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    _write_jsonl(
        run_dir / "fast_candidates" / "candidate_events.jsonl",
        [
            {
                "candidate_id": "cand-b1",
                "pair": "BTCUSDT",
                "timeframe": "15m",
                "engine_id": "engine_a",
            }
        ],
    )
    _write_jsonl(
        run_dir / "ml_label_store" / "strategy_ladder_replay_label_store.jsonl",
        [_row(candidate_id="cand-label")],
    )

    write_b2_label_store_ml_training_audit_reports(run_dir, **_dates())

    alignment = json.loads(
        (run_dir / "reports" / A2_B2_FEATURE_LABEL_ALIGNMENT_REPORT_FILENAME).read_text(
            encoding="utf-8"
        )
    )
    assert alignment["mismatch_count"] == 1
    assert alignment["rows"][0]["alignment_status"] == "A2_B1_B2_ALIGNMENT_BLOCKED"
    assert "B1_CANDIDATE_REF_NOT_FOUND" in alignment["rows"][0]["blocker_codes"]
    eligibility = json.loads(
        (run_dir / "reports" / ML_TRAINING_ROW_ELIGIBILITY_REPORT_FILENAME).read_text(
            encoding="utf-8"
        )
    )
    assert eligibility["rows"][0]["eligibility_status"] == TRAINING_ROW_BLOCKED


def test_pair_timeframe_engine_mismatch_is_explicit(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    _write_jsonl(
        run_dir / "fast_candidates" / "candidate_events.jsonl",
        [
            {
                "candidate_id": "cand-label",
                "pair": "ETHUSDT",
                "timeframe": "5m",
                "engine_id": "engine_b",
            }
        ],
    )
    _write_jsonl(
        run_dir / "ml_label_store" / "strategy_ladder_replay_label_store.jsonl",
        [_row()],
    )

    write_b2_label_store_ml_training_audit_reports(run_dir, **_dates())

    alignment = json.loads(
        (run_dir / "reports" / A2_B2_FEATURE_LABEL_ALIGNMENT_REPORT_FILENAME).read_text(
            encoding="utf-8"
        )
    )
    blockers = set(alignment["rows"][0]["blocker_codes"])
    assert {"PAIR_MISMATCH", "TIMEFRAME_MISMATCH", "ENGINE_ID_MISMATCH"} <= blockers


def test_missing_a2_or_b2_refs_are_not_filled_by_default(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    _write_jsonl(
        run_dir / "fast_candidates" / "candidate_events.jsonl",
        [
            {
                "candidate_id": "cand-label",
                "pair": "BTCUSDT",
                "timeframe": "15m",
                "engine_id": "engine_a",
            }
        ],
    )
    _write_jsonl(
        run_dir / "ml_label_store" / "strategy_ladder_replay_label_store.jsonl",
        [_row(feature_vector_ref="", replay_ref="", raw_window_ref="")],
    )

    write_b2_label_store_ml_training_audit_reports(run_dir, **_dates())

    alignment = json.loads(
        (run_dir / "reports" / A2_B2_FEATURE_LABEL_ALIGNMENT_REPORT_FILENAME).read_text(
            encoding="utf-8"
        )
    )
    blockers = set(alignment["rows"][0]["blocker_codes"])
    assert "A2_FEATURE_REF_MISSING" in blockers
    assert "B2_REPLAY_RECORD_REF_MISSING" in blockers
    assert "POST_OR_RAW_WINDOW_REF_MISSING" in blockers
    assert alignment["rows"][0]["a2_feature_ref"] == "MISSING_IN_ARTIFACT"
