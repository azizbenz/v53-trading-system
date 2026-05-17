from __future__ import annotations

from cockpit.runtime_support import read_runtime_surfaces
from cockpit.state import read_warmup_summary
from cockpit.state_run_comparison import read_run_comparison

from ._operational_helpers import (
    build_paths,
    cleanup_scratch,
    scratch_dir,
    seed_phase25_files,
)


def test_run_comparison_reads_latest_vs_previous_run() -> None:
    scratch = scratch_dir("run_comparison")
    try:
        paths = build_paths(scratch)
        seed_phase25_files(paths)
        runtime = read_runtime_surfaces(
            service_dir=paths.service_dir,
            queue_root=paths.dashboard_command_queue_root,
            observability_output_dir=paths.observability_output_dir,
            backtest_jobs_root=paths.backtest_jobs_root,
        )
        snapshot = read_run_comparison(
            paths.auto_exports_root,
            runtime=runtime,
            warmup=read_warmup_summary(paths),
        )
        assert snapshot.status == "ok"
        assert snapshot.current_run_id == "run-shadow-vps-live-2026-04-27"
        assert snapshot.previous_run_id == "run-shadow-vps-live-2026-04-26"
        assert snapshot.engines_active_count_transition.current == 2
        assert snapshot.sample_warning == "SAMPLE_TOO_SMALL"
    finally:
        cleanup_scratch(scratch)


def test_run_comparison_falls_back_to_insufficient_history() -> None:
    scratch = scratch_dir("run_comparison_insufficient")
    try:
        paths = build_paths(scratch)
        seed_phase25_files(paths)
        previous_dir = paths.auto_exports_root / "2026-04-26"
        for child in previous_dir.iterdir():
            child.unlink()
        previous_dir.rmdir()
        runtime = read_runtime_surfaces(
            service_dir=paths.service_dir,
            queue_root=paths.dashboard_command_queue_root,
            observability_output_dir=paths.observability_output_dir,
            backtest_jobs_root=paths.backtest_jobs_root,
        )
        snapshot = read_run_comparison(
            paths.auto_exports_root,
            runtime=runtime,
            warmup=read_warmup_summary(paths),
        )
        assert snapshot.status == "insufficient_history"
    finally:
        cleanup_scratch(scratch)
