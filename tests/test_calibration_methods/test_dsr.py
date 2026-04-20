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


def test_dsr_table1_mapping_anchor() -> None:
    """DSR anchor: Bailey et al. (2014) Table 1 mapped onto the current API.

    The current implementation returns:
    - `sharpe_ratio`: observed sample Sharpe
    - `benchmark_sharpe`: multiple-testing-adjusted hurdle
    - `dsr`: probability that observed SR beats the adjusted hurdle

    For the Table 1-style modest-SR scenario (mu≈0.5/12, n=1000, trial_count=20),
    the current API should show:
    - benchmark_sharpe > sharpe_ratio
    - passes_floor is False for acceptance_floor=0.95

    Reference: Bailey, Borwein, Lopez de Prado & Zhu (2014), Table 1.
    """
    import random

    rng = random.Random(20240422)
    mu_monthly = 0.5 / 12.0
    returns = tuple(rng.gauss(mu_monthly, 1.0) for _ in range(1000))

    result = compute_deflated_sharpe_ratio(
        returns,
        trial_count=20,
        acceptance_floor=0.95,
    )

    assert result.observation_count == 1000
    assert result.trial_count == 20
    assert result.benchmark_sharpe > result.sharpe_ratio
    assert result.dsr < result.acceptance_floor
    assert result.passes_floor is False
