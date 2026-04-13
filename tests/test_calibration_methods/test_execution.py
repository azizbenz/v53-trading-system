from __future__ import annotations

from calibration_methods.execution import (
    apply_hampel_filter,
    calibrate_rate_limit_throttle_ratio,
    calibrate_slippage_model_bps,
    calibrate_spread_guard_threshold_bps,
    calibrate_time_sync_threshold_ms,
    calibrate_websocket_gap_threshold_s,
)


def test_hampel_filter_drops_large_outlier():
    result = apply_hampel_filter((20.0, 25.0, 30.0, 4_000.0, 35.0), window_size=3, k=3.0)

    assert result.input_count == 5
    assert result.kept_count == 4
    assert result.dropped_count == 1
    assert result.dropped_indices == (3,)


def test_calibrate_time_sync_threshold_ms_adds_margin_after_hampel_filter():
    estimate = calibrate_time_sync_threshold_ms(
        (20.0, 25.0, 30.0, 4_000.0, 35.0),
        quantile=0.999,
        additive_margin_ms=200.0,
        hard_cap_ms=1_000.0,
        hampel_window_size=3,
        hampel_k=3.0,
    )

    assert estimate.method == "hampel_abs_quantile_plus_margin"
    assert estimate.filtered_observation_count == 4
    assert estimate.point_estimate == 235.0
    assert estimate.published_value == 235.0
    assert estimate.hard_cap_binding is False


def test_calibrate_websocket_gap_threshold_caps_large_quantile():
    estimate = calibrate_websocket_gap_threshold_s((0.1, 0.2, 8.0), quantile=0.9999, hard_cap_s=5.0)

    assert estimate.method == "empirical_quantile_capped"
    assert estimate.point_estimate == 8.0
    assert estimate.published_value == 5.0
    assert estimate.hard_cap_binding is True


def test_calibrate_spread_guard_threshold_bps_uses_lognormal_envelope():
    estimate = calibrate_spread_guard_threshold_bps((2.0, 3.0, 4.0, 6.0), hard_cap_bps=50.0)

    assert estimate.method == "lognormal_mu_plus_2sigma_capped"
    assert estimate.unit == "bps"
    assert estimate.filtered_observation_count == 4
    assert estimate.point_estimate > 4.0
    assert estimate.published_value <= 50.0
    assert estimate.hard_cap_binding is False


def test_calibrate_rate_limit_throttle_ratio_caps_at_human_quota_ceiling():
    estimate = calibrate_rate_limit_throttle_ratio(
        quota_call_counts=(8, 9, 10),
        quota_probe_durations_s=(4.0, 4.5, 5.0),
        quota_limit_calls_per_minute_values=(120, 120, 120),
        observed_calls_per_minute=(120.0, 120.0, 120.0),
    )

    assert estimate.method == "little_law_burst_margin_capped"
    assert estimate.unit == "quota_ratio"
    assert estimate.point_estimate == 1.5
    assert estimate.published_value == 0.8
    assert estimate.hard_cap_binding is True


def test_calibrate_slippage_model_bps_fits_positive_sqrt_size_relation():
    model = calibrate_slippage_model_bps(
        (1.5, 1.8, 2.0, 2.4),
        final_sizes=(6.0, 9.0, 12.0, 16.0),
    )

    assert model.method == "sqrt_size_huber_linear_v1"
    assert model.size_proxy == "final_size"
    assert model.observation_count == 4
    assert model.sqrt_size_coefficient > 0.0
    assert model.r_squared >= 0.3
    assert model.reference_size > 0.0
    assert model.reference_prediction_bps > 0.0
