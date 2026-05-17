"""Persistent state and event logging for a long-running VPS Shadow service."""

from __future__ import annotations

import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from pydantic import BaseModel, Field, model_validator

from interface_contracts.shadow_vps_service_contracts import (
    ShadowVpsCampaignSummary,
    ShadowVpsRuntimeEvidenceBundle,
    ShadowVpsServiceEvent,
    ShadowVpsServiceState,
    ShadowVpsServiceStatus,
)
from interface_contracts.atomic_io import atomic_write_json
from .shadow_live_plan import canonical_shadow_pair_universe


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
    pairs: tuple[str, ...] = Field(
        default=canonical_shadow_pair_universe(),
        min_length=1,
    )
    stream_types: tuple[str, ...] = Field(default=("trade", "depth"), min_length=1)
    connect_timeout_s: float = Field(default=5.0, gt=0.0)
    recv_timeout_s: float = Field(default=1.0, gt=0.0)
    capture_timeout_s: float = Field(default=15.0, gt=0.0)
    capture_frame_limit: int = Field(default=50, ge=1)
    idle_poll_limit: int = Field(default=20, ge=1)
    time_sync_probe_enabled: bool = False
    time_sync_rest_base_url: str = Field(
        default="https://api.binance.com",
        min_length=1,
    )
    time_sync_rest_timeout_s: float = Field(default=5.0, gt=0.0)
    time_sync_sample_count: int = Field(default=3, ge=1, le=32)
    time_sync_sample_pause_s: float = Field(default=0.0, ge=0.0, le=5.0)
    time_sync_rest_quota_max_calls_per_minute: int | None = Field(default=None, ge=1)
    execution_runtime_bootstrap_enabled: bool = False
    execution_runtime_gatekeeper_audit_path_ref: str = ""
    execution_runtime_projection_path_ref: str = ""
    regime_lite_assessment_path_ref: str = ""
    regime_lite_safing_recommendation_path_ref: str = ""
    info_stress_assessment_path_ref: str = ""
    telegram_alert_config_path_ref: str = ""
    telegram_alert_key_path_ref: str = ""
    user_data_stream_enabled: bool = False
    user_data_endpoint: str = Field(
        default="wss://ws-api.binance.com:443/ws-api/v3",
        min_length=1,
    )
    user_data_api_key_env_var: str = Field(default="BINANCE_API_KEY", min_length=1)
    user_data_api_secret_env_var: str = Field(
        default="BINANCE_API_SECRET",
        min_length=1,
    )
    user_data_recv_window_ms: int = Field(default=5000, ge=1, le=60000)
    user_data_capture_timeout_s: float = Field(default=10.0, gt=0.0)
    user_data_idle_poll_limit: int = Field(default=20, ge=1)
    user_data_event_limit: int = Field(default=20, ge=1)
    session_date_override: str = ""
    route_hints_by_pair: dict[str, object] = Field(default_factory=dict)
    config: ShadowVpsRawInputConfig = Field(default_factory=ShadowVpsRawInputConfig)


class ShadowLiveUserDataCaptureSummary(BaseModel, frozen=True):
    """Audit-ready summary of an authenticated Binance user-data websocket capture."""

    session_date: str = Field(..., min_length=10)
    endpoint: str = Field(..., min_length=1)
    summary_path_ref: str = Field(..., min_length=1)
    events_path_ref: str = Field(..., min_length=1)
    authenticated: bool = False
    subscription_id: int | None = Field(default=None, ge=0)
    emitted_event_count: int = Field(default=0, ge=0)
    event_types: tuple[str, ...] = ()


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
    time_sync_offsets_path_ref: str = ""
    time_sync_sample_count: int = Field(default=0, ge=0)
    time_sync_probe_error: str = ""
    user_data_summary_path_ref: str = ""
    user_data_events_path_ref: str = ""
    user_data_authenticated: bool = False
    user_data_subscription_id: int | None = Field(default=None, ge=0)
    user_data_event_count: int = Field(default=0, ge=0)
    user_data_event_types: tuple[str, ...] = ()


class ShadowVpsServiceStore:
    """Persist state and append JSONL events for the autonomous VPS Shadow service."""

    def __init__(
        self,
        state_dir: Path,
        *,
        state_filename: str = "shadow_vps_service.state.json",
        events_filename: str = "shadow_vps_service.events.jsonl",
        events_max_bytes: int = 5 * 1024 * 1024,
        events_backup_count: int = 5,
    ) -> None:
        self._state_dir = state_dir
        self._state_path = state_dir / state_filename
        self._events_path = state_dir / events_filename
        self._event_handler = RotatingFileHandler(
            filename=str(self._events_path),
            maxBytes=events_max_bytes,
            backupCount=events_backup_count,
            encoding="utf-8",
            delay=True,
        )
        self._event_handler.setFormatter(logging.Formatter("%(message)s"))
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
                if not isinstance(data, dict):
                    raise ValueError(f"State file root must be a JSON object, got {type(data).__name__}")
                return ShadowVpsServiceState(**data)
            except (json.JSONDecodeError, OSError, ValueError, TypeError) as exc:
                # BS-122: fail-safe — backup corrupted file before reset
                # Preserves forensic evidence; marks state so caller can alert
                backup = self._state_path.with_suffix(".corrupted")
                try:
                    self._state_path.rename(backup)
                except OSError:
                    pass
                return ShadowVpsServiceState(
                    last_error=f"state_file_corrupted:{type(exc).__name__}:{exc}"
                )
        return ShadowVpsServiceState()

    def persist(self) -> None:
        self._state_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_json(self._state_path, self._state.model_dump(mode="json"))

    def reload(self) -> ShadowVpsServiceState:
        self._state = self._load_or_create()
        return self._state

    def update_state(self, **updates: object) -> ShadowVpsServiceState:
        self._state = self._state.model_copy(update=updates)
        self.persist()
        return self._state

    def append_event(self, event: ShadowVpsServiceEvent) -> None:
        self._state_dir.mkdir(parents=True, exist_ok=True)
        record = logging.LogRecord(
            name="shadow_vps_service.events",
            level=logging.INFO,
            pathname=__file__,
            lineno=0,
            msg=event.model_dump_json(),
            args=(),
            exc_info=None,
        )
        self._event_handler.emit(record)

    def close(self) -> None:
        self._event_handler.close()

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            return


__all__ = [
    "ShadowVpsServiceStatus",
    "ShadowVpsServiceState",
    "ShadowVpsRawInputConfig",
    "ShadowVpsRawInputSlot",
    "ShadowVpsWebsocketInputSlot",
    "ShadowLiveWebSocketConfig",
    "ShadowLiveUserDataCaptureSummary",
    "ShadowLiveWebSocketCaptureResult",
    "ShadowVpsRuntimeEvidenceBundle",
    "ShadowVpsCampaignSummary",
    "ShadowVpsServiceEvent",
    "ShadowVpsServiceStore",
]
