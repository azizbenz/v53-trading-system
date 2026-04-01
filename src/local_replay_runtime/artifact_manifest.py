"""Canonical manifest for LOCAL_REPLAY artifacts."""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from interface_contracts import ProfileId, RuntimeMode, StrategyClassification


SHARED_CORE_ID = "v5_3_shared_core"


class ArtifactManifest(BaseModel, frozen=True):
    """Minimal manifest carried by replay bundles and imports."""

    artifact_id: str = Field(..., min_length=1)
    correlation_id: str = Field(..., min_length=1)
    source_profile: ProfileId
    runtime_mode: RuntimeMode = RuntimeMode.LOCAL_REPLAY
    strategy_classification: StrategyClassification
    strategy_version: str = Field(..., min_length=1)
    lineage_version: str = Field(..., min_length=1)
    shared_core_id: str = Field(default=SHARED_CORE_ID, min_length=1)
    exported_from: str = Field(default="local", min_length=1)
    dataset_ref: str = ""
    clock_ref: str = ""
    feature_bridge_ref: str = ""
    parity_diagnostics_ref: str = ""
    replay_metrics_ref: str = ""
    replay_dtr_ref: str = ""
    diagnostic_ids: tuple[str, ...] = ()
    candidate_ids: tuple[str, ...] = ()
    review_export_ref: str = ""
    backtest_profile: str | None = None
    creates_profile_fork: bool = False
    implicit_promotion_requested: bool = False

    @model_validator(mode="after")
    def validate_unified_plan(self) -> "ArtifactManifest":
        if self.runtime_mode != RuntimeMode.LOCAL_REPLAY:
            raise ValueError("Artifacts must originate from runtime_mode=LOCAL_REPLAY")
        if self.shared_core_id != SHARED_CORE_ID:
            raise ValueError("Artifacts must reference the shared V5.3 core")
        if self.backtest_profile is not None:
            raise ValueError("BACKTEST_PROFILE is forbidden in the unified V5.3")
        if self.creates_profile_fork:
            raise ValueError("Local/VPS profile forks are forbidden")
        if self.implicit_promotion_requested:
            raise ValueError("Artifacts must not request implicit promotion")
        if not self.lineage_version.startswith(self.strategy_version):
            raise ValueError("lineage_version must extend strategy_version")
        if bool(self.dataset_ref) != bool(self.clock_ref):
            raise ValueError("Artifact manifests must declare dataset and clock refs together")
        if len(set(self.diagnostic_ids)) != len(self.diagnostic_ids):
            raise ValueError("Artifact diagnostic refs must be unique")
        if len(set(self.candidate_ids)) != len(self.candidate_ids):
            raise ValueError("Artifact candidate refs must be unique")
        return self


__all__ = [
    "ArtifactManifest",
    "SHARED_CORE_ID",
]
