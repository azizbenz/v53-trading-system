from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from uuid import uuid4
from datetime import datetime, timezone

from interface_contracts.domain_types import ProfileId, RuntimeMode, StrategyClassification
from local_replay_runtime.artifact_exporter import (
    ReplayArtifactExportRequest,
    export_local_replay_artifact,
)
from local_replay_runtime.local_lab_execution_telemetry_artifact import (
    LocalLabExecutionTelemetryArtifact,
)
from local_replay_runtime.replay_metrics_collector import build_replay_metrics_summary
from local_replay_runtime.replay_run_manifest import ReplayRunManifest
from local_replay_runtime.shadow_execution_simulator import ReplayParityDiagnosticsSummary
from monitoring.local_lab_bundle_loader import load_local_lab_monitoring_bundle
from meta_minimal.dtr_core.decision_state_encoder import DecisionState
from meta_minimal.dtr_core.dtr_record_builder import build_dtr
from scripts.run_local_lab_analysis_bundle import main


def _scratch_dir() -> Path:
    return Path("build/pytest-local-lab-analysis-bundle") / uuid4().hex


def _records():
    return (
        build_dtr(
            dtr_id="dtr-a-1",
            pair="BTCUSDT",
            engine_id="engine_a",
            decision_state=DecisionState.EXECUTED,
            expected_cost=0.0010,
            realized_cost=0.0009,
            gross_return=0.0080,
            ce_expected=0.0030,
            runtime_mode="local_replay",
            input_source="local_replay",
            timestamp=1_700_000_000.0,
        ),
        build_dtr(
            dtr_id="dtr-a-2",
            pair="BTCUSDT",
            engine_id="engine_a",
            decision_state=DecisionState.EXECUTED,
            expected_cost=0.0011,
            realized_cost=0.0010,
            gross_return=0.0083,
            ce_expected=0.0032,
            runtime_mode="local_replay",
            input_source="local_replay",
            timestamp=1_700_000_060.0,
        ),
    )


def _baseline_records():
    return (
        build_dtr(
            dtr_id="dtr-a-1",
            pair="BTCUSDT",
            engine_id="engine_a",
            decision_state=DecisionState.EXECUTED,
            expected_cost=0.0010,
            realized_cost=0.0009,
            gross_return=0.0020,
            ce_expected=0.0015,
            runtime_mode="local_replay",
            input_source="local_replay",
            timestamp=1_700_000_000.0,
        ),
        build_dtr(
            dtr_id="dtr-a-2",
            pair="BTCUSDT",
            engine_id="engine_a",
            decision_state=DecisionState.EXECUTED,
            expected_cost=0.0011,
            realized_cost=0.0010,
            gross_return=0.0021,
            ce_expected=0.0016,
            runtime_mode="local_replay",
            input_source="local_replay",
            timestamp=1_700_000_060.0,
        ),
    )


def _multiscope_records():
    return (
        build_dtr(
            dtr_id="dtr-a-1",
            pair="BTCUSDT",
            engine_id="engine_a",
            decision_state=DecisionState.EXECUTED,
            expected_cost=0.0010,
            realized_cost=0.0009,
            gross_return=0.0080,
            ce_expected=0.0030,
            regime="trend",
            candidate_size=1.0,
            final_size=1.0,
            runtime_mode="local_replay",
            input_source="local_replay",
            timestamp=1_700_000_000.0,
        ),
        build_dtr(
            dtr_id="dtr-a-2",
            pair="BTCUSDT",
            engine_id="engine_a",
            decision_state=DecisionState.EXECUTED,
            expected_cost=0.0011,
            realized_cost=0.0010,
            gross_return=0.0083,
            ce_expected=0.0032,
            regime="range",
            candidate_size=1.0,
            final_size=0.95,
            runtime_mode="local_replay",
            input_source="local_replay",
            timestamp=1_700_000_060.0,
        ),
        build_dtr(
            dtr_id="dtr-b-1",
            pair="ETHUSDT",
            engine_id="engine_b",
            decision_state=DecisionState.EXECUTED,
            expected_cost=0.0010,
            realized_cost=0.0009,
            gross_return=0.0070,
            ce_expected=0.0028,
            regime="trend",
            candidate_size=1.0,
            final_size=1.0,
            runtime_mode="local_replay",
            input_source="local_replay",
            timestamp=1_700_000_120.0,
        ),
        build_dtr(
            dtr_id="dtr-b-2",
            pair="ETHUSDT",
            engine_id="engine_b",
            decision_state=DecisionState.EXECUTED,
            expected_cost=0.0011,
            realized_cost=0.0010,
            gross_return=0.0072,
            ce_expected=0.0030,
            regime="range",
            candidate_size=1.0,
            final_size=0.95,
            runtime_mode="local_replay",
            input_source="local_replay",
            timestamp=1_700_000_180.0,
        ),
    )


def _multiscope_baseline_records():
    return (
        build_dtr(
            dtr_id="dtr-a-1",
            pair="BTCUSDT",
            engine_id="engine_a",
            decision_state=DecisionState.EXECUTED,
            expected_cost=0.0010,
            realized_cost=0.0009,
            gross_return=0.0020,
            ce_expected=0.0015,
            regime="trend",
            candidate_size=1.0,
            final_size=1.0,
            runtime_mode="local_replay",
            input_source="local_replay",
            timestamp=1_700_000_000.0,
        ),
        build_dtr(
            dtr_id="dtr-a-2",
            pair="BTCUSDT",
            engine_id="engine_a",
            decision_state=DecisionState.EXECUTED,
            expected_cost=0.0011,
            realized_cost=0.0010,
            gross_return=0.0021,
            ce_expected=0.0016,
            regime="range",
            candidate_size=1.0,
            final_size=0.95,
            runtime_mode="local_replay",
            input_source="local_replay",
            timestamp=1_700_000_060.0,
        ),
        build_dtr(
            dtr_id="dtr-b-1",
            pair="ETHUSDT",
            engine_id="engine_b",
            decision_state=DecisionState.EXECUTED,
            expected_cost=0.0010,
            realized_cost=0.0009,
            gross_return=0.0018,
            ce_expected=0.0014,
            regime="trend",
            candidate_size=1.0,
            final_size=1.0,
            runtime_mode="local_replay",
            input_source="local_replay",
            timestamp=1_700_000_120.0,
        ),
        build_dtr(
            dtr_id="dtr-b-2",
            pair="ETHUSDT",
            engine_id="engine_b",
            decision_state=DecisionState.EXECUTED,
            expected_cost=0.0011,
            realized_cost=0.0010,
            gross_return=0.0019,
            ce_expected=0.0015,
            regime="range",
            candidate_size=1.0,
            final_size=0.95,
            runtime_mode="local_replay",
            input_source="local_replay",
            timestamp=1_700_000_180.0,
        ),
    )


def _build_review_export_markdown(
    *,
    run_id: str,
    strategy_id: str,
    strategy_version: str,
    lineage_version: str,
    profile_scope: str,
    runtime_mode: str,
    performance_mode: str,
    total_opportunities: int,
    total_records: int,
    dtr_coverage: float,
    status: str,
    decision_match_rate: float,
) -> str:
    return "\n".join(
        [
            "# Governed Review Export",
            f"- run_id: {run_id}",
            f"- strategy_id: {strategy_id}",
            f"- strategy_version: {strategy_version}",
            f"- lineage_version: {lineage_version}",
            f"- profile_scope: {profile_scope}",
            f"- runtime_mode: {runtime_mode}",
            f"- performance_mode: {performance_mode}",
            f"- total_opportunities: {total_opportunities}",
            f"- total_records: {total_records}",
            f"- dtr_coverage: {dtr_coverage:.3f}",
            f"- status: {status}",
            f"- decision_match_rate: {decision_match_rate}",
            "",
        ]
    )


def test_run_local_lab_analysis_bundle_chains_review_and_edge_calibration():
    scratch = _scratch_dir()
    scratch.mkdir(parents=True, exist_ok=False)
    try:
        export_dir = scratch / "export_dir"
        output_root = scratch / "analysis"
        records = _records()
        metrics = build_replay_metrics_summary(records, total_opportunities=len(records))
        parity = ReplayParityDiagnosticsSummary(
            parity_status="passed",
            dataset_id="dataset-analysis-01",
            decision_match_rate=1.0,
            score_match_rate=1.0,
            baseline_status="available",
            score_alignment="aligned",
            cost_alignment="aligned",
            compared_records=len(records),
            shared_core_match=True,
            parity_policy={"kind": "test"},
        )
        run_manifest = ReplayRunManifest(
            run_id="run-analysis-01",
            strategy_id="strat-analysis",
            strategy_version="v5.3",
            strategy_classification=StrategyClassification.A_VARIANT,
            lineage_version="v5.3.lineage",
            profile_scope=ProfileId.COMPLETE,
            runtime_mode=RuntimeMode.LOCAL_REPLAY,
            engine_scope=("engine_a",),
            tested_pairs=("BTCUSDT",),
            dataset_manifest_id="dataset-analysis-01",
            timeframe_scope="2026-04-01/2026-04-02",
            formula_set_version="formula.v1",
            scoring_version="scoring.v1",
            regime_version="regime.v1",
            risk_policy_version="risk.v1",
            cost_model_version="cost.v1",
            performance_mode="shadow_fidelity_mode",
            artifact_hash="artifact-analysis-01",
            clock_id="clock-analysis-01",
            start_timestamp_ms=1_700_000_000_000,
            end_timestamp_ms=1_700_000_060_000,
            tick_count=len(records),
            record_count=len(records),
        )
        export_local_replay_artifact(
            export_dir,
            ReplayArtifactExportRequest(
                run_manifest=run_manifest,
                review_export_markdown=_build_review_export_markdown(
                    run_id=run_manifest.run_id,
                    strategy_id=run_manifest.strategy_id,
                    strategy_version=run_manifest.strategy_version,
                    lineage_version=run_manifest.lineage_version,
                    profile_scope=run_manifest.profile_scope.value,
                    runtime_mode=run_manifest.runtime_mode.value,
                    performance_mode=run_manifest.performance_mode,
                    total_opportunities=metrics.total_opportunities,
                    total_records=metrics.total_records,
                    dtr_coverage=metrics.dtr_coverage,
                    status=parity.parity_status,
                    decision_match_rate=parity.decision_match_rate,
                ),
                feature_bridge_payload={
                    "dataset_id": run_manifest.dataset_manifest_id,
                    "feature_set_version": run_manifest.feature_set_version,
                    "transform_set_version": run_manifest.transform_set_version,
                    "pairs": list(run_manifest.tested_pairs),
                    "engines": list(run_manifest.engine_scope),
                },
                parity_diagnostics_payload=parity.model_dump(mode="json"),
                replay_metrics_payload=metrics.model_dump(mode="json"),
                replay_dtr_records=tuple(record.model_dump(mode="json") for record in records),
            ),
        )

        exit_code = main(
            [
                "--export-dir",
                str(export_dir),
                "--correlation-id",
                "corr-analysis-01",
                "--signed-by",
                "operator.aziz",
                "--output-root",
                str(output_root),
                "--pair",
                "BTCUSDT",
                "--engine-id",
                "engine_a",
                "--bootstrap-samples",
                "250",
                "--min-positive-trades",
                "2",
                "--min-cost-observations",
                "2",
            ]
        )

        assert exit_code == 0
        summary = json.loads((output_root / "local_lab_analysis_summary.json").read_text(encoding="utf-8"))
        review_input = json.loads((output_root / "post_trade_review" / "governed_input_summary.json").read_text(encoding="utf-8"))
        edge_input = json.loads((output_root / "edge_gate.input_summary.json").read_text(encoding="utf-8"))

        assert summary["correlation_id"] == "corr-analysis-01"
        assert summary["run_id"] == "run-analysis-01"
        assert summary["dataset_manifest_id"] == "dataset-analysis-01"
        assert summary["selected_pair"] == "BTCUSDT"
        assert summary["selected_engine_id"] == "engine_a"
        assert summary["artifact_ablation_study_path"].endswith("artifact_ablation_study.json")
        assert summary["review_ready"] is True
        assert summary["trade_loss_attribution_ready"] is True
        assert summary["walk_forward_review_ready"] is False
        assert summary["artifact_ablation_ready"] is False
        assert summary["artifact_proof_ready"] is False
        assert summary["artifact_proof_summary_path"].endswith("artifact_proof_summary.json")
        assert summary["artifact_proof_assessment_path"].endswith("artifact_proof_assessment.json")
        assert summary["artifact_release_candidate_path"].endswith("artifact_release_candidate.json")
        assert summary["local_lab_recalibration_plan_path"].endswith(
            "local_lab_recalibration_plan.json"
        )
        assert summary["artifact_import_dry_run_bridge_path"].endswith(
            "artifact_import_dry_run_bridge.json"
        )
        assert summary["artifact_promotion_readiness_summary_path"].endswith(
            "artifact_promotion_readiness_summary.json"
        )
        assert summary["local_lab_monitoring_projection_path"].endswith(
            "local_lab_monitoring_projection.json"
        )
        assert summary["local_lab_observability_export_path"].endswith(
            "local_lab_observability_export.json"
        )
        assert summary["local_lab_observability_text_path"].endswith(
            "local_lab_observability.prom"
        )
        assert summary["local_lab_monitoring_backend_payload_path"].endswith(
            "local_lab_monitoring_backend_payload.json"
        )
        assert summary["local_lab_monitoring_backend_status"] == "warning"
        assert summary["local_lab_monitoring_ingestion_summary_path"].endswith(
            "local_lab_monitoring_ingestion_summary.json"
        )
        assert summary["local_lab_monitoring_ingestion_ready"] is True
        assert summary["local_lab_loss_surrogate_path"].endswith(
            "local_lab_loss_surrogate_report.json"
        )
        assert summary["loss_surrogate_status"] == "insufficient_executed_records"
        assert summary["loss_surrogate_ready"] is False
        assert summary["local_lab_calibration_methods_review_path"].endswith(
            "local_lab_calibration_methods_review.json"
        )
        assert summary["calibration_methods_review_status"] == "partial"
        assert summary["calibration_methods_review_ready"] is False
        assert summary["calibration_methods_dsr_pass"] is None
        assert summary["calibration_methods_walk_forward_plan_ready"] is False
        assert summary["local_lab_execution_review_path"].endswith(
            "local_lab_execution_review.json"
        )
        assert summary["local_lab_execution_runtime_projection_path"].endswith(
            "local_lab_execution_runtime_projection.json"
        )
        assert summary["execution_review_status"] == "partial"
        assert summary["execution_review_ready"] is False
        assert summary["execution_runtime_projection_status"] == "partial"
        assert summary["execution_runtime_projection_ready"] is False
        assert summary["execution_ready_threshold_count"] == 0
        assert summary["execution_partial_threshold_count"] == 5
        assert summary["execution_blocked_threshold_count"] == 0
        assert summary["local_lab_tail_risk_review_path"].endswith(
            "local_lab_tail_risk_review.json"
        )
        assert summary["tail_risk_review_status"] == "partial"
        assert summary["tail_risk_review_ready"] is False
        assert summary["tail_risk_ready_breaker_count"] == 0
        assert summary["tail_risk_partial_breaker_count"] == 3
        assert summary["tail_risk_blocked_breaker_count"] == 0
        assert summary["local_lab_calibration_normalized_report_path"].endswith(
            "local_lab_calibration_normalized_report.json"
        )
        assert summary["calibration_normalized_report_status"] == "partial"
        assert summary["calibration_normalized_report_ready"] is False
        assert summary["calibration_normalized_threshold_count"] == 5
        assert summary["local_lab_research_priority_path"].endswith(
            "local_lab_research_priority.json"
        )
        assert summary["research_priority_status"] == "no_losing_scopes"
        assert summary["research_priority_scope_count"] == 0
        assert summary["local_lab_replay_candidate_queue_path"].endswith(
            "local_lab_replay_candidate_queue.json"
        )
        assert summary["replay_candidate_queue_status"] == "no_candidates"
        assert summary["replay_candidate_count"] == 0
        assert summary["local_lab_replay_ticket_index_path"].endswith(
            "local_lab_replay_ticket_index.json"
        )
        assert summary["replay_ticket_index_status"] == "no_tickets"
        assert summary["replay_ticket_count"] == 0
        assert summary["local_lab_replay_dispatch_plan_path"].endswith(
            "local_lab_replay_dispatch_plan.json"
        )
        assert summary["replay_dispatch_plan_status"] == "no_items"
        assert summary["replay_dispatch_ready_count"] == 0
        assert summary["artifact_proof_validation_reasons"] == [
            "PROOF_WALK_FORWARD_REQUIRED",
            "PROOF_REGIME_SEGMENTATION_REQUIRED",
            "PROOF_ABLATION_DELTA_NET_PNL_TOO_LOW",
            "PROOF_ABLATION_DELTA_CE_REQUIRED",
        ]
        assert summary["release_ready_for_shadow"] is False
        assert summary["release_status"] == "local_only"
        assert summary["recalibration_candidate_ready"] is False
        assert summary["recalibration_blocking_reasons"] == ["NO_LOSING_TRADES_TO_RECALIBRATE"]
        assert summary["recalibration_action_count"] == 0
        assert summary["bridge_ready_for_shadow_dry_run"] is False
        assert (output_root / "local_lab_research_priority.json").exists()
        assert summary["bridge_status"] == "blocked_release_candidate"
        assert summary["bridge_release_gate_status"] == "proof_gate_blocked"
        assert summary["bridge_release_gate_reasons"] == [
            "PROOF_WALK_FORWARD_REQUIRED",
            "PROOF_REGIME_SEGMENTATION_REQUIRED",
            "PROOF_ABLATION_DELTA_NET_PNL_TOO_LOW",
            "PROOF_ABLATION_DELTA_CE_REQUIRED",
            "RECALIBRATION_NOT_REQUIRED",
        ]
        assert summary["promotion_readiness_status"] == "local_only"
        assert summary["promotion_activation_stage"] == "replay_only"
        assert summary["promotion_normalized_state"] == "replay_only"
        assert summary["promotion_review_state"] == "needs_revision"
        assert summary["monitoring_projection_status"] == "warning"
        assert summary["monitoring_projection_detail"].startswith(
            "Local IA Lab remains local-only pending proof"
        )
        assert summary["local_lab_observability_sample_count"] > 0
        assert summary["bridge_semantic_status"] == "not_evaluated"
        assert summary["bridge_semantic_reasons"] == []
        assert summary["edge_calibration_ready"] is True
        assert summary["trade_loss_attribution_path"].endswith("trade_loss_attribution.json")
        assert summary["walk_forward_review_template_path"].endswith("walk_forward_review.template.json")
        assert summary["walk_forward_review_summary_path"].endswith("walk_forward_review.summary.json")
        assert review_input["source_kind"] == "export_dir"
        assert edge_input["source_kind"] == "export_dir"
        assert edge_input["recalibration_plan_ref"].endswith("local_lab_recalibration_plan.json")
        assert edge_input["recalibration_candidate_ready"] is False
        assert edge_input["recalibration_blocking_reasons"] == ["NO_LOSING_TRADES_TO_RECALIBRATE"]
        tail_risk_review = json.loads(
            (output_root / "local_lab_tail_risk_review.json").read_text(encoding="utf-8")
        )
        calibration_normalized_report = json.loads(
            (output_root / "local_lab_calibration_normalized_report.json").read_text(
                encoding="utf-8"
            )
        )
        assert tail_risk_review["review_status"] == "partial"
        assert tail_risk_review["review_ready"] is False
        assert tail_risk_review["ready_breaker_count"] == 0
        assert tail_risk_review["partial_breaker_count"] == 3
        assert calibration_normalized_report["review_status"] == "partial"
        assert calibration_normalized_report["threshold_count"] == 5
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_run_local_lab_analysis_bundle_accepts_service_owned_execution_telemetry_artifact():
    scratch = _scratch_dir()
    scratch.mkdir(parents=True, exist_ok=False)
    try:
        export_dir = scratch / "export_dir"
        output_root = scratch / "analysis"
        telemetry_path = scratch / "shadow_vps_service_execution_telemetry.json"
        records = _records()
        metrics = build_replay_metrics_summary(records, total_opportunities=len(records))
        parity = ReplayParityDiagnosticsSummary(
            parity_status="passed",
            dataset_id="dataset-analysis-telemetry",
            decision_match_rate=1.0,
            score_match_rate=1.0,
            baseline_status="available",
            score_alignment="aligned",
            cost_alignment="aligned",
            compared_records=len(records),
            shared_core_match=True,
            parity_policy={"kind": "test"},
        )
        run_manifest = ReplayRunManifest(
            run_id="run-analysis-telemetry",
            strategy_id="strat-analysis",
            strategy_version="v5.3",
            strategy_classification=StrategyClassification.A_VARIANT,
            lineage_version="v5.3.lineage",
            profile_scope=ProfileId.COMPLETE,
            runtime_mode=RuntimeMode.LOCAL_REPLAY,
            engine_scope=("engine_a",),
            tested_pairs=("BTCUSDT",),
            dataset_manifest_id="dataset-analysis-telemetry",
            timeframe_scope="2026-04-01/2026-04-02",
            formula_set_version="formula.v1",
            scoring_version="scoring.v1",
            regime_version="regime.v1",
            risk_policy_version="risk.v1",
            cost_model_version="cost.v1",
            performance_mode="shadow_fidelity_mode",
            artifact_hash="artifact-analysis-telemetry",
            clock_id="clock-analysis-telemetry",
            start_timestamp_ms=1_700_000_000_000,
            end_timestamp_ms=1_700_000_060_000,
            tick_count=len(records),
            record_count=len(records),
        )
        export_local_replay_artifact(
            export_dir,
            ReplayArtifactExportRequest(
                run_manifest=run_manifest,
                review_export_markdown=_build_review_export_markdown(
                    run_id=run_manifest.run_id,
                    strategy_id=run_manifest.strategy_id,
                    strategy_version=run_manifest.strategy_version,
                    lineage_version=run_manifest.lineage_version,
                    profile_scope=run_manifest.profile_scope.value,
                    runtime_mode=run_manifest.runtime_mode.value,
                    performance_mode=run_manifest.performance_mode,
                    total_opportunities=metrics.total_opportunities,
                    total_records=metrics.total_records,
                    dtr_coverage=metrics.dtr_coverage,
                    status=parity.parity_status,
                    decision_match_rate=parity.decision_match_rate,
                ),
                feature_bridge_payload={
                    "dataset_id": run_manifest.dataset_manifest_id,
                    "feature_set_version": run_manifest.feature_set_version,
                    "transform_set_version": run_manifest.transform_set_version,
                    "pairs": list(run_manifest.tested_pairs),
                    "engines": list(run_manifest.engine_scope),
                },
                parity_diagnostics_payload=parity.model_dump(mode="json"),
                replay_metrics_payload=metrics.model_dump(mode="json"),
                replay_dtr_records=tuple(record.model_dump(mode="json") for record in records),
            ),
        )
        telemetry_artifact = LocalLabExecutionTelemetryArtifact(
            export_dir=str(export_dir.resolve()),
            run_id=run_manifest.run_id,
            source_session_dates=("2026-04-01", "2026-04-02"),
            time_sync_offsets_ms=(20.0, 22.0, 25.0, 27.0, 29.0, 31.0, 33.0),
            time_sync_observation_days=7.0,
            time_sync_session_dates=("2026-04-01",),
            time_sync_source_refs=("E:/shadow/time_sync_offsets.json",),
            quota_call_counts=(7, 7),
            quota_probe_durations_s=(3.5, 3.5),
            quota_limit_calls_per_minute_values=(120, 120),
            quota_calls_per_minute_observed=(120.0, 120.0),
            quota_observation_days=31.0,
            quota_session_dates=("2026-04-01", "2026-04-02"),
            quota_source_refs=("E:/shadow/time_sync_offsets.json",),
            websocket_interarrival_s=(0.05, 0.07, 0.09, 0.12, 0.15, 0.20, 0.22, 0.30),
            websocket_observation_days=30.0,
            websocket_session_dates=("2026-04-01", "2026-04-02"),
            websocket_source_refs=("E:/shadow/live_capture_1.json", "E:/shadow/live_capture_2.json"),
            spread_bps=(1.2, 1.5, 1.7, 2.0, 2.2, 2.8, 3.1, 3.8),
            spread_observation_days=30.0,
            spread_session_dates=("2026-04-01", "2026-04-02"),
            spread_source_refs=("E:/shadow/live_capture_1.json", "E:/shadow/live_capture_2.json"),
            slippage_bps=(1.5, 1.8, 2.0, 2.4),
            slippage_observation_days=30.0,
            slippage_session_dates=("2026-04-01", "2026-04-02"),
            slippage_source_refs=("E:/shadow/live_capture_1.json", "E:/shadow/live_capture_2.json"),
            candidate_sizes=(6.5, 9.5, 12.5, 16.5),
            candidate_size_observation_days=30.0,
            candidate_size_session_dates=("2026-04-01", "2026-04-02"),
            candidate_size_source_refs=("E:/shadow/live_capture_1.json", "E:/shadow/live_capture_2.json"),
            final_sizes=(6.0, 9.0, 12.0, 16.0),
            final_size_observation_days=30.0,
            final_size_session_dates=("2026-04-01", "2026-04-02"),
            final_size_source_refs=("E:/shadow/live_capture_1.json", "E:/shadow/live_capture_2.json"),
            coverage_caution_flags=("THR-X02_ACCEPTED_EVENTS_ONLY",),
        )
        telemetry_path.write_text(
            telemetry_artifact.model_dump_json(indent=2),
            encoding="utf-8",
        )

        exit_code = main(
            [
                "--export-dir",
                str(export_dir),
                "--correlation-id",
                "corr-analysis-telemetry",
                "--signed-by",
                "operator.aziz",
                "--output-root",
                str(output_root),
                "--pair",
                "BTCUSDT",
                "--engine-id",
                "engine_a",
                "--execution-telemetry-path",
                str(telemetry_path),
                "--bootstrap-samples",
                "250",
                "--min-positive-trades",
                "2",
                "--min-cost-observations",
                "2",
            ]
        )

        assert exit_code == 0
        summary = json.loads(
            (output_root / "local_lab_analysis_summary.json").read_text(
                encoding="utf-8"
            )
        )
        execution_review = json.loads(
            (output_root / "local_lab_execution_review.json").read_text(
                encoding="utf-8"
            )
        )
        execution_runtime_projection = json.loads(
            (output_root / "local_lab_execution_runtime_projection.json").read_text(
                encoding="utf-8"
            )
        )

        assert summary["execution_review_status"] == "ready"
        assert summary["execution_review_ready"] is True
        assert summary["execution_ready_threshold_count"] == 5
        assert summary["execution_partial_threshold_count"] == 0
        assert summary["local_lab_execution_runtime_projection_path"].endswith(
            "local_lab_execution_runtime_projection.json"
        )
        assert summary["execution_runtime_projection_status"] == "ready"
        assert summary["execution_runtime_projection_ready"] is True
        assert summary["execution_runtime_projection_consumer_count"] == 3
        assert summary["execution_runtime_projection_ready_consumer_count"] == 3
        assert execution_review["review_status"] == "ready"
        assert "THR-X02_ACCEPTED_EVENTS_ONLY" in execution_review["caution_flags"]
        assert "THR-X03_HUMAN_HARD_CAP_CLIPPED" in execution_review["caution_flags"]
        assert execution_runtime_projection["projection_status"] == "ready"
        assert execution_runtime_projection["projection_ready"] is True
        assert execution_runtime_projection["consumers"][0]["consumer_id"] == "rate_limiter"
        assert execution_runtime_projection["consumers"][1]["consumer_id"] == "spread_guard"
        assert execution_runtime_projection["consumers"][2]["consumer_id"] == "slippage_model"
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_run_local_lab_analysis_bundle_direct_script_execution_bootstraps_repo_root():
    scratch = _scratch_dir()
    scratch.mkdir(parents=True, exist_ok=False)
    try:
        export_dir = scratch / "export_dir"
        output_root = scratch / "analysis"
        records = _records()
        metrics = build_replay_metrics_summary(records, total_opportunities=len(records))
        parity = ReplayParityDiagnosticsSummary(
            parity_status="passed",
            dataset_id="dataset-analysis-02",
            decision_match_rate=1.0,
            score_match_rate=1.0,
            baseline_status="available",
            score_alignment="aligned",
            cost_alignment="aligned",
            compared_records=len(records),
            shared_core_match=True,
            parity_policy={"kind": "test"},
        )
        run_manifest = ReplayRunManifest(
            run_id="run-analysis-02",
            strategy_id="strat-analysis",
            strategy_version="v5.3",
            strategy_classification=StrategyClassification.A_VARIANT,
            lineage_version="v5.3.lineage",
            profile_scope=ProfileId.COMPLETE,
            runtime_mode=RuntimeMode.LOCAL_REPLAY,
            engine_scope=("engine_a",),
            tested_pairs=("BTCUSDT",),
            dataset_manifest_id="dataset-analysis-02",
            timeframe_scope="2026-04-01/2026-04-02",
            formula_set_version="formula.v1",
            scoring_version="scoring.v1",
            regime_version="regime.v1",
            risk_policy_version="risk.v1",
            cost_model_version="cost.v1",
            performance_mode="shadow_fidelity_mode",
            artifact_hash="artifact-analysis-02",
            clock_id="clock-analysis-02",
            start_timestamp_ms=1_700_000_000_000,
            end_timestamp_ms=1_700_000_060_000,
            tick_count=len(records),
            record_count=len(records),
        )
        export_local_replay_artifact(
            export_dir,
            ReplayArtifactExportRequest(
                run_manifest=run_manifest,
                review_export_markdown=_build_review_export_markdown(
                    run_id=run_manifest.run_id,
                    strategy_id=run_manifest.strategy_id,
                    strategy_version=run_manifest.strategy_version,
                    lineage_version=run_manifest.lineage_version,
                    profile_scope=run_manifest.profile_scope.value,
                    runtime_mode=run_manifest.runtime_mode.value,
                    performance_mode=run_manifest.performance_mode,
                    total_opportunities=metrics.total_opportunities,
                    total_records=metrics.total_records,
                    dtr_coverage=metrics.dtr_coverage,
                    status=parity.parity_status,
                    decision_match_rate=parity.decision_match_rate,
                ),
                feature_bridge_payload={
                    "dataset_id": run_manifest.dataset_manifest_id,
                    "feature_set_version": run_manifest.feature_set_version,
                    "transform_set_version": run_manifest.transform_set_version,
                    "pairs": list(run_manifest.tested_pairs),
                    "engines": list(run_manifest.engine_scope),
                },
                parity_diagnostics_payload=parity.model_dump(mode="json"),
                replay_metrics_payload=metrics.model_dump(mode="json"),
                replay_dtr_records=tuple(record.model_dump(mode="json") for record in records),
            ),
        )

        repo_root = Path(__file__).resolve().parents[2]
        script_path = repo_root / "scripts" / "run_local_lab_analysis_bundle.py"
        env = os.environ.copy()
        env.pop("PYTHONPATH", None)
        result = subprocess.run(
            [
                sys.executable,
                str(script_path),
                "--export-dir",
                str(export_dir),
                "--correlation-id",
                "corr-analysis-direct",
                "--signed-by",
                "operator.aziz",
                "--output-root",
                str(output_root),
                "--pair",
                "BTCUSDT",
                "--engine-id",
                "engine_a",
                "--bootstrap-samples",
                "250",
                "--min-positive-trades",
                "2",
                "--min-cost-observations",
                "2",
            ],
            cwd=repo_root,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

        assert result.returncode == 0, result.stderr
        summary = json.loads((output_root / "local_lab_analysis_summary.json").read_text(encoding="utf-8"))
        assert summary["correlation_id"] == "corr-analysis-direct"
        assert summary["trade_loss_attribution_ready"] is True
        assert summary["walk_forward_review_ready"] is False
        assert summary["artifact_ablation_ready"] is False
        assert summary["artifact_proof_ready"] is False
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_run_local_lab_analysis_bundle_accepts_approved_walk_forward_review():
    scratch = _scratch_dir()
    scratch.mkdir(parents=True, exist_ok=False)
    try:
        export_dir = scratch / "export_dir"
        output_root = scratch / "analysis"
        review_path = scratch / "walk_forward_review.json"
        records = _records()
        metrics = build_replay_metrics_summary(records, total_opportunities=len(records))
        parity = ReplayParityDiagnosticsSummary(
            parity_status="passed",
            dataset_id="dataset-analysis-03",
            decision_match_rate=1.0,
            score_match_rate=1.0,
            baseline_status="available",
            score_alignment="aligned",
            cost_alignment="aligned",
            compared_records=len(records),
            shared_core_match=True,
            parity_policy={"kind": "test"},
        )
        run_manifest = ReplayRunManifest(
            run_id="run-analysis-03",
            strategy_id="strat-analysis",
            strategy_version="v5.3",
            strategy_classification=StrategyClassification.A_VARIANT,
            lineage_version="v5.3.lineage",
            profile_scope=ProfileId.COMPLETE,
            runtime_mode=RuntimeMode.LOCAL_REPLAY,
            engine_scope=("engine_a",),
            tested_pairs=("BTCUSDT",),
            dataset_manifest_id="dataset-analysis-03",
            timeframe_scope="2026-04-01/2026-04-02",
            formula_set_version="formula.v1",
            scoring_version="scoring.v1",
            regime_version="regime.v1",
            risk_policy_version="risk.v1",
            cost_model_version="cost.v1",
            performance_mode="shadow_fidelity_mode",
            artifact_hash="artifact-analysis-03",
            clock_id="clock-analysis-03",
            start_timestamp_ms=1_700_000_000_000,
            end_timestamp_ms=1_700_000_060_000,
            tick_count=len(records),
            record_count=len(records),
        )
        export_local_replay_artifact(
            export_dir,
            ReplayArtifactExportRequest(
                run_manifest=run_manifest,
                review_export_markdown=_build_review_export_markdown(
                    run_id=run_manifest.run_id,
                    strategy_id=run_manifest.strategy_id,
                    strategy_version=run_manifest.strategy_version,
                    lineage_version=run_manifest.lineage_version,
                    profile_scope=run_manifest.profile_scope.value,
                    runtime_mode=run_manifest.runtime_mode.value,
                    performance_mode=run_manifest.performance_mode,
                    total_opportunities=metrics.total_opportunities,
                    total_records=metrics.total_records,
                    dtr_coverage=metrics.dtr_coverage,
                    status=parity.parity_status,
                    decision_match_rate=parity.decision_match_rate,
                ),
                feature_bridge_payload={
                    "dataset_id": run_manifest.dataset_manifest_id,
                    "feature_set_version": run_manifest.feature_set_version,
                    "transform_set_version": run_manifest.transform_set_version,
                    "pairs": list(run_manifest.tested_pairs),
                    "engines": list(run_manifest.engine_scope),
                },
                parity_diagnostics_payload=parity.model_dump(mode="json"),
                replay_metrics_payload=metrics.model_dump(mode="json"),
                replay_dtr_records=tuple(record.model_dump(mode="json") for record in records),
            ),
        )
        review_path.write_text(
            json.dumps(
                {
                    "correlation_id": "corr-analysis-03",
                    "export_dir": str(export_dir.resolve()),
                    "run_id": "run-analysis-03",
                    "review_status": "approved",
                    "reviewed_by": "operator.aziz",
                    "reviewed_at": datetime(2026, 4, 10, 12, 0, tzinfo=timezone.utc).isoformat(),
                    "walk_forward_window_count": 5,
                    "temporal_split_confirmed": True,
                    "no_future_data_leak_confirmed": True,
                    "feature_timestamp_alignment_confirmed": True,
                    "calibration_fit_window_confirmed": True,
                    "notes": "Walk-forward reviewed and approved by human gate.",
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        exit_code = main(
            [
                "--export-dir",
                str(export_dir),
                "--correlation-id",
                "corr-analysis-03",
                "--signed-by",
                "operator.aziz",
                "--output-root",
                str(output_root),
                "--pair",
                "BTCUSDT",
                "--engine-id",
                "engine_a",
                "--walk-forward-review-path",
                str(review_path),
                "--bootstrap-samples",
                "250",
                "--min-positive-trades",
                "2",
                "--min-cost-observations",
                "2",
            ]
        )

        assert exit_code == 0
        summary = json.loads((output_root / "local_lab_analysis_summary.json").read_text(encoding="utf-8"))
        walk_forward_summary = json.loads(
            (output_root / "walk_forward_review.summary.json").read_text(encoding="utf-8")
        )
        artifact_proof_assessment = json.loads(
            (output_root / "artifact_proof_assessment.json").read_text(encoding="utf-8")
        )
        assert summary["walk_forward_review_ready"] is True
        assert summary["walk_forward_review_path"].endswith("walk_forward_review.json")
        assert summary["artifact_proof_ready"] is False
        assert walk_forward_summary["walk_forward_pass"] is True
        assert walk_forward_summary["review_status"] == "approved"
        assert artifact_proof_assessment["proof_summary"]["walk_forward_pass"] is True
        assert artifact_proof_assessment["ready_for_vps_import"] is False
        assert artifact_proof_assessment["validation_reasons"] == [
            "PROOF_REGIME_SEGMENTATION_REQUIRED",
            "PROOF_ABLATION_DELTA_NET_PNL_TOO_LOW",
            "PROOF_ABLATION_DELTA_CE_REQUIRED",
        ]
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_run_local_lab_analysis_bundle_uses_baseline_export_for_ablation():
    scratch = _scratch_dir()
    scratch.mkdir(parents=True, exist_ok=False)
    try:
        export_dir = scratch / "candidate_export"
        baseline_export_dir = scratch / "baseline_export"
        output_root = scratch / "analysis"
        records = _records()
        baseline_records = _baseline_records()

        def _write_export(target_dir: Path, dataset_id: str, run_id: str, artifact_hash: str, rows):
            metrics = build_replay_metrics_summary(rows, total_opportunities=len(rows))
            parity = ReplayParityDiagnosticsSummary(
                parity_status="passed",
                dataset_id=dataset_id,
                decision_match_rate=1.0,
                score_match_rate=1.0,
                baseline_status="available",
                score_alignment="aligned",
                cost_alignment="aligned",
                compared_records=len(rows),
                shared_core_match=True,
                parity_policy={"kind": "test"},
            )
            run_manifest = ReplayRunManifest(
                run_id=run_id,
                strategy_id="strat-analysis",
                strategy_version="v5.3",
                strategy_classification=StrategyClassification.A_VARIANT,
                lineage_version="v5.3.lineage",
                profile_scope=ProfileId.COMPLETE,
                runtime_mode=RuntimeMode.LOCAL_REPLAY,
                engine_scope=("engine_a",),
                tested_pairs=("BTCUSDT",),
                dataset_manifest_id=dataset_id,
                timeframe_scope="2026-04-01/2026-04-02",
                formula_set_version="formula.v1",
                scoring_version="scoring.v1",
                regime_version="regime.v1",
                risk_policy_version="risk.v1",
                cost_model_version="cost.v1",
                performance_mode="shadow_fidelity_mode",
                artifact_hash=artifact_hash,
                clock_id=f"clock-{run_id}",
                start_timestamp_ms=1_700_000_000_000,
                end_timestamp_ms=1_700_000_060_000,
                tick_count=len(rows),
                record_count=len(rows),
            )
            export_local_replay_artifact(
                target_dir,
                ReplayArtifactExportRequest(
                    run_manifest=run_manifest,
                    review_export_markdown=_build_review_export_markdown(
                        run_id=run_manifest.run_id,
                        strategy_id=run_manifest.strategy_id,
                        strategy_version=run_manifest.strategy_version,
                        lineage_version=run_manifest.lineage_version,
                        profile_scope=run_manifest.profile_scope.value,
                        runtime_mode=run_manifest.runtime_mode.value,
                        performance_mode=run_manifest.performance_mode,
                        total_opportunities=metrics.total_opportunities,
                        total_records=metrics.total_records,
                        dtr_coverage=metrics.dtr_coverage,
                        status=parity.parity_status,
                        decision_match_rate=parity.decision_match_rate,
                    ),
                    feature_bridge_payload={
                        "dataset_id": run_manifest.dataset_manifest_id,
                        "feature_set_version": run_manifest.feature_set_version,
                        "transform_set_version": run_manifest.transform_set_version,
                        "pairs": list(run_manifest.tested_pairs),
                        "engines": list(run_manifest.engine_scope),
                    },
                    parity_diagnostics_payload=parity.model_dump(mode="json"),
                    replay_metrics_payload=metrics.model_dump(mode="json"),
                    replay_dtr_records=tuple(record.model_dump(mode="json") for record in rows),
                ),
            )

        _write_export(export_dir, "dataset-analysis-04", "run-analysis-04", "artifact-analysis-04", records)
        _write_export(
            baseline_export_dir,
            "dataset-analysis-04",
            "run-analysis-baseline-04",
            "artifact-analysis-baseline-04",
            baseline_records,
        )

        review_path = scratch / "walk_forward_review.json"
        review_path.write_text(
            json.dumps(
                {
                    "correlation_id": "corr-analysis-04",
                    "export_dir": str(export_dir.resolve()),
                    "run_id": "run-analysis-04",
                    "review_status": "approved",
                    "reviewed_by": "operator.aziz",
                    "reviewed_at": datetime(2026, 4, 10, 12, 0, tzinfo=timezone.utc).isoformat(),
                    "walk_forward_window_count": 5,
                    "temporal_split_confirmed": True,
                    "no_future_data_leak_confirmed": True,
                    "feature_timestamp_alignment_confirmed": True,
                    "calibration_fit_window_confirmed": True,
                    "notes": "Walk-forward reviewed and approved by human gate.",
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        exit_code = main(
            [
                "--export-dir",
                str(export_dir),
                "--baseline-export-dir",
                str(baseline_export_dir),
                "--correlation-id",
                "corr-analysis-04",
                "--signed-by",
                "operator.aziz",
                "--output-root",
                str(output_root),
                "--pair",
                "BTCUSDT",
                "--engine-id",
                "engine_a",
                "--walk-forward-review-path",
                str(review_path),
                "--bootstrap-samples",
                "250",
                "--min-positive-trades",
                "2",
                "--min-cost-observations",
                "2",
            ]
        )

        assert exit_code == 0
        summary = json.loads((output_root / "local_lab_analysis_summary.json").read_text(encoding="utf-8"))
        ablation = json.loads((output_root / "artifact_ablation_study.json").read_text(encoding="utf-8"))
        artifact_proof_assessment = json.loads(
            (output_root / "artifact_proof_assessment.json").read_text(encoding="utf-8")
        )
        assert summary["artifact_ablation_ready"] is True
        assert ablation["study_ready"] is True
        assert ablation["ablation_delta_net_pnl"] > 0.0
        assert ablation["ablation_delta_ce"] > 0.0
        assert artifact_proof_assessment["proof_summary"]["walk_forward_pass"] is True
        assert artifact_proof_assessment["proof_summary"]["ablation_delta_net_pnl"] > 0.01
        assert artifact_proof_assessment["validation_reasons"] == [
            "PROOF_REGIME_SEGMENTATION_REQUIRED"
        ]
        assert summary["artifact_release_candidate_path"].endswith("artifact_release_candidate.json")
        assert summary["release_ready_for_shadow"] is False
        assert summary["release_status"] == "local_only"
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_run_local_lab_analysis_bundle_all_scopes_emits_scope_matrix():
    scratch = _scratch_dir()
    scratch.mkdir(parents=True, exist_ok=False)
    try:
        export_dir = scratch / "export_dir"
        baseline_export_dir = scratch / "baseline_export_dir"
        output_root = scratch / "analysis"
        records = _multiscope_records()
        baseline_records = _multiscope_baseline_records()

        def _write_export(target_dir: Path, run_id: str, artifact_hash: str, rows):
            metrics = build_replay_metrics_summary(rows, total_opportunities=len(rows))
            parity = ReplayParityDiagnosticsSummary(
                parity_status="passed",
                dataset_id="dataset-analysis-multi-01",
                decision_match_rate=1.0,
                score_match_rate=1.0,
                baseline_status="available",
                score_alignment="aligned",
                cost_alignment="aligned",
                compared_records=len(rows),
                shared_core_match=True,
                parity_policy={"kind": "test"},
            )
            run_manifest = ReplayRunManifest(
                run_id=run_id,
                strategy_id="strat-analysis",
                strategy_version="v5.3",
                strategy_classification=StrategyClassification.A_VARIANT,
                lineage_version="v5.3.lineage",
                profile_scope=ProfileId.COMPLETE,
                runtime_mode=RuntimeMode.LOCAL_REPLAY,
                engine_scope=("engine_a", "engine_b"),
                tested_pairs=("BTCUSDT", "ETHUSDT"),
                dataset_manifest_id="dataset-analysis-multi-01",
                timeframe_scope="2026-04-01/2026-04-02",
                formula_set_version="formula.v1",
                scoring_version="scoring.v1",
                regime_version="regime.v1",
                risk_policy_version="risk.v1",
                cost_model_version="cost.v1",
                performance_mode="shadow_fidelity_mode",
                artifact_hash=artifact_hash,
                clock_id=f"clock-{run_id}",
                start_timestamp_ms=1_700_000_000_000,
                end_timestamp_ms=1_700_000_180_000,
                tick_count=len(rows),
                record_count=len(rows),
            )
            export_local_replay_artifact(
                target_dir,
                ReplayArtifactExportRequest(
                    run_manifest=run_manifest,
                    review_export_markdown=_build_review_export_markdown(
                        run_id=run_manifest.run_id,
                        strategy_id=run_manifest.strategy_id,
                        strategy_version=run_manifest.strategy_version,
                        lineage_version=run_manifest.lineage_version,
                        profile_scope=run_manifest.profile_scope.value,
                        runtime_mode=run_manifest.runtime_mode.value,
                        performance_mode=run_manifest.performance_mode,
                        total_opportunities=metrics.total_opportunities,
                        total_records=metrics.total_records,
                        dtr_coverage=metrics.dtr_coverage,
                        status=parity.parity_status,
                        decision_match_rate=parity.decision_match_rate,
                    ),
                    feature_bridge_payload={
                        "dataset_id": run_manifest.dataset_manifest_id,
                        "feature_set_version": run_manifest.feature_set_version,
                        "transform_set_version": run_manifest.transform_set_version,
                        "pairs": list(run_manifest.tested_pairs),
                        "engines": list(run_manifest.engine_scope),
                    },
                    parity_diagnostics_payload=parity.model_dump(mode="json"),
                    replay_metrics_payload=metrics.model_dump(mode="json"),
                    replay_dtr_records=tuple(record.model_dump(mode="json") for record in rows),
                ),
            )

        _write_export(export_dir, "run-analysis-multi-01", "artifact-analysis-multi-01", records)
        _write_export(
            baseline_export_dir,
            "run-analysis-multi-baseline-01",
            "artifact-analysis-multi-baseline-01",
            baseline_records,
        )

        review_path = scratch / "walk_forward_review.json"
        review_path.write_text(
            json.dumps(
                {
                    "correlation_id": "corr-analysis-multi-01",
                    "export_dir": str(export_dir.resolve()),
                    "run_id": "run-analysis-multi-01",
                    "review_status": "approved",
                    "reviewed_by": "operator.aziz",
                    "reviewed_at": datetime(2026, 4, 10, 12, 0, tzinfo=timezone.utc).isoformat(),
                    "walk_forward_window_count": 5,
                    "temporal_split_confirmed": True,
                    "no_future_data_leak_confirmed": True,
                    "feature_timestamp_alignment_confirmed": True,
                    "calibration_fit_window_confirmed": True,
                    "notes": "Human anti-leakage review approved.",
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        exit_code = main(
            [
                "--export-dir",
                str(export_dir),
                "--baseline-export-dir",
                str(baseline_export_dir),
                "--correlation-id",
                "corr-analysis-multi-01",
                "--signed-by",
                "operator.aziz",
                "--output-root",
                str(output_root),
                "--walk-forward-review-path",
                str(review_path),
                "--all-scopes",
                "--bootstrap-samples",
                "250",
                "--min-positive-trades",
                "2",
                "--min-cost-observations",
                "2",
            ]
        )

        assert exit_code == 0
        summary = json.loads((output_root / "local_lab_analysis_summary.json").read_text(encoding="utf-8"))
        matrix = json.loads((output_root / "local_lab_scope_matrix.json").read_text(encoding="utf-8"))
        release_candidate = json.loads(
            (output_root / "artifact_release_candidate.json").read_text(encoding="utf-8")
        )
        monitoring = json.loads(
            (output_root / "local_lab_monitoring_projection.json").read_text(encoding="utf-8")
        )
        calibration_methods_review = json.loads(
            (output_root / "local_lab_calibration_methods_review.json").read_text(
                encoding="utf-8"
            )
        )
        tail_risk_review = json.loads(
            (output_root / "local_lab_tail_risk_review.json").read_text(encoding="utf-8")
        )
        calibration_normalized_report = json.loads(
            (output_root / "local_lab_calibration_normalized_report.json").read_text(
                encoding="utf-8"
            )
        )
        observability = json.loads(
            (output_root / "local_lab_observability_export.json").read_text(encoding="utf-8")
        )
        observability_text = (output_root / "local_lab_observability.prom").read_text(
            encoding="utf-8"
        )
        backend_payload = json.loads(
            (output_root / "local_lab_monitoring_backend_payload.json").read_text(encoding="utf-8")
        )
        ingestion_summary = json.loads(
            (output_root / "local_lab_monitoring_ingestion_summary.json").read_text(encoding="utf-8")
        )

        assert summary["scope_matrix_path"].endswith("local_lab_scope_matrix.json")
        assert summary["scope_count"] == 2
        assert summary["scope_ready_count"] == 2
        assert summary["scope_blocked_count"] == 0
        assert summary["release_scope_ready_count"] == 2
        assert summary["release_scope_blocked_count"] == 0
        assert summary["local_lab_monitoring_backend_payload_path"].endswith(
            "local_lab_monitoring_backend_payload.json"
        )
        assert summary["local_lab_observability_text_path"].endswith(
            "local_lab_observability.prom"
        )
        assert summary["local_lab_monitoring_backend_status"] == "warning"
        assert summary["local_lab_monitoring_ingestion_summary_path"].endswith(
            "local_lab_monitoring_ingestion_summary.json"
        )
        assert summary["local_lab_monitoring_ingestion_ready"] is True
        assert summary["local_lab_loss_surrogate_path"].endswith(
            "local_lab_loss_surrogate_report.json"
        )
        assert summary["loss_surrogate_status"] == "single_class_only"
        assert summary["loss_surrogate_ready"] is False
        assert summary["local_lab_research_priority_path"].endswith(
            "local_lab_research_priority.json"
        )
        assert summary["research_priority_status"] == "no_losing_scopes"
        assert summary["research_priority_scope_count"] == 0
        assert summary["local_lab_replay_candidate_queue_path"].endswith(
            "local_lab_replay_candidate_queue.json"
        )
        assert summary["replay_candidate_queue_status"] == "no_candidates"
        assert summary["replay_candidate_count"] == 0
        assert summary["local_lab_replay_ticket_index_path"].endswith(
            "local_lab_replay_ticket_index.json"
        )
        assert summary["replay_ticket_index_status"] == "no_tickets"
        assert summary["replay_ticket_count"] == 0
        assert summary["local_lab_replay_dispatch_plan_path"].endswith(
            "local_lab_replay_dispatch_plan.json"
        )
        assert summary["replay_dispatch_plan_status"] == "no_items"
        assert summary["replay_dispatch_ready_count"] == 0
        assert summary["artifact_proof_ready"] is True
        assert summary["artifact_proof_validation_reasons"] == []
        assert summary["artifact_release_candidate_path"].endswith("artifact_release_candidate.json")
        assert summary["release_ready_for_shadow"] is True
        assert summary["release_status"] == "shadow_candidate"
        assert summary["release_blocking_reasons"] == []
        assert summary["release_ready_scope_slugs"] == [
            "btcusdt__engine_a",
            "ethusdt__engine_b",
        ]
        assert summary["release_blocked_scope_slugs"] == []
        assert summary["release_scope_summary_count"] == 2
        assert summary["release_scope_summary_paths"][0].endswith(
            "scopes\\btcusdt__engine_a\\artifact_release_scope_summary.json"
        )
        assert summary["release_scope_summary_paths"][1].endswith(
            "scopes\\ethusdt__engine_b\\artifact_release_scope_summary.json"
        )
        assert summary["artifact_import_dry_run_bridge_path"].endswith(
            "artifact_import_dry_run_bridge.json"
        )
        assert summary["bridge_ready_for_shadow_dry_run"] is False
        assert summary["bridge_status"] == "blocked_missing_governance_inputs"
        assert summary["bridge_release_gate_status"] == "proof_backed_no_recalibration_required"
        assert summary["bridge_release_gate_reasons"] == [
            "PROOF_GATE_PASSED",
            "RECALIBRATION_NOT_REQUIRED",
        ]
        assert summary["promotion_readiness_status"] == "shadow_candidate_pending_dry_run"
        assert summary["promotion_activation_stage"] == "shadow_ready"
        assert summary["promotion_normalized_state"] == "shadow_candidate"
        assert summary["promotion_review_state"] == "pending"
        assert summary["monitoring_projection_status"] == "warning"
        assert summary["monitoring_projection_detail"].startswith(
            "Local IA Lab release candidate is proof-backed locally"
        )
        assert summary["local_lab_observability_sample_count"] > 0
        assert summary["bridge_semantic_status"] == "not_evaluated"
        assert summary["bridge_semantic_reasons"] == []
        assert summary["review_output_dir"] is None
        assert summary["artifact_proof_summary_path"] is None
        assert monitoring["status"] == "warning"
        assert monitoring["promotion_readiness_status"] == "shadow_candidate_pending_dry_run"
        assert monitoring["release_scope_ready_count"] == 2
        assert monitoring["release_scope_blocked_count"] == 0
        assert observability["text_payload"].startswith("# V5.3 Local IA Lab observability export")
        assert observability_text == observability["text_payload"] + "\n"
        assert any(
            sample["name"] == "v53_local_lab_monitoring_status"
            for sample in observability["samples"]
        )
        assert backend_payload["status"] == "warning"
        assert backend_payload["scope_count"] == 2
        assert backend_payload["observability_sample_count"] == len(observability["samples"])
        assert ingestion_summary["ingestion_ready"] is True
        assert ingestion_summary["sample_count"] == len(observability["samples"])

        assert matrix["scope_count"] == 2
        assert matrix["ready_scope_count"] == 2
        assert matrix["blocked_scope_count"] == 0
        assert matrix["release_ready_scope_count"] == 2
        assert matrix["release_blocked_scope_count"] == 0
        assert [scope["scope_slug"] for scope in matrix["scopes"]] == [
            "btcusdt__engine_a",
            "ethusdt__engine_b",
        ]
        assert all(scope["artifact_proof_ready"] is True for scope in matrix["scopes"])
        assert all(scope["artifact_ablation_ready"] is True for scope in matrix["scopes"])
        assert all(scope["release_ready"] is True for scope in matrix["scopes"])
        assert matrix["scopes"][0]["release_scope_summary_path"].endswith(
            "artifact_release_scope_summary.json"
        )
        assert [scope["scope_slug"] for scope in release_candidate["release_scopes"]] == [
            "btcusdt__engine_a",
            "ethusdt__engine_b",
        ]
        assert release_candidate["release_scopes"][0]["review_bundle_path"].endswith(
            "meta_learning_review.bundle.json"
        )
        assert release_candidate["release_scopes"][0]["trade_loss_attribution_path"].endswith(
            "trade_loss_attribution.json"
        )
        assert release_candidate["release_scopes"][0]["artifact_proof_summary_path"].endswith(
            "artifact_proof_summary.json"
        )
        assert release_candidate["release_scopes"][0]["artifact_proof_assessment_path"].endswith(
            "artifact_proof_assessment.json"
        )
        assert release_candidate["release_scopes"][0]["release_scope_summary_path"].endswith(
            "artifact_release_scope_summary.json"
        )
        scope_release_summary = json.loads(
            (
                output_root
                / "scopes"
                / "btcusdt__engine_a"
                / "artifact_release_scope_summary.json"
            ).read_text(encoding="utf-8")
        )
        assert scope_release_summary["scope_slug"] == "btcusdt__engine_a"
        assert scope_release_summary["ready_for_shadow_import"] is True
        assert scope_release_summary["scope_release_ready"] is True
        assert scope_release_summary["shared_release_gate_summary_path"].endswith(
            "artifact_release_gate_summary.json"
        )
        assert scope_release_summary["shared_source_artifact_summary_path"].endswith(
            "artifact_source_summary.json"
        )
        assert scope_release_summary["shared_artifact_import_dry_run_bridge_path"].endswith(
            "artifact_import_dry_run_bridge.json"
        )
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_run_local_lab_analysis_bundle_emits_governed_import_dry_run_when_ready():
    scratch = _scratch_dir()
    scratch.mkdir(parents=True, exist_ok=False)
    try:
        export_dir = scratch / "export_dir"
        baseline_export_dir = scratch / "baseline_export_dir"
        output_root = scratch / "analysis"
        records = tuple(
            record for record in _multiscope_records() if record.pair == "BTCUSDT"
        )
        baseline_records = tuple(
            record for record in _multiscope_baseline_records() if record.pair == "BTCUSDT"
        )

        def _write_export(target_dir: Path, run_id: str, artifact_hash: str, rows):
            metrics = build_replay_metrics_summary(rows, total_opportunities=len(rows))
            parity = ReplayParityDiagnosticsSummary(
                parity_status="passed",
                dataset_id="dataset-analysis-bridge-01",
                decision_match_rate=1.0,
                score_match_rate=1.0,
                baseline_status="available",
                score_alignment="aligned",
                cost_alignment="aligned",
                compared_records=len(rows),
                shared_core_match=True,
                parity_policy={"kind": "test"},
            )
            run_manifest = ReplayRunManifest(
                run_id=run_id,
                strategy_id="strat-analysis",
                strategy_version="v5.3",
                strategy_classification=StrategyClassification.A_VARIANT,
                lineage_version="v5.3.lineage",
                profile_scope=ProfileId.COMPLETE,
                runtime_mode=RuntimeMode.LOCAL_REPLAY,
                engine_scope=("engine_a",),
                tested_pairs=("BTCUSDT",),
                dataset_manifest_id="dataset-analysis-bridge-01",
                timeframe_scope="2026-04-01/2026-04-02",
                formula_set_version="formula.v1",
                scoring_version="scoring.v1",
                regime_version="regime.v1",
                risk_policy_version="risk.v1",
                cost_model_version="cost.v1",
                performance_mode="shadow_fidelity_mode",
                artifact_hash=artifact_hash,
                clock_id=f"clock-{run_id}",
                start_timestamp_ms=1_700_000_000_000,
                end_timestamp_ms=1_700_000_060_000,
                tick_count=len(rows),
                record_count=len(rows),
            )
            export_local_replay_artifact(
                target_dir,
                ReplayArtifactExportRequest(
                    run_manifest=run_manifest,
                    review_export_markdown=_build_review_export_markdown(
                        run_id=run_manifest.run_id,
                        strategy_id=run_manifest.strategy_id,
                        strategy_version=run_manifest.strategy_version,
                        lineage_version=run_manifest.lineage_version,
                        profile_scope=run_manifest.profile_scope.value,
                        runtime_mode=run_manifest.runtime_mode.value,
                        performance_mode=run_manifest.performance_mode,
                        total_opportunities=metrics.total_opportunities,
                        total_records=metrics.total_records,
                        dtr_coverage=metrics.dtr_coverage,
                        status=parity.parity_status,
                        decision_match_rate=parity.decision_match_rate,
                    ),
                    feature_bridge_payload={
                        "dataset_id": run_manifest.dataset_manifest_id,
                        "feature_set_version": run_manifest.feature_set_version,
                        "transform_set_version": run_manifest.transform_set_version,
                        "pairs": list(run_manifest.tested_pairs),
                        "engines": list(run_manifest.engine_scope),
                    },
                    parity_diagnostics_payload=parity.model_dump(mode="json"),
                    replay_metrics_payload=metrics.model_dump(mode="json"),
                    replay_dtr_records=tuple(record.model_dump(mode="json") for record in rows),
                ),
            )

        _write_export(export_dir, "run-analysis-bridge-01", "artifact-analysis-bridge-01", records)
        _write_export(
            baseline_export_dir,
            "run-analysis-bridge-baseline-01",
            "artifact-analysis-bridge-baseline-01",
            baseline_records,
        )

        review_path = scratch / "walk_forward_review.json"
        review_path.write_text(
            json.dumps(
                {
                    "correlation_id": "corr-analysis-bridge-01",
                    "export_dir": str(export_dir.resolve()),
                    "run_id": "run-analysis-bridge-01",
                    "review_status": "approved",
                    "reviewed_by": "operator.aziz",
                    "reviewed_at": datetime(2026, 4, 10, 12, 0, tzinfo=timezone.utc).isoformat(),
                    "walk_forward_window_count": 5,
                    "temporal_split_confirmed": True,
                    "no_future_data_leak_confirmed": True,
                    "feature_timestamp_alignment_confirmed": True,
                    "calibration_fit_window_confirmed": True,
                    "notes": "Human anti-leakage review approved.",
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        exit_code = main(
            [
                "--export-dir",
                str(export_dir),
                "--baseline-export-dir",
                str(baseline_export_dir),
                "--correlation-id",
                "corr-analysis-bridge-01",
                "--signed-by",
                "operator.aziz",
                "--output-root",
                str(output_root),
                "--walk-forward-review-path",
                str(review_path),
                "--pair",
                "BTCUSDT",
                "--engine-id",
                "engine_a",
                "--bootstrap-samples",
                "250",
                "--min-positive-trades",
                "2",
                "--min-cost-observations",
                "2",
                "--bridge-governance-reference-date",
                "2026-04-10",
                "--bridge-training-end",
                "2026-04-09",
                "--bridge-artifact-class",
                "DAMAGE_REDUCER",
                "--bridge-artifact-scope",
                "engine_a:edge_gate",
                "--bridge-lifecycle-ttl-days",
                "30",
                "--bridge-rule-half-life-days",
                "7",
                "--bridge-drift-score-threshold",
                "0.85",
            ]
        )

        assert exit_code == 0
        summary = json.loads((output_root / "local_lab_analysis_summary.json").read_text(encoding="utf-8"))
        bridge = json.loads(
            (output_root / "artifact_import_dry_run_bridge.json").read_text(encoding="utf-8")
        )
        promotion = json.loads(
            (output_root / "artifact_promotion_readiness_summary.json").read_text(encoding="utf-8")
        )
        monitoring = json.loads(
            (output_root / "local_lab_monitoring_projection.json").read_text(encoding="utf-8")
        )
        calibration_methods_review = json.loads(
            (output_root / "local_lab_calibration_methods_review.json").read_text(
                encoding="utf-8"
            )
        )
        tail_risk_review = json.loads(
            (output_root / "local_lab_tail_risk_review.json").read_text(encoding="utf-8")
        )
        calibration_normalized_report = json.loads(
            (output_root / "local_lab_calibration_normalized_report.json").read_text(
                encoding="utf-8"
            )
        )
        observability = json.loads(
            (output_root / "local_lab_observability_export.json").read_text(encoding="utf-8")
        )
        observability_text = (output_root / "local_lab_observability.prom").read_text(
            encoding="utf-8"
        )
        backend_payload = json.loads(
            (output_root / "local_lab_monitoring_backend_payload.json").read_text(encoding="utf-8")
        )
        ingestion_summary = json.loads(
            (output_root / "local_lab_monitoring_ingestion_summary.json").read_text(encoding="utf-8")
        )
        upload_request = json.loads(
            (output_root / "artifact_upload_request.dry_run.json").read_text(encoding="utf-8")
        )
        import_request = json.loads(
            (output_root / "artifact_import_request.dry_run.json").read_text(encoding="utf-8")
        )
        import_decision = json.loads(
            (output_root / "artifact_import_decision.dry_run.json").read_text(encoding="utf-8")
        )
        upload_decision = json.loads(
            (output_root / "artifact_upload_decision.dry_run.json").read_text(encoding="utf-8")
        )
        source_summary = json.loads(
            (output_root / "artifact_source_summary.json").read_text(encoding="utf-8")
        )
        release_gate_summary = json.loads(
            (output_root / "artifact_release_gate_summary.json").read_text(encoding="utf-8")
        )

        assert summary["release_ready_for_shadow"] is True
        assert summary["bridge_ready_for_shadow_dry_run"] is True
        assert summary["bridge_status"] == "dry_run_ready"
        assert summary["bridge_blocking_reasons"] == []
        assert summary["bridge_release_gate_status"] == "proof_backed_no_recalibration_required"
        assert summary["bridge_release_gate_reasons"] == [
            "PROOF_GATE_PASSED",
            "RECALIBRATION_NOT_REQUIRED",
        ]
        assert summary["artifact_source_summary_path"].endswith("artifact_source_summary.json")
        assert summary["artifact_release_gate_summary_path"].endswith(
            "artifact_release_gate_summary.json"
        )
        assert summary["bridge_semantic_status"] == "transport_packet_with_source_artifact_refs"
        assert summary["bridge_semantic_reasons"] == [
            "TRANSPORT_ARTIFACT_ID_DIFFERS_FROM_SOURCE_ARTIFACT_ID",
            "TRANSPORT_KIND_IS_REVIEW_PACKET",
            "TRANSPORT_SUPPLEMENTARY_REFS_CARRY_SOURCE_ARTIFACT",
            "TRANSPORT_SUPPLEMENTARY_REFS_CARRY_SOURCE_ARTIFACT_SUMMARY",
            "TRANSPORT_SUPPLEMENTARY_REFS_CARRY_RELEASE_GATE_SUMMARY",
        ]
        assert summary["bridge_transport_payload_ref_count"] == 8
        assert len(summary["bridge_transport_supplementary_refs"]) == 3
        assert summary["bridge_transport_supplementary_refs"][0].endswith("edge_gate.yml")
        assert summary["bridge_transport_supplementary_refs"][1].endswith(
            "artifact_source_summary.json"
        )
        assert summary["bridge_transport_supplementary_refs"][2].endswith(
            "artifact_release_gate_summary.json"
        )
        assert summary["artifact_import_dry_run_bridge_path"].endswith(
            "artifact_import_dry_run_bridge.json"
        )
        assert summary["artifact_promotion_readiness_summary_path"].endswith(
            "artifact_promotion_readiness_summary.json"
        )
        assert summary["local_lab_monitoring_projection_path"].endswith(
            "local_lab_monitoring_projection.json"
        )
        assert summary["local_lab_observability_export_path"].endswith(
            "local_lab_observability_export.json"
        )
        assert summary["local_lab_observability_text_path"].endswith(
            "local_lab_observability.prom"
        )
        assert summary["local_lab_monitoring_backend_payload_path"].endswith(
            "local_lab_monitoring_backend_payload.json"
        )
        assert summary["local_lab_monitoring_ingestion_summary_path"].endswith(
            "local_lab_monitoring_ingestion_summary.json"
        )
        assert summary["local_lab_loss_surrogate_path"].endswith(
            "local_lab_loss_surrogate_report.json"
        )
        assert summary["loss_surrogate_status"] == "insufficient_executed_records"
        assert summary["loss_surrogate_ready"] is False
        assert summary["local_lab_calibration_methods_review_path"].endswith(
            "local_lab_calibration_methods_review.json"
        )
        assert summary["calibration_methods_review_status"] == "partial"
        assert summary["calibration_methods_review_ready"] is False
        assert summary["calibration_methods_dsr_pass"] is None
        assert summary["calibration_methods_walk_forward_plan_ready"] is False
        assert summary["local_lab_execution_review_path"].endswith(
            "local_lab_execution_review.json"
        )
        assert summary["execution_review_status"] == "partial"
        assert summary["execution_review_ready"] is False
        assert summary["execution_ready_threshold_count"] == 0
        assert summary["execution_partial_threshold_count"] == 5
        assert summary["execution_blocked_threshold_count"] == 0
        assert summary["local_lab_tail_risk_review_path"].endswith(
            "local_lab_tail_risk_review.json"
        )
        assert summary["tail_risk_review_status"] == "partial"
        assert summary["tail_risk_review_ready"] is False
        assert summary["tail_risk_ready_breaker_count"] == 0
        assert summary["tail_risk_partial_breaker_count"] == 3
        assert summary["tail_risk_blocked_breaker_count"] == 0
        assert summary["local_lab_calibration_normalized_report_path"].endswith(
            "local_lab_calibration_normalized_report.json"
        )
        assert summary["calibration_normalized_report_status"] == "partial"
        assert summary["calibration_normalized_report_ready"] is False
        assert summary["calibration_normalized_threshold_count"] == 5
        assert summary["local_lab_research_priority_path"].endswith(
            "local_lab_research_priority.json"
        )
        assert summary["research_priority_status"] == "no_losing_scopes"
        assert summary["research_priority_scope_count"] == 0
        assert summary["artifact_upload_request_path"].endswith(
            "artifact_upload_request.dry_run.json"
        )
        assert summary["artifact_import_request_path"].endswith(
            "artifact_import_request.dry_run.json"
        )
        assert summary["artifact_import_decision_path"].endswith(
            "artifact_import_decision.dry_run.json"
        )
        assert summary["artifact_upload_decision_path"].endswith(
            "artifact_upload_decision.dry_run.json"
        )
        assert summary["promotion_readiness_status"] == "shadow_candidate_dry_run_ready"
        assert summary["promotion_activation_stage"] == "shadow_ready"
        assert summary["promotion_normalized_state"] == "shadow_candidate"
        assert summary["promotion_review_state"] == "pending"
        assert summary["monitoring_projection_status"] == "healthy"
        assert summary["monitoring_projection_detail"].startswith(
            "Local IA Lab dry-run handoff is ready for SHADOW import review"
        )
        assert summary["local_lab_observability_sample_count"] > 0
        assert summary["local_lab_monitoring_backend_status"] == "healthy"
        assert summary["local_lab_monitoring_ingestion_ready"] is True
        assert summary["local_lab_monitoring_backend_status"] == "healthy"

        assert bridge["bridge_status"] == "dry_run_ready"
        assert bridge["ready_for_shadow_import_dry_run"] is True
        assert bridge["release_ready_for_shadow"] is True
        assert bridge["release_artifact_proof_ready"] is True
        assert bridge["release_calibration_methods_review_status"] == "partial"
        assert bridge["release_calibration_methods_review_ready"] is False
        assert bridge["release_calibration_methods_dsr_pass"] is None
        assert bridge["release_calibration_methods_walk_forward_plan_ready"] is False
        assert bridge["release_calibration_methods_review_ref"].endswith(
            "local_lab_calibration_methods_review.json"
        )
        assert bridge["release_recalibration_candidate_ready"] is False
        assert bridge["release_recalibration_blocking_reasons"] == [
            "NO_LOSING_TRADES_TO_RECALIBRATE"
        ]
        assert bridge["release_gate_status"] == "proof_backed_no_recalibration_required"
        assert bridge["release_gate_reasons"] == [
            "PROOF_GATE_PASSED",
            "RECALIBRATION_NOT_REQUIRED",
        ]
        assert bridge["release_candidate_artifact_id"] == "edge_gate_thresholds"
        assert bridge["source_artifact_id"] == "edge_gate_thresholds"
        assert bridge["source_artifact_family"] == "calibration_artifact"
        assert bridge["source_artifact_schema_version"] == "calibration.v1"
        assert bridge["source_artifact_version"] == "v1"
        assert bridge["governed_artifact_id"] == "artifact-analysis-bridge-01"
        assert bridge["transport_artifact_id"] == "artifact-analysis-bridge-01"
        assert bridge["artifact_kind"] == "review_packet"
        assert bridge["transport_artifact_kind"] == "review_packet"
        assert bridge["artifact_class"] == "DAMAGE_REDUCER"
        assert bridge["artifact_scope"] == "engine_a:edge_gate"
        assert bridge["source_artifact_summary_ref"].endswith("artifact_source_summary.json")
        assert bridge["release_gate_summary_ref"].endswith("artifact_release_gate_summary.json")
        assert bridge["semantic_status"] == "transport_packet_with_source_artifact_refs"
        assert bridge["semantic_reasons"] == [
            "TRANSPORT_ARTIFACT_ID_DIFFERS_FROM_SOURCE_ARTIFACT_ID",
            "TRANSPORT_KIND_IS_REVIEW_PACKET",
            "TRANSPORT_SUPPLEMENTARY_REFS_CARRY_SOURCE_ARTIFACT",
            "TRANSPORT_SUPPLEMENTARY_REFS_CARRY_SOURCE_ARTIFACT_SUMMARY",
            "TRANSPORT_SUPPLEMENTARY_REFS_CARRY_RELEASE_GATE_SUMMARY",
        ]
        assert bridge["transport_payload_ref_count"] == 8
        assert len(bridge["transport_supplementary_refs"]) == 3
        assert bridge["transport_supplementary_refs"][0].endswith("edge_gate.yml")
        assert bridge["transport_supplementary_refs"][1].endswith("artifact_source_summary.json")
        assert bridge["transport_supplementary_refs"][2].endswith(
            "artifact_release_gate_summary.json"
        )

        assert source_summary["artifact_id"] == "edge_gate_thresholds"
        assert source_summary["artifact_family"] == "calibration_artifact"
        assert source_summary["schema_version"] == "calibration.v1"
        assert source_summary["version"] == "v1"
        assert source_summary["threshold_count"] == 2
        assert release_gate_summary["release_candidate_artifact_id"] == "edge_gate_thresholds"
        assert release_gate_summary["release_calibration_methods_review_status"] == "partial"
        assert release_gate_summary["release_calibration_methods_review_ready"] is False
        assert release_gate_summary["release_calibration_methods_dsr_pass"] is None
        assert release_gate_summary["release_calibration_methods_walk_forward_plan_ready"] is False
        assert release_gate_summary["release_calibration_methods_review_ref"].endswith(
            "local_lab_calibration_methods_review.json"
        )
        assert release_gate_summary["release_gate_status"] == "proof_backed_no_recalibration_required"
        assert release_gate_summary["release_gate_reasons"] == [
            "PROOF_GATE_PASSED",
            "RECALIBRATION_NOT_REQUIRED",
        ]
        assert promotion["readiness_status"] == "shadow_candidate_dry_run_ready"
        assert promotion["activation_stage"] == "shadow_ready"
        assert promotion["normalized_promotion_state"] == "shadow_candidate"
        assert promotion["review_state"] == "pending"
        assert promotion["dry_run_bridge_status"] == "dry_run_ready"
        assert promotion["release_gate_status"] == "proof_backed_no_recalibration_required"
        assert monitoring["status"] == "healthy"
        assert monitoring["bridge_status"] == "dry_run_ready"
        assert monitoring["promotion_readiness_status"] == "shadow_candidate_dry_run_ready"
        assert monitoring["release_gate_status"] == "proof_backed_no_recalibration_required"
        assert monitoring["calibration_methods_review_status"] == "partial"
        assert monitoring["calibration_methods_review_ready"] is False
        assert monitoring["local_lab_calibration_methods_review_path"].endswith(
            "local_lab_calibration_methods_review.json"
        )
        assert monitoring["tail_risk_review_status"] == "partial"
        assert monitoring["tail_risk_review_ready"] is False
        assert monitoring["tail_risk_partial_breaker_count"] == 3
        assert monitoring["local_lab_tail_risk_review_path"].endswith(
            "local_lab_tail_risk_review.json"
        )
        assert monitoring["calibration_normalized_report_status"] == "partial"
        assert monitoring["calibration_normalized_report_ready"] is False
        assert monitoring["calibration_normalized_threshold_count"] == 5
        assert monitoring["local_lab_calibration_normalized_report_path"].endswith(
            "local_lab_calibration_normalized_report.json"
        )
        assert calibration_methods_review["review_status"] == "partial"
        assert calibration_methods_review["review_ready"] is False
        assert calibration_methods_review["walk_forward_plan_status"] == "insufficient_history"
        assert calibration_methods_review["stationarity_status"] == "insufficient_history"
        assert calibration_methods_review["dsr_status"] == "insufficient_history"
        assert tail_risk_review["review_status"] == "partial"
        assert tail_risk_review["review_ready"] is False
        assert tail_risk_review["partial_breaker_count"] == 3
        assert calibration_normalized_report["review_status"] == "partial"
        assert calibration_normalized_report["threshold_count"] == 5
        assert monitoring["artifact_promotion_readiness_summary_path"].endswith(
            "artifact_promotion_readiness_summary.json"
        )
        assert observability["text_payload"].startswith("# V5.3 Local IA Lab observability export")
        assert observability_text == observability["text_payload"] + "\n"
        assert any(
            sample["name"] == "v53_local_lab_dry_run_ready_for_shadow"
            and sample["value"] == 1.0
            for sample in observability["samples"]
        )
        assert any(
            sample["name"] == "v53_local_lab_calibration_methods_review_ready"
            and sample["value"] == 0.0
            for sample in observability["samples"]
        )
        assert any(
            sample["name"] == "v53_local_lab_tail_risk_review_ready"
            and sample["value"] == 0.0
            for sample in observability["samples"]
        )
        assert any(
            sample["name"] == "v53_local_lab_calibration_normalized_report_ready"
            and sample["value"] == 0.0
            for sample in observability["samples"]
        )
        assert backend_payload["status"] == "healthy"
        assert backend_payload["ready_for_shadow_import_dry_run"] is True
        assert backend_payload["observability_sample_count"] == len(observability["samples"])
        assert backend_payload["calibration_methods_review_status"] == "partial"
        assert backend_payload["calibration_methods_review_ready"] is False
        assert backend_payload["calibration_methods_stationarity_status"] == "insufficient_history"
        assert backend_payload["calibration_methods_stationarity_pass"] is None
        assert backend_payload["local_lab_calibration_methods_review_ref"].endswith(
            "local_lab_calibration_methods_review.json"
        )
        assert backend_payload["tail_risk_review_status"] == "partial"
        assert backend_payload["tail_risk_review_ready"] is False
        assert backend_payload["tail_risk_partial_breaker_count"] == 3
        assert backend_payload["local_lab_tail_risk_review_ref"].endswith(
            "local_lab_tail_risk_review.json"
        )
        assert backend_payload["calibration_normalized_report_status"] == "partial"
        assert backend_payload["calibration_normalized_report_ready"] is False
        assert backend_payload["calibration_normalized_threshold_count"] == 5
        assert backend_payload["local_lab_calibration_normalized_report_ref"].endswith(
            "local_lab_calibration_normalized_report.json"
        )
        assert ingestion_summary["ingestion_ready"] is True
        assert ingestion_summary["projection_status"] == "healthy"
        loaded_bundle = load_local_lab_monitoring_bundle(output_root)
        assert loaded_bundle.backend_payload.status == "healthy"
        assert loaded_bundle.ingestion_summary.ingestion_ready is True

        assert upload_request["payload_bundle"]["review_export_ref"].endswith("review_export.md")
        assert upload_request["payload_bundle"]["feature_bridge_ref"].endswith("feature_bridge.json")
        assert upload_request["payload_bundle"]["parity_diagnostics_ref"].endswith(
            "parity_diagnostics.json"
        )
        assert upload_request["payload_bundle"]["replay_metrics_ref"].endswith(
            "replay_metrics.json"
        )
        assert upload_request["payload_bundle"]["replay_dtr_ref"].endswith("replay_dtr.jsonl")
        assert len(upload_request["payload_bundle"]["supplementary_refs"]) == 3
        assert upload_request["payload_bundle"]["supplementary_refs"][0].endswith("edge_gate.yml")
        assert upload_request["payload_bundle"]["supplementary_refs"][1].endswith(
            "artifact_source_summary.json"
        )
        assert upload_request["payload_bundle"]["supplementary_refs"][2].endswith(
            "artifact_release_gate_summary.json"
        )

        assert upload_request["governance_reference_date"] == "2026-04-10"
        assert upload_request["upload_context"] == "LOCAL_LAB"
        assert import_request["target_runtime_mode"] == "shadow"
        assert import_decision["accepted"] is True
        assert upload_decision["accepted"] is True
        assert upload_decision["status"] == "DRY_RUN_OK"
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
