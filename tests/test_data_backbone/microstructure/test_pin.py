from __future__ import annotations

import pytest

from data_backbone.microstructure.pin import (
    PIN_METHOD_VERSION_HASH,
    PinParameterEstimate,
    compute_pin_from_parameters,
)


def test_pin_matches_formula_from_parameters() -> None:
    estimate = PinParameterEstimate(
        alpha=0.2,
        delta=0.4,
        mu=10.0,
        epsilon_b=4.0,
        epsilon_s=6.0,
        estimation_source="synthetic_em_fixture",
    )

    result = compute_pin_from_parameters(
        estimate,
        pair="btcusdt",
        computed_at_ns=1_000_000_000,
    )

    assert result.value == pytest.approx((0.2 * 10.0) / ((0.2 * 10.0) + 4.0 + 6.0))
    assert result.parameter_source == "synthetic_em_fixture"
    assert result.method_version_hash == PIN_METHOD_VERSION_HASH
    assert result.pair == "BTCUSDT"


def test_pin_stays_in_unit_interval() -> None:
    estimate = PinParameterEstimate(
        alpha=1.0,
        delta=0.0,
        mu=5.0,
        epsilon_b=0.0,
        epsilon_s=5.0,
        estimation_source="edge_case",
    )

    result = compute_pin_from_parameters(
        estimate,
        pair="ethusdt",
        computed_at_ns=1_000_000_000,
    )

    assert 0.0 <= result.value <= 1.0
    assert result.pair == "ETHUSDT"


def test_pin_rejects_zero_denominator() -> None:
    with pytest.raises(ValueError, match="denominator"):
        PinParameterEstimate(
            alpha=0.0,
            delta=0.0,
            mu=0.0,
            epsilon_b=0.0,
            epsilon_s=0.0,
            estimation_source="invalid",
        )
