"""Tests for risk_backbone.emergency_kill_switch.circuit_breaker — GEM-10/QWEN-07."""

import json
import pytest

from risk_backbone.emergency_kill_switch.circuit_breaker import (
    EmergencyCircuitBreaker,
    KillSwitchReason,
    KillSwitchRecord,
    KillSwitchState,
)


pytestmark = pytest.mark.build1


@pytest.fixture
def ks_dir(tmp_path):
    return tmp_path


class TestKillSwitchTrip:
    """Trip behavior and persistence."""

    def test_initial_state_armed(self, ks_dir):
        cb = EmergencyCircuitBreaker(state_dir=ks_dir)
        assert cb.current_state == KillSwitchState.ARMED
        assert cb.is_trading_allowed() is True

    def test_trip_blocks_trading(self, ks_dir):
        cb = EmergencyCircuitBreaker(state_dir=ks_dir)
        record = cb.trip(KillSwitchReason.LOSS_BUDGET_BREACH, "test trip")
        assert cb.is_trading_allowed() is False
        assert cb.current_state == KillSwitchState.TRIPPED
        assert record.state == KillSwitchState.TRIPPED
        assert record.reason == KillSwitchReason.LOSS_BUDGET_BREACH

    def test_trip_persists_to_disk(self, ks_dir):
        cb = EmergencyCircuitBreaker(state_dir=ks_dir)
        cb.trip(KillSwitchReason.CRITICAL_DIVERGENCE, "persist test")
        state_file = ks_dir / "kill_switch_state.json"
        assert state_file.exists()
        data = json.loads(state_file.read_text(encoding="utf-8"))
        assert data["state"] == "tripped"
        assert data["reason"] == "critical_divergence"

    def test_trip_records_timestamp(self, ks_dir):
        cb = EmergencyCircuitBreaker(state_dir=ks_dir)
        cb.trip(KillSwitchReason.DATA_CORRUPTION)
        assert cb.tripped_at is not None
        assert cb.tripped_at > 0


class TestKillSwitchRestore:
    """Reload / restart persistence verification."""

    def test_reload_restores_tripped_state(self, ks_dir):
        cb1 = EmergencyCircuitBreaker(state_dir=ks_dir)
        cb1.trip(KillSwitchReason.LOSS_BUDGET_BREACH, "test")
        # Simulate restart: new instance same dir
        cb2 = EmergencyCircuitBreaker(state_dir=ks_dir)
        assert cb2.is_trading_allowed() is False
        assert cb2.current_state == KillSwitchState.TRIPPED
        assert cb2.current_reason == KillSwitchReason.LOSS_BUDGET_BREACH

    def test_reload_armed_state_stays_armed(self, ks_dir):
        cb1 = EmergencyCircuitBreaker(state_dir=ks_dir)
        # No trip — just persist via internal state
        cb2 = EmergencyCircuitBreaker(state_dir=ks_dir)
        assert cb2.is_trading_allowed() is True

    def test_corrupted_state_file_assumes_tripped(self, ks_dir):
        """Safety invariant: corrupted state = assume tripped."""
        state_file = ks_dir / "kill_switch_state.json"
        state_file.write_text("NOT VALID JSON!!!", encoding="utf-8")
        cb = EmergencyCircuitBreaker(state_dir=ks_dir)
        assert cb.is_trading_allowed() is False
        assert cb.current_state == KillSwitchState.TRIPPED
        assert cb.current_reason == KillSwitchReason.DATA_CORRUPTION

    def test_multiple_restart_cycles(self, ks_dir):
        """Trip → restart → still tripped → reset → restart → armed."""
        cb1 = EmergencyCircuitBreaker(state_dir=ks_dir)
        cb1.trip(KillSwitchReason.CRITICAL_DIVERGENCE)
        # Restart 1: still tripped
        cb2 = EmergencyCircuitBreaker(state_dir=ks_dir)
        assert cb2.is_trading_allowed() is False
        # Reset
        cb2.reset("operator approved")
        # Restart 2: should be armed
        cb3 = EmergencyCircuitBreaker(state_dir=ks_dir)
        assert cb3.is_trading_allowed() is True


class TestExternalFileFlag:
    """External KILL_SWITCH_ACTIVE file detection."""

    def test_external_flag_trips_on_init(self, ks_dir):
        flag_file = ks_dir / "KILL_SWITCH_ACTIVE"
        flag_file.write_text("operator kill", encoding="utf-8")
        cb = EmergencyCircuitBreaker(state_dir=ks_dir)
        assert cb.is_trading_allowed() is False
        assert cb.current_reason == KillSwitchReason.EXTERNAL_FILE_FLAG

    def test_external_flag_trips_on_check(self, ks_dir):
        cb = EmergencyCircuitBreaker(state_dir=ks_dir)
        assert cb.is_trading_allowed() is True
        # Create flag file after init
        flag_file = ks_dir / "KILL_SWITCH_ACTIVE"
        flag_file.write_text("", encoding="utf-8")
        assert cb.is_trading_allowed() is False

    def test_reset_removes_external_flag(self, ks_dir):
        flag_file = ks_dir / "KILL_SWITCH_ACTIVE"
        flag_file.write_text("", encoding="utf-8")
        cb = EmergencyCircuitBreaker(state_dir=ks_dir)
        assert cb.is_trading_allowed() is False
        cb.reset("cleared by operator")
        assert not flag_file.exists()
        assert cb.is_trading_allowed() is True


class TestKillSwitchReset:
    """Reset behavior."""

    def test_reset_allows_trading(self, ks_dir):
        cb = EmergencyCircuitBreaker(state_dir=ks_dir)
        cb.trip(KillSwitchReason.LOSS_BUDGET_BREACH)
        assert cb.is_trading_allowed() is False
        record = cb.reset("test reset")
        assert cb.is_trading_allowed() is True
        assert record.state == KillSwitchState.ARMED

    def test_reset_persists(self, ks_dir):
        cb = EmergencyCircuitBreaker(state_dir=ks_dir)
        cb.trip(KillSwitchReason.LOSS_BUDGET_BREACH)
        cb.reset("test")
        # Reload
        cb2 = EmergencyCircuitBreaker(state_dir=ks_dir)
        assert cb2.is_trading_allowed() is True

    def test_history_tracks_events(self, ks_dir):
        cb = EmergencyCircuitBreaker(state_dir=ks_dir)
        cb.trip(KillSwitchReason.LOSS_BUDGET_BREACH)
        cb.reset("cleared")
        history = cb.get_history()
        assert len(history) == 2
        assert history[0].state == KillSwitchState.TRIPPED
        assert history[1].state == KillSwitchState.ARMED
