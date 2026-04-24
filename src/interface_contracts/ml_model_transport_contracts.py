"""Shared typed contracts for governed ML supplementary transport refs."""

from __future__ import annotations

from pydantic import BaseModel, Field

from .domain_types import PromotionState


class MlModelSourceArtifactSummary(BaseModel, frozen=True):
    """Stable sidecar summary for a packaged ML artifact transported to VPS."""

    artifact_hash: str = Field(..., min_length=64, max_length=64)
    schema_version: str = Field(..., min_length=1)
    model_family: str = Field(..., min_length=1)
    calibration_version: str = Field(..., min_length=1)
    feature_hash: str = Field(..., min_length=64, max_length=64)
    dataset_hash: str = Field(..., min_length=64, max_length=64)
    promotion_state: PromotionState
    pair_universe: tuple[str, ...]
    train_window_start_at: str = Field(..., min_length=1)
    train_window_end_at: str = Field(..., min_length=1)
    validation_window_start_at: str = Field(..., min_length=1)
    validation_window_end_at: str = Field(..., min_length=1)
    source_artifact_ref: str = Field(..., min_length=1)
    transport_artifact_ref: str = Field(..., min_length=1)


__all__ = ["MlModelSourceArtifactSummary"]
