"""Compact future-dashboard projection for Local IA Lab packaging and dry-run handoff."""

from __future__ import annotations

from pydantic import BaseModel, Field

from monitoring.contracts import ProjectionStatus

from local_replay_runtime.artifact_release_candidate import LocalLabArtifactReleaseCandidate
from local_replay_runtime.artifact_upload_bridge_candidate import LocalLabArtifactUploadDryRunBridge
from local_replay_runtime.local_lab_promotion_readiness import LocalLabPromotionReadinessSummary


class LocalLabMonitoringProjection(BaseModel, frozen=True):
    """Audit-ready Local IA Lab monitoring summary without coupling to UI."""

    status: ProjectionStatus
    correlation_id: str = Field(..., min_length=1)
    run_id: str = Field(..., min_length=1)
    export_dir: str = Field(..., min_length=1)
    runtime_mode: str = Field(default="local_replay", min_length=1)
    dataset_manifest_id: str = Field(..., min_length=1)
    artifact_id: str = Field(..., min_length=1)
    selected_pair: str | None = None
    selected_engine_id: str | None = None
    detail: str = Field(..., min_length=1)
    review_ready: bool = False
    trade_loss_attribution_ready: bool = False
    walk_forward_review_ready: bool = False
    artifact_ablation_ready: bool = False
    artifact_proof_ready: bool = False
    edge_calibration_ready: bool = False
    release_ready_for_shadow: bool = False
    ready_for_shadow_import_dry_run: bool = False
    release_status: str = Field(..., min_length=1)
    bridge_status: str = Field(..., min_length=1)
    promotion_readiness_status: str = Field(..., min_length=1)
    activation_stage: str = Field(..., min_length=1)
    normalized_promotion_state: str = Field(..., min_length=1)
    review_state: str = Field(..., min_length=1)
    release_gate_status: str = Field(..., min_length=1)
    semantic_status: str = Field(..., min_length=1)
    scope_count: int = Field(default=0, ge=0)
    scope_ready_count: int = Field(default=0, ge=0)
    scope_blocked_count: int = Field(default=0, ge=0)
    release_scope_ready_count: int = Field(default=0, ge=0)
    release_scope_blocked_count: int = Field(default=0, ge=0)
    blocking_reasons: tuple[str, ...] = ()
    artifact_proof_validation_reasons: tuple[str, ...] = ()
    recalibration_blocking_reasons: tuple[str, ...] = ()
    release_gate_reasons: tuple[str, ...] = ()
    bridge_blocking_reasons: tuple[str, ...] = ()
    scope_matrix_path: str | None = None
    artifact_release_candidate_path: str | None = None
    artifact_import_dry_run_bridge_path: str | None = None
    artifact_promotion_readiness_summary_path: str | None = None


def _dedupe(items: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(items))


def _build_detail(
    *,
    status: ProjectionStatus,
    promotion: LocalLabPromotionReadinessSummary,
    release_candidate: LocalLabArtifactReleaseCandidate,
    dry_run_bridge: LocalLabArtifactUploadDryRunBridge,
) -> str:
    if status == "healthy":
        return (
            "Local IA Lab dry-run handoff is ready for SHADOW import review "
            f"(scopes={promotion.release_ready_scope_count}/{promotion.scope_count})."
        )
    if release_candidate.ready_for_shadow_import:
        return (
            "Local IA Lab release candidate is proof-backed locally, but the governed dry-run "
            f"handoff is still pending ({dry_run_bridge.bridge_status})."
        )
    if status == "critical":
        return "Local IA Lab core analysis outputs are incomplete or missing."
    return (
        "Local IA Lab remains local-only pending proof, walk-forward, or recalibration closure "
        f"({promotion.readiness_status})."
    )


def build_local_lab_monitoring_projection(
    *,
    correlation_id: str,
    run_id: str,
    export_dir: str,
    dataset_manifest_id: str,
    artifact_id: str,
    selected_pair: str | None,
    selected_engine_id: str | None,
    review_ready: bool,
    trade_loss_attribution_ready: bool,
    walk_forward_review_ready: bool,
    artifact_ablation_ready: bool,
    artifact_proof_ready: bool,
    edge_calibration_ready: bool,
    scope_count: int,
    scope_ready_count: int,
    scope_blocked_count: int,
    release_scope_ready_count: int,
    release_scope_blocked_count: int,
    release_candidate: LocalLabArtifactReleaseCandidate,
    dry_run_bridge: LocalLabArtifactUploadDryRunBridge,
    promotion_readiness: LocalLabPromotionReadinessSummary,
    scope_matrix_path: str | None = None,
    artifact_release_candidate_path: str | None = None,
    artifact_import_dry_run_bridge_path: str | None = None,
    artifact_promotion_readiness_summary_path: str | None = None,
) -> LocalLabMonitoringProjection:
    """Normalize the current Local IA Lab packaging state into one monitoring sidecar."""

    core_outputs_ready = review_ready and trade_loss_attribution_ready and edge_calibration_ready
    if dry_run_bridge.ready_for_shadow_import_dry_run:
        status: ProjectionStatus = "healthy"
    elif not core_outputs_ready:
        status = "critical"
    elif (
        release_candidate.ready_for_shadow_import
        or artifact_proof_ready
        or walk_forward_review_ready
        or artifact_ablation_ready
        or release_candidate.blocking_reasons
        or dry_run_bridge.blocking_reasons
    ):
        status = "warning"
    else:
        status = "info"

    blocking_reasons = _dedupe(
        [
            *release_candidate.blocking_reasons,
            *dry_run_bridge.blocking_reasons,
        ]
    )
    return LocalLabMonitoringProjection(
        status=status,
        correlation_id=correlation_id,
        run_id=run_id,
        export_dir=export_dir,
        dataset_manifest_id=dataset_manifest_id,
        artifact_id=artifact_id,
        selected_pair=selected_pair,
        selected_engine_id=selected_engine_id,
        detail=_build_detail(
            status=status,
            promotion=promotion_readiness,
            release_candidate=release_candidate,
            dry_run_bridge=dry_run_bridge,
        ),
        review_ready=review_ready,
        trade_loss_attribution_ready=trade_loss_attribution_ready,
        walk_forward_review_ready=walk_forward_review_ready,
        artifact_ablation_ready=artifact_ablation_ready,
        artifact_proof_ready=artifact_proof_ready,
        edge_calibration_ready=edge_calibration_ready,
        release_ready_for_shadow=release_candidate.ready_for_shadow_import,
        ready_for_shadow_import_dry_run=dry_run_bridge.ready_for_shadow_import_dry_run,
        release_status=release_candidate.release_status,
        bridge_status=dry_run_bridge.bridge_status,
        promotion_readiness_status=promotion_readiness.readiness_status,
        activation_stage=promotion_readiness.activation_stage.value,
        normalized_promotion_state=promotion_readiness.normalized_promotion_state.value,
        review_state=promotion_readiness.review_state.value,
        release_gate_status=dry_run_bridge.release_gate_status,
        semantic_status=dry_run_bridge.semantic_status,
        scope_count=scope_count,
        scope_ready_count=scope_ready_count,
        scope_blocked_count=scope_blocked_count,
        release_scope_ready_count=release_scope_ready_count,
        release_scope_blocked_count=release_scope_blocked_count,
        blocking_reasons=blocking_reasons,
        artifact_proof_validation_reasons=release_candidate.artifact_proof_validation_reasons,
        recalibration_blocking_reasons=release_candidate.recalibration_blocking_reasons,
        release_gate_reasons=dry_run_bridge.release_gate_reasons,
        bridge_blocking_reasons=dry_run_bridge.blocking_reasons,
        scope_matrix_path=scope_matrix_path,
        artifact_release_candidate_path=artifact_release_candidate_path,
        artifact_import_dry_run_bridge_path=artifact_import_dry_run_bridge_path,
        artifact_promotion_readiness_summary_path=artifact_promotion_readiness_summary_path,
    )


__all__ = [
    "LocalLabMonitoringProjection",
    "build_local_lab_monitoring_projection",
]
