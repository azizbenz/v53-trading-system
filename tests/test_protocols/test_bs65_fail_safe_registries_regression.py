"""
BS-65 regression tests — fail-safe on corruption for 4 shadow registries.

Before fix: json.JSONDecodeError / invalid data → silent reset to zero.
After fix:  corrupted file → backup (.corrupted) + last_error marker set.

Covers:
- ShadowDayCounter (shadow_day_counter.py)
- ShadowDailyOrchestrator (shadow_daily_orchestrator.py)
- ShadowSessionRegistry (shadow_session_registry.py)
- ShadowRuntimeEvidenceRecorder (shadow_runtime_evidence.py)
"""

from __future__ import annotations

import json

import pytest

from protocols.shadow_day_counter import ShadowDayCounter, ShadowProfile
from protocols.shadow_daily_orchestrator import ShadowDailyOrchestrator
from protocols.shadow_runtime_evidence import ShadowRuntimeEvidenceRecorder, ShadowRuntimeEvidenceRecorderConfig
from protocols.shadow_session_registry import ShadowSessionRegistry


BASE_TS = 1_700_000_000.0
ONE_DAY = 86_400.0


# ===========================================================================
# ShadowDayCounter — BS-65
# ===========================================================================

class TestShadowDayCounterFailSafe:

    def test_corrupted_json_sets_last_error(self, repo_tmp_path):
        """BS-65: JSONDecodeError on load must set last_error, not silently reset."""
        state_file = repo_tmp_path / "shadow_counter_complete.json"
        state_file.write_text("{ not valid json }", encoding="utf-8")

        counter = ShadowDayCounter(state_dir=repo_tmp_path, profile=ShadowProfile.COMPLETE)

        assert counter._state.last_error is not None
        assert "state_file_corrupted" in counter._state.last_error

    def test_corrupted_json_creates_backup(self, repo_tmp_path):
        """BS-65: Corrupted file must be renamed to .corrupted for forensics."""
        state_file = repo_tmp_path / "shadow_counter_complete.json"
        state_file.write_text("{{{{broken", encoding="utf-8")

        ShadowDayCounter(state_dir=repo_tmp_path, profile=ShadowProfile.COMPLETE)

        backup = repo_tmp_path / "shadow_counter_complete.corrupted"
        assert backup.exists(), "Backup .corrupted file must be created"
        assert not state_file.exists(), "Original corrupted file must be removed"

    def test_non_dict_json_sets_last_error(self, repo_tmp_path):
        """BS-65: JSON root that is not a dict (e.g. null, list) must be treated as corruption."""
        state_file = repo_tmp_path / "shadow_counter_complete.json"
        state_file.write_text("null", encoding="utf-8")

        counter = ShadowDayCounter(state_dir=repo_tmp_path, profile=ShadowProfile.COMPLETE)

        assert counter._state.last_error is not None
        assert counter._state.consecutive_days == 0

    def test_corrupted_state_has_zero_consecutive_days(self, repo_tmp_path):
        """BS-65: After corruption reset, counter starts from 0 — no phantom days inherited."""
        state_file = repo_tmp_path / "shadow_counter_complete.json"
        state_file.write_text("CORRUPTED", encoding="utf-8")

        counter = ShadowDayCounter(state_dir=repo_tmp_path, profile=ShadowProfile.COMPLETE)

        assert counter._state.consecutive_days == 0

    def test_valid_state_loads_normally(self, repo_tmp_path):
        """BS-65: Valid state file must not be touched — normal load path unchanged."""
        counter = ShadowDayCounter(state_dir=repo_tmp_path, profile=ShadowProfile.COMPLETE)
        counter.record_shadow_day(passed_all_gates=True, now=BASE_TS)
        counter.record_shadow_day(passed_all_gates=True, now=BASE_TS + ONE_DAY * 0.5)

        # Reload
        counter2 = ShadowDayCounter(state_dir=repo_tmp_path, profile=ShadowProfile.COMPLETE)

        assert counter2._state.last_error is None
        assert counter2._state.consecutive_days == 2


# ===========================================================================
# ShadowDailyOrchestrator — BS-65
# ===========================================================================

class TestShadowDailyOrchestratorFailSafe:

    def test_corrupted_json_sets_last_error(self, repo_tmp_path):
        """BS-65: JSONDecodeError on load must set last_error marker."""
        state_file = repo_tmp_path / "shadow_daily_orchestrator.state.json"
        state_file.write_text("not json at all", encoding="utf-8")

        orch = ShadowDailyOrchestrator(state_dir=repo_tmp_path)

        assert orch._state.last_error is not None
        assert "state_file_corrupted" in orch._state.last_error

    def test_corrupted_json_creates_backup(self, repo_tmp_path):
        """BS-65: Corrupted orchestrator state must be backed up."""
        state_file = repo_tmp_path / "shadow_daily_orchestrator.state.json"
        state_file.write_text("[1,2,3]", encoding="utf-8")  # valid JSON but not a dict

        ShadowDailyOrchestrator(state_dir=repo_tmp_path)

        backup = repo_tmp_path / "shadow_daily_orchestrator.state.corrupted"
        assert backup.exists()

    def test_corrupted_state_has_empty_runs(self, repo_tmp_path):
        """BS-65: After corruption, completed_runs starts empty — no phantom history."""
        state_file = repo_tmp_path / "shadow_daily_orchestrator.state.json"
        state_file.write_text("{{{", encoding="utf-8")

        orch = ShadowDailyOrchestrator(state_dir=repo_tmp_path)

        assert orch.get_completed_runs() == ()

    def test_valid_state_loads_normally(self, repo_tmp_path):
        """BS-65: Valid state must load without error marker."""
        orch = ShadowDailyOrchestrator(state_dir=repo_tmp_path)
        # Reload fresh (no completed runs yet)
        orch2 = ShadowDailyOrchestrator(state_dir=repo_tmp_path)

        assert orch2._state.last_error is None


# ===========================================================================
# ShadowSessionRegistry — BS-65
# ===========================================================================

class TestShadowSessionRegistryFailSafe:

    def test_corrupted_json_sets_last_error(self, repo_tmp_path):
        """BS-65: JSONDecodeError on load must set last_error marker."""
        state_file = repo_tmp_path / "shadow_session_registry.json"
        state_file.write_text("!!invalid!!", encoding="utf-8")

        registry = ShadowSessionRegistry(state_dir=repo_tmp_path)

        assert registry._state.last_error is not None
        assert "state_file_corrupted" in registry._state.last_error

    def test_corrupted_json_creates_backup(self, repo_tmp_path):
        """BS-65: Corrupted registry file must be backed up."""
        state_file = repo_tmp_path / "shadow_session_registry.json"
        state_file.write_text("null", encoding="utf-8")

        ShadowSessionRegistry(state_dir=repo_tmp_path)

        backup = repo_tmp_path / "shadow_session_registry.corrupted"
        assert backup.exists()

    def test_corrupted_state_has_empty_entries(self, repo_tmp_path):
        """BS-65: After corruption, entries starts empty — no phantom sessions."""
        state_file = repo_tmp_path / "shadow_session_registry.json"
        state_file.write_text("true", encoding="utf-8")  # valid JSON, not a dict

        registry = ShadowSessionRegistry(state_dir=repo_tmp_path)

        assert registry.get_entries() == ()

    def test_valid_state_loads_normally(self, repo_tmp_path):
        """BS-65: Valid state must load without error marker."""
        registry = ShadowSessionRegistry(state_dir=repo_tmp_path)
        registry2 = ShadowSessionRegistry(state_dir=repo_tmp_path)

        assert registry2._state.last_error is None


# ===========================================================================
# ShadowRuntimeEvidenceRecorder — BS-65
# ===========================================================================

class TestShadowRuntimeEvidenceRecorderFailSafe:

    def _recorder(self, state_dir) -> ShadowRuntimeEvidenceRecorder:
        return ShadowRuntimeEvidenceRecorder(
            config=ShadowRuntimeEvidenceRecorderConfig(
                state_dir=state_dir,
                persist_state=True,
            )
        )

    def test_corrupted_json_sets_last_error(self, repo_tmp_path):
        """BS-65: JSONDecodeError on load must set last_error marker."""
        state_file = repo_tmp_path / "shadow_runtime_evidence.json"
        state_file.write_text("{{not json}}", encoding="utf-8")

        recorder = self._recorder(repo_tmp_path)

        assert recorder._state.last_error is not None
        assert "state_file_corrupted" in recorder._state.last_error

    def test_corrupted_json_creates_backup(self, repo_tmp_path):
        """BS-65: Corrupted evidence file must be backed up."""
        state_file = repo_tmp_path / "shadow_runtime_evidence.json"
        state_file.write_text("[1, 2, 3]", encoding="utf-8")  # list, not dict

        self._recorder(repo_tmp_path)

        backup = repo_tmp_path / "shadow_runtime_evidence.corrupted"
        assert backup.exists()
        assert not state_file.exists()

    def test_non_dict_json_sets_last_error(self, repo_tmp_path):
        """BS-65: JSON root that is not a dict must be treated as corruption."""
        state_file = repo_tmp_path / "shadow_runtime_evidence.json"
        state_file.write_text("true", encoding="utf-8")

        recorder = self._recorder(repo_tmp_path)

        assert recorder._state.last_error is not None

    def test_corrupted_state_has_default_field_values(self, repo_tmp_path):
        """BS-65: After corruption, state starts with defaults — no phantom evidence."""
        state_file = repo_tmp_path / "shadow_runtime_evidence.json"
        state_file.write_text("GARBAGE", encoding="utf-8")

        recorder = self._recorder(repo_tmp_path)

        assert recorder._state.runtime_event_loop_tick_count == 0
        assert recorder._state.runtime_config_loaded is False
        assert recorder._state.runtime_shadow_dtr_persisted is False

    def test_valid_state_loads_normally(self, repo_tmp_path):
        """BS-65: Valid state must load without error marker."""
        # Create a fresh recorder (no state file yet) — loads defaults, no error
        recorder = self._recorder(repo_tmp_path)

        assert recorder._state.last_error is None
