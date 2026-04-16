"""Shadow VPS service telemetry helpers."""

from __future__ import annotations

from pathlib import Path

from interface_contracts.atomic_io import atomic_write_json
from local_replay_runtime.local_lab_execution_telemetry_artifact import (
    build_local_lab_execution_telemetry_artifact_for_export,
    load_local_lab_execution_telemetry_archive,
)
from protocols import ShadowLiveWebSocketCaptureResult, ShadowVpsWebsocketInputSlot


def _resolve_time_sync_offsets_path(
    *,
    execution_time_sync_offsets_path: Path | None,
    live_capture_result: ShadowLiveWebSocketCaptureResult | None,
) -> Path | None:
    if execution_time_sync_offsets_path is not None and execution_time_sync_offsets_path.is_file():
        return execution_time_sync_offsets_path
    if (
        live_capture_result is not None
        and live_capture_result.time_sync_offsets_path_ref
        and Path(live_capture_result.time_sync_offsets_path_ref).is_file()
    ):
        return Path(live_capture_result.time_sync_offsets_path_ref)
    return None


def _write_execution_telemetry_artifacts(
    *,
    service_dir: Path,
    session_date: str,
    last_run: dict,
    websocket_slot: ShadowVpsWebsocketInputSlot | None,
    live_capture_result: ShadowLiveWebSocketCaptureResult | None,
    execution_time_sync_offsets_path: Path | None,
) -> tuple[Path, Path]:
    archive_path = service_dir / "shadow_vps_service_execution_telemetry.archive.json"
    artifact_path = service_dir / "shadow_vps_service_execution_telemetry.json"
    export_dir_ref = str(last_run.get("export_dir_ref", "")).strip()
    if not export_dir_ref:
        raise ValueError(
            "Shadow VPS execution telemetry requires export_dir_ref after successful orchestration"
        )
    resolved_time_sync_offsets_path = _resolve_time_sync_offsets_path(
        execution_time_sync_offsets_path=execution_time_sync_offsets_path,
        live_capture_result=live_capture_result,
    )
    existing_archive = load_local_lab_execution_telemetry_archive(archive_path)
    updated_archive, artifact = build_local_lab_execution_telemetry_artifact_for_export(
        export_dir=Path(export_dir_ref),
        session_date=session_date,
        websocket_stream_path=(
            Path(websocket_slot.stream_path_ref)
            if websocket_slot is not None and websocket_slot.stream_path_ref
            else None
        ),
        snapshot_batch_path=(
            Path(live_capture_result.snapshot_batch_path_ref)
            if live_capture_result is not None
            and live_capture_result.snapshot_batch_path_ref
            else None
        ),
        time_sync_offsets_path=resolved_time_sync_offsets_path,
        existing_archive=existing_archive,
    )
    atomic_write_json(
        archive_path,
        updated_archive.model_dump(mode="json"),
    )
    atomic_write_json(
        artifact_path,
        artifact.model_dump(mode="json"),
    )
    return archive_path, artifact_path
