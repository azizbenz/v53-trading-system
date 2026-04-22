"""
Regression tests - BS-122
ShadowVpsServiceStore must NOT silently reset on state corruption.
It must: backup the corrupted file, mark last_error, preserve evidence.
"""
from __future__ import annotations

import shutil
from pathlib import Path

from protocols.shadow_vps_service import ShadowVpsServiceState, ShadowVpsServiceStore
from tests.support_paths import make_repo_scratch_dir


def _scratch_dir(label: str) -> Path:
    return make_repo_scratch_dir("pytest-shadow-vps-service-bs122", label)


def test_valid_state_loads_correctly() -> None:
    """Sanity: valid state file loads without error."""
    output_dir = _scratch_dir("valid")
    try:
        store = ShadowVpsServiceStore(output_dir)
        store._state.loop_count  # access to confirm no AttributeError
        store._state = ShadowVpsServiceState(loop_count=5, success_count=3)
        store.persist()

        store2 = ShadowVpsServiceStore(output_dir)
        assert store2.state.loop_count == 5
        assert store2.state.success_count == 3
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_corrupted_json_creates_backup() -> None:
    """BS-122: corrupted JSON must be backed up, not silently dropped."""
    output_dir = _scratch_dir("corrupted_backup")
    try:
        state_path = output_dir / "shadow_vps_service.state.json"
        state_path.write_text("{ INVALID JSON !!!", encoding="utf-8")

        ShadowVpsServiceStore(output_dir)

        backup = state_path.with_suffix(".corrupted")
        assert backup.exists(), "Corrupted file must be backed up as .corrupted"
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_corrupted_state_marks_last_error() -> None:
    """BS-122: fresh state after corruption must expose the error in last_error."""
    output_dir = _scratch_dir("corrupted_last_error")
    try:
        state_path = output_dir / "shadow_vps_service.state.json"
        state_path.write_text("null", encoding="utf-8")

        store = ShadowVpsServiceStore(output_dir)

        assert "corrupted" in store.state.last_error.lower(), (
            f"Expected 'corrupted' in last_error, got: {store.state.last_error!r}"
        )
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_corrupted_state_resets_counters() -> None:
    """After corruption recovery, counters start at zero."""
    output_dir = _scratch_dir("corrupted_reset")
    try:
        state_path = output_dir / "shadow_vps_service.state.json"
        state_path.write_text("{bad", encoding="utf-8")

        store = ShadowVpsServiceStore(output_dir)

        assert store.state.loop_count == 0
        assert store.state.success_count == 0
        assert (
            store.state.consecutive_days_completed == 0
            if hasattr(store.state, "consecutive_days_completed")
            else True
        )
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_missing_state_file_returns_fresh_state() -> None:
    """No state file -> fresh state with no error marker."""
    output_dir = _scratch_dir("missing")
    try:
        store = ShadowVpsServiceStore(output_dir)
        assert store.state.loop_count == 0
        assert store.state.last_error == ""
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_truncated_json_creates_backup() -> None:
    """Partial write (truncated JSON) must also be backed up."""
    output_dir = _scratch_dir("truncated")
    try:
        state_path = output_dir / "shadow_vps_service.state.json"
        state_path.write_text('{"loop_count": 5, "success_', encoding="utf-8")

        store = ShadowVpsServiceStore(output_dir)

        backup = state_path.with_suffix(".corrupted")
        assert backup.exists()
        assert "corrupted" in store.state.last_error.lower()
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
