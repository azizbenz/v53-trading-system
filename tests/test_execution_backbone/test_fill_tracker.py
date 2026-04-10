"""Tests for execution_backbone.fill_tracker — Build-3."""
import logging

import pytest

from execution_backbone.fill_tracker.order_state_tracker import (
    OrderState,
    OrderStateTracker,
    TERMINAL_STATES,
)
from execution_backbone.fill_tracker.fill_aggregator import (
    FillAggregator,
    FillEvent,
)
from execution_backbone.fill_tracker.latency_meter import LatencyMeter
from execution_backbone.fill_tracker.order_terminal_state_resolver import (
    TerminalCategory,
    resolve_terminal,
)
from execution_backbone.fill_tracker.fill_reporter import FillReporter


pytestmark = pytest.mark.build3


# --- Order State Tracker ---

class TestOrderStateTracker:
    def test_lifecycle_pending_to_filled(self):
        t = OrderStateTracker()
        t.register_order("o1", "BTC", "A", "buy", "market", 1.0)
        assert t.get("o1").state == OrderState.PENDING

        t.mark_sent("o1", 100.0)
        assert t.get("o1").state == OrderState.SENT

        t.mark_acked("o1", 100.5)
        assert t.get("o1").state == OrderState.ACKED

        t.mark_fill("o1", 1.0, 50000.0, 100.8)
        assert t.get("o1").state == OrderState.FILLED
        assert t.is_terminal("o1")

    def test_partial_fills(self):
        t = OrderStateTracker()
        t.register_order("o1", "BTC", "A", "buy", "market", 2.0)
        t.mark_sent("o1", 100.0)
        t.mark_acked("o1", 100.5)

        t.mark_fill("o1", 0.5, 50000.0, 101.0)
        assert t.get("o1").state == OrderState.PARTIALLY_FILLED
        assert t.get("o1").filled_quantity == 0.5

        t.mark_fill("o1", 1.5, 50100.0, 101.5)
        assert t.get("o1").state == OrderState.FILLED
        assert t.get("o1").filled_quantity == 2.0
        # Weighted average: (50000*0.5 + 50100*1.5) / 2.0 = 50075
        assert t.get("o1").average_fill_price == pytest.approx(50075.0)

    def test_cancelled(self):
        t = OrderStateTracker()
        t.register_order("o1", "BTC", "A", "buy", "limit", 1.0)
        t.mark_sent("o1", 100.0)
        t.mark_cancelled("o1", 110.0, "timeout")
        assert t.get("o1").state == OrderState.CANCELLED
        assert t.is_terminal("o1")

    def test_rejected(self):
        t = OrderStateTracker()
        t.register_order("o1", "BTC", "A", "buy", "market", 1.0)
        t.mark_sent("o1", 100.0)
        t.mark_rejected("o1", 100.2, "insufficient balance")
        assert t.get("o1").state == OrderState.REJECTED

    def test_open_orders(self):
        t = OrderStateTracker()
        t.register_order("o1", "BTC", "A", "buy", "market", 1.0)
        t.register_order("o2", "ETH", "A", "sell", "limit", 5.0)
        t.mark_sent("o1", 100.0)
        t.mark_acked("o1", 100.5)
        t.mark_fill("o1", 1.0, 50000.0, 101.0)
        assert len(t.get_open_orders()) == 1  # o2 still open

    def test_unknown_order_raises(self):
        t = OrderStateTracker()
        with pytest.raises(KeyError):
            t.mark_sent("unknown", 100.0)

    def test_duplicate_fill_id_is_ignored(self):
        t = OrderStateTracker()
        t.register_order("o1", "BTC", "A", "buy", "market", 1.0)
        t.mark_fill("o1", 0.4, 50000.0, 100.0, fill_id="f1")
        result = t.mark_fill("o1", 0.4, 50000.0, 100.1, fill_id="f1")
        assert result.filled_quantity == pytest.approx(0.4)
        assert result.state == OrderState.PARTIALLY_FILLED

    def test_late_ack_does_not_regress_after_partial_fill(self):
        t = OrderStateTracker()
        t.register_order("o1", "BTC", "A", "buy", "limit", 1.0)
        t.mark_fill("o1", 0.2, 50000.0, 100.0, fill_id="f1")
        result = t.mark_acked("o1", 99.0)
        assert result.state == OrderState.PARTIALLY_FILLED
        assert result.first_fill_time == pytest.approx(100.0)

    def test_terminal_state_is_not_downgraded_by_late_cancel(self):
        t = OrderStateTracker()
        t.register_order("o1", "BTC", "A", "buy", "market", 1.0)
        t.mark_fill("o1", 1.0, 50000.0, 100.0, fill_id="f1")
        result = t.mark_cancelled("o1", 101.0, "late_cancel")
        assert result.state == OrderState.FILLED


# --- Fill Aggregator ---

class TestFillAggregator:
    def test_single_fill(self):
        agg = FillAggregator()
        fill = FillEvent(
            fill_id="f1", order_id="o1", pair="BTC", side="buy",
            quantity=1.0, price=50000.0, fee=50.0, timestamp=100.0,
        )
        result = agg.record_fill(fill)
        assert result.fill_count == 1
        assert result.total_filled_qty == 1.0
        assert result.total_filled_qty_exact == "1"
        assert result.total_notional_exact == "50000"
        assert result.total_fees == 50.0
        assert result.total_fees_exact == "50"

    def test_multiple_fills(self):
        agg = FillAggregator()
        agg.record_fill(FillEvent(
            fill_id="f1", order_id="o1", pair="BTC", side="buy",
            quantity=0.5, price=50000.0, fee=25.0, timestamp=100.0,
        ))
        result = agg.record_fill(FillEvent(
            fill_id="f2", order_id="o1", pair="BTC", side="buy",
            quantity=0.5, price=50100.0, fee=25.1, timestamp=101.0,
        ))
        assert result.fill_count == 2
        assert result.total_filled_qty == 1.0
        assert result.average_price == pytest.approx(50050.0)
        assert result.average_price_exact == "50050"
        assert result.total_notional_exact == "50050"
        assert result.total_fees == pytest.approx(50.1)
        assert result.total_fees_exact == "50.1"

    def test_total_fills(self):
        agg = FillAggregator()
        agg.record_fill(FillEvent(
            fill_id="f1", order_id="o1", pair="BTC", side="buy",
            quantity=1.0, price=50000.0, timestamp=100.0,
        ))
        agg.record_fill(FillEvent(
            fill_id="f2", order_id="o2", pair="ETH", side="sell",
            quantity=10.0, price=3000.0, timestamp=101.0,
        ))
        assert agg.total_fills == 2

    def test_duplicate_fill_event_is_idempotent(self):
        agg = FillAggregator()
        fill = FillEvent(
            fill_id="f1", order_id="o1", pair="BTC", side="buy",
            quantity=1.0, price=50000.0, timestamp=100.0,
        )
        agg.record_fill(fill)
        result = agg.record_fill(fill)
        assert result.fill_count == 1
        assert result.total_filled_qty == pytest.approx(1.0)

    def test_conflicting_fill_metadata_raises(self):
        agg = FillAggregator()
        agg.record_fill(FillEvent(
            fill_id="f1", order_id="o1", pair="BTC", side="buy",
            quantity=0.5, price=50000.0, timestamp=100.0,
        ))
        with pytest.raises(ValueError):
            agg.record_fill(FillEvent(
                fill_id="f2", order_id="o1", pair="ETH", side="buy",
                quantity=0.5, price=3000.0, timestamp=101.0,
            ))

    def test_zero_quantity_fill_is_rejected_during_aggregation(self):
        agg = FillAggregator()
        with pytest.raises(ValueError, match="aggregated fill quantity must be > 0"):
            agg.record_fill(FillEvent(
                fill_id="f0", order_id="o0", pair="BTC", side="buy",
                quantity=0.0, price=50000.0, timestamp=100.0,
            ))


# --- Latency Meter ---

class TestLatencyMeter:
    def test_full_latency(self):
        meter = LatencyMeter()
        m = meter.record("o1", sent_time=100.0, ack_time=100.2, first_fill_time=100.5, full_fill_time=101.0)
        assert m.submit_to_ack_s == pytest.approx(0.2)
        assert m.submit_to_first_fill_s == pytest.approx(0.5)
        assert m.submit_to_full_fill_s == pytest.approx(1.0)
        assert m.ack_to_first_fill_s == pytest.approx(0.3)

    def test_partial_latency(self):
        meter = LatencyMeter()
        m = meter.record("o1", sent_time=100.0, ack_time=100.3)
        assert m.submit_to_ack_s == pytest.approx(0.3)
        assert m.submit_to_first_fill_s is None

    def test_zero_sent_time_not_treated_as_none(self):
        """sent_time=0.0 is a valid timestamp, must not be treated as absent."""
        meter = LatencyMeter()
        m = meter.record("o1", sent_time=0.0, ack_time=0.2)
        assert m.submit_to_ack_s == pytest.approx(0.2)
        assert m.submit_to_ack_s is not None

    def test_zero_ack_time_not_treated_as_none(self):
        """ack_time=0.0 is valid, first_fill latency must be computed."""
        meter = LatencyMeter()
        m = meter.record("o1", sent_time=0.0, ack_time=0.0, first_fill_time=0.3)
        assert m.ack_to_first_fill_s == pytest.approx(0.3)
        assert m.submit_to_first_fill_s == pytest.approx(0.3)

    def test_stats(self):
        meter = LatencyMeter()
        meter.record("o1", sent_time=100.0, ack_time=100.1)
        meter.record("o2", sent_time=200.0, ack_time=200.3)
        stats = meter.get_stats()
        assert stats.count == 2
        assert stats.avg_submit_to_ack_s == pytest.approx(0.2)

    def test_negative_latency_is_filtered(self):
        meter = LatencyMeter()
        m = meter.record("o1", sent_time=100.2, ack_time=100.1)
        assert m.submit_to_ack_s is None
        assert meter.get_stats().filtered_samples == 1

    def test_aberrant_latency_is_filtered(self):
        meter = LatencyMeter(max_latency_s=1.0)
        m = meter.record("o1", sent_time=100.0, full_fill_time=105.0)
        assert m.submit_to_full_fill_s is None
        assert meter.get_stats().filtered_samples == 1


# --- Terminal State Resolver ---

class TestTerminalStateResolver:
    def test_full_fill(self):
        r = resolve_terminal("o1", OrderState.FILLED, 1.0, 1.0)
        assert r.category == TerminalCategory.FULL_FILL
        assert r.fill_ratio == 1.0
        assert r.has_residual is False

    def test_partial_cancelled(self):
        r = resolve_terminal("o1", OrderState.CANCELLED, 1.0, 0.3)
        assert r.category == TerminalCategory.PARTIAL_FILL_CANCELLED
        assert r.has_residual is True

    def test_zero_fill_cancelled(self):
        r = resolve_terminal("o1", OrderState.CANCELLED, 1.0, 0.0)
        assert r.category == TerminalCategory.ZERO_FILL_CANCELLED

    def test_expired_with_fills(self):
        r = resolve_terminal("o1", OrderState.EXPIRED, 1.0, 0.5)
        assert r.category == TerminalCategory.EXPIRED_WITH_FILLS

    def test_rejected(self):
        r = resolve_terminal("o1", OrderState.REJECTED, 1.0, 0.0)
        assert r.category == TerminalCategory.REJECTED

    def test_non_terminal_raises(self):
        with pytest.raises(ValueError):
            resolve_terminal("o1", OrderState.ACKED, 1.0, 0.0)


# --- Fill Reporter ---

class TestFillReporter:
    def test_full_lifecycle(self):
        reporter = FillReporter()
        reporter.record_order_created()
        reporter.record_order_created()
        reporter.record_order_created()
        reporter.record_terminal(OrderState.FILLED)
        reporter.record_terminal(OrderState.CANCELLED, had_partial_fills=True)
        reporter.record_terminal(OrderState.REJECTED)
        stats = reporter.get_stats()
        assert stats.total_orders == 3
        assert stats.full_fills == 1
        assert stats.partial_fills == 1
        assert stats.rejections == 1
        assert stats.open_orders == 0
        assert stats.full_fill_rate == pytest.approx(1 / 3)

    def test_expired_with_partial_fills_counts_as_partial(self):
        reporter = FillReporter()
        reporter.record_order_created()
        reporter.record_terminal(OrderState.EXPIRED, had_partial_fills=True)
        stats = reporter.get_stats()
        assert stats.partial_fills == 1
        assert stats.expirations == 0  # not double-counted

    def test_expired_without_fills_counts_as_expiration(self):
        reporter = FillReporter()
        reporter.record_order_created()
        reporter.record_terminal(OrderState.EXPIRED, had_partial_fills=False)
        stats = reporter.get_stats()
        assert stats.expirations == 1
        assert stats.partial_fills == 0

    def test_cancelled_with_partial_fills_counts_as_partial(self):
        reporter = FillReporter()
        reporter.record_order_created()
        reporter.record_terminal(OrderState.CANCELLED, had_partial_fills=True)
        stats = reporter.get_stats()
        assert stats.partial_fills == 1
        assert stats.cancellations == 0

    def test_cancelled_without_fills_counts_as_cancellation(self):
        reporter = FillReporter()
        reporter.record_order_created()
        reporter.record_terminal(OrderState.CANCELLED, had_partial_fills=False)
        stats = reporter.get_stats()
        assert stats.cancellations == 1
        assert stats.partial_fills == 0

    def test_reporter_emits_structured_logs(self, caplog: pytest.LogCaptureFixture):
        caplog.set_level(logging.INFO)
        reporter = FillReporter()
        reporter.record_order_created()
        reporter.record_terminal(OrderState.REJECTED)
        messages = {record.message for record in caplog.records}
        assert "execution_order_created" in messages
        assert "execution_order_terminal" in messages
