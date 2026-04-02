"""Tests for the external daily Shadow orchestrator state."""

from __future__ import annotations

from pathlib import Path
import shutil
from uuid import uuid4

from protocols import (
    ShadowDailyExecutionRecord,
    ShadowDailyOrchestrator,
)


def _scratch_dir(label: str) -> Path:
    repo_root = Path(__file__).resolve().parents[2]
    base_dir = repo_root / "build" / "shadow_daily_orchestrator_tests"
    base_dir.mkdir(parents=True, exist_ok=True)
    output_dir = base_dir / f"{label}_{uuid4().hex}"
    output_dir.mkdir(parents=True, exist_ok=False)
    return output_dir


def test_shadow_daily_orchestrator_discovers_sorted_dated_export_dirs():
    output_dir = _scratch_dir("discover")

    try:
        exports_root = output_dir / "exports_root"
        (exports_root / "2026-04-03").mkdir(parents=True)
        (exports_root / "2026-04-01").mkdir(parents=True)
        (exports_root / "not-a-date").mkdir(parents=True)

        orchestrator = ShadowDailyOrchestrator(output_dir)
        slots = orchestrator.discover_slots(exports_root)

        assert [slot.session_date for slot in slots] == ["2026-04-01", "2026-04-03"]
        assert slots[0].export_dir_ref.endswith("2026-04-01")
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_shadow_daily_orchestrator_selects_next_pending_slot_after_recorded_run():
    output_dir = _scratch_dir("select")

    try:
        exports_root = output_dir / "exports_root"
        (exports_root / "2026-04-01").mkdir(parents=True)
        (exports_root / "2026-04-02").mkdir(parents=True)

        orchestrator = ShadowDailyOrchestrator(output_dir)
        first_slot = orchestrator.select_next_slot(exports_root)
        assert first_slot is not None
        assert first_slot.session_date == "2026-04-01"

        orchestrator.record_execution(
            ShadowDailyExecutionRecord(
                session_date="2026-04-01",
                export_dir_ref=first_slot.export_dir_ref,
                shadow_output_dir_ref="build/shadow_session",
                shadow_summary_ref="build/summary.json",
                shadow_report_ref="build/report.json",
                shadow_session_summary_ref="build/session_summary.json",
                shadow_session_registry_ref="build/session_registry.json",
                accepted=True,
                consecutive_days=1,
                remaining_days=29,
            )
        )

        next_slot = orchestrator.select_next_slot(exports_root)
        assert next_slot is not None
        assert next_slot.session_date == "2026-04-02"
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
