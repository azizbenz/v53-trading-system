from __future__ import annotations

from execution_backbone.execution_routing_features import ExecutionRoutingFeatureSnapshot
from tests.support_hybrid_router_v2 import build_calibration, build_router, build_snapshot


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


def test_no_trade_when_both_ev_below_floor() -> None:
    router, _, _ = build_router()

    decision = router.decide(build_snapshot(expected_edge_bps=1.0, spread_bps=4.0))

    assert decision.action.value == "NO_TRADE"


def test_limit_maker_when_maker_advantage_and_high_p_fill() -> None:
    router, _, _ = build_router()

    decision = router.decide(_maker_friendly_snapshot())

    assert decision.action.value == "LIMIT_MAKER"


def test_market_taker_when_maker_advantage_insufficient() -> None:
    router, _, _ = build_router()

    decision = router.decide(
        build_snapshot(
            expected_edge_bps=6.0,
            spread_bps=1.0,
            market_toxicity_score=0.9,
            regime_transition_risk=0.9,
            regime_stability_score=0.1,
        )
    )

    assert decision.action.value == "MARKET_TAKER"


def test_market_taker_when_p_fill_below_min_even_if_ev_maker_higher() -> None:
    calibration = build_calibration(maker_fill_probability_min=0.95)
    router, _, _ = build_router(calibration=calibration)

    decision = router.decide(build_snapshot(expected_edge_bps=10.0, spread_bps=1.0))

    assert decision.action.value == "MARKET_TAKER"


def test_no_trade_when_taker_ev_negative_and_maker_not_eligible() -> None:
    calibration = build_calibration(maker_fill_probability_min=0.95, route_edge_floor_bps=3.0)
    router, _, _ = build_router(calibration=calibration)

    decision = router.decide(build_snapshot(expected_edge_bps=2.5, spread_bps=4.0))

    assert decision.action.value == "NO_TRADE"


def test_decision_uses_weighted_ev_not_raw() -> None:
    calibration = build_calibration(maker_fill_probability_min=0.95)
    router, _, _ = build_router(calibration=calibration)

    decision = router.decide(
        build_snapshot(
            expected_edge_bps=8.0,
            spread_bps=1.0,
            market_toxicity_score=0.8,
            regime_transition_risk=0.8,
            short_window_volatility_z=2.0,
        )
    )

    assert decision.diagnostics.ev_maker_raw_bps > decision.ev_taker_bps
    assert decision.action.value == "MARKET_TAKER"


def test_decision_is_deterministic_for_same_input() -> None:
    router, _, _ = build_router()
    snapshot = _maker_friendly_snapshot()

    actions = {router.decide(snapshot).action.value for _ in range(10)}

    assert actions == {"LIMIT_MAKER"}


def test_decision_buy_sell_symmetry_with_flipped_book() -> None:
    router, _, _ = build_router()
    buy_decision = router.decide(
        build_snapshot(
            side="BUY",
            order_book_imbalance=0.4,
            microprice_pressure=0.4,
            aggressive_trade_imbalance=0.3,
        )
    )
    sell_decision = router.decide(
        build_snapshot(
            side="SELL",
            order_book_imbalance=-0.4,
            microprice_pressure=-0.4,
            aggressive_trade_imbalance=-0.3,
        )
    )

    assert buy_decision.action == sell_decision.action
