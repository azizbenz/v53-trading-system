"""Thin governed bridge from upload dry-run payloads to import contracts."""

from __future__ import annotations

from backtest_artifact_import.contracts import (
    ArtifactImportDecision,
    ArtifactImportRequest,
    ArtifactUploadDecision,
    ArtifactUploadRequest,
    ArtifactUploadStatus,
)

_SCHEMA_REASONS = {
    "ARTIFACT_SCHEMA_UNKNOWN",
    "ARTIFACT_SCHEMA_MAJOR_INCOMPATIBLE",
    "ARTIFACT_SCHEMA_MINOR_UNSUPPORTED",
    "FEATURE_SET_UNKNOWN",
    "FEATURE_SET_INCOMPATIBLE",
    "TRANSFORM_SET_UNKNOWN",
    "TRANSFORM_SET_INCOMPATIBLE",
    "ARTIFACT_REQUIRES_MIGRATION",
}

_SIGNATURE_REASONS = {
    "SIGNATURE_INVALID",
    "KEY_ID_UNKNOWN",
    "KEY_REVOKED",
    "PAYLOAD_HASH_MISMATCH",
    "TRUST_STORE_UNAVAILABLE",
}


def build_import_request_from_upload_request(
    request: ArtifactUploadRequest,
) -> ArtifactImportRequest:
    """Convert a governed upload dry-run request into the bounded import contract."""

    expected_feature_ids = tuple(
        dict.fromkeys(
            (
                *(condition.feature_id for rule in request.bundle.rules for condition in rule.conditions),
                *request.bundle.regime_features_used,
            )
        )
    )
    expected_transform_ids = tuple(
        dict.fromkeys(
            transform_id
            for record in request.bundle.feature_lineage_lock.records
            for transform_id in record.transform_ids
        )
    )

    return ArtifactImportRequest(
        manifest=request.manifest,
        artifact_kind=request.artifact_kind,
        payload_bundle=request.payload_bundle,
        payload_refs=request.payload_bundle.payload_refs,
        feature_lineage_lock=request.bundle.feature_lineage_lock,
        feature_lineage_required=True,
        expected_feature_ids=expected_feature_ids,
        transform_whitelist_lock=request.bundle.transform_whitelist_lock,
        transform_whitelist_required=True,
        expected_transform_ids=expected_transform_ids,
        lifecycle_policy=request.bundle.lifecycle_policy,
        training_end=request.bundle.training_end,
        governance_reference_date=request.governance_reference_date,
        drift_score_threshold=request.bundle.drift_score_threshold,
        proof_summary=request.bundle.proof_summary,
        proof_required=True,
        target_runtime_mode=request.target_runtime_mode,
        requested_promotion_state=request.requested_promotion_state,
        review_state=request.review_state,
    )


def build_artifact_upload_decision(
    request: ArtifactUploadRequest,
    import_decision: ArtifactImportDecision,
) -> ArtifactUploadDecision:
    """Map bounded import-decision outcomes into upload dry-run vocabulary."""

    reasons = set(import_decision.reasons)
    if import_decision.accepted:
        status = ArtifactUploadStatus.DRY_RUN_OK if request.dry_run else ArtifactUploadStatus.REGISTERED
    elif reasons & _SIGNATURE_REASONS:
        status = ArtifactUploadStatus.REJECTED_SIGNATURE
    elif reasons & _SCHEMA_REASONS:
        status = ArtifactUploadStatus.REJECTED_SCHEMA
    elif any(reason.upper().startswith("PROOF_") for reason in reasons):
        status = ArtifactUploadStatus.REJECTED_PROOF
    else:
        status = ArtifactUploadStatus.REJECTED_SCOPE
    return ArtifactUploadDecision(
        artifact_id=request.bundle.artifact_id,
        accepted=import_decision.accepted,
        status=status,
        rejection_reasons=import_decision.reasons,
    )


__all__ = [
    "build_import_request_from_upload_request",
    "build_artifact_upload_decision",
]
