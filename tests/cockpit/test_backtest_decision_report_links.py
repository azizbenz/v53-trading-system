from __future__ import annotations

import json
from pathlib import Path

from cockpit.action_support import (
    CockpitBacktestJobKind,
    CockpitBacktestJobRecord,
    CockpitBacktestJobStatus,
)
from cockpit.runtime_support import (
    StrategyLadderBacktestSummary,
    _enrich_strategy_ladder_summary_from_artifacts,
)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def test_backtest_summary_surfaces_decision_report_links(repo_tmp_path: Path) -> None:
    output_root = repo_tmp_path / "output"
    run_id = "strategy_ladder_workflow-ui"
    run_dir = output_root / "backtest_strategy_ladder" / run_id
    reports = run_dir / "reports"
    _write_json(reports / "strategy_ladder_summary.json", {"run_id": run_id})
    _write_json(run_dir / "run_manifest.json", {"run_id": run_id})
    _write_json(
        reports / "backtest_decision_report.json",
        {
            "report_status": "BACKTEST_DECISION_REPORT_PARTIAL",
            "profitability_backtest_ready": False,
            "summary": {"profitability_claim_allowed": False},
            "recommendation": {
                "live_ready": False,
                "shadow_ready": False,
                "research_only": True,
                "next_required_patch": "NO_EXECUTED_TRADES",
            },
            "timeframe_ranking": [
                {"timeframe": "1m", "rank": 1, "executed_count": 3}
            ],
            "pair_ranking": [{"pair": "BTCUSDT", "rank": 1, "executed_count": 3}],
            "capital_bucket_ranking": [
                {"capital_bucket": 400, "rank": 1, "executed_count": 3}
            ],
            "ml_vs_no_ml_delta": {"status": "ML_VS_NO_ML_REPORT_UNAVAILABLE"},
        },
    )
    _write_json(
        reports / "backtest_decision_report_final_verdict.json",
        {
            "verdict": "BACKTEST_DECISION_REPORT_PARTIAL",
            "profitability_backtest_ready": False,
        },
    )
    _write_json(
        reports / "backtest_decision_capability_audit.json",
        {"overall_status": "BACKTEST_DECISION_REPORT_PARTIAL"},
    )
    for filename in (
        "timeframe_ranking_report.json",
        "pair_ranking_report.json",
        "capital_bucket_ranking_report.json",
        "cost_fill_realism_report.json",
    ):
        _write_json(reports / filename, {"status": "PARTIAL"})

    summary = _enrich_strategy_ladder_summary_from_artifacts(
        StrategyLadderBacktestSummary(run_id=run_id),
        output_root=output_root,
        jobs=(),
        selected_candidate_id="",
    )

    labels = {item["label"] for item in summary.backtest_decision_report_links}
    assert summary.backtest_decision_report_status == "BACKTEST_DECISION_REPORT_PARTIAL"
    assert summary.backtest_decision_best_timeframe == "1m"
    assert summary.backtest_decision_best_pair == "BTCUSDT"
    assert summary.backtest_decision_best_capital_bucket == "400"
    assert summary.backtest_decision_ml_benefit_status == "ML_VS_NO_ML_REPORT_UNAVAILABLE"
    assert summary.backtest_decision_next_blocker == "NO_EXECUTED_TRADES"
    assert summary.backtest_decision_profitability_ready is False
    assert summary.backtest_decision_profitability_claim_allowed is False
    assert {
        "decision_report",
        "capability_audit",
        "final_verdict",
        "timeframe_ranking",
        "pair_ranking",
        "capital_bucket_ranking",
        "cost_fill_realism",
    }.issubset(labels)


def test_backtest_summary_surfaces_a2_performance_links(repo_tmp_path: Path) -> None:
    output_root = repo_tmp_path / "phase_a2_data_factory"
    _write_json(
        output_root / "a2_microstructure_performance_report.json",
        {
            "status": "A2_PERFORMANCE_REPORT_READY",
            "stage_timings_s": {"gold_feature_build": 13.59},
            "gold": {
                "decision_window_status": "GOLD_DECISION_WINDOW_FILTER_READY",
                "feature_equivalence_status": "A2_FEATURE_EQUIVALENCE_READY",
            },
            "microstructure": {
                "cache_status": "A2_MICROSTRUCTURE_FILE_CACHE_READY",
                "streaming_status": "A2_MICROSTRUCTURE_STREAMING_READY",
                "repeated_raw_scan_status": "FILE_CACHE_ACTIVE",
                "time_index_hit_count": 1498,
                "time_index_miss_count": 2,
            },
        },
    )
    _write_json(
        output_root / "a2_microstructure_cache_manifest.json",
        {"cache_status": "A2_MICROSTRUCTURE_FILE_CACHE_READY"},
    )
    _write_json(
        output_root / "a2_feature_equivalence_report.json",
        {"status": "A2_FEATURE_EQUIVALENCE_READY"},
    )

    summary = _enrich_strategy_ladder_summary_from_artifacts(
        StrategyLadderBacktestSummary(),
        output_root=output_root,
        jobs=(),
        selected_candidate_id="",
    )

    labels = {item["label"] for item in summary.a2_microstructure_report_links}
    assert summary.a2_microstructure_performance_status == "A2_PERFORMANCE_REPORT_READY"
    assert summary.a2_microstructure_cache_status == "A2_MICROSTRUCTURE_FILE_CACHE_READY"
    assert summary.a2_microstructure_streaming_status == "A2_MICROSTRUCTURE_STREAMING_READY"
    assert summary.a2_feature_equivalence_status == "A2_FEATURE_EQUIVALENCE_READY"
    assert summary.a2_gold_decision_window_status == "GOLD_DECISION_WINDOW_FILTER_READY"
    assert summary.a2_gold_feature_build_wall_time_s == 13.59
    assert summary.a2_microstructure_time_index_hit_count == 1498
    assert summary.a2_microstructure_time_index_miss_count == 2
    assert {"a2_performance", "a2_cache_manifest", "a2_feature_equivalence"}.issubset(labels)


def test_running_job_explains_95_percent_without_artifacts(repo_tmp_path: Path) -> None:
    record = CockpitBacktestJobRecord(
        job_id="strategy_ladder_data_factory-stale",
        correlation_id="corr",
        job_kind=CockpitBacktestJobKind.STRATEGY_LADDER_DATA_FACTORY,
        status=CockpitBacktestJobStatus.JOB_RUNNING,
        requested_at_iso="2025-01-01T00:00:00+00:00",
        started_at_iso="2025-01-01T00:00:00+00:00",
        output_root=str((repo_tmp_path / "empty_output").resolve()),
    )

    assert record.progress_pct == 95
    assert record.produced_file_count == 0
    assert record.progress_health_status == "RUNNING_AT_95_WITHOUT_ARTIFACTS"
    assert "no artifacts are visible" in record.progress_health_message


def test_backtest_template_contains_decision_report_surface() -> None:
    template = Path("src/cockpit/templates/pages/backtest.html").read_text(
        encoding="utf-8"
    )
    # Patch A (2026-05-31) — the Decision Report card was extracted to
    # partials/_decision_report_card.html (included on /backtest AND
    # /backtest/replay). The surface strings now live in the partial; the main
    # page must reference the partial via include.
    decision_partial = Path(
        "src/cockpit/templates/partials/_decision_report_card.html"
    ).read_text(encoding="utf-8")

    assert "partials/_decision_report_card.html" in template
    assert "backtest-decision-report-card" in decision_partial
    assert "backtest_decision_report_status" in decision_partial
    assert "backtest_decision_report_links" in decision_partial
    assert "backtest_decision_next_blocker" in decision_partial
    # Cards still rendered inline on the main /backtest control center:
    assert "backtest-a2-performance-card" in template
    assert "a2_microstructure_report_links" in template
    assert "backtest-latest-job-health" in template
