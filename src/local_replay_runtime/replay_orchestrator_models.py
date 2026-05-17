"""Models for governed LOCAL_REPLAY orchestration."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field, model_validator

from interface_contracts import ProfileId, StrategyClassification
from local_replay_runtime.historical_data_gateway import HistoricalReplayDataset
from local_replay_runtime.performance_mode_guard import PerformanceModeGuardReport
from local_replay_runtime.replay_executor import ReplayExecutionResult
from local_replay_runtime.replay_scope_identity import ReplayScopeIdentity
from local_replay_runtime.replay_session_config import ReplayInputKind, ReplaySessionConfig
from local_replay_runtime.run_consistency_guard import RunConsistencyGuardReport


class ReplayOrchestratorRequest(BaseModel, frozen=True):
    """Inputs required to run the governed LOCAL_REPLAY orchestrator."""

    output_dir: Path
    run_id: str = Field(..., min_length=1)
    strategy_id: str = Field(..., min_length=1)
    strategy_version: str = Field(..., min_length=1)
    strategy_classification: StrategyClassification
    lineage_version: str = Field(..., min_length=1)
    performance_mode: str = Field(..., min_length=1)
    input_kind: ReplayInputKind | None = None
    dataset: HistoricalReplayDataset | None = None
    execution_runtime_projection_path: Path | None = None
    profile_scope: ProfileId = ProfileId.COMPLETE
    chunk_count: int = Field(default=1, ge=1)
    chunk_index: int = Field(default=1, ge=1)
    selected_chunk_indices: tuple[int, ...] = ()
    window_start_ms: int | None = Field(default=None, ge=0)
    window_end_ms: int | None = Field(default=None, ge=0)
    rewind_requested: bool = False
    resume: bool = False
    run_all_chunks: bool = False

    @model_validator(mode="after")
    def validate_request(self) -> "ReplayOrchestratorRequest":
        if self.chunk_index > self.chunk_count:
            raise ValueError("ReplayOrchestratorRequest chunk_index must stay <= chunk_count")
        if self.window_start_ms is not None and self.window_end_ms is not None:
            if self.window_end_ms < self.window_start_ms:
                raise ValueError(
                    "ReplayOrchestratorRequest window_end_ms must stay >= window_start_ms"
                )
        if any(index < 1 or index > self.chunk_count for index in self.selected_chunk_indices):
            raise ValueError(
                "ReplayOrchestratorRequest selected_chunk_indices must stay within chunk_count"
            )
        if len(self.selected_chunk_indices) != len(set(self.selected_chunk_indices)):
            raise ValueError(
                "ReplayOrchestratorRequest selected_chunk_indices must stay unique"
            )
        return self


class ReplayChunkArtifact(BaseModel, frozen=True):
    """Audit-ready summary of a chunk export produced in a governed replay session."""

    chunk_index: int = Field(..., ge=1)
    chunk_output_dir: Path
    record_count: int = Field(default=0, ge=0)
    produced_dtr_count: int = Field(default=0, ge=0)
    replay_run_manifest_path: Path
    review_export_path: Path
    replay_dtr_path: Path
    completed: bool = False
    resumed: bool = False


class ReplayChunkSessionSummary(BaseModel, frozen=True):
    """Session-level summary for a governed multi-chunk LOCAL_REPLAY export."""

    run_id: str = Field(..., min_length=1)
    strategy_id: str = Field(..., min_length=1)
    strategy_version: str = Field(..., min_length=1)
    lineage_version: str = Field(..., min_length=1)
    input_kind: ReplayInputKind
    performance_mode: str = Field(..., min_length=1)
    chunk_count: int = Field(..., ge=1)
    selected_chunk_indices: tuple[int, ...] = ()
    window_start_ms: int | None = Field(default=None, ge=0)
    window_end_ms: int | None = Field(default=None, ge=0)
    completed_chunk_indices: tuple[int, ...] = ()
    resumed_chunk_indices: tuple[int, ...] = ()
    aggregate_ready: bool = False
    aggregate_export_dir: Path
    replay_scope_identity: ReplayScopeIdentity | None = None
    chunk_artifacts: tuple[ReplayChunkArtifact, ...] = ()
    summary: str = Field(..., min_length=1)


class ReplayOrchestratorResult(BaseModel, frozen=True):
    """Stable output of the governed LOCAL_REPLAY orchestrator."""

    session_config_path: Path
    session_state_path: Path
    performance_mode_guard_path: Path
    run_consistency_guard_path: Path
    export_result: ReplayExecutionResult
    session_config: ReplaySessionConfig
    performance_mode_guard: PerformanceModeGuardReport
    run_consistency_guard: RunConsistencyGuardReport
    processed_dataset: HistoricalReplayDataset
    chunk_session_path: Path | None = None
    chunk_output_dirs: tuple[Path, ...] = ()
    completed_chunk_indices: tuple[int, ...] = ()
    resumed_chunk_indices: tuple[int, ...] = ()
    resumed: bool = False


__all__ = [
    "ReplayChunkArtifact",
    "ReplayChunkSessionSummary",
    "ReplayOrchestratorRequest",
    "ReplayOrchestratorResult",
]
