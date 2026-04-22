"""Tests for the governed LOCAL_REPLAY -> VPS import -> SHADOW runner."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import shutil
import sys
from uuid import uuid4

import pytest

from interface_contracts import ProfileId, RuntimeMode, StrategyClassification
from local_replay_runtime import (
    HistoricalReplayDataset,
    HistoricalReplayOpportunity,
    ReplayExecutionInput,
    ReplayOrchestratorRequest,
    ReplayRunManifest,
    execute_local_replay_export,
    orchestrate_local_replay_export,
)
from meta_minimal.dtr_core.decision_state_encoder import DecisionState
from meta_minimal.dtr_core.dtr_record_builder import build_dtr
from protocols import ShadowDayCounter, ShadowProfile, ShadowSessionRegistry
from regime_classifier import RegimeLiteAssessment, RegimeLiteState
from risk_backbone import (
    InfoStressAssessment,
    InfoStressLevel,
    build_regime_lite_safing_recommendation,
)
from tests.support_paths import repo_build_path


def _load_runner_module():
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "scripts" / "run_local_replay_shadow.py"
    module_name = "test_run_local_replay_shadow"
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _scratch_dir(label: str) -> Path:
    from tests.support_paths import make_repo_scratch_dir

    return make_repo_scratch_dir("local_replay_shadow_runner_tests", label)


def _write_execution_runtime_projection(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "correlation_id": "corr-exec-runtime",
                "export_dir": "build/local_lab",
                "run_id": "local-lab-run-1",
                "projection_status": "ready",
                "projection_ready": True,
                "execution_review_status": "ready",
                "execution_review_ready": True,
                "consumer_count": 3,
                "ready_consumer_count": 3,
                "partial_consumer_count": 0,
                "blocked_consumer_count": 0,
                "blocking_reasons": [],
                "caution_flags": ["THR-X05_ACCEPTED_EVENTS_ONLY"],
                "consumers": [
                    {
                        "consumer_id": "rate_limiter",
                        "consumer_interface": "quota_ratio_ceiling",
                        "threshold_id": "THR-X03",
                        "target_runtime_mode": "shadow",
                        "projection_status": "ready",
                        "projection_ready": True,
                        "threshold_review_status": "ready",
                        "threshold_fit_ready": True,
                        "method": "quota_ratio_ceiling_v1",
                        "unit": "quota_ratio",
                        "projection_value": 0.8,
                        "projection_value_semantics": "max_observed_quota_ratio_before_throttle",
                        "hard_cap_human": 0.8,
                        "hard_cap_binding": False,
                        "blocking_reasons": [],
                        "caution_flags": [],
                    },
                    {
                        "consumer_id": "spread_guard",
                        "consumer_interface": "spread_bps_ceiling",
                        "threshold_id": "THR-X04",
                        "target_runtime_mode": "shadow",
                        "projection_status": "ready",
                        "projection_ready": True,
                        "threshold_review_status": "ready",
                        "threshold_fit_ready": True,
                        "method": "lognormal_mu_plus_2sigma_capped",
                        "unit": "bps",
                        "projection_value": 24.0,
                        "projection_value_semantics": "max_observed_spread_bps_before_no_trade",
                        "hard_cap_human": 50.0,
                        "hard_cap_binding": False,
                        "blocking_reasons": [],
                        "caution_flags": [],
                    },
                    {
                        "consumer_id": "slippage_model",
                        "consumer_interface": "sqrt_size_slippage_predictor",
                        "threshold_id": "THR-X05",
                        "target_runtime_mode": "shadow",
                        "projection_status": "ready",
                        "projection_ready": True,
                        "threshold_review_status": "ready",
                        "threshold_fit_ready": True,
                        "method": "size_slippage_huber_v1",
                        "unit": "bps",
                        "projection_value": 18.0,
                        "projection_value_semantics": "reference_slippage_bps_at_q95_size",
                        "reference_size": 4.0,
                        "size_proxy": "final_size",
                        "intercept_bps": 2.0,
                        "sqrt_size_coefficient": 8.0,
                        "r_squared": 0.55,
                        "mean_absolute_error_bps": 1.5,
                        "blocking_reasons": [],
                        "caution_flags": ["THR-X05_ACCEPTED_EVENTS_ONLY"],
                    },
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def _write_regime_lite_assessment(path: Path) -> None:
    assessment = RegimeLiteAssessment(
        state=RegimeLiteState.EXTREME,
        candidate_state=RegimeLiteState.EXTREME,
        previous_state=RegimeLiteState.STRESSED,
        state_changed=True,
        state_entered_ts=1_700_000_000_000,
        entries_blocked_until_ts=1_700_086_400_000,
        entries_blocked=True,
        sudden_event=True,
        transition_path=(
            RegimeLiteState.STRESSED,
            RegimeLiteState.EXTREME,
        ),
        reason_codes=(
            "RG_EXTREME_BTC_DROP_1H",
            "RG_EXTREME_INTRADAY_DRAWDOWN",
        ),
        btc_realized_vol_24h=0.09,
        btc_drop_1h=-0.08,
        intraday_drawdown=0.12,
        engine_return_dispersion=0.07,
    )
    path.write_text(assessment.model_dump_json(indent=2), encoding="utf-8")


def _write_regime_lite_safing_recommendation(path: Path) -> None:
    assessment = RegimeLiteAssessment(
        state=RegimeLiteState.EXTREME,
        candidate_state=RegimeLiteState.EXTREME,
        previous_state=RegimeLiteState.STRESSED,
        state_changed=True,
        state_entered_ts=1_700_000_000_000,
        entries_blocked_until_ts=1_700_086_400_000,
        entries_blocked=True,
        sudden_event=True,
        transition_path=(
            RegimeLiteState.STRESSED,
            RegimeLiteState.EXTREME,
        ),
        reason_codes=(
            "RG_EXTREME_BTC_DROP_1H",
            "RG_EXTREME_INTRADAY_DRAWDOWN",
        ),
        btc_realized_vol_24h=0.09,
        btc_drop_1h=-0.08,
        intraday_drawdown=0.12,
        engine_return_dispersion=0.07,
    )
    recommendation = build_regime_lite_safing_recommendation(
        assessment,
        source_runtime_mode=RuntimeMode.SHADOW,
        timestamp_ms=1_700_000_000_000,
    )
    path.write_text(recommendation.model_dump_json(indent=2), encoding="utf-8")


def _write_info_stress_assessment(path: Path) -> None:
    assessment = InfoStressAssessment(
        pair="BTCUSDT",
        level=InfoStressLevel.EXTREME,
        alert_count=3,
        reason_codes=(
            "INFO_STRESS_SPREAD_EXPLOSION",
            "INFO_STRESS_DEPTH_RATIO_COLLAPSE",
            "INFO_STRESS_CANCELLATION_SPIKE",
        ),
        entries_blocked=True,
        entries_blocked_until_ts=1_700_086_400,
        detail="info_stress reached EXTREME with 3 active anomaly signal(s)",
    )
    path.write_text(assessment.model_dump_json(indent=2), encoding="utf-8")


def _real_exports_dir(*, profile_scope: ProfileId = ProfileId.COMPLETE) -> Path:
    export_dir = repo_build_path(
        "local_replay_shadow_runner_tests",
        f"real_exports_{uuid4().hex}",
    )
    export_dir.mkdir(parents=True, exist_ok=False)
    execute_local_replay_export(
        export_dir,
        ReplayExecutionInput(
            run_manifest=ReplayRunManifest(
                run_id="run-local-export-1",
                strategy_id="strategy-a-1",
                strategy_version="a.v2.0",
                strategy_classification=StrategyClassification.A_VARIANT,
                lineage_version="a.v2.0.r3",
                profile_scope=profile_scope,
                engine_scope=("engine_a", "engine_b"),
                tested_pairs=("BTCUSDT", "ETHUSDT"),
                dataset_manifest_id="dataset-export-20260401",
                timeframe_scope="2026-03-01/2026-03-31",
                feature_set_version="2.0.0",
                transform_set_version="2.0.0",
                formula_set_version="formula.v2",
                scoring_version="score.v2",
                regime_version="regime.v2",
                risk_policy_version="risk.v2",
                cost_model_version="cost.v2",
                performance_mode="research_fast_mode",
                artifact_schema_version="2.0.0",
                artifact_hash="artifact-hash-local-export-1",
                clock_id="clock-local-export-1",
                start_timestamp_ms=1_700_000_000_000,
                end_timestamp_ms=1_700_003_600_000,
                tick_count=360,
                record_count=2048,
            ),
            total_opportunities=3,
            dtr_records=(
                build_dtr(
                    dtr_id="run-local-export-1:dtr:1",
                    pair="BTCUSDT",
                    engine_id="engine_a",
                    decision_state=DecisionState.SELECTED,
                    expected_cost=0.0010,
                    realized_cost=0.0011,
                    gross_return=0.0020,
                    ce_expected=0.0006,
                    runtime_mode="local_replay",
                    input_source="local_replay",
                    timestamp=1_700_000_000.0,
                ),
                build_dtr(
                    dtr_id="run-local-export-1:dtr:2",
                    pair="ETHUSDT",
                    engine_id="engine_b",
                    decision_state=DecisionState.REJECTED_RANKING,
                    expected_cost=0.0013,
                    realized_cost=0.0,
                    gross_return=-0.0003,
                    ce_expected=0.0001,
                    runtime_mode="local_replay",
                    input_source="local_replay",
                    timestamp=1_700_000_060.0,
                ),
            ),
            feature_bridge_payload={
                "bridge": "ok",
                "dataset_id": "dataset-export-20260401",
                "feature_set_version": "2.0.0",
                "transform_set_version": "2.0.0",
                "pairs": ["BTCUSDT", "ETHUSDT"],
                "engines": ["engine_a", "engine_b"],
            },
            parity_diagnostics_payload={
                "parity_status": "ok",
                "dataset_id": "dataset-export-20260401",
                "decision_match_rate": 1.0,
            },
            review_notes=("runner integration export",),
        ),
    )
    return export_dir


def _chunked_exports_dir() -> Path:
    export_dir = repo_build_path(
        "local_replay_shadow_runner_tests",
        f"chunked_exports_{uuid4().hex}",
    )
    export_dir.mkdir(parents=True, exist_ok=False)
    dataset = HistoricalReplayDataset.from_records(
        dataset_id="dataset-export-chunked-20260401",
        source_path="inmemory://dataset-export-chunked-20260401",
        source="test_dataset",
        records=(
            HistoricalReplayOpportunity(
                opportunity_id="chunk-op-1",
                timestamp_ms=1_700_000_000_000,
                pair="BTCUSDT",
                engine_id="engine_a",
                raw_score=0.91,
                penalized_score=0.88,
                final_score=0.86,
                expected_edge_bps=17.0,
                spread_bps=3.0,
                slippage_bps=4.0,
                latency_penalty_bps=1.0,
                fill_ratio=1.0,
                target_decision_state="executed",
                production_decision_state="executed",
                production_final_score=0.86,
                production_expected_cost=0.00086,
                candidate_size=1.0,
                final_size=1.0,
                gross_return_bps=18.0,
                feature_values={"spread_bps": 3.0},
            ),
            HistoricalReplayOpportunity(
                opportunity_id="chunk-op-2",
                timestamp_ms=1_700_000_060_000,
                pair="ETHUSDT",
                engine_id="engine_b",
                raw_score=0.84,
                penalized_score=0.8,
                final_score=0.77,
                expected_edge_bps=9.0,
                spread_bps=4.0,
                slippage_bps=3.0,
                latency_penalty_bps=1.0,
                fill_ratio=1.0,
                target_decision_state="executed",
                production_decision_state="executed",
                production_final_score=0.77,
                production_expected_cost=0.00077,
                candidate_size=1.0,
                final_size=1.0,
                gross_return_bps=11.0,
                feature_values={"spread_bps": 4.0},
            ),
            HistoricalReplayOpportunity(
                opportunity_id="chunk-op-3",
                timestamp_ms=1_700_000_120_000,
                pair="SOLUSDT",
                engine_id="engine_c",
                raw_score=0.62,
                penalized_score=0.58,
                final_score=0.52,
                expected_edge_bps=6.0,
                spread_bps=6.0,
                slippage_bps=2.0,
                latency_penalty_bps=1.0,
                fill_ratio=0.5,
                target_decision_state="reduced",
                production_decision_state="reduced",
                production_final_score=0.52,
                production_expected_cost=0.00071,
                candidate_size=1.0,
                final_size=0.5,
                gross_return_bps=5.0,
                feature_values={"spread_bps": 6.0},
            ),
        ),
    )
    orchestrate_local_replay_export(
        ReplayOrchestratorRequest(
            output_dir=export_dir,
            run_id="run-local-export-chunked-1",
            strategy_id="strategy-a-chunked-1",
            strategy_version="a.v2.1",
            strategy_classification=StrategyClassification.A_VARIANT,
            lineage_version="a.v2.1.r1",
            performance_mode="research_fast_mode",
            input_kind="historical_dataset",
            dataset=dataset,
            chunk_count=3,
            run_all_chunks=True,
        )
    )
    return export_dir


def test_export_local_replay_shadow_run_writes_governed_chain_sidecars():
    runner = _load_runner_module()
    output_dir = _scratch_dir("runner")

    try:
        artifacts = runner.export_local_replay_shadow_run(output_dir)

        assert artifacts.run_manifest_json_path is None
        assert artifacts.replay_plan_json_path.exists()
        assert artifacts.import_summary_json_path.exists()
        assert artifacts.local_replay_evidence_json_path.exists()
        assert artifacts.baseline_payload_json_path.exists()
        assert artifacts.candidate_payload_json_path.exists()
        assert artifacts.engine_shadow_evidence_json_path.exists()
        assert artifacts.shadow_input_json_path.exists()
        assert artifacts.shadow_runtime_evidence_json_path.exists()
        assert artifacts.shadow_summary_json_path.exists()
        assert artifacts.shadow_day_record_json_path.exists()
        assert artifacts.shadow_report_json_path.exists()
        assert artifacts.shadow_days_dir_path.exists()
        assert artifacts.shadow_session_summary_json_path.exists()
        assert artifacts.shadow_session_registry_json_path.exists()
        assert artifacts.upload_request_json_path is not None and artifacts.upload_request_json_path.exists()
        assert artifacts.upload_decision_json_path is not None and artifacts.upload_decision_json_path.exists()

        import_summary = json.loads(artifacts.import_summary_json_path.read_text(encoding="utf-8"))
        upload_request = json.loads(
            artifacts.upload_request_json_path.read_text(encoding="utf-8")
        )
        upload_decision = json.loads(
            artifacts.upload_decision_json_path.read_text(encoding="utf-8")
        )
        local_replay_evidence = json.loads(
            artifacts.local_replay_evidence_json_path.read_text(encoding="utf-8")
        )
        candidate_payload = json.loads(
            artifacts.candidate_payload_json_path.read_text(encoding="utf-8")
        )
        engine_shadow_evidence = json.loads(
            artifacts.engine_shadow_evidence_json_path.read_text(encoding="utf-8")
        )
        shadow_input = json.loads(artifacts.shadow_input_json_path.read_text(encoding="utf-8"))
        shadow_runtime_evidence = json.loads(
            artifacts.shadow_runtime_evidence_json_path.read_text(encoding="utf-8")
        )
        shadow_summary = json.loads(artifacts.shadow_summary_json_path.read_text(encoding="utf-8"))
        shadow_day_record = json.loads(
            artifacts.shadow_day_record_json_path.read_text(encoding="utf-8")
        )
        shadow_report = json.loads(
            artifacts.shadow_report_json_path.read_text(encoding="utf-8")
        )
        shadow_session_summary = json.loads(
            artifacts.shadow_session_summary_json_path.read_text(encoding="utf-8")
        )
        shadow_session_registry = json.loads(
            artifacts.shadow_session_registry_json_path.read_text(encoding="utf-8")
        )

        assert import_summary["accepted"] is True
        assert import_summary["validation_status"] == "accepted"
        assert import_summary["ttl_status"] == "active"
        assert import_summary["ttl_reasons"] == []
        assert import_summary["drift_status"] == "not_observed"
        assert import_summary["drift_reasons"] == []
        assert upload_request["upload_context"] == "LOCAL_LAB"
        assert upload_request["dry_run"] is True
        assert upload_decision["accepted"] is True
        assert upload_decision["status"] == "DRY_RUN_OK"
        assert local_replay_evidence["data_source"] == "recorded_replay"
        assert local_replay_evidence["replay_useful_ready"] is True
        assert candidate_payload["replay_import"]["validation_status"] == "accepted"
        assert candidate_payload["replay_import"]["signature_check_status"] == "verified"
        assert candidate_payload["system"]["build14_status"] == "warning"
        assert len(candidate_payload["build14"]["reader_projections"]) == 9
        reader_projections = {
            reader["reader_name"]: reader for reader in candidate_payload["build14"]["reader_projections"]
        }
        assert set(reader_projections) == {
            "market_toxicity_snapshot",
            "execution_fragility_score",
            "lob_deep_filter_vwa",
            "order_book_imbalance",
            "micro_edge_exit_governor",
            "micro_edge_entry_timing_layer",
            "false_breakout_model",
            "hurst_regime_classifier",
            "competition_monitor",
        }
        assert (
            reader_projections["market_toxicity_snapshot"]["structured_log_key"]
            == "build14.shadow_enabled.market_toxicity"
        )
        assert "backlog=10" in reader_projections["market_toxicity_snapshot"]["detail"]
        assert (
            reader_projections["false_breakout_model"]["structured_log_key"]
            == "build14.shadow_enabled.false_breakout_model"
        )
        assert reader_projections["execution_fragility_score"]["status"] == "elevated"
        assert reader_projections["hurst_regime_classifier"]["status"] == "elevated"
        assert len(engine_shadow_evidence) == 4
        engine_runtime_evidence = {
            entry["component_id"]: entry for entry in engine_shadow_evidence
        }
        assert tuple(engine_runtime_evidence) == (
            "engine_a",
            "engine_b",
            "engine_c",
            "engine_d",
        )
        assert engine_runtime_evidence["engine_a"]["runtime_status"] == "accepted"
        assert engine_runtime_evidence["engine_b"]["runtime_status"] == "accepted"
        assert engine_runtime_evidence["engine_c"]["runtime_status"] == "hard_blocked"
        assert engine_runtime_evidence["engine_d"]["runtime_status"] == "accepted"
        assert "features=" in engine_runtime_evidence["engine_a"]["scoring_summary"]
        assert engine_runtime_evidence["engine_a"]["risk_summary"] == "risk=accept / no blocker triggered"
        assert "SELECTION_SELECTED" in engine_runtime_evidence["engine_a"]["scoring_reason_codes"]
        assert engine_runtime_evidence["engine_a"]["risk_reason_codes"] == []
        assert (
            engine_runtime_evidence["engine_c"]["details"]["refusal_record"]["category"]
            == "hard_block"
        )
        assert engine_runtime_evidence["engine_c"]["details"]["refusal_record"]["reason_codes"] == [
            "engine_c.runtime.coordination_input_missing",
            "engine_c.runtime.coordination_required",
        ]
        engine_metrics = {
            entry["engine_id"]: entry for entry in candidate_payload["engines"]
        }
        assert "features=" in engine_metrics["engine_a"]["scoring_summary"]
        assert engine_metrics["engine_a"]["risk_summary"] == "risk=accept / no blocker triggered"
        assert "SELECTION_SELECTED" in engine_metrics["engine_a"]["scoring_reason_codes"]
        assert "PORTFOLIO_COMPATIBLE" in engine_metrics["engine_a"]["scoring_reason_codes"]
        assert shadow_input["validation_set"]["runtime_data_source"] == "recorded_replay"
        assert shadow_input["validation_set"]["runtime_continuous_hours"] >= 24.0
        component_assessments = {
            entry["component_id"]: entry
            for entry in shadow_input["validation_set"]["component_assessments"]
        }
        assert "structure=" in component_assessments["engine_a"]["evidence_summary"]
        assert "z_score=" in component_assessments["engine_b"]["evidence_summary"]
        assert "breakout_type=" in component_assessments["engine_c"]["evidence_summary"]
        assert "origin=" in component_assessments["engine_d"]["evidence_summary"]
        assert shadow_runtime_evidence["event_loop_ready"] is True
        assert shadow_runtime_evidence["config_loaded"] is True
        assert shadow_runtime_evidence["shadow_dtr_persisted"] is True
        assert shadow_runtime_evidence["continuous_hours"] >= 24.0
        assert shadow_summary["decision"]["accepted"] is False
        assert shadow_summary["decision"]["verdict"] == "blocked"
        assert shadow_summary["shadow_days_completed"] == 1
        assert shadow_summary["shadow_report_ready"] is False
        assert shadow_summary["runtime_evidence_ready"] is True
        assert shadow_day_record["passed_all_gates"] is True
        assert shadow_day_record["metrics_summary"]["dominant_cluster"] == "unclustered"
        assert shadow_report["consecutive_days"] == 1
        assert shadow_report["data_infra_report_ready"] is True
        assert shadow_report["inter_engine_comparison_ready"] is True
        assert shadow_report["build14_contribution_ready"] is True
        assert shadow_report["portfolio_report_ready"] is True
        assert shadow_report["ui_alerting_report_ready"] is True
        assert len(shadow_report["rendered_sections"]) == 7
        assert "30_day_counter" in shadow_report["missing_sections"]
        assert shadow_session_summary["requested_shadow_days"] == 1
        assert shadow_session_summary["recorded_shadow_days_this_run"] == 1
        assert shadow_session_summary["base_session_date"] == "2023-11-14"
        assert len(shadow_session_summary["daily_record_paths"]) == 1
        assert len(shadow_session_registry["entries"]) == 1
        assert shadow_session_registry["entries"][0]["session_date"] == "2023-11-14"
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_export_local_replay_shadow_run_accepts_real_export_directory():
    runner = _load_runner_module()
    output_dir = _scratch_dir("real_dir")
    export_dir = _real_exports_dir()

    try:
        artifacts = runner.export_local_replay_shadow_run(output_dir, export_dir=export_dir)

        assert artifacts.run_manifest_json_path is not None
        assert artifacts.run_manifest_json_path.exists()
        assert artifacts.upload_request_json_path is not None and artifacts.upload_request_json_path.exists()
        assert artifacts.upload_decision_json_path is not None and artifacts.upload_decision_json_path.exists()
        import_summary = json.loads(artifacts.import_summary_json_path.read_text(encoding="utf-8"))
        upload_decision = json.loads(
            artifacts.upload_decision_json_path.read_text(encoding="utf-8")
        )
        replay_plan = json.loads(artifacts.replay_plan_json_path.read_text(encoding="utf-8"))
        local_replay_evidence = json.loads(
            artifacts.local_replay_evidence_json_path.read_text(encoding="utf-8")
        )
        run_manifest = json.loads(artifacts.run_manifest_json_path.read_text(encoding="utf-8"))
        shadow_day_record = json.loads(
            artifacts.shadow_day_record_json_path.read_text(encoding="utf-8")
        )

        assert import_summary["accepted"] is True
        assert import_summary["ttl_status"] == "active"
        assert import_summary["ttl_reasons"] == []
        assert import_summary["drift_status"] == "not_observed"
        assert import_summary["drift_reasons"] == []
        assert import_summary["signature_check_status"] == "verified"
        assert upload_decision["status"] == "DRY_RUN_OK"
        assert import_summary["artifact_id"] == "artifact-hash-local-export-1"
        assert import_summary["lineage_version"] == "a.v2.0.r3"
        assert import_summary["review_export_ref"] == str((export_dir / "review_export.md").resolve())
        assert import_summary["feature_bridge_ref"] == str((export_dir / "feature_bridge.json").resolve())
        assert import_summary["parity_diagnostics_ref"] == str((export_dir / "parity_diagnostics.json").resolve())
        assert import_summary["replay_metrics_ref"] == str((export_dir / "replay_metrics.json").resolve())
        assert import_summary["replay_dtr_ref"] == str((export_dir / "replay_dtr.jsonl").resolve())
        assert replay_plan["request"]["correlation_id"] == "run-local-export-1"
        assert replay_plan["request"]["lineage_version"] == "a.v2.0.r3"
        assert replay_plan["request"]["strategy_classification"] == "a_variant"
        assert replay_plan["dataset_ref"]["dataset_id"] == "dataset-export-20260401"
        assert replay_plan["clock_ref"]["clock_id"] == "clock-local-export-1"
        assert replay_plan["bundle"]["manifest"]["strategy_version"] == "a.v2.0"
        assert replay_plan["bundle"]["payload_refs"] == [
            str((export_dir / "review_export.md").resolve()),
            str((export_dir / "feature_bridge.json").resolve()),
            str((export_dir / "parity_diagnostics.json").resolve()),
            str((export_dir / "replay_metrics.json").resolve()),
            str((export_dir / "replay_dtr.jsonl").resolve()),
        ]
        assert run_manifest["strategy_id"] == "strategy-a-1"
        assert run_manifest["performance_mode"] == "research_fast_mode"
        assert local_replay_evidence["replay_useful_ready"] is True
        assert abs(shadow_day_record["metrics_summary"]["dtr_coverage"] - (2 / 3)) < 1e-6
        assert shadow_day_record["metrics_summary"]["hard_block_rate"] == 0.0
        assert shadow_day_record["metrics_summary"]["phantom_trade_count"] == 0.0
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_export_local_replay_shadow_run_rejects_session_date_mismatch_with_export_metadata():
    runner = _load_runner_module()
    output_dir = _scratch_dir("real_dir_session_mismatch")
    export_dir = _real_exports_dir()

    try:
        with pytest.raises(
            ValueError,
            match="Explicit session_date does not match governed export metadata",
        ):
            runner.export_local_replay_shadow_run(
                output_dir,
                export_dir=export_dir,
                session_date="2026-04-01",
            )
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_export_local_replay_shadow_run_preserves_light_profile_and_fails_closed():
    runner = _load_runner_module()
    output_dir = _scratch_dir("real_dir_light_profile")
    export_dir = _real_exports_dir(profile_scope=ProfileId.LIGHT)

    try:
        artifacts = runner.export_local_replay_shadow_run(output_dir, export_dir=export_dir)

        import_summary = json.loads(artifacts.import_summary_json_path.read_text(encoding="utf-8"))
        replay_plan = json.loads(artifacts.replay_plan_json_path.read_text(encoding="utf-8"))

        assert import_summary["accepted"] is False
        assert "governed import requires source_profile=COMPLETE" in import_summary["rejection_reasons"]
        assert import_summary["signature_check_status"] == "verified"
        assert replay_plan["request"]["profile"] == ProfileId.LIGHT.value
        assert replay_plan["bundle"]["manifest"]["source_profile"] == ProfileId.LIGHT.value
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_export_local_replay_shadow_run_rejects_export_dir_without_run_manifest():
    runner = _load_runner_module()
    output_dir = _scratch_dir("real_dir_missing_manifest")
    export_dir = _real_exports_dir()

    try:
        (export_dir / "replay_run_manifest.json").unlink()

        with pytest.raises(
            FileNotFoundError,
            match="Missing governed export file for replay_run_manifest",
        ):
            runner.export_local_replay_shadow_run(output_dir, export_dir=export_dir)
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_runner_main_accepts_output_dir():
    runner = _load_runner_module()
    output_dir = _scratch_dir("cli")

    try:
        exit_code = runner.main(["--output-dir", str(output_dir)])

        assert exit_code == 0
        assert (output_dir / "local_replay_shadow.shadow_summary.json").exists()
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_export_local_replay_shadow_run_autoloads_execution_runtime_projection_bridge():
    runner = _load_runner_module()
    output_dir = _scratch_dir("runtime_projection")

    try:
        _write_execution_runtime_projection(
            output_dir / "local_lab_execution_runtime_projection.json"
        )

        artifacts = runner.export_local_replay_shadow_run(output_dir)

        candidate_payload = json.loads(
            artifacts.candidate_payload_json_path.read_text(encoding="utf-8")
        )
        bridge = candidate_payload["execution_runtime_projection_bridge"]

        assert bridge["status"] == "healthy"
        assert bridge["projection_status"] == "ready"
        assert bridge["configured"] is True
        assert bridge["projection_found"] is True
        assert bridge["projection_loaded"] is True
        assert bridge["rate_limit_model_loaded"] is True
        assert bridge["spread_guard_model_loaded"] is True
        assert bridge["slippage_model_loaded"] is True
        assert bridge["ready_consumer_count"] == 3
        assert bridge["partial_consumer_count"] == 0
        assert bridge["blocked_consumer_count"] == 0
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_runner_main_accepts_execution_runtime_projection_path():
    runner = _load_runner_module()
    output_dir = _scratch_dir("cli_runtime_projection")
    projection_path = output_dir / "external_execution_runtime_projection.json"

    try:
        _write_execution_runtime_projection(projection_path)

        exit_code = runner.main(
            [
                "--output-dir",
                str(output_dir),
                "--execution-runtime-projection-path",
                str(projection_path),
            ]
        )

        assert exit_code == 0
        candidate_payload = json.loads(
            (output_dir / "local_replay_shadow.candidate_payload.json").read_text(
                encoding="utf-8"
            )
        )
        assert (
            candidate_payload["execution_runtime_projection_bridge"]["projection_path"]
            == str(projection_path)
        )
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_export_local_replay_shadow_run_accepts_regime_lite_inputs():
    runner = _load_runner_module()
    output_dir = _scratch_dir("regime_lite_inputs")
    assessment_path = output_dir / "regime_lite_assessment.json"
    recommendation_path = output_dir / "regime_lite_safing_recommendation.json"

    try:
        _write_regime_lite_assessment(assessment_path)
        _write_regime_lite_safing_recommendation(recommendation_path)

        artifacts = runner.export_local_replay_shadow_run(
            output_dir,
            regime_lite_assessment_path=assessment_path,
            regime_lite_safing_recommendation_path=recommendation_path,
        )

        shadow_summary = json.loads(
            artifacts.shadow_summary_json_path.read_text(encoding="utf-8")
        )
        governance = shadow_summary["regime_lite_governance"]

        assert governance["status"] == "ready"
        assert governance["state"] == "extreme"
        assert governance["entries_blocked"] is True
        assert governance["safing_severity"] == "halt_recommended"
        assert governance["should_exit_all"] is True
        assert governance["recommended_operator_action"] == "set_halted"
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_export_local_replay_shadow_run_autoloads_regime_lite_inputs():
    runner = _load_runner_module()
    output_dir = _scratch_dir("regime_lite_autoload")

    try:
        _write_regime_lite_assessment(output_dir / "regime_lite_assessment.json")
        _write_regime_lite_safing_recommendation(
            output_dir / "regime_lite_safing_recommendation.json"
        )

        artifacts = runner.export_local_replay_shadow_run(output_dir)

        shadow_summary = json.loads(
            artifacts.shadow_summary_json_path.read_text(encoding="utf-8")
        )
        governance = shadow_summary["regime_lite_governance"]

        assert governance["status"] == "ready"
        assert governance["state"] == "extreme"
        assert governance["safing_severity"] == "halt_recommended"
        assert governance["should_exit_all"] is True
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_export_local_replay_shadow_run_accepts_info_stress_input():
    runner = _load_runner_module()
    output_dir = _scratch_dir("info_stress_input")
    assessment_path = output_dir / "info_stress_assessment.json"

    try:
        _write_info_stress_assessment(assessment_path)

        artifacts = runner.export_local_replay_shadow_run(
            output_dir,
            info_stress_assessment_path=assessment_path,
        )

        shadow_summary = json.loads(
            artifacts.shadow_summary_json_path.read_text(encoding="utf-8")
        )
        governance = shadow_summary["info_stress_governance"]

        assert governance["status"] == "assessment_only"
        assert governance["level"] == "extreme"
        assert governance["alert_count"] == 3
        assert governance["entries_blocked"] is True
        assert governance["entries_blocked_until_ts"] == 1_700_086_400
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_export_local_replay_shadow_run_autoloads_info_stress_input():
    runner = _load_runner_module()
    output_dir = _scratch_dir("info_stress_autoload")

    try:
        _write_info_stress_assessment(output_dir / "info_stress_assessment.json")

        artifacts = runner.export_local_replay_shadow_run(output_dir)

        shadow_summary = json.loads(
            artifacts.shadow_summary_json_path.read_text(encoding="utf-8")
        )
        governance = shadow_summary["info_stress_governance"]

        assert governance["status"] == "assessment_only"
        assert governance["level"] == "extreme"
        assert governance["entries_blocked"] is True
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_export_local_replay_shadow_run_accepts_chunked_aggregate_export_directory():
    runner = _load_runner_module()
    output_dir = _scratch_dir("chunked_dir")
    export_dir = _chunked_exports_dir()

    try:
        artifacts = runner.export_local_replay_shadow_run(output_dir, export_dir=export_dir)

        import_summary = json.loads(artifacts.import_summary_json_path.read_text(encoding="utf-8"))
        shadow_summary = json.loads(artifacts.shadow_summary_json_path.read_text(encoding="utf-8"))
        run_manifest = json.loads(artifacts.run_manifest_json_path.read_text(encoding="utf-8"))
        shadow_report = json.loads(artifacts.shadow_report_json_path.read_text(encoding="utf-8"))

        assert import_summary["accepted"] is True
        assert import_summary["ttl_status"] == "active"
        assert import_summary["drift_status"] == "not_observed"
        assert import_summary["artifact_id"] == "artifact-run-local-export-chunked-1"
        assert import_summary["feature_bridge_ref"] == str((export_dir / "feature_bridge.json").resolve())
        assert import_summary["replay_dtr_ref"] == str((export_dir / "replay_dtr.jsonl").resolve())
        assert run_manifest["record_count"] == 3
        assert shadow_summary["decision"]["accepted"] is False
        assert shadow_summary["shadow_days_completed"] == 1
        assert shadow_summary["shadow_report_ready"] is False
        assert shadow_summary["runtime_evidence_ready"] is True
        assert shadow_report["go_no_go_report_ready"] is True
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_export_local_replay_shadow_run_materializes_multiple_governed_days():
    runner = _load_runner_module()
    output_dir = _scratch_dir("multi_days")

    try:
        artifacts = runner.export_local_replay_shadow_run(output_dir, shadow_days=3)

        shadow_report = json.loads(artifacts.shadow_report_json_path.read_text(encoding="utf-8"))
        shadow_session_summary = json.loads(
            artifacts.shadow_session_summary_json_path.read_text(encoding="utf-8")
        )

        assert shadow_report["consecutive_days"] == 3
        assert shadow_session_summary["requested_shadow_days"] == 3
        assert shadow_session_summary["recorded_shadow_days_this_run"] == 3
        assert len(shadow_session_summary["daily_record_paths"]) == 3
        for record_path in shadow_session_summary["daily_record_paths"]:
            assert Path(record_path).exists()
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_export_local_replay_shadow_run_resumes_existing_shadow_session():
    runner = _load_runner_module()
    output_dir = _scratch_dir("resume_days")

    try:
        runner.export_local_replay_shadow_run(output_dir, shadow_days=2)
        artifacts = runner.export_local_replay_shadow_run(output_dir, shadow_days=2)

        shadow_report = json.loads(artifacts.shadow_report_json_path.read_text(encoding="utf-8"))
        shadow_session_summary = json.loads(
            artifacts.shadow_session_summary_json_path.read_text(encoding="utf-8")
        )

        assert shadow_report["consecutive_days"] == 4
        assert shadow_session_summary["session_resumed"] is True
        assert shadow_session_summary["starting_consecutive_days"] == 2
        assert shadow_session_summary["recorded_shadow_days_this_run"] == 2
        assert len(shadow_session_summary["daily_record_paths"]) == 2
        assert Path(shadow_session_summary["daily_record_paths"][0]).name.endswith("0003.json")
        assert Path(shadow_session_summary["daily_record_paths"][1]).name.endswith("0004.json")
        assert (artifacts.shadow_days_dir_path / "local_replay_shadow.day_0001.json").exists()
        assert (artifacts.shadow_days_dir_path / "local_replay_shadow.day_0004.json").exists()
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_export_local_replay_shadow_run_recovers_counter_semantics_after_counter_corruption():
    runner = _load_runner_module()
    output_dir = _scratch_dir("recover_counter")

    try:
        runner.export_local_replay_shadow_run(output_dir, shadow_days=2)
        (output_dir / "shadow_counter_complete.json").write_text(
            "{ broken counter state",
            encoding="utf-8",
        )

        artifacts = runner.export_local_replay_shadow_run(output_dir, shadow_days=1)

        shadow_report = json.loads(artifacts.shadow_report_json_path.read_text(encoding="utf-8"))
        shadow_session_summary = json.loads(
            artifacts.shadow_session_summary_json_path.read_text(encoding="utf-8")
        )
        shadow_session_registry = json.loads(
            artifacts.shadow_session_registry_json_path.read_text(encoding="utf-8")
        )
        counter = ShadowDayCounter(output_dir, ShadowProfile.COMPLETE)

        assert counter.get_status().last_error is None
        assert shadow_report["consecutive_days"] == 3
        assert shadow_session_summary["session_resumed"] is True
        assert shadow_session_summary["starting_consecutive_days"] == 2
        assert shadow_session_summary["base_session_date"] == "2023-11-16"
        assert len(shadow_session_registry["entries"]) == 3
        assert shadow_session_registry["entries"][-1]["session_date"] == "2023-11-16"
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_export_local_replay_shadow_run_recovers_double_corruption_from_day_records():
    runner = _load_runner_module()
    output_dir = _scratch_dir("recover_double_corruption")

    try:
        runner.export_local_replay_shadow_run(output_dir, shadow_days=2)
        (output_dir / "shadow_counter_complete.json").write_text(
            "{ broken counter state",
            encoding="utf-8",
        )
        (output_dir / "shadow_session_registry.json").write_text(
            "{ broken registry state",
            encoding="utf-8",
        )

        artifacts = runner.export_local_replay_shadow_run(output_dir, shadow_days=1)

        shadow_report = json.loads(artifacts.shadow_report_json_path.read_text(encoding="utf-8"))
        shadow_session_summary = json.loads(
            artifacts.shadow_session_summary_json_path.read_text(encoding="utf-8")
        )
        shadow_session_registry = json.loads(
            artifacts.shadow_session_registry_json_path.read_text(encoding="utf-8")
        )

        assert shadow_report["consecutive_days"] == 3
        assert shadow_session_summary["session_resumed"] is True
        assert shadow_session_summary["starting_consecutive_days"] == 2
        assert shadow_session_summary["base_session_date"] == "2023-11-16"
        assert len(shadow_session_registry["entries"]) == 3
        assert shadow_session_registry["entries"][0]["run_id"] == "recovered:shadow_session_registry"
        assert shadow_session_registry["entries"][0]["artifact_id"] == "recovered:artifact"
        assert shadow_session_registry["entries"][1]["lineage_version"] == "recovered:lineage"
        assert shadow_session_registry["entries"][-1]["run_id"] == "local-replay-shadow-demo-run"
        assert shadow_session_registry["entries"][-1]["session_date"] == "2023-11-16"
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_export_local_replay_shadow_run_rejects_duplicate_session_date_before_counter_mutation():
    runner = _load_runner_module()
    output_dir = _scratch_dir("duplicate_session_date")

    try:
        runner.export_local_replay_shadow_run(
            output_dir,
            shadow_days=1,
            session_date="2026-04-01",
        )

        with pytest.raises(ValueError, match="already recorded session_date"):
            runner.export_local_replay_shadow_run(
                output_dir,
                shadow_days=1,
                session_date="2026-04-01",
            )

        counter = ShadowDayCounter(output_dir, ShadowProfile.COMPLETE)
        registry = ShadowSessionRegistry(output_dir)
        assert counter.get_status().consecutive_days == 1
        assert len(registry.get_entries()) == 1
        assert registry.get_entries()[0].session_date == "2026-04-01"
        assert not (output_dir / "shadow_days" / "local_replay_shadow.day_0002.json").exists()
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
