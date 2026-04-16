"""Shadow VPS service input slot + auto-export helpers."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from protocols import (
    ShadowDailyOrchestrator,
    ShadowLiveWebSocketConfig,
    ShadowVpsRawInputSlot,
    ShadowVpsWebsocketInputSlot,
    build_snapshot_batch_from_injected_websocket_stream,
    capture_live_websocket_snapshot_batch,
)
from shadow_vps_service_io_support import _read_raw_input_config
from shadow_vps_service_loader_support import _load_local_replay_export_module


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
        (
            raw_input_dir / candidate
            for candidate in dataset_candidates
            if (raw_input_dir / candidate).is_file()
        ),
        None,
    )
    snapshot_path = next(
        (
            raw_input_dir / candidate
            for candidate in snapshot_candidates
            if (raw_input_dir / candidate).is_file()
        ),
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
    dated_dirs = sorted(item for item in raw_inputs_root.iterdir() if item.is_dir())
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


def _has_auto_export_artifacts(auto_export_dir: Path) -> bool:
    return (
        (auto_export_dir / "replay_run_manifest.json").is_file()
        and (auto_export_dir / "review_export.md").is_file()
        and (auto_export_dir / "feature_bridge.json").is_file()
        and (auto_export_dir / "parity_diagnostics.json").is_file()
        and (auto_export_dir / "replay_metrics.json").is_file()
        and (
            (auto_export_dir / "replay_dtr.jsonl").is_file()
            or (auto_export_dir / "replay_dtr.json").is_file()
        )
    )


def _ensure_auto_export_from_raw_slot(
    raw_slot: ShadowVpsRawInputSlot,
    *,
    auto_exports_root: Path,
) -> Path:
    auto_export_dir = auto_exports_root / raw_slot.session_date
    if _has_auto_export_artifacts(auto_export_dir):
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
    if _has_auto_export_artifacts(auto_export_dir):
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
    if _has_auto_export_artifacts(auto_export_dir):
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
