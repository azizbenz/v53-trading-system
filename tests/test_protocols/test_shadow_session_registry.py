"""Tests for the governed Build-11 Shadow session registry."""

from __future__ import annotations

from pathlib import Path
import shutil
from uuid import uuid4

import pytest

from protocols import ShadowSessionEntry, ShadowSessionRegistry


def _scratch_dir(label: str) -> Path:
    from tests.support_paths import make_repo_scratch_dir

    return make_repo_scratch_dir("shadow_session_registry_tests", label)


def _entry(session_date: str, counter_day_number: int) -> ShadowSessionEntry:
    return ShadowSessionEntry(
        session_date=session_date,
        counter_day_number=counter_day_number,
        correlation_id=f"corr:{session_date}",
        run_id="shadow-run-1",
        artifact_id="artifact-shadow-1",
        lineage_version="a.v1.0.r1",
        day_record_ref=f"build/{session_date}.json",
        export_dir_ref="build/export",
    )


def test_shadow_session_registry_appends_unique_increasing_dates():
    output_dir = _scratch_dir("append")

    try:
        registry = ShadowSessionRegistry(output_dir)
        registry.append_entries(
            (
                _entry("2026-04-01", 1),
                _entry("2026-04-02", 2),
            )
        )

        entries = registry.get_entries()
        assert len(entries) == 2
        assert entries[0].session_date == "2026-04-01"
        assert entries[1].session_date == "2026-04-02"
        assert registry.last_session_date().isoformat() == "2026-04-02"
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_shadow_session_registry_rejects_duplicate_existing_dates():
    output_dir = _scratch_dir("duplicate")

    try:
        registry = ShadowSessionRegistry(output_dir)
        registry.append_entries((_entry("2026-04-01", 1),))

        with pytest.raises(ValueError, match="already recorded session_date"):
            registry.append_entries((_entry("2026-04-01", 2),))

        entries = registry.get_entries()
        assert len(entries) == 1
        assert entries[0].counter_day_number == 1
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_shadow_session_registry_rejects_non_increasing_batch_dates():
    output_dir = _scratch_dir("ordering")

    try:
        registry = ShadowSessionRegistry(output_dir)

        with pytest.raises(ValueError, match="strictly increasing session_date"):
            registry.validate_session_dates(("2026-04-03", "2026-04-02"))
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
