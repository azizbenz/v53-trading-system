"""Tests for data_backbone.freshness_checker - Build-2."""
import pytest

from interface_contracts import RuntimeMode

from data_backbone.freshness_checker.last_update_tracker import LastUpdateTracker
from data_backbone.freshness_checker.age_calculator import (
    calculate_age,
    calculate_ages_for_pair,
)
from data_backbone.freshness_checker.stale_penalty_builder import compute_stale_penalty
from data_backbone.freshness_checker.stale_hard_guard import (
    StaleVerdict,
    evaluate_exchange_staleness,
    evaluate_staleness,
)
from data_backbone.freshness_checker.freshness_reporter import (
    FreshnessEvent,
    FreshnessReporter,
)


pytestmark = pytest.mark.build2


class TestLastUpdateTracker:
    def test_record_and_get(self):
        tracker = LastUpdateTracker()
        tracker.record_update("BTCUSDT", "trade", 100.0)
        assert tracker.get_last_update("BTCUSDT", "trade") == 100.0

    def test_none_if_never_updated(self):
        tracker = LastUpdateTracker()
        assert tracker.get_last_update("BTCUSDT", "trade") is None

    def test_overwrites_with_newer(self):
        tracker = LastUpdateTracker()
        tracker.record_update("BTCUSDT", "trade", 100.0)
        tracker.record_update("BTCUSDT", "trade", 105.0)
        assert tracker.get_last_update("BTCUSDT", "trade") == 105.0

    def test_get_record(self):
        tracker = LastUpdateTracker()
        tracker.record_update("BTCUSDT", "trade", 100.0)
        tracker.record_update("BTCUSDT", "trade", 101.0)
        record = tracker.get_record("BTCUSDT", "trade")
        assert record.update_count == 2

    def test_multi_stream(self):
        tracker = LastUpdateTracker()
        tracker.record_update("BTCUSDT", "trade", 100.0)
        tracker.record_update("BTCUSDT", "depth", 101.0)
        records = tracker.get_all_records()
        assert len(records) == 2


class TestAgeCalculator:
    def test_calculate_age(self):
        result = calculate_age("BTCUSDT", "trade", 100.0, 105.0)
        assert result.age_s == 5.0

    def test_calculate_ages_for_pair(self):
        results = calculate_ages_for_pair(
            "BTCUSDT", {"trade": 100.0, "depth": 102.0}, 110.0,
        )
        assert len(results) == 2
        ages = {r.stream_type: r.age_s for r in results}
        assert ages["trade"] == 10.0
        assert ages["depth"] == 8.0


class TestStalePenaltyBuilder:
    def test_fresh_no_penalty(self):
        result = compute_stale_penalty("BTC", "trade", age_s=3.0, threshold_s=5.0)
        assert result.penalty == 0.0

    def test_stale_penalty_grows(self):
        result = compute_stale_penalty(
            "BTC", "trade", age_s=10.0, threshold_s=5.0, lambda_factor=0.1,
        )
        assert result.penalty == pytest.approx(0.5)

    def test_exact_threshold_no_penalty(self):
        result = compute_stale_penalty("BTC", "trade", age_s=5.0, threshold_s=5.0)
        assert result.penalty == 0.0


class TestStaleHardGuard:
    def test_fresh(self):
        result = evaluate_staleness("BTC", "trade", 2.0, soft_threshold_s=5.0, hard_threshold_s=30.0)
        assert result.verdict == StaleVerdict.FRESH
        assert result.blocked is False

    def test_degraded(self):
        result = evaluate_staleness("BTC", "trade", 10.0, soft_threshold_s=5.0, hard_threshold_s=30.0)
        assert result.verdict == StaleVerdict.DEGRADED
        assert result.blocked is False

    def test_hard_stale(self):
        result = evaluate_staleness("BTC", "trade", 35.0, soft_threshold_s=5.0, hard_threshold_s=30.0)
        assert result.verdict == StaleVerdict.HARD_STALE
        assert result.blocked is True

    def test_recovery_after_fresh_update(self):
        result = evaluate_staleness("BTC", "trade", 1.0, soft_threshold_s=5.0, hard_threshold_s=30.0)
        assert result.verdict == StaleVerdict.FRESH

    def test_exchange_stale_shadow_is_logged_only(self):
        result = evaluate_exchange_staleness(
            "BTC",
            "trade",
            local_timestamp=100.5,
            exchange_timestamp=100.0,
            runtime_mode=RuntimeMode.SHADOW,
            stale_threshold_s=0.2,
        )
        assert result.verdict == StaleVerdict.DEGRADED
        assert result.blocked is False

    def test_exchange_stale_micro_live_is_blocking(self):
        result = evaluate_exchange_staleness(
            "BTC",
            "trade",
            local_timestamp=100.5,
            exchange_timestamp=100.0,
            runtime_mode=RuntimeMode.MICRO_LIVE,
            stale_threshold_s=0.2,
        )
        assert result.verdict == StaleVerdict.HARD_STALE
        assert result.blocked is True

    def test_exchange_stale_live_is_blocking(self):
        result = evaluate_exchange_staleness(
            "BTC",
            "trade",
            local_timestamp=100.5,
            exchange_timestamp=100.0,
            runtime_mode=RuntimeMode.LIVE,
            stale_threshold_s=0.2,
        )
        assert result.verdict == StaleVerdict.HARD_STALE
        assert result.blocked is True


class TestFreshnessReporter:
    def test_record_and_stats(self):
        reporter = FreshnessReporter()
        reporter.record(FreshnessEvent(pair="BTC", stream_type="trade", verdict=StaleVerdict.FRESH, age_s=1.0))
        reporter.record(FreshnessEvent(pair="ETH", stream_type="trade", verdict=StaleVerdict.HARD_STALE, age_s=50.0))
        stats = reporter.get_stats()
        assert stats.total_checks == 2
        assert stats.fresh_count == 1
        assert stats.hard_stale_count == 1
        assert stats.max_age_observed == 50.0

    def test_filter_by_pair(self):
        reporter = FreshnessReporter()
        reporter.record(FreshnessEvent(pair="BTC", stream_type="trade", verdict=StaleVerdict.FRESH, age_s=1.0))
        reporter.record(FreshnessEvent(pair="ETH", stream_type="trade", verdict=StaleVerdict.FRESH, age_s=2.0))
        assert len(reporter.get_events("BTC")) == 1
