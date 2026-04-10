"""Stateful runtime evidence recorder for governed LOCAL_REPLAY sessions."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field

from interface_contracts.atomic_io import atomic_write_json
from local_replay_runtime.contracts import LocalReplayRuntimeEvidence, ReplayExecutionPlan


class LocalReplayEvidenceRecorderConfig(BaseModel, frozen=True):
    """Persistence options for the LOCAL_REPLAY evidence recorder."""

    state_dir: Path | None = None
    persist_state: bool = False
    state_filename: str = "local_replay_runtime_evidence.json"


class LocalReplayEvidenceRecorderState(BaseModel):
    """Persisted state for a LOCAL_REPLAY evidence recording session."""

    artifact_id: str = ""
    lineage_version: str = ""
    last_error: str = ""
    data_source: str = "unknown"
    validation_ready: bool = False
    feature_bridge_ref: str = ""
    parity_diagnostics_ref: str = ""
    replay_metrics_ref: str = ""
    replay_dtr_ref: str = ""
    generated_payload_refs: tuple[str, ...] = ()


class LocalReplayEvidenceRecorder:
    """Track whether a LOCAL_REPLAY run materialized the governed evidence refs."""

    def __init__(
        self,
        *,
        config: LocalReplayEvidenceRecorderConfig | None = None,
    ) -> None:
        self._config = config or LocalReplayEvidenceRecorderConfig()
        self._state_path = (
            self._config.state_dir / self._config.state_filename
            if self._config.state_dir is not None
            else None
        )
        self._state = self._load_or_create()

    def load_execution_plan(self, execution_plan: ReplayExecutionPlan) -> None:
        """Bind the recorder to the governed replay plan that is about to execute."""

        manifest = execution_plan.bundle.manifest
        data_source = (
            "recorded_replay"
            if execution_plan.dataset_ref is not None and execution_plan.clock_ref is not None
            else "unknown"
        )
        self._state = LocalReplayEvidenceRecorderState(
            artifact_id=manifest.artifact_id,
            lineage_version=manifest.lineage_version,
            data_source=data_source,
            validation_ready=execution_plan.validation_ready,
            feature_bridge_ref=manifest.feature_bridge_ref,
            parity_diagnostics_ref=manifest.parity_diagnostics_ref,
            replay_metrics_ref=manifest.replay_metrics_ref,
            replay_dtr_ref=manifest.replay_dtr_ref,
            generated_payload_refs=(),
        )
        self._persist()

    def mark_payload_generated(self, payload_ref: str) -> None:
        """Record that a governed replay artifact ref was materially emitted."""

        if not payload_ref:
            return
        self._state.generated_payload_refs = tuple(
            dict.fromkeys((*self._state.generated_payload_refs, payload_ref))
        )
        self._persist()

    def mark_payloads_generated(self, payload_refs: tuple[str, ...]) -> None:
        """Record a batch of governed replay artifact refs."""

        for payload_ref in payload_refs:
            self.mark_payload_generated(payload_ref)

    def build_evidence(self) -> LocalReplayRuntimeEvidence:
        """Project the current recorder state into the canonical replay evidence contract."""

        payload_refs = set(self._state.generated_payload_refs)
        feature_bridge_ready = bool(self._state.feature_bridge_ref) and (
            self._state.feature_bridge_ref in payload_refs
        )
        parity_diagnostics_ready = bool(self._state.parity_diagnostics_ref) and (
            self._state.parity_diagnostics_ref in payload_refs
        )
        replay_metrics_ready = bool(self._state.replay_metrics_ref) and (
            self._state.replay_metrics_ref in payload_refs
        )
        replay_dtr_ready = bool(self._state.replay_dtr_ref) and (
            self._state.replay_dtr_ref in payload_refs
        )
        replay_useful_ready = (
            self._state.validation_ready
            and self._state.data_source == "recorded_replay"
            and feature_bridge_ready
            and parity_diagnostics_ready
            and replay_metrics_ready
            and replay_dtr_ready
        )
        return LocalReplayRuntimeEvidence(
            artifact_id=self._state.artifact_id or "unknown_artifact",
            lineage_version=self._state.lineage_version or "unknown_lineage",
            data_source=self._state.data_source,  # type: ignore[arg-type]
            feature_bridge_ready=feature_bridge_ready,
            parity_diagnostics_ready=parity_diagnostics_ready,
            replay_metrics_ready=replay_metrics_ready,
            replay_dtr_ready=replay_dtr_ready,
            replay_useful_ready=replay_useful_ready,
            evidence_summary=(
                f"source={self._state.data_source} / "
                f"feature_bridge={'yes' if feature_bridge_ready else 'no'} / "
                f"parity={'yes' if parity_diagnostics_ready else 'no'} / "
                f"metrics={'yes' if replay_metrics_ready else 'no'} / "
                f"replay_dtr={'yes' if replay_dtr_ready else 'no'}"
            ),
        )

    def build_state(self) -> LocalReplayEvidenceRecorderState:
        """Return the current recorder state snapshot."""

        return self._state.model_copy(deep=True)

    def _load_or_create(self) -> LocalReplayEvidenceRecorderState:
        if self._state_path is not None and self._state_path.exists():
            try:
                data = json.loads(self._state_path.read_text(encoding="utf-8"))
                if not isinstance(data, dict):
                    raise ValueError(
                        f"State file root must be a JSON object, got {type(data).__name__}"
                    )
                return LocalReplayEvidenceRecorderState(**data)
            except (json.JSONDecodeError, OSError, ValueError, TypeError) as exc:
                backup = self._state_path.with_suffix(".corrupted")
                try:
                    self._state_path.rename(backup)
                except OSError:
                    pass
                return LocalReplayEvidenceRecorderState(
                    last_error=f"state_file_corrupted:{type(exc).__name__}:{exc}"
                )
        return LocalReplayEvidenceRecorderState()

    def _persist(self) -> None:
        if not self._config.persist_state or self._state_path is None:
            return
        if self._config.state_dir is not None:
            self._config.state_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_json(self._state_path, self._state.model_dump(mode="json"))


__all__ = [
    "LocalReplayEvidenceRecorderConfig",
    "LocalReplayEvidenceRecorderState",
    "LocalReplayEvidenceRecorder",
]
