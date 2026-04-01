"""Runtime tests for execution_backbone Build-3."""
import logging

import pytest

from execution_backbone.execution_runtime import (
    ExecutionOpportunity,
    ExecutionRuntime,
    ExecutionSubmissionStatus,
    RemoteExecutionState,
    ReplaceReceipt,
    SubmitReceipt,
    VenueOrderEvent,
    VenueOrderEventType,
)
from execution_backbone.fill_tracker.order_terminal_state_resolver import TerminalCategory
from execution_backbone.order_decider.intent_builder import NoTradeReason
from execution_backbone.reconciliation_layer.recovery_trigger import RecoveryAction


pytestmark = pytest.mark.build3


class FakeExecutionVenue:
    def __init__(self) -> None:
        self.submissions: list[tuple[str, object, float]] = []
        self.replacements: list[tuple[str, str, object, float]] = []
        self.cancel_requests: list[tuple[str, float, str]] = []
        self._events: list[VenueOrderEvent] = []
        self.remote_state = RemoteExecutionState()
        self._counter = 0

    def submit_order(self, intent, now: float) -> SubmitReceipt:
        self._counter += 1
        order_id = f"ord-{self._counter}"
        self.submissions.append((order_id, intent, now))
        return SubmitReceipt(order_id=order_id, submitted_at=now)

    def replace_order(self, original_order_id: str, intent, now: float) -> ReplaceReceipt:
        self._counter += 1
        replacement_order_id = f"ord-{self._counter}"
        self.replacements.append((original_order_id, replacement_order_id, intent, now))
        return ReplaceReceipt(
            original_order_id=original_order_id,
            replacement_order_id=replacement_order_id,
            replaced_at=now,
            submitted_at=now,
        )

    def cancel_order(self, order_id: str, now: float, reason: str = "") -> None:
        self.cancel_requests.append((order_id, now, reason))

    def poll_order_events(self) -> tuple[VenueOrderEvent, ...]:
        events = tuple(self._events)
        self._events.clear()
        return events

    def fetch_remote_state(self) -> RemoteExecutionState:
        return self.remote_state

    def push_events(self, *events: VenueOrderEvent) -> None:
        self._events.extend(events)


def _opportunity(
    *,
    intent_id: str = "intent-1",
    pair: str = "BTCUSDT",
    side: str = "buy",
    quantity: float = 0.25,
    expected_gain: float = 0.0100,
    expected_cost: float = 0.0015,
    spread_bps: float = 2.0,
    reference_price: float | None = None,
) -> ExecutionOpportunity:
    return ExecutionOpportunity(
        intent_id=intent_id,
        pair=pair,
        engine_id="engine_a",
        side=side,
        quantity=quantity,
        expected_gain=expected_gain,
        expected_cost=expected_cost,
        score=0.82,
        justification="validated execution path",
        spread_bps=spread_bps,
        reference_price=reference_price,
    )


class TestExecutionRuntime:
    def test_runtime_executes_real_path_across_fill_cost_and_reconciliation(self):
        adapter = FakeExecutionVenue()
        runtime = ExecutionRuntime(adapter, max_recon_age_s=30.0)

        submission = runtime.submit_opportunity(_opportunity(), now=100.0)
        assert submission.status == ExecutionSubmissionStatus.SUBMITTED
        assert submission.order_id == "ord-1"
        assert len(adapter.submissions) == 1

        adapter.push_events(
            VenueOrderEvent(order_id="ord-1", event_type=VenueOrderEventType.ACK, timestamp=100.1),
            VenueOrderEvent(
                order_id="ord-1",
                event_type=VenueOrderEventType.FILL,
                timestamp=100.5,
                fill_id="fill-1",
                fill_quantity=0.25,
                fill_price=50010.0,
                fee_amount=12.5,
                mid_price=50000.0,
                post_fill_mid_price=49980.0,
                current_mid=49990.0,
                market_impact=0.0002,
            ),
        )

        processing = runtime.process_events()
        assert processing.processed_events == 2
        assert len(processing.terminal_resolutions) == 1
        assert processing.terminal_resolutions[0].category == TerminalCategory.FULL_FILL
        assert processing.fill_stats.full_fills == 1
        assert processing.latency_stats.count == 1
        assert processing.cost_aggregate.count == 1
        assert runtime.get_local_positions()["BTC"] == pytest.approx(0.25)

        adapter.remote_state = RemoteExecutionState(
            orders={},
            fills={"ord-1": 0.25},
            positions={"BTC": 0.25},
        )
        runtime.reconcile(now=100.6)
        reconciliation = runtime.reconcile(now=100.7)
        assert reconciliation.order_result.aligned is True
        assert reconciliation.fill_result.aligned is True
        assert reconciliation.position_result.aligned is True
        assert reconciliation.recovery_decision.action == RecoveryAction.NONE

    def test_runtime_reconciliation_ignores_terminal_orders_returned_by_remote(self):
        adapter = FakeExecutionVenue()
        runtime = ExecutionRuntime(adapter, max_recon_age_s=30.0)

        submission = runtime.submit_opportunity(_opportunity(), now=100.0)
        assert submission.status == ExecutionSubmissionStatus.SUBMITTED

        adapter.push_events(
            VenueOrderEvent(order_id="ord-1", event_type=VenueOrderEventType.ACK, timestamp=100.1),
            VenueOrderEvent(
                order_id="ord-1",
                event_type=VenueOrderEventType.FILL,
                timestamp=100.5,
                fill_id="fill-1",
                fill_quantity=0.25,
                fill_price=50010.0,
                fee_amount=12.5,
                mid_price=50000.0,
                post_fill_mid_price=49980.0,
                current_mid=49990.0,
            ),
        )
        runtime.process_events()

        adapter.remote_state = RemoteExecutionState(
            orders={"ord-1": "filled"},
            fills={"ord-1": 0.25},
            positions={"BTC": 0.25},
        )
        first_reconciliation = runtime.reconcile(now=100.6)
        assert first_reconciliation.recovery_decision.action == RecoveryAction.SOFT_RESYNC

        reconciliation = runtime.reconcile(now=100.7)
        assert reconciliation.order_result.aligned is True
        assert reconciliation.order_result.order_diff == 0
        assert reconciliation.divergence_summary.is_critical is False
        assert reconciliation.recovery_decision.action == RecoveryAction.NONE

    def test_runtime_rejects_no_trade_when_cost_kills_edge(self):
        adapter = FakeExecutionVenue()
        runtime = ExecutionRuntime(adapter)

        submission = runtime.submit_opportunity(
            _opportunity(expected_gain=0.0010, expected_cost=0.0050),
            now=10.0,
        )
        assert submission.status == ExecutionSubmissionStatus.NO_TRADE
        assert submission.no_trade is not None
        assert submission.no_trade.reason == NoTradeReason.COST_EXCEEDS_EDGE
        assert len(adapter.submissions) == 0

    def test_runtime_timeout_requests_cancel_and_finalizes_partial_cancel(self):
        adapter = FakeExecutionVenue()
        runtime = ExecutionRuntime(adapter)

        submission = runtime.submit_opportunity(
            _opportunity(intent_id="limit-intent", spread_bps=6.0, reference_price=50000.0, quantity=1.0),
            now=200.0,
        )
        assert submission.status == ExecutionSubmissionStatus.SUBMITTED
        assert submission.intent is not None
        assert submission.intent.order_type.value == "limit"

        adapter.push_events(
            VenueOrderEvent(order_id="ord-1", event_type=VenueOrderEventType.ACK, timestamp=200.1),
            VenueOrderEvent(
                order_id="ord-1",
                event_type=VenueOrderEventType.FILL,
                timestamp=200.4,
                fill_id="fill-1",
                fill_quantity=0.4,
                fill_price=50000.0,
                fee_rate=0.001,
                mid_price=49995.0,
                post_fill_mid_price=49990.0,
                current_mid=49992.0,
            ),
        )
        first_processing = runtime.process_events()
        assert first_processing.fill_stats.open_orders == 1
        assert first_processing.cost_aggregate.count == 0

        timeout_result = runtime.sweep_timeouts(now=231.0)
        assert timeout_result.cancelled_order_ids == ("ord-1",)
        assert adapter.cancel_requests == [("ord-1", 231.0, "timeout")]

        adapter.push_events(
            VenueOrderEvent(
                order_id="ord-1",
                event_type=VenueOrderEventType.CANCELLED,
                timestamp=231.5,
                reason="timeout",
            ),
        )
        final_processing = runtime.process_events()
        assert len(final_processing.terminal_resolutions) == 1
        assert final_processing.terminal_resolutions[0].category == TerminalCategory.PARTIAL_FILL_CANCELLED
        assert final_processing.fill_stats.partial_fills == 1
        assert final_processing.cost_aggregate.count == 1

    def test_runtime_replace_order_cancels_old_and_submits_new(self):
        adapter = FakeExecutionVenue()
        runtime = ExecutionRuntime(adapter)

        first = runtime.submit_opportunity(
            _opportunity(intent_id="replace-me", spread_bps=6.0, reference_price=50000.0),
            now=50.0,
        )
        replacement = runtime.replace_order(first.order_id, new_price_limit=49990.0, now=55.0)

        assert replacement.status == ExecutionSubmissionStatus.REPLACED
        assert replacement.replaced_order_id == "ord-1"
        assert replacement.order_id == "ord-2"
        assert len(adapter.replacements) == 1
        fill_stats = runtime.get_fill_stats()
        assert fill_stats.cancellations == 1
        assert fill_stats.open_orders == 1

    def test_runtime_critical_reconciliation_triggers_halt(self):
        adapter = FakeExecutionVenue()
        runtime = ExecutionRuntime(adapter, max_recon_age_s=30.0)

        runtime.submit_opportunity(_opportunity(quantity=0.1), now=300.0)
        adapter.push_events(
            VenueOrderEvent(order_id="ord-1", event_type=VenueOrderEventType.ACK, timestamp=300.1),
            VenueOrderEvent(
                order_id="ord-1",
                event_type=VenueOrderEventType.FILL,
                timestamp=300.4,
                fill_id="fill-1",
                fill_quantity=0.1,
                fill_price=50000.0,
                fee_amount=5.0,
                mid_price=49995.0,
                post_fill_mid_price=49970.0,
            ),
        )
        runtime.process_events()

        adapter.remote_state = RemoteExecutionState(
            orders={"ord-1": "filled"},
            fills={"ord-1": 0.1},
            positions={"BTC": 2.0},
        )
        reconciliation = runtime.reconcile(now=301.0)
        assert reconciliation.position_result.aligned is False
        assert reconciliation.divergence_summary.is_critical is True
        assert reconciliation.recovery_decision.action == RecoveryAction.HALT_TRADING

    def test_runtime_emits_structured_logs(self, caplog: pytest.LogCaptureFixture):
        caplog.set_level(logging.INFO)
        adapter = FakeExecutionVenue()
        runtime = ExecutionRuntime(adapter)

        submission = runtime.submit_opportunity(_opportunity(), now=100.0)
        assert submission.status == ExecutionSubmissionStatus.SUBMITTED
        assert any(record.message == "execution_submission_submitted" for record in caplog.records)

        adapter.push_events(
            VenueOrderEvent(order_id="ord-1", event_type=VenueOrderEventType.ACK, timestamp=100.1),
            VenueOrderEvent(
                order_id="ord-1",
                event_type=VenueOrderEventType.FILL,
                timestamp=100.2,
                fill_id="fill-1",
                fill_quantity=0.25,
                fill_price=50010.0,
                fee_amount=12.5,
                mid_price=50000.0,
                post_fill_mid_price=49980.0,
                current_mid=49990.0,
            ),
        )
        runtime.process_events()
        adapter.remote_state = RemoteExecutionState(orders={}, fills={"ord-1": 0.25}, positions={"BTC": 0.25})
        runtime.reconcile(now=100.3)
        assert any(record.message == "execution_reconciliation_completed" for record in caplog.records)
