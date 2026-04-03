#!/usr/bin/env python3
"""Run the autonomous long-running VPS Shadow service."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
from datetime import date
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from protocols import (  # noqa: E402
    ShadowVpsCampaignSummary,
    ShadowLiveWebSocketConfig,
    ShadowLiveWebSocketCaptureResult,
    ShadowDailyOrchestrator,
    ShadowVpsServiceEvent,
    ShadowVpsRawInputConfig,
    ShadowVpsRawInputSlot,
    ShadowVpsRuntimeEvidenceBundle,
    ShadowVpsWebsocketInputSlot,
    ShadowVpsServiceStatus,
    ShadowVpsServiceStore,
    build_snapshot_batch_from_injected_websocket_stream,
    capture_live_websocket_snapshot_batch,
)


def _configure_stdio() -> None:
    stdout = getattr(sys, "stdout", None)
    if stdout is not None and hasattr(stdout, "reconfigure"):
        stdout.reconfigure(encoding="utf-8", errors="replace")
    stderr = getattr(sys, "stderr", None)
    if stderr is not None and hasattr(stderr, "reconfigure"):
        stderr.reconfigure(encoding="utf-8", errors="replace")


def _load_daily_orchestrator_module():
    script_path = REPO_ROOT / "scripts" / "run_shadow_daily_orchestrator.py"
    module_name = "shadow_vps_service_daily_orchestrator"
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load run_shadow_daily_orchestrator.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _load_local_replay_export_module():
    script_path = REPO_ROOT / "scripts" / "run_local_replay_export.py"
    module_name = "shadow_vps_service_local_replay_export"
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load run_local_replay_export.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _read_last_run(orchestrator_output_dir: Path) -> dict:
    last_run_path = orchestrator_output_dir / "shadow_daily_orchestrator.last_run.json"
    return json.loads(last_run_path.read_text(encoding="utf-8"))


def _read_optional_json(path_ref: str) -> dict:
    if not path_ref:
        return {}
    try:
        return json.loads(Path(path_ref).read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {}


def _read_runtime_evidence_bundle(
    bundle_path_ref: str,
) -> ShadowVpsRuntimeEvidenceBundle | None:
    if not bundle_path_ref:
        return None
    bundle_path = Path(bundle_path_ref)
    if not bundle_path.is_file():
        return None
    try:
        return ShadowVpsRuntimeEvidenceBundle.model_validate_json(
            bundle_path.read_text(encoding="utf-8")
        )
    except (OSError, ValueError, TypeError):
        return None


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


def _read_raw_input_config(config_path: Path | None) -> ShadowVpsRawInputConfig:
    if config_path is None or not config_path.is_file():
        return ShadowVpsRawInputConfig()
    return ShadowVpsRawInputConfig.model_validate_json(
        config_path.read_text(encoding="utf-8-sig")
    )


def _read_live_websocket_config(config_path: Path) -> ShadowLiveWebSocketConfig:
    if not config_path.is_file():
        raise FileNotFoundError(f"Missing live websocket config: {config_path}")
    return ShadowLiveWebSocketConfig.model_validate_json(
        config_path.read_text(encoding="utf-8-sig")
    )


def _discover_raw_input_slot(raw_inputs_root: Path, session_date: str) -> ShadowVpsRawInputSlot:
    raw_input_dir = raw_inputs_root / session_date
    if not raw_input_dir.is_dir():
        raise FileNotFoundError(
            f"Missing raw input directory for session_date={session_date}: {raw_input_dir}"
        )
    dataset_candidates = (
        "replay_dataset.json",
        "replay_dataset.jsonl",
        "replay_dataset.csv",
        "dataset.json",
        "dataset.jsonl",
        "dataset.csv",
    )
    snapshot_candidates = (
        "snapshot_batch.json",
        "snapshot_batch.jsonl",
        "snapshot_batch.csv",
        "snapshots.json",
        "snapshots.jsonl",
        "snapshots.csv",
    )
    dataset_path = next(
        (raw_input_dir / candidate for candidate in dataset_candidates if (raw_input_dir / candidate).is_file()),
        None,
    )
    snapshot_path = next(
        (raw_input_dir / candidate for candidate in snapshot_candidates if (raw_input_dir / candidate).is_file()),
        None,
    )
    config_path = raw_input_dir / "shadow_input_config.json"
    return ShadowVpsRawInputSlot(
        session_date=session_date,
        raw_input_dir_ref=str(raw_input_dir.resolve()),
        dataset_path_ref=str(dataset_path.resolve()) if dataset_path is not None else "",
        snapshot_path_ref=str(snapshot_path.resolve()) if snapshot_path is not None else "",
        config_path_ref=str(config_path.resolve()) if config_path.is_file() else "",
        config=_read_raw_input_config(config_path if config_path.is_file() else None),
    )


def _select_next_raw_input_slot(
    raw_inputs_root: Path,
    orchestrator: ShadowDailyOrchestrator,
) -> ShadowVpsRawInputSlot | None:
    if not raw_inputs_root.exists():
        return None
    completed_dates = set(orchestrator.completed_session_dates())
    dated_dirs = sorted(
        item
        for item in raw_inputs_root.iterdir()
        if item.is_dir()
    )
    for item in dated_dirs:
        try:
            session_date = date.fromisoformat(item.name).isoformat()
        except ValueError:
            continue
        if session_date in completed_dates:
            continue
        return _discover_raw_input_slot(raw_inputs_root, session_date)
    return None


def _discover_websocket_input_slot(
    websocket_streams_root: Path,
    session_date: str,
) -> ShadowVpsWebsocketInputSlot:
    websocket_input_dir = websocket_streams_root / session_date
    if not websocket_input_dir.is_dir():
        raise FileNotFoundError(
            f"Missing websocket input directory for session_date={session_date}: "
            f"{websocket_input_dir}"
        )
    stream_candidates = (
        "websocket_stream.jsonl",
        "websocket_stream.json",
        "websocket_frames.jsonl",
        "websocket_frames.json",
    )
    stream_path = next(
        (
            websocket_input_dir / candidate
            for candidate in stream_candidates
            if (websocket_input_dir / candidate).is_file()
        ),
        None,
    )
    if stream_path is None:
        raise FileNotFoundError(
            f"Missing websocket stream file in {websocket_input_dir}"
        )
    config_path = websocket_input_dir / "shadow_input_config.json"
    return ShadowVpsWebsocketInputSlot(
        session_date=session_date,
        websocket_input_dir_ref=str(websocket_input_dir.resolve()),
        stream_path_ref=str(stream_path.resolve()),
        config_path_ref=str(config_path.resolve()) if config_path.is_file() else "",
        config=_read_raw_input_config(config_path if config_path.is_file() else None),
    )


def _select_next_websocket_input_slot(
    websocket_streams_root: Path,
    orchestrator: ShadowDailyOrchestrator,
) -> ShadowVpsWebsocketInputSlot | None:
    if not websocket_streams_root.exists():
        return None
    completed_dates = set(orchestrator.completed_session_dates())
    dated_dirs = sorted(item for item in websocket_streams_root.iterdir() if item.is_dir())
    for item in dated_dirs:
        try:
            session_date = date.fromisoformat(item.name).isoformat()
        except ValueError:
            continue
        if session_date in completed_dates:
            continue
        return _discover_websocket_input_slot(websocket_streams_root, session_date)
    return None


def _ensure_auto_export_from_raw_slot(
    raw_slot: ShadowVpsRawInputSlot,
    *,
    auto_exports_root: Path,
) -> Path:
    auto_export_dir = auto_exports_root / raw_slot.session_date
    if (
        (auto_export_dir / "replay_run_manifest.json").is_file()
        and (auto_export_dir / "review_export.md").is_file()
        and (auto_export_dir / "feature_bridge.json").is_file()
        and (auto_export_dir / "parity_diagnostics.json").is_file()
        and (auto_export_dir / "replay_metrics.json").is_file()
        and (
            (auto_export_dir / "replay_dtr.jsonl").is_file()
            or (auto_export_dir / "replay_dtr.json").is_file()
        )
    ):
        return auto_export_dir

    auto_export_dir.mkdir(parents=True, exist_ok=True)
    export_launcher = _load_local_replay_export_module()
    argv = [
        "--output-dir",
        str(auto_export_dir),
        "--run-id",
        f"run-shadow-vps-native-{raw_slot.session_date}",
        "--strategy-id",
        raw_slot.config.strategy_id,
        "--strategy-classification",
        raw_slot.config.strategy_classification,
        "--strategy-version",
        raw_slot.config.strategy_version,
        "--lineage-version",
        raw_slot.config.lineage_version,
        "--performance-mode",
        raw_slot.config.performance_mode,
    ]
    if raw_slot.dataset_path_ref:
        argv.extend(["--dataset-path", raw_slot.dataset_path_ref])
    if raw_slot.snapshot_path_ref:
        argv.extend(["--snapshot-path", raw_slot.snapshot_path_ref])
    exit_code = export_launcher.main(argv)
    if exit_code != 0:
        raise RuntimeError(
            f"Local replay export launcher returned non-zero exit code {exit_code}"
        )
    return auto_export_dir


def _ensure_auto_export_from_websocket_slot(
    websocket_slot: ShadowVpsWebsocketInputSlot,
    *,
    auto_snapshots_root: Path,
    auto_exports_root: Path,
) -> tuple[Path, Path]:
    auto_snapshot_dir = auto_snapshots_root / websocket_slot.session_date
    auto_snapshot_path = auto_snapshot_dir / "websocket_snapshot_batch.json"
    auto_summary_path = auto_snapshot_dir / "websocket_snapshot_ingest.json"
    if not auto_snapshot_path.is_file() or not auto_summary_path.is_file():
        auto_snapshot_dir.mkdir(parents=True, exist_ok=True)
        build_snapshot_batch_from_injected_websocket_stream(
            Path(websocket_slot.stream_path_ref),
            snapshot_batch_path=auto_snapshot_path,
            summary_path=auto_summary_path,
        )

    auto_export_dir = auto_exports_root / websocket_slot.session_date
    if (
        (auto_export_dir / "replay_run_manifest.json").is_file()
        and (auto_export_dir / "review_export.md").is_file()
        and (auto_export_dir / "feature_bridge.json").is_file()
        and (auto_export_dir / "parity_diagnostics.json").is_file()
        and (auto_export_dir / "replay_metrics.json").is_file()
        and (
            (auto_export_dir / "replay_dtr.jsonl").is_file()
            or (auto_export_dir / "replay_dtr.json").is_file()
        )
    ):
        return auto_snapshot_dir, auto_export_dir

    auto_export_dir.mkdir(parents=True, exist_ok=True)
    export_launcher = _load_local_replay_export_module()
    argv = [
        "--output-dir",
        str(auto_export_dir),
        "--run-id",
        f"run-shadow-vps-websocket-{websocket_slot.session_date}",
        "--strategy-id",
        websocket_slot.config.strategy_id,
        "--strategy-classification",
        websocket_slot.config.strategy_classification,
        "--strategy-version",
        websocket_slot.config.strategy_version,
        "--lineage-version",
        websocket_slot.config.lineage_version,
        "--performance-mode",
        websocket_slot.config.performance_mode,
        "--snapshot-path",
        str(auto_snapshot_path),
    ]
    exit_code = export_launcher.main(argv)
    if exit_code != 0:
        raise RuntimeError(
            f"Local replay export launcher returned non-zero exit code {exit_code}"
        )
    return auto_snapshot_dir, auto_export_dir


def _ensure_auto_export_from_live_websocket(
    live_config: ShadowLiveWebSocketConfig,
    *,
    live_captures_root: Path,
    auto_exports_root: Path,
) -> tuple[Path, Path]:
    session_date = live_config.session_date_override or date.today().isoformat()
    live_capture_dir = live_captures_root / session_date
    capture_summary_path = live_capture_dir / "live_websocket_capture_summary.json"
    snapshot_batch_path = live_capture_dir / "live_websocket_snapshot_batch.json"
    if not capture_summary_path.is_file() or not snapshot_batch_path.is_file():
        capture_live_websocket_snapshot_batch(
            live_config,
            output_dir=live_capture_dir,
        )

    auto_export_dir = auto_exports_root / session_date
    if (
        (auto_export_dir / "replay_run_manifest.json").is_file()
        and (auto_export_dir / "review_export.md").is_file()
        and (auto_export_dir / "feature_bridge.json").is_file()
        and (auto_export_dir / "parity_diagnostics.json").is_file()
        and (auto_export_dir / "replay_metrics.json").is_file()
        and (
            (auto_export_dir / "replay_dtr.jsonl").is_file()
            or (auto_export_dir / "replay_dtr.json").is_file()
        )
    ):
        return live_capture_dir, auto_export_dir

    auto_export_dir.mkdir(parents=True, exist_ok=True)
    export_launcher = _load_local_replay_export_module()
    argv = [
        "--output-dir",
        str(auto_export_dir),
        "--run-id",
        f"run-shadow-vps-live-{session_date}",
        "--strategy-id",
        live_config.config.strategy_id,
        "--strategy-classification",
        live_config.config.strategy_classification,
        "--strategy-version",
        live_config.config.strategy_version,
        "--lineage-version",
        live_config.config.lineage_version,
        "--performance-mode",
        live_config.config.performance_mode,
        "--snapshot-path",
        str(snapshot_batch_path),
    ]
    exit_code = export_launcher.main(argv)
    if exit_code != 0:
        raise RuntimeError(
            f"Local replay export launcher returned non-zero exit code {exit_code}"
        )
    return live_capture_dir, auto_export_dir


def _resolve_acquisition_mode(
    *,
    raw_slot: ShadowVpsRawInputSlot | None,
    websocket_slot: ShadowVpsWebsocketInputSlot | None,
    live_capture_dir: Path | None,
    export_dir_ref: str,
) -> str:
    if live_capture_dir is not None:
        return "native_live_websocket_auto_export"
    if websocket_slot is not None:
        return "websocket_stream_auto_export"
    if raw_slot is not None:
        return "raw_input_auto_export"
    if export_dir_ref:
        return "dated_export"
    return "demo"


def _write_runtime_evidence_bundle(
    *,
    service_dir: Path,
    session_date: str,
    raw_slot: ShadowVpsRawInputSlot | None,
    websocket_slot: ShadowVpsWebsocketInputSlot | None,
    live_capture_result: ShadowLiveWebSocketCaptureResult | None,
    auto_snapshot_dir: Path | None,
    auto_export_dir: Path | None,
    last_run: dict,
) -> Path:
    bundle_dir = service_dir / "runtime_evidence"
    bundle_dir.mkdir(parents=True, exist_ok=True)
    bundle_path = bundle_dir / f"{session_date}.shadow_vps_runtime_evidence.json"
    runtime_evidence_payload = _read_optional_json(
        str(last_run.get("shadow_runtime_evidence_ref", ""))
    )
    bundle = ShadowVpsRuntimeEvidenceBundle(
        session_date=session_date,
        acquisition_mode=_resolve_acquisition_mode(
            raw_slot=raw_slot,
            websocket_slot=websocket_slot,
            live_capture_dir=Path(live_capture_result.live_capture_dir_ref)
            if live_capture_result is not None
            else None,
            export_dir_ref=str(last_run.get("export_dir_ref", "")),
        ),
        raw_input_dir_ref=raw_slot.raw_input_dir_ref if raw_slot is not None else "",
        websocket_input_dir_ref=(
            websocket_slot.websocket_input_dir_ref if websocket_slot is not None else ""
        ),
        live_capture_dir_ref=(
            live_capture_result.live_capture_dir_ref if live_capture_result is not None else ""
        ),
        live_capture_snapshot_batch_ref=(
            live_capture_result.snapshot_batch_path_ref if live_capture_result is not None else ""
        ),
        live_capture_summary_ref=(
            live_capture_result.summary_path_ref if live_capture_result is not None else ""
        ),
        live_capture_emitted_message_count=(
            live_capture_result.emitted_message_count if live_capture_result is not None else 0
        ),
        live_capture_accepted_message_count=(
            live_capture_result.accepted_message_count if live_capture_result is not None else 0
        ),
        live_capture_ignored_message_count=(
            live_capture_result.ignored_message_count if live_capture_result is not None else 0
        ),
        live_capture_rejected_message_count=(
            live_capture_result.rejected_message_count if live_capture_result is not None else 0
        ),
        live_capture_pair_scope=(
            live_capture_result.pair_scope if live_capture_result is not None else ()
        ),
        live_capture_event_types=(
            live_capture_result.event_types if live_capture_result is not None else ()
        ),
        live_user_data_summary_ref=(
            live_capture_result.user_data_summary_path_ref
            if live_capture_result is not None
            else ""
        ),
        live_user_data_events_ref=(
            live_capture_result.user_data_events_path_ref
            if live_capture_result is not None
            else ""
        ),
        live_user_data_authenticated=(
            live_capture_result.user_data_authenticated
            if live_capture_result is not None
            else False
        ),
        live_user_data_subscription_id=(
            live_capture_result.user_data_subscription_id
            if live_capture_result is not None
            else None
        ),
        live_user_data_event_count=(
            live_capture_result.user_data_event_count if live_capture_result is not None else 0
        ),
        live_user_data_event_types=(
            live_capture_result.user_data_event_types if live_capture_result is not None else ()
        ),
        auto_snapshot_dir_ref=str(auto_snapshot_dir.resolve()) if auto_snapshot_dir is not None else "",
        auto_export_dir_ref=str(auto_export_dir.resolve()) if auto_export_dir is not None else "",
        export_dir_ref=str(last_run.get("export_dir_ref", "")),
        local_replay_evidence_ref=str(last_run.get("local_replay_evidence_ref", "")),
        shadow_runtime_evidence_ref=str(last_run.get("shadow_runtime_evidence_ref", "")),
        shadow_summary_ref=str(last_run.get("shadow_summary_ref", "")),
        shadow_report_ref=str(last_run.get("shadow_report_ref", "")),
        shadow_session_summary_ref=str(last_run.get("shadow_session_summary_ref", "")),
        shadow_session_registry_ref=str(last_run.get("shadow_session_registry_ref", "")),
        orchestrator_state_ref=str(last_run.get("state_path", "")),
        runtime_data_source=str(runtime_evidence_payload.get("data_source", "unknown")),
        runtime_evidence_summary=str(
            runtime_evidence_payload.get(
                "evidence_summary",
                "No real runtime evidence recorded",
            )
        ),
        accepted=bool(last_run.get("accepted", False)),
        consecutive_days=int(last_run.get("consecutive_days", 0)),
        remaining_days=int(last_run.get("remaining_days", 0)),
    )
    bundle_path.write_text(bundle.model_dump_json(indent=2), encoding="utf-8")
    return bundle_path


def _write_campaign_summary(
    *,
    service_dir: Path,
    state,
    bundle: ShadowVpsRuntimeEvidenceBundle | None,
) -> Path:
    summary_path = service_dir / "shadow_vps_service.campaign_summary.json"
    summary = ShadowVpsCampaignSummary(
        service_status=state.service_status,
        loop_count=state.loop_count,
        success_count=state.success_count,
        idle_count=state.idle_count,
        failure_count=state.failure_count,
        resumed=state.resumed,
        last_selected_session_date=state.last_selected_session_date,
        last_completed_session_date=state.last_completed_session_date,
        acquisition_mode=bundle.acquisition_mode if bundle is not None else "",
        accepted=bundle.accepted if bundle is not None else False,
        consecutive_days=bundle.consecutive_days if bundle is not None else 0,
        remaining_days=bundle.remaining_days if bundle is not None else 0,
        promotion_gate_passed=(
            bundle.accepted and bundle.remaining_days == 0 if bundle is not None else False
        ),
        runtime_data_source=bundle.runtime_data_source if bundle is not None else "unknown",
        runtime_evidence_summary=(
            bundle.runtime_evidence_summary
            if bundle is not None
            else "No real runtime evidence recorded"
        ),
        live_capture_summary_ref=(
            bundle.live_capture_summary_ref if bundle is not None else ""
        ),
        live_capture_emitted_message_count=(
            bundle.live_capture_emitted_message_count if bundle is not None else 0
        ),
        live_capture_accepted_message_count=(
            bundle.live_capture_accepted_message_count if bundle is not None else 0
        ),
        live_capture_ignored_message_count=(
            bundle.live_capture_ignored_message_count if bundle is not None else 0
        ),
        live_capture_rejected_message_count=(
            bundle.live_capture_rejected_message_count if bundle is not None else 0
        ),
        live_capture_pair_scope=(
            bundle.live_capture_pair_scope if bundle is not None else ()
        ),
        live_capture_event_types=(
            bundle.live_capture_event_types if bundle is not None else ()
        ),
        live_user_data_summary_ref=(
            bundle.live_user_data_summary_ref if bundle is not None else ""
        ),
        live_user_data_authenticated=(
            bundle.live_user_data_authenticated if bundle is not None else False
        ),
        live_user_data_subscription_id=(
            bundle.live_user_data_subscription_id if bundle is not None else None
        ),
        live_user_data_event_count=(
            bundle.live_user_data_event_count if bundle is not None else 0
        ),
        live_user_data_event_types=(
            bundle.live_user_data_event_types if bundle is not None else ()
        ),
        runtime_evidence_bundle_ref=state.last_runtime_evidence_bundle_ref,
        shadow_report_ref=state.last_shadow_report_ref,
        shadow_session_summary_ref=state.last_shadow_session_summary_ref,
        shadow_session_registry_ref=state.last_shadow_session_registry_ref,
        orchestrator_state_ref=state.last_orchestrator_state_ref,
    )
    summary_path.write_text(summary.model_dump_json(indent=2), encoding="utf-8")
    return summary_path


def run_shadow_vps_service(
    service_dir: Path,
    *,
    orchestrator_output_dir: Path | None = None,
    shadow_output_dir: Path | None = None,
    exports_root: Path | None = None,
    raw_inputs_root: Path | None = None,
    websocket_streams_root: Path | None = None,
    live_websocket_config_path: Path | None = None,
    live_captures_root: Path | None = None,
    auto_snapshots_root: Path | None = None,
    auto_exports_root: Path | None = None,
    poll_interval_s: float = 5.0,
    max_cycles: int | None = None,
    continue_on_error: bool = True,
) -> int:
    service_dir.mkdir(parents=True, exist_ok=True)
    resolved_orchestrator_output_dir = orchestrator_output_dir or (
        service_dir / "orchestrator"
    )
    resolved_shadow_output_dir = shadow_output_dir or (service_dir / "shadow_session")
    resolved_live_captures_root = live_captures_root or (service_dir / "live_captures")
    resolved_auto_snapshots_root = auto_snapshots_root or (service_dir / "auto_snapshots")
    resolved_auto_exports_root = auto_exports_root or (service_dir / "auto_exports")
    store = ShadowVpsServiceStore(service_dir)
    state = store.state
    state.resumed = state.loop_count > 0
    if state.started_at is None:
        state.started_at = time.time()
    state.service_status = ShadowVpsServiceStatus.RUNNING
    state.last_error = ""
    store.persist()
    store.append_event(
        ShadowVpsServiceEvent(
            event_type="service_started",
            message=(
                "Shadow VPS service resumed"
                if state.resumed
                else "Shadow VPS service started"
            ),
        )
    )

    launcher = _load_daily_orchestrator_module()
    cycle_index = 0
    while max_cycles is None or cycle_index < max_cycles:
        cycle_index += 1
        state.loop_count += 1
        state.last_heartbeat_at = time.time()
        state.service_status = ShadowVpsServiceStatus.RUNNING
        store.persist()

        try:
            daily_orchestrator = ShadowDailyOrchestrator(resolved_orchestrator_output_dir)
            completed_session_dates = set(daily_orchestrator.completed_session_dates())
            raw_slot = (
                _select_next_raw_input_slot(raw_inputs_root, daily_orchestrator)
                if raw_inputs_root is not None
                else None
            )
            websocket_slot = (
                _select_next_websocket_input_slot(websocket_streams_root, daily_orchestrator)
                if websocket_streams_root is not None
                else None
            )
            live_config = (
                _read_live_websocket_config(live_websocket_config_path)
                if live_websocket_config_path is not None
                else None
            )
            live_session_date = (
                live_config.session_date_override or date.today().isoformat()
                if live_config is not None
                else ""
            )
            auto_export_dir: Path | None = None
            auto_snapshot_dir: Path | None = None
            live_capture_dir: Path | None = None
            if raw_slot is not None:
                auto_export_dir = _ensure_auto_export_from_raw_slot(
                    raw_slot,
                    auto_exports_root=resolved_auto_exports_root,
                )
                next_slot = daily_orchestrator.select_next_slot(resolved_auto_exports_root)
            elif websocket_slot is not None:
                auto_snapshot_dir, auto_export_dir = _ensure_auto_export_from_websocket_slot(
                    websocket_slot,
                    auto_snapshots_root=resolved_auto_snapshots_root,
                    auto_exports_root=resolved_auto_exports_root,
                )
                next_slot = daily_orchestrator.select_next_slot(resolved_auto_exports_root)
            elif live_config is not None:
                if live_session_date in completed_session_dates:
                    next_slot = None
                else:
                    live_capture_dir, auto_export_dir = _ensure_auto_export_from_live_websocket(
                        live_config,
                        live_captures_root=resolved_live_captures_root,
                        auto_exports_root=resolved_auto_exports_root,
                    )
                    next_slot = daily_orchestrator.select_next_slot(resolved_auto_exports_root)
            else:
                next_slot = (
                    daily_orchestrator.select_next_slot(exports_root)
                    if exports_root is not None
                    else daily_orchestrator.next_demo_slot()
                )
            if next_slot is None:
                state.idle_count += 1
                state.service_status = ShadowVpsServiceStatus.IDLE
                store.persist()
                store.append_event(
                    ShadowVpsServiceEvent(
                        event_type="idle_no_pending_export",
                        message="No pending governed Shadow export directory was found.",
                    )
                )
                if max_cycles is None or cycle_index < max_cycles:
                    time.sleep(max(0.0, poll_interval_s))
                continue

            state.last_selected_session_date = next_slot.session_date
            state.last_raw_input_dir_ref = raw_slot.raw_input_dir_ref if raw_slot is not None else ""
            state.last_websocket_input_dir_ref = (
                websocket_slot.websocket_input_dir_ref if websocket_slot is not None else ""
            )
            live_capture_result = _read_live_capture_result(live_capture_dir)
            state.last_live_capture_dir_ref = (
                live_capture_result.live_capture_dir_ref
                if live_capture_result is not None
                else ""
            )
            state.last_live_capture_snapshot_batch_ref = (
                live_capture_result.snapshot_batch_path_ref
                if live_capture_result is not None
                else ""
            )
            state.last_live_capture_summary_ref = (
                live_capture_result.summary_path_ref
                if live_capture_result is not None
                else ""
            )
            state.last_live_user_data_summary_ref = (
                live_capture_result.user_data_summary_path_ref
                if live_capture_result is not None
                else ""
            )
            state.last_auto_snapshot_dir_ref = (
                str(auto_snapshot_dir.resolve()) if auto_snapshot_dir is not None else ""
            )
            state.last_auto_export_dir_ref = str(auto_export_dir.resolve()) if auto_export_dir is not None else ""
            store.persist()
            if raw_slot is not None and auto_export_dir is not None:
                store.append_event(
                    ShadowVpsServiceEvent(
                        event_type="auto_export_completed",
                        message="Governed local replay export was auto-generated from raw VPS input.",
                        session_date=raw_slot.session_date,
                        export_dir_ref=str(auto_export_dir.resolve()),
                    )
                )
            if websocket_slot is not None and auto_snapshot_dir is not None:
                store.append_event(
                    ShadowVpsServiceEvent(
                        event_type="auto_snapshot_completed",
                        message="Historical snapshot batch was auto-generated from injected websocket stream.",
                        session_date=websocket_slot.session_date,
                        export_dir_ref=str(auto_snapshot_dir.resolve()),
                    )
                )
            if websocket_slot is not None and auto_export_dir is not None:
                store.append_event(
                    ShadowVpsServiceEvent(
                        event_type="auto_export_completed",
                        message="Governed local replay export was auto-generated from injected websocket stream.",
                        session_date=websocket_slot.session_date,
                        export_dir_ref=str(auto_export_dir.resolve()),
                    )
                )
            if live_capture_dir is not None:
                store.append_event(
                    ShadowVpsServiceEvent(
                        event_type="live_capture_completed",
                        message="Native live_websocket capture completed.",
                        session_date=next_slot.session_date,
                        export_dir_ref=str(live_capture_dir.resolve()),
                        live_capture_summary_ref=(
                            live_capture_result.summary_path_ref
                            if live_capture_result is not None
                            else ""
                        ),
                        emitted_message_count=(
                            live_capture_result.emitted_message_count
                            if live_capture_result is not None
                            else None
                        ),
                        accepted_message_count=(
                            live_capture_result.accepted_message_count
                            if live_capture_result is not None
                            else None
                        ),
                        ignored_message_count=(
                            live_capture_result.ignored_message_count
                            if live_capture_result is not None
                            else None
                        ),
                        rejected_message_count=(
                            live_capture_result.rejected_message_count
                            if live_capture_result is not None
                            else None
                        ),
                        pair_scope=(
                            live_capture_result.pair_scope
                            if live_capture_result is not None
                            else ()
                        ),
                        event_types=(
                            live_capture_result.event_types
                            if live_capture_result is not None
                            else ()
                        ),
                    )
                )
            if live_capture_dir is not None and auto_export_dir is not None:
                store.append_event(
                    ShadowVpsServiceEvent(
                        event_type="auto_export_completed",
                        message="Governed local replay export was auto-generated from native live_websocket capture.",
                        session_date=next_slot.session_date,
                        export_dir_ref=str(auto_export_dir.resolve()),
                    )
                )
            exit_code = launcher.orchestrate_one_shadow_day(
                resolved_orchestrator_output_dir,
                shadow_output_dir=resolved_shadow_output_dir,
                export_dir=Path(next_slot.export_dir_ref)
                if next_slot.export_dir_ref
                else None,
                session_date=next_slot.session_date,
            )
            if exit_code != 0:
                raise RuntimeError(
                    f"Daily Shadow orchestrator returned non-zero exit code {exit_code}"
                )

            last_run = _read_last_run(resolved_orchestrator_output_dir)
            runtime_evidence_bundle_path = _write_runtime_evidence_bundle(
                service_dir=service_dir,
                session_date=last_run["session_date"],
                raw_slot=raw_slot,
                websocket_slot=websocket_slot,
                live_capture_result=live_capture_result,
                auto_snapshot_dir=auto_snapshot_dir,
                auto_export_dir=auto_export_dir,
                last_run=last_run,
            )
            state.success_count += 1
            state.service_status = ShadowVpsServiceStatus.RUNNING
            state.last_completed_session_date = last_run["session_date"]
            state.last_live_capture_dir_ref = (
                str(live_capture_dir.resolve())
                if live_capture_dir is not None
                else state.last_live_capture_dir_ref
            )
            state.last_auto_snapshot_dir_ref = (
                str(auto_snapshot_dir.resolve())
                if auto_snapshot_dir is not None
                else state.last_auto_snapshot_dir_ref
            )
            state.last_auto_export_dir_ref = (
                str(auto_export_dir.resolve()) if auto_export_dir is not None else state.last_auto_export_dir_ref
            )
            state.last_export_dir_ref = last_run.get("export_dir_ref", "")
            state.last_local_replay_evidence_ref = last_run.get("local_replay_evidence_ref", "")
            state.last_shadow_runtime_evidence_ref = last_run.get("shadow_runtime_evidence_ref", "")
            state.last_runtime_evidence_bundle_ref = str(runtime_evidence_bundle_path.resolve())
            state.last_orchestrator_state_ref = last_run["state_path"]
            state.last_shadow_report_ref = last_run["shadow_report_ref"]
            state.last_shadow_session_summary_ref = last_run["shadow_session_summary_ref"]
            state.last_shadow_session_registry_ref = last_run[
                "shadow_session_registry_ref"
            ]
            state.last_error = ""
            bundle = _read_runtime_evidence_bundle(str(runtime_evidence_bundle_path))
            campaign_summary_path = _write_campaign_summary(
                service_dir=service_dir,
                state=state,
                bundle=bundle,
            )
            state.last_campaign_summary_ref = str(campaign_summary_path.resolve())
            store.persist()
            store.append_event(
                ShadowVpsServiceEvent(
                    event_type="runtime_evidence_bundle_written",
                    message="Durable Build-11 runtime evidence bundle was written.",
                    session_date=last_run["session_date"],
                    export_dir_ref=str(runtime_evidence_bundle_path.resolve()),
                )
            )
            store.append_event(
                ShadowVpsServiceEvent(
                    event_type="shadow_day_completed",
                    message="Governed Shadow day completed.",
                    session_date=last_run["session_date"],
                    export_dir_ref=last_run.get("export_dir_ref", ""),
                    accepted=bool(last_run["accepted"]),
                    consecutive_days=int(last_run["consecutive_days"]),
                    remaining_days=int(last_run["remaining_days"]),
                )
            )
        except Exception as exc:
            state.failure_count += 1
            state.service_status = ShadowVpsServiceStatus.DEGRADED
            state.last_error = str(exc)
            store.persist()
            store.append_event(
                ShadowVpsServiceEvent(
                    event_type="shadow_day_failed",
                    message="Governed Shadow day failed.",
                    session_date=state.last_selected_session_date,
                    export_dir_ref=state.last_export_dir_ref,
                    error=str(exc),
                )
            )
            if not continue_on_error:
                break
            if max_cycles is None or cycle_index < max_cycles:
                time.sleep(max(0.0, poll_interval_s))

    if state.service_status != ShadowVpsServiceStatus.DEGRADED:
        state.service_status = ShadowVpsServiceStatus.STOPPED
    state.last_heartbeat_at = time.time()
    final_bundle = _read_runtime_evidence_bundle(state.last_runtime_evidence_bundle_ref)
    if state.last_runtime_evidence_bundle_ref:
        campaign_summary_path = _write_campaign_summary(
            service_dir=service_dir,
            state=state,
            bundle=final_bundle,
        )
        state.last_campaign_summary_ref = str(campaign_summary_path.resolve())
    store.persist()
    store.append_event(
        ShadowVpsServiceEvent(
            event_type="service_stopped",
            message="Shadow VPS service stopped.",
            session_date=state.last_completed_session_date,
        )
    )

    print(f"Shadow VPS service state JSON: {store.state_path}")
    print(f"Shadow VPS service events JSONL: {store.events_path}")
    print(f"Shadow daily orchestrator state JSON: {resolved_orchestrator_output_dir / 'shadow_daily_orchestrator.state.json'}")
    print(f"Shadow session summary JSON: {resolved_shadow_output_dir / 'local_replay_shadow.shadow_session_summary.json'}")
    if state.last_campaign_summary_ref:
        print(f"Shadow VPS campaign summary JSON: {state.last_campaign_summary_ref}")
    if state.last_runtime_evidence_bundle_ref:
        print(f"Shadow runtime evidence bundle JSON: {state.last_runtime_evidence_bundle_ref}")
    return 0


def main(argv: list[str] | None = None) -> int:
    _configure_stdio()
    parser = argparse.ArgumentParser(
        description=(
            "Run the autonomous VPS Shadow service that keeps polling and processing governed Shadow days."
        ),
    )
    parser.add_argument(
        "--service-dir",
        type=Path,
        default=REPO_ROOT / "build" / "shadow_vps_service",
        help="Directory used to persist the VPS Shadow service state and logs.",
    )
    parser.add_argument(
        "--orchestrator-output-dir",
        type=Path,
        default=None,
        help="Optional directory used for the external daily orchestrator state.",
    )
    parser.add_argument(
        "--shadow-output-dir",
        type=Path,
        default=None,
        help="Optional directory used for the long-lived Shadow session artifacts.",
    )
    parser.add_argument(
        "--exports-root",
        type=Path,
        default=None,
        help="Optional root containing daily export directories named YYYY-MM-DD.",
    )
    parser.add_argument(
        "--raw-inputs-root",
        type=Path,
        default=None,
        help=(
            "Optional root containing daily raw input directories named YYYY-MM-DD. "
            "Each dated directory must contain a replay_dataset.* or snapshot_batch.* file."
        ),
    )
    parser.add_argument(
        "--websocket-streams-root",
        type=Path,
        default=None,
        help=(
            "Optional root containing daily injected websocket directories named YYYY-MM-DD. "
            "Each dated directory must contain websocket_stream.json(.l) or websocket_frames.json(.l)."
        ),
    )
    parser.add_argument(
        "--live-websocket-config",
        type=Path,
        default=None,
        help=(
            "Optional JSON config used to capture a bounded native live_websocket window "
            "directly from the VPS."
        ),
    )
    parser.add_argument(
        "--live-captures-root",
        type=Path,
        default=None,
        help=(
            "Optional root where native live_websocket captures will be written before "
            "governed export."
        ),
    )
    parser.add_argument(
        "--auto-snapshots-root",
        type=Path,
        default=None,
        help=(
            "Optional root where historical snapshot batches auto-generated from "
            "--websocket-streams-root will be written."
        ),
    )
    parser.add_argument(
        "--auto-exports-root",
        type=Path,
        default=None,
        help=(
            "Optional root where governed exports auto-generated from --raw-inputs-root "
            "will be written."
        ),
    )
    parser.add_argument(
        "--poll-interval-s",
        type=float,
        default=5.0,
        help="Sleep duration between cycles when the service stays alive.",
    )
    parser.add_argument(
        "--max-cycles",
        type=int,
        default=None,
        help="Optional maximum number of service cycles. Useful for tests and smoke runs.",
    )
    parser.add_argument(
        "--stop-on-error",
        action="store_true",
        help="Stop the service immediately on the first orchestration error.",
    )
    args = parser.parse_args(argv)
    selected_input_roots = (
        int(args.exports_root is not None)
        + int(args.raw_inputs_root is not None)
        + int(args.websocket_streams_root is not None)
        + int(args.live_websocket_config is not None)
    )
    if selected_input_roots > 1:
        parser.error(
            "--exports-root, --raw-inputs-root, --websocket-streams-root, and --live-websocket-config are mutually exclusive"
        )
    return run_shadow_vps_service(
        args.service_dir,
        orchestrator_output_dir=args.orchestrator_output_dir,
        shadow_output_dir=args.shadow_output_dir,
        exports_root=args.exports_root,
        raw_inputs_root=args.raw_inputs_root,
        websocket_streams_root=args.websocket_streams_root,
        live_websocket_config_path=args.live_websocket_config,
        live_captures_root=args.live_captures_root,
        auto_snapshots_root=args.auto_snapshots_root,
        auto_exports_root=args.auto_exports_root,
        poll_interval_s=max(0.0, args.poll_interval_s),
        max_cycles=args.max_cycles,
        continue_on_error=not args.stop_on_error,
    )


if __name__ == "__main__":
    raise SystemExit(main())
