"""Pure equations for the Build-3 hybrid router."""

from __future__ import annotations

import math

from execution_backbone.execution_routing_features import ExecutionRoutingFeatureSnapshot

from .hybrid_router_calibration import HybridRouterCalibration


def sigmoid(x: float) -> float:
    if x >= 0.0:
        exp_term = math.exp(-x)
        return 1.0 / (1.0 + exp_term)
    exp_term = math.exp(x)
    return exp_term / (1.0 + exp_term)


def compute_same_side_signals(
    snap: ExecutionRoutingFeatureSnapshot,
    *,
    sign_side: int,
) -> tuple[float, float, float]:
    return (
        sign_side * float(snap.order_book_imbalance),
        sign_side * float(snap.microprice_pressure),
        sign_side * float(snap.aggressive_trade_imbalance),
    )


def compute_participation_ratio(
    snap: ExecutionRoutingFeatureSnapshot,
    *,
    eps_notional: float,
) -> float:
    opposite_side_notional = (
        float(snap.top_n_ask_notional)
        if snap.side == "BUY"
        else float(snap.top_n_bid_notional)
    )
    return float(snap.candidate_notional) / max(opposite_side_notional, eps_notional)


def compute_p_fill_proxy(
    *,
    composite_dir: float,
    market_toxicity_score: float,
    regime_transition_risk: float,
    short_window_volatility_z: float,
    participation_ratio: float,
    calib: HybridRouterCalibration,
) -> float:
    logit_fill = (
        calib.beta_0
        + calib.beta_dir * composite_dir
        - calib.beta_toxic * market_toxicity_score
        - calib.beta_transition * regime_transition_risk
        - calib.beta_vol * short_window_volatility_z
        - calib.beta_participation * participation_ratio
    )
    return sigmoid(logit_fill)


def compute_expected_miss_cost_bps(
    *,
    expected_edge_bps: float,
    expected_wait_s: float,
    tau_alpha_s: float,
) -> float:
    alpha_decay_factor = 1.0 - math.exp(-expected_wait_s / tau_alpha_s)
    return expected_edge_bps * alpha_decay_factor


def compute_expected_adverse_selection_bps(
    *,
    market_toxicity_score: float,
    regime_stability_score: float,
    scale_bps: float,
) -> float:
    return scale_bps * market_toxicity_score * (1.0 - regime_stability_score)


def compute_expected_taker_slippage_bps(
    *,
    spread_bps: float,
    participation_ratio: float,
    lambda_impact_bps: float,
) -> float:
    return 0.5 * spread_bps + lambda_impact_bps * math.sqrt(max(participation_ratio, 0.0))


def compute_capital_opportunity_cost_bps(
    *,
    expected_wait_s: float,
    rate_bps_per_s: float,
) -> float:
    return rate_bps_per_s * expected_wait_s


def compute_expected_latency_staleness_bps(
    *,
    short_window_volatility_z: float,
    scale_bps: float,
) -> float:
    return scale_bps * max(short_window_volatility_z, 0.0)


def compute_ev_maker_bps(
    *,
    expected_edge_bps: float,
    p_fill_proxy: float,
    maker_fee_bps: float,
    expected_miss_cost_bps: float,
    expected_adverse_selection_bps: float,
    capital_opportunity_cost_bps: float,
    expected_latency_staleness_bps: float,
) -> float:
    return (
        expected_edge_bps * p_fill_proxy
        - maker_fee_bps
        - expected_miss_cost_bps
        - expected_adverse_selection_bps
        - capital_opportunity_cost_bps
        - expected_latency_staleness_bps
    )


def compute_ev_taker_bps(
    *,
    expected_edge_bps: float,
    taker_fee_bps: float,
    expected_taker_slippage_bps: float,
) -> float:
    return expected_edge_bps - taker_fee_bps - expected_taker_slippage_bps


__all__ = [
    "compute_capital_opportunity_cost_bps",
    "compute_ev_maker_bps",
    "compute_ev_taker_bps",
    "compute_expected_adverse_selection_bps",
    "compute_expected_latency_staleness_bps",
    "compute_expected_miss_cost_bps",
    "compute_expected_taker_slippage_bps",
    "compute_p_fill_proxy",
    "compute_participation_ratio",
    "compute_same_side_signals",
    "sigmoid",
]
