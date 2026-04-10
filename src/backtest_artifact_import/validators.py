"""Guards for controlled artifact import."""

from __future__ import annotations

from backtest_artifact_import.contracts import (
    ArtifactImportDecision,
    ArtifactImportRequest,
    ArtifactImportSummary,
    StrategyOnboardingDecision,
    StrategyOnboardingRequest,
)
from backtest_artifact_import.compatibility_policy import (
    evaluate_artifact_compatibility_policy,
)
from backtest_artifact_import.signature_policy import (
    ArtifactSignatureVerifier,
    DEFAULT_ARTIFACT_TRUST_STORE,
    evaluate_artifact_signature_policy,
)
from interface_contracts import (
    NON_ACTIVE_ARTIFACT_HEALTH_STATES,
    ArtifactActionKind,
    CANONICAL_ARTIFACT_CONFLICT_POLICY,
    CANONICAL_COMPILED_ARTIFACT_REGISTRY_POLICY,
    evaluate_artifact_runtime_governance,
    ProfileId,
    PromotionState,
    ReviewState,
    RuntimeMode,
    StrategyClassification,
    validate_artifact_proof_summary,
    validate_feature_lineage_lock,
    validate_transform_whitelist_lock,
)
from local_replay_runtime.artifact_manifest import ArtifactManifest
from local_replay_runtime.enums import ReplayArtifactKind


def validate_artifact_manifest(manifest: ArtifactManifest) -> None:
    """Rely on ArtifactManifest model validation for canonical guards."""
    ArtifactManifest.model_validate(manifest.model_dump())


def validate_import_request(
    request: ArtifactImportRequest,
    *,
    expected_payload_hash_sha256: str | None = None,
    signature_verifier: ArtifactSignatureVerifier | None = None,
) -> ArtifactImportDecision:
    """Validate import request without bypassing promotion gates."""
    validate_artifact_manifest(request.manifest)

    reasons: list[str] = []
    compatibility_check = evaluate_artifact_compatibility_policy(request.manifest)
    reasons.extend(compatibility_check.reasons)
    signature_check = evaluate_artifact_signature_policy(
        request.manifest,
        trust_store=DEFAULT_ARTIFACT_TRUST_STORE,
        expected_payload_hash_sha256=expected_payload_hash_sha256,
        signature_verifier=signature_verifier,
    )
    reasons.extend(signature_check.reasons)

    if request.target_runtime_mode != RuntimeMode.SHADOW:
        reasons.append("import target must start at SHADOW")

    if request.requested_promotion_state in {
        PromotionState.MICRO_LIVE_CANDIDATE,
        PromotionState.LIVE_CANDIDATE,
    }:
        reasons.append("implicit promotion beyond SHADOW is forbidden")

    if request.manifest.exported_from != "local":
        reasons.append("unsupported artifact origin")

    if request.manifest.source_profile != ProfileId.COMPLETE:
        reasons.append("governed import requires source_profile=COMPLETE")

    if request.manifest.health_state in NON_ACTIVE_ARTIFACT_HEALTH_STATES:
        reasons.append("artifact health state blocks governed import")

    if request.manifest.allowed_hook_ids and not request.manifest.allowed_action_kinds:
        reasons.append("governed hook declarations require explicit action kinds")

    if request.manifest.allowed_action_kinds and not request.manifest.allowed_hook_ids:
        reasons.append("explicit action kinds require governed hook declarations")

    if (
        any(
            kind in request.manifest.allowed_action_kinds
            for kind in (
                ArtifactActionKind.SOFT_BOOST,
                ArtifactActionKind.SOFT_REDUCE,
                ArtifactActionKind.SIZE_REDUCE,
                ArtifactActionKind.RANK_ADJUST,
            )
        )
        and not request.manifest.allowed_action_units
    ):
        reasons.append("governed action kinds require explicit action units")

    if len(set(request.payload_refs)) != len(request.payload_refs):
        reasons.append("payload refs must be unique")

    if not request.payload_refs:
        reasons.append("payload refs are required for governed import")

    if request.artifact_kind == ReplayArtifactKind.REVIEW_PACKET:
        if not request.manifest.review_export_ref:
            reasons.append("review packets require a review export ref")
        elif request.manifest.review_export_ref not in request.payload_refs:
            reasons.append("review export ref must be included in payload refs")

    if request.payload_bundle is not None:
        if request.manifest.review_export_ref != request.payload_bundle.review_export_ref:
            reasons.append("manifest review_export_ref must match payload bundle")
        if request.manifest.feature_bridge_ref != request.payload_bundle.feature_bridge_ref:
            reasons.append("manifest feature_bridge_ref must match payload bundle")
        if request.manifest.parity_diagnostics_ref != request.payload_bundle.parity_diagnostics_ref:
            reasons.append("manifest parity_diagnostics_ref must match payload bundle")
        if request.manifest.replay_metrics_ref != request.payload_bundle.replay_metrics_ref:
            reasons.append("manifest replay_metrics_ref must match payload bundle")
        if request.manifest.replay_dtr_ref != request.payload_bundle.replay_dtr_ref:
            reasons.append("manifest replay_dtr_ref must match payload bundle")

    if not request.manifest.dataset_ref or not request.manifest.clock_ref:
        reasons.append("dataset and clock refs are required for governed import")
    if not request.manifest.feature_bridge_ref:
        reasons.append("feature bridge ref is required for governed import")
    elif request.manifest.feature_bridge_ref not in request.payload_refs:
        reasons.append("feature bridge ref must be included in payload refs")
    if not request.manifest.parity_diagnostics_ref:
        reasons.append("parity diagnostics ref is required for governed import")
    elif request.manifest.parity_diagnostics_ref not in request.payload_refs:
        reasons.append("parity diagnostics ref must be included in payload refs")
    if not request.manifest.replay_metrics_ref:
        reasons.append("replay metrics ref is required for governed import")
    elif request.manifest.replay_metrics_ref not in request.payload_refs:
        reasons.append("replay metrics ref must be included in payload refs")
    if not request.manifest.replay_dtr_ref:
        reasons.append("replay dtr ref is required for governed import")
    elif request.manifest.replay_dtr_ref not in request.payload_refs:
        reasons.append("replay dtr ref must be included in payload refs")

    if request.feature_lineage_required:
        if request.feature_lineage_lock is None:
            reasons.append("feature lineage lock is required for governed artifact upload")
        else:
            if (
                request.feature_lineage_lock.feature_set_version
                != request.manifest.feature_set_version
            ):
                reasons.append(
                    "feature lineage lock feature_set_version must match manifest"
                )
            if (
                request.feature_lineage_lock.transform_set_version
                != request.manifest.transform_set_version
            ):
                reasons.append(
                    "feature lineage lock transform_set_version must match manifest"
                )
            reasons.extend(
                f"feature lineage lock: {reason}"
                for reason in validate_feature_lineage_lock(
                    request.expected_feature_ids,
                    request.feature_lineage_lock,
                )
            )

    if request.transform_whitelist_required:
        if request.transform_whitelist_lock is None:
            reasons.append(
                "transform whitelist lock is required for governed artifact upload"
            )
        else:
            if (
                request.transform_whitelist_lock.transform_set_version
                != request.manifest.transform_set_version
            ):
                reasons.append(
                    "transform whitelist lock transform_set_version must match manifest"
                )
            reasons.extend(
                f"transform whitelist lock: {reason}"
                for reason in validate_transform_whitelist_lock(
                    request.expected_transform_ids,
                    request.transform_whitelist_lock,
                )
            )

    runtime_governance = evaluate_artifact_runtime_governance(
        training_end=request.training_end,
        lifecycle_policy=request.lifecycle_policy,
        governance_reference_date=request.governance_reference_date,
        drift_score_threshold=request.drift_score_threshold,
        observed_drift_score=request.observed_drift_score,
    )
    reasons.extend(runtime_governance.ttl_reasons)
    reasons.extend(runtime_governance.drift_reasons)

    if request.proof_required:
        if request.proof_summary is None:
            reasons.append("PROOF_SUMMARY_REQUIRED")
        else:
            reasons.extend(validate_artifact_proof_summary(request.proof_summary))

    accepted = len(reasons) == 0
    normalized_state = (
        PromotionState.SHADOW_CANDIDATE if accepted else PromotionState.REPLAY_ONLY
    )
    review_state = ReviewState.PENDING if accepted else ReviewState.NEEDS_REVISION

    return ArtifactImportDecision(
        accepted=accepted,
        normalized_promotion_state=normalized_state,
        review_state=review_state,
        reasons=tuple(reasons),
    )


def summarize_import_request(
    request: ArtifactImportRequest,
    decision: ArtifactImportDecision,
    *,
    expected_payload_hash_sha256: str | None = None,
    signature_verifier: ArtifactSignatureVerifier | None = None,
) -> ArtifactImportSummary:
    """Build a stable summary for monitoring and UI projections."""
    compatibility_check = evaluate_artifact_compatibility_policy(request.manifest)
    signature_check = evaluate_artifact_signature_policy(
        request.manifest,
        trust_store=DEFAULT_ARTIFACT_TRUST_STORE,
        expected_payload_hash_sha256=expected_payload_hash_sha256,
        signature_verifier=signature_verifier,
    )
    feature_lineage_reasons: tuple[str, ...] = ()
    feature_lineage_status = "not_required"
    if request.feature_lineage_required:
        if request.feature_lineage_lock is None:
            feature_lineage_status = "missing"
            feature_lineage_reasons = (
                "feature lineage lock is required for governed artifact upload",
            )
        else:
            derived_reasons: list[str] = []
            if (
                request.feature_lineage_lock.feature_set_version
                != request.manifest.feature_set_version
            ):
                derived_reasons.append(
                    "feature lineage lock feature_set_version must match manifest"
                )
            if (
                request.feature_lineage_lock.transform_set_version
                != request.manifest.transform_set_version
            ):
                derived_reasons.append(
                    "feature lineage lock transform_set_version must match manifest"
                )
            derived_reasons.extend(
                f"feature lineage lock: {reason}"
                for reason in validate_feature_lineage_lock(
                    request.expected_feature_ids,
                    request.feature_lineage_lock,
                )
            )
            feature_lineage_reasons = tuple(derived_reasons)
            feature_lineage_status = "ok" if not feature_lineage_reasons else "invalid"

    transform_whitelist_reasons: tuple[str, ...] = ()
    transform_whitelist_status = "not_required"
    if request.transform_whitelist_required:
        if request.transform_whitelist_lock is None:
            transform_whitelist_status = "missing"
            transform_whitelist_reasons = (
                "transform whitelist lock is required for governed artifact upload",
            )
        else:
            derived_transform_reasons: list[str] = []
            if (
                request.transform_whitelist_lock.transform_set_version
                != request.manifest.transform_set_version
            ):
                derived_transform_reasons.append(
                    "transform whitelist lock transform_set_version must match manifest"
                )
            derived_transform_reasons.extend(
                f"transform whitelist lock: {reason}"
                for reason in validate_transform_whitelist_lock(
                    request.expected_transform_ids,
                    request.transform_whitelist_lock,
                )
            )
            transform_whitelist_reasons = tuple(derived_transform_reasons)
            transform_whitelist_status = (
                "ok" if not transform_whitelist_reasons else "invalid"
            )

    runtime_governance = evaluate_artifact_runtime_governance(
        training_end=request.training_end,
        lifecycle_policy=request.lifecycle_policy,
        governance_reference_date=request.governance_reference_date,
        drift_score_threshold=request.drift_score_threshold,
        observed_drift_score=request.observed_drift_score,
    )

    return ArtifactImportSummary(
        artifact_id=request.manifest.artifact_id,
        correlation_id=request.manifest.correlation_id,
        artifact_kind=request.artifact_kind,
        strategy_classification=request.manifest.strategy_classification,
        source_profile=request.manifest.source_profile,
        lineage_version=request.manifest.lineage_version,
        exported_from=request.manifest.exported_from,
        artifact_schema_version=request.manifest.artifact_schema_version,
        feature_set_version=request.manifest.feature_set_version,
        transform_set_version=request.manifest.transform_set_version,
        compatibility_status=compatibility_check.status,
        compatibility_reasons=compatibility_check.reasons,
        activation_stage=request.manifest.activation_stage,
        health_state=request.manifest.health_state,
        allowed_hook_ids=request.manifest.allowed_hook_ids,
        allowed_action_kinds=request.manifest.allowed_action_kinds,
        allowed_action_units=request.manifest.allowed_action_units,
        signature_envelope=request.manifest.signature_envelope,
        signature_check_status=signature_check.status,
        signature_check_reasons=signature_check.reasons,
        signature_key_id=signature_check.key_id,
        trusted_key_status=signature_check.trusted_key_status,
        conflict_policy=CANONICAL_ARTIFACT_CONFLICT_POLICY,
        registry_policy=CANONICAL_COMPILED_ARTIFACT_REGISTRY_POLICY,
        feature_lineage_required=request.feature_lineage_required,
        feature_lineage_present=request.feature_lineage_lock is not None,
        feature_lineage_status=feature_lineage_status,
        feature_lineage_reasons=feature_lineage_reasons,
        transform_whitelist_required=request.transform_whitelist_required,
        transform_whitelist_present=request.transform_whitelist_lock is not None,
        transform_whitelist_status=transform_whitelist_status,
        transform_whitelist_reasons=transform_whitelist_reasons,
        training_end=request.training_end,
        governance_reference_date=request.governance_reference_date,
        ttl_max_days=(
            None if request.lifecycle_policy is None else request.lifecycle_policy.ttl_max_days
        ),
        ttl_status=runtime_governance.ttl_status.value,
        ttl_reasons=runtime_governance.ttl_reasons,
        drift_score_threshold=request.drift_score_threshold,
        observed_drift_score=request.observed_drift_score,
        drift_status=runtime_governance.drift_status.value,
        drift_reasons=runtime_governance.drift_reasons,
        dataset_ref=request.manifest.dataset_ref,
        clock_ref=request.manifest.clock_ref,
        feature_bridge_ref=request.manifest.feature_bridge_ref,
        parity_diagnostics_ref=request.manifest.parity_diagnostics_ref,
        replay_metrics_ref=request.manifest.replay_metrics_ref,
        replay_dtr_ref=request.manifest.replay_dtr_ref,
        review_export_ref=request.manifest.review_export_ref,
        payload_ref_count=len(request.payload_refs),
        payload_bundle_present=request.payload_bundle is not None,
        accepted=decision.accepted,
        validation_status="accepted" if decision.accepted else "needs_revision",
        normalized_promotion_state=decision.normalized_promotion_state,
        review_state=decision.review_state,
        rejection_reasons=decision.reasons,
    )


def validate_strategy_onboarding_request(
    request: StrategyOnboardingRequest,
    *,
    signature_verifier: ArtifactSignatureVerifier | None = None,
) -> StrategyOnboardingDecision:
    """Validate the minimal governed strategy onboarding flow."""

    reasons: list[str] = []
    import_decision = validate_import_request(
        request.import_request,
        signature_verifier=signature_verifier,
    )
    if not import_decision.accepted:
        reasons.extend(f"import gate: {reason}" for reason in import_decision.reasons)

    if request.automatic_promotion_requested:
        reasons.append("automatic promotion is forbidden")

    if request.bypass_runtime_gates_requested:
        reasons.append("bypassing SHADOW/MICRO_LIVE/LIVE gates is forbidden")

    if request.classification == StrategyClassification.OUT_OF_SCOPE_FOR_V5_3:
        reasons.append("classification is out_of_scope_for_V5_3")

    if request.classification in {
        StrategyClassification.C_CANDIDATE,
        StrategyClassification.D_CANDIDATE,
    }:
        reasons.append("C/D candidates stay documented only until later builds are opened")

    accepted = len(reasons) == 0
    if request.classification == StrategyClassification.BUILD14_ENABLER and accepted:
        normalized_state = PromotionState.REPLAY_ONLY
    else:
        normalized_state = (
            PromotionState.SHADOW_CANDIDATE if accepted else PromotionState.REPLAY_ONLY
        )
    review_state = ReviewState.PENDING if accepted else ReviewState.NEEDS_REVISION

    return StrategyOnboardingDecision(
        accepted=accepted,
        normalized_promotion_state=normalized_state,
        review_state=review_state,
        reasons=tuple(reasons),
    )


__all__ = [
    "DEFAULT_ARTIFACT_COMPATIBILITY_REGISTRY",
    "validate_artifact_manifest",
    "validate_import_request",
    "summarize_import_request",
    "validate_strategy_onboarding_request",
]
