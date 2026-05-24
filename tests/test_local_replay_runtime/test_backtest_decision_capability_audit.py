from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from local_replay_runtime.backtest_decision_report_builder import (
    write_backtest_decision_reports,
)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )


def _seed_partial_run(run_dir: Path) -> None:
    reports = run_dir / "reports"
    _write_json(
        reports / "strategy_ladder_summary.json",
        {
            "run_id": run_dir.name,
            "candidate_count": 1,
            "ml_mode_status": "ML_MODE_OFF",
            "blocker_codes": ["NO_EXECUTED_TRADES", "EXPECTED_EDGE_PROXY_BLOCKED"],
            "fee_model_source": "EXCHANGE_METADATA",
            "spread_model_source": "CANONICAL_BOOK_WALK_DEPTH20",
            "slippage_model_source": "CANONICAL_BOOK_WALK_DEPTH20",
            "partial_fill_model_source": "CANONICAL_PARTIAL_FILL_MODEL",
            "adverse_selection_source": "REPLAY_PROXY",
            "execution_fidelity_gap_codes": ["ADVERSE_SELECTION_PROXY"],
            "expected_edge_proxy_count": 1,
            "expected_edge_governed_count": 0,
        },
    )
    _write_json(
        run_dir / "run_manifest.json",
        {"run_id": run_dir.name, "start": "2025-04-29", "end": "2025-05-01"},
    )
    _write_json(
        reports / "profitability_truth_verdict.json",
        {"profitability_claim_allowed": False},
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
                "compatibility_payload": {},
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
            "execution_state": "hard_blocked",
            "reason_codes": ["EXPECTED_EDGE_PROXY_BLOCKED"],
            "fill_realism_status": "FILL_REALISM_NOT_PROVEN",
        },
    )
    _write_json(
        reports / "timeframe_matrix.json",
        [
            {
                "timeframe": "1m",
                "candidate_count": 1,
                "executed_count": 0,
                "net_pnl_bps": None,
            }
        ],
    )
    _write_json(
        reports / "engine_matrix.json",
        [{"engine_id": "engine_a", "candidate_count": 1, "executed_count": 0}],
    )
    _write_json(
        reports / "pair_matrix.json",
        [{"pair": "BTCUSDT", "candidate_count": 1, "executed_count": 0}],
    )
    _write_json(
        reports / "capital_bucket_matrix.json",
        [
            {
                "capital_bucket": 400,
                "record_count": 1,
                "selected_count": 0,
                "executed_count": 0,
                "reduced_count": 0,
            }
        ],
    )
    _write_json(
        reports / "measured_spread_report.json",
        {
            "rows": [
                {
                    "candidate_id": "c1",
                    "capital_bucket": 400,
                    "spread_bps": 1.25,
                    "status": "MEASURED",
                }
            ]
        },
    )
    _write_json(
        reports / "measured_slippage_report.json",
        {
            "rows": [
                {
                    "candidate_id": "c1",
                    "capital_bucket": 400,
                    "walk_cost_bps": 2.5,
                    "status": "MEASURED",
                }
            ]
        },
    )
    _write_json(
        reports / "fill_realism_report.json",
        {"rows": [{"candidate_id": "c1", "capital_bucket": 400, "status": "PARTIAL"}]},
    )
    _write_json(reports / "execution_realism_summary.json", {"status": "PARTIAL"})
    _write_json(
        reports / "candidate_threshold_audit.json",
        {
            "rows": [
                {
                    "candidate_id": "c1",
                    "threshold_alignment_status": "THRESHOLD_TOO_LOOSE_FOR_B2",
                }
            ]
        },
    )
    _write_json(
        reports / "gate_counterfactual_matrix.json",
        {"rows": [{"scenario_id": "baseline", "counterfactual_survival_count": 0}]},
    )
    _write_json(
        reports / "gate_waterfall_analysis.json",
        {
            "best_counterfactual_scenario": {
                "scenario_id": "baseline",
                "counterfactual_survival_count": 0,
            }
        },
    )
    _write_jsonl(
        run_dir / "ml_label_store" / "strategy_ladder_replay_label_store.jsonl",
        [{"candidate_id": "c1", "feature_values": {"vpin": 0.1, "queue_pressure": 0.2}}],
    )


def test_backtest_decision_capability_audit_classifies_partial_run(
    repo_tmp_path: Path,
) -> None:
    run_dir = repo_tmp_path / "backtest_strategy_ladder" / "run-partial"
    _seed_partial_run(run_dir)

    write_backtest_decision_reports(run_dir)

    audit = json.loads(
        (run_dir / "reports" / "backtest_decision_capability_audit.json").read_text(
            encoding="utf-8"
        )
    )

    assert audit["schema_version"] == "v53.backtest_decision_capability_audit.v1"
    assert audit["overall_status"] == "BACKTEST_DECISION_REPORT_PARTIAL"
    assert audit["profitability_backtest_ready"] is False
    assert audit["capabilities"]["timeframe_ranking"]["status"] == "PARTIAL"
    assert audit["capabilities"]["feature_ranking"]["status"] == "PARTIAL"
    assert audit["capabilities"]["ml_vs_no_ml"]["status"] == "PARTIAL"
    assert audit["capabilities"]["engine_by_regime"]["status"] == "MISSING"
    assert audit["capabilities"]["cost_fill_realism"]["status"] == "PARTIAL"
    assert audit["capabilities"]["threshold_near_miss"]["status"] == "PARTIAL"
