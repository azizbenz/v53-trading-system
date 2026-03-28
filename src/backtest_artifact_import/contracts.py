"""Contracts for controlled local->VPS artifact import."""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from interface_contracts import PromotionState, ReviewState, RuntimeMode, StrategyClassification
from local_replay_runtime.artifact_manifest import ArtifactManifest
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


__all__ = [
    "ArtifactImportRequest",
    "ArtifactImportDecision",
    "ArtifactImportSummary",
]
