"""Tests for protocols.shadow_day_counter — HARD STATEMENT §0.6."""

import json
import pytest

from protocols.shadow_day_counter import (
    ShadowCounterState,
    ShadowDayCounter,
    ShadowDayRecord,
    ShadowProfile,
    _MAX_GAP_SECONDS,
)


pytestmark = pytest.mark.build1


BASE_TS = 1_700_000_000.0  # Reference timestamp
ONE_DAY = 86_400.0


@pytest.fixture
def counter_dir(repo_tmp_path):
    return repo_tmp_path


class TestDayCountIncrement:
    """Correct day counting."""

    def test_first_day_increments_to_1(self, counter_dir):
        c = ShadowDayCounter(state_dir=counter_dir, profile=ShadowProfile.LIGHT)
        rec = c.record_shadow_day(passed_all_gates=True, now=BASE_TS)
        assert rec.day_number == 1
        assert rec.passed_all_gates is True
        assert c.get_status().consecutive_days == 1

    def test_consecutive_days_increment(self, counter_dir):
        c = ShadowDayCounter(state_dir=counter_dir, profile=ShadowProfile.LIGHT)
        for i in range(5):
            c.record_shadow_day(passed_all_gates=True, now=BASE_TS + i * ONE_DAY * 0.9)
        assert c.get_status().consecutive_days == 5

    def test_failed_gate_does_not_count(self, counter_dir):
        c = ShadowDayCounter(state_dir=counter_dir, profile=ShadowProfile.LIGHT)
        c.record_shadow_day(passed_all_gates=True, now=BASE_TS)
        rec = c.record_shadow_day(passed_all_gates=False, now=BASE_TS + ONE_DAY * 0.5)
        assert rec.passed_all_gates is False
        assert c.get_status().consecutive_days == 1  # unchanged

    def test_30_days_reaches_promotion(self, counter_dir):
        c = ShadowDayCounter(state_dir=counter_dir, profile=ShadowProfile.LIGHT)
        for i in range(30):
            c.record_shadow_day(passed_all_gates=True, now=BASE_TS + i * ONE_DAY * 0.9)
        assert c.is_promotion_ready() is True
        assert c.get_status().remaining_days == 0

    def test_29_days_not_ready(self, counter_dir):
        c = ShadowDayCounter(state_dir=counter_dir, profile=ShadowProfile.LIGHT)
        for i in range(29):
            c.record_shadow_day(passed_all_gates=True, now=BASE_TS + i * ONE_DAY * 0.9)
        assert c.is_promotion_ready() is False
        assert c.get_status().remaining_days == 1


class TestGapReset:
    """24h gap resets counter — HARD STATEMENT."""

    def test_gap_over_24h_resets(self, counter_dir):
        c = ShadowDayCounter(state_dir=counter_dir, profile=ShadowProfile.LIGHT)
        c.record_shadow_day(passed_all_gates=True, now=BASE_TS)
        c.record_shadow_day(passed_all_gates=True, now=BASE_TS + ONE_DAY * 0.5)
        assert c.get_status().consecutive_days == 2
        # Gap > 24h
        c.record_shadow_day(passed_all_gates=True, now=BASE_TS + ONE_DAY * 3)
        assert c.get_status().consecutive_days == 1  # reset then +1
        assert c.get_status().resets == 1

    def test_exactly_24h_does_not_reset(self, counter_dir):
        c = ShadowDayCounter(state_dir=counter_dir, profile=ShadowProfile.LIGHT)
        c.record_shadow_day(passed_all_gates=True, now=BASE_TS)
        # Exactly 24h gap is NOT > 24h
        c.record_shadow_day(passed_all_gates=True, now=BASE_TS + _MAX_GAP_SECONDS)
        assert c.get_status().consecutive_days == 2
        assert c.get_status().resets == 0

    def test_just_over_24h_resets(self, counter_dir):
        c = ShadowDayCounter(state_dir=counter_dir, profile=ShadowProfile.LIGHT)
        c.record_shadow_day(passed_all_gates=True, now=BASE_TS)
        # 24h + 1 second
        c.record_shadow_day(passed_all_gates=True, now=BASE_TS + _MAX_GAP_SECONDS + 1)
        assert c.get_status().consecutive_days == 1
        assert c.get_status().resets == 1

    def test_multiple_resets_tracked(self, counter_dir):
        c = ShadowDayCounter(state_dir=counter_dir, profile=ShadowProfile.LIGHT)
        for reset_round in range(3):
            c.record_shadow_day(passed_all_gates=True, now=BASE_TS + reset_round * ONE_DAY * 5)
        assert c.get_status().resets == 2  # 2 gaps > 24h


class TestPersistence:
    """State survives restart."""

    def test_persist_and_reload(self, counter_dir):
        c1 = ShadowDayCounter(state_dir=counter_dir, profile=ShadowProfile.LIGHT)
        for i in range(10):
            c1.record_shadow_day(passed_all_gates=True, now=BASE_TS + i * ONE_DAY * 0.5)
        # Simulate restart
        c2 = ShadowDayCounter(state_dir=counter_dir, profile=ShadowProfile.LIGHT)
        assert c2.get_status().consecutive_days == 10

    def test_state_file_is_valid_json(self, counter_dir):
        c = ShadowDayCounter(state_dir=counter_dir, profile=ShadowProfile.LIGHT)
        c.record_shadow_day(passed_all_gates=True, now=BASE_TS)
        state_file = counter_dir / "shadow_counter_light.json"
        assert state_file.exists()
        data = json.loads(state_file.read_text(encoding="utf-8"))
        assert data["consecutive_days"] == 1
        assert data["profile"] == "light"

    def test_complete_profile_separate_file(self, counter_dir):
        c_light = ShadowDayCounter(state_dir=counter_dir, profile=ShadowProfile.LIGHT)
        c_complete = ShadowDayCounter(state_dir=counter_dir, profile=ShadowProfile.COMPLETE)
        c_light.record_shadow_day(passed_all_gates=True, now=BASE_TS)
        c_complete.record_shadow_day(passed_all_gates=True, now=BASE_TS)
        c_complete.record_shadow_day(passed_all_gates=True, now=BASE_TS + 1000)
        assert c_light.get_status().consecutive_days == 1
        assert c_complete.get_status().consecutive_days == 2

    def test_corrupted_state_starts_fresh(self, counter_dir):
        state_file = counter_dir / "shadow_counter_light.json"
        state_file.write_text("CORRUPTED!!!", encoding="utf-8")
        c = ShadowDayCounter(state_dir=counter_dir, profile=ShadowProfile.LIGHT)
        assert c.get_status().consecutive_days == 0


class TestReport:
    """Report generation."""

    def test_generate_report_structure(self, counter_dir):
        c = ShadowDayCounter(state_dir=counter_dir, profile=ShadowProfile.LIGHT)
        c.record_shadow_day(passed_all_gates=True, now=BASE_TS)
        report = c.generate_report()
        assert report["profile"] == "light"
        assert report["consecutive_days"] == 1
        assert report["required_days"] == 30
        assert report["remaining_days"] == 29
        assert report["is_complete"] is False

    def test_save_report_creates_file(self, counter_dir):
        c = ShadowDayCounter(state_dir=counter_dir, profile=ShadowProfile.LIGHT)
        c.record_shadow_day(passed_all_gates=True, now=BASE_TS)
        report_path = c.save_report()
        assert report_path.exists()
        data = json.loads(report_path.read_text(encoding="utf-8"))
        assert data["consecutive_days"] == 1

    def test_report_at_30_days_shows_complete(self, counter_dir):
        c = ShadowDayCounter(state_dir=counter_dir, profile=ShadowProfile.COMPLETE)
        for i in range(30):
            c.record_shadow_day(passed_all_gates=True, now=BASE_TS + i * ONE_DAY * 0.5)
        report = c.generate_report()
        assert report["is_complete"] is True
        assert report["remaining_days"] == 0


class TestMetricsSummary:
    """Metrics recording in day records."""

    def test_metrics_recorded_in_day(self, counter_dir):
        c = ShadowDayCounter(state_dir=counter_dir, profile=ShadowProfile.LIGHT)
        metrics = {"pnl": 0.02, "sharpe": 1.5}
        rec = c.record_shadow_day(passed_all_gates=True, metrics_summary=metrics, now=BASE_TS)
        assert rec.metrics_summary == metrics
