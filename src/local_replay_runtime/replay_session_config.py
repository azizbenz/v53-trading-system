"""Typed session configuration for governed LOCAL_REPLAY runs."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from interface_contracts import ProfileId, RuntimeMode

from local_replay_runtime.replay_run_manifest import ReplayRunManifest

ReplayInputKind = Literal[
    "demo_dataset",
    "historical_dataset",
    "historical_snapshot_batch",
]
ReplayDetailLevel = Literal["rich", "summary"]


class ReplaySessionConfig(BaseModel, frozen=True):
    """Canonical session config for a governed local replay execution."""

    run_id: str = Field(..., min_length=1)
    strategy_id: str = Field(..., min_length=1)
    strategy_version: str = Field(..., min_length=1)
    lineage_version: str = Field(..., min_length=1)
    profile_scope: ProfileId
    runtime_mode: RuntimeMode = RuntimeMode.LOCAL_REPLAY
    performance_mode: Literal["shadow_fidelity_mode", "research_fast_mode"]
    input_kind: ReplayInputKind
    input_path: str = Field(..., min_length=1)
    input_record_count: int = Field(..., ge=1)
    chunk_count: int = Field(default=1, ge=1)
    chunk_index: int = Field(default=1, ge=1)
    chunk_window_ms: int = Field(default=0, ge=0)
    rewind_requested: bool = False
    log_detail_level: ReplayDetailLevel
    monitoring_detail_level: ReplayDetailLevel
    ui_live_enabled: bool = False
    expected_same_decisions: bool = True

    @model_validator(mode="after")
    def validate_config(self) -> "ReplaySessionConfig":
        if self.runtime_mode != RuntimeMode.LOCAL_REPLAY:
            raise ValueError("ReplaySessionConfig requires runtime_mode=LOCAL_REPLAY")
        if self.chunk_index > self.chunk_count:
            raise ValueError("ReplaySessionConfig chunk_index must stay <= chunk_count")
        if not self.expected_same_decisions:
            raise ValueError(
                "ReplaySessionConfig must preserve the same business decisions as Shadow"
            )
        if self.ui_live_enabled:
            raise ValueError("LOCAL_REPLAY must not require a live UI")
        if self.performance_mode == "shadow_fidelity_mode":
            if self.log_detail_level != "rich":
                raise ValueError(
                    "shadow_fidelity_mode requires rich log detail level"
                )
            if self.monitoring_detail_level != "rich":
                raise ValueError(
                    "shadow_fidelity_mode requires rich monitoring detail level"
                )
        if self.performance_mode == "research_fast_mode":
            if self.log_detail_level not in {"summary", "rich"}:
                raise ValueError(
                    "research_fast_mode only supports summary or rich logs"
                )
            if self.monitoring_detail_level not in {"summary", "rich"}:
                raise ValueError(
                    "research_fast_mode only supports summary or rich monitoring"
                )
        return self


def build_replay_session_config(
    run_manifest: ReplayRunManifest,
    *,
    input_kind: ReplayInputKind,
    input_path: str,
    input_record_count: int,
    chunk_count: int = 1,
    chunk_index: int = 1,
    rewind_requested: bool = False,
) -> ReplaySessionConfig:
    """Project a session config directly from the governed replay manifest."""

    duration_ms = max(
        run_manifest.end_timestamp_ms - run_manifest.start_timestamp_ms,
        0,
    )
    chunk_window_ms = duration_ms // chunk_count if chunk_count else 0
    detail_level: ReplayDetailLevel = (
        "rich"
        if run_manifest.performance_mode == "shadow_fidelity_mode"
        else "summary"
    )
    return ReplaySessionConfig(
        run_id=run_manifest.run_id,
        strategy_id=run_manifest.strategy_id,
        strategy_version=run_manifest.strategy_version,
        lineage_version=run_manifest.lineage_version,
        profile_scope=run_manifest.profile_scope,
        performance_mode=run_manifest.performance_mode,
        input_kind=input_kind,
        input_path=input_path,
        input_record_count=input_record_count,
        chunk_count=chunk_count,
        chunk_index=chunk_index,
        chunk_window_ms=chunk_window_ms,
        rewind_requested=rewind_requested,
        log_detail_level=detail_level,
        monitoring_detail_level=detail_level,
    )


__all__ = [
    "ReplayInputKind",
    "ReplayDetailLevel",
    "ReplaySessionConfig",
    "build_replay_session_config",
]
