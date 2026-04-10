"""Tests for data_backbone.internal_router — Build-2."""
import logging

import pytest

from data_backbone.internal_router.consumer_registry import (
    ConsumerPriority,
    ConsumerSubscription,
    ConsumerRegistry,
)
from data_backbone.internal_router.priority_dispatcher import dispatch_event
from data_backbone.internal_router.queue_manager import QueueManager
from data_backbone.internal_router.backpressure_guard import (
    BackpressureAction,
    evaluate_backpressure,
)
from data_backbone.internal_router.routing_reporter import RoutingReporter


pytestmark = pytest.mark.build2


# --- Consumer Registry ---

class TestConsumerRegistry:
    def test_register_and_get(self):
        reg = ConsumerRegistry()
        sub = ConsumerSubscription(consumer_id="engine_a", priority=ConsumerPriority.CRITICAL)
        reg.register(sub)
        assert reg.get("engine_a") == sub
        assert reg.consumer_count == 1

    def test_unregister(self):
        reg = ConsumerRegistry()
        reg.register(ConsumerSubscription(consumer_id="x"))
        assert reg.unregister("x") is True
        assert reg.unregister("x") is False

    def test_get_consumers_for_event_priority_order(self):
        reg = ConsumerRegistry()
        reg.register(ConsumerSubscription(consumer_id="analytics", priority=ConsumerPriority.LOW))
        reg.register(ConsumerSubscription(consumer_id="engine", priority=ConsumerPriority.CRITICAL))
        reg.register(ConsumerSubscription(consumer_id="scoring", priority=ConsumerPriority.HIGH))
        consumers = reg.get_consumers_for_event("trade", "BTCUSDT")
        assert consumers[0].consumer_id == "engine"
        assert consumers[1].consumer_id == "scoring"
        assert consumers[2].consumer_id == "analytics"

    def test_filter_by_event_type(self):
        reg = ConsumerRegistry()
        reg.register(ConsumerSubscription(
            consumer_id="trade_only", event_types=frozenset({"trade"}),
        ))
        reg.register(ConsumerSubscription(consumer_id="all_events"))
        consumers = reg.get_consumers_for_event("depth", "BTCUSDT")
        assert len(consumers) == 1
        assert consumers[0].consumer_id == "all_events"

    def test_filter_by_pair(self):
        reg = ConsumerRegistry()
        reg.register(ConsumerSubscription(
            consumer_id="btc_only", pairs=frozenset({"BTCUSDT"}),
        ))
        consumers = reg.get_consumers_for_event("trade", "ETHUSDT")
        assert len(consumers) == 0


# --- Priority Dispatcher ---

class TestPriorityDispatcher:
    def test_dispatch_simple(self):
        consumers = (
            ConsumerSubscription(consumer_id="a", priority=ConsumerPriority.CRITICAL),
            ConsumerSubscription(consumer_id="b", priority=ConsumerPriority.NORMAL),
        )
        result = dispatch_event("trade", "BTCUSDT", consumers)
        assert result.total_dispatched == 2
        assert "a" in result.dispatched_to

    def test_dispatch_enforces_priority_order_even_if_input_is_unsorted(self):
        consumers = (
            ConsumerSubscription(consumer_id="analytics", priority=ConsumerPriority.NORMAL),
            ConsumerSubscription(consumer_id="risk", priority=ConsumerPriority.CRITICAL),
            ConsumerSubscription(consumer_id="scoring", priority=ConsumerPriority.HIGH),
        )
        result = dispatch_event("trade", "BTCUSDT", consumers)
        assert result.dispatched_to == ("risk", "scoring", "analytics")

    def test_dispatch_with_blocked(self):
        consumers = (
            ConsumerSubscription(consumer_id="a"),
            ConsumerSubscription(consumer_id="b"),
        )
        result = dispatch_event("trade", "BTCUSDT", consumers, blocked_consumers=frozenset({"b"}))
        assert result.total_dispatched == 1
        assert result.total_dropped == 1
        assert "b" in result.dropped_for


# --- Queue Manager ---

class TestQueueManager:
    def test_enqueue_dequeue(self):
        qm = QueueManager()
        qm.create_queue("c1", max_size=100)
        assert qm.enqueue("c1", "event1") is True
        items = qm.dequeue("c1")
        assert items == ("event1",)

    def test_bounded_queue_drops_oldest(self):
        """GEM-05: drop_oldest=True evicts oldest when full."""
        qm = QueueManager()
        qm.create_queue("c1", max_size=2)
        qm.enqueue("c1", "a")
        qm.enqueue("c1", "b")
        assert qm.enqueue("c1", "c") is True  # accepted, oldest dropped
        stats = qm.get_stats("c1")
        assert stats.total_dropped == 1
        assert stats.depth == 2
        items = qm.dequeue("c1")
        assert items == ("b", "c")  # "a" was evicted

    def test_stats(self):
        qm = QueueManager()
        qm.create_queue("c1", max_size=10)
        qm.enqueue("c1", "a")
        qm.enqueue("c1", "b")
        stats = qm.get_stats("c1")
        assert stats.depth == 2
        assert stats.total_enqueued == 2
        assert stats.capacity == 10
        assert stats.high_water_mark == 2
        assert stats.utilization == 0.2

    def test_partial_dequeue(self):
        qm = QueueManager()
        qm.create_queue("c1", max_size=100)
        for i in range(5):
            qm.enqueue("c1", f"e{i}")
        items = qm.dequeue("c1", max_count=3)
        assert len(items) == 3
        assert qm.get_depth("c1") == 2

    def test_unknown_queue(self):
        qm = QueueManager()
        assert qm.enqueue("unknown", "x") is False
        assert qm.get_stats("unknown") is None


# --- Backpressure Guard ---

class TestBackpressureGuard:
    def test_backpressure_actions_do_not_expose_dead_block_state(self):
        assert {action.value for action in BackpressureAction} == {"none", "warn", "drop"}

    def test_no_pressure(self):
        result = evaluate_backpressure("c1", 0.3, ConsumerPriority.NORMAL)
        assert result.action == BackpressureAction.NONE
        assert result.is_blocked is False

    def test_warn_threshold(self):
        result = evaluate_backpressure("c1", 0.8, ConsumerPriority.NORMAL)
        assert result.action == BackpressureAction.WARN

    def test_drop_threshold_normal(self):
        result = evaluate_backpressure("c1", 0.95, ConsumerPriority.NORMAL)
        assert result.action == BackpressureAction.DROP
        assert result.is_blocked is True

    def test_critical_never_dropped(self):
        result = evaluate_backpressure("c1", 0.95, ConsumerPriority.CRITICAL)
        assert result.action == BackpressureAction.WARN
        assert result.is_blocked is False


# --- Routing Reporter ---

class TestRoutingReporter:
    def test_stats(self):
        reporter = RoutingReporter()
        reporter.record_dispatch("c1")
        reporter.record_dispatch("c1")
        reporter.record_dispatch("c2")
        reporter.record_drop("c3")
        stats = reporter.get_stats()
        assert stats.total_dispatched == 3
        assert stats.total_dropped == 1
        assert stats.by_consumer["c1"] == 2

    def test_drop_rate(self):
        reporter = RoutingReporter()
        reporter.record_dispatch("c1")
        reporter.record_drop("c1")
        assert reporter.drop_rate == 0.5

    def test_reporter_emits_structured_logs(self, caplog: pytest.LogCaptureFixture):
        caplog.set_level(logging.INFO)
        reporter = RoutingReporter()
        reporter.record_dispatch("c1")
        reporter.record_drop("c1")
        reporter.record_backpressure()
        messages = {record.message for record in caplog.records}
        assert "routing_dispatch_recorded" in messages
        assert "routing_drop_recorded" in messages
        assert "routing_backpressure_recorded" in messages
