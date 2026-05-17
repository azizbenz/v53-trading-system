"""Typed file-queue command plane for Build-17 governed dashboard actions."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from interface_contracts import (
    BinanceCredentialInventoryEntry,
    DashboardArtifactTransferManifest,
    DashboardCommandQueueSnapshot,
    DashboardCommandQueueStatus,
    DashboardGovernedCommandAck,
    DashboardGovernedCommandRequest,
    DashboardGovernedCommandResult,
    DashboardGovernedCommandStatus,
)
from interface_contracts.atomic_io import atomic_write_json
from .dashboard_command_execution_support import (
    _persist_command_result_state,
    execute_dashboard_governed_command,
)

_ModelT = TypeVar("_ModelT", bound=BaseModel)


@dataclass(frozen=True)
class DashboardCommandQueuePaths:
    """Resolved request/ack/result directories for one governed queue root."""

    root: Path
    requests_dir: Path
    acks_dir: Path
    results_dir: Path


@dataclass(frozen=True)
class DashboardGovernedCommandExecutionContext:
    """Bounded execution context used by the VPS-side queue processor."""

    allowed_commands: frozenset
    active_ml_artifact: DashboardArtifactTransferManifest | None = None
    active_regime_detector_artifact: DashboardArtifactTransferManifest | None = None
    shadow_ml_challenger_artifact: DashboardArtifactTransferManifest | None = None
    shadow_regime_detector_challenger_artifact: DashboardArtifactTransferManifest | None = None
    shadow_ml_artifact_comparison_ref: str = ""
    shadow_regime_detector_artifact_comparison_ref: str = ""
    shadow_challenger_verdict_bundle_ref: str = ""
    regime_detector_shadow_audit_bundle_ref: str = ""
    binance_credential_inventory: tuple[BinanceCredentialInventoryEntry, ...] = ()
    binance_credential_inventory_export_ref: str = (
        "exports/binance_credential_inventory.json"
    )
    shadow_vps_service_state_dir: Path | None = None


def resolve_dashboard_command_queue_paths(
    queue_root: str | Path,
) -> DashboardCommandQueuePaths:
    """Resolve the canonical request/ack/result layout under one queue root."""

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


def load_dashboard_command_requests(
    queue_root: str | Path,
) -> tuple[DashboardGovernedCommandRequest, ...]:
    """Load typed governed command requests from the watched queue root."""

    paths = resolve_dashboard_command_queue_paths(queue_root)
    return tuple(
        model
        for _, model in _load_models(
            paths.requests_dir,
            model_type=DashboardGovernedCommandRequest,
            label="request",
        )
    )


def load_dashboard_command_acks(
    queue_root: str | Path,
) -> tuple[DashboardGovernedCommandAck, ...]:
    """Load typed governed command acknowledgements from the queue root."""

    paths = resolve_dashboard_command_queue_paths(queue_root)
    return tuple(
        model
        for _, model in _load_models(
            paths.acks_dir,
            model_type=DashboardGovernedCommandAck,
            label="ack",
        )
    )


def load_dashboard_command_results(
    queue_root: str | Path,
) -> tuple[DashboardGovernedCommandResult, ...]:
    """Load typed governed command results from the queue root."""

    paths = resolve_dashboard_command_queue_paths(queue_root)
    return tuple(
        model
        for _, model in _load_models(
            paths.results_dir,
            model_type=DashboardGovernedCommandResult,
            label="result",
        )
    )


def _write_model(path: Path, model: BaseModel) -> Path:
    atomic_write_json(path, model.model_dump(mode="json"), indent=2)
    return path


def _request_filename(request: DashboardGovernedCommandRequest) -> str:
    return f"{request.timestamp_ms}_{request.request_id}.request.json"


def _ack_filename(ack: DashboardGovernedCommandAck) -> str:
    return f"{ack.timestamp_ms}_{ack.request_id}.ack.json"


def _result_filename(result: DashboardGovernedCommandResult) -> str:
    return f"{result.timestamp_ms}_{result.request_id}.result.json"


def write_dashboard_command_request(
    queue_root: str | Path,
    request: DashboardGovernedCommandRequest,
) -> Path:
    """Persist one governed dashboard request into the watched request directory."""

    paths = resolve_dashboard_command_queue_paths(queue_root)
    paths.requests_dir.mkdir(parents=True, exist_ok=True)
    return _write_model(paths.requests_dir / _request_filename(request), request)


def write_dashboard_command_ack(
    queue_root: str | Path,
    ack: DashboardGovernedCommandAck,
) -> Path:
    """Persist one governed dashboard acknowledgement into the ack directory."""

    paths = resolve_dashboard_command_queue_paths(queue_root)
    paths.acks_dir.mkdir(parents=True, exist_ok=True)
    return _write_model(paths.acks_dir / _ack_filename(ack), ack)


def write_dashboard_command_result(
    queue_root: str | Path,
    result: DashboardGovernedCommandResult,
) -> Path:
    """Persist one governed dashboard result into the result directory."""

    paths = resolve_dashboard_command_queue_paths(queue_root)
    paths.results_dir.mkdir(parents=True, exist_ok=True)
    return _write_model(paths.results_dir / _result_filename(result), result)


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


def process_dashboard_command_queue_once(
    queue_root: str | Path,
    *,
    context: DashboardGovernedCommandExecutionContext,
) -> DashboardCommandQueueSnapshot:
    """Consume pending governed dashboard requests once and emit acks/results."""

    paths = resolve_dashboard_command_queue_paths(queue_root)
    initialize_dashboard_command_queue(paths.root)
    existing_results = load_dashboard_command_results(paths.root)
    handled_idempotency = {result.idempotency_key for result in existing_results}
    handled_request_ids = {result.request_id for result in existing_results}
    existing_ack_ids = {ack.request_id for ack in load_dashboard_command_acks(paths.root)}

    for request in load_dashboard_command_requests(paths.root):
        if request.request_id in handled_request_ids or request.idempotency_key in handled_idempotency:
            continue
        try:
            result = execute_dashboard_governed_command(
                request,
                context=context,
                timestamp_ms=request.timestamp_ms,
            )
        except RuntimeError as exc:
            result = DashboardGovernedCommandResult(
                timestamp_ms=request.timestamp_ms,
                correlation_id=request.correlation_id,
                result_id=f"{request.request_id}.result",
                request_id=request.request_id,
                command_kind=request.command_kind,
                status=DashboardGovernedCommandStatus.FAILED,
                idempotency_key=request.idempotency_key,
                reason_codes=("dashboard.command.execution_exception",),
                detail=str(exc),
                failure_stage="execute_dashboard_governed_command",
            )
        _persist_command_result_state(context, request, result)
        ack_status = (
            DashboardGovernedCommandStatus.REJECTED
            if result.status == DashboardGovernedCommandStatus.REJECTED
            else DashboardGovernedCommandStatus.ACCEPTED
        )
        if request.request_id not in existing_ack_ids:
            ack = DashboardGovernedCommandAck(
                timestamp_ms=request.timestamp_ms,
                correlation_id=request.correlation_id,
                ack_id=f"{request.request_id}.ack",
                request_id=request.request_id,
                command_kind=request.command_kind,
                status=ack_status,
                idempotency_key=request.idempotency_key,
                reason_codes=result.reason_codes,
                detail=result.detail,
            )
            write_dashboard_command_ack(paths.root, ack)
            existing_ack_ids.add(request.request_id)
        write_dashboard_command_result(paths.root, result)
        handled_request_ids.add(request.request_id)
        handled_idempotency.add(request.idempotency_key)
    return build_dashboard_command_queue_snapshot(paths.root)


__all__ = [
    "DashboardCommandQueuePaths",
    "DashboardGovernedCommandExecutionContext",
    "resolve_dashboard_command_queue_paths",
    "initialize_dashboard_command_queue",
    "load_dashboard_command_requests",
    "load_dashboard_command_acks",
    "load_dashboard_command_results",
    "write_dashboard_command_request",
    "write_dashboard_command_ack",
    "write_dashboard_command_result",
    "execute_dashboard_governed_command",
    "build_dashboard_command_queue_snapshot",
    "process_dashboard_command_queue_once",
]
