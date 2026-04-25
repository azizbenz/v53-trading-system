"""Deterministic Build-3 hybrid router.

This router is shadow-first and does not model queue position. Its `p_fill_proxy`
is a governed routing proxy, not a calibrated real-world probability until the
shadow calibration wave has converged.
"""

from __future__ import annotations

import math

from execution_backbone.execution_routing_features import (
    ExecutionRoutingFeatureSnapshot,
    snapshot_reason_codes,
)

from .hybrid_router_calibration import HybridRouterCalibration
from .hybrid_router_equations import (
    compute_capital_opportunity_cost_bps,
    compute_ev_maker_bps,
    compute_ev_taker_bps,
    compute_expected_adverse_selection_bps,
    compute_expected_latency_staleness_bps,
    compute_expected_miss_cost_bps,
    compute_expected_taker_slippage_bps,
    compute_p_fill_proxy,
    compute_participation_ratio,
    compute_same_side_signals,
)
from .hybrid_router_metrics import HybridRouterMetricsSink
from .hybrid_router_types import (
    HybridFallbackAction,
    HybridRoutingAction,
    HybridRoutingDecision,
    HybridRoutingPlan,
)


class HybridRouter:
    def __init__(
        self,
        calib: HybridRouterCalibration,
        metrics_sink: HybridRouterMetricsSink | None,
    ) -> None:
        calib.validate()
        self._calib = calib
        self._metrics_sink = metrics_sink
        if self._metrics_sink is not None:
            self._metrics_sink.live_mode_enabled = calib.live_mode_enabled

    def decide(
        self,
        snap: ExecutionRoutingFeatureSnapshot,
    ) -> HybridRoutingDecision:
        sign_side = 1 if snap.side == "BUY" else -1
        same_side_obi, same_side_micro, same_side_aggr = compute_same_side_signals(
            snap,
            sign_side=sign_side,
        )
        participation_ratio = compute_participation_ratio(
            snap,
            eps_notional=self._calib.eps_notional_eur,
        )
        reason_codes = list(snapshot_reason_codes(snap))
        market_toxicity_score = _sanitize_zero_to_one(
            float(snap.market_toxicity_score),
            "market_toxicity_score",
            reason_codes,
        )
        regime_transition_risk = _sanitize_zero_to_one(
            float(snap.regime_transition_risk),
            "regime_transition_risk",
            reason_codes,
        )
        regime_stability_score = _sanitize_zero_to_one(
            float(snap.regime_stability_score),
            "regime_stability_score",
            reason_codes,
        )
        short_window_volatility_z = _sanitize_vol_z(
            float(snap.short_window_volatility_z),
            self._calib.vol_z_clip,
            reason_codes,
        )
        composite_dir = (
            self._calib.w_obi * same_side_obi
            + self._calib.w_micro * same_side_micro
            + self._calib.w_aggr * same_side_aggr
        )
        p_fill_proxy = compute_p_fill_proxy(
            composite_dir=composite_dir,
            market_toxicity_score=market_toxicity_score,
            regime_transition_risk=regime_transition_risk,
            short_window_volatility_z=short_window_volatility_z,
            participation_ratio=participation_ratio,
            calib=self._calib,
        )
        expected_wait_s = self._calib.maker_timeout_s * (1.0 - p_fill_proxy)
        expected_miss_cost_bps = compute_expected_miss_cost_bps(
            expected_edge_bps=float(snap.expected_edge_bps),
            expected_wait_s=expected_wait_s,
            tau_alpha_s=self._calib.tau_alpha_s,
        )
        expected_adverse_selection_bps = compute_expected_adverse_selection_bps(
            market_toxicity_score=market_toxicity_score,
            regime_stability_score=regime_stability_score,
            scale_bps=self._calib.adverse_selection_scale_bps,
        )
        expected_taker_slippage_bps = compute_expected_taker_slippage_bps(
            spread_bps=float(snap.spread_bps),
            participation_ratio=participation_ratio,
            lambda_impact_bps=self._calib.lambda_impact_bps,
        )
        capital_opportunity_cost_bps = compute_capital_opportunity_cost_bps(
            expected_wait_s=expected_wait_s,
            rate_bps_per_s=self._calib.capital_opportunity_rate_bps_per_s,
        )
        expected_latency_staleness_bps = compute_expected_latency_staleness_bps(
            short_window_volatility_z=short_window_volatility_z,
            scale_bps=self._calib.latency_staleness_scale_bps,
        )
        ev_maker_bps = compute_ev_maker_bps(
            expected_edge_bps=float(snap.expected_edge_bps),
            p_fill_proxy=p_fill_proxy,
            maker_fee_bps=float(snap.maker_fee_bps),
            expected_miss_cost_bps=expected_miss_cost_bps,
            expected_adverse_selection_bps=expected_adverse_selection_bps,
            capital_opportunity_cost_bps=capital_opportunity_cost_bps,
            expected_latency_staleness_bps=expected_latency_staleness_bps,
        )
        ev_taker_bps = compute_ev_taker_bps(
            expected_edge_bps=float(snap.expected_edge_bps),
            taker_fee_bps=float(snap.taker_fee_bps),
            expected_taker_slippage_bps=expected_taker_slippage_bps,
        )
        action = _decide_action(
            ev_maker_bps=ev_maker_bps,
            ev_taker_bps=ev_taker_bps,
            p_fill_proxy=p_fill_proxy,
            calib=self._calib,
        )
        reason_codes.extend(_action_reason_codes(action))
        decision = HybridRoutingDecision(
            action=action,
            ev_maker_bps=ev_maker_bps,
            ev_taker_bps=ev_taker_bps,
            p_fill_proxy=p_fill_proxy,
            participation_ratio=participation_ratio,
            expected_wait_s=expected_wait_s,
            expected_miss_cost_bps=expected_miss_cost_bps,
            expected_adverse_selection_bps=expected_adverse_selection_bps,
            expected_taker_slippage_bps=expected_taker_slippage_bps,
            capital_opportunity_cost_bps=capital_opportunity_cost_bps,
            expected_latency_staleness_bps=expected_latency_staleness_bps,
            reason_codes=tuple(reason_codes),
        )
        if self._metrics_sink is not None:
            self._metrics_sink.record_decision(
                decision,
                shadow_only=not self._calib.live_mode_enabled,
            )
        return decision

    def build_plan(
        self,
        decision: HybridRoutingDecision,
    ) -> HybridRoutingPlan:
        return HybridRoutingPlan(
            decision=decision,
            maker_timeout_s=self._calib.maker_timeout_s,
            max_signal_age_for_fallback_s=self._calib.max_signal_age_for_fallback_s,
            maker_min_fill_progress_ratio=self._calib.maker_min_fill_progress_ratio,
            inv003_max_participation_ratio=self._calib.inv003_max_participation_ratio,
            shadow_only=not self._calib.live_mode_enabled,
        )

    def evaluate_fallback(
        self,
        *,
        initial_plan: HybridRoutingPlan,
        current_snapshot: ExecutionRoutingFeatureSnapshot,
        observed_fill_ratio: float,
        elapsed_s: float,
    ) -> tuple[HybridFallbackAction, tuple[str, ...]]:
        _ = elapsed_s
        participation_ratio_current = compute_participation_ratio(
            current_snapshot,
            eps_notional=self._calib.eps_notional_eur,
        )
        if participation_ratio_current > initial_plan.inv003_max_participation_ratio:
            return HybridFallbackAction.CANCEL, ("inv003_depth_degraded",)
        current_decision = self.decide(current_snapshot)
        if current_snapshot.signal_age_s > initial_plan.max_signal_age_for_fallback_s:
            return HybridFallbackAction.CANCEL, ("signal_too_old",)
        if observed_fill_ratio >= initial_plan.maker_min_fill_progress_ratio:
            return HybridFallbackAction.CANCEL, ("maker_progress_sufficient",)
        if current_decision.ev_taker_bps <= self._calib.route_edge_floor_bps:
            return HybridFallbackAction.CANCEL, ("taker_edge_below_floor",)
        return HybridFallbackAction.CONVERT_TO_MARKET, ("fallback_convert_to_market",)


def _sanitize_zero_to_one(value: float, name: str, reason_codes: list[str]) -> float:
    if not math.isfinite(value):
        reason_codes.append(f"regime_input_clamped:{name}")
        return 0.0
    clamped = min(1.0, max(0.0, value))
    if clamped != value:
        reason_codes.append(f"regime_input_clamped:{name}")
    return clamped


def _sanitize_vol_z(value: float, clip_value: float, reason_codes: list[str]) -> float:
    if not math.isfinite(value):
        reason_codes.append("vol_zscore_unavailable")
        return 0.0
    clamped = min(clip_value, max(-clip_value, value))
    if clamped != value:
        reason_codes.append("vol_zscore_clipped")
    return clamped


def _decide_action(
    *,
    ev_maker_bps: float,
    ev_taker_bps: float,
    p_fill_proxy: float,
    calib: HybridRouterCalibration,
) -> HybridRoutingAction:
    if max(ev_maker_bps, ev_taker_bps) <= calib.route_edge_floor_bps:
        return HybridRoutingAction.NO_TRADE
    if (
        ev_maker_bps >= ev_taker_bps + calib.maker_advantage_min_bps
        and p_fill_proxy >= calib.maker_fill_probability_min
    ):
        return HybridRoutingAction.LIMIT_MAKER
    if ev_taker_bps > calib.route_edge_floor_bps:
        return HybridRoutingAction.MARKET_TAKER
    return HybridRoutingAction.NO_TRADE


def _action_reason_codes(action: HybridRoutingAction) -> tuple[str, ...]:
    if action == HybridRoutingAction.NO_TRADE:
        return ("hybrid_router_no_trade",)
    if action == HybridRoutingAction.LIMIT_MAKER:
        return ("hybrid_router_limit_maker",)
    return ("hybrid_router_market_taker",)


__all__ = ["HybridRouter"]
