from __future__ import annotations

import math
from statistics import NormalDist

import pytest

from calibration_methods import (
    DeflatedSharpeRatioError,
    compute_deflated_sharpe_ratio,
    compute_deflated_sharpe_ratio_from_moments,
)


def _positive_return_series(length: int = 200) -> tuple[float, ...]:
    series: list[float] = []
    for index in range(length):
        base = 0.0025 + ((index % 9) - 4) * 0.00015
        seasonal = 0.0004 if index % 7 == 0 else -0.0001
        series.append(base + seasonal)
    return tuple(series)


def _moderate_return_series(length: int = 200) -> tuple[float, ...]:
    series: list[float] = []
    for index in range(length):
        seasonal = ((index % 11) - 5) * 0.0010 / 11.0
        kick = 0.0009 if index % 17 == 0 else -0.0003
        series.append(0.0003 + seasonal + kick)
    return tuple(series)


def _reference_dsr(
    returns: tuple[float, ...],
    *,
    trial_count: int,
) -> tuple[float, float, float, float, float, float]:
    mean_return = sum(returns) / len(returns)
    sample_std = math.sqrt(
        sum((value - mean_return) ** 2 for value in returns)
        / float(len(returns) - 1)
    )
    sharpe_ratio = mean_return / sample_std
    standardized = tuple((value - mean_return) / sample_std for value in returns)
    skewness = sum(value**3 for value in standardized) / len(standardized)
    kurtosis = sum(value**4 for value in standardized) / len(standardized)
    denominator_term = 1.0 - (skewness * sharpe_ratio) + (
        ((kurtosis - 1.0) / 4.0) * sharpe_ratio**2
    )
    sharpe_variance = denominator_term / float(len(returns) - 1)
    if trial_count <= 1:
        benchmark_sharpe = 0.0
    else:
        distribution = NormalDist()
        gamma_e = 0.5772156649015329
        variance_scale = math.sqrt(sharpe_variance)
        upper_quantile = distribution.inv_cdf(1.0 - (1.0 / trial_count))
        corrected_quantile = distribution.inv_cdf(
            1.0 - (1.0 / (trial_count * math.e))
        )
        benchmark_sharpe = variance_scale * (
            ((1.0 - gamma_e) * upper_quantile) + (gamma_e * corrected_quantile)
        )
    z_score = (
        (sharpe_ratio - benchmark_sharpe)
        * math.sqrt(len(returns) - 1)
        / math.sqrt(denominator_term)
    )
    dsr = NormalDist().cdf(z_score)
    return (
        mean_return,
        sample_std,
        sharpe_ratio,
        sharpe_variance,
        benchmark_sharpe,
        dsr,
    )


def test_dsr_is_high_for_stable_positive_series() -> None:
    result = compute_deflated_sharpe_ratio(
        _positive_return_series(),
        trial_count=8,
    )

    assert 0.95 <= result.dsr <= 1.0
    assert result.passes_floor is True
    assert result.benchmark_sharpe >= 0.0


def test_dsr_penalizes_multiple_trials() -> None:
    returns = _moderate_return_series()

    low_trial = compute_deflated_sharpe_ratio(returns, trial_count=1)
    high_trial = compute_deflated_sharpe_ratio(returns, trial_count=200)

    assert high_trial.benchmark_sharpe > low_trial.benchmark_sharpe
    assert high_trial.dsr < low_trial.dsr


def test_dsr_rejects_zero_variance_returns() -> None:
    with pytest.raises(DeflatedSharpeRatioError, match="standard deviation"):
        compute_deflated_sharpe_ratio((0.01, 0.01, 0.01, 0.01), trial_count=3)


def test_dsr_matches_current_api_reference_mapping() -> None:
    """Closure path B: verify the current returns-based seam field by field.

    This is an equivalence proof for the real API. It does not inject a paper
    table directly into the function signature.
    """

    returns = _moderate_return_series(length=160)
    trial_count = 20

    (
        expected_mean,
        expected_std,
        expected_sr,
        expected_variance,
        expected_benchmark,
        expected_dsr,
    ) = _reference_dsr(returns, trial_count=trial_count)
    result = compute_deflated_sharpe_ratio(
        returns,
        trial_count=trial_count,
        acceptance_floor=0.95,
    )

    assert result.observation_count == len(returns)
    assert result.trial_count == trial_count
    assert result.mean_return == pytest.approx(expected_mean)
    assert result.sample_std == pytest.approx(expected_std)
    assert result.sharpe_ratio == pytest.approx(expected_sr)
    assert result.sharpe_variance == pytest.approx(expected_variance)
    assert result.benchmark_sharpe == pytest.approx(expected_benchmark)
    assert result.dsr == pytest.approx(expected_dsr)
    assert result.passes_floor is (expected_dsr >= 0.95)


def test_dsr_from_moments_matches_returns_api_reference_mapping() -> None:
    returns = _moderate_return_series(length=160)
    trial_count = 20

    (
        expected_mean,
        expected_std,
        expected_sr,
        _expected_variance,
        _expected_benchmark,
        _expected_dsr,
    ) = _reference_dsr(returns, trial_count=trial_count)
    standardized = tuple((value - expected_mean) / expected_std for value in returns)
    skewness = sum(value**3 for value in standardized) / len(standardized)
    kurtosis = sum(value**4 for value in standardized) / len(standardized)

    returns_result = compute_deflated_sharpe_ratio(
        returns,
        trial_count=trial_count,
        acceptance_floor=0.95,
    )
    moments_result = compute_deflated_sharpe_ratio_from_moments(
        observation_count=len(returns),
        trial_count=trial_count,
        sharpe_ratio=expected_sr,
        skewness=skewness,
        kurtosis=kurtosis,
        sample_std=expected_std,
        acceptance_floor=0.95,
    )

    assert moments_result.method_version == "deflated_sharpe_ratio_from_moments_v1"
    assert moments_result.mean_return == pytest.approx(returns_result.mean_return)
    assert moments_result.sample_std == pytest.approx(returns_result.sample_std)
    assert moments_result.sharpe_ratio == pytest.approx(returns_result.sharpe_ratio)
    assert moments_result.sharpe_variance == pytest.approx(returns_result.sharpe_variance)
    assert moments_result.benchmark_sharpe == pytest.approx(returns_result.benchmark_sharpe)
    assert moments_result.dsr == pytest.approx(returns_result.dsr)
    assert moments_result.passes_floor is returns_result.passes_floor


def test_dsr_from_moments_table1_style_anchor_documents_trial_count_semantics() -> None:
    """Table-1-style seam: direct moments input, no raw returns required.

    `trial_count` remains the effective number of tested strategies / promotion
    trials. The seam is additive and does not alter the production returns API.
    """

    result = compute_deflated_sharpe_ratio_from_moments(
        observation_count=1_000,
        trial_count=20,
        sharpe_ratio=0.10,
        skewness=0.0,
        kurtosis=3.0,
        acceptance_floor=0.95,
    )

    assert result.observation_count == 1_000
    assert result.trial_count == 20
    assert result.sample_std == 1.0
    assert result.mean_return == pytest.approx(0.10)
    assert result.benchmark_sharpe > 0.0
    assert result.dsr < 0.95
    assert result.passes_floor is False
