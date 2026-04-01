"""State persistence for governed LOCAL_REPLAY sessions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from interface_contracts.atomic_io import atomic_write_json

from local_replay_runtime.historical_data_gateway import HistoricalReplayDataset
from local_replay_runtime.replay_executor import ReplayExecutionResult
from local_replay_runtime.replay_session_config import ReplaySessionConfig

ReplaySessionLifecycle = Literal[
    "idle",
    "initialized",
    "dataset_ready",
    "export_completed",
]


class ReplaySessionStoreConfig(BaseModel, frozen=True):
    """Persistence options for the governed replay session state."""

    state_dir: Path | None = None
    persist_state: bool = False
    state_filename: str = "replay_session_state.json"


class ReplaySessionState(BaseModel):
    """Persisted lifecycle state for a governed local replay session."""

    run_id: str = ""
    strategy_id: str = ""
    lifecycle_state: ReplaySessionLifecycle = "idle"
    input_kind: str = "demo_dataset"
    input_path: str = ""
    performance_mode: str = "research_fast_mode"
    chunk_count: int = Field(default=1, ge=1)
    chunk_index: int = Field(default=1, ge=1)
    rewind_requested: bool = False
    input_record_count: int = Field(default=0, ge=0)
    pair_scope: tuple[str, ...] = ()
    processed_records: int = Field(default=0, ge=0)
    produced_dtr_count: int = Field(default=0, ge=0)
    output_dir: str = ""
    artifact_paths: tuple[str, ...] = ()
    feature_bridge_ready: bool = False
    parity_diagnostics_ready: bool = False
    replay_metrics_ready: bool = False
    replay_dtr_ready: bool = False
    notes: tuple[str, ...] = ()


class ReplaySessionStateStore:
    """Persist a minimal but audit-ready state for local replay exports."""

    def __init__(
        self,
        *,
        config: ReplaySessionStoreConfig | None = None,
    ) -> None:
        self._config = config or ReplaySessionStoreConfig()
        self._state_path = (
            self._config.state_dir / self._config.state_filename
            if self._config.state_dir is not None
            else None
        )
        self._state = self._load_or_create()

    def initialize(
        self,
        session_config: ReplaySessionConfig,
        *,
        output_dir: Path,
    ) -> None:
        """Start a governed session state before the replay dataset is materialized."""

        self._state = ReplaySessionState(
            run_id=session_config.run_id,
            strategy_id=session_config.strategy_id,
            lifecycle_state="initialized",
            input_kind=session_config.input_kind,
            input_path=session_config.input_path,
            performance_mode=session_config.performance_mode,
            chunk_count=session_config.chunk_count,
            chunk_index=session_config.chunk_index,
            rewind_requested=session_config.rewind_requested,
            input_record_count=session_config.input_record_count,
            output_dir=str(output_dir.resolve()),
            notes=(
                f"log_detail_level={session_config.log_detail_level}",
                f"monitoring_detail_level={session_config.monitoring_detail_level}",
            ),
        )
        self._persist()

    def mark_dataset_ready(self, dataset: HistoricalReplayDataset) -> None:
        """Record that the normalized replay dataset has been prepared."""

        self._state.lifecycle_state = "dataset_ready"
        self._state.pair_scope = dataset.pair_scope
        self._state.processed_records = dataset.record_count
        self._state.notes = tuple(
            dict.fromkeys(
                (
                    *self._state.notes,
                    f"dataset_source={dataset.source}",
                    f"dataset_id={dataset.dataset_id}",
                )
            )
        )
        self._persist()

    def mark_export_completed(self, execution_result: ReplayExecutionResult) -> None:
        """Record that the governed replay artifact export completed successfully."""

        export_result = execution_result.export_result
        self._state.lifecycle_state = "export_completed"
        self._state.produced_dtr_count = execution_result.metrics_summary.total_records
        self._state.artifact_paths = (
            str(export_result.run_manifest_path.resolve()),
            str(export_result.review_export_path.resolve()),
            str(export_result.feature_bridge_path.resolve()),
            str(export_result.parity_diagnostics_path.resolve()),
            str(export_result.replay_metrics_path.resolve()),
            str(export_result.replay_dtr_path.resolve()),
        )
        self._state.feature_bridge_ready = export_result.feature_bridge_path.exists()
        self._state.parity_diagnostics_ready = export_result.parity_diagnostics_path.exists()
        self._state.replay_metrics_ready = export_result.replay_metrics_path.exists()
        self._state.replay_dtr_ready = export_result.replay_dtr_path.exists()
        self._persist()

    def build_state(self) -> ReplaySessionState:
        """Return the current state snapshot."""

        return self._state.model_copy(deep=True)

    def _load_or_create(self) -> ReplaySessionState:
        if self._state_path is not None and self._state_path.exists():
            try:
                data = json.loads(self._state_path.read_text(encoding="utf-8"))
                return ReplaySessionState(**data)
            except (json.JSONDecodeError, OSError, ValueError):
                pass
        return ReplaySessionState()

    def _persist(self) -> None:
        if not self._config.persist_state or self._state_path is None:
            return
        if self._config.state_dir is not None:
            self._config.state_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_json(self._state_path, self._state.model_dump(mode="json"))


__all__ = [
    "ReplaySessionLifecycle",
    "ReplaySessionStoreConfig",
    "ReplaySessionState",
    "ReplaySessionStateStore",
]
