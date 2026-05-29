from __future__ import annotations

import json
from pathlib import Path

import pytest

from local_replay_runtime.no_shadow_threshold_challenge import (
    NO_SHADOW_THRESHOLD_CHALLENGE_FILENAME,
    OFFLINE_MODE,
    TEST_MODE,
    build_no_shadow_threshold_challenge_payloads,
    write_no_shadow_threshold_challenge_reports,
)
from local_replay_runtime.engine_math_canary_audit import (
    build_engine_threshold_boundary_report,
)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )


def _read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _seed_threshold_run(run_dir: Path, *, include_metrics: bool = True) -> None:
    _write_json(
        run_dir / "reports" / "strategy_ladder_summary.json",
        {
            "run_id": run_dir.name,
            "candidate_count": 1,
            "selected_count": 0,
            "executed_trade_count": 0,
            "blocker_codes": ["NO_EXECUTED_TRADES", "EXPECTED_EDGE_PROXY_BLOCKED"],
            "execution_fidelity_gap_codes": ["ADVERSE_SELECTION_PROXY"],
            "adverse_selection_source": "REPLAY_PROXY",
            "expected_edge_proxy_count": 1,
        },
    )
    _write_json(
        run_dir / "run_manifest.json",
        {"run_id": run_dir.name, "start": "2025-04-29", "end": "2025-05-01"},
    )
    compatibility_payload: dict[str, object] = {
        "hard_block_reasons": ["EXPECTED_EDGE_PROXY_BLOCKED"],
        "expected_edge_truth_status": "EXPECTED_EDGE_PROXY_BLOCKED",
    }
    if include_metrics:
        compatibility_payload.update(
            {
                "direction_score": 0.18,
                "structure_score": 0.58,
                "expected_gain": 0.0002,
                "expected_cost": 0.0001,
                "ce_expected": 0.00005,
            }
        )
    _write_jsonl(
        run_dir / "fast_candidates" / "candidate_events.jsonl",
        [
            {
                "candidate_id": "c1",
                "pair": "BTCUSDT",
                "timeframe": "1m",
                "engine_id": "engine_a",
                "strategy_id": "strategy_a",
                "timestamp_ms": 1_746_000_000_000,
                "preliminary_reason_codes": ["EXPECTED_EDGE_PROXY_BLOCKED"],
                "compatibility_payload": compatibility_payload,
            }
        ],
    )
    _write_json(
        run_dir / "detailed_replay" / "by_bucket" / "400" / "c1.json",
        {
            "candidate_id": "c1",
            "pair": "BTCUSDT",
            "engine_id": "engine_a",
            "strategy_id": "strategy_a",
            "capital_bucket": 400,
            "timestamp_ms": 1_746_000_000_000,
            "execution_state": "hard_blocked",
            "reason_codes": ["EXPECTED_EDGE_PROXY_BLOCKED"],
            "fill_realism_status": "FILL_REALISM_NOT_PROVEN",
        },
    )
    _write_json(
        run_dir / "reports" / "cost_fill_realism_report.json",
        {
            "status": "COST_FILL_REALISM_PARTIAL",
            "proxy_contamination_present": True,
        },
    )


def _engine_a_threshold(payloads: dict[str, object], threshold_name: str) -> dict[str, object]:
    report = payloads["threshold_sweep_by_engine.json"]
    assert isinstance(report, dict)
    engines = report["engines"]
    assert isinstance(engines, dict)
    engine_a = engines["engine_a"]
    assert isinstance(engine_a, dict)
    for row in engine_a["thresholds"]:
        if row["threshold_name"] == threshold_name:
            return row
    raise AssertionError(f"missing engine_a threshold {threshold_name}")


def test_no_shadow_builder_preserves_real_decision_counts_and_artifacts(
    repo_tmp_path: Path,
) -> None:
    run_dir = repo_tmp_path / "backtest_strategy_ladder" / "run-threshold"
    _seed_threshold_run(run_dir)
    summary_path = run_dir / "reports" / "strategy_ladder_summary.json"
    summary_before = summary_path.read_text(encoding="utf-8")
    boundary_before = build_engine_threshold_boundary_report()["rows"]
    engine_file = Path("src/engines/engine_a/engine_a_runner.py")
    engine_before = engine_file.read_text(encoding="utf-8")

    refs = write_no_shadow_threshold_challenge_reports(
        run_dir,
        docs_audit_dir=repo_tmp_path / "docs" / "audit",
    )

    assert summary_path.read_text(encoding="utf-8") == summary_before
    assert engine_file.read_text(encoding="utf-8") == engine_before
    assert build_engine_threshold_boundary_report()["rows"] == boundary_before
    assert NO_SHADOW_THRESHOLD_CHALLENGE_FILENAME in refs

    report = _read_json(run_dir / "reports" / NO_SHADOW_THRESHOLD_CHALLENGE_FILENAME)
    assert report["mode"] == OFFLINE_MODE
    assert report["shadow_used"] is False
    assert report["micro_live_used"] is False
    assert report["orders_sent"] is False
    assert report["trading_decisions_modified"] is False
    assert report["selected_count_real"] == 0
    assert report["executed_count_real"] == 0
    assert report["profitability_claim_allowed"] is False
    assert (repo_tmp_path / "docs" / "audit" / "NO_SHADOW_THRESHOLD_CHALLENGE_REPORT.md").is_file()


def test_mode_a_changes_only_counterfactual_native_pass_count(
    repo_tmp_path: Path,
) -> None:
    run_dir = repo_tmp_path / "backtest_strategy_ladder" / "run-mode-a"
    _seed_threshold_run(run_dir)

    payloads = build_no_shadow_threshold_challenge_payloads(run_dir)

    min_direction = _engine_a_threshold(payloads, "min_direction")
    rows = {row["tested_value"]: row for row in min_direction["sweeps"]}
    assert rows[0.20]["native_pass_count"] == 0
    assert rows[0.15]["native_pass_count"] == 1

    report = payloads[NO_SHADOW_THRESHOLD_CHALLENGE_FILENAME]
    assert isinstance(report, dict)
    assert report["selected_count_real"] == 0
    assert report["executed_count_real"] == 0
    assert report["trading_decisions_modified"] is False


def test_mode_b_preserves_global_proxy_and_fill_blockers(
    repo_tmp_path: Path,
) -> None:
    run_dir = repo_tmp_path / "backtest_strategy_ladder" / "run-mode-b"
    _seed_threshold_run(run_dir)

    payloads = build_no_shadow_threshold_challenge_payloads(run_dir)
    governance = payloads["threshold_governance_survival_report.json"]
    assert isinstance(governance, dict)

    assert governance["real_selected_count"] == 0
    assert governance["real_executed_count"] == 0
    assert governance["executed_count_after_counterfactual"] == 0
    blockers = {
        row["reason_code"]
        for row in governance["dominant_remaining_blockers"]
        if isinstance(row, dict)
    }
    assert "EXPECTED_EDGE_PROXY_BLOCKED" in blockers

    final_verdict = payloads["no_shadow_threshold_challenge_final_verdict.json"]
    assert isinstance(final_verdict, dict)
    assert final_verdict["verdict"] == "CALIBRATION_PREMATURE_COST_FILL_NOT_READY"


def test_synthetic_governed_oracle_requires_test_runtime_mode(
    repo_tmp_path: Path,
) -> None:
    run_dir = repo_tmp_path / "backtest_strategy_ladder" / "run-synthetic"
    _seed_threshold_run(run_dir)

    with pytest.raises(ValueError, match="runtime_mode=TEST"):
        build_no_shadow_threshold_challenge_payloads(
            run_dir,
            synthetic_records=[{"candidate_id": "synthetic"}],
        )

    payloads = build_no_shadow_threshold_challenge_payloads(
        run_dir,
        runtime_mode=TEST_MODE,
        synthetic_records=[{"candidate_id": "synthetic"}],
    )
    report = payloads[NO_SHADOW_THRESHOLD_CHALLENGE_FILENAME]
    assert isinstance(report, dict)
    oracle = report["synthetic_governed_oracle"]
    assert isinstance(oracle, dict)
    assert oracle["status"] == "SYNTHETIC_ORACLE_ONLY"
    assert oracle["profitability_evidence_status"] == "NOT_REAL_BACKTEST_EVIDENCE"


def test_missing_metrics_are_reported_without_hallucination(repo_tmp_path: Path) -> None:
    run_dir = repo_tmp_path / "backtest_strategy_ladder" / "run-missing"
    _seed_threshold_run(run_dir, include_metrics=False)

    payloads = build_no_shadow_threshold_challenge_payloads(run_dir)

    min_direction = _engine_a_threshold(payloads, "min_direction")
    assert min_direction["status"] == "INSUFFICIENT_DATA"
    assert min_direction["missing_metric_count"] == 1
    assert min_direction["metric_available_count"] == 0


def test_missing_threshold_is_reported_not_found(repo_tmp_path: Path) -> None:
    run_dir = repo_tmp_path / "backtest_strategy_ladder" / "run-missing-threshold"
    _seed_threshold_run(run_dir)

    payloads = build_no_shadow_threshold_challenge_payloads(
        run_dir,
        current_thresholds={},
    )

    min_direction = _engine_a_threshold(payloads, "min_direction")
    assert min_direction["status"] == "NOT_FOUND"
    assert min_direction["current_value_status"] == "NOT_FOUND"


def test_selected_count_zero_blocks_profitability_claim(repo_tmp_path: Path) -> None:
    run_dir = repo_tmp_path / "backtest_strategy_ladder" / "run-profitability"
    _seed_threshold_run(run_dir)

    write_no_shadow_threshold_challenge_reports(run_dir)

    report = _read_json(run_dir / "reports" / NO_SHADOW_THRESHOLD_CHALLENGE_FILENAME)
    final_verdict = _read_json(
        run_dir / "reports" / "no_shadow_threshold_challenge_final_verdict.json"
    )
    assert report["selected_count_real"] == 0
    assert report["profitability_claim_allowed"] is False
    assert final_verdict["profitability_backtest_ready"] is False
    assert final_verdict["profitability_claim_allowed"] is False
