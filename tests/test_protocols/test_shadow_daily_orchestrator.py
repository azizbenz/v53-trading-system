"""Tests for the external daily Shadow orchestrator state."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
from uuid import uuid4

import pytest

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


def _write_session_summary(export_dir: Path, *, base_session_date: str, session_dates: tuple[str, ...]) -> None:
    (export_dir / "local_replay_shadow.shadow_session_summary.json").write_text(
        json.dumps(
            {
                "base_session_date": base_session_date,
                "session_dates": list(session_dates),
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def _write_session_registry(export_dir: Path, *, session_dates: tuple[str, ...]) -> None:
    (export_dir / "shadow_session_registry.json").write_text(
        json.dumps(
            {
                "entries": [
                    {
                        "session_date": session_date,
                        "counter_day_number": index + 1,
                        "correlation_id": f"corr-{index + 1}",
                        "run_id": "shadow-run-1",
                        "artifact_id": "artifact-1",
                        "lineage_version": "a.v1",
                    }
                    for index, session_date in enumerate(session_dates)
                ]
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def _write_run_manifest(export_dir: Path, *, timeframe_scope: str, start_timestamp_ms: int) -> None:
    (export_dir / "replay_run_manifest.json").write_text(
        json.dumps(
            {
                "timeframe_scope": timeframe_scope,
                "start_timestamp_ms": start_timestamp_ms,
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def test_shadow_daily_orchestrator_discovers_sorted_dated_export_dirs():
    output_dir = _scratch_dir("discover")

    try:
        exports_root = output_dir / "exports_root"
        slot_b = exports_root / "slot_b"
        slot_a = exports_root / "slot_a"
        invalid_slot = exports_root / "slot_invalid"
        slot_b.mkdir(parents=True)
        slot_a.mkdir(parents=True)
        invalid_slot.mkdir(parents=True)
        _write_session_summary(
            slot_b,
            base_session_date="2026-04-03",
            session_dates=("2026-04-03",),
        )
        _write_session_summary(
            slot_a,
            base_session_date="2026-04-01",
            session_dates=("2026-04-01",),
        )
        _write_session_summary(
            invalid_slot,
            base_session_date="not-a-date",
            session_dates=("not-a-date",),
        )

        orchestrator = ShadowDailyOrchestrator(output_dir)
        slots = orchestrator.discover_slots(exports_root)

        assert [slot.session_date for slot in slots] == ["2026-04-01", "2026-04-03"]
        assert slots[0].export_dir_ref.endswith("slot_a")
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_shadow_daily_orchestrator_selects_next_pending_slot_after_recorded_run():
    output_dir = _scratch_dir("select")

    try:
        exports_root = output_dir / "exports_root"
        first_export = exports_root / "shadow_run_a"
        second_export = exports_root / "shadow_run_b"
        first_export.mkdir(parents=True)
        second_export.mkdir(parents=True)
        _write_session_summary(
            first_export,
            base_session_date="2026-04-01",
            session_dates=("2026-04-01",),
        )
        _write_session_summary(
            second_export,
            base_session_date="2026-04-02",
            session_dates=("2026-04-02",),
        )

        orchestrator = ShadowDailyOrchestrator(output_dir)
        first_slot = orchestrator.select_next_slot(exports_root)
        assert first_slot is not None
        assert first_slot.session_date == "2026-04-01"

        orchestrator.record_execution(
            ShadowDailyExecutionRecord(
                session_date="2026-04-01",
                export_dir_ref=first_slot.export_dir_ref,
                shadow_output_dir_ref="build/shadow_session",
                local_replay_evidence_ref="build/local_replay_evidence.json",
                shadow_runtime_evidence_ref="build/shadow_runtime_evidence.json",
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


def test_shadow_daily_orchestrator_retries_uncounted_slot_until_shadow_day_is_recorded():
    output_dir = _scratch_dir("retry_uncounted")

    try:
        exports_root = output_dir / "exports_root"
        first_export = exports_root / "shadow_run_a"
        second_export = exports_root / "shadow_run_b"
        first_export.mkdir(parents=True)
        second_export.mkdir(parents=True)
        _write_session_summary(
            first_export,
            base_session_date="2026-04-01",
            session_dates=("2026-04-01",),
        )
        _write_session_summary(
            second_export,
            base_session_date="2026-04-02",
            session_dates=("2026-04-02",),
        )

        orchestrator = ShadowDailyOrchestrator(output_dir)
        first_slot = orchestrator.select_next_slot(exports_root)
        assert first_slot is not None
        assert first_slot.session_date == "2026-04-01"

        orchestrator.record_execution(
            ShadowDailyExecutionRecord(
                session_date="2026-04-01",
                export_dir_ref=first_slot.export_dir_ref,
                shadow_output_dir_ref="build/shadow_session",
                local_replay_evidence_ref="build/local_replay_evidence.json",
                shadow_runtime_evidence_ref="build/shadow_runtime_evidence.json",
                shadow_summary_ref="build/summary.json",
                shadow_report_ref="build/report.json",
                shadow_session_summary_ref="build/session_summary.json",
                shadow_session_registry_ref="build/session_registry.json",
                shadow_day_recorded=False,
                accepted=False,
                consecutive_days=0,
                remaining_days=30,
            )
        )

        retry_slot = orchestrator.select_next_slot(exports_root)
        assert retry_slot is not None
        assert retry_slot.session_date == "2026-04-01"

        orchestrator.record_execution(
            ShadowDailyExecutionRecord(
                session_date="2026-04-01",
                export_dir_ref=retry_slot.export_dir_ref,
                shadow_output_dir_ref="build/shadow_session",
                local_replay_evidence_ref="build/local_replay_evidence.json",
                shadow_runtime_evidence_ref="build/shadow_runtime_evidence.json",
                shadow_summary_ref="build/summary.json",
                shadow_report_ref="build/report.json",
                shadow_session_summary_ref="build/session_summary.json",
                shadow_session_registry_ref="build/session_registry.json",
                shadow_day_recorded=True,
                accepted=True,
                consecutive_days=1,
                remaining_days=29,
            )
        )

        next_slot = orchestrator.select_next_slot(exports_root)
        assert next_slot is not None
        assert next_slot.session_date == "2026-04-02"
        assert orchestrator.recorded_session_dates() == ("2026-04-01", "2026-04-01")
        assert orchestrator.completed_session_dates() == ("2026-04-01",)
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_shadow_daily_orchestrator_falls_back_to_registry_when_summary_is_absent():
    output_dir = _scratch_dir("registry_fallback")

    try:
        exports_root = output_dir / "exports_root"
        export_dir = exports_root / "shadow_run_registry_only"
        export_dir.mkdir(parents=True)
        _write_session_registry(
            export_dir,
            session_dates=("2026-04-05", "2026-04-06"),
        )

        orchestrator = ShadowDailyOrchestrator(output_dir)
        slots = orchestrator.discover_slots(exports_root)

        assert len(slots) == 1
        assert slots[0].session_date == "2026-04-05"
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_shadow_daily_orchestrator_falls_back_to_run_manifest_datetime_scope():
    output_dir = _scratch_dir("manifest_datetime_fallback")

    try:
        exports_root = output_dir / "exports_root"
        export_dir = exports_root / "shadow_run_manifest_only"
        export_dir.mkdir(parents=True)
        _write_run_manifest(
            export_dir,
            timeframe_scope="2023-11-14T22:13:20Z/2023-11-14T22:14:20Z",
            start_timestamp_ms=1_700_000_000_000,
        )

        orchestrator = ShadowDailyOrchestrator(output_dir)
        slots = orchestrator.discover_slots(exports_root)

        assert len(slots) == 1
        assert slots[0].session_date == "2023-11-14"
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_shadow_daily_orchestrator_rejects_mismatched_governed_slot_metadata():
    output_dir = _scratch_dir("metadata_mismatch")

    try:
        exports_root = output_dir / "exports_root"
        export_dir = exports_root / "shadow_run_mismatch"
        export_dir.mkdir(parents=True)
        _write_session_summary(
            export_dir,
            base_session_date="2026-04-05",
            session_dates=("2026-04-05",),
        )
        _write_session_registry(
            export_dir,
            session_dates=("2026-04-06",),
        )

        orchestrator = ShadowDailyOrchestrator(output_dir)

        with pytest.raises(
            ValueError,
            match="Shadow slot session_date mismatch across governed metadata sources",
        ):
            orchestrator.build_slot_from_export_dir(export_dir)
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
