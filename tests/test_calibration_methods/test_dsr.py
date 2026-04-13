from __future__ import annotations

import pytest

from calibration_methods import DeflatedSharpeRatioError, compute_deflated_sharpe_ratio


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


def test_dsr_is_high_for_stable_positive_series():
    result = compute_deflated_sharpe_ratio(
        _positive_return_series(),
        trial_count=8,
    )

    assert 0.95 <= result.dsr <= 1.0
    assert result.passes_floor is True
    assert result.benchmark_sharpe >= 0.0


def test_dsr_penalizes_multiple_trials():
    returns = _moderate_return_series()

    low_trial = compute_deflated_sharpe_ratio(returns, trial_count=1)
    high_trial = compute_deflated_sharpe_ratio(returns, trial_count=200)

    assert high_trial.benchmark_sharpe > low_trial.benchmark_sharpe
    assert high_trial.dsr < low_trial.dsr


def test_dsr_rejects_zero_variance_returns():
    with pytest.raises(DeflatedSharpeRatioError, match="standard deviation"):
        compute_deflated_sharpe_ratio((0.01, 0.01, 0.01, 0.01), trial_count=3)
