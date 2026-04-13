"""Dry-run governed bridge builder from Local IA Lab release candidates to VPS import contracts."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from calibration_loader.loader import CalibrationLoaderError, load_calibration_artifact
from backtest_artifact_import.contracts import (
    ArtifactImportDecision,
    ArtifactPayloadRefBundle,
    ArtifactUploadContext,
    ArtifactUploadDecision,
)
from backtest_artifact_import.export_dir_bridge import (
    ReplayPlanUploadBuildContext,
    build_artifact_export_bundle_from_replay_import_context,
    build_import_context_from_export_dir,
    build_upload_request_from_replay_plan,
)
from backtest_artifact_import.signature_policy import build_lab_fixture_signature_envelope
from backtest_artifact_import.upload_bridge import (
    build_artifact_upload_decision,
    build_import_request_from_upload_request,
)
from backtest_artifact_import.validators import validate_import_request
from interface_contracts import ArtifactClass, ArtifactLifecyclePolicy, ArtifactProofSummary

from local_replay_runtime.artifact_upload_bridge_candidate import (
    LocalLabArtifactUploadDryRunBridge,
    LocalLabReleaseGateSummary,
    LocalLabSourceArtifactSummary,
)
from local_replay_runtime.artifact_release_candidate import LocalLabArtifactReleaseCandidate
from local_replay_runtime.orchestrator import LocalReplayOrchestrator


def _dedupe(reasons: list[str] | tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(reasons))


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


def build_local_lab_source_artifact_summary(
    source_artifact_path: str,
) -> LocalLabSourceArtifactSummary:
    """Load the Local IA Lab source artifact and project a stable future-facing summary."""

    artifact = load_calibration_artifact(source_artifact_path)
    threshold_ids = tuple(entry.threshold_id for entry in artifact.thresholds)
    return LocalLabSourceArtifactSummary(
        artifact_id=artifact.artifact_id,
        artifact_family="calibration_artifact",
        schema_version=artifact.schema_version,
        version=artifact.version,
        produced_by=artifact.produced_by,
        source_artifact_path=source_artifact_path,
        threshold_ids=threshold_ids,
        threshold_count=len(threshold_ids),
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
        release_artifact_proof_validation_reasons=release_candidate.artifact_proof_validation_reasons,
        release_calibration_methods_review_status=release_candidate.calibration_methods_review_status,
        release_calibration_methods_review_ready=release_candidate.calibration_methods_review_ready,
        release_calibration_methods_dsr_pass=release_candidate.calibration_methods_dsr_pass,
        release_calibration_methods_walk_forward_plan_ready=(
            release_candidate.calibration_methods_walk_forward_plan_ready
        ),
        release_calibration_methods_review_ref=(
            release_candidate.local_lab_calibration_methods_review_path
        ),
        release_recalibration_candidate_ready=release_candidate.recalibration_candidate_ready,
        release_recalibration_blocking_reasons=release_candidate.recalibration_blocking_reasons,
        release_gate_status=release_gate_status,
        release_gate_reasons=release_gate_reasons,
    )


def _load_source_artifact_metadata(
    source_artifact_path: str,
) -> tuple[bool, LocalLabSourceArtifactSummary | None, tuple[str, ...]]:
    try:
        artifact_summary = build_local_lab_source_artifact_summary(source_artifact_path)
    except (CalibrationLoaderError, OSError, ValueError):
        return False, None, ("SOURCE_ARTIFACT_UNREADABLE",)
    return (
        True,
        artifact_summary,
        (),
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
            LocalLabArtifactUploadDryRunBridge(
                correlation_id=release_candidate.correlation_id,
                export_dir=release_candidate.export_dir,
                release_candidate_artifact_id=release_candidate.artifact_id,
                source_artifact_path=release_candidate.artifact_path,
                release_gate_summary_ref=release_gate_summary_ref,
                uploaded_by=uploaded_by,
                bridge_status="blocked_release_candidate",
                release_ready_for_shadow=release_candidate.ready_for_shadow_import,
                release_artifact_proof_ready=release_candidate.artifact_proof_ready,
                release_artifact_proof_validation_reasons=release_candidate.artifact_proof_validation_reasons,
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
                release_recalibration_blocking_reasons=release_candidate.recalibration_blocking_reasons,
                release_gate_status=release_gate_status,
                release_gate_reasons=release_gate_reasons,
                blocking_reasons=release_candidate.blocking_reasons,
            ),
            None,
        )

    blocking_reasons: list[str] = []
    if proof_summary is None:
        blocking_reasons.append("PROOF_SUMMARY_REQUIRED_FOR_DRY_RUN_BRIDGE")
    if governance_reference_date is None:
        blocking_reasons.append("GOVERNANCE_REFERENCE_DATE_REQUIRED")
    if training_end is None:
        blocking_reasons.append("TRAINING_END_REQUIRED")
    if artifact_class is None:
        blocking_reasons.append("ARTIFACT_CLASS_REQUIRED")
    if artifact_scope is None or not artifact_scope.strip():
        blocking_reasons.append("ARTIFACT_SCOPE_REQUIRED")
    if lifecycle_ttl_days is None:
        blocking_reasons.append("LIFECYCLE_TTL_DAYS_REQUIRED")
    if rule_half_life_days is None:
        blocking_reasons.append("RULE_HALF_LIFE_DAYS_REQUIRED")
    if drift_score_threshold is None:
        blocking_reasons.append("DRIFT_SCORE_THRESHOLD_REQUIRED")
    if source_artifact_summary_ref is None or not source_artifact_summary_ref.strip():
        blocking_reasons.append("SOURCE_ARTIFACT_SUMMARY_REQUIRED")
    if release_gate_summary_ref is None or not release_gate_summary_ref.strip():
        blocking_reasons.append("RELEASE_GATE_SUMMARY_REQUIRED")

    if blocking_reasons:
        return (
            LocalLabArtifactUploadDryRunBridge(
                correlation_id=release_candidate.correlation_id,
                export_dir=release_candidate.export_dir,
                release_candidate_artifact_id=release_candidate.artifact_id,
                source_artifact_path=release_candidate.artifact_path,
                source_artifact_summary_ref=source_artifact_summary_ref,
                release_gate_summary_ref=release_gate_summary_ref,
                uploaded_by=uploaded_by,
                governance_reference_date=governance_reference_date,
                training_end=training_end,
                artifact_class=None if artifact_class is None else artifact_class.value,
                artifact_scope=artifact_scope,
                lifecycle_ttl_days=lifecycle_ttl_days,
                rule_half_life_days=rule_half_life_days,
                drift_score_threshold=drift_score_threshold,
                bridge_status="blocked_missing_governance_inputs",
                release_ready_for_shadow=release_candidate.ready_for_shadow_import,
                release_artifact_proof_ready=release_candidate.artifact_proof_ready,
                release_artifact_proof_validation_reasons=release_candidate.artifact_proof_validation_reasons,
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
                release_recalibration_blocking_reasons=release_candidate.recalibration_blocking_reasons,
                release_gate_status=release_gate_status,
                release_gate_reasons=release_gate_reasons,
                blocking_reasons=_dedupe(blocking_reasons),
            ),
            None,
        )

    lifecycle_policy = ArtifactLifecyclePolicy(
        ttl_max_days=lifecycle_ttl_days,
        rule_half_life_days=rule_half_life_days,
    )
    source_artifact_ok, source_artifact_summary, source_artifact_reasons = _load_source_artifact_metadata(
        release_candidate.artifact_path
    )
    if not source_artifact_ok:
        return (
            LocalLabArtifactUploadDryRunBridge(
                correlation_id=release_candidate.correlation_id,
                export_dir=release_candidate.export_dir,
                release_candidate_artifact_id=release_candidate.artifact_id,
                source_artifact_path=release_candidate.artifact_path,
                source_artifact_summary_ref=source_artifact_summary_ref,
                release_gate_summary_ref=release_gate_summary_ref,
                uploaded_by=uploaded_by,
                governance_reference_date=governance_reference_date,
                training_end=training_end,
                artifact_class=artifact_class.value,
                artifact_scope=artifact_scope,
                lifecycle_ttl_days=lifecycle_ttl_days,
                rule_half_life_days=rule_half_life_days,
                drift_score_threshold=drift_score_threshold,
                bridge_status="blocked_source_artifact",
                release_ready_for_shadow=release_candidate.ready_for_shadow_import,
                release_artifact_proof_ready=release_candidate.artifact_proof_ready,
                release_artifact_proof_validation_reasons=release_candidate.artifact_proof_validation_reasons,
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
                release_recalibration_blocking_reasons=release_candidate.recalibration_blocking_reasons,
                release_gate_status=release_gate_status,
                release_gate_reasons=release_gate_reasons,
                blocking_reasons=source_artifact_reasons,
            ),
            None,
        )
    assert source_artifact_summary is not None
    import_context = build_import_context_from_export_dir(
        Path(release_candidate.export_dir),
        lifecycle_policy=lifecycle_policy,
        training_end=training_end,
        governance_reference_date=governance_reference_date,
        drift_score_threshold=drift_score_threshold,
    )
    local_replay_evidence = LocalReplayOrchestrator.build_runtime_evidence(
        import_context.replay_plan
    )
    if not local_replay_evidence.replay_useful_ready:
        return (
            LocalLabArtifactUploadDryRunBridge(
                correlation_id=release_candidate.correlation_id,
                export_dir=release_candidate.export_dir,
                release_candidate_artifact_id=release_candidate.artifact_id,
                source_artifact_path=release_candidate.artifact_path,
                source_artifact_summary_ref=source_artifact_summary_ref,
                release_gate_summary_ref=release_gate_summary_ref,
                uploaded_by=uploaded_by,
                governance_reference_date=governance_reference_date,
                training_end=training_end,
                artifact_class=artifact_class.value,
                artifact_scope=artifact_scope,
                lifecycle_ttl_days=lifecycle_ttl_days,
                rule_half_life_days=rule_half_life_days,
                drift_score_threshold=drift_score_threshold,
                bridge_status="blocked_local_replay_evidence",
                release_ready_for_shadow=release_candidate.ready_for_shadow_import,
                release_artifact_proof_ready=release_candidate.artifact_proof_ready,
                release_artifact_proof_validation_reasons=release_candidate.artifact_proof_validation_reasons,
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
                release_recalibration_blocking_reasons=release_candidate.recalibration_blocking_reasons,
                release_gate_status=release_gate_status,
                release_gate_reasons=release_gate_reasons,
                blocking_reasons=("LOCAL_REPLAY_EVIDENCE_NOT_READY",),
            ),
            None,
        )

    signature_envelope = build_lab_fixture_signature_envelope()
    artifact_bundle = build_artifact_export_bundle_from_replay_import_context(
        import_context,
        local_replay_evidence=local_replay_evidence,
        signature_envelope=signature_envelope,
        artifact_class=artifact_class,
        artifact_scope=artifact_scope,
        governance_reference_date=governance_reference_date,
        lifecycle_policy=lifecycle_policy,
        drift_score_threshold=drift_score_threshold,
        proof_summary=proof_summary,
    )
    base_payload_bundle = import_context.import_request.payload_bundle
    assert base_payload_bundle is not None
    enriched_payload_bundle = ArtifactPayloadRefBundle(
        review_export_ref=base_payload_bundle.review_export_ref,
        feature_bridge_ref=base_payload_bundle.feature_bridge_ref,
        parity_diagnostics_ref=base_payload_bundle.parity_diagnostics_ref,
        replay_metrics_ref=base_payload_bundle.replay_metrics_ref,
        replay_dtr_ref=base_payload_bundle.replay_dtr_ref,
        supplementary_refs=_dedupe(
            [
                *base_payload_bundle.supplementary_refs,
                release_candidate.artifact_path,
                source_artifact_summary_ref,
                release_gate_summary_ref,
            ]
        ),
    )
    upload_request = build_upload_request_from_replay_plan(
        import_context.replay_plan,
        payload_bundle=enriched_payload_bundle,
        bundle=artifact_bundle,
        signature_envelope=signature_envelope,
        uploaded_by=uploaded_by,
        upload_context=ArtifactUploadContext.LOCAL_LAB,
        governance_reference_date=governance_reference_date,
    )
    import_request = build_import_request_from_upload_request(upload_request)
    upload_build_context = ReplayPlanUploadBuildContext(
        import_context=import_context,
        local_replay_evidence=local_replay_evidence,
        artifact_bundle=artifact_bundle,
        signature_envelope=signature_envelope,
        upload_request=upload_request,
        import_request=import_request,
    )
    import_decision = validate_import_request(upload_build_context.import_request)
    upload_decision = build_artifact_upload_decision(
        upload_build_context.upload_request,
        import_decision,
    )
    upload_build_context = upload_build_context.model_copy(
        update={
            "import_decision": import_decision,
            "upload_decision": upload_decision,
        }
    )

    ready_for_shadow_import_dry_run = import_decision.accepted and upload_decision.accepted
    bridge_status = "dry_run_ready" if ready_for_shadow_import_dry_run else "dry_run_rejected"
    semantic_reasons: list[str] = []
    transport_artifact_id = upload_build_context.upload_request.bundle.artifact_id
    transport_artifact_kind = upload_build_context.import_request.artifact_kind.value
    if source_artifact_summary.artifact_id != transport_artifact_id:
        semantic_reasons.append("TRANSPORT_ARTIFACT_ID_DIFFERS_FROM_SOURCE_ARTIFACT_ID")
    if transport_artifact_kind == "review_packet":
        semantic_reasons.append("TRANSPORT_KIND_IS_REVIEW_PACKET")
    if release_candidate.artifact_path in upload_build_context.upload_request.payload_bundle.supplementary_refs:
        semantic_reasons.append("TRANSPORT_SUPPLEMENTARY_REFS_CARRY_SOURCE_ARTIFACT")
    if source_artifact_summary_ref in upload_build_context.upload_request.payload_bundle.supplementary_refs:
        semantic_reasons.append("TRANSPORT_SUPPLEMENTARY_REFS_CARRY_SOURCE_ARTIFACT_SUMMARY")
    if release_gate_summary_ref in upload_build_context.upload_request.payload_bundle.supplementary_refs:
        semantic_reasons.append("TRANSPORT_SUPPLEMENTARY_REFS_CARRY_RELEASE_GATE_SUMMARY")
    semantic_status = (
        "transport_packet_with_source_artifact_refs"
        if semantic_reasons
        else "source_and_transport_aligned"
    )

    return (
        LocalLabArtifactUploadDryRunBridge(
            correlation_id=release_candidate.correlation_id,
            export_dir=release_candidate.export_dir,
            release_candidate_artifact_id=release_candidate.artifact_id,
            source_artifact_id=source_artifact_summary.artifact_id,
            source_artifact_family=source_artifact_summary.artifact_family,
            source_artifact_schema_version=source_artifact_summary.schema_version,
            source_artifact_version=source_artifact_summary.version,
            governed_artifact_id=transport_artifact_id,
            transport_artifact_id=transport_artifact_id,
            source_artifact_path=release_candidate.artifact_path,
            source_artifact_summary_ref=source_artifact_summary_ref,
            release_gate_summary_ref=release_gate_summary_ref,
            artifact_kind=transport_artifact_kind,
            transport_artifact_kind=transport_artifact_kind,
            artifact_class=artifact_class.value,
            artifact_scope=artifact_scope,
            uploaded_by=uploaded_by,
            governance_reference_date=governance_reference_date,
            training_end=training_end,
            lifecycle_ttl_days=lifecycle_ttl_days,
            rule_half_life_days=rule_half_life_days,
            drift_score_threshold=drift_score_threshold,
            transport_payload_ref_count=len(upload_build_context.upload_request.payload_bundle.payload_refs),
            transport_supplementary_refs=upload_build_context.upload_request.payload_bundle.supplementary_refs,
            bridge_status=bridge_status,
            ready_for_shadow_import_dry_run=ready_for_shadow_import_dry_run,
            release_ready_for_shadow=release_candidate.ready_for_shadow_import,
            release_artifact_proof_ready=release_candidate.artifact_proof_ready,
            release_artifact_proof_validation_reasons=release_candidate.artifact_proof_validation_reasons,
            release_calibration_methods_review_status=release_candidate.calibration_methods_review_status,
            release_calibration_methods_review_ready=release_candidate.calibration_methods_review_ready,
            release_calibration_methods_dsr_pass=release_candidate.calibration_methods_dsr_pass,
            release_calibration_methods_walk_forward_plan_ready=(
                release_candidate.calibration_methods_walk_forward_plan_ready
            ),
            release_calibration_methods_review_ref=(
                release_candidate.local_lab_calibration_methods_review_path
            ),
            release_recalibration_candidate_ready=release_candidate.recalibration_candidate_ready,
            release_recalibration_blocking_reasons=release_candidate.recalibration_blocking_reasons,
            release_gate_status=release_gate_status,
            release_gate_reasons=release_gate_reasons,
            blocking_reasons=(
                ()
                if ready_for_shadow_import_dry_run
                else _dedupe(list(import_decision.reasons) + list(upload_decision.rejection_reasons))
            ),
            import_decision_reasons=import_decision.reasons,
            upload_decision_status=upload_decision.status.value,
            semantic_status=semantic_status,
            semantic_reasons=_dedupe(semantic_reasons),
        ),
        upload_build_context,
    )


__all__ = [
    "LocalLabReleaseGateSummary",
    "build_local_lab_release_gate_summary",
    "LocalLabSourceArtifactSummary",
    "build_local_lab_source_artifact_summary",
    "LocalLabArtifactUploadDryRunBridge",
    "build_local_lab_artifact_upload_dry_run_bridge",
]
