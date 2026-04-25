from __future__ import annotations

import math

from execution_backbone.order_decider.hybrid_router_equations import (
    compute_capital_opportunity_cost_bps,
    compute_ev_maker_raw_bps,
    compute_ev_maker_weighted_bps,
    compute_expected_adverse_selection_bps,
    compute_expected_latency_staleness_bps,
    compute_expected_miss_cost_bps,
    compute_expected_taker_slippage_bps,
    compute_p_fill_proxy,
    compute_participation_ratio,
    compute_same_side_signals,
    sigmoid,
)
from tests.support_hybrid_router_v2 import build_calibration, build_snapshot


def test_sigmoid_bounds() -> None:
    assert 0.0 < sigmoid(-100.0) < 1.0
    assert 0.0 < sigmoid(0.0) < 1.0
    assert 0.0 < sigmoid(100.0) < 1.0


def test_same_side_signals_buy_sell_symmetry() -> None:
    buy_snapshot = build_snapshot(side="BUY")
    sell_snapshot = build_snapshot(side="SELL")

    assert compute_same_side_signals(buy_snapshot, sign_side=1) == (0.4, 0.4, 0.3)
    assert compute_same_side_signals(sell_snapshot, sign_side=-1) == (-0.4, -0.4, -0.3)


def test_participation_ratio_uses_opposite_side_for_buy() -> None:
    snapshot = build_snapshot(side="BUY", candidate_notional=100.0, top_n_ask_notional=500.0)

    assert compute_participation_ratio(snapshot, eps_notional=1.0) == 0.2


def test_participation_ratio_uses_opposite_side_for_sell() -> None:
    snapshot = build_snapshot(side="SELL", candidate_notional=100.0, top_n_bid_notional=400.0)

    assert compute_participation_ratio(snapshot, eps_notional=1.0) == 0.25


def test_participation_ratio_eps_guard() -> None:
    snapshot = build_snapshot(candidate_notional=50.0, top_n_ask_notional=0.0)

    assert math.isfinite(compute_participation_ratio(snapshot, eps_notional=1.0))


def test_p_fill_proxy_monotone_in_composite_dir() -> None:
    calibration = build_calibration()

    low = compute_p_fill_proxy(
        composite_dir=-0.5,
        market_toxicity_score=0.1,
        regime_transition_risk=0.1,
        short_window_volatility_z=0.0,
        participation_ratio=0.1,
        calib=calibration,
    )
    high = compute_p_fill_proxy(
        composite_dir=0.5,
        market_toxicity_score=0.1,
        regime_transition_risk=0.1,
        short_window_volatility_z=0.0,
        participation_ratio=0.1,
        calib=calibration,
    )

    assert high > low


def test_p_fill_proxy_decreasing_in_toxicity() -> None:
    calibration = build_calibration()

    low_toxic = compute_p_fill_proxy(
        composite_dir=0.5,
        market_toxicity_score=0.1,
        regime_transition_risk=0.1,
        short_window_volatility_z=0.0,
        participation_ratio=0.1,
        calib=calibration,
    )
    high_toxic = compute_p_fill_proxy(
        composite_dir=0.5,
        market_toxicity_score=0.9,
        regime_transition_risk=0.1,
        short_window_volatility_z=0.0,
        participation_ratio=0.1,
        calib=calibration,
    )

    assert high_toxic < low_toxic


def test_p_fill_proxy_decreasing_in_participation() -> None:
    calibration = build_calibration()

    low_participation = compute_p_fill_proxy(
        composite_dir=0.5,
        market_toxicity_score=0.1,
        regime_transition_risk=0.1,
        short_window_volatility_z=0.0,
        participation_ratio=0.05,
        calib=calibration,
    )
    high_participation = compute_p_fill_proxy(
        composite_dir=0.5,
        market_toxicity_score=0.1,
        regime_transition_risk=0.1,
        short_window_volatility_z=0.0,
        participation_ratio=0.5,
        calib=calibration,
    )

    assert high_participation < low_participation


def test_expected_miss_cost_exponential_shape() -> None:
    assert compute_expected_miss_cost_bps(expected_edge_bps=10.0, expected_wait_s=0.0, tau_alpha_s=30.0) == 0.0
    assert math.isclose(
        compute_expected_miss_cost_bps(expected_edge_bps=10.0, expected_wait_s=1e9, tau_alpha_s=30.0),
        10.0,
        rel_tol=1e-6,
    )


def test_expected_miss_cost_zero_when_edge_zero() -> None:
    assert compute_expected_miss_cost_bps(expected_edge_bps=0.0, expected_wait_s=5.0, tau_alpha_s=30.0) == 0.0


def test_adverse_selection_bounds() -> None:
    value = compute_expected_adverse_selection_bps(
        market_toxicity_score=0.5,
        regime_stability_score=0.25,
        scale_bps=2.0,
    )

    assert 0.0 <= value <= 2.0


def test_taker_slippage_additive_halfspread_plus_sqrt_impact() -> None:
    value = compute_expected_taker_slippage_bps(
        spread_bps=4.0,
        participation_ratio=0.25,
        lambda_impact_bps=2.0,
    )

    assert value == 3.0


def test_taker_slippage_zero_participation_equals_half_spread() -> None:
    assert compute_expected_taker_slippage_bps(
        spread_bps=6.0,
        participation_ratio=0.0,
        lambda_impact_bps=2.0,
    ) == 3.0


def test_capital_opportunity_cost_linear_in_wait() -> None:
    assert compute_capital_opportunity_cost_bps(expected_wait_s=5.0, rate_bps_per_s=0.2) == 1.0


def test_latency_staleness_nonnegative() -> None:
    assert compute_expected_latency_staleness_bps(short_window_volatility_z=-1.0, scale_bps=0.3) == 0.0


def test_ev_maker_raw_does_not_apply_p_fill() -> None:
    value = compute_ev_maker_raw_bps(
        expected_edge_bps=5.0,
        maker_fee_bps=1.0,
        expected_miss_cost_bps=0.5,
        expected_adverse_selection_bps=0.5,
        capital_opportunity_cost_bps=0.2,
        expected_latency_staleness_bps=0.1,
    )

    assert math.isclose(value, 2.7)


def test_ev_maker_weighted_applies_p_fill_only_on_edge_term() -> None:
    value = compute_ev_maker_weighted_bps(
        expected_edge_bps=5.0,
        p_fill_proxy=0.0,
        maker_fee_bps=1.0,
        expected_miss_cost_bps=0.5,
        expected_adverse_selection_bps=0.5,
        capital_opportunity_cost_bps=0.2,
        expected_latency_staleness_bps=0.1,
    )

    assert math.isclose(value, -2.3)


def test_ev_maker_weighted_equals_raw_when_p_fill_one() -> None:
    raw = compute_ev_maker_raw_bps(
        expected_edge_bps=5.0,
        maker_fee_bps=1.0,
        expected_miss_cost_bps=0.5,
        expected_adverse_selection_bps=0.5,
        capital_opportunity_cost_bps=0.2,
        expected_latency_staleness_bps=0.1,
    )
    weighted = compute_ev_maker_weighted_bps(
        expected_edge_bps=5.0,
        p_fill_proxy=1.0,
        maker_fee_bps=1.0,
        expected_miss_cost_bps=0.5,
        expected_adverse_selection_bps=0.5,
        capital_opportunity_cost_bps=0.2,
        expected_latency_staleness_bps=0.1,
    )

    assert weighted == raw
