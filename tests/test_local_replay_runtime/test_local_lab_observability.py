from __future__ import annotations

from interface_contracts.domain_types import ProfileId, RuntimeMode
from local_replay_runtime import build_local_lab_artifact_release_candidate
from local_replay_runtime.artifact_upload_bridge_candidate import (
    LocalLabArtifactUploadDryRunBridge,
)
from monitoring.local_lab_monitoring_projection import (
    build_local_lab_monitoring_projection,
)
from monitoring.local_lab_observability import (
    build_local_lab_observability_export,
)
from local_replay_runtime.local_lab_promotion_readiness import (
    build_local_lab_promotion_readiness_summary,
)


def _projection(*, dry_run_ready: bool):
    release_candidate = build_local_lab_artifact_release_candidate(
        correlation_id="corr-observability",
        export_dir="E:/lab/candidate",
        baseline_export_dir=None,
        run_id="run-observability",
        artifact_id="edge_gate_thresholds",
        artifact_path="E:/lab/edge_gate.yml",
        artifact_input_summary_path="E:/lab/edge_gate.input_summary.json",
        walk_forward_review_summary_path="E:/lab/walk_forward_review.summary.json",
        local_lab_recalibration_plan_path="E:/lab/local_lab_recalibration_plan.json",
        edge_calibration_ready=True,
        recalibration_candidate_ready=False,
        recalibration_blocking_reasons=("NO_LOSING_TRADES_TO_RECALIBRATE",),
        artifact_proof_ready=True,
        artifact_proof_validation_reasons=(),
    )
    bridge = LocalLabArtifactUploadDryRunBridge(
        correlation_id="corr-observability",
        export_dir="E:/lab/candidate",
        release_candidate_artifact_id="edge_gate_thresholds",
        source_artifact_path="E:/lab/edge_gate.yml",
        uploaded_by="operator.aziz",
        bridge_status="dry_run_ready" if dry_run_ready else "blocked_missing_governance_inputs",
        ready_for_shadow_import_dry_run=dry_run_ready,
        release_ready_for_shadow=True,
        release_artifact_proof_ready=True,
        release_recalibration_candidate_ready=False,
        release_recalibration_blocking_reasons=("NO_LOSING_TRADES_TO_RECALIBRATE",),
        release_gate_status="proof_backed_no_recalibration_required",
        release_gate_reasons=("PROOF_GATE_PASSED", "RECALIBRATION_NOT_REQUIRED"),
        blocking_reasons=() if dry_run_ready else ("GOVERNANCE_REFERENCE_DATE_REQUIRED",),
        semantic_status="transport_packet_with_source_artifact_refs",
    )
    promotion = build_local_lab_promotion_readiness_summary(
        release_candidate=release_candidate,
        dry_run_bridge=bridge,
    )
    return build_local_lab_monitoring_projection(
        correlation_id="corr-observability",
        run_id="run-observability",
        export_dir="E:/lab/candidate",
        dataset_manifest_id="dataset-observability-01",
        artifact_id="edge_gate_thresholds",
        selected_pair="BTCUSDT",
        selected_engine_id="engine_a",
        review_ready=True,
        trade_loss_attribution_ready=True,
        walk_forward_review_ready=True,
        artifact_ablation_ready=True,
        artifact_proof_ready=True,
        edge_calibration_ready=True,
        calibration_methods_stationarity_status="failed_threshold",
        calibration_methods_stationarity_pass=False,
        execution_review_status="partial",
        execution_review_ready=False,
        execution_ready_threshold_count=0,
        execution_partial_threshold_count=2,
        execution_blocked_threshold_count=0,
        multiple_testing_review_status="ready",
        multiple_testing_review_ready=True,
        multiple_testing_correction_required=False,
        multiple_testing_correction="not_required_interval_publication",
        multiple_testing_family_count=2,
        calibration_normalized_report_status="partial",
        calibration_normalized_report_ready=False,
        calibration_normalized_threshold_count=5,
        tail_risk_review_status="partial",
        tail_risk_review_ready=False,
        tail_risk_ready_breaker_count=0,
        tail_risk_partial_breaker_count=3,
        tail_risk_blocked_breaker_count=0,
        scope_count=2,
        scope_ready_count=2,
        scope_blocked_count=0,
        release_scope_ready_count=2,
        release_scope_blocked_count=0,
        release_ready_for_shadow=release_candidate.ready_for_shadow_import,
        release_status=release_candidate.release_status,
        release_blocking_reasons=release_candidate.blocking_reasons,
        artifact_proof_validation_reasons=release_candidate.artifact_proof_validation_reasons,
        recalibration_blocking_reasons=release_candidate.recalibration_blocking_reasons,
        bridge_status=bridge.bridge_status,
        ready_for_shadow_import_dry_run=bridge.ready_for_shadow_import_dry_run,
        bridge_blocking_reasons=bridge.blocking_reasons,
        release_gate_status=bridge.release_gate_status,
        release_gate_reasons=bridge.release_gate_reasons,
        semantic_status=bridge.semantic_status,
        promotion_readiness_status=promotion.readiness_status,
        activation_stage=promotion.activation_stage.value,
        normalized_promotion_state=promotion.normalized_promotion_state.value,
        review_state=promotion.review_state.value,
    )


def test_local_lab_observability_export_emits_metric_samples_and_text_payload():
    projection = _projection(dry_run_ready=True)
    export = build_local_lab_observability_export(
        projection=projection,
        profile=ProfileId.COMPLETE,
        runtime_mode=RuntimeMode.LOCAL_REPLAY,
        timestamp_ms=1_700_000_060_000,
    )

    sample_names = {sample.name for sample in export.samples}
    assert export.correlation_id == "corr-observability"
    assert export.profile is ProfileId.COMPLETE
    assert export.runtime_mode is RuntimeMode.LOCAL_REPLAY
    assert "v53_local_lab_monitoring_status" in sample_names
    assert "v53_local_lab_dry_run_ready_for_shadow" in sample_names
    assert "v53_local_lab_release_scope_ready_count" in sample_names
    assert "v53_local_lab_loss_surrogate_ready" in sample_names
    assert "v53_local_lab_loss_surrogate_top_probability" in sample_names
    assert "v53_local_lab_research_priority_scope_count" in sample_names
    assert "v53_local_lab_research_priority_top_score" in sample_names
    assert "v53_local_lab_calibration_methods_stationarity_pass" in sample_names
    assert "v53_local_lab_execution_review_ready" in sample_names
    assert "v53_local_lab_execution_partial_threshold_count" in sample_names
    assert "v53_local_lab_multiple_testing_review_ready" in sample_names
    assert "v53_local_lab_multiple_testing_correction_required" in sample_names
    assert "v53_local_lab_multiple_testing_family_count" in sample_names
    assert "v53_local_lab_calibration_normalized_report_ready" in sample_names
    assert "v53_local_lab_calibration_normalized_threshold_count" in sample_names
    assert "v53_local_lab_tail_risk_review_ready" in sample_names
    assert "v53_local_lab_tail_risk_partial_breaker_count" in sample_names
    assert export.text_payload.startswith("# V5.3 Local IA Lab observability export")
    assert 'profile="complete"' in export.text_payload
    assert 'runtime_mode="local_replay"' in export.text_payload


def test_local_lab_observability_export_tracks_warning_state_when_dry_run_is_not_ready():
    projection = _projection(dry_run_ready=False)
    export = build_local_lab_observability_export(
        projection=projection,
        profile=ProfileId.COMPLETE,
        runtime_mode=RuntimeMode.LOCAL_REPLAY,
        timestamp_ms=1_700_000_060_000,
    )

    status_sample = next(
        sample for sample in export.samples if sample.name == "v53_local_lab_monitoring_status"
    )
    assert projection.status == "warning"
    assert status_sample.value == 2.0
    assert status_sample.labels["status"] == "warning"
