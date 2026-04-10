from __future__ import annotations

from local_replay_runtime import build_local_lab_artifact_release_candidate
from local_replay_runtime.artifact_upload_bridge_candidate import (
    LocalLabArtifactUploadDryRunBridge,
)
from local_replay_runtime.local_lab_promotion_readiness import (
    build_local_lab_promotion_readiness_summary,
)


def _release_candidate(*, ready_for_shadow_import: bool):
    return build_local_lab_artifact_release_candidate(
        correlation_id="corr-promotion",
        export_dir="E:/lab/candidate",
        baseline_export_dir=None,
        run_id="run-promotion",
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


def test_local_lab_promotion_readiness_stays_local_only_when_release_is_blocked():
    summary = build_local_lab_promotion_readiness_summary(
        release_candidate=_release_candidate(ready_for_shadow_import=False),
        dry_run_bridge=LocalLabArtifactUploadDryRunBridge(
            correlation_id="corr-promotion",
            export_dir="E:/lab/candidate",
            release_candidate_artifact_id="edge_gate_thresholds",
            source_artifact_path="E:/lab/edge_gate.yml",
            uploaded_by="operator.aziz",
            bridge_status="blocked_release_candidate",
            release_gate_status="proof_gate_blocked",
            release_gate_reasons=("PROOF_WALK_FORWARD_REQUIRED", "RECALIBRATION_NOT_REQUIRED"),
            blocking_reasons=("PROOF_WALK_FORWARD_REQUIRED",),
        ),
    )

    assert summary.readiness_status == "local_only"
    assert summary.activation_stage.value == "replay_only"
    assert summary.normalized_promotion_state.value == "replay_only"
    assert summary.review_state.value == "needs_revision"


def test_local_lab_promotion_readiness_marks_shadow_candidate_pending_dry_run():
    summary = build_local_lab_promotion_readiness_summary(
        release_candidate=_release_candidate(ready_for_shadow_import=True),
        dry_run_bridge=LocalLabArtifactUploadDryRunBridge(
            correlation_id="corr-promotion",
            export_dir="E:/lab/candidate",
            release_candidate_artifact_id="edge_gate_thresholds",
            source_artifact_path="E:/lab/edge_gate.yml",
            uploaded_by="operator.aziz",
            bridge_status="blocked_missing_governance_inputs",
            release_ready_for_shadow=True,
            release_artifact_proof_ready=True,
            release_recalibration_candidate_ready=False,
            release_recalibration_blocking_reasons=("NO_LOSING_TRADES_TO_RECALIBRATE",),
            release_gate_status="proof_backed_no_recalibration_required",
            release_gate_reasons=("PROOF_GATE_PASSED", "RECALIBRATION_NOT_REQUIRED"),
            blocking_reasons=("GOVERNANCE_REFERENCE_DATE_REQUIRED",),
        ),
    )

    assert summary.readiness_status == "shadow_candidate_pending_dry_run"
    assert summary.activation_stage.value == "shadow_ready"
    assert summary.normalized_promotion_state.value == "shadow_candidate"
    assert summary.review_state.value == "pending"


def test_local_lab_promotion_readiness_marks_dry_run_ready_shadow_candidate():
    summary = build_local_lab_promotion_readiness_summary(
        release_candidate=_release_candidate(ready_for_shadow_import=True),
        dry_run_bridge=LocalLabArtifactUploadDryRunBridge(
            correlation_id="corr-promotion",
            export_dir="E:/lab/candidate",
            release_candidate_artifact_id="edge_gate_thresholds",
            source_artifact_path="E:/lab/edge_gate.yml",
            uploaded_by="operator.aziz",
            bridge_status="dry_run_ready",
            ready_for_shadow_import_dry_run=True,
            release_ready_for_shadow=True,
            release_artifact_proof_ready=True,
            release_recalibration_candidate_ready=False,
            release_recalibration_blocking_reasons=("NO_LOSING_TRADES_TO_RECALIBRATE",),
            release_gate_status="proof_backed_no_recalibration_required",
            release_gate_reasons=("PROOF_GATE_PASSED", "RECALIBRATION_NOT_REQUIRED"),
        ),
    )

    assert summary.readiness_status == "shadow_candidate_dry_run_ready"
    assert summary.activation_stage.value == "shadow_ready"
    assert summary.normalized_promotion_state.value == "shadow_candidate"
    assert summary.review_state.value == "pending"
