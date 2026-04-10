"""Top-level Local IA Lab promotion-readiness projection over the dry-run handoff rail."""

from __future__ import annotations

from pydantic import BaseModel, Field

from interface_contracts import ArtifactActivationStage, PromotionState, ReviewState

from local_replay_runtime.artifact_release_candidate import LocalLabArtifactReleaseCandidate
from local_replay_runtime.artifact_upload_bridge_candidate import LocalLabArtifactUploadDryRunBridge


class LocalLabPromotionReadinessSummary(BaseModel, frozen=True):
    """Audit-ready readiness summary bridging Local IA Lab packaging truth to canonical promotion vocabulary."""

    correlation_id: str = Field(..., min_length=1)
    run_id: str = Field(..., min_length=1)
    export_dir: str = Field(..., min_length=1)
    artifact_id: str = Field(..., min_length=1)
    artifact_path: str = Field(..., min_length=1)
    target_runtime_mode: str = Field(default="shadow", min_length=1)
    readiness_status: str = Field(..., min_length=1)
    activation_stage: ArtifactActivationStage
    normalized_promotion_state: PromotionState
    review_state: ReviewState
    release_ready_for_shadow: bool = False
    ready_for_shadow_import_dry_run: bool = False
    artifact_proof_ready: bool = False
    artifact_proof_validation_reasons: tuple[str, ...] = ()
    recalibration_candidate_ready: bool = False
    recalibration_blocking_reasons: tuple[str, ...] = ()
    release_gate_status: str = Field(default="not_evaluated", min_length=1)
    release_gate_reasons: tuple[str, ...] = ()
    local_release_status: str = Field(..., min_length=1)
    dry_run_bridge_status: str = Field(..., min_length=1)
    blocking_reasons: tuple[str, ...] = ()
    scope_count: int = Field(default=0, ge=0)
    release_ready_scope_count: int = Field(default=0, ge=0)
    release_blocked_scope_count: int = Field(default=0, ge=0)


def build_local_lab_promotion_readiness_summary(
    *,
    release_candidate: LocalLabArtifactReleaseCandidate,
    dry_run_bridge: LocalLabArtifactUploadDryRunBridge,
) -> LocalLabPromotionReadinessSummary:
    """Project the current Local IA Lab packaging state into canonical promotion vocabulary."""

    if dry_run_bridge.ready_for_shadow_import_dry_run:
        readiness_status = "shadow_candidate_dry_run_ready"
        activation_stage = ArtifactActivationStage.SHADOW_READY
        normalized_promotion_state = PromotionState.SHADOW_CANDIDATE
        review_state = ReviewState.PENDING
        blocking_reasons: tuple[str, ...] = ()
    elif release_candidate.ready_for_shadow_import:
        readiness_status = "shadow_candidate_pending_dry_run"
        activation_stage = ArtifactActivationStage.SHADOW_READY
        normalized_promotion_state = PromotionState.SHADOW_CANDIDATE
        review_state = ReviewState.PENDING
        blocking_reasons = tuple(
            dict.fromkeys(
                list(release_candidate.blocking_reasons) + list(dry_run_bridge.blocking_reasons)
            )
        )
    else:
        readiness_status = "local_only"
        activation_stage = ArtifactActivationStage.REPLAY_ONLY
        normalized_promotion_state = PromotionState.REPLAY_ONLY
        review_state = ReviewState.NEEDS_REVISION
        blocking_reasons = tuple(
            dict.fromkeys(
                list(release_candidate.blocking_reasons) + list(dry_run_bridge.blocking_reasons)
            )
        )

    return LocalLabPromotionReadinessSummary(
        correlation_id=release_candidate.correlation_id,
        run_id=release_candidate.run_id,
        export_dir=release_candidate.export_dir,
        artifact_id=release_candidate.artifact_id,
        artifact_path=release_candidate.artifact_path,
        target_runtime_mode=dry_run_bridge.target_runtime_mode,
        readiness_status=readiness_status,
        activation_stage=activation_stage,
        normalized_promotion_state=normalized_promotion_state,
        review_state=review_state,
        release_ready_for_shadow=release_candidate.ready_for_shadow_import,
        ready_for_shadow_import_dry_run=dry_run_bridge.ready_for_shadow_import_dry_run,
        artifact_proof_ready=release_candidate.artifact_proof_ready,
        artifact_proof_validation_reasons=release_candidate.artifact_proof_validation_reasons,
        recalibration_candidate_ready=release_candidate.recalibration_candidate_ready,
        recalibration_blocking_reasons=release_candidate.recalibration_blocking_reasons,
        release_gate_status=dry_run_bridge.release_gate_status,
        release_gate_reasons=dry_run_bridge.release_gate_reasons,
        local_release_status=release_candidate.release_status,
        dry_run_bridge_status=dry_run_bridge.bridge_status,
        blocking_reasons=blocking_reasons,
        scope_count=release_candidate.scope_count,
        release_ready_scope_count=release_candidate.ready_scope_count,
        release_blocked_scope_count=release_candidate.blocked_scope_count,
    )


__all__ = [
    "LocalLabPromotionReadinessSummary",
    "build_local_lab_promotion_readiness_summary",
]
