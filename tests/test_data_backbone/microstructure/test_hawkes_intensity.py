from __future__ import annotations

import pytest

from data_backbone.microstructure.hawkes_intensity import (
    HAWKES_METHOD_VERSION_HASH,
    HawkesEventPoint,
    HawkesParameterEstimate,
    compute_hawkes_intensity,
)


def test_hawkes_intensity_matches_manual_sum() -> None:
    estimate = HawkesParameterEstimate(
        mu=0.2,
        alpha=0.5,
        beta=1.0,
        estimation_source="synthetic_mle_fixture",
    )
    events = [
        HawkesEventPoint(timestamp_ns=1_000_000_000),
        HawkesEventPoint(timestamp_ns=2_000_000_000),
        HawkesEventPoint(timestamp_ns=3_000_000_000),
    ]

    result = compute_hawkes_intensity(
        estimate,
        events,
        pair="btcusdt",
        computed_at_ns=4_000_000_000,
    )

    assert result.value > estimate.mu
    assert result.parameter_source == "synthetic_mle_fixture"
    assert result.method_version_hash == HAWKES_METHOD_VERSION_HASH
    assert result.pair == "BTCUSDT"
    assert result.n_events_used == 3
    assert result.window_used == pytest.approx((3, 2.0))


def test_hawkes_intensity_rejects_unordered_events() -> None:
    estimate = HawkesParameterEstimate(
        mu=0.1,
        alpha=0.2,
        beta=1.0,
        estimation_source="synthetic",
    )
    events = [
        HawkesEventPoint(timestamp_ns=2_000_000_000),
        HawkesEventPoint(timestamp_ns=1_000_000_000),
    ]

    with pytest.raises(ValueError, match="non-decreasing"):
        compute_hawkes_intensity(estimate, events, pair="BTCUSDT")


def test_hawkes_intensity_rejects_past_eval_time() -> None:
    estimate = HawkesParameterEstimate(
        mu=0.1,
        alpha=0.2,
        beta=1.0,
        estimation_source="synthetic",
    )
    events = [HawkesEventPoint(timestamp_ns=2_000_000_000)]

    with pytest.raises(ValueError, match="computed_at_ns"):
        compute_hawkes_intensity(
            estimate,
            events,
            pair="BTCUSDT",
            computed_at_ns=1_000_000_000,
        )


def test_hawkes_intensity_warns_when_decay_is_slow_relative_to_window() -> None:
    estimate = HawkesParameterEstimate(
        mu=0.1,
        alpha=0.1,
        beta=0.4,
        estimation_source="slow_decay_fixture",
    )
    events = [
        HawkesEventPoint(timestamp_ns=1_000_000_000),
        HawkesEventPoint(timestamp_ns=2_000_000_000),
        HawkesEventPoint(timestamp_ns=3_000_000_000),
    ]

    result = compute_hawkes_intensity(
        estimate,
        events,
        pair="BTCUSDT",
        computed_at_ns=4_000_000_000,
    )

    assert result.parameter_warning == "slow_decay_relative_to_window"
    assert result.low_sample_confidence is True
