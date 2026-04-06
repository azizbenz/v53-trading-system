"""Contracts for controlled local->VPS artifact import."""

from __future__ import annotations

from datetime import date
from enum import StrEnum

from pydantic import BaseModel, Field, model_validator

from interface_contracts import (
    ActionUnit,
    ArtifactActivationStage,
    ArtifactActionKind,
    ArtifactCompatibilityEntry,
    ArtifactCompatibilityStatus,
    ArtifactConflictPolicy,
    ArtifactExportBundle,
    ArtifactHealthState,
    ArtifactLifecyclePolicy,
    ArtifactProofSummary,
    ArtifactSignatureEnvelope,
    CANONICAL_FEATURE_SET_VERSION,
    CANONICAL_TRANSFORM_SET_VERSION,
    CANONICAL_ARTIFACT_CONFLICT_POLICY,
    CANONICAL_COMPILED_ARTIFACT_REGISTRY_POLICY,
    CompiledArtifactRegistryPolicy,
    FeatureLineageLock,
    HookId,
    ProfileId,
    PromotionState,
    ReviewState,
    RuntimeMode,
    StrategyClassification,
    TransformWhitelistId,
    TransformWhitelistLock,
)
from local_replay_runtime.artifact_manifest import ArtifactManifest, SHARED_CORE_ID
from local_replay_runtime.enums import ReplayArtifactKind


class ArtifactSignatureCheckStatus(StrEnum):
    """Import-side signature policy status without claiming cryptographic verification."""

    NOT_PROVIDED = "not_provided"
    TRUST_ELIGIBLE = "trust_eligible"
    TRUST_STORE_UNAVAILABLE = "trust_store_unavailable"
    KEY_ID_UNKNOWN = "key_id_unknown"
    KEY_REVOKED = "key_revoked"
    PAYLOAD_HASH_MISMATCH = "payload_hash_mismatch"


class ArtifactSignatureCheckResult(BaseModel, frozen=True):
    """Bounded import-side result of trust-store and payload-hash policy checks."""

    status: ArtifactSignatureCheckStatus
    accepted: bool
    key_id: str = ""
    trusted_key_status: str = ""
    reasons: tuple[str, ...] = ()


class ArtifactCompatibilityCheckResult(BaseModel, frozen=True):
    """Bounded import-side result of compatibility-registry evaluation."""

    status: ArtifactCompatibilityStatus
    accepted: bool
    reasons: tuple[str, ...] = ()
    matched_entry: ArtifactCompatibilityEntry | None = None


class ArtifactPayloadRefBundle(BaseModel, frozen=True):
    """Canonical typed upload payload bundle for governed LOCAL_REPLAY imports."""

    review_export_ref: str = Field(..., min_length=1)
    feature_bridge_ref: str = Field(..., min_length=1)
    parity_diagnostics_ref: str = Field(..., min_length=1)
    replay_metrics_ref: str = Field(..., min_length=1)
    replay_dtr_ref: str = Field(..., min_length=1)
    supplementary_refs: tuple[str, ...] = ()

    @property
    def payload_refs(self) -> tuple[str, ...]:
        return tuple(
            dict.fromkeys(
                (
                    self.review_export_ref,
                    self.feature_bridge_ref,
                    self.parity_diagnostics_ref,
                    self.replay_metrics_ref,
                    self.replay_dtr_ref,
                    *self.supplementary_refs,
                )
            )
        )


class ArtifactImportRequest(BaseModel, frozen=True):
    """Request to import a LOCAL_REPLAY artifact into the controlled VPS path."""

    manifest: ArtifactManifest
    artifact_kind: ReplayArtifactKind = ReplayArtifactKind.REVIEW_PACKET
    payload_bundle: ArtifactPayloadRefBundle | None = None
    payload_refs: tuple[str, ...] = ()
    feature_lineage_lock: FeatureLineageLock | None = None
    feature_lineage_required: bool = False
    expected_feature_ids: tuple[str, ...] = ()
    transform_whitelist_lock: TransformWhitelistLock | None = None
    transform_whitelist_required: bool = False
    expected_transform_ids: tuple[TransformWhitelistId, ...] = ()
    lifecycle_policy: ArtifactLifecyclePolicy | None = None
    training_end: date | None = None
    governance_reference_date: date | None = None
    drift_score_threshold: float | None = Field(default=None, ge=0.0)
    observed_drift_score: float | None = Field(default=None, ge=0.0)
    proof_summary: ArtifactProofSummary | None = None
    proof_required: bool = False
    target_runtime_mode: RuntimeMode = RuntimeMode.SHADOW
    requested_promotion_state: PromotionState = PromotionState.REPLAY_ONLY
    review_state: ReviewState = ReviewState.PENDING

    @model_validator(mode="before")
    @classmethod
    def normalize_payload_refs(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value
        data = dict(value)
        payload_bundle = data.get("payload_bundle")
        if payload_bundle is None:
            return data
        if not isinstance(payload_bundle, ArtifactPayloadRefBundle):
            payload_bundle = ArtifactPayloadRefBundle.model_validate(payload_bundle)
            data["payload_bundle"] = payload_bundle
        bundle_refs = payload_bundle.payload_refs
        payload_refs = tuple(data.get("payload_refs", ()))
        if not payload_refs:
            data["payload_refs"] = bundle_refs
            return data
        if payload_refs != bundle_refs:
            raise ValueError("ArtifactImportRequest payload_refs must match payload_bundle")
        return data

    @model_validator(mode="after")
    def validate_target(self) -> "ArtifactImportRequest":
        if self.target_runtime_mode == RuntimeMode.LOCAL_REPLAY:
            raise ValueError("Artifact import must target a VPS-side controlled mode")
        return self


class ArtifactImportDecision(BaseModel, frozen=True):
    """Deterministic decision returned by import validators."""

    accepted: bool
    normalized_promotion_state: PromotionState
    review_state: ReviewState
    reasons: tuple[str, ...] = ()


class ArtifactImportSummary(BaseModel, frozen=True):
    """Stable import summary suitable for monitoring/UI projections."""

    artifact_id: str = Field(..., min_length=1)
    correlation_id: str = Field(..., min_length=1)
    artifact_kind: ReplayArtifactKind
    strategy_classification: StrategyClassification
    source_profile: ProfileId
    lineage_version: str = Field(..., min_length=1)
    exported_from: str = Field(..., min_length=1)
    artifact_schema_version: str = Field(default="1.0.0", min_length=1)
    feature_set_version: str = Field(default=CANONICAL_FEATURE_SET_VERSION, min_length=1)
    transform_set_version: str = Field(default=CANONICAL_TRANSFORM_SET_VERSION, min_length=1)
    compatibility_status: ArtifactCompatibilityStatus = ArtifactCompatibilityStatus.SUPPORTED
    compatibility_reasons: tuple[str, ...] = ()
    activation_stage: ArtifactActivationStage = ArtifactActivationStage.REPLAY_ONLY
    health_state: ArtifactHealthState = ArtifactHealthState.ACTIVE
    allowed_hook_ids: tuple[HookId, ...] = ()
    allowed_action_kinds: tuple[ArtifactActionKind, ...] = ()
    allowed_action_units: tuple[ActionUnit, ...] = ()
    signature_envelope: ArtifactSignatureEnvelope | None = None
    signature_check_status: ArtifactSignatureCheckStatus = ArtifactSignatureCheckStatus.NOT_PROVIDED
    signature_check_reasons: tuple[str, ...] = ()
    signature_key_id: str = ""
    trusted_key_status: str = ""
    conflict_policy: ArtifactConflictPolicy = Field(
        default_factory=lambda: CANONICAL_ARTIFACT_CONFLICT_POLICY
    )
    registry_policy: CompiledArtifactRegistryPolicy = Field(
        default_factory=lambda: CANONICAL_COMPILED_ARTIFACT_REGISTRY_POLICY
    )
    feature_lineage_required: bool = False
    feature_lineage_present: bool = False
    feature_lineage_status: str = "not_required"
    feature_lineage_reasons: tuple[str, ...] = ()
    transform_whitelist_required: bool = False
    transform_whitelist_present: bool = False
    transform_whitelist_status: str = "not_required"
    transform_whitelist_reasons: tuple[str, ...] = ()
    training_end: date | None = None
    governance_reference_date: date | None = None
    ttl_max_days: int | None = None
    ttl_status: str = "not_required"
    ttl_reasons: tuple[str, ...] = ()
    drift_score_threshold: float | None = None
    observed_drift_score: float | None = None
    drift_status: str = "not_required"
    drift_reasons: tuple[str, ...] = ()
    dataset_ref: str = ""
    clock_ref: str = ""
    feature_bridge_ref: str = ""
    parity_diagnostics_ref: str = ""
    replay_metrics_ref: str = ""
    replay_dtr_ref: str = ""
    review_export_ref: str = ""
    payload_ref_count: int = Field(..., ge=0)
    payload_bundle_present: bool = False
    accepted: bool
    validation_status: str = Field(..., min_length=1)
    normalized_promotion_state: PromotionState
    review_state: ReviewState
    rejection_reasons: tuple[str, ...] = ()


class ArtifactUploadContext(StrEnum):
    """Origin of a governed artifact upload/dry-run request."""

    LOCAL_LAB = "LOCAL_LAB"
    MANUAL_ADMIN = "MANUAL_ADMIN"


class ArtifactUploadStatus(StrEnum):
    """Normalized upload dry-run outcome aligned with the blueprint vocabulary."""

    REGISTERED = "REGISTERED"
    REJECTED_SCHEMA = "REJECTED_SCHEMA"
    REJECTED_SIGNATURE = "REJECTED_SIGNATURE"
    REJECTED_SCOPE = "REJECTED_SCOPE"
    REJECTED_PROOF = "REJECTED_PROOF"
    DRY_RUN_OK = "DRY_RUN_OK"


class ArtifactUploadRequest(BaseModel, frozen=True):
    """Typed upload dry-run request bridging blueprint payloads to governed import."""

    bundle: ArtifactExportBundle
    manifest: ArtifactManifest
    payload_bundle: ArtifactPayloadRefBundle
    uploaded_by: str = Field(..., min_length=1)
    upload_context: ArtifactUploadContext
    artifact_kind: ReplayArtifactKind = ReplayArtifactKind.REVIEW_PACKET
    dry_run: bool = True
    target_runtime_mode: RuntimeMode = RuntimeMode.SHADOW
    requested_promotion_state: PromotionState = PromotionState.REPLAY_ONLY
    review_state: ReviewState = ReviewState.PENDING

    @model_validator(mode="after")
    def validate_alignment(self) -> "ArtifactUploadRequest":
        if self.bundle.artifact_id != self.manifest.artifact_id:
            raise ValueError("ArtifactUploadRequest bundle.artifact_id must match manifest.artifact_id")
        if self.bundle.feature_set_version != self.manifest.feature_set_version:
            raise ValueError(
                "ArtifactUploadRequest bundle.feature_set_version must match manifest.feature_set_version"
            )
        if self.bundle.transform_set_version != self.manifest.transform_set_version:
            raise ValueError(
                "ArtifactUploadRequest bundle.transform_set_version must match manifest.transform_set_version"
            )
        if (
            self.bundle.feature_lineage_lock.feature_set_version
            != self.manifest.feature_set_version
        ):
            raise ValueError(
                "ArtifactUploadRequest bundle.feature_lineage_lock.feature_set_version must match manifest.feature_set_version"
            )
        if (
            self.bundle.feature_lineage_lock.transform_set_version
            != self.manifest.transform_set_version
        ):
            raise ValueError(
                "ArtifactUploadRequest bundle.feature_lineage_lock.transform_set_version must match manifest.transform_set_version"
            )
        if (
            self.bundle.transform_whitelist_lock.transform_set_version
            != self.manifest.transform_set_version
        ):
            raise ValueError(
                "ArtifactUploadRequest bundle.transform_whitelist_lock.transform_set_version must match manifest.transform_set_version"
            )
        if self.bundle.allowed_hook_ids != self.manifest.allowed_hook_ids:
            raise ValueError(
                "ArtifactUploadRequest bundle.allowed_hook_ids must match manifest.allowed_hook_ids"
            )
        if self.bundle.allowed_action_kinds != self.manifest.allowed_action_kinds:
            raise ValueError(
                "ArtifactUploadRequest bundle.allowed_action_kinds must match manifest.allowed_action_kinds"
            )
        if self.bundle.allowed_action_units != self.manifest.allowed_action_units:
            raise ValueError(
                "ArtifactUploadRequest bundle.allowed_action_units must match manifest.allowed_action_units"
            )
        if self.bundle.distilled_logic_format != self.manifest.distilled_logic_format:
            raise ValueError(
                "ArtifactUploadRequest bundle.distilled_logic_format must match manifest.distilled_logic_format"
            )
        envelope = self.manifest.signature_envelope
        if envelope is None:
            raise ValueError(
                "ArtifactUploadRequest manifest.signature_envelope is required for governed upload dry-run"
            )
        if self.bundle.payload_hash_sha256 != envelope.payload_hash_sha256:
            raise ValueError(
                "ArtifactUploadRequest bundle.payload_hash_sha256 must match manifest.signature_envelope.payload_hash_sha256"
            )
        if self.bundle.public_key_author_sig != envelope.public_key_author_sig:
            raise ValueError(
                "ArtifactUploadRequest bundle.public_key_author_sig must match manifest.signature_envelope.public_key_author_sig"
            )
        return self


class ArtifactUploadDecision(BaseModel, frozen=True):
    """Typed upload dry-run outcome aligned with the blueprint contract surface."""

    artifact_id: str = Field(..., min_length=1)
    accepted: bool
    status: ArtifactUploadStatus
    rejection_reasons: tuple[str, ...] = ()


class StrategyLineageRecord(BaseModel, frozen=True):
    """Minimal lineage record for governed strategy onboarding."""

    proposal_id: str = Field(..., min_length=1)
    classification: StrategyClassification
    strategy_version: str = Field(..., min_length=1)
    lineage_version: str = Field(..., min_length=1)
    source_version: str = Field(..., min_length=1)
    shared_core_id: str = Field(default=SHARED_CORE_ID, min_length=1)
    artifact_id: str = ""
    parent_lineage_version: str = ""

    @model_validator(mode="after")
    def validate_lineage(self) -> "StrategyLineageRecord":
        if self.shared_core_id != SHARED_CORE_ID:
            raise ValueError("Strategy onboarding must stay on the shared V5.3 core")
        if not self.lineage_version.startswith(self.strategy_version):
            raise ValueError("Onboarding lineage_version must extend strategy_version")
        return self


class StrategyOnboardingRequest(BaseModel, frozen=True):
    """Minimal executable onboarding request inside the governed import flow."""

    proposal_id: str = Field(..., min_length=1)
    proposal_name: str = Field(..., min_length=1)
    classification: StrategyClassification
    strategy_version: str = Field(..., min_length=1)
    source_version: str = Field(..., min_length=1)
    economic_hypothesis: str = Field(..., min_length=1)
    portfolio_hypothesis: str = Field(..., min_length=1)
    lineage: StrategyLineageRecord
    import_request: ArtifactImportRequest
    automatic_promotion_requested: bool = False
    bypass_runtime_gates_requested: bool = False

    @model_validator(mode="after")
    def validate_consistency(self) -> "StrategyOnboardingRequest":
        manifest = self.import_request.manifest
        if manifest.strategy_classification != self.classification:
            raise ValueError("Onboarding classification must match artifact classification")
        if manifest.strategy_version != self.strategy_version:
            raise ValueError("Onboarding strategy_version must match artifact strategy_version")
        if manifest.lineage_version != self.lineage.lineage_version:
            raise ValueError("Onboarding lineage_version must match artifact lineage_version")
        if self.lineage.classification != self.classification:
            raise ValueError("Lineage classification must match onboarding classification")
        if self.lineage.strategy_version != self.strategy_version:
            raise ValueError("Lineage strategy_version must match onboarding strategy_version")
        if self.lineage.source_version != self.source_version:
            raise ValueError("Lineage source_version must match onboarding source_version")
        return self


class StrategyOnboardingDecision(BaseModel, frozen=True):
    """Deterministic outcome of the governed strategy onboarding checks."""

    accepted: bool
    normalized_promotion_state: PromotionState
    review_state: ReviewState
    reasons: tuple[str, ...] = ()


__all__ = [
    "ArtifactCompatibilityCheckResult",
    "ArtifactSignatureCheckStatus",
    "ArtifactSignatureCheckResult",
    "ArtifactPayloadRefBundle",
    "ArtifactImportRequest",
    "ArtifactImportDecision",
    "ArtifactImportSummary",
    "ArtifactUploadContext",
    "ArtifactUploadStatus",
    "ArtifactUploadRequest",
    "ArtifactUploadDecision",
    "StrategyLineageRecord",
    "StrategyOnboardingRequest",
    "StrategyOnboardingDecision",
]
