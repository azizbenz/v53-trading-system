"""Cockpit-local governed queue helpers with the canonical Build-17 wire format."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from interface_contracts import (
    DashboardCommandQueueSnapshot,
    DashboardCommandQueueStatus,
    DashboardGovernedCommandAck,
    DashboardGovernedCommandRequest,
    DashboardGovernedCommandResult,
    DashboardGovernedCommandStatus,
)
from interface_contracts.atomic_io import atomic_write_json

_ModelT = TypeVar("_ModelT", bound=BaseModel)


@dataclass(frozen=True)
class DashboardCommandQueuePaths:
    """Resolved request/ack/result directories for one governed queue root."""

    root: Path
    requests_dir: Path
    acks_dir: Path
    results_dir: Path


def resolve_dashboard_command_queue_paths(
    queue_root: str | Path,
) -> DashboardCommandQueuePaths:
    """Resolve the canonical queue layout under one queue root."""

    root = Path(queue_root).resolve()
    return DashboardCommandQueuePaths(
        root=root,
        requests_dir=root / "requests",
        acks_dir=root / "acks",
        results_dir=root / "results",
    )


def initialize_dashboard_command_queue(
    queue_root: str | Path,
) -> DashboardCommandQueueSnapshot:
    """Create the canonical queue directories and return their initial snapshot."""

    paths = resolve_dashboard_command_queue_paths(queue_root)
    for directory in (paths.root, paths.requests_dir, paths.acks_dir, paths.results_dir):
        directory.mkdir(parents=True, exist_ok=True)
    return build_dashboard_command_queue_snapshot(paths.root)


def write_dashboard_command_request(
    queue_root: str | Path,
    request: DashboardGovernedCommandRequest,
) -> Path:
    """Persist one governed dashboard request into the watched request directory."""

    paths = resolve_dashboard_command_queue_paths(queue_root)
    paths.requests_dir.mkdir(parents=True, exist_ok=True)
    return _write_model(paths.requests_dir / _request_filename(request), request)


def build_dashboard_command_queue_snapshot(
    queue_root: str | Path,
) -> DashboardCommandQueueSnapshot:
    """Project one queue root into a deterministic queue health snapshot."""

    paths = resolve_dashboard_command_queue_paths(queue_root)
    request_items = (
        _load_models(
            paths.requests_dir,
            model_type=DashboardGovernedCommandRequest,
            label="request",
        )
        if paths.requests_dir.exists()
        else ()
    )
    ack_items = (
        _load_models(
            paths.acks_dir,
            model_type=DashboardGovernedCommandAck,
            label="ack",
        )
        if paths.acks_dir.exists()
        else ()
    )
    result_items = (
        _load_models(
            paths.results_dir,
            model_type=DashboardGovernedCommandResult,
            label="result",
        )
        if paths.results_dir.exists()
        else ()
    )
    request_ids = {item.request_id for _, item in request_items}
    result_ids = {item.request_id for _, item in result_items}
    ambiguous_pending_count = len(request_ids - result_ids)
    rejected_ack_count = sum(
        1 for _, ack in ack_items if ack.status == DashboardGovernedCommandStatus.REJECTED
    )
    failed_result_count = sum(
        1
        for _, result in result_items
        if result.status == DashboardGovernedCommandStatus.FAILED
    )
    writable = all(
        os.access(directory, os.W_OK)
        for directory in (paths.root, paths.requests_dir, paths.acks_dir, paths.results_dir)
        if directory.exists()
    )
    drainable = all(
        directory.exists()
        for directory in (paths.requests_dir, paths.acks_dir, paths.results_dir)
    )
    blocking_reasons: list[str] = []
    if not writable:
        blocking_reasons.append("dashboard.command.queue.not_writable")
    if not drainable:
        blocking_reasons.append("dashboard.command.queue.not_drainable")
    if ambiguous_pending_count:
        blocking_reasons.append("dashboard.command.queue.ambiguous_pending")
    queue_status = (
        DashboardCommandQueueStatus.BLOCKED
        if blocking_reasons
        else (
            DashboardCommandQueueStatus.WARNING
            if failed_result_count or rejected_ack_count
            else DashboardCommandQueueStatus.HEALTHY
        )
    )
    latest_result_path, latest_result = result_items[-1] if result_items else (None, None)
    latest_request = request_items[-1][1] if request_items else None
    return DashboardCommandQueueSnapshot(
        queue_dir_ref=str(paths.root),
        request_dir_ref=str(paths.requests_dir),
        ack_dir_ref=str(paths.acks_dir),
        result_dir_ref=str(paths.results_dir),
        queue_status=queue_status,
        pending_request_count=len(request_items),
        accepted_ack_count=sum(
            1 for _, ack in ack_items if ack.status == DashboardGovernedCommandStatus.ACCEPTED
        ),
        rejected_ack_count=rejected_ack_count,
        completed_result_count=sum(
            1
            for _, result in result_items
            if result.status == DashboardGovernedCommandStatus.COMPLETED
        ),
        failed_result_count=failed_result_count,
        ambiguous_pending_count=ambiguous_pending_count,
        writable=writable,
        drainable=drainable,
        healthy=queue_status == DashboardCommandQueueStatus.HEALTHY,
        last_request_id="" if latest_request is None else latest_request.request_id,
        last_result_status="" if latest_result is None else latest_result.status.value,
        last_result_ref="" if latest_result_path is None else str(latest_result_path),
        blocking_reasons=tuple(blocking_reasons),
    )


def _iter_json_files(directory: Path) -> tuple[Path, ...]:
    return tuple(sorted(directory.glob("*.json")))


def _load_model(path: Path, *, model_type: type[_ModelT], label: str) -> _ModelT:
    try:
        return model_type.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValidationError, ValueError) as exc:
        raise ValueError(f"Invalid dashboard queue {label}: {path.name}") from exc


def _load_models(
    directory: Path,
    *,
    model_type: type[_ModelT],
    label: str,
) -> tuple[tuple[Path, _ModelT], ...]:
    return tuple(
        (path, _load_model(path, model_type=model_type, label=label))
        for path in _iter_json_files(directory)
    )


def _write_model(path: Path, model: BaseModel) -> Path:
    atomic_write_json(path, model.model_dump(mode="json"), indent=2)
    return path


def _request_filename(request: DashboardGovernedCommandRequest) -> str:
    return f"{request.timestamp_ms}_{request.request_id}.request.json"
