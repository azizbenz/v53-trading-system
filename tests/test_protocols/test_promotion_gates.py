"""Tests for protocols.promotion_gates — HARD STATEMENT §0.6."""

import pytest

from protocols.promotion_gates import (
    PromotionGateResult,
    check_all_gates,
    check_complete_to_live,
    check_light_to_micro_live,
)
from protocols.shadow_day_counter import ShadowDayCounter, ShadowProfile


pytestmark = pytest.mark.build1


BASE_TS = 1_700_000_000.0
ONE_DAY = 86_400.0


@pytest.fixture
def gate_dir(repo_tmp_path):
    return repo_tmp_path


def _fill_shadow_days(state_dir, profile: ShadowProfile, count: int):
    """Helper: record N consecutive passing shadow days."""
    c = ShadowDayCounter(state_dir=state_dir, profile=profile)
    for i in range(count):
        c.record_shadow_day(passed_all_gates=True, now=BASE_TS + i * ONE_DAY * 0.5)


class TestLightToMicroLive:
    """Light → Micro-live gate (30 days shadow)."""

    def test_rejects_with_zero_days(self, gate_dir):
        result = check_light_to_micro_live(gate_dir)
        assert result.passed is False
        assert result.consecutive_days == 0
        assert result.remaining_days == 30
        assert "BLOCKED" in result.message

    def test_rejects_with_29_days(self, gate_dir):
        _fill_shadow_days(gate_dir, ShadowProfile.LIGHT, 29)
        result = check_light_to_micro_live(gate_dir)
        assert result.passed is False
        assert result.remaining_days == 1
        assert "1 days remaining" in result.message

    def test_accepts_with_30_days(self, gate_dir):
        _fill_shadow_days(gate_dir, ShadowProfile.LIGHT, 30)
        result = check_light_to_micro_live(gate_dir)
        assert result.passed is True
        assert result.consecutive_days == 30
        assert result.remaining_days == 0
        assert result.message == "PASSED"

    def test_accepts_with_more_than_30_days(self, gate_dir):
        _fill_shadow_days(gate_dir, ShadowProfile.LIGHT, 35)
        result = check_light_to_micro_live(gate_dir)
        assert result.passed is True

    def test_gate_name(self, gate_dir):
        result = check_light_to_micro_live(gate_dir)
        assert result.gate_name == "light_shadow_30j"
        assert result.profile == "light"


class TestCompleteToLive:
    """Complete → Live gate (30 days shadow)."""

    def test_rejects_with_zero_days(self, gate_dir):
        result = check_complete_to_live(gate_dir)
        assert result.passed is False
        assert "BLOCKED" in result.message

    def test_rejects_with_15_days(self, gate_dir):
        _fill_shadow_days(gate_dir, ShadowProfile.COMPLETE, 15)
        result = check_complete_to_live(gate_dir)
        assert result.passed is False
        assert result.remaining_days == 15

    def test_accepts_with_30_days(self, gate_dir):
        _fill_shadow_days(gate_dir, ShadowProfile.COMPLETE, 30)
        result = check_complete_to_live(gate_dir)
        assert result.passed is True
        assert result.message == "PASSED"

    def test_gate_name(self, gate_dir):
        result = check_complete_to_live(gate_dir)
        assert result.gate_name == "complete_shadow_30j"
        assert result.profile == "complete"


class TestCheckAllGates:
    """Combined gate check."""

    def test_both_fail_with_empty_state(self, gate_dir):
        results = check_all_gates(gate_dir)
        assert len(results) == 2
        assert all(not r.passed for r in results)

    def test_light_passes_complete_fails(self, gate_dir):
        _fill_shadow_days(gate_dir, ShadowProfile.LIGHT, 30)
        results = check_all_gates(gate_dir)
        light_result = [r for r in results if r.profile == "light"][0]
        complete_result = [r for r in results if r.profile == "complete"][0]
        assert light_result.passed is True
        assert complete_result.passed is False

    def test_both_pass(self, gate_dir):
        _fill_shadow_days(gate_dir, ShadowProfile.LIGHT, 30)
        _fill_shadow_days(gate_dir, ShadowProfile.COMPLETE, 30)
        results = check_all_gates(gate_dir)
        assert all(r.passed for r in results)


class TestResetTracking:
    """Reset count visible in gate results."""

    def test_resets_tracked_in_result(self, gate_dir):
        c = ShadowDayCounter(state_dir=gate_dir, profile=ShadowProfile.LIGHT)
        c.record_shadow_day(passed_all_gates=True, now=BASE_TS)
        # Force gap > 24h
        c.record_shadow_day(passed_all_gates=True, now=BASE_TS + 200_000)
        result = check_light_to_micro_live(gate_dir)
        assert result.total_resets >= 1
