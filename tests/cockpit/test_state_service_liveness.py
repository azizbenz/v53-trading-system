from __future__ import annotations

from datetime import UTC, datetime, timedelta
import json

from cockpit.runtime_support import read_runtime_surfaces
from cockpit.state_service_liveness import read_service_liveness

from ._operational_helpers import build_paths, cleanup_scratch, scratch_dir, seed_phase25_files


def test_service_liveness_reports_running_when_pid_alive(monkeypatch) -> None:
    scratch = scratch_dir("service_liveness_running")
    try:
        paths = build_paths(scratch)
        seed_phase25_files(paths)
        paths.pid_file.write_text("6576", encoding="utf-8")
        runtime = read_runtime_surfaces(
            service_dir=paths.service_dir,
            queue_root=paths.dashboard_command_queue_root,
            observability_output_dir=paths.observability_output_dir,
            backtest_jobs_root=paths.backtest_jobs_root,
        )
        monkeypatch.setattr("cockpit.state_service_liveness._pid_is_alive", lambda pid: True)
        snapshot = read_service_liveness(paths, runtime=runtime)
        assert snapshot.shadow_service_running is True
        assert snapshot.pid_is_alive is True
        assert snapshot.control_ready is False
        assert snapshot.archive_reader_only is False
    finally:
        cleanup_scratch(scratch)


def test_service_liveness_reports_offline_without_pid_and_stale_heartbeat() -> None:
    scratch = scratch_dir("service_liveness_offline")
    try:
        paths = build_paths(scratch)
        seed_phase25_files(paths)
        runtime = read_runtime_surfaces(
            service_dir=paths.service_dir,
            queue_root=paths.dashboard_command_queue_root,
            observability_output_dir=paths.observability_output_dir,
            backtest_jobs_root=paths.backtest_jobs_root,
        )
        payload = runtime.monitoring_payload.model_copy(update={"heartbeat_age_ms": 120_000})
        (paths.service_dir / "shadow_vps_service_monitoring_backend_payload.json").write_text(
            payload.model_dump_json(indent=2),
            encoding="utf-8",
        )
        runtime = read_runtime_surfaces(
            service_dir=paths.service_dir,
            queue_root=paths.dashboard_command_queue_root,
            observability_output_dir=paths.observability_output_dir,
            backtest_jobs_root=paths.backtest_jobs_root,
        )
        snapshot = read_service_liveness(paths, runtime=runtime)
        assert snapshot.shadow_service_running is False
        assert snapshot.archive_reader_only is True
    finally:
        cleanup_scratch(scratch)


def test_service_liveness_returns_parse_error_for_corrupt_payload() -> None:
    scratch = scratch_dir("service_liveness_parse")
    try:
        paths = build_paths(scratch)
        (paths.service_dir / "shadow_vps_service_monitoring_backend_payload.json").write_text(
            "{bad json",
            encoding="utf-8",
        )
        runtime = read_runtime_surfaces(
            service_dir=paths.service_dir,
            queue_root=paths.dashboard_command_queue_root,
            observability_output_dir=paths.observability_output_dir,
            backtest_jobs_root=paths.backtest_jobs_root,
        )
        snapshot = read_service_liveness(paths, runtime=runtime)
        assert snapshot.source_status == "parse_error"
    finally:
        cleanup_scratch(scratch)


def test_service_liveness_does_not_treat_stale_payload_heartbeat_as_live() -> None:
    scratch = scratch_dir("service_liveness_stale_payload")
    try:
        paths = build_paths(scratch)
        seed_phase25_files(paths)
        runtime = read_runtime_surfaces(
            service_dir=paths.service_dir,
            queue_root=paths.dashboard_command_queue_root,
            observability_output_dir=paths.observability_output_dir,
            backtest_jobs_root=paths.backtest_jobs_root,
        )
        stale_timestamp_ms = int(
            (datetime.now(tz=UTC) - timedelta(minutes=11)).timestamp() * 1000.0
        )
        payload = runtime.monitoring_payload.model_copy(
            update={
                "timestamp_ms": stale_timestamp_ms,
                "heartbeat_age_ms": 388,
            }
        )
        (paths.service_dir / "shadow_vps_service_monitoring_backend_payload.json").write_text(
            payload.model_dump_json(indent=2),
            encoding="utf-8",
        )
        runtime = read_runtime_surfaces(
            service_dir=paths.service_dir,
            queue_root=paths.dashboard_command_queue_root,
            observability_output_dir=paths.observability_output_dir,
            backtest_jobs_root=paths.backtest_jobs_root,
        )
        snapshot = read_service_liveness(paths, runtime=runtime)
        assert snapshot.shadow_service_running is False
        assert snapshot.archive_reader_only is True
        assert snapshot.heartbeat_age_seconds is not None
        assert snapshot.heartbeat_age_seconds > 600.0
    finally:
        cleanup_scratch(scratch)


def test_service_liveness_treats_idle_service_with_fresh_heartbeat_as_control_ready(monkeypatch) -> None:
    scratch = scratch_dir("service_liveness_idle_control_ready")
    try:
        paths = build_paths(scratch)
        seed_phase25_files(paths)
        paths.pid_file.write_text("7777", encoding="utf-8")
        runtime = read_runtime_surfaces(
            service_dir=paths.service_dir,
            queue_root=paths.dashboard_command_queue_root,
            observability_output_dir=paths.observability_output_dir,
            backtest_jobs_root=paths.backtest_jobs_root,
        )
        payload = runtime.monitoring_payload.model_copy(update={"service_status": "idle"})
        (paths.service_dir / "shadow_vps_service_monitoring_backend_payload.json").write_text(
            payload.model_dump_json(indent=2),
            encoding="utf-8",
        )
        runtime = read_runtime_surfaces(
            service_dir=paths.service_dir,
            queue_root=paths.dashboard_command_queue_root,
            observability_output_dir=paths.observability_output_dir,
            backtest_jobs_root=paths.backtest_jobs_root,
        )
        monkeypatch.setattr("cockpit.state_service_liveness._pid_is_alive", lambda pid: True)
        snapshot = read_service_liveness(paths, runtime=runtime)
        assert snapshot.shadow_service_running is True
        assert snapshot.pid_is_alive is True
        assert snapshot.service_status == "idle"
        assert snapshot.control_ready is True
        assert snapshot.archive_reader_only is False
        assert "service_not_control_ready" not in snapshot.reason_codes
    finally:
        cleanup_scratch(scratch)


def test_service_liveness_tolerates_null_state_heartbeat_without_payload() -> None:
    scratch = scratch_dir("service_liveness_null_state_heartbeat")
    try:
        paths = build_paths(scratch)
        seed_phase25_files(paths)
        state_path = paths.service_dir / "shadow_vps_service.state.json"
        payload_path = paths.service_dir / "shadow_vps_service_monitoring_backend_payload.json"
        state_payload = json.loads(state_path.read_text(encoding="utf-8"))
        state_payload["last_heartbeat_at"] = None
        state_path.write_text(json.dumps(state_payload, indent=2), encoding="utf-8")
        payload_path.unlink(missing_ok=True)
        runtime = read_runtime_surfaces(
            service_dir=paths.service_dir,
            queue_root=paths.dashboard_command_queue_root,
            observability_output_dir=paths.observability_output_dir,
            backtest_jobs_root=paths.backtest_jobs_root,
        )
        snapshot = read_service_liveness(paths, runtime=runtime)
        assert snapshot.last_heartbeat_at is None
        assert snapshot.heartbeat_age_seconds is None
        assert snapshot.shadow_service_running is False
    finally:
        cleanup_scratch(scratch)
