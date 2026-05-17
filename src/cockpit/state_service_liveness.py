"""Phase 2.5 adapter - explicit cockpit vs Shadow service liveness."""

from __future__ import annotations

from datetime import UTC, datetime
import os
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from cockpit.runtime_support import CockpitRuntimeSurfaces
from cockpit.state_freshness import (
    OperationalSourceSnapshot,
    json_validator,
    source_stamp,
    worst_status,
)

if TYPE_CHECKING:
    from cockpit.state import CockpitPaths


class ServiceLivenessSnapshot(OperationalSourceSnapshot):
    cockpit_alive: bool = True
    shadow_service_running: bool = False
    control_ready: bool = False
    archive_reader_only: bool = True
    pid_file_present: bool = False
    pid: int | None = None
    pid_is_alive: bool = False
    last_heartbeat_at: str | None = None
    heartbeat_age_seconds: float | None = None
    main_loop_count: int = 0
    last_cycle_duration_ms: float | None = None
    service_status: str = "unknown"
    runtime_mode: str = "unknown"


_CONTROL_READY_STATUSES = {"running", "idle"}


def _read_pid(pid_file: Path) -> int | None:
    try:
        raw = pid_file.read_text(encoding="utf-8").strip()
    except (FileNotFoundError, OSError):
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _pid_is_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _heartbeat_from_runtime(runtime: CockpitRuntimeSurfaces) -> tuple[str | None, float | None]:
    payload = runtime.monitoring_payload
    if payload is not None:
        now = datetime.now(tz=UTC)
        snapshot_time = datetime.fromtimestamp(payload.timestamp_ms / 1000.0, tz=UTC)
        heartbeat_at = snapshot_time.timestamp() - (payload.heartbeat_age_ms / 1000.0)
        heartbeat_dt = datetime.fromtimestamp(heartbeat_at, tz=UTC)
        age_seconds = max((now - heartbeat_dt).total_seconds(), 0.0)
        return heartbeat_dt.isoformat(), age_seconds
    state = runtime.service_state
    last_heartbeat_at = state.last_heartbeat_at if state is not None else None
    if isinstance(last_heartbeat_at, (int, float)) and last_heartbeat_at > 0:
        heartbeat_dt = datetime.fromtimestamp(float(last_heartbeat_at), tz=UTC)
        age_seconds = max((datetime.now(tz=UTC) - heartbeat_dt).total_seconds(), 0.0)
        return heartbeat_dt.isoformat(), age_seconds
    return None, None


def read_service_liveness(
    paths: CockpitPaths,
    *,
    runtime: CockpitRuntimeSurfaces,
) -> ServiceLivenessSnapshot:
    """Build a service liveness proof that does not conflate cockpit and runtime."""

    monitoring_path = paths.service_dir / "shadow_vps_service_monitoring_backend_payload.json"
    state_path = paths.service_state
    payload_stamp = source_stamp(
        path=monitoring_path if monitoring_path.exists() else state_path,
        stale_after_seconds=60.0,
        validator=json_validator,
    )
    state = runtime.service_state
    payload = runtime.monitoring_payload
    pid = _read_pid(paths.pid_file)
    if pid is None and payload is not None:
        pid = payload.process.pid
    pid_alive = _pid_is_alive(pid) if pid is not None else False
    heartbeat_iso, heartbeat_age = _heartbeat_from_runtime(runtime)
    fresh_heartbeat = heartbeat_age is not None and heartbeat_age <= 60.0
    service_status = (
        payload.service_status
        if payload is not None
        else (state.service_status if state is not None else "unknown")
    )
    runtime_mode = (
        payload.runtime_mode.value
        if payload is not None
        else "unknown"
    )
    main_loop_count = (
        payload.loop_count
        if payload is not None
        else (state.loop_count if state is not None else 0)
    )
    control_ready = bool(pid_alive or fresh_heartbeat) and service_status in _CONTROL_READY_STATUSES
    archive_reader_only = not bool(pid_alive or fresh_heartbeat)
    reason_codes = list(payload_stamp["reason_codes"])
    if not pid_alive:
        reason_codes.append("service_pid_not_alive")
    if not fresh_heartbeat:
        reason_codes.append("service_heartbeat_stale")
    if not control_ready:
        reason_codes.append("service_not_control_ready")
    return ServiceLivenessSnapshot(
        source_status=worst_status(
            payload_stamp["source_status"],
            "ok" if (pid_alive or fresh_heartbeat) else "stale",
        ),
        source_file=str(payload_stamp["source_file"]) if payload_stamp["source_file"] else None,
        last_modified_at=payload_stamp["last_modified_at"],
        age_seconds=payload_stamp["age_seconds"],
        reason_codes=tuple(dict.fromkeys(reason_codes)),
        cockpit_alive=True,
        shadow_service_running=bool(pid_alive or fresh_heartbeat),
        control_ready=control_ready,
        archive_reader_only=archive_reader_only,
        pid_file_present=paths.pid_file.is_file(),
        pid=pid,
        pid_is_alive=pid_alive,
        last_heartbeat_at=heartbeat_iso,
        heartbeat_age_seconds=heartbeat_age,
        main_loop_count=main_loop_count,
        last_cycle_duration_ms=None,
        service_status=service_status,
        runtime_mode=runtime_mode,
    )


__all__ = ["ServiceLivenessSnapshot", "read_service_liveness"]
