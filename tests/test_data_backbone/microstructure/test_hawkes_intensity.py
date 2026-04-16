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

    with pytest.raises(ValueError, match="strictly ordered"):
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
