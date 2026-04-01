"""Stateful runtime evidence recorder for governed Build-11 Shadow sessions."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field

from interface_contracts.atomic_io import atomic_write_json
from local_replay_runtime import LocalReplayRuntimeEvidence
from protocols.contracts import ShadowRuntimeEvidence
from protocols.shadow_runtime import build_shadow_runtime_evidence


class ShadowRuntimeEvidenceRecorderConfig(BaseModel, frozen=True):
    """Persistence options for the Build-11 runtime evidence recorder."""

    state_dir: Path | None = None
    persist_state: bool = False
    state_filename: str = "shadow_runtime_evidence.json"


class ShadowRuntimeEvidenceRecorderState(BaseModel):
    """Persisted state of Build-11 runtime evidence collection."""

    runtime_data_source: str = "unknown"
    runtime_event_loop_started_ms: int | None = Field(default=None, ge=0)
    runtime_event_loop_last_ms: int | None = Field(default=None, ge=0)
    runtime_event_loop_tick_count: int = Field(default=0, ge=0)
    runtime_config_loaded: bool = False
    runtime_config_ref: str = ""
    runtime_shadow_dtr_persisted: bool = False
    runtime_shadow_dtr_ref: str = ""


class ShadowRuntimeEvidenceRecorder:
    """Collect Build-11 runtime evidence as a Shadow session actually runs."""

    def __init__(
        self,
        *,
        local_replay_evidence: LocalReplayRuntimeEvidence | None = None,
        config: ShadowRuntimeEvidenceRecorderConfig | None = None,
    ) -> None:
        self._config = config or ShadowRuntimeEvidenceRecorderConfig()
        self._state_path = (
            self._config.state_dir / self._config.state_filename
            if self._config.state_dir is not None
            else None
        )
        self._state = self._load_or_create()
        self._local_replay_evidence = local_replay_evidence

    def attach_local_replay_evidence(
        self,
        local_replay_evidence: LocalReplayRuntimeEvidence,
    ) -> None:
        """Attach typed replay evidence produced by the upstream LOCAL_REPLAY runtime."""

        self._local_replay_evidence = local_replay_evidence

    def mark_runtime_source(self, runtime_data_source: str) -> None:
        """Record the actual Shadow data source used by the runtime."""

        self._state.runtime_data_source = runtime_data_source
        self._persist()

    def record_event_loop_tick(self, timestamp_ms: int) -> None:
        """Record a heartbeat from the running Shadow event loop."""

        if self._state.runtime_event_loop_started_ms is None:
            self._state.runtime_event_loop_started_ms = timestamp_ms
        self._state.runtime_event_loop_last_ms = timestamp_ms
        self._state.runtime_event_loop_tick_count += 1
        self._persist()

    def mark_config_loaded(self, config_ref: str) -> None:
        """Record that the official runtime config was loaded by Shadow."""

        self._state.runtime_config_loaded = True
        self._state.runtime_config_ref = config_ref
        self._persist()

    def mark_shadow_dtr_persisted(self, dtr_ref: str) -> None:
        """Record that a persisted shadow DTR artifact was materially written."""

        self._state.runtime_shadow_dtr_persisted = True
        self._state.runtime_shadow_dtr_ref = dtr_ref
        self._persist()

    def build_evidence(self) -> ShadowRuntimeEvidence:
        """Project the current session state into the canonical Shadow runtime evidence contract."""

        continuous_hours = 0.0
        if (
            self._state.runtime_event_loop_started_ms is not None
            and self._state.runtime_event_loop_last_ms is not None
            and self._state.runtime_event_loop_last_ms >= self._state.runtime_event_loop_started_ms
        ):
            continuous_hours = (
                self._state.runtime_event_loop_last_ms - self._state.runtime_event_loop_started_ms
            ) / 3_600_000.0

        return build_shadow_runtime_evidence(
            local_replay_evidence=self._local_replay_evidence,
            runtime_data_source=self._state.runtime_data_source,
            runtime_event_loop_ready=self._state.runtime_event_loop_tick_count > 0,
            runtime_config_loaded=self._state.runtime_config_loaded,
            runtime_shadow_dtr_persisted=self._state.runtime_shadow_dtr_persisted,
            runtime_continuous_hours=continuous_hours,
        )

    def _load_or_create(self) -> ShadowRuntimeEvidenceRecorderState:
        if self._state_path is not None and self._state_path.exists():
            try:
                data = json.loads(self._state_path.read_text(encoding="utf-8"))
                return ShadowRuntimeEvidenceRecorderState(**data)
            except (json.JSONDecodeError, OSError, ValueError):
                pass
        return ShadowRuntimeEvidenceRecorderState()

    def _persist(self) -> None:
        if not self._config.persist_state or self._state_path is None:
            return
        if self._config.state_dir is not None:
            self._config.state_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_json(self._state_path, self._state.model_dump(mode="json"))


__all__ = [
    "ShadowRuntimeEvidenceRecorderConfig",
    "ShadowRuntimeEvidenceRecorderState",
    "ShadowRuntimeEvidenceRecorder",
]
