"""Dry-run governed bridge builder from Local IA Lab release candidates to VPS import contracts."""

from __future__ import annotations

from datetime import date

from backtest_artifact_import.local_lab_upload_bridge_candidate_support import (
    _build_base_upload_bridge,
    _build_upload_bridge_from_import_context,
    _collect_missing_governance_inputs,
    _dedupe,
    _load_source_artifact_metadata,
    build_local_lab_source_artifact_summary,
)
from backtest_artifact_import.export_dir_bridge import ReplayPlanUploadBuildContext
from interface_contracts import ArtifactClass, ArtifactLifecyclePolicy, ArtifactProofSummary
from local_replay_runtime.artifact_upload_bridge_candidate import (
    LocalLabArtifactUploadDryRunBridge,
    LocalLabReleaseGateSummary,
    LocalLabSourceArtifactSummary,
)
from local_replay_runtime.artifact_release_candidate import LocalLabArtifactReleaseCandidate


def _benign_recalibration_blockers(reasons: tuple[str, ...]) -> bool:
    return bool(reasons) and set(reasons) == {"NO_LOSING_TRADES_TO_RECALIBRATE"}


def _evaluate_release_gate(
    release_candidate: LocalLabArtifactReleaseCandidate,
) -> tuple[str, tuple[str, ...]]:
    reasons: list[str] = []
    if release_candidate.artifact_proof_ready:
        reasons.append("PROOF_GATE_PASSED")
    else:
        reasons.extend(release_candidate.artifact_proof_validation_reasons)
    if release_candidate.recalibration_candidate_ready:
        reasons.append("RECALIBRATION_GATE_PASSED")
    elif _benign_recalibration_blockers(release_candidate.recalibration_blocking_reasons):
        reasons.append("RECALIBRATION_NOT_REQUIRED")
    else:
        reasons.extend(release_candidate.recalibration_blocking_reasons)
    if release_candidate.ready_for_shadow_import:
        if release_candidate.recalibration_candidate_ready:
            return "proof_and_recalibration_backed", _dedupe(reasons)
        return "proof_backed_no_recalibration_required", _dedupe(reasons)
    if not release_candidate.artifact_proof_ready:
        return "proof_gate_blocked", _dedupe(reasons)
    if release_candidate.recalibration_blocking_reasons and not _benign_recalibration_blockers(
        release_candidate.recalibration_blocking_reasons
    ):
        return "recalibration_gate_blocked", _dedupe(reasons)
    return "release_candidate_blocked", _dedupe(
        list(reasons) + list(release_candidate.blocking_reasons)
    )


def build_local_lab_release_gate_summary(
    release_candidate: LocalLabArtifactReleaseCandidate,
) -> LocalLabReleaseGateSummary:
    """Project the packaging gate verdict into a future-facing stable sidecar."""

    release_gate_status, release_gate_reasons = _evaluate_release_gate(release_candidate)
    return LocalLabReleaseGateSummary(
        correlation_id=release_candidate.correlation_id,
        release_candidate_artifact_id=release_candidate.artifact_id,
        release_ready_for_shadow=release_candidate.ready_for_shadow_import,
        release_artifact_proof_ready=release_candidate.artifact_proof_ready,
        release_artifact_proof_validation_reasons=(
            release_candidate.artifact_proof_validation_reasons
        ),
        release_calibration_methods_review_status=(
            release_candidate.calibration_methods_review_status
        ),
        release_calibration_methods_review_ready=(
            release_candidate.calibration_methods_review_ready
        ),
        release_calibration_methods_dsr_pass=release_candidate.calibration_methods_dsr_pass,
        release_calibration_methods_walk_forward_plan_ready=(
            release_candidate.calibration_methods_walk_forward_plan_ready
        ),
        release_calibration_methods_review_ref=(
            release_candidate.local_lab_calibration_methods_review_path
        ),
        release_recalibration_candidate_ready=release_candidate.recalibration_candidate_ready,
        release_recalibration_blocking_reasons=(
            release_candidate.recalibration_blocking_reasons
        ),
        release_gate_status=release_gate_status,
        release_gate_reasons=release_gate_reasons,
    )


def build_local_lab_artifact_upload_dry_run_bridge(
    *,
    release_candidate: LocalLabArtifactReleaseCandidate,
    proof_summary: ArtifactProofSummary | None,
    governance_reference_date: date | None,
    training_end: date | None,
    artifact_class: ArtifactClass | None,
    artifact_scope: str | None,
    lifecycle_ttl_days: int | None,
    rule_half_life_days: int | None,
    drift_score_threshold: float | None,
    uploaded_by: str,
    source_artifact_summary_ref: str | None = None,
    release_gate_summary_ref: str | None = None,
) -> tuple[LocalLabArtifactUploadDryRunBridge, ReplayPlanUploadBuildContext | None]:
    """Build a dry-run governed import/upload bridge when the Local IA Lab release is ready."""

    release_gate_status, release_gate_reasons = _evaluate_release_gate(release_candidate)
    if not release_candidate.ready_for_shadow_import:
        return (
            _build_base_upload_bridge(
                release_candidate=release_candidate,
                uploaded_by=uploaded_by,
                source_artifact_summary_ref=None,
                release_gate_summary_ref=release_gate_summary_ref,
                governance_reference_date=None,
                training_end=None,
                artifact_class_value=None,
                artifact_scope=None,
                lifecycle_ttl_days=None,
                rule_half_life_days=None,
                drift_score_threshold=None,
                bridge_status="blocked_release_candidate",
                release_gate_status=release_gate_status,
                release_gate_reasons=release_gate_reasons,
                blocking_reasons=release_candidate.blocking_reasons,
            ),
            None,
        )

    blocking_reasons = _collect_missing_governance_inputs(
        proof_summary=proof_summary,
        governance_reference_date=governance_reference_date,
        training_end=training_end,
        artifact_class=artifact_class,
        artifact_scope=artifact_scope,
        lifecycle_ttl_days=lifecycle_ttl_days,
        rule_half_life_days=rule_half_life_days,
        drift_score_threshold=drift_score_threshold,
        source_artifact_summary_ref=source_artifact_summary_ref,
        release_gate_summary_ref=release_gate_summary_ref,
    )

    if blocking_reasons:
        return (
            _build_base_upload_bridge(
                release_candidate=release_candidate,
                uploaded_by=uploaded_by,
                source_artifact_summary_ref=source_artifact_summary_ref,
                release_gate_summary_ref=release_gate_summary_ref,
                governance_reference_date=governance_reference_date,
                training_end=training_end,
                artifact_class_value=None if artifact_class is None else artifact_class.value,
                artifact_scope=artifact_scope,
                lifecycle_ttl_days=lifecycle_ttl_days,
                rule_half_life_days=rule_half_life_days,
                drift_score_threshold=drift_score_threshold,
                bridge_status="blocked_missing_governance_inputs",
                release_gate_status=release_gate_status,
                release_gate_reasons=release_gate_reasons,
                blocking_reasons=blocking_reasons,
            ),
            None,
        )

    lifecycle_policy = ArtifactLifecyclePolicy(
        ttl_max_days=lifecycle_ttl_days,
        rule_half_life_days=rule_half_life_days,
    )
    source_artifact_ok, source_artifact_summary, source_artifact_reasons = (
        _load_source_artifact_metadata(release_candidate.artifact_path)
    )
    if not source_artifact_ok:
        return (
            _build_base_upload_bridge(
                release_candidate=release_candidate,
                uploaded_by=uploaded_by,
                source_artifact_summary_ref=source_artifact_summary_ref,
                release_gate_summary_ref=release_gate_summary_ref,
                governance_reference_date=governance_reference_date,
                training_end=training_end,
                artifact_class_value=artifact_class.value,
                artifact_scope=artifact_scope,
                lifecycle_ttl_days=lifecycle_ttl_days,
                rule_half_life_days=rule_half_life_days,
                drift_score_threshold=drift_score_threshold,
                bridge_status="blocked_source_artifact",
                release_gate_status=release_gate_status,
                release_gate_reasons=release_gate_reasons,
                blocking_reasons=source_artifact_reasons,
            ),
            None,
        )
    assert source_artifact_summary is not None
    return _build_upload_bridge_from_import_context(
        release_candidate=release_candidate,
        source_artifact_summary=source_artifact_summary,
        proof_summary=proof_summary,
        governance_reference_date=governance_reference_date,
        training_end=training_end,
        artifact_class=artifact_class,
        artifact_scope=artifact_scope,
        lifecycle_policy=lifecycle_policy,
        drift_score_threshold=drift_score_threshold,
        uploaded_by=uploaded_by,
        source_artifact_summary_ref=source_artifact_summary_ref,
        release_gate_summary_ref=release_gate_summary_ref,
        release_gate_status=release_gate_status,
        release_gate_reasons=release_gate_reasons,
    )


__all__ = [
    "LocalLabReleaseGateSummary",
    "build_local_lab_release_gate_summary",
    "LocalLabSourceArtifactSummary",
    "build_local_lab_source_artifact_summary",
    "LocalLabArtifactUploadDryRunBridge",
    "build_local_lab_artifact_upload_dry_run_bridge",
]
