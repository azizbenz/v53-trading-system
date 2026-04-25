"""Execution-backbone-local metrics sink and projections for hybrid routing V2."""

from __future__ import annotations

from dataclasses import dataclass
import math

from pydantic import BaseModel, Field

from .hybrid_router_types import (
    HybridFallbackAction,
    HybridRoutingDecision,
    RoutingTraceCompact,
    RoutingTraceFull,
    build_compact_routing_trace,
    build_full_routing_trace,
)


class HybridRouterDistributionSummary(BaseModel, frozen=True):
    count: int = Field(default=0, ge=0)
    mean_value: float = 0.0
    p50_value: float = 0.0
    p90_value: float = 0.0


class HybridRouterCalibrationMetricProjection(BaseModel, frozen=True):
    sample_count: int = Field(default=0, ge=0)
    value: float | None = None
    ready: bool = False


class HybridRouterTraceProjection(BaseModel, frozen=True):
    action: str = ""
    ev_maker_bps: float = 0.0
    ev_taker_bps: float = 0.0
    p_fill_proxy: float = 0.0
    participation_ratio: float = 0.0
    n_reason_codes: int = 0
    calibration_version: str = ""
    shadow_only: bool = True


class HybridRouterFullTraceProjection(BaseModel, frozen=True):
    compact: HybridRouterTraceProjection = HybridRouterTraceProjection()
    diagnostics: dict[str, object] = Field(default_factory=dict)
    reason_codes: tuple[str, ...] = ()


class HybridRouterMetricsProjection(BaseModel, frozen=True):
    status: str = "planned"
    live_mode_enabled: bool = False
    latest_calibration_version: str = ""
    hybrid_router_no_trade_total: int = Field(default=0, ge=0)
    hybrid_router_maker_selected_total: int = Field(default=0, ge=0)
    hybrid_router_taker_selected_total: int = Field(default=0, ge=0)
    hybrid_router_maker_converted_to_taker_total: int = Field(default=0, ge=0)
    hybrid_router_maker_cancelled_on_timeout_total: int = Field(default=0, ge=0)
    hybrid_router_shadow_only_decision_total: int = Field(default=0, ge=0)
    hybrid_router_fallback_blocked_by_runtime_total: int = Field(default=0, ge=0)
    hybrid_router_regime_input_clamped_total: dict[str, int] = Field(default_factory=dict)
    hybrid_router_vol_zscore_unavailable_total: int = Field(default=0, ge=0)
    routing_feature_projection_total: int = Field(default=0, ge=0)
    routing_feature_projection_rejection_total: dict[str, int] = Field(default_factory=dict)
    routing_feature_rejection_rate: dict[str, float] = Field(default_factory=dict)
    hybrid_router_shadow_decision_match_total: int = Field(default=0, ge=0)
    hybrid_router_shadow_decision_diff_total: dict[str, int] = Field(default_factory=dict)
    ev_maker_raw_bps: HybridRouterDistributionSummary = HybridRouterDistributionSummary()
    ev_maker_weighted_bps: HybridRouterDistributionSummary = HybridRouterDistributionSummary()
    ev_taker_bps: HybridRouterDistributionSummary = HybridRouterDistributionSummary()
    ev_maker_raw_minus_taker_bps: HybridRouterDistributionSummary = HybridRouterDistributionSummary()
    ev_maker_weighted_minus_taker_bps: HybridRouterDistributionSummary = HybridRouterDistributionSummary()
    p_fill_proxy: HybridRouterDistributionSummary = HybridRouterDistributionSummary()
    participation_ratio: HybridRouterDistributionSummary = HybridRouterDistributionSummary()
    expected_wait_s: HybridRouterDistributionSummary = HybridRouterDistributionSummary()
    expected_taker_slippage_bps: HybridRouterDistributionSummary = HybridRouterDistributionSummary()
    capital_opportunity_cost_bps: HybridRouterDistributionSummary = HybridRouterDistributionSummary()
    hybrid_router_p_fill_realized_vs_predicted_brier: HybridRouterCalibrationMetricProjection = HybridRouterCalibrationMetricProjection()
    hybrid_router_p_fill_calibration_error_mean: HybridRouterCalibrationMetricProjection = HybridRouterCalibrationMetricProjection()
    hybrid_router_wait_realized_vs_predicted_mae_s: HybridRouterCalibrationMetricProjection = HybridRouterCalibrationMetricProjection()
    hybrid_router_taker_slippage_realized_vs_predicted_mae_bps: HybridRouterCalibrationMetricProjection = HybridRouterCalibrationMetricProjection()
    hybrid_router_maker_miss_cost_realized_vs_predicted_mae_bps: HybridRouterCalibrationMetricProjection = HybridRouterCalibrationMetricProjection()
    latest_live_routing_trace: HybridRouterTraceProjection = HybridRouterTraceProjection()
    latest_shadow_routing_trace: HybridRouterFullTraceProjection | None = None
    shadow_record_count: int = Field(default=0, ge=0)


@dataclass
class HybridRouterMetricsSink:
    live_mode_enabled: bool = False

    def __post_init__(self) -> None:
        self.hybrid_router_no_trade_total = 0
        self.hybrid_router_maker_selected_total = 0
        self.hybrid_router_taker_selected_total = 0
        self.hybrid_router_maker_converted_to_taker_total = 0
        self.hybrid_router_maker_cancelled_on_timeout_total = 0
        self.hybrid_router_shadow_only_decision_total = 0
        self.hybrid_router_fallback_blocked_by_runtime_total = 0
        self.hybrid_router_vol_zscore_unavailable_total = 0
        self.hybrid_router_shadow_decision_match_total = 0
        self.shadow_record_count = 0
        self.routing_feature_projection_total = 0
        self._latest_calibration_version = ""
        self._regime_clamp_breakdown: dict[str, int] = {}
        self._bridge_rejections: dict[str, int] = {}
        self._shadow_decision_diff_breakdown: dict[str, int] = {}
        self._ev_maker_raw: list[float] = []
        self._ev_maker_weighted: list[float] = []
        self._ev_taker: list[float] = []
        self._ev_maker_raw_minus_taker: list[float] = []
        self._ev_maker_weighted_minus_taker: list[float] = []
        self._p_fill: list[float] = []
        self._participation: list[float] = []
        self._expected_wait: list[float] = []
        self._expected_taker_slippage: list[float] = []
        self._capital_opportunity_cost: list[float] = []
        self._p_fill_brier_terms: list[float] = []
        self._p_fill_calibration_terms: list[float] = []
        self._wait_abs_errors: list[float] = []
        self._taker_slippage_abs_errors: list[float] = []
        self._maker_miss_cost_abs_errors: list[float] = []
        self._latest_live_trace = HybridRouterTraceProjection()
        self._latest_shadow_trace: HybridRouterFullTraceProjection | None = None

    def record_decision(
        self,
        decision: HybridRoutingDecision,
        *,
        shadow_only: bool,
        calibration_version: str,
    ) -> None:
        action = decision.action.value
        if action == "NO_TRADE":
            self.hybrid_router_no_trade_total += 1
        elif action == "LIMIT_MAKER":
            self.hybrid_router_maker_selected_total += 1
        elif action == "MARKET_TAKER":
            self.hybrid_router_taker_selected_total += 1
        if shadow_only:
            self.hybrid_router_shadow_only_decision_total += 1
        self._latest_calibration_version = calibration_version
        for reason_code in decision.reason_codes:
            if reason_code.startswith("regime_input_clamped:"):
                bucket = reason_code.removeprefix("regime_input_clamped:")
                self._regime_clamp_breakdown[bucket] = self._regime_clamp_breakdown.get(bucket, 0) + 1
            if reason_code == "vol_zscore_unavailable":
                self.hybrid_router_vol_zscore_unavailable_total += 1
        diagnostics = decision.diagnostics
        self._ev_maker_raw.append(diagnostics.ev_maker_raw_bps)
        self._ev_maker_weighted.append(diagnostics.ev_maker_weighted_bps)
        self._ev_taker.append(diagnostics.ev_taker_bps)
        self._ev_maker_raw_minus_taker.append(diagnostics.ev_maker_raw_minus_taker_bps)
        self._ev_maker_weighted_minus_taker.append(diagnostics.ev_maker_weighted_minus_taker_bps)
        self._p_fill.append(decision.p_fill_proxy)
        self._participation.append(diagnostics.participation_ratio)
        self._expected_wait.append(diagnostics.expected_wait_s)
        self._expected_taker_slippage.append(decision.expected_taker_slippage_bps)
        self._capital_opportunity_cost.append(diagnostics.capital_opportunity_cost_bps)
        if not shadow_only:
            self._latest_live_trace = HybridRouterTraceProjection.model_validate(
                build_compact_routing_trace(
                    decision,
                    calibration_version=calibration_version,
                    shadow_only=shadow_only,
                ).__dict__
            )

    def record_fallback(self, action: HybridFallbackAction, *, reason_codes: tuple[str, ...]) -> None:
        _ = reason_codes
        if action == HybridFallbackAction.CONVERT_TO_MARKET:
            self.hybrid_router_maker_converted_to_taker_total += 1
        else:
            self.hybrid_router_maker_cancelled_on_timeout_total += 1

    def record_fallback_blocked_by_runtime(self) -> None:
        self.hybrid_router_fallback_blocked_by_runtime_total += 1

    def record_bridge_projection(self, *, rejected: bool, reason: str | None = None) -> None:
        self.routing_feature_projection_total += 1
        if rejected and reason is not None:
            self._bridge_rejections[reason] = self._bridge_rejections.get(reason, 0) + 1

    def record_shadow_observation(
        self,
        *,
        full_trace: RoutingTraceFull,
        decision_diff: str,
    ) -> None:
        self.shadow_record_count += 1
        if decision_diff == "match":
            self.hybrid_router_shadow_decision_match_total += 1
        else:
            self._shadow_decision_diff_breakdown[decision_diff] = (
                self._shadow_decision_diff_breakdown.get(decision_diff, 0) + 1
            )
        self._latest_shadow_trace = HybridRouterFullTraceProjection.model_validate(
            {
                "compact": full_trace.compact.__dict__,
                "diagnostics": {
                    "market_toxicity": full_trace.diagnostics.market_toxicity.__dict__,
                    "regime_transition_risk": full_trace.diagnostics.regime_transition_risk.__dict__,
                    "regime_stability": full_trace.diagnostics.regime_stability.__dict__,
                    "short_window_volatility_z": full_trace.diagnostics.short_window_volatility_z.__dict__,
                    "composite_dir": full_trace.diagnostics.composite_dir,
                    "participation_ratio": full_trace.diagnostics.participation_ratio,
                    "expected_wait_s": full_trace.diagnostics.expected_wait_s,
                    "alpha_decay_factor": full_trace.diagnostics.alpha_decay_factor,
                    "capital_opportunity_rate_bps_per_s": full_trace.diagnostics.capital_opportunity_rate_bps_per_s,
                    "capital_opportunity_cost_bps": full_trace.diagnostics.capital_opportunity_cost_bps,
                    "ev_maker_raw_bps": full_trace.diagnostics.ev_maker_raw_bps,
                    "ev_maker_weighted_bps": full_trace.diagnostics.ev_maker_weighted_bps,
                    "ev_taker_bps": full_trace.diagnostics.ev_taker_bps,
                    "ev_maker_raw_minus_taker_bps": full_trace.diagnostics.ev_maker_raw_minus_taker_bps,
                    "ev_maker_weighted_minus_taker_bps": full_trace.diagnostics.ev_maker_weighted_minus_taker_bps,
                },
                "reason_codes": full_trace.reason_codes,
            }
        )

    def record_realized_outcome(
        self,
        *,
        predicted_decision: HybridRoutingDecision,
        realized_fill_ratio: float | None = None,
        realized_wait_s: float | None = None,
        realized_taker_slippage_bps: float | None = None,
        realized_miss_cost_bps: float | None = None,
    ) -> None:
        diagnostics = predicted_decision.diagnostics
        if realized_fill_ratio is not None:
            self._p_fill_brier_terms.append((predicted_decision.p_fill_proxy - realized_fill_ratio) ** 2)
            self._p_fill_calibration_terms.append(realized_fill_ratio - predicted_decision.p_fill_proxy)
        if realized_wait_s is not None:
            self._wait_abs_errors.append(abs(realized_wait_s - diagnostics.expected_wait_s))
        if realized_taker_slippage_bps is not None:
            self._taker_slippage_abs_errors.append(
                abs(realized_taker_slippage_bps - predicted_decision.expected_taker_slippage_bps)
            )
        if realized_miss_cost_bps is not None:
            self._maker_miss_cost_abs_errors.append(
                abs(realized_miss_cost_bps - predicted_decision.expected_miss_cost_bps)
            )

    def build_projection(self) -> HybridRouterMetricsProjection:
        decision_total = (
            self.hybrid_router_no_trade_total
            + self.hybrid_router_maker_selected_total
            + self.hybrid_router_taker_selected_total
        )
        status = "healthy" if decision_total > 0 or self.routing_feature_projection_total > 0 else "planned"
        rejection_rate: dict[str, float] = {}
        if self.routing_feature_projection_total > 0:
            overall_rejections = sum(self._bridge_rejections.values())
            rejection_rate["overall"] = overall_rejections / self.routing_feature_projection_total
            for reason, count in self._bridge_rejections.items():
                rejection_rate[reason] = count / self.routing_feature_projection_total
        return HybridRouterMetricsProjection(
            status=status,
            live_mode_enabled=self.live_mode_enabled,
            latest_calibration_version=self._latest_calibration_version,
            hybrid_router_no_trade_total=self.hybrid_router_no_trade_total,
            hybrid_router_maker_selected_total=self.hybrid_router_maker_selected_total,
            hybrid_router_taker_selected_total=self.hybrid_router_taker_selected_total,
            hybrid_router_maker_converted_to_taker_total=self.hybrid_router_maker_converted_to_taker_total,
            hybrid_router_maker_cancelled_on_timeout_total=self.hybrid_router_maker_cancelled_on_timeout_total,
            hybrid_router_shadow_only_decision_total=self.hybrid_router_shadow_only_decision_total,
            hybrid_router_fallback_blocked_by_runtime_total=self.hybrid_router_fallback_blocked_by_runtime_total,
            hybrid_router_regime_input_clamped_total=dict(sorted(self._regime_clamp_breakdown.items())),
            hybrid_router_vol_zscore_unavailable_total=self.hybrid_router_vol_zscore_unavailable_total,
            routing_feature_projection_total=self.routing_feature_projection_total,
            routing_feature_projection_rejection_total=dict(sorted(self._bridge_rejections.items())),
            routing_feature_rejection_rate=rejection_rate,
            hybrid_router_shadow_decision_match_total=self.hybrid_router_shadow_decision_match_total,
            hybrid_router_shadow_decision_diff_total=dict(sorted(self._shadow_decision_diff_breakdown.items())),
            ev_maker_raw_bps=_distribution_summary(self._ev_maker_raw),
            ev_maker_weighted_bps=_distribution_summary(self._ev_maker_weighted),
            ev_taker_bps=_distribution_summary(self._ev_taker),
            ev_maker_raw_minus_taker_bps=_distribution_summary(self._ev_maker_raw_minus_taker),
            ev_maker_weighted_minus_taker_bps=_distribution_summary(self._ev_maker_weighted_minus_taker),
            p_fill_proxy=_distribution_summary(self._p_fill),
            participation_ratio=_distribution_summary(self._participation),
            expected_wait_s=_distribution_summary(self._expected_wait),
            expected_taker_slippage_bps=_distribution_summary(self._expected_taker_slippage),
            capital_opportunity_cost_bps=_distribution_summary(self._capital_opportunity_cost),
            hybrid_router_p_fill_realized_vs_predicted_brier=_calibration_metric(self._p_fill_brier_terms),
            hybrid_router_p_fill_calibration_error_mean=_calibration_metric(self._p_fill_calibration_terms),
            hybrid_router_wait_realized_vs_predicted_mae_s=_calibration_metric(self._wait_abs_errors),
            hybrid_router_taker_slippage_realized_vs_predicted_mae_bps=_calibration_metric(
                self._taker_slippage_abs_errors
            ),
            hybrid_router_maker_miss_cost_realized_vs_predicted_mae_bps=_calibration_metric(
                self._maker_miss_cost_abs_errors
            ),
            latest_live_routing_trace=self._latest_live_trace,
            latest_shadow_routing_trace=self._latest_shadow_trace,
            shadow_record_count=self.shadow_record_count,
        )


def _distribution_summary(values: list[float]) -> HybridRouterDistributionSummary:
    if not values:
        return HybridRouterDistributionSummary()
    ordered = sorted(float(value) for value in values)
    return HybridRouterDistributionSummary(
        count=len(ordered),
        mean_value=float(sum(ordered) / len(ordered)),
        p50_value=_percentile(ordered, 0.50),
        p90_value=_percentile(ordered, 0.90),
    )


def _calibration_metric(values: list[float]) -> HybridRouterCalibrationMetricProjection:
    if not values:
        return HybridRouterCalibrationMetricProjection()
    return HybridRouterCalibrationMetricProjection(
        sample_count=len(values),
        value=float(sum(values) / len(values)),
        ready=True,
    )


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return float(values[0])
    rank = (len(values) - 1) * percentile
    lower = math.floor(rank)
    upper = math.ceil(rank)
    if lower == upper:
        return float(values[lower])
    weight = rank - lower
    return float(values[lower] * (1.0 - weight) + values[upper] * weight)


__all__ = [
    "HybridRouterCalibrationMetricProjection",
    "HybridRouterDistributionSummary",
    "HybridRouterFullTraceProjection",
    "HybridRouterMetricsProjection",
    "HybridRouterMetricsSink",
    "HybridRouterTraceProjection",
]
