"""Contracts for controlled local->VPS artifact import."""

from __future__ import annotations

from pydantic import BaseModel, model_validator

from interface_contracts import PromotionState, ReviewState, RuntimeMode
from local_replay_runtime.artifact_manifest import ArtifactManifest


class ArtifactImportRequest(BaseModel, frozen=True):
    """Request to import a LOCAL_REPLAY artifact into the controlled VPS path."""

    manifest: ArtifactManifest
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


__all__ = [
    "ArtifactImportRequest",
    "ArtifactImportDecision",
]
