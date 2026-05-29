from __future__ import annotations

import json
from pathlib import Path

from local_replay_runtime.backtest_backbone_parity_audit import (
    B2_COST_BLOCKER_COMPONENT_AUDIT_FILENAME,
    BACKTEST_BACKBONE_PARITY_FINAL_REPORT_FILENAME,
    COUNT_SEMANTICS_DEEP_AUDIT_FILENAME,
    ENGINE_A_EXECUTED_CANDIDATE_AUTOPSY_FILENAME,
    ENGINE_NATIVE_RUNNER_INVOCATION_AUDIT_FILENAME,
    EXECUTED_RECORD_INVARIANT_REPORT_FILENAME,
    REASON_CODE_TAXONOMY_AUDIT_FILENAME,
    write_backtest_backbone_parity_audit_reports,
)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _build_bucket_row(candidate_id: str, bucket: int) -> dict:
    return {
        "candidate_id": candidate_id,
        "engine_id": "engine_a",
        "capital_bucket": bucket,
        "execution_state": "executed",
        "book_depth_source_status": "BOOK_DEPTH20_AVAILABLE",
        "fill_realism_status": "FILL_REALISM_SHADOW_MEASURED",
        "fee_source_status": "FEE_SOURCE_EXCHANGE_METADATA",
        "cost_parity_status": "REPLAY_LIVE_COST_PARITY_BLOCKED",
        "forward_return_h1": -67.75,
        "mfe_bps": 0.0,
        "mae_bps": -99.36,
        "executed_only_net_return": -0.001151,
        "reason_codes": [
            "ENGINE_NATIVE_RUNNER_NOT_INVOKED",
            "B2_COST_MEASUREMENT_BLOCKED",
            "engine_a.emit.valid",
            "engine_a.cost.feasible",
        ],
        "parity_payload": {
            "measured_spread_report": {"status": "SPREAD_MEASURED_FROM_BOOK"},
            "measured_slippage_report": {"status": "SLIPPAGE_ESTIMATED_FROM_DEPTH20"},
            "adverse_selection_report": {"status": "ADVERSE_SELECTION_PROXY"},
            "fill_realism_report": {"status": "FILL_REALISM_PARTIAL_REPLAY"},
            "partial_fill_status": "FULL_DEPTH_FILL",
        },
        "dtr_record": {"primary_reason": "selected"},
    }


def _build_run(tmp_path: Path) -> Path:
    run_dir = tmp_path / "strategy_ladder_workflow-test"
    candidate_id = "ae5c57f5197f33fcab27b346"
    _write_json(
        run_dir / "reports" / "strategy_ladder_summary.json",
        {
            "run_id": "strategy_ladder_workflow-test",
            "candidate_count": 200,
            "executed_trade_count": 4,
        },
    )
    _write_jsonl(
        run_dir / "fast_candidates" / "candidate_events.jsonl",
        [
            {
                "candidate_id": candidate_id,
                "engine_id": "engine_a",
                "compatibility_payload": {
                    "engine_native_status": "ENGINE_NATIVE_RUNNER_INVOKED",
                    "engine_native_decision": "TRADE",
                },
            }
        ],
    )
    for bucket in (400, 500, 1500, 4000):
        _write_json(
            run_dir / "detailed_replay" / "by_bucket" / str(bucket) / f"{candidate_id}.json",
            _build_bucket_row(candidate_id, bucket),
        )
    return run_dir


def test_backbone_parity_audit_reports_bucket_expansion_and_no_logic_change(tmp_path: Path) -> None:
    run_dir = _build_run(tmp_path)

    before = [
        _read_json(path)
        for path in sorted((run_dir / "detailed_replay" / "by_bucket").rglob("*.json"))
    ]
    written = write_backtest_backbone_parity_audit_reports(
        run_dir,
        repo_root=Path.cwd(),
        docs_dir=tmp_path / "docs",
    )
    after = [
        _read_json(path)
        for path in sorted((run_dir / "detailed_replay" / "by_bucket").rglob("*.json"))
    ]

    assert before == after
    assert BACKTEST_BACKBONE_PARITY_FINAL_REPORT_FILENAME in written

    counts = _read_json(run_dir / "reports" / COUNT_SEMANTICS_DEEP_AUDIT_FILENAME)
    assert counts["independent_executed_signal_count"] == 1
    assert counts["executed_bucket_record_count"] == 4
    assert counts["verdict"] == "COUNT_SEMANTICS_BUCKET_EXPANSION_CONFUSING"

    invariant = _read_json(run_dir / "reports" / EXECUTED_RECORD_INVARIANT_REPORT_FILENAME)
    assert invariant["status"] == "EXECUTED_RECORD_INVARIANT_VIOLATED"
    assert invariant["violation_count"] == 4


def test_reason_codes_and_invocation_are_classified_as_diagnostic_not_bypassed(tmp_path: Path) -> None:
    run_dir = _build_run(tmp_path)

    write_backtest_backbone_parity_audit_reports(
        run_dir,
        repo_root=Path.cwd(),
        docs_dir=tmp_path / "docs",
    )

    taxonomy = _read_json(run_dir / "reports" / REASON_CODE_TAXONOMY_AUDIT_FILENAME)
    assert taxonomy["verdict"] == "REASON_CODE_PATCH_REQUIRED"
    first_row = taxonomy["rows"][0]
    assert "ENGINE_NATIVE_RUNNER_NOT_INVOKED" in first_row["previous_stage_reason_codes"]
    assert "B2_COST_MEASUREMENT_BLOCKED" in first_row["previous_stage_reason_codes"]

    invocation = _read_json(run_dir / "reports" / ENGINE_NATIVE_RUNNER_INVOCATION_AUDIT_FILENAME)
    assert invocation["verdict"] == "ENGINE_NATIVE_RUNNER_NOT_INVOKED_MISNAMED_DIAGNOSTIC"
    assert invocation["rows"][0]["recommended_reclassification"] == "B2_ENGINE_NATIVE_REEVALUATION_NOT_REQUESTED"


def test_cost_components_and_engine_a_autopsy_are_reported_without_promotion(tmp_path: Path) -> None:
    run_dir = _build_run(tmp_path)

    write_backtest_backbone_parity_audit_reports(
        run_dir,
        repo_root=Path.cwd(),
        docs_dir=tmp_path / "docs",
    )

    cost = _read_json(run_dir / "reports" / B2_COST_BLOCKER_COMPONENT_AUDIT_FILENAME)
    first = cost["rows"][0]
    assert first["final_cost_truth_status"] == "PARTIAL_MEASURED"
    assert "B2_COST_BLOCKED_BY_ADVERSE_SELECTION_PROXY" in first["cost_blocker_components"]
    assert "B2_COST_GOVERNANCE_BLOCKED_PARTIAL_MEASUREMENT" in first["cost_blocker_components"]

    autopsy = _read_json(run_dir / "reports" / ENGINE_A_EXECUTED_CANDIDATE_AUTOPSY_FILENAME)
    assert autopsy["distinct_signal_count"] == 1
    assert autopsy["bucket_execution_count"] == 4
    assert "BUCKET_EXPANDED_SINGLE_SIGNAL" in autopsy["verdict"]
    assert "INCONSISTENT_RECORD" in autopsy["verdict"]
