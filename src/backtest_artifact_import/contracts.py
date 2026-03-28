"""Contracts for controlled local->VPS artifact import."""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from interface_contracts import PromotionState, ReviewState, RuntimeMode, StrategyClassification
from local_replay_runtime.artifact_manifest import ArtifactManifest, SHARED_CORE_ID
from local_replay_runtime.enums import ReplayArtifactKind


class ArtifactImportRequest(BaseModel, frozen=True):
    """Request to import a LOCAL_REPLAY artifact into the controlled VPS path."""

    manifest: ArtifactManifest
    artifact_kind: ReplayArtifactKind = ReplayArtifactKind.REVIEW_PACKET
    payload_refs: tuple[str, ...] = ()
    target_runtime_mode: RuntimeMode = RuntimeMode.SHADOW
    requested_promotion_state: PromotionState = PromotionState.REPLAY_ONLY
    review_state: ReviewState = ReviewState.PENDING

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
    lineage_version: str = Field(..., min_length=1)
    exported_from: str = Field(..., min_length=1)
    dataset_ref: str = ""
    clock_ref: str = ""
    review_export_ref: str = ""
    payload_ref_count: int = Field(..., ge=0)
    accepted: bool
    validation_status: str = Field(..., min_length=1)
    normalized_promotion_state: PromotionState
    review_state: ReviewState
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
    "ArtifactImportRequest",
    "ArtifactImportDecision",
    "ArtifactImportSummary",
    "StrategyLineageRecord",
    "StrategyOnboardingRequest",
    "StrategyOnboardingDecision",
]
