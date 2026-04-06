"""Typed run manifest for governed LOCAL_REPLAY artifact exports."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from interface_contracts import (
    CANONICAL_FEATURE_SET_VERSION,
    CANONICAL_TRANSFORM_SET_VERSION,
    ProfileId,
    RuntimeMode,
    StrategyClassification,
)


class ReplayRunManifest(BaseModel, frozen=True):
    """Minimal typed contract for a governed local replay export run."""

    run_id: str = Field(..., min_length=1)
    strategy_id: str = Field(..., min_length=1)
    strategy_version: str = Field(..., min_length=1)
    strategy_classification: StrategyClassification
    lineage_version: str = Field(..., min_length=1)
    profile_scope: ProfileId
    runtime_mode: RuntimeMode = RuntimeMode.LOCAL_REPLAY
    engine_scope: tuple[str, ...] = Field(..., min_length=1)
    tested_pairs: tuple[str, ...] = Field(..., min_length=1)
    dataset_manifest_id: str = Field(..., min_length=1)
    timeframe_scope: str = Field(..., min_length=1)
    feature_set_version: str = Field(default=CANONICAL_FEATURE_SET_VERSION, min_length=1)
    transform_set_version: str = Field(default=CANONICAL_TRANSFORM_SET_VERSION, min_length=1)
    formula_set_version: str = Field(..., min_length=1)
    scoring_version: str = Field(..., min_length=1)
    regime_version: str = Field(..., min_length=1)
    risk_policy_version: str = Field(..., min_length=1)
    cost_model_version: str = Field(..., min_length=1)
    performance_mode: Literal["shadow_fidelity_mode", "research_fast_mode"]
    artifact_schema_version: str = Field(default="1.0.0", min_length=1)
    artifact_hash: str = Field(..., min_length=1)
    clock_id: str = Field(..., min_length=1)
    start_timestamp_ms: int = Field(..., ge=0)
    end_timestamp_ms: int = Field(..., ge=0)
    tick_count: int = Field(default=0, ge=0)
    record_count: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_manifest(self) -> "ReplayRunManifest":
        if self.runtime_mode != RuntimeMode.LOCAL_REPLAY:
            raise ValueError("ReplayRunManifest requires runtime_mode=LOCAL_REPLAY")
        if self.end_timestamp_ms < self.start_timestamp_ms:
            raise ValueError(
                "ReplayRunManifest end_timestamp_ms must be >= start_timestamp_ms"
            )
        if len(self.engine_scope) != len(set(self.engine_scope)):
            raise ValueError("ReplayRunManifest engine_scope must stay unique")
        if len(self.tested_pairs) != len(set(self.tested_pairs)):
            raise ValueError("ReplayRunManifest tested_pairs must stay unique")
        if not self.lineage_version.startswith(self.strategy_version):
            raise ValueError(
                "ReplayRunManifest lineage_version must extend strategy_version"
            )
        return self


__all__ = ["ReplayRunManifest"]
