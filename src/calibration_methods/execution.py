"""Shared Local IA Lab execution-calibration helpers for THR-X01 to THR-X05."""

from __future__ import annotations

import math
import statistics

from pydantic import BaseModel, Field

from calibration_methods.hard_cap_floor import (
    HumanHardCapPolicyResult,
    apply_human_maximum_cap,
)


class ExecutionCalibrationError(ValueError):
    """Raised when bounded execution-calibration inputs are invalid."""


class HampelFilterResult(BaseModel, frozen=True):
    """Audit-ready result of a Hampel filter pass."""

    method_version: str = "hampel_filter_v1"
    window_size: int = Field(..., ge=1)
    k: float = Field(..., gt=0.0)
    input_count: int = Field(..., ge=0)
    kept_count: int = Field(..., ge=0)
    dropped_count: int = Field(..., ge=0)
    kept_values: tuple[float, ...] = ()
    dropped_indices: tuple[int, ...] = ()


class ExecutionThresholdEstimate(BaseModel, frozen=True):
    """One bounded execution threshold estimate."""

    method_version: str = "execution_threshold_estimate_v1"
    method: str = Field(..., min_length=1)
    unit: str = Field(..., min_length=1)
    quantile: float = Field(..., gt=0.0, lt=1.0)
    observation_count: int = Field(..., ge=0)
    filtered_observation_count: int = Field(..., ge=0)
    point_estimate: float = Field(..., ge=0.0)
    published_value: float = Field(..., ge=0.0)
    additive_margin: float = Field(default=0.0, ge=0.0)
    hard_cap_human: float = Field(..., gt=0.0)
    hard_cap_satisfied: bool
    hard_cap_binding: bool
    cap_policy: HumanHardCapPolicyResult
    hampel_filter: HampelFilterResult | None = None


class ExecutionSlippageModelEstimate(BaseModel, frozen=True):
    """One bounded service-owned slippage model estimate."""

    method_version: str = "execution_slippage_model_estimate_v1"
    method: str = Field(..., min_length=1)
    unit: str = Field(default="bps", min_length=1)
    size_proxy: str = Field(..., min_length=1)
    observation_count: int = Field(..., ge=0)
    filtered_observation_count: int = Field(..., ge=0)
    intercept_bps: float
    sqrt_size_coefficient: float = Field(..., ge=0.0)
    r_squared: float = Field(..., ge=0.0, le=1.0)
    mean_absolute_error_bps: float = Field(..., ge=0.0)
    min_required_r_squared: float = Field(..., ge=0.0, le=1.0)
    reference_size: float = Field(..., gt=0.0)
    reference_prediction_bps: float = Field(..., ge=0.0)


def apply_hampel_filter(
    values: tuple[float, ...],
    *,
    window_size: int = 60,
    k: float = 3.0,
) -> HampelFilterResult:
    """Remove bounded outliers with a Hampel filter."""

    if window_size <= 0:
        raise ExecutionCalibrationError("window_size must be > 0")
    if k <= 0.0:
        raise ExecutionCalibrationError("k must be > 0")
    _validate_finite_series(values, name="values")
    if not values:
        raise ExecutionCalibrationError("Hampel filter requires at least one observation")

    radius = max(window_size // 2, 1)
    kept_values: list[float] = []
    dropped_indices: list[int] = []
    for index, value in enumerate(values):
        start = max(0, index - radius)
        end = min(len(values), index + radius + 1)
        window = values[start:end]
        median = statistics.median(window)
        abs_deviations = tuple(abs(item - median) for item in window)
        mad = statistics.median(abs_deviations)
        if mad <= 0.0:
            kept_values.append(value)
            continue
        scaled_mad = 1.4826 * mad
        if abs(value - median) > k * scaled_mad:
            dropped_indices.append(index)
            continue
        kept_values.append(value)

    return HampelFilterResult(
        window_size=window_size,
        k=k,
        input_count=len(values),
        kept_count=len(kept_values),
        dropped_count=len(dropped_indices),
        kept_values=tuple(kept_values),
        dropped_indices=tuple(dropped_indices),
    )


def calibrate_time_sync_threshold_ms(
    offsets_ms: tuple[float, ...],
    *,
    quantile: float = 0.999,
    additive_margin_ms: float = 200.0,
    hard_cap_ms: float = 1000.0,
    hampel_window_size: int = 60,
    hampel_k: float = 3.0,
) -> ExecutionThresholdEstimate:
    """Calibrate THR-X01 from local/server clock offsets."""

    if additive_margin_ms < 0.0:
        raise ExecutionCalibrationError("additive_margin_ms must be >= 0")
    filtered = apply_hampel_filter(offsets_ms, window_size=hampel_window_size, k=hampel_k)
    if not filtered.kept_values:
        raise ExecutionCalibrationError("THR-X01 calibration requires kept Hampel observations")
    absolute_offsets = tuple(abs(value) for value in filtered.kept_values)
    point_estimate = empirical_quantile(absolute_offsets, quantile=quantile) + additive_margin_ms
    cap_policy = apply_human_maximum_cap(point_estimate, hard_cap_ms)
    return ExecutionThresholdEstimate(
        method="hampel_abs_quantile_plus_margin",
        unit="ms",
        quantile=quantile,
        observation_count=len(offsets_ms),
        filtered_observation_count=len(filtered.kept_values),
        point_estimate=point_estimate,
        published_value=cap_policy.published_value,
        additive_margin=additive_margin_ms,
        hard_cap_human=hard_cap_ms,
        hard_cap_satisfied=cap_policy.hard_cap_satisfied,
        hard_cap_binding=cap_policy.hard_cap_binding,
        cap_policy=cap_policy,
        hampel_filter=filtered,
    )


def calibrate_websocket_gap_threshold_s(
    interarrival_s: tuple[float, ...],
    *,
    quantile: float = 0.9999,
    hard_cap_s: float = 5.0,
) -> ExecutionThresholdEstimate:
    """Calibrate THR-X02 from websocket inter-arrival times."""

    _validate_non_negative_series(interarrival_s, name="interarrival_s")
    if not interarrival_s:
        raise ExecutionCalibrationError("THR-X02 calibration requires at least one observation")
    point_estimate = empirical_quantile(interarrival_s, quantile=quantile)
    cap_policy = apply_human_maximum_cap(point_estimate, hard_cap_s)
    return ExecutionThresholdEstimate(
        method="empirical_quantile_capped",
        unit="s",
        quantile=quantile,
        observation_count=len(interarrival_s),
        filtered_observation_count=len(interarrival_s),
        point_estimate=point_estimate,
        published_value=cap_policy.published_value,
        additive_margin=0.0,
        hard_cap_human=hard_cap_s,
        hard_cap_satisfied=cap_policy.hard_cap_satisfied,
        hard_cap_binding=cap_policy.hard_cap_binding,
        cap_policy=cap_policy,
    )


def calibrate_spread_guard_threshold_bps(
    spread_bps: tuple[float, ...],
    *,
    hard_cap_bps: float = 50.0,
) -> ExecutionThresholdEstimate:
    """Calibrate THR-X04 from observed relative spreads in bps."""

    _validate_non_negative_series(spread_bps, name="spread_bps")
    strictly_positive = tuple(value for value in spread_bps if value > 0.0)
    if not strictly_positive:
        raise ExecutionCalibrationError(
            "THR-X04 calibration requires at least one strictly positive spread sample"
        )
    log_values = tuple(math.log(value) for value in strictly_positive)
    mean_log = statistics.fmean(log_values)
    sigma_log = statistics.pstdev(log_values) if len(log_values) > 1 else 0.0
    point_estimate = math.exp(mean_log + 2.0 * sigma_log)
    cap_policy = apply_human_maximum_cap(point_estimate, hard_cap_bps)
    return ExecutionThresholdEstimate(
        method="lognormal_mu_plus_2sigma_capped",
        unit="bps",
        quantile=0.97725,
        observation_count=len(spread_bps),
        filtered_observation_count=len(strictly_positive),
        point_estimate=point_estimate,
        published_value=cap_policy.published_value,
        additive_margin=0.0,
        hard_cap_human=hard_cap_bps,
        hard_cap_satisfied=cap_policy.hard_cap_satisfied,
        hard_cap_binding=cap_policy.hard_cap_binding,
        cap_policy=cap_policy,
    )


def calibrate_rate_limit_throttle_ratio(
    *,
    quota_call_counts: tuple[int, ...] = (),
    quota_probe_durations_s: tuple[float, ...] = (),
    quota_limit_calls_per_minute_values: tuple[int, ...],
    observed_calls_per_minute: tuple[float, ...] = (),
    quantile: float = 0.95,
    burst_horizon_minutes: float = 1.0,
    burst_margin_multiplier: float = 1.5,
    hard_cap_quota_ratio: float = 0.80,
) -> ExecutionThresholdEstimate:
    """Calibrate THR-X03 from service-owned REST quota probe telemetry."""

    if burst_horizon_minutes <= 0.0:
        raise ExecutionCalibrationError("burst_horizon_minutes must be > 0")
    if burst_margin_multiplier <= 0.0:
        raise ExecutionCalibrationError("burst_margin_multiplier must be > 0")
    if hard_cap_quota_ratio <= 0.0:
        raise ExecutionCalibrationError("hard_cap_quota_ratio must be > 0")
    _validate_non_negative_series(quota_call_counts, name="quota_call_counts")
    _validate_positive_series(
        quota_limit_calls_per_minute_values,
        name="quota_limit_calls_per_minute_values",
    )

    if observed_calls_per_minute:
        _validate_non_negative_series(
            observed_calls_per_minute,
            name="observed_calls_per_minute",
        )
        rate_series = tuple(float(value) for value in observed_calls_per_minute)
    else:
        _validate_positive_series(
            quota_probe_durations_s,
            name="quota_probe_durations_s",
        )
        if not quota_call_counts or not quota_probe_durations_s:
            raise ExecutionCalibrationError(
                "THR-X03 calibration requires observed calls/minute or call_count + probe_duration telemetry"
            )
        if len(quota_call_counts) != len(quota_probe_durations_s):
            raise ExecutionCalibrationError(
                "THR-X03 call counts and probe durations must stay aligned"
            )
        rate_series = tuple(
            (call_count / duration_s) * 60.0
            for call_count, duration_s in zip(quota_call_counts, quota_probe_durations_s)
        )

    if not rate_series:
        raise ExecutionCalibrationError(
            "THR-X03 calibration requires at least one quota rate observation"
        )

    quota_cap = float(min(quota_limit_calls_per_minute_values))
    lambda_quantile = empirical_quantile(rate_series, quantile=quantile)
    point_estimate = (
        lambda_quantile * burst_horizon_minutes * burst_margin_multiplier
    ) / quota_cap
    cap_policy = apply_human_maximum_cap(point_estimate, hard_cap_quota_ratio)
    return ExecutionThresholdEstimate(
        method="little_law_burst_margin_capped",
        unit="quota_ratio",
        quantile=quantile,
        observation_count=len(rate_series),
        filtered_observation_count=len(rate_series),
        point_estimate=point_estimate,
        published_value=cap_policy.published_value,
        additive_margin=0.0,
        hard_cap_human=hard_cap_quota_ratio,
        hard_cap_satisfied=cap_policy.hard_cap_satisfied,
        hard_cap_binding=cap_policy.hard_cap_binding,
        cap_policy=cap_policy,
    )


def calibrate_slippage_model_bps(
    slippage_bps: tuple[float, ...],
    *,
    candidate_sizes: tuple[float, ...] = (),
    final_sizes: tuple[float, ...] = (),
    min_r_squared: float = 0.30,
    reference_quantile: float = 0.95,
    huber_k: float = 1.345,
) -> ExecutionSlippageModelEstimate:
    """Calibrate THR-X05 from service-owned size/slippage telemetry."""

    if not 0.0 < min_r_squared <= 1.0:
        raise ExecutionCalibrationError("min_r_squared must be in (0, 1]")
    _validate_non_negative_series(slippage_bps, name="slippage_bps")
    if not slippage_bps:
        raise ExecutionCalibrationError(
            "THR-X05 calibration requires at least one slippage observation"
        )
    size_proxy, size_series = _select_slippage_size_series(
        slippage_bps=slippage_bps,
        candidate_sizes=candidate_sizes,
        final_sizes=final_sizes,
    )
    sqrt_sizes = tuple(math.sqrt(value) for value in size_series)
    intercept_bps, sqrt_size_coefficient = _fit_huber_linear_regression(
        x=sqrt_sizes,
        y=slippage_bps,
        k=huber_k,
    )
    if sqrt_size_coefficient < 0.0:
        raise ExecutionCalibrationError(
            "THR-X05 calibration produced a negative size slope"
        )

    predictions = tuple(
        max(0.0, intercept_bps + sqrt_size_coefficient * value) for value in sqrt_sizes
    )
    r_squared = _coefficient_of_determination(
        actual=slippage_bps,
        predicted=predictions,
    )
    if r_squared < min_r_squared:
        raise ExecutionCalibrationError(
            f"THR-X05 model r_squared {r_squared:.6f} < required {min_r_squared:.6f}"
        )
    mean_absolute_error_bps = statistics.fmean(
        tuple(abs(actual - predicted) for actual, predicted in zip(slippage_bps, predictions))
    )
    reference_size = empirical_quantile(size_series, quantile=reference_quantile)
    reference_prediction_bps = max(
        0.0,
        intercept_bps + sqrt_size_coefficient * math.sqrt(reference_size),
    )
    return ExecutionSlippageModelEstimate(
        method="sqrt_size_huber_linear_v1",
        size_proxy=size_proxy,
        observation_count=len(slippage_bps),
        filtered_observation_count=len(slippage_bps),
        intercept_bps=intercept_bps,
        sqrt_size_coefficient=sqrt_size_coefficient,
        r_squared=r_squared,
        mean_absolute_error_bps=mean_absolute_error_bps,
        min_required_r_squared=min_r_squared,
        reference_size=reference_size,
        reference_prediction_bps=reference_prediction_bps,
    )


def empirical_quantile(values: tuple[float, ...], *, quantile: float) -> float:
    """Return the bounded empirical quantile via nearest-rank selection."""

    if not 0.0 < quantile < 1.0:
        raise ExecutionCalibrationError("quantile must be strictly between 0 and 1")
    _validate_finite_series(values, name="values")
    if not values:
        raise ExecutionCalibrationError("empirical_quantile requires at least one observation")
    ordered = sorted(values)
    index = max(0, math.ceil(len(ordered) * quantile) - 1)
    return float(ordered[index])


def _validate_finite_series(values: tuple[float, ...], *, name: str) -> None:
    if any(not math.isfinite(value) for value in values):
        raise ExecutionCalibrationError(f"{name} must contain only finite values")


def _validate_positive_series(values: tuple[float, ...] | tuple[int, ...], *, name: str) -> None:
    _validate_finite_series(tuple(float(value) for value in values), name=name)
    if any(float(value) <= 0.0 for value in values):
        raise ExecutionCalibrationError(f"{name} must contain only strictly positive values")


def _validate_non_negative_series(values: tuple[float, ...], *, name: str) -> None:
    _validate_finite_series(values, name=name)
    if any(value < 0.0 for value in values):
        raise ExecutionCalibrationError(f"{name} must contain only non-negative values")


def _select_slippage_size_series(
    *,
    slippage_bps: tuple[float, ...],
    candidate_sizes: tuple[float, ...],
    final_sizes: tuple[float, ...],
) -> tuple[str, tuple[float, ...]]:
    if final_sizes and len(final_sizes) == len(slippage_bps):
        _validate_positive_series(final_sizes, name="final_sizes")
        return "final_size", tuple(float(value) for value in final_sizes)
    if candidate_sizes and len(candidate_sizes) == len(slippage_bps):
        _validate_positive_series(candidate_sizes, name="candidate_sizes")
        return "candidate_size", tuple(float(value) for value in candidate_sizes)
    raise ExecutionCalibrationError(
        "THR-X05 calibration requires size telemetry aligned with slippage observations"
    )


def _fit_huber_linear_regression(
    *,
    x: tuple[float, ...],
    y: tuple[float, ...],
    k: float,
    max_iter: int = 25,
    tolerance: float = 1e-8,
) -> tuple[float, float]:
    if len(x) != len(y):
        raise ExecutionCalibrationError("x and y must have the same length")
    if len(x) < 2:
        raise ExecutionCalibrationError("Huber regression requires at least two observations")
    if k <= 0.0:
        raise ExecutionCalibrationError("Huber regression requires k > 0")
    if max(x) == min(x):
        raise ExecutionCalibrationError("Huber regression requires varying size observations")

    weights = tuple(1.0 for _ in x)
    intercept, slope = _weighted_linear_regression(x=x, y=y, weights=weights)
    for _ in range(max_iter):
        residuals = tuple(actual - (intercept + slope * value) for value, actual in zip(x, y))
        median_residual = statistics.median(residuals)
        mad = statistics.median(tuple(abs(value - median_residual) for value in residuals))
        scale = 1.4826 * mad
        if scale <= 1e-12:
            break
        threshold = k * scale
        new_weights = tuple(
            1.0 if abs(residual) <= threshold else threshold / abs(residual)
            for residual in residuals
        )
        new_intercept, new_slope = _weighted_linear_regression(
            x=x,
            y=y,
            weights=new_weights,
        )
        if (
            max(abs(new_intercept - intercept), abs(new_slope - slope))
            <= tolerance
        ):
            intercept, slope = new_intercept, new_slope
            break
        weights = new_weights
        intercept, slope = new_intercept, new_slope
    return intercept, slope


def _weighted_linear_regression(
    *,
    x: tuple[float, ...],
    y: tuple[float, ...],
    weights: tuple[float, ...],
) -> tuple[float, float]:
    if len(x) != len(y) or len(x) != len(weights):
        raise ExecutionCalibrationError("weighted regression inputs must stay aligned")
    total_weight = math.fsum(weights)
    if total_weight <= 0.0:
        raise ExecutionCalibrationError("weighted regression requires positive total weight")
    mean_x = math.fsum(weight * value for weight, value in zip(weights, x)) / total_weight
    mean_y = math.fsum(weight * value for weight, value in zip(weights, y)) / total_weight
    centered_var_x = math.fsum(
        weight * (value - mean_x) ** 2 for weight, value in zip(weights, x)
    )
    if centered_var_x <= 0.0:
        raise ExecutionCalibrationError("weighted regression requires varying x")
    centered_cov_xy = math.fsum(
        weight * (value - mean_x) * (target - mean_y)
        for weight, value, target in zip(weights, x, y)
    )
    slope = centered_cov_xy / centered_var_x
    intercept = mean_y - slope * mean_x
    return intercept, slope


def _coefficient_of_determination(
    *,
    actual: tuple[float, ...],
    predicted: tuple[float, ...],
) -> float:
    if len(actual) != len(predicted):
        raise ExecutionCalibrationError("R^2 inputs must stay aligned")
    if not actual:
        raise ExecutionCalibrationError("R^2 requires at least one observation")
    mean_actual = statistics.fmean(actual)
    total_sum_squares = math.fsum((value - mean_actual) ** 2 for value in actual)
    residual_sum_squares = math.fsum(
        (value - estimate) ** 2 for value, estimate in zip(actual, predicted)
    )
    if total_sum_squares <= 0.0:
        return 1.0 if residual_sum_squares <= 1e-12 else 0.0
    return max(0.0, min(1.0, 1.0 - residual_sum_squares / total_sum_squares))


__all__ = [
    "ExecutionCalibrationError",
    "ExecutionSlippageModelEstimate",
    "ExecutionThresholdEstimate",
    "HampelFilterResult",
    "apply_hampel_filter",
    "calibrate_rate_limit_throttle_ratio",
    "calibrate_slippage_model_bps",
    "calibrate_spread_guard_threshold_bps",
    "calibrate_time_sync_threshold_ms",
    "calibrate_websocket_gap_threshold_s",
    "empirical_quantile",
]
