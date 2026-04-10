"""Future-facing Local IA Lab artifact release candidate for governed VPS import."""

from __future__ import annotations

from pydantic import BaseModel, Field

from interface_contracts.domain_types import RuntimeMode

from local_replay_runtime.local_lab_scope_matrix import LocalLabScopeAnalysisMatrix


class LocalLabArtifactReleaseScope(BaseModel, frozen=True):
    """Per-scope release readiness projected from the Local IA Lab analysis matrix."""

    pair: str = Field(..., min_length=1)
    engine_id: str = Field(..., min_length=1)
    scope_slug: str = Field(..., min_length=1)
    review_bundle_path: str | None = None
    trade_loss_attribution_path: str | None = None
    artifact_proof_summary_path: str | None = None
    artifact_proof_assessment_path: str | None = None
    executed_records: int = Field(default=0, ge=0)
    losing_trade_count: int = Field(default=0, ge=0)
    release_scope_summary_path: str | None = None
    release_ready: bool = False
    blocking_reasons: tuple[str, ...] = ()


class LocalLabArtifactReleaseScopeSummary(BaseModel, frozen=True):
    """Per-scope packaging drill-down for future Local IA Lab dashboards and operator review."""

    correlation_id: str = Field(..., min_length=1)
    run_id: str = Field(..., min_length=1)
    export_dir: str = Field(..., min_length=1)
    release_candidate_artifact_id: str = Field(..., min_length=1)
    artifact_path: str = Field(..., min_length=1)
    pair: str = Field(..., min_length=1)
    engine_id: str = Field(..., min_length=1)
    scope_slug: str = Field(..., min_length=1)
    release_status: str = Field(..., min_length=1)
    ready_for_shadow_import: bool = False
    review_bundle_path: str | None = None
    trade_loss_attribution_path: str | None = None
    artifact_proof_summary_path: str | None = None
    artifact_proof_assessment_path: str | None = None
    executed_records: int = Field(default=0, ge=0)
    losing_trade_count: int = Field(default=0, ge=0)
    scope_release_ready: bool = False
    scope_blocking_reasons: tuple[str, ...] = ()
    shared_release_gate_summary_path: str | None = None
    shared_source_artifact_summary_path: str | None = None
    shared_artifact_import_dry_run_bridge_path: str | None = None


class LocalLabArtifactReleaseCandidate(BaseModel, frozen=True):
    """Audit-ready packaging candidate emitted before any VPS import request is built."""

    correlation_id: str = Field(..., min_length=1)
    export_dir: str = Field(..., min_length=1)
    baseline_export_dir: str | None = None
    run_id: str = Field(..., min_length=1)
    artifact_id: str = Field(..., min_length=1)
    artifact_path: str = Field(..., min_length=1)
    artifact_input_summary_path: str = Field(..., min_length=1)
    walk_forward_review_summary_path: str = Field(..., min_length=1)
    local_lab_recalibration_plan_path: str | None = None
    artifact_proof_summary_path: str | None = None
    artifact_proof_assessment_path: str | None = None
    scope_matrix_path: str | None = None
    target_runtime_mode: RuntimeMode = RuntimeMode.SHADOW
    release_status: str = Field(..., min_length=1)
    ready_for_shadow_import: bool = False
    artifact_proof_ready: bool = False
    artifact_proof_validation_reasons: tuple[str, ...] = ()
    recalibration_candidate_ready: bool = False
    recalibration_blocking_reasons: tuple[str, ...] = ()
    scope_count: int = Field(default=0, ge=0)
    ready_scope_count: int = Field(default=0, ge=0)
    blocked_scope_count: int = Field(default=0, ge=0)
    release_scopes: tuple[LocalLabArtifactReleaseScope, ...] = ()
    blocking_reasons: tuple[str, ...] = ()


def build_local_lab_artifact_release_candidate(
    *,
    correlation_id: str,
    export_dir: str,
    baseline_export_dir: str | None,
    run_id: str,
    artifact_id: str,
    artifact_path: str,
    artifact_input_summary_path: str,
    walk_forward_review_summary_path: str,
    local_lab_recalibration_plan_path: str | None,
    edge_calibration_ready: bool,
    recalibration_candidate_ready: bool,
    recalibration_blocking_reasons: tuple[str, ...],
    artifact_proof_ready: bool,
    artifact_proof_validation_reasons: tuple[str, ...],
    artifact_proof_summary_path: str | None = None,
    artifact_proof_assessment_path: str | None = None,
    scope_matrix_path: str | None = None,
    scope_matrix: LocalLabScopeAnalysisMatrix | None = None,
) -> LocalLabArtifactReleaseCandidate:
    """Build a conservative Local IA Lab packaging candidate for future VPS import."""

    blocking_reasons: list[str] = []
    if local_lab_recalibration_plan_path is None or not local_lab_recalibration_plan_path.strip():
        blocking_reasons.append("RECALIBRATION_PLAN_REQUIRED")
    if not edge_calibration_ready:
        blocking_reasons.append("EDGE_CALIBRATION_NOT_READY")
    blocking_reasons.extend(
        reason
        for reason in recalibration_blocking_reasons
        if reason != "NO_LOSING_TRADES_TO_RECALIBRATE"
    )
    blocking_reasons.extend(artifact_proof_validation_reasons)

    release_scopes: tuple[LocalLabArtifactReleaseScope, ...] = ()
    scope_count = 0
    ready_scope_count = 0
    blocked_scope_count = 0
    if scope_matrix is not None:
        release_scopes = tuple(
            LocalLabArtifactReleaseScope(
                pair=scope.pair,
                engine_id=scope.engine_id,
                scope_slug=scope.scope_slug,
                review_bundle_path=scope.review_bundle_path,
                trade_loss_attribution_path=scope.trade_loss_attribution_path,
                artifact_proof_summary_path=scope.artifact_proof_summary_path,
                artifact_proof_assessment_path=scope.artifact_proof_assessment_path,
                executed_records=scope.executed_records,
                losing_trade_count=scope.losing_trade_count,
                release_ready=scope.artifact_proof_ready,
                blocking_reasons=scope.artifact_proof_validation_reasons,
            )
            for scope in scope_matrix.scopes
        )
        scope_count = scope_matrix.scope_count
        ready_scope_count = scope_matrix.ready_scope_count
        blocked_scope_count = scope_matrix.blocked_scope_count

    ready_for_shadow_import = edge_calibration_ready and artifact_proof_ready and not blocking_reasons
    release_status = "shadow_candidate" if ready_for_shadow_import else "local_only"

    return LocalLabArtifactReleaseCandidate(
        correlation_id=correlation_id,
        export_dir=export_dir,
        baseline_export_dir=baseline_export_dir,
        run_id=run_id,
        artifact_id=artifact_id,
        artifact_path=artifact_path,
        artifact_input_summary_path=artifact_input_summary_path,
        walk_forward_review_summary_path=walk_forward_review_summary_path,
        local_lab_recalibration_plan_path=local_lab_recalibration_plan_path,
        artifact_proof_summary_path=artifact_proof_summary_path,
        artifact_proof_assessment_path=artifact_proof_assessment_path,
        scope_matrix_path=scope_matrix_path,
        target_runtime_mode=RuntimeMode.SHADOW,
        release_status=release_status,
        ready_for_shadow_import=ready_for_shadow_import,
        artifact_proof_ready=artifact_proof_ready,
        artifact_proof_validation_reasons=artifact_proof_validation_reasons,
        recalibration_candidate_ready=recalibration_candidate_ready,
        recalibration_blocking_reasons=recalibration_blocking_reasons,
        scope_count=scope_count,
        ready_scope_count=ready_scope_count,
        blocked_scope_count=blocked_scope_count,
        release_scopes=release_scopes,
        blocking_reasons=tuple(dict.fromkeys(blocking_reasons)),
    )


def build_local_lab_artifact_release_scope_summary(
    *,
    release_candidate: LocalLabArtifactReleaseCandidate,
    scope: LocalLabArtifactReleaseScope,
    shared_release_gate_summary_path: str | None,
    shared_source_artifact_summary_path: str | None,
    shared_artifact_import_dry_run_bridge_path: str | None,
) -> LocalLabArtifactReleaseScopeSummary:
    """Build a per-scope drill-down summary around the shared Local IA Lab packaging verdict."""

    return LocalLabArtifactReleaseScopeSummary(
        correlation_id=release_candidate.correlation_id,
        run_id=release_candidate.run_id,
        export_dir=release_candidate.export_dir,
        release_candidate_artifact_id=release_candidate.artifact_id,
        artifact_path=release_candidate.artifact_path,
        pair=scope.pair,
        engine_id=scope.engine_id,
        scope_slug=scope.scope_slug,
        release_status=release_candidate.release_status,
        ready_for_shadow_import=release_candidate.ready_for_shadow_import,
        review_bundle_path=scope.review_bundle_path,
        trade_loss_attribution_path=scope.trade_loss_attribution_path,
        artifact_proof_summary_path=scope.artifact_proof_summary_path,
        artifact_proof_assessment_path=scope.artifact_proof_assessment_path,
        executed_records=scope.executed_records,
        losing_trade_count=scope.losing_trade_count,
        scope_release_ready=scope.release_ready,
        scope_blocking_reasons=scope.blocking_reasons,
        shared_release_gate_summary_path=shared_release_gate_summary_path,
        shared_source_artifact_summary_path=shared_source_artifact_summary_path,
        shared_artifact_import_dry_run_bridge_path=shared_artifact_import_dry_run_bridge_path,
    )


__all__ = [
    "LocalLabArtifactReleaseCandidate",
    "LocalLabArtifactReleaseScope",
    "LocalLabArtifactReleaseScopeSummary",
    "build_local_lab_artifact_release_candidate",
    "build_local_lab_artifact_release_scope_summary",
]
