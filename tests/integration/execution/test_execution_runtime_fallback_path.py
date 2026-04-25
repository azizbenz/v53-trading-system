from __future__ import annotations

from dataclasses import replace

from execution_backbone.execution_routing_features import ExecutionRoutingFeatureSnapshot
from execution_backbone.execution_runtime import ExecutionRuntime
from execution_backbone.execution_runtime_models import ExecutionSubmission, ExecutionSubmissionStatus
from execution_backbone.order_decider.hybrid_router_types import HybridRoutingDecision, HybridRoutingPlan
from execution_backbone.order_decider.hybrid_router_metrics import HybridRouterMetricsSink
from tests.support_hybrid_router_v2 import (
    FakeExecutionVenue,
    build_calibration,
    build_opportunity,
    build_runtime,
    build_snapshot,
)


def _maker_friendly_snapshot() -> ExecutionRoutingFeatureSnapshot:
    return build_snapshot(
        expected_edge_bps=25.0,
        spread_bps=0.1,
        candidate_notional=1.0,
        top_n_bid_notional=10_000.0,
        top_n_ask_notional=10_000.0,
        order_book_imbalance=1.0,
        microprice_pressure=1.0,
        aggressive_trade_imbalance=1.0,
        short_window_volatility_z=-5.0,
        market_toxicity_score=0.0,
        regime_transition_risk=0.0,
        regime_stability_score=1.0,
        maker_fee_bps=0.0,
        taker_fee_bps=3.0,
    )


def _submit_live_maker() -> tuple[ExecutionRuntime, FakeExecutionVenue, HybridRouterMetricsSink, ExecutionSubmission]:
    runtime, adapter, metrics, _ = build_runtime(
        calibration=replace(build_calibration(), live_mode_enabled=True)
    )
    submission = runtime.submit_opportunity(
        build_opportunity(
            routing_features=_maker_friendly_snapshot(),
            expected_gain=0.0020,
            expected_cost=0.0002,
        ),
        now=10.0,
    )
    return runtime, adapter, metrics, submission


def test_fallback_convert_calls_native_submit_market_order() -> None:
    runtime, adapter, _, submission = _submit_live_maker()
    called = {"count": 0}
    original = runtime.submit_market_order

    def wrapped(
        opportunity: object,
        *,
        now: float,
        decision: HybridRoutingDecision | None = None,
        plan: HybridRoutingPlan | None = None,
    ) -> ExecutionSubmission:
        called["count"] += 1
        return original(opportunity, now=now, decision=decision, plan=plan)

    runtime.submit_market_order = wrapped  # type: ignore[method-assign]

    result = runtime.sweep_timeouts(now=20.0)

    assert called["count"] == 1
    assert submission.order_id in result.converted_order_ids
    assert len(adapter.submissions) == 2


def test_fallback_convert_blocked_by_runtime_inv003_increments_metric() -> None:
    runtime, _, metrics, _ = _submit_live_maker()

    runtime.submit_market_order = (  # type: ignore[method-assign]
        lambda opportunity, *, now, decision=None, plan=None: ExecutionSubmission(
            status=ExecutionSubmissionStatus.BLOCKED,
            detail="runtime blocked market submit",
        )
    )

    runtime.sweep_timeouts(now=20.0)

    assert metrics.build_projection().hybrid_router_fallback_blocked_by_runtime_total == 1


def test_fallback_convert_blocked_results_in_cancellation() -> None:
    runtime, adapter, _, submission = _submit_live_maker()

    runtime.submit_market_order = (  # type: ignore[method-assign]
        lambda opportunity, *, now, decision=None, plan=None: ExecutionSubmission(
            status=ExecutionSubmissionStatus.BLOCKED,
            detail="runtime blocked market submit",
        )
    )

    result = runtime.sweep_timeouts(now=20.0)

    assert result.converted_order_ids == ()
    assert adapter.cancel_requests[0][0] == submission.order_id


def test_fallback_does_not_bypass_runtime_hard_blocks() -> None:
    runtime, adapter, metrics, _ = _submit_live_maker()

    runtime.submit_market_order = (  # type: ignore[method-assign]
        lambda opportunity, *, now, decision=None, plan=None: ExecutionSubmission(
            status=ExecutionSubmissionStatus.BLOCKED,
            detail="runtime blocked market submit",
        )
    )

    runtime.sweep_timeouts(now=20.0)

    assert len(adapter.submissions) == 1
    assert metrics.build_projection().hybrid_router_fallback_blocked_by_runtime_total == 1
