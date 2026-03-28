"""Contracts for the LOCAL_REPLAY scaffold."""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from interface_contracts import ProfileId, RuntimeMode, StrategyClassification
from local_replay_runtime.artifact_manifest import ArtifactManifest
from local_replay_runtime.enums import ReplayArtifactKind, ReplayLifecycleState


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


__all__ = [
    "LocalReplayRequest",
    "ReplayBundle",
]
