from __future__ import annotations

import time

from cockpit.runtime_support import read_runtime_surfaces
from cockpit.state_queue_trace import read_queue_trace

from ._operational_helpers import (
    build_paths,
    cleanup_scratch,
    scratch_dir,
    seed_phase25_files,
    write_queue_request,
    write_queue_result,
)


def test_queue_trace_not_configured_when_root_missing() -> None:
    scratch = scratch_dir("queue_trace_missing")
    try:
        paths = build_paths(scratch)
        runtime = read_runtime_surfaces(
            service_dir=paths.service_dir,
            queue_root=None,
            observability_output_dir=paths.observability_output_dir,
            backtest_jobs_root=paths.backtest_jobs_root,
        )
        snapshot = read_queue_trace(
            paths.model_copy(update={"dashboard_command_queue_root": None}),
            runtime=runtime,
        )
        assert snapshot.consumption_status == "not_configured"
    finally:
        cleanup_scratch(scratch)


def test_queue_trace_marks_pending_queue_without_result() -> None:
    scratch = scratch_dir("queue_trace_pending")
    try:
        paths = build_paths(scratch)
        seed_phase25_files(paths)
        write_queue_request(
            paths,
            request_id="req-pending",
            timestamp_ms=int(time.time() * 1000) - 120_000,
        )
        runtime = read_runtime_surfaces(
            service_dir=paths.service_dir,
            queue_root=paths.dashboard_command_queue_root,
            observability_output_dir=paths.observability_output_dir,
            backtest_jobs_root=paths.backtest_jobs_root,
        )
        snapshot = read_queue_trace(paths, runtime=runtime)
        assert snapshot.queue_status == "queue_pending"
        assert snapshot.queue_backlog_stalled is True
    finally:
        cleanup_scratch(scratch)


def test_queue_trace_distinguishes_consumed_by_service_vs_queue_only() -> None:
    scratch = scratch_dir("queue_trace_consumed")
    try:
        paths = build_paths(scratch)
        seed_phase25_files(paths)
        write_queue_request(paths, request_id="req-1")
        write_queue_result(paths, request_id="req-1")
        runtime = read_runtime_surfaces(
            service_dir=paths.service_dir,
            queue_root=paths.dashboard_command_queue_root,
            observability_output_dir=paths.observability_output_dir,
            backtest_jobs_root=paths.backtest_jobs_root,
        )
        queue_only = read_queue_trace(paths, runtime=runtime)
        assert queue_only.consumption_status == "queue_only"

        monitoring_path = paths.service_dir / "shadow_vps_service_monitoring_backend_payload.json"
        payload = runtime.monitoring_payload.model_copy(
            update={
                "dashboard_control_last_request_id": "req-1",
                "dashboard_control_last_command_kind": "request_export_shadow_challenger_verdict_bundle",
                "dashboard_control_last_result_status": "completed",
            }
        )
        monitoring_path.write_text(payload.model_dump_json(indent=2), encoding="utf-8")
        runtime = read_runtime_surfaces(
            service_dir=paths.service_dir,
            queue_root=paths.dashboard_command_queue_root,
            observability_output_dir=paths.observability_output_dir,
            backtest_jobs_root=paths.backtest_jobs_root,
        )
        consumed = read_queue_trace(paths, runtime=runtime)
        assert consumed.consumption_status == "consumed_by_service"
        assert consumed.consumer_service_pid == runtime.monitoring_payload.process.pid
        assert consumed.service_last_request_id == "req-1"
        assert consumed.service_last_result_status == "completed"
    finally:
        cleanup_scratch(scratch)
