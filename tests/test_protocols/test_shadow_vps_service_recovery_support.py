from __future__ import annotations

import os
import shutil
from pathlib import Path
from types import SimpleNamespace

from protocols import (
    ShadowLiveWebSocketCaptureResult,
    ShadowLiveWebSocketConfig,
    ShadowVpsServiceStore,
)


def _load_recovery_support_module():
    from tests.test_protocols.test_shadow_vps_service_launcher import _load_service_module

    _load_service_module()
    import shadow_vps_service_recovery_support as recovery_support

    return recovery_support


def _scratch_dir(label: str) -> Path:
    from tests.test_protocols.test_shadow_vps_service_launcher import _scratch_dir

    return _scratch_dir(label)


def test_refresh_shadow_vps_recovery_artifacts_recaptures_stale_live_capture(
    monkeypatch,
) -> None:
    recovery_support = _load_recovery_support_module()
    output_dir = _scratch_dir("recovery_refreshes_stale_live_capture")

    try:
        service_dir = output_dir / "service"
        live_captures_root = output_dir / "live_captures"
        store = ShadowVpsServiceStore(service_dir)
        stale_capture = ShadowLiveWebSocketCaptureResult(
            session_date="2026-04-27",
            live_capture_dir_ref=str((live_captures_root / "2026-04-27").resolve()),
            snapshot_batch_path_ref=str(
                (live_captures_root / "2026-04-27" / "live_websocket_snapshot_batch.json").resolve()
            ),
            summary_path_ref=str(
                (live_captures_root / "2026-04-27" / "live_websocket_capture_summary.json").resolve()
            ),
            user_data_authenticated=False,
        )
        refreshed_capture = ShadowLiveWebSocketCaptureResult(
            session_date="2026-04-28",
            live_capture_dir_ref=str((live_captures_root / "2026-04-28").resolve()),
            snapshot_batch_path_ref=str(
                (live_captures_root / "2026-04-28" / "live_websocket_snapshot_batch.json").resolve()
            ),
            summary_path_ref=str(
                (live_captures_root / "2026-04-28" / "live_websocket_capture_summary.json").resolve()
            ),
            time_sync_offsets_path_ref=str(
                (live_captures_root / "2026-04-28" / "time_sync_offsets.json").resolve()
            ),
            user_data_summary_path_ref=str(
                (live_captures_root / "2026-04-28" / "live_user_data_capture_summary.json").resolve()
            ),
            user_data_authenticated=True,
        )
        live_config = ShadowLiveWebSocketConfig(
            user_data_stream_enabled=True,
            session_date_override="2026-04-28",
        )
        capture_calls: list[Path] = []
        persisted: list[tuple[object, object]] = []
        readiness_inputs: list[ShadowLiveWebSocketCaptureResult | None] = []

        context = SimpleNamespace(
            resolved_live_captures_root=live_captures_root,
            live_websocket_config_path=output_dir / "live_websocket_config.json",
            execution_time_sync_offsets_path=None,
            bootstrap_summary=SimpleNamespace(status="ready"),
            store=store,
        )

        monkeypatch.setattr(
            recovery_support,
            "_load_capture_result",
            lambda _context, _live_capture_result=None: stale_capture,
        )
        monkeypatch.setattr(
            recovery_support,
            "_resolve_live_config",
            lambda _context: live_config,
        )
        monkeypatch.setattr(
            recovery_support,
            "capture_live_websocket_snapshot_batch",
            lambda _config, *, output_dir: capture_calls.append(Path(output_dir)) or refreshed_capture,
        )
        monkeypatch.setattr(
            recovery_support,
            "_build_readiness_report",
            lambda _context, *, capture_result, live_config: readiness_inputs.append(capture_result) or "report",
        )
        monkeypatch.setattr(
            recovery_support,
            "_build_warmup_summary",
            lambda report: "warmup",
        )
        monkeypatch.setattr(
            recovery_support,
            "_persist_recovery_artifacts",
            lambda _context, report, warmup: persisted.append((report, warmup)),
        )

        report, warmup = recovery_support._refresh_shadow_vps_recovery_artifacts(context)

        assert capture_calls == [live_captures_root / "2026-04-28"]
        assert readiness_inputs == [refreshed_capture]
        assert persisted == [("report", "warmup")]
        assert report == "report"
        assert warmup == "warmup"
        assert store.state.last_live_capture_dir_ref == refreshed_capture.live_capture_dir_ref
        assert (
            store.state.last_live_capture_snapshot_batch_ref
            == refreshed_capture.snapshot_batch_path_ref
        )
        assert (
            store.state.last_live_user_data_summary_ref
            == refreshed_capture.user_data_summary_path_ref
        )
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_refresh_shadow_vps_recovery_artifacts_recaptures_current_session_when_snapshot_is_stale(
    monkeypatch,
) -> None:
    recovery_support = _load_recovery_support_module()
    output_dir = _scratch_dir("recovery_refreshes_current_session_stale_snapshot")

    try:
        service_dir = output_dir / "service"
        live_captures_root = output_dir / "live_captures"
        capture_dir = live_captures_root / "2026-04-28"
        capture_dir.mkdir(parents=True, exist_ok=True)
        snapshot_path = capture_dir / "live_websocket_snapshot_batch.json"
        summary_path = capture_dir / "live_websocket_capture_summary.json"
        snapshot_path.write_text("[]", encoding="utf-8")
        summary_path.write_text("{}", encoding="utf-8")
        os.utime(snapshot_path, (1_000.0, 1_000.0))
        os.utime(summary_path, (1_000.0, 1_000.0))

        store = ShadowVpsServiceStore(service_dir)
        stale_capture = ShadowLiveWebSocketCaptureResult(
            session_date="2026-04-28",
            live_capture_dir_ref=str(capture_dir.resolve()),
            snapshot_batch_path_ref=str(snapshot_path.resolve()),
            summary_path_ref=str(summary_path.resolve()),
            user_data_authenticated=True,
        )
        refreshed_capture = ShadowLiveWebSocketCaptureResult(
            session_date="2026-04-28",
            live_capture_dir_ref=str(capture_dir.resolve()),
            snapshot_batch_path_ref=str(snapshot_path.resolve()),
            summary_path_ref=str(summary_path.resolve()),
            user_data_authenticated=True,
        )
        live_config = ShadowLiveWebSocketConfig(
            user_data_stream_enabled=True,
            session_date_override="2026-04-28",
        )
        capture_calls: list[Path] = []
        readiness_inputs: list[ShadowLiveWebSocketCaptureResult | None] = []

        context = SimpleNamespace(
            resolved_live_captures_root=live_captures_root,
            live_websocket_config_path=output_dir / "live_websocket_config.json",
            execution_time_sync_offsets_path=None,
            bootstrap_summary=SimpleNamespace(status="ready"),
            store=store,
        )

        monkeypatch.setattr(recovery_support.time, "time", lambda: 1_030.0)
        monkeypatch.setattr(
            recovery_support,
            "_load_capture_result",
            lambda _context, _live_capture_result=None: stale_capture,
        )
        monkeypatch.setattr(
            recovery_support,
            "_resolve_live_config",
            lambda _context: live_config,
        )
        monkeypatch.setattr(
            recovery_support,
            "capture_live_websocket_snapshot_batch",
            lambda _config, *, output_dir: capture_calls.append(Path(output_dir)) or refreshed_capture,
        )
        monkeypatch.setattr(
            recovery_support,
            "_build_readiness_report",
            lambda _context, *, capture_result, live_config: readiness_inputs.append(capture_result) or "report",
        )
        monkeypatch.setattr(recovery_support, "_build_warmup_summary", lambda report: "warmup")
        monkeypatch.setattr(
            recovery_support,
            "_persist_recovery_artifacts",
            lambda _context, report, warmup: None,
        )

        report, warmup = recovery_support._refresh_shadow_vps_recovery_artifacts(context)

        assert capture_calls == [live_captures_root / "2026-04-28"]
        assert readiness_inputs == [refreshed_capture]
        assert report == "report"
        assert warmup == "warmup"
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
