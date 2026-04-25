"""Execution-backbone-local metrics sink and projections for hybrid routing."""

from __future__ import annotations

from dataclasses import dataclass
import math

from pydantic import BaseModel, Field

from .hybrid_router_types import (
    HybridFallbackAction,
    HybridRoutingDecision,
    build_routing_trace_payload,
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
    expected_wait_s: float = 0.0
    expected_miss_cost_bps: float = 0.0
    expected_adverse_selection_bps: float = 0.0
    expected_taker_slippage_bps: float = 0.0
    capital_opportunity_cost_bps: float = 0.0
    expected_latency_staleness_bps: float = 0.0
    reason_codes: tuple[str, ...] = ()
    shadow_only: bool = True


class HybridRouterMetricsProjection(BaseModel, frozen=True):
    status: str = "planned"
    live_mode_enabled: bool = False
    hybrid_router_no_trade_total: int = Field(default=0, ge=0)
    hybrid_router_maker_selected_total: int = Field(default=0, ge=0)
    hybrid_router_taker_selected_total: int = Field(default=0, ge=0)
    hybrid_router_maker_converted_to_taker_total: int = Field(default=0, ge=0)
    hybrid_router_maker_cancelled_on_timeout_total: int = Field(default=0, ge=0)
    hybrid_router_shadow_only_decision_total: int = Field(default=0, ge=0)
    hybrid_router_inv003_depth_degraded_total: int = Field(default=0, ge=0)
    hybrid_router_regime_input_clamped_total: int = Field(default=0, ge=0)
    hybrid_router_vol_zscore_unavailable_total: int = Field(default=0, ge=0)
    ev_maker_bps: HybridRouterDistributionSummary = HybridRouterDistributionSummary()
    ev_taker_bps: HybridRouterDistributionSummary = HybridRouterDistributionSummary()
    p_fill_proxy: HybridRouterDistributionSummary = HybridRouterDistributionSummary()
    participation_ratio: HybridRouterDistributionSummary = HybridRouterDistributionSummary()
    expected_wait_s: HybridRouterDistributionSummary = HybridRouterDistributionSummary()
    expected_taker_slippage_bps: HybridRouterDistributionSummary = HybridRouterDistributionSummary()
    hybrid_router_p_fill_realized_vs_predicted_brier: HybridRouterCalibrationMetricProjection = HybridRouterCalibrationMetricProjection()
    hybrid_router_wait_realized_vs_predicted_mae_s: HybridRouterCalibrationMetricProjection = HybridRouterCalibrationMetricProjection()
    hybrid_router_taker_slippage_realized_vs_predicted_mae_bps: HybridRouterCalibrationMetricProjection = HybridRouterCalibrationMetricProjection()
    hybrid_router_maker_miss_cost_realized_vs_predicted_mae_bps: HybridRouterCalibrationMetricProjection = HybridRouterCalibrationMetricProjection()
    latest_routing_trace: HybridRouterTraceProjection = HybridRouterTraceProjection()
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
        self.hybrid_router_inv003_depth_degraded_total = 0
        self.hybrid_router_regime_input_clamped_total = 0
        self.hybrid_router_vol_zscore_unavailable_total = 0
        self.shadow_record_count = 0
        self._ev_maker: list[float] = []
        self._ev_taker: list[float] = []
        self._p_fill: list[float] = []
        self._participation: list[float] = []
        self._expected_wait: list[float] = []
        self._expected_taker_slippage: list[float] = []
        self._p_fill_brier_terms: list[float] = []
        self._wait_abs_errors: list[float] = []
        self._taker_slippage_abs_errors: list[float] = []
        self._maker_miss_cost_abs_errors: list[float] = []
        self._latest_trace = HybridRouterTraceProjection()

    def record_decision(self, decision: HybridRoutingDecision, *, shadow_only: bool) -> None:
        action = decision.action.value
        if action == "NO_TRADE":
            self.hybrid_router_no_trade_total += 1
        elif action == "LIMIT_MAKER":
            self.hybrid_router_maker_selected_total += 1
        elif action == "MARKET_TAKER":
            self.hybrid_router_taker_selected_total += 1
        if shadow_only:
            self.hybrid_router_shadow_only_decision_total += 1
        for reason_code in decision.reason_codes:
            if reason_code.startswith("regime_input_clamped:"):
                self.hybrid_router_regime_input_clamped_total += 1
            if reason_code == "vol_zscore_unavailable":
                self.hybrid_router_vol_zscore_unavailable_total += 1
        self._ev_maker.append(decision.ev_maker_bps)
        self._ev_taker.append(decision.ev_taker_bps)
        self._p_fill.append(decision.p_fill_proxy)
        self._participation.append(decision.participation_ratio)
        self._expected_wait.append(decision.expected_wait_s)
        self._expected_taker_slippage.append(decision.expected_taker_slippage_bps)
        self._latest_trace = HybridRouterTraceProjection.model_validate(
            build_routing_trace_payload(decision, shadow_only=shadow_only)
        )

    def record_fallback(self, action: HybridFallbackAction, *, reason_codes: tuple[str, ...]) -> None:
        if action == HybridFallbackAction.CONVERT_TO_MARKET:
            self.hybrid_router_maker_converted_to_taker_total += 1
        else:
            self.hybrid_router_maker_cancelled_on_timeout_total += 1
        if "inv003_depth_degraded" in reason_codes:
            self.hybrid_router_inv003_depth_degraded_total += 1

    def record_shadow_observation(self) -> None:
        self.shadow_record_count += 1

    def record_realized_outcome(
        self,
        *,
        predicted_decision: HybridRoutingDecision,
        realized_fill: float | None = None,
        realized_wait_s: float | None = None,
        realized_taker_slippage_bps: float | None = None,
        realized_miss_cost_bps: float | None = None,
    ) -> None:
        if realized_fill is not None:
            self._p_fill_brier_terms.append((predicted_decision.p_fill_proxy - realized_fill) ** 2)
        if realized_wait_s is not None:
            self._wait_abs_errors.append(abs(realized_wait_s - predicted_decision.expected_wait_s))
        if realized_taker_slippage_bps is not None:
            self._taker_slippage_abs_errors.append(
                abs(realized_taker_slippage_bps - predicted_decision.expected_taker_slippage_bps)
            )
        if realized_miss_cost_bps is not None:
            self._maker_miss_cost_abs_errors.append(
                abs(realized_miss_cost_bps - predicted_decision.expected_miss_cost_bps)
            )

    def build_projection(self) -> HybridRouterMetricsProjection:
        status = "healthy" if (
            self.hybrid_router_no_trade_total
            + self.hybrid_router_maker_selected_total
            + self.hybrid_router_taker_selected_total
        ) > 0 else "planned"
        return HybridRouterMetricsProjection(
            status=status,
            live_mode_enabled=self.live_mode_enabled,
            hybrid_router_no_trade_total=self.hybrid_router_no_trade_total,
            hybrid_router_maker_selected_total=self.hybrid_router_maker_selected_total,
            hybrid_router_taker_selected_total=self.hybrid_router_taker_selected_total,
            hybrid_router_maker_converted_to_taker_total=self.hybrid_router_maker_converted_to_taker_total,
            hybrid_router_maker_cancelled_on_timeout_total=self.hybrid_router_maker_cancelled_on_timeout_total,
            hybrid_router_shadow_only_decision_total=self.hybrid_router_shadow_only_decision_total,
            hybrid_router_inv003_depth_degraded_total=self.hybrid_router_inv003_depth_degraded_total,
            hybrid_router_regime_input_clamped_total=self.hybrid_router_regime_input_clamped_total,
            hybrid_router_vol_zscore_unavailable_total=self.hybrid_router_vol_zscore_unavailable_total,
            ev_maker_bps=_distribution_summary(self._ev_maker),
            ev_taker_bps=_distribution_summary(self._ev_taker),
            p_fill_proxy=_distribution_summary(self._p_fill),
            participation_ratio=_distribution_summary(self._participation),
            expected_wait_s=_distribution_summary(self._expected_wait),
            expected_taker_slippage_bps=_distribution_summary(self._expected_taker_slippage),
            hybrid_router_p_fill_realized_vs_predicted_brier=_calibration_metric(self._p_fill_brier_terms),
            hybrid_router_wait_realized_vs_predicted_mae_s=_calibration_metric(self._wait_abs_errors),
            hybrid_router_taker_slippage_realized_vs_predicted_mae_bps=_calibration_metric(
                self._taker_slippage_abs_errors
            ),
            hybrid_router_maker_miss_cost_realized_vs_predicted_mae_bps=_calibration_metric(
                self._maker_miss_cost_abs_errors
            ),
            latest_routing_trace=self._latest_trace,
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
    "HybridRouterMetricsProjection",
    "HybridRouterMetricsSink",
    "HybridRouterTraceProjection",
]
