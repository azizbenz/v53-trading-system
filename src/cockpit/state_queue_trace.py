"""Phase 2.5 adapter - queue visibility vs queue consumption proof."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import time
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel

from cockpit.runtime_support import CockpitRuntimeSurfaces
from cockpit.state_freshness import OperationalSourceSnapshot, source_stamp
from interface_contracts import (
    DashboardGovernedCommandAck,
    DashboardGovernedCommandRequest,
    DashboardGovernedCommandResult,
)

if TYPE_CHECKING:
    from cockpit.state import CockpitPaths


ConsumptionStatus = Literal[
    "consumed_by_service",
    "queue_only",
    "not_configured",
    "unknown",
]


class QueueConsumptionTraceSnapshot(OperationalSourceSnapshot):
    queue_status: str = "not_configured"
    pending_count: int = 0
    completed_count: int = 0
    failed_count: int = 0
    last_command_id: str = ""
    last_kind: str = ""
    created_at: str | None = None
    picked_at: str | None = None
    completed_at: str | None = None
    latency_ms: float | None = None
    result_code: str = ""
    consumer_service_pid: int | None = None
    service_last_request_id: str = ""
    service_last_result_status: str = ""
    service_last_command_kind: str = ""
    queue_backlog_stalled: bool = False
    command_queue_snapshot_present: bool = False
    consumption_status: ConsumptionStatus = "unknown"


def _load_latest_model(directory: Path, model_type: type[BaseModel]) -> BaseModel | None:
    if not directory.is_dir():
        return None
    try:
        candidates = sorted(directory.glob("*.json"))
    except OSError:
        return None
    if not candidates:
        return None
    latest = candidates[-1]
    try:
        return model_type.model_validate_json(latest.read_text(encoding="utf-8"))
    except Exception:
        return None


def _iso(timestamp_ms: int | None) -> str | None:
    if not timestamp_ms:
        return None
    return datetime.fromtimestamp(timestamp_ms / 1000.0, tz=UTC).isoformat()


def read_queue_trace(
    paths: CockpitPaths,
    *,
    runtime: CockpitRuntimeSurfaces,
) -> QueueConsumptionTraceSnapshot:
    """Tell the operator whether the queue is merely visible or actually consumed."""

    queue_root = paths.dashboard_command_queue_root
    if queue_root is None:
        return QueueConsumptionTraceSnapshot(
            source_status="missing",
            source_file=None,
            last_modified_at=None,
            age_seconds=None,
            reason_codes=("queue_root_not_configured",),
            queue_status="not_configured",
            consumption_status="not_configured",
        )
    stamp = source_stamp(
        path=queue_root,
        stale_after_seconds=300.0,
        status_if_missing="missing",
    )
    snapshot = runtime.queue_snapshot
    request = _load_latest_model(queue_root / "requests", DashboardGovernedCommandRequest)
    ack = _load_latest_model(queue_root / "acks", DashboardGovernedCommandAck)
    result = _load_latest_model(queue_root / "results", DashboardGovernedCommandResult)
    service_request_id = (
        runtime.monitoring_payload.dashboard_control_last_request_id
        if runtime.monitoring_payload is not None
        else (
            runtime.service_state.dashboard_control_last_request_id
            if runtime.service_state is not None
            else ""
        )
    )
    service_result_status = (
        runtime.monitoring_payload.dashboard_control_last_result_status
        if runtime.monitoring_payload is not None
        else (
            runtime.service_state.dashboard_control_last_result_status
            if runtime.service_state is not None
            else ""
        )
    )
    service_command_kind = (
        runtime.monitoring_payload.dashboard_control_last_command_kind
        if runtime.monitoring_payload is not None
        else (
            runtime.service_state.dashboard_control_last_command_kind
            if runtime.service_state is not None
            else ""
        )
    )
    service_pid = (
        runtime.monitoring_payload.process.pid
        if runtime.monitoring_payload is not None
        else None
    )
    last_request_id = ""
    last_kind = ""
    created_at = None
    picked_at = None
    completed_at = None
    latency_ms = None
    result_code = ""
    if isinstance(request, DashboardGovernedCommandRequest):
        last_request_id = request.request_id
        last_kind = request.command_kind.value
        created_at = _iso(request.timestamp_ms)
    if isinstance(ack, DashboardGovernedCommandAck):
        picked_at = _iso(ack.timestamp_ms)
    if isinstance(result, DashboardGovernedCommandResult):
        last_request_id = result.request_id or last_request_id
        last_kind = result.command_kind.value or last_kind
        completed_at = _iso(result.timestamp_ms)
        result_code = result.status.value
        if isinstance(request, DashboardGovernedCommandRequest):
            latency_ms = max(float(result.timestamp_ms - request.timestamp_ms), 0.0)
    elif isinstance(ack, DashboardGovernedCommandAck) and isinstance(request, DashboardGovernedCommandRequest):
        latency_ms = max(float(ack.timestamp_ms - request.timestamp_ms), 0.0)
    if not snapshot:
        consumption_status: ConsumptionStatus = "not_configured"
    elif isinstance(result, DashboardGovernedCommandResult):
        if service_pid is not None and service_request_id and service_request_id == result.request_id:
            consumption_status = "consumed_by_service"
        else:
            consumption_status = "queue_only"
    elif isinstance(request, DashboardGovernedCommandRequest):
        consumption_status = "unknown"
    else:
        consumption_status = "unknown"
    queue_backlog_stalled = bool(
        snapshot is not None
        and snapshot.pending_request_count > 0
        and isinstance(request, DashboardGovernedCommandRequest)
        and (int(time.time() * 1000) - request.timestamp_ms) > 60_000
        and service_request_id != request.request_id
    )
    if snapshot is None:
        queue_status = "not_configured"
    elif isinstance(result, DashboardGovernedCommandResult):
        queue_status = result.status.value
    elif isinstance(request, DashboardGovernedCommandRequest):
        queue_status = "queue_pending"
    else:
        queue_status = snapshot.queue_status.value
    reason_codes = list(stamp["reason_codes"])
    if consumption_status == "queue_only":
        reason_codes.append("queue_result_without_service_consumption_proof")
    if consumption_status == "not_configured":
        reason_codes.append("queue_snapshot_not_configured")
    if queue_backlog_stalled:
        reason_codes.append("queue_backlog_stalled")
    return QueueConsumptionTraceSnapshot(
        source_status=stamp["source_status"],
        source_file=str(stamp["source_file"]) if stamp["source_file"] else None,
        last_modified_at=stamp["last_modified_at"],
        age_seconds=stamp["age_seconds"],
        reason_codes=tuple(dict.fromkeys(reason_codes)),
        queue_status=queue_status,
        pending_count=snapshot.pending_request_count if snapshot is not None else 0,
        completed_count=snapshot.completed_result_count if snapshot is not None else 0,
        failed_count=snapshot.failed_result_count if snapshot is not None else 0,
        last_command_id=last_request_id,
        last_kind=last_kind,
        created_at=created_at,
        picked_at=picked_at,
        completed_at=completed_at,
        latency_ms=latency_ms,
        result_code=result_code,
        consumer_service_pid=service_pid if consumption_status == "consumed_by_service" else None,
        service_last_request_id=service_request_id,
        service_last_result_status=service_result_status,
        service_last_command_kind=service_command_kind,
        queue_backlog_stalled=queue_backlog_stalled,
        command_queue_snapshot_present=snapshot is not None,
        consumption_status=consumption_status,
    )


__all__ = ["QueueConsumptionTraceSnapshot", "read_queue_trace"]
