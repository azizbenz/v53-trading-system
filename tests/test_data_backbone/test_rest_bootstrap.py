"""Tests for data_backbone.rest_bootstrap — Build-2."""
import pytest

from data_backbone.rest_bootstrap.snapshot_fetcher import (
    Snapshot,
    SnapshotStatus,
    validate_snapshot_age,
)
from data_backbone.rest_bootstrap.rate_limit_guard import RateLimitGuard
from data_backbone.rest_bootstrap.gap_fill_controller import (
    GapFillDecision,
    evaluate_gap_fill,
)
from data_backbone.rest_bootstrap.bootstrap_reporter import (
    BootstrapEvent,
    BootstrapOutcome,
    BootstrapReporter,
)


pytestmark = pytest.mark.build2


# --- Snapshot Age Validator ---

class TestSnapshotAgeValidator:
    def _snap(self, fetch_time=100.0, exchange_time=None):
        return Snapshot(
            pair="BTCUSDT",
            data_type="orderbook",
            payload={"bids": [], "asks": []},
            fetch_time=fetch_time,
            exchange_time=exchange_time,
        )

    def test_valid_snapshot(self):
        snap = self._snap(fetch_time=100.0)
        result = validate_snapshot_age(snap, max_age_s=10.0, now=105.0)
        assert result.status == SnapshotStatus.VALID
        assert result.age_s == 5.0

    def test_too_old_snapshot(self):
        snap = self._snap(fetch_time=100.0)
        result = validate_snapshot_age(snap, max_age_s=10.0, now=115.0)
        assert result.status == SnapshotStatus.TOO_OLD
        assert result.age_s == 15.0

    def test_uses_exchange_time_when_available(self):
        snap = self._snap(fetch_time=100.0, exchange_time=98.0)
        result = validate_snapshot_age(snap, max_age_s=10.0, now=105.0)
        assert result.age_s == 7.0  # 105 - 98

    def test_boundary_exact(self):
        snap = self._snap(fetch_time=100.0)
        result = validate_snapshot_age(snap, max_age_s=10.0, now=110.0)
        assert result.status == SnapshotStatus.VALID  # exactly at boundary


# --- RateLimitGuard ---

class TestRateLimitGuard:
    def test_allows_under_limit(self):
        guard = RateLimitGuard(max_calls=3, window_size_s=60.0)
        assert guard.can_call(100.0) is True
        assert guard.record_call(100.0) is True

    def test_blocks_at_limit(self):
        guard = RateLimitGuard(max_calls=2, window_size_s=60.0)
        guard.record_call(100.0)
        guard.record_call(101.0)
        assert guard.can_call(102.0) is False
        assert guard.record_call(102.0) is False

    def test_window_expires(self):
        guard = RateLimitGuard(max_calls=2, window_size_s=10.0)
        guard.record_call(100.0)
        guard.record_call(101.0)
        assert guard.can_call(102.0) is False
        assert guard.can_call(111.0) is True  # window expired

    def test_state(self):
        guard = RateLimitGuard(max_calls=5, window_size_s=60.0)
        guard.record_call(100.0)
        guard.record_call(101.0)
        state = guard.get_state(102.0)
        assert state.calls_in_window == 2
        assert state.is_throttled is False

    def test_usage_rate(self):
        guard = RateLimitGuard(max_calls=4, window_size_s=60.0)
        guard.record_call(100.0)
        guard.record_call(101.0)
        assert guard.usage_rate == 0.5


# --- Gap Fill Controller ---

class TestGapFillController:
    def test_fill_accepted(self):
        result = evaluate_gap_fill("BTCUSDT", 100.0, 200.0, max_gap_s=300.0)
        assert result.decision == GapFillDecision.FILL

    def test_reject_too_large(self):
        result = evaluate_gap_fill("BTCUSDT", 100.0, 500.0, max_gap_s=300.0)
        assert result.decision == GapFillDecision.REJECT_TOO_LARGE

    def test_reject_rate_limited(self):
        result = evaluate_gap_fill("BTCUSDT", 100.0, 200.0, rate_limited=True)
        assert result.decision == GapFillDecision.REJECT_RATE_LIMITED

    def test_gap_size_computed(self):
        result = evaluate_gap_fill("BTCUSDT", 100.0, 250.0)
        assert result.request.gap_size_s == 150.0


# --- Bootstrap Reporter ---

class TestBootstrapReporter:
    def test_record_and_summarize(self):
        reporter = BootstrapReporter()
        reporter.record(BootstrapEvent(
            pair="BTCUSDT", operation="bootstrap",
            outcome=BootstrapOutcome.SUCCESS, timestamp=100.0,
        ))
        reporter.record(BootstrapEvent(
            pair="ETHUSDT", operation="gap_fill",
            outcome=BootstrapOutcome.SNAPSHOT_TOO_OLD, timestamp=101.0,
        ))
        summary = reporter.summarize()
        assert summary.total_operations == 2
        assert summary.successful == 1
        assert summary.failed == 1

    def test_filter_by_pair(self):
        reporter = BootstrapReporter()
        reporter.record(BootstrapEvent(
            pair="BTCUSDT", operation="bootstrap",
            outcome=BootstrapOutcome.SUCCESS, timestamp=100.0,
        ))
        reporter.record(BootstrapEvent(
            pair="ETHUSDT", operation="bootstrap",
            outcome=BootstrapOutcome.SUCCESS, timestamp=101.0,
        ))
        events = reporter.get_events(pair="BTCUSDT")
        assert len(events) == 1

    def test_failure_rate(self):
        reporter = BootstrapReporter()
        reporter.record(BootstrapEvent(
            pair="BTCUSDT", operation="bootstrap",
            outcome=BootstrapOutcome.SUCCESS, timestamp=100.0,
        ))
        reporter.record(BootstrapEvent(
            pair="BTCUSDT", operation="recovery",
            outcome=BootstrapOutcome.RATE_LIMITED, timestamp=101.0,
        ))
        assert reporter.failure_rate == 0.5
