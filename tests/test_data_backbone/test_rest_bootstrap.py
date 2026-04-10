"""Tests for data_backbone.rest_bootstrap — Build-2."""
import logging

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
from data_backbone.rest_bootstrap.runtime_bootstrap import RestBootstrapRuntime


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

    def test_prune_keeps_container_identity(self):
        guard = RateLimitGuard(max_calls=3, window_size_s=10.0)
        guard.record_call(100.0)
        guard.record_call(101.0)
        container_id = id(guard._call_times)

        assert guard.can_call(112.0) is True
        assert id(guard._call_times) == container_id
        assert len(guard._call_times) == 0


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

    def test_record_emits_structured_log(self, caplog: pytest.LogCaptureFixture):
        caplog.set_level(logging.INFO)
        reporter = BootstrapReporter()
        reporter.record(BootstrapEvent(
            pair="BTCUSDT", operation="bootstrap",
            outcome=BootstrapOutcome.SUCCESS, timestamp=100.0,
        ))
        assert any(record.message == "rest_bootstrap_event" for record in caplog.records)


class _FakeSnapshotProvider:
    def __init__(self) -> None:
        self.snapshot: Snapshot | None = None
        self.gap_snapshot: Snapshot | None = None
        self.fetch_error: Exception | None = None
        self.fill_error: Exception | None = None
        self.fill_calls: int = 0

    def fetch_snapshot(self, pair: str, data_type: str) -> Snapshot:
        if self.fetch_error is not None:
            raise self.fetch_error
        assert self.snapshot is not None
        return self.snapshot

    def fill_gap(self, pair: str, data_type: str, gap_start: float, gap_end: float) -> Snapshot:
        self.fill_calls += 1
        if self.fill_error is not None:
            raise self.fill_error
        assert self.gap_snapshot is not None
        return self.gap_snapshot


class TestRestBootstrapRuntime:
    def test_bootstrap_success(self):
        provider = _FakeSnapshotProvider()
        provider.snapshot = Snapshot(
            pair="BTCUSDT",
            data_type="orderbook",
            payload={"bids": [], "asks": []},
            fetch_time=100.0,
        )
        runtime = RestBootstrapRuntime(provider)
        result = runtime.bootstrap("BTCUSDT", "orderbook", now=105.0, max_age_s=10.0)
        assert result.outcome == BootstrapOutcome.SUCCESS
        assert result.snapshot is not None
        assert runtime.reporter.total_events == 1

    def test_bootstrap_too_old_snapshot(self):
        provider = _FakeSnapshotProvider()
        provider.snapshot = Snapshot(
            pair="BTCUSDT",
            data_type="orderbook",
            payload={"bids": [], "asks": []},
            fetch_time=100.0,
        )
        runtime = RestBootstrapRuntime(provider)
        result = runtime.bootstrap("BTCUSDT", "orderbook", now=120.0, max_age_s=10.0)
        assert result.outcome == BootstrapOutcome.SNAPSHOT_TOO_OLD
        assert result.blocked is True

    def test_bootstrap_fetch_error(self):
        provider = _FakeSnapshotProvider()
        provider.fetch_error = RuntimeError("snapshot failed")
        runtime = RestBootstrapRuntime(provider)
        result = runtime.bootstrap("BTCUSDT", "orderbook", now=100.0)
        assert result.outcome == BootstrapOutcome.FETCH_ERROR
        assert "snapshot failed" in result.message

    def test_gap_fill_rejected_when_too_large(self):
        provider = _FakeSnapshotProvider()
        runtime = RestBootstrapRuntime(provider)
        result = runtime.resync(
            "BTCUSDT",
            "orderbook",
            gap_start=100.0,
            gap_end=500.0,
            now=105.0,
            max_gap_s=300.0,
        )
        assert result.outcome == BootstrapOutcome.GAP_TOO_LARGE
        assert result.blocked is True

    def test_gap_fill_success(self):
        provider = _FakeSnapshotProvider()
        provider.gap_snapshot = Snapshot(
            pair="BTCUSDT",
            data_type="orderbook",
            payload={"bids": [], "asks": []},
            fetch_time=105.0,
        )
        runtime = RestBootstrapRuntime(provider)
        result = runtime.resync(
            "BTCUSDT",
            "orderbook",
            gap_start=100.0,
            gap_end=110.0,
            now=106.0,
            max_gap_s=30.0,
            max_age_s=10.0,
        )
        assert result.outcome == BootstrapOutcome.SUCCESS
        assert result.gap_fill_result is not None

    def test_gap_fill_respects_record_call_failure_after_gap_validation(self):
        provider = _FakeSnapshotProvider()
        provider.gap_snapshot = Snapshot(
            pair="BTCUSDT",
            data_type="orderbook",
            payload={"bids": [], "asks": []},
            fetch_time=105.0,
        )

        class _RaceyRateLimitGuard:
            def record_call(self, now: float) -> bool:
                return False

        runtime = RestBootstrapRuntime(provider, rate_limit_guard=_RaceyRateLimitGuard())
        result = runtime.resync(
            "BTCUSDT",
            "orderbook",
            gap_start=100.0,
            gap_end=110.0,
            now=106.0,
            max_gap_s=30.0,
            max_age_s=10.0,
        )

        assert result.outcome == BootstrapOutcome.RATE_LIMITED
        assert result.blocked is True
        assert result.gap_fill_result is not None
        assert result.gap_fill_result.decision == GapFillDecision.REJECT_RATE_LIMITED
        assert provider.fill_calls == 0

    def test_runtime_logs_bootstrap_request(self, caplog: pytest.LogCaptureFixture):
        caplog.set_level(logging.INFO)
        provider = _FakeSnapshotProvider()
        provider.snapshot = Snapshot(
            pair="BTCUSDT",
            data_type="orderbook",
            payload={"bids": [], "asks": []},
            fetch_time=100.0,
        )
        runtime = RestBootstrapRuntime(provider)
        runtime.bootstrap("BTCUSDT", "orderbook", now=105.0, max_age_s=10.0)
        assert any(record.message == "rest_bootstrap_requested" for record in caplog.records)
