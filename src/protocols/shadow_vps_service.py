"""Persistent state and event logging for a long-running VPS Shadow service."""

from __future__ import annotations

from datetime import date
import json
import time
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field, model_validator

from interface_contracts.atomic_io import atomic_write_json


class ShadowVpsServiceStatus(StrEnum):
    """Runtime status for the autonomous VPS Shadow service."""

    IDLE = "idle"
    RUNNING = "running"
    DEGRADED = "degraded"
    STOPPED = "stopped"


class ShadowVpsServiceState(BaseModel):
    """Persisted state for the autonomous VPS Shadow service."""

    service_status: ShadowVpsServiceStatus = ShadowVpsServiceStatus.IDLE
    started_at: float | None = None
    last_heartbeat_at: float | None = None
    loop_count: int = Field(default=0, ge=0)
    success_count: int = Field(default=0, ge=0)
    idle_count: int = Field(default=0, ge=0)
    failure_count: int = Field(default=0, ge=0)
    resumed: bool = False
    last_selected_session_date: str = ""
    last_completed_session_date: str = ""
    last_raw_input_dir_ref: str = ""
    last_websocket_input_dir_ref: str = ""
    last_live_capture_dir_ref: str = ""
    last_live_capture_snapshot_batch_ref: str = ""
    last_live_capture_summary_ref: str = ""
    last_auto_snapshot_dir_ref: str = ""
    last_auto_export_dir_ref: str = ""
    last_export_dir_ref: str = ""
    last_local_replay_evidence_ref: str = ""
    last_shadow_runtime_evidence_ref: str = ""
    last_runtime_evidence_bundle_ref: str = ""
    last_shadow_report_ref: str = ""
    last_shadow_session_summary_ref: str = ""
    last_shadow_session_registry_ref: str = ""
    last_orchestrator_state_ref: str = ""
    last_error: str = ""


class ShadowVpsRawInputConfig(BaseModel, frozen=True):
    """Optional strategy/config metadata attached to a dated raw Shadow input."""

    strategy_id: str = Field(default="strategy-shadow-vps-native", min_length=1)
    strategy_version: str = Field(default="a.v1.0", min_length=1)
    lineage_version: str = Field(default="a.v1.0.r1", min_length=1)
    strategy_classification: str = Field(default="a_variant", min_length=1)
    performance_mode: str = Field(default="research_fast_mode", min_length=1)


class ShadowVpsRawInputSlot(BaseModel, frozen=True):
    """Single dated raw input directory consumed by the VPS Shadow service."""

    session_date: str = Field(..., min_length=10)
    raw_input_dir_ref: str = Field(..., min_length=1)
    dataset_path_ref: str = ""
    snapshot_path_ref: str = ""
    config_path_ref: str = ""
    config: ShadowVpsRawInputConfig = Field(default_factory=ShadowVpsRawInputConfig)

    @model_validator(mode="after")
    def validate_slot(self) -> "ShadowVpsRawInputSlot":
        if bool(self.dataset_path_ref) == bool(self.snapshot_path_ref):
            raise ValueError(
                "ShadowVpsRawInputSlot requires exactly one dataset_path_ref or snapshot_path_ref"
            )
        return self


class ShadowVpsWebsocketInputSlot(BaseModel, frozen=True):
    """Single dated injected websocket directory consumed by the VPS Shadow service."""

    session_date: str = Field(..., min_length=10)
    websocket_input_dir_ref: str = Field(..., min_length=1)
    stream_path_ref: str = Field(..., min_length=1)
    config_path_ref: str = ""
    config: ShadowVpsRawInputConfig = Field(default_factory=ShadowVpsRawInputConfig)


class ShadowLiveWebSocketConfig(BaseModel, frozen=True):
    """Configuration for native live websocket capture on the VPS Shadow service."""

    endpoint: str = Field(
        default="wss://stream.binance.com:9443/ws",
        min_length=1,
    )
    pairs: tuple[str, ...] = Field(default=("BTCUSDT", "ETHUSDT"), min_length=1)
    stream_types: tuple[str, ...] = Field(default=("trade", "depth"), min_length=1)
    connect_timeout_s: float = Field(default=5.0, gt=0.0)
    recv_timeout_s: float = Field(default=1.0, gt=0.0)
    capture_timeout_s: float = Field(default=15.0, gt=0.0)
    capture_frame_limit: int = Field(default=50, ge=1)
    idle_poll_limit: int = Field(default=20, ge=1)
    session_date_override: str = ""
    route_hints_by_pair: dict[str, dict[str, object]] = Field(default_factory=dict)
    config: ShadowVpsRawInputConfig = Field(default_factory=ShadowVpsRawInputConfig)


class ShadowLiveWebSocketCaptureResult(BaseModel, frozen=True):
    """Audit-ready result of a native live websocket capture on the VPS."""

    session_date: str = Field(..., min_length=10)
    live_capture_dir_ref: str = Field(..., min_length=1)
    snapshot_batch_path_ref: str = Field(..., min_length=1)
    summary_path_ref: str = Field(..., min_length=1)
    emitted_message_count: int = Field(default=0, ge=0)
    accepted_message_count: int = Field(default=0, ge=0)
    ignored_message_count: int = Field(default=0, ge=0)
    rejected_message_count: int = Field(default=0, ge=0)
    pair_scope: tuple[str, ...] = ()
    event_types: tuple[str, ...] = ()


class ShadowVpsRuntimeEvidenceBundle(BaseModel, frozen=True):
    """Durable proof chain emitted by the autonomous VPS Shadow service."""

    session_date: str = Field(..., min_length=10)
    acquisition_mode: str = Field(..., min_length=1)
    raw_input_dir_ref: str = ""
    websocket_input_dir_ref: str = ""
    live_capture_dir_ref: str = ""
    live_capture_snapshot_batch_ref: str = ""
    live_capture_summary_ref: str = ""
    live_capture_emitted_message_count: int = Field(default=0, ge=0)
    live_capture_accepted_message_count: int = Field(default=0, ge=0)
    live_capture_ignored_message_count: int = Field(default=0, ge=0)
    live_capture_rejected_message_count: int = Field(default=0, ge=0)
    live_capture_pair_scope: tuple[str, ...] = ()
    live_capture_event_types: tuple[str, ...] = ()
    auto_snapshot_dir_ref: str = ""
    auto_export_dir_ref: str = ""
    export_dir_ref: str = ""
    local_replay_evidence_ref: str = ""
    shadow_runtime_evidence_ref: str = ""
    shadow_summary_ref: str = ""
    shadow_report_ref: str = ""
    shadow_session_summary_ref: str = ""
    shadow_session_registry_ref: str = ""
    orchestrator_state_ref: str = ""
    runtime_data_source: str = "unknown"
    runtime_evidence_summary: str = "No real runtime evidence recorded"
    accepted: bool = False
    consecutive_days: int = Field(default=0, ge=0)
    remaining_days: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_session_date(self) -> "ShadowVpsRuntimeEvidenceBundle":
        date.fromisoformat(self.session_date)
        return self


class ShadowVpsServiceEvent(BaseModel, frozen=True):
    """Single structured event emitted by the autonomous VPS Shadow service."""

    event_type: str = Field(..., min_length=1)
    timestamp: float = Field(default_factory=time.time)
    message: str = Field(..., min_length=1)
    session_date: str = ""
    export_dir_ref: str = ""
    accepted: bool | None = None
    consecutive_days: int | None = Field(default=None, ge=0)
    remaining_days: int | None = Field(default=None, ge=0)
    live_capture_summary_ref: str = ""
    emitted_message_count: int | None = Field(default=None, ge=0)
    accepted_message_count: int | None = Field(default=None, ge=0)
    ignored_message_count: int | None = Field(default=None, ge=0)
    rejected_message_count: int | None = Field(default=None, ge=0)
    pair_scope: tuple[str, ...] = ()
    event_types: tuple[str, ...] = ()
    error: str = ""


class ShadowVpsServiceStore:
    """Persist state and append JSONL events for the autonomous VPS Shadow service."""

    def __init__(
        self,
        state_dir: Path,
        *,
        state_filename: str = "shadow_vps_service.state.json",
        events_filename: str = "shadow_vps_service.events.jsonl",
    ) -> None:
        self._state_dir = state_dir
        self._state_path = state_dir / state_filename
        self._events_path = state_dir / events_filename
        self._state = self._load_or_create()

    @property
    def state(self) -> ShadowVpsServiceState:
        return self._state

    @property
    def state_path(self) -> Path:
        return self._state_path

    @property
    def events_path(self) -> Path:
        return self._events_path

    def _load_or_create(self) -> ShadowVpsServiceState:
        if self._state_path.exists():
            try:
                data = json.loads(self._state_path.read_text(encoding="utf-8"))
                return ShadowVpsServiceState(**data)
            except (json.JSONDecodeError, OSError, ValueError):
                pass
        return ShadowVpsServiceState()

    def persist(self) -> None:
        self._state_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_json(self._state_path, self._state.model_dump(mode="json"))

    def append_event(self, event: ShadowVpsServiceEvent) -> None:
        self._state_dir.mkdir(parents=True, exist_ok=True)
        with self._events_path.open("a", encoding="utf-8") as handle:
            handle.write(event.model_dump_json())
            handle.write("\n")


__all__ = [
    "ShadowVpsServiceStatus",
    "ShadowVpsServiceState",
    "ShadowVpsRawInputConfig",
    "ShadowVpsRawInputSlot",
    "ShadowVpsWebsocketInputSlot",
    "ShadowLiveWebSocketConfig",
    "ShadowLiveWebSocketCaptureResult",
    "ShadowVpsRuntimeEvidenceBundle",
    "ShadowVpsServiceEvent",
    "ShadowVpsServiceStore",
]
