"""Integration tests for execution_backbone Build-3."""

import pytest

from execution_backbone.execution_cost_meter.cost_aggregator import (
    CostAggregator,
    compute_trade_cost,
)
from execution_backbone.execution_cost_meter.elw_meter import compute_elw
from execution_backbone.execution_cost_meter.fee_meter import estimate_fee
from execution_backbone.fill_tracker.fill_aggregator import FillAggregator, FillEvent
from execution_backbone.fill_tracker.order_state_tracker import OrderStateTracker
from execution_backbone.order_decider.decision_reporter import DecisionReporter
from execution_backbone.order_decider.execution_guard import GuardVerdict, check_execution_guards
from execution_backbone.order_decider.intent_builder import OrderType, build_intent
from execution_backbone.order_decider.order_type_selector import select_order_type
from execution_backbone.order_decider.timeout_policy_selector import select_timeout_policy
from execution_backbone.reconciliation_layer.divergence_classifier import (
    DivergenceSeverity,
    classify_all,
    classify_divergence,
)
from execution_backbone.reconciliation_layer.fill_reconciler import reconcile_fills
from execution_backbone.reconciliation_layer.order_reconciler import reconcile_orders
from execution_backbone.reconciliation_layer.position_reconciler import reconcile_positions
from execution_backbone.reconciliation_layer.recovery_trigger import RecoveryAction, RecoveryTrigger


pytestmark = pytest.mark.build3


class TestExecutionBackboneIntegration:
    def test_end_to_end_aligned_path(self):
        decision = select_order_type(
            expected_gain=0.0100,
            expected_cost=0.0015,
            safety_margin=0.0010,
            spread_bps=2.0,
        )
        assert decision.order_type == OrderType.MARKET

        guard = check_execution_guards(
            pair_health_score=0.95,
            infrastructure_ok=True,
            data_stale=False,
            expected_cost=decision.expected_cost,
            max_acceptable_cost=0.005,
        )
        assert guard.verdict == GuardVerdict.PASS

        intent = build_intent(
            intent_id="intent-1",
            pair="BTCUSDT",
            engine_id="engine_a",
            side="buy",
            order_type=decision.order_type,
            quantity=0.25,
            expected_cost=decision.expected_cost,
            expected_gain=decision.expected_gain,
            score=0.82,
            justification=decision.reason,
            timeout_s=select_timeout_policy(decision.order_type).timeout_s,
        )

        reporter = DecisionReporter()
        reporter.record_trade(intent, timestamp=100.0)
        assert reporter.get_stats().trades == 1

        tracker = OrderStateTracker()
        tracker.register_order("ord-1", intent.pair, intent.engine_id, intent.side, intent.order_type.value, intent.quantity)
        tracker.mark_sent("ord-1", 100.0)
        tracker.mark_acked("ord-1", 100.1)
        state = tracker.mark_fill("ord-1", 0.25, 50010.0, 100.4, fill_id="fill-1")
        assert state.state.value == "filled"

        aggregator = FillAggregator()
        aggregated = aggregator.record_fill(FillEvent(
            fill_id="fill-1",
            order_id="ord-1",
            pair=intent.pair,
            side=intent.side,
            quantity=0.25,
            price=50010.0,
            timestamp=100.4,
        ))
        assert aggregated.total_filled_qty == pytest.approx(0.25)

        fee = estimate_fee(price=50010.0, quantity=0.25, fee_rate=0.001)
        elw = compute_elw("ord-1", intent.pair, exec_price=50010.0, mid_price=50000.0, side=intent.side)
        cost = compute_trade_cost(
            "ord-1",
            intent.pair,
            intent.engine_id,
            explicit_fee=fee,
            implicit_cost=elw.elw,
            market_impact=0.0002,
            expected_cost=intent.expected_cost,
        )
        cost_agg = CostAggregator()
        cost_agg.record(cost)
        assert cost_agg.get_aggregate().count == 1

        order_recon = reconcile_orders({"ord-1": "filled"}, {"ord-1": "filled"})
        fill_recon = reconcile_fills({"ord-1": aggregated.total_filled_qty}, {"ord-1": 0.25})
        pos_recon = reconcile_positions({"BTC": 0.25}, {"BTC": 0.25})
        assert order_recon.aligned is True
        assert fill_recon.aligned is True
        assert pos_recon.aligned is True

    def test_divergence_path_triggers_recovery(self):
        order_recon = reconcile_orders({"ord-1": "acked"}, {"ord-1": "filled"})
        fill_recon = reconcile_fills({"ord-1": 0.1}, {"ord-1": 0.3})
        pos_recon = reconcile_positions({"BTC": 0.1}, {"BTC": 1.5})

        classified = (
            classify_divergence("order", order_recon.divergences[0].detail, abs_diff=1.0),
            classify_divergence("fill", fill_recon.divergences[0].detail, abs_diff=fill_recon.max_qty_diff),
            classify_divergence("position", "position mismatch", abs_diff=pos_recon.max_abs_diff),
        )
        summary = classify_all(classified)
        assert summary.max_severity == DivergenceSeverity.CRITICAL

        trigger = RecoveryTrigger(max_recon_age_s=30.0)
        trigger.record_reconciliation(100.0)
        decision = trigger.evaluate(summary.max_severity, now=131.0, divergence_count=summary.total_divergences)
        assert decision.action == RecoveryAction.HALT_TRADING
        assert decision.stale_reconciliation is True
