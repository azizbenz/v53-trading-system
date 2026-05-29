from __future__ import annotations

import json
from pathlib import Path

from local_replay_runtime.backtest_decision_report_builder import (
    write_backtest_decision_reports,
)
from tests.test_local_replay_runtime.test_backtest_decision_capability_audit import (
    _seed_partial_run,
)


def _read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_backtest_decision_report_builder_preserves_decision_artifacts(
    repo_tmp_path: Path,
) -> None:
    run_dir = repo_tmp_path / "backtest_strategy_ladder" / "run-report"
    _seed_partial_run(run_dir)
    summary_path = run_dir / "reports" / "strategy_ladder_summary.json"
    summary_before = summary_path.read_text(encoding="utf-8")

    refs = write_backtest_decision_reports(run_dir)

    assert summary_path.read_text(encoding="utf-8") == summary_before
    assert "backtest_decision_report.json" in refs
    assert "timeframe_ranking_report.json" in refs

    decision = _read_json(run_dir / "reports" / "backtest_decision_report.json")
    summary = decision["summary"]
    assert isinstance(summary, dict)
    assert summary["candidate_count"] == 1
    assert summary["selected_count"] == 0
    assert summary["executed_count"] == 0
    assert summary["hard_blocked_count"] == 1
    assert summary["profitability_claim_allowed"] is False

    recommendation = decision["recommendation"]
    assert isinstance(recommendation, dict)
    assert recommendation["live_ready"] is False
    assert recommendation["shadow_ready"] is False
    assert recommendation["research_only"] is True
    assert recommendation["next_required_patch"] == "NO_EXECUTED_TRADES"


def test_backtest_decision_report_builder_does_not_rank_without_executions(
    repo_tmp_path: Path,
) -> None:
    run_dir = repo_tmp_path / "backtest_strategy_ladder" / "run-no-exec"
    _seed_partial_run(run_dir)

    write_backtest_decision_reports(run_dir)

    timeframe_report = _read_json(run_dir / "reports" / "timeframe_ranking_report.json")
    assert timeframe_report["status"] == "TIMEFRAME_RANKING_PARTIAL"
    assert timeframe_report["ranking_status"] == "insufficient_executions"
    assert timeframe_report["top_timeframe"] is None
    assert timeframe_report["rows"]
    assert timeframe_report["rows"][0]["recommendation"] == "insufficient_executions"

    pair_report = _read_json(run_dir / "reports" / "pair_ranking_report.json")
    assert pair_report["top_pair"] is None
    assert pair_report["rows"][0]["final_recommendation"] == "insufficient_executions"

    capital_report = _read_json(run_dir / "reports" / "capital_bucket_ranking_report.json")
    assert capital_report["top_capital_bucket"] is None
    assert capital_report["rows"][0]["capital_recommendation"] == "insufficient_executions"


def test_backtest_decision_report_builder_keeps_proxy_costs_research_only(
    repo_tmp_path: Path,
) -> None:
    run_dir = repo_tmp_path / "backtest_strategy_ladder" / "run-cost-partial"
    _seed_partial_run(run_dir)

    write_backtest_decision_reports(run_dir)

    cost_report = _read_json(run_dir / "reports" / "cost_fill_realism_report.json")
    assert cost_report["status"] == "COST_FILL_REALISM_PARTIAL"
    assert cost_report["profitability_ready"] is False
    assert cost_report["proxy_contamination_present"] is True

    final_verdict = _read_json(
        run_dir / "reports" / "backtest_decision_report_final_verdict.json"
    )
    assert final_verdict["verdict"] == "BACKTEST_DECISION_REPORT_PARTIAL"
    assert final_verdict["profitability_backtest_ready"] is False
    assert final_verdict["research_only"] is True


def test_backtest_decision_report_builder_marks_ml_delta_unavailable(
    repo_tmp_path: Path,
) -> None:
    run_dir = repo_tmp_path / "backtest_strategy_ladder" / "run-ml-unavailable"
    _seed_partial_run(run_dir)

    write_backtest_decision_reports(run_dir)

    ml_delta = _read_json(run_dir / "reports" / "ml_vs_no_ml_delta_report.json")
    assert ml_delta["status"] == "ML_VS_NO_ML_REPORT_UNAVAILABLE"
    assert ml_delta["reason"] == "aligned_baseline_and_overlay_run_dirs_not_provided"


def test_backtest_decision_report_builder_separates_distinct_candidates_from_bucket_records(
    repo_tmp_path: Path,
) -> None:
    """Patch P0-COUNT-1 (2026-05-27) — bucket expansion regression test.

    When a single candidate is replicated across N capital buckets, the legacy
    ``selected_count`` / ``executed_count`` are bucket-record counters and
    inflate by N. The audit on run strategy_ladder_workflow-2df91d9d5c48dfbf
    showed 1 distinct candidate appearing as ``selected_count=4`` (1 × 4
    buckets). The new ``selected_distinct_candidate_count`` /
    ``executed_distinct_candidate_count`` collapse the replication.
    """
    import json as _json

    run_dir = repo_tmp_path / "backtest_strategy_ladder" / "run-bucket-replication"
    _seed_partial_run(run_dir)

    # Replace the partial-run hard-blocked sample with one executed candidate
    # replicated across 4 capital buckets to simulate the audited scenario.
    reports = run_dir / "reports"
    detailed = run_dir / "detailed_replay" / "by_bucket"
    # Clear the 400-bucket sample and rebuild with executed state.
    for bucket in (400, 500, 1500, 4000):
        bucket_dir = detailed / str(bucket)
        bucket_dir.mkdir(parents=True, exist_ok=True)
        (bucket_dir / "c1.json").write_text(
            _json.dumps(
                {
                    "candidate_id": "c1",
                    "pair": "BTCUSDT",
                    "engine_id": "engine_a",
                    "strategy_id": "strategy_a",
                    "capital_bucket": bucket,
                    "execution_state": "executed",
                    "reason_codes": [
                        "engine_a.emit.valid",
                        "B2_COST_MEASUREMENT_BLOCKED",
                    ],
                    "fill_realism_status": "FILL_REALISM_SHADOW_MEASURED",
                    "executed_only_net_return": -0.0067,
                },
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )

    # Update matrix files so ranking sees the executions.
    (reports / "timeframe_matrix.json").write_text(
        _json.dumps(
            [
                {
                    "timeframe": "1m",
                    "candidate_count": 1,
                    "executed_count": 4,
                    "net_pnl_bps": -46.04,
                }
            ],
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    (reports / "pair_matrix.json").write_text(
        _json.dumps(
            [
                {
                    "pair": "BTCUSDT",
                    "candidate_count": 1,
                    "selected_count": 4,
                    "executed_count": 4,
                    "executed_only_net_return": -0.0067,
                }
            ],
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    write_backtest_decision_reports(run_dir)

    # Timeframe ranking : the 4 bucket-records correspond to 1 distinct
    # candidate. P1-RANKING-WORDING-1 also blocks `ranked` for N=1.
    tf_report = _read_json(reports / "timeframe_ranking_report.json")
    assert tf_report["timeframes_tested_count"] == 1
    assert tf_report["ranking_status"] == "ONLY_AVAILABLE_PARTIAL_NO_RANK"
    assert tf_report["top_timeframe"] is None
    assert tf_report["only_timeframe_tested"] == "1m"
    tf_row = tf_report["rows"][0]
    assert tf_row["selected_count"] == 4, "legacy bucket-record count preserved"
    assert tf_row["executed_count"] == 4
    assert tf_row["selected_bucket_record_count"] == 4
    assert tf_row["selected_distinct_candidate_count"] == 1, (
        "P0-COUNT-1: 1 candidate × 4 buckets should collapse to 1 distinct"
    )
    assert tf_row["executed_distinct_candidate_count"] == 1

    # Pair ranking : same collapse + wording downgrade for N=1.
    pair_report = _read_json(reports / "pair_ranking_report.json")
    assert pair_report["pairs_tested_count"] == 1
    assert pair_report["ranking_status"] == "ONLY_AVAILABLE_PARTIAL_NO_RANK"
    assert pair_report["top_pair"] is None
    assert pair_report["only_pair_tested"] == "BTCUSDT"
    pair_row = pair_report["rows"][0]
    assert pair_row["selected_count"] == 4
    assert pair_row["executed_count"] == 4
    assert pair_row["selected_bucket_record_count"] == 4
    assert pair_row["selected_distinct_candidate_count"] == 1
    assert pair_row["executed_distinct_candidate_count"] == 1


def test_backtest_decision_report_builder_does_not_hallucinate_feature_importance(
    repo_tmp_path: Path,
) -> None:
    run_dir = repo_tmp_path / "backtest_strategy_ladder" / "run-features"
    _seed_partial_run(run_dir)

    write_backtest_decision_reports(run_dir)

    feature_report = _read_json(run_dir / "reports" / "feature_ranking_report.json")
    assert feature_report["status"] == "FEATURE_RANKING_PARTIAL"
    assert feature_report["feature_count"] == 2
    rows = feature_report["rows"]
    assert {row["feature_name"] for row in rows} == {"queue_pressure", "vpin"}
    assert all(row["importance"] is None for row in rows)
    assert all(row["rank"] is None for row in rows)
    assert all(
        row["utility_status"] == "UNPROVEN_WITHOUT_ABLATION_OR_OOS_STABILITY"
        for row in rows
    )
