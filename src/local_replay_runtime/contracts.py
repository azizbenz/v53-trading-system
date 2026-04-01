"""Contracts for the LOCAL_REPLAY scaffold."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from interface_contracts import ProfileId, RuntimeMode, StrategyClassification
from local_replay_runtime.artifact_manifest import ArtifactManifest
from local_replay_runtime.enums import ReplayArtifactKind, ReplayLifecycleState


class ReplayDatasetRef(BaseModel, frozen=True):
    """Reference to the dataset chosen for governed replay."""

    dataset_id: str = Field(..., min_length=1)
    source: str = Field(default="local_dataset", min_length=1)
    pair_scope: tuple[str, ...] = ()
    record_count: int = Field(default=0, ge=0)


class ReplayClockRef(BaseModel, frozen=True):
    """Reference to the replay clock configuration."""

    clock_id: str = Field(..., min_length=1)
    mode: str = Field(default="historical", min_length=1)
    start_timestamp_ms: int = Field(..., ge=0)
    end_timestamp_ms: int = Field(..., ge=0)
    tick_count: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_range(self) -> "ReplayClockRef":
        if self.end_timestamp_ms < self.start_timestamp_ms:
            raise ValueError("Replay clock end_timestamp_ms must be >= start_timestamp_ms")
        return self


class LocalReplayRequest(BaseModel, frozen=True):
    """Governed request entering the LOCAL_REPLAY path."""

    correlation_id: str = Field(..., min_length=1)
    profile: ProfileId
    runtime_mode: RuntimeMode = RuntimeMode.LOCAL_REPLAY
    strategy_classification: StrategyClassification
    lineage_version: str = Field(..., min_length=1)
    replay_reason: str = Field(..., min_length=1)
    backtest_profile: str | None = None
    creates_profile_fork: bool = False
    live_mutation_requested: bool = False

    @model_validator(mode="after")
    def validate_request(self) -> "LocalReplayRequest":
        if self.runtime_mode != RuntimeMode.LOCAL_REPLAY:
            raise ValueError("LocalReplayRequest only supports runtime_mode=LOCAL_REPLAY")
        if self.backtest_profile is not None:
            raise ValueError("BACKTEST_PROFILE is forbidden in the unified V5.3")
        if self.creates_profile_fork:
            raise ValueError("Local/VPS profile forks are forbidden")
        if self.live_mutation_requested:
            raise ValueError("LOCAL_REPLAY must not mutate live state")
        return self


class ReplayBundle(BaseModel, frozen=True):
    """Minimal bundle exported from LOCAL_REPLAY."""

    manifest: ArtifactManifest
    artifact_kind: ReplayArtifactKind
    lifecycle_state: ReplayLifecycleState = ReplayLifecycleState.DRAFT
    payload_refs: tuple[str, ...] = ()
    notes: str = ""


class ReplayExecutionPlan(BaseModel, frozen=True):
    """Prepared LOCAL_REPLAY bundle with governed readiness metadata."""

    request: LocalReplayRequest
    bundle: ReplayBundle
    dataset_ref: ReplayDatasetRef | None = None
    clock_ref: ReplayClockRef | None = None
    validation_ready: bool = False
    validation_notes: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_coherence(self) -> "ReplayExecutionPlan":
        if self.request.correlation_id != self.bundle.manifest.correlation_id:
            raise ValueError("Replay plan correlation_id must match bundle manifest correlation_id")
        if bool(self.dataset_ref) != bool(self.clock_ref):
            raise ValueError("ReplayExecutionPlan requires dataset_ref and clock_ref together")
        return self


class LocalReplayRuntimeEvidence(BaseModel, frozen=True):
    """Typed proof that a LOCAL_REPLAY plan is materially useful, not decorative."""

    artifact_id: str = Field(..., min_length=1)
    lineage_version: str = Field(..., min_length=1)
    data_source: Literal["unknown", "recorded_replay"] = "unknown"
    feature_bridge_ready: bool = False
    parity_diagnostics_ready: bool = False
    replay_metrics_ready: bool = False
    replay_dtr_ready: bool = False
    replay_useful_ready: bool = False
    evidence_summary: str = "No local replay runtime evidence recorded"


__all__ = [
    "ReplayDatasetRef",
    "ReplayClockRef",
    "LocalReplayRequest",
    "ReplayBundle",
    "ReplayExecutionPlan",
    "LocalReplayRuntimeEvidence",
]
