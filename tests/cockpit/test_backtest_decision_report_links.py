from __future__ import annotations

import json
from pathlib import Path

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


def test_backtest_template_contains_decision_report_surface() -> None:
    template = Path("src/cockpit/templates/pages/backtest.html").read_text(
        encoding="utf-8"
    )

    assert "backtest-decision-report-card" in template
    assert "backtest_decision_report_status" in template
    assert "backtest_decision_report_links" in template
    assert "backtest_decision_next_blocker" in template
