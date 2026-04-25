from __future__ import annotations

from dataclasses import replace

from execution_backbone.execution_routing_features import ExecutionRoutingFeatureSnapshot
from execution_backbone.execution_runtime_models import ExecutionSubmissionStatus
from execution_backbone.order_decider.intent_builder import OrderType
from tests.support_hybrid_router_v2 import build_calibration, build_opportunity, build_runtime, build_snapshot


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


def test_runtime_submits_maker_on_limit_maker_decision() -> None:
    runtime, adapter, _, _ = build_runtime(calibration=replace(build_calibration(), live_mode_enabled=True))

    submission = runtime.submit_opportunity(
        build_opportunity(
            routing_features=_maker_friendly_snapshot(),
            expected_gain=0.0020,
            expected_cost=0.0002,
        ),
        now=10.0,
    )

    assert submission.status == ExecutionSubmissionStatus.SUBMITTED
    assert adapter.submissions[0][1].order_type == OrderType.LIMIT


def test_runtime_submits_market_on_market_taker_decision() -> None:
    runtime, adapter, _, _ = build_runtime(calibration=replace(build_calibration(), live_mode_enabled=True))

    submission = runtime.submit_opportunity(
        build_opportunity(
            routing_features=build_snapshot(
                expected_edge_bps=8.0,
                spread_bps=1.0,
                market_toxicity_score=0.9,
                regime_transition_risk=0.9,
                regime_stability_score=0.1,
            )
            ,
            expected_gain=0.0020,
            expected_cost=0.0002,
        ),
        now=10.0,
    )

    assert submission.status == ExecutionSubmissionStatus.SUBMITTED
    assert adapter.submissions[0][1].order_type == OrderType.MARKET


def test_runtime_does_nothing_on_no_trade_decision() -> None:
    runtime, adapter, _, _ = build_runtime(calibration=replace(build_calibration(), live_mode_enabled=True))

    submission = runtime.submit_opportunity(
        build_opportunity(
            routing_features=build_snapshot(expected_edge_bps=1.0, spread_bps=6.0),
            expected_gain=0.0020,
            expected_cost=0.0002,
        ),
        now=10.0,
    )

    assert submission.status == ExecutionSubmissionStatus.NO_TRADE
    assert adapter.submissions == []


def test_runtime_arms_maker_timeout_and_persists_plan() -> None:
    calibration = replace(build_calibration(), live_mode_enabled=True)
    runtime, _, _, _ = build_runtime(calibration=calibration)

    submission = runtime.submit_opportunity(
        build_opportunity(
            routing_features=_maker_friendly_snapshot(),
            expected_gain=0.0020,
            expected_cost=0.0002,
        ),
        now=10.0,
    )

    assert submission.order_id in runtime._hybrid_plans_by_order_id
    assert runtime._timeout_by_order_id[submission.order_id] == calibration.maker_timeout_s


def test_runtime_emits_routing_trace_compact_in_live_metrics() -> None:
    runtime, _, metrics, _ = build_runtime(calibration=replace(build_calibration(), live_mode_enabled=True))

    runtime.submit_opportunity(
        build_opportunity(
            routing_features=_maker_friendly_snapshot(),
            expected_gain=0.0020,
            expected_cost=0.0002,
        ),
        now=10.0,
    )
    projection = metrics.build_projection()

    assert projection.latest_live_routing_trace.action in {"LIMIT_MAKER", "MARKET_TAKER", "NO_TRADE"}
    assert projection.latest_shadow_routing_trace is None


def test_runtime_emits_routing_trace_full_in_shadow_log() -> None:
    runtime, _, metrics, shadow_logger = build_runtime()

    runtime.submit_opportunity(
        build_opportunity(
            routing_features=_maker_friendly_snapshot(),
            expected_gain=0.0020,
            expected_cost=0.0002,
        ),
        now=10.0,
    )
    projection = metrics.build_projection()

    assert shadow_logger.records()
    assert projection.latest_shadow_routing_trace is not None
    assert "diagnostics" in projection.latest_shadow_routing_trace.model_dump()
