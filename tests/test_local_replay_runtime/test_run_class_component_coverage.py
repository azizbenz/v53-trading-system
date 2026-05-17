from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from local_replay_runtime.run_class_component_coverage import (
    build_run_class_component_coverage,
    emit_run_class_component_coverage,
)
from tests.support_paths import repo_build_path


def _scratch_dir(name: str) -> Path:
    return repo_build_path("run_class_component_coverage_tests", f"{name}_{uuid4().hex}")


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(row) for row in rows) + ("\n" if rows else ""),
        encoding="utf-8",
    )


def _write_engine_native_artifacts(
    root: Path,
    *,
    run_id: str = "run-coverage",
    include_build14_shadow_report: bool = False,
    executed_count: int = 0,
    reduced_count: int = 0,
    engine_id: str = "engine_c",
    expected_edge_truth_status: str = "EXPECTED_EDGE_GOVERNED_BACKTEST_TRUTH",
    expected_edge_governed_count: int = 1,
) -> Path:
    run_dir = root / "backtest_strategy_ladder" / run_id
    _write_json(
        root / "data_factory_manifest.json",
        {
            "run_id": run_id,
            "data_factory_status": "DATA_FACTORY_READY",
            "historical_metadata_status": "BYBIT_HISTORICAL_METADATA_READY",
        },
    )
    _write_json(
        root / "first_run_manifest.json",
        {"run_id": run_id, "first_run_status": "FIRST_RUN_RAN_WITH_PARTIAL_EVIDENCE"},
    )
    _write_json(
        root / "backtest_proof_matrix.json",
        {
            "run_id": run_id,
            "candidate_engine_native_count": 1,
            "candidate_count": 1,
            "detailed_replay_count": 1,
            "executed_count": executed_count,
            "reduced_count": reduced_count,
            "fee_provenance_status": "CONFIGURED_FEE_PROVENANCE_READY",
            "replay_impact_source_status": "IMPACT_SOURCE_DEPTH20_MODEL",
            "replay_cost_parity_status": "REPLAY_LIVE_COST_PARITY_BLOCKED_BY_TELEMETRY",
            "true_drawdown_status": "NOT_PROVEN",
        },
    )
    _write_json(
        run_dir / "run_manifest.json",
        {
            "run_id": run_id,
            "candidate_count": 1,
            "candidate_engine_native_count": 1,
            "candidate_proxy_count": 0,
            "engine_native_status": "ENGINE_NATIVE_FULL_PATH_READY",
            "engine_native_records_built": 5,
            "expected_edge_truth_status": expected_edge_truth_status,
            "expected_edge_governed_count": expected_edge_governed_count,
            "executed_trade_count": executed_count,
            "ml_mode_status": "ML_MODE_OFF",
        },
    )
    _write_json(run_dir / "reports" / "strategy_ladder_summary.json", {"run_id": run_id})
    _write_jsonl(
        run_dir / "fast_candidates" / "candidate_events.jsonl",
        [
            {
                "candidate_id": "c1",
                "pair": "BTCUSDT",
                "engine_id": engine_id,
                "preliminary_reason_codes": [
                    "ENGINE_NATIVE_DECISION:NO_TRADE",
                    f"{engine_id}.microstructure.not_applied",
                    "history_weak",
                ],
                "compatibility_payload": {
                    "engine_native_reason_codes": [f"{engine_id}.breakout.structured_breakout"],
                    "engine_native_no_trade_reasons": ["continuation_not_viable"],
                    **(
                        {
                            "build14_shadow_report": {
                                "snapshots": [
                                    {
                                        "reader_name": "market_toxicity_snapshot",
                                        "status": "critical",
                                    },
                                    {
                                        "reader_name": "lob_deep_filter_vwa",
                                        "status": "elevated",
                                    },
                                    {
                                        "reader_name": "execution_fragility_score",
                                        "status": "critical",
                                    },
                                ]
                            }
                        }
                        if include_build14_shadow_report
                        else {}
                    ),
                },
            }
        ],
    )
    _write_jsonl(run_dir / "refusal_ledger.jsonl", [{"candidate_id": "c1"}])
    return run_dir


def test_component_coverage_has_no_unknown_status() -> None:
    root = _scratch_dir("no_unknown")
    _write_engine_native_artifacts(root)

    matrix = build_run_class_component_coverage(output_root=root, run_id="run-coverage")

    assert matrix.run_class == "ENGINE_NATIVE_DECISION_REPLAY"
    assert all(component.status != "UNKNOWN" for component in matrix.components)


def test_live_only_modules_are_not_required_in_bybit_replay() -> None:
    root = _scratch_dir("live_only")
    _write_engine_native_artifacts(root)

    matrix = build_run_class_component_coverage(output_root=root, run_id="run-coverage")
    by_id = matrix.by_component_id()

    assert by_id["execution_backbone.reconciliation_layer"].status == "SHADOW_LIVE_ONLY"
    assert by_id["venue_adapters.binance_spot.live_submission"].status == "SHADOW_LIVE_ONLY"
    assert by_id["execution_backbone.order_decider"].status == "EXPLICITLY_NOT_APPLICABLE_TO_RUN_CLASS"


def test_history_weak_is_not_applicable_without_executed_or_reduced_trades() -> None:
    root = _scratch_dir("history_weak")
    _write_engine_native_artifacts(root)

    matrix, path = emit_run_class_component_coverage(output_root=root, run_id="run-coverage")
    by_id = matrix.by_component_id()

    assert path.name == "run_class_component_coverage.json"
    assert by_id["protocols.closed_episode_journal"].status == "NOT_APPLICABLE_NO_EXECUTED_TRADES"
    assert "no_executed_or_reduced_episodes_available" in by_id[
        "protocols.closed_episode_journal"
    ].reason_codes


def test_history_weak_keeps_wiring_gap_when_executed_or_reduced_trades_exist() -> None:
    root = _scratch_dir("history_weak_executed")
    _write_engine_native_artifacts(root, executed_count=1, engine_id="engine_d")

    matrix = build_run_class_component_coverage(output_root=root, run_id="run-coverage")
    by_id = matrix.by_component_id()

    assert (
        by_id["protocols.closed_episode_journal"].status
        == "REQUIRED_FOR_ENGINE_D_HISTORY_BUT_NO_EPISODE_SOURCE"
    )
    assert "ENGINE_D_HISTORY_BLOCKED_BY_MISSING_CLOSED_EPISODE_JOURNAL" in by_id[
        "protocols.closed_episode_journal"
    ].reason_codes


def test_expected_edge_proxy_reclassifies_fee_and_break_even_as_explicit_blockers() -> None:
    root = _scratch_dir("proxy_edge_reclassifies_gates")
    _write_engine_native_artifacts(
        root,
        expected_edge_truth_status="EXPECTED_EDGE_PROXY_BLOCKED",
        expected_edge_governed_count=0,
    )

    matrix = build_run_class_component_coverage(output_root=root, run_id="run-coverage")
    by_id = matrix.by_component_id()

    assert (
        by_id["execution_backbone.fee_aware_edge_gate"].status
        == "BLOCKED_BY_EXPECTED_EDGE_PROXY"
    )
    assert "FEE_AWARE_EDGE_PROXY_BLOCKED" in by_id[
        "execution_backbone.fee_aware_edge_gate"
    ].reason_codes
    assert (
        by_id["scoring_backbone.break_even_filter"].status
        == "BLOCKED_BY_EXPECTED_EDGE_PROXY"
    )
    assert "BREAK_EVEN_PROXY_BLOCKED" in by_id[
        "scoring_backbone.break_even_filter"
    ].reason_codes


def test_complete_enablers_mark_used_when_build14_reports_are_carried() -> None:
    root = _scratch_dir("build14_used")
    _write_engine_native_artifacts(root, include_build14_shadow_report=True)

    matrix = build_run_class_component_coverage(output_root=root, run_id="run-coverage")
    by_id = matrix.by_component_id()

    assert by_id["complete_enablers.market_toxicity"].status == "USED"
    assert by_id["complete_enablers.lob_deep_filter"].status == "USED"
    assert by_id["complete_enablers.execution_fragility"].status == "USED"
