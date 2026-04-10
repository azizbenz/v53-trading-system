from __future__ import annotations

from local_replay_runtime import build_local_lab_artifact_release_candidate
from local_replay_runtime.artifact_upload_bridge_candidate import (
    LocalLabArtifactUploadDryRunBridge,
)
from local_replay_runtime.local_lab_monitoring_projection import (
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
        release_candidate=release_candidate,
        dry_run_bridge=bridge,
        promotion_readiness=promotion,
    )

    assert projection.status == "critical"
    assert projection.promotion_readiness_status == "local_only"
    assert projection.detail == "Local IA Lab core analysis outputs are incomplete or missing."


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
        release_candidate=release_candidate,
        dry_run_bridge=bridge,
        promotion_readiness=promotion,
    )

    assert projection.status == "warning"
    assert projection.promotion_readiness_status == "shadow_candidate_pending_dry_run"
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
        release_candidate=release_candidate,
        dry_run_bridge=bridge,
        promotion_readiness=promotion,
    )

    assert projection.status == "healthy"
    assert projection.promotion_readiness_status == "shadow_candidate_dry_run_ready"
    assert projection.detail.startswith("Local IA Lab dry-run handoff is ready for SHADOW import review")
