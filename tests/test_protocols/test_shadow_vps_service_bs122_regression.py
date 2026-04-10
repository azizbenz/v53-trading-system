"""
Regression tests — BS-122
ShadowVpsServiceStore must NOT silently reset on state corruption.
It must: backup the corrupted file, mark last_error, preserve evidence.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from protocols.shadow_vps_service import ShadowVpsServiceState, ShadowVpsServiceStore


def test_valid_state_loads_correctly(tmp_path: Path):
    """Sanity: valid state file loads without error."""
    store = ShadowVpsServiceStore(tmp_path)
    store._state.loop_count  # access to confirm no AttributeError
    store._state = ShadowVpsServiceState(loop_count=5, success_count=3)
    store.persist()

    store2 = ShadowVpsServiceStore(tmp_path)
    assert store2.state.loop_count == 5
    assert store2.state.success_count == 3


def test_corrupted_json_creates_backup(tmp_path: Path):
    """BS-122: corrupted JSON must be backed up, not silently dropped."""
    state_path = tmp_path / "shadow_vps_service.state.json"
    state_path.write_text("{ INVALID JSON !!!", encoding="utf-8")

    store = ShadowVpsServiceStore(tmp_path)

    backup = state_path.with_suffix(".corrupted")
    assert backup.exists(), "Corrupted file must be backed up as .corrupted"


def test_corrupted_state_marks_last_error(tmp_path: Path):
    """BS-122: fresh state after corruption must expose the error in last_error."""
    state_path = tmp_path / "shadow_vps_service.state.json"
    state_path.write_text("null", encoding="utf-8")

    store = ShadowVpsServiceStore(tmp_path)

    assert "corrupted" in store.state.last_error.lower(), (
        f"Expected 'corrupted' in last_error, got: {store.state.last_error!r}"
    )


def test_corrupted_state_resets_counters(tmp_path: Path):
    """After corruption recovery, counters start at zero."""
    state_path = tmp_path / "shadow_vps_service.state.json"
    state_path.write_text("{bad", encoding="utf-8")

    store = ShadowVpsServiceStore(tmp_path)

    assert store.state.loop_count == 0
    assert store.state.success_count == 0
    assert store.state.consecutive_days_completed == 0 if hasattr(store.state, "consecutive_days_completed") else True


def test_missing_state_file_returns_fresh_state(tmp_path: Path):
    """No state file → fresh state with no error marker."""
    store = ShadowVpsServiceStore(tmp_path)
    assert store.state.loop_count == 0
    assert store.state.last_error == ""


def test_truncated_json_creates_backup(tmp_path: Path):
    """Partial write (truncated JSON) must also be backed up."""
    state_path = tmp_path / "shadow_vps_service.state.json"
    state_path.write_text('{"loop_count": 5, "success_', encoding="utf-8")

    store = ShadowVpsServiceStore(tmp_path)

    backup = state_path.with_suffix(".corrupted")
    assert backup.exists()
    assert "corrupted" in store.state.last_error.lower()
