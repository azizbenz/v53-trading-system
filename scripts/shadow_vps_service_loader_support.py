"""Shadow VPS service loader helpers."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

from protocols import ShadowLiveWebSocketCaptureResult
from shadow_vps_service_projection_support import _read_optional_json


SCRIPT_ROOT = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_ROOT.parent


def _load_script_module(script_name: str, module_name: str) -> ModuleType:
    script_path = REPO_ROOT / "scripts" / script_name
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {script_name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _load_daily_orchestrator_module() -> ModuleType:
    return _load_script_module(
        "run_shadow_daily_orchestrator.py",
        "shadow_vps_service_daily_orchestrator",
    )


def _load_local_replay_export_module() -> ModuleType:
    return _load_script_module(
        "run_local_replay_export.py",
        "shadow_vps_service_local_replay_export",
    )


def _read_last_run(orchestrator_output_dir: Path) -> dict:
    last_run_path = orchestrator_output_dir / "shadow_daily_orchestrator.last_run.json"
    return json.loads(last_run_path.read_text(encoding="utf-8"))


def _read_live_capture_result(
    live_capture_dir: Path | None,
) -> ShadowLiveWebSocketCaptureResult | None:
    if live_capture_dir is None:
        return None
    summary_path = live_capture_dir / "live_websocket_capture_summary.json"
    snapshot_batch_path = live_capture_dir / "live_websocket_snapshot_batch.json"
    if not summary_path.is_file() or not snapshot_batch_path.is_file():
        return None
    try:
        return ShadowLiveWebSocketCaptureResult.model_validate_json(
            summary_path.read_text(encoding="utf-8")
        )
    except (TypeError, ValueError):
        payload = _read_optional_json(str(summary_path))
        try:
            return ShadowLiveWebSocketCaptureResult(
                session_date=live_capture_dir.name,
                live_capture_dir_ref=str(live_capture_dir.resolve()),
                snapshot_batch_path_ref=str(snapshot_batch_path.resolve()),
                summary_path_ref=str(summary_path.resolve()),
                emitted_message_count=int(payload.get("emitted_message_count", 0)),
                accepted_message_count=int(payload.get("accepted_message_count", 0)),
                ignored_message_count=int(payload.get("ignored_message_count", 0)),
                rejected_message_count=int(payload.get("rejected_message_count", 0)),
                pair_scope=tuple(str(value) for value in payload.get("pair_scope", ())),
                event_types=tuple(str(value) for value in payload.get("event_types", ())),
                time_sync_offsets_path_ref=str(
                    payload.get("time_sync_offsets_path_ref", "")
                ),
                time_sync_sample_count=int(payload.get("time_sync_sample_count", 0)),
                time_sync_probe_error=str(payload.get("time_sync_probe_error", "")),
                user_data_summary_path_ref=str(
                    payload.get("user_data_summary_path_ref", "")
                ),
                user_data_events_path_ref=str(
                    payload.get("user_data_events_path_ref", "")
                ),
                user_data_authenticated=bool(
                    payload.get("user_data_authenticated", False)
                ),
                user_data_subscription_id=(
                    int(payload["user_data_subscription_id"])
                    if payload.get("user_data_subscription_id") is not None
                    else None
                ),
                user_data_event_count=int(payload.get("user_data_event_count", 0)),
                user_data_event_types=tuple(
                    str(value) for value in payload.get("user_data_event_types", ())
                ),
            )
        except (TypeError, ValueError):
            return None
