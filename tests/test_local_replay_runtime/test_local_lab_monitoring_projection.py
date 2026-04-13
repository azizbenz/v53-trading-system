from __future__ import annotations

from local_replay_runtime import build_local_lab_artifact_release_candidate
from local_replay_runtime.artifact_upload_bridge_candidate import (
    LocalLabArtifactUploadDryRunBridge,
)
from monitoring.local_lab_monitoring_projection import (
    build_local_lab_monitoring_projection,
)
from local_replay_runtime.local_lab_promotion_readiness import (
    build_local_lab_promotion_readiness_summary,
)


def _release_candidate(*, ready_for_shadow_import: bool):
    return build_local_lab_artifact_release_candidate(
        correlation_id="corr-monitoring",
        export_dir="E:/lab/candidate",
        baseline_export_dir=None,
        run_id="run-monitoring",
        artifact_id="edge_gate_thresholds",
        artifact_path="E:/lab/edge_gate.yml",
        artifact_input_summary_path="E:/lab/edge_gate.input_summary.json",
        walk_forward_review_summary_path="E:/lab/walk_forward_review.summary.json",
        local_lab_recalibration_plan_path="E:/lab/local_lab_recalibration_plan.json",
        edge_calibration_ready=True,
        recalibration_candidate_ready=False,
        recalibration_blocking_reasons=("NO_LOSING_TRADES_TO_RECALIBRATE",),
        artifact_proof_ready=ready_for_shadow_import,
        artifact_proof_validation_reasons=(
            () if ready_for_shadow_import else ("PROOF_WALK_FORWARD_REQUIRED",)
        ),
    )


def _promotion(ready_for_shadow_import: bool, *, dry_run_ready: bool, bridge_status: str):
    release_candidate = _release_candidate(ready_for_shadow_import=ready_for_shadow_import)
    bridge = LocalLabArtifactUploadDryRunBridge(
        correlation_id="corr-monitoring",
        export_dir="E:/lab/candidate",
        release_candidate_artifact_id="edge_gate_thresholds",
        source_artifact_path="E:/lab/edge_gate.yml",
        uploaded_by="operator.aziz",
        bridge_status=bridge_status,
        ready_for_shadow_import_dry_run=dry_run_ready,
        release_ready_for_shadow=ready_for_shadow_import,
        release_artifact_proof_ready=ready_for_shadow_import,
        release_recalibration_candidate_ready=False,
        release_recalibration_blocking_reasons=("NO_LOSING_TRADES_TO_RECALIBRATE",),
        release_gate_status=(
            "proof_backed_no_recalibration_required"
            if ready_for_shadow_import
            else "proof_gate_blocked"
        ),
        release_gate_reasons=(
            ("PROOF_GATE_PASSED", "RECALIBRATION_NOT_REQUIRED")
            if ready_for_shadow_import
            else ("PROOF_WALK_FORWARD_REQUIRED", "RECALIBRATION_NOT_REQUIRED")
        ),
        blocking_reasons=(
            () if dry_run_ready else ("GOVERNANCE_REFERENCE_DATE_REQUIRED",)
        ),
    )
    return release_candidate, bridge, build_local_lab_promotion_readiness_summary(
        release_candidate=release_candidate,
        dry_run_bridge=bridge,
    )


def test_local_lab_monitoring_projection_is_critical_when_core_outputs_are_missing():
    release_candidate, bridge, promotion = _promotion(
        ready_for_shadow_import=False,
        dry_run_ready=False,
        bridge_status="blocked_release_candidate",
    )
    projection = build_local_lab_monitoring_projection(
        correlation_id="corr-monitoring",
        run_id="run-monitoring",
        export_dir="E:/lab/candidate",
        dataset_manifest_id="dataset-monitoring-01",
        artifact_id="edge_gate_thresholds",
        selected_pair="BTCUSDT",
        selected_engine_id="engine_a",
        review_ready=False,
        trade_loss_attribution_ready=False,
        walk_forward_review_ready=False,
        artifact_ablation_ready=False,
        artifact_proof_ready=False,
        edge_calibration_ready=False,
        scope_count=1,
        scope_ready_count=0,
        scope_blocked_count=1,
        release_scope_ready_count=0,
        release_scope_blocked_count=1,
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

    assert projection.status == "critical"
    assert projection.promotion_readiness_status == "local_only"
    assert projection.detail == "Local IA Lab core analysis outputs are incomplete or missing."
    assert projection.loss_surrogate_status == "not_evaluated"
    assert projection.research_priority_status == "not_evaluated"


def test_local_lab_monitoring_projection_warns_when_candidate_is_only_locally_ready():
    release_candidate, bridge, promotion = _promotion(
        ready_for_shadow_import=True,
        dry_run_ready=False,
        bridge_status="blocked_missing_governance_inputs",
    )
    projection = build_local_lab_monitoring_projection(
        correlation_id="corr-monitoring",
        run_id="run-monitoring",
        export_dir="E:/lab/candidate",
        dataset_manifest_id="dataset-monitoring-01",
        artifact_id="edge_gate_thresholds",
        selected_pair="BTCUSDT",
        selected_engine_id="engine_a",
        review_ready=True,
        trade_loss_attribution_ready=True,
        walk_forward_review_ready=True,
        artifact_ablation_ready=True,
        artifact_proof_ready=True,
        edge_calibration_ready=True,
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
        loss_surrogate_status="single_class_only",
        loss_surrogate_ready=False,
        loss_surrogate_scope_count=1,
        loss_surrogate_top_scope_slug="",
        loss_surrogate_top_probability=0.0,
        execution_review_status="partial",
        execution_review_ready=False,
        execution_ready_threshold_count=0,
        execution_partial_threshold_count=2,
        execution_blocked_threshold_count=0,
        local_lab_execution_review_path="E:/lab/local_lab_execution_review.json",
        multiple_testing_review_status="ready",
        multiple_testing_review_ready=True,
        multiple_testing_correction_required=False,
        multiple_testing_correction="not_required_interval_publication",
        multiple_testing_family_count=2,
        research_priority_status="ready",
        research_priority_scope_count=1,
        research_priority_top_scope_slug="btcusdt__engine_a",
        research_priority_top_score=0.81,
        local_lab_loss_surrogate_path="E:/lab/local_lab_loss_surrogate_report.json",
        local_lab_research_priority_path="E:/lab/local_lab_research_priority.json",
    )

    assert projection.status == "warning"
    assert projection.promotion_readiness_status == "shadow_candidate_pending_dry_run"
    assert projection.loss_surrogate_status == "single_class_only"
    assert projection.execution_review_status == "partial"
    assert projection.execution_review_ready is False
    assert projection.execution_partial_threshold_count == 2
    assert projection.multiple_testing_review_status == "ready"
    assert projection.multiple_testing_review_ready is True
    assert projection.research_priority_status == "ready"
    assert projection.research_priority_scope_count == 1
    assert projection.research_priority_top_scope_slug == "btcusdt__engine_a"
    assert projection.detail.startswith(
        "Local IA Lab release candidate is proof-backed locally"
    )


def test_local_lab_monitoring_projection_is_healthy_when_dry_run_is_ready():
    release_candidate, bridge, promotion = _promotion(
        ready_for_shadow_import=True,
        dry_run_ready=True,
        bridge_status="dry_run_ready",
    )
    projection = build_local_lab_monitoring_projection(
        correlation_id="corr-monitoring",
        run_id="run-monitoring",
        export_dir="E:/lab/candidate",
        dataset_manifest_id="dataset-monitoring-01",
        artifact_id="edge_gate_thresholds",
        selected_pair=None,
        selected_engine_id=None,
        review_ready=True,
        trade_loss_attribution_ready=True,
        walk_forward_review_ready=True,
        artifact_ablation_ready=True,
        artifact_proof_ready=True,
        edge_calibration_ready=True,
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

    assert projection.status == "healthy"
    assert projection.promotion_readiness_status == "shadow_candidate_dry_run_ready"
    assert projection.loss_surrogate_scope_count == 0
    assert projection.research_priority_scope_count == 0
    assert projection.detail.startswith("Local IA Lab dry-run handoff is ready for SHADOW import review")
