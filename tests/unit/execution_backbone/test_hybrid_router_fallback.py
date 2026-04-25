from __future__ import annotations

from execution_backbone.order_decider.hybrid_router import HybridRouter
from execution_backbone.order_decider.hybrid_router_types import HybridRoutingPlan
from tests.support_hybrid_router_v2 import build_router, build_snapshot


def _initial_plan() -> tuple[HybridRouter, HybridRoutingPlan]:
    router, _, _ = build_router()
    decision = router.decide(
        build_snapshot(
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
    )
    return router, router.build_plan(decision)


def test_fallback_cancel_when_signal_too_old() -> None:
    router, plan = _initial_plan()

    action, reason_codes = router.evaluate_fallback(
        initial_plan=plan,
        current_snapshot=build_snapshot(signal_age_s=3.0),
        observed_fill_ratio=0.0,
        elapsed_s=2.0,
    )

    assert action.value == "CANCEL"
    assert reason_codes == ("signal_too_old",)


def test_fallback_cancel_when_taker_ev_below_floor_at_timeout() -> None:
    router, plan = _initial_plan()

    action, reason_codes = router.evaluate_fallback(
        initial_plan=plan,
        current_snapshot=build_snapshot(expected_edge_bps=1.0, spread_bps=6.0),
        observed_fill_ratio=0.0,
        elapsed_s=2.0,
    )

    assert action.value == "CANCEL"
    assert reason_codes == ("taker_edge_below_floor",)


def test_fallback_convert_to_market_when_all_conditions_met() -> None:
    router, plan = _initial_plan()

    action, reason_codes = router.evaluate_fallback(
        initial_plan=plan,
        current_snapshot=build_snapshot(expected_edge_bps=8.0, spread_bps=1.0, signal_age_s=0.5),
        observed_fill_ratio=0.0,
        elapsed_s=2.0,
    )

    assert action.value == "CONVERT_TO_MARKET"
    assert reason_codes == ("fallback_convert_to_market",)


def test_fallback_cancel_when_partial_fill_already_above_progress_threshold() -> None:
    router, plan = _initial_plan()

    action, reason_codes = router.evaluate_fallback(
        initial_plan=plan,
        current_snapshot=build_snapshot(expected_edge_bps=8.0, spread_bps=1.0, signal_age_s=0.5),
        observed_fill_ratio=0.5,
        elapsed_s=2.0,
    )

    assert action.value == "CANCEL"
    assert reason_codes == ("maker_progress_sufficient",)


def test_fallback_uses_current_features_not_initial_features() -> None:
    router, plan = _initial_plan()

    action, _ = router.evaluate_fallback(
        initial_plan=plan,
        current_snapshot=build_snapshot(expected_edge_bps=1.0, spread_bps=6.0, signal_age_s=0.5),
        observed_fill_ratio=0.0,
        elapsed_s=2.0,
    )

    assert action.value == "CANCEL"


def test_fallback_does_not_perform_local_inv003_recheck() -> None:
    router, plan = _initial_plan()

    action, reason_codes = router.evaluate_fallback(
        initial_plan=plan,
        current_snapshot=build_snapshot(
            expected_edge_bps=8.0,
            spread_bps=1.0,
            signal_age_s=0.5,
            candidate_notional=50.0,
            top_n_ask_notional=100.0,
        ),
        observed_fill_ratio=0.0,
        elapsed_s=2.0,
    )

    assert action.value == "CONVERT_TO_MARKET"
    assert "inv003_depth_degraded" not in reason_codes
