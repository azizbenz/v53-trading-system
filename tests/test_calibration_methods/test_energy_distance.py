"""Tests for the scaled energy-distance seam."""

from __future__ import annotations

import random

import pytest

from calibration_methods.energy_distance import (
    EnergyDistanceError,
    EnergyDistanceResult,
    _energy_statistic,
    compute_energy_distance_test,
)


def _gaussian_pair(
    *,
    size: int,
    seed_x: int,
    seed_y: int,
    mean_x: float = 0.0,
    mean_y: float = 0.0,
    sigma_x: float = 1.0,
    sigma_y: float = 1.0,
) -> tuple[tuple[float, ...], tuple[float, ...]]:
    rng_x = random.Random(seed_x)
    rng_y = random.Random(seed_y)
    x = tuple(rng_x.gauss(mean_x, sigma_x) for _ in range(size))
    y = tuple(rng_y.gauss(mean_y, sigma_y) for _ in range(size))
    return x, y


def _null_scaled_threshold(*, size: int, seeds: range) -> float:
    null_statistics = []
    for seed in seeds:
        x, y = _gaussian_pair(size=size, seed_x=seed, seed_y=seed + 10_000)
        null_statistics.append(_energy_statistic(x, y))
    ordered = sorted(null_statistics)
    index = int(0.95 * (len(ordered) - 1))
    return ordered[index]


def test_energy_statistic_is_zero_for_identical_data() -> None:
    data = (0.1, 0.2, 0.3, 0.4, 0.5)
    assert _energy_statistic(data, data) == 0.0


def test_energy_statistic_positive_for_different_data() -> None:
    x, y = _gaussian_pair(size=50, seed_x=0, seed_y=1, mean_y=5.0)
    stat = _energy_statistic(x, y)
    assert stat > 0.0


def test_energy_statistic_exceeds_half_point_for_unit_mean_shift_anchor() -> None:
    x, y = _gaussian_pair(size=500, seed_x=20260420, seed_y=20260421, mean_y=1.0)
    stat = _energy_statistic(x, y)
    assert stat > 0.5


def test_energy_statistic_is_symmetric() -> None:
    x, y = _gaussian_pair(size=30, seed_x=1, seed_y=2, mean_y=1.0)
    assert abs(_energy_statistic(x, y) - _energy_statistic(y, x)) < 1e-10


def test_energy_statistic_increases_with_separation() -> None:
    base, shifted_small = _gaussian_pair(size=50, seed_x=2, seed_y=2, mean_y=1.0)
    _, shifted_large = _gaussian_pair(size=50, seed_x=2, seed_y=2, mean_y=5.0)
    e_small = _energy_statistic(base, shifted_small)
    e_large = _energy_statistic(base, shifted_large)
    assert e_large > e_small


def test_energy_test_returns_result_type() -> None:
    x, y = _gaussian_pair(size=40, seed_x=10, seed_y=11, sigma_x=0.01, sigma_y=0.01)
    result = compute_energy_distance_test(x, y, n_permutations=99)
    assert isinstance(result, EnergyDistanceResult)
    assert result.method_version == "energy_distance_permutation_v1"


def test_energy_test_pvalue_in_bounds() -> None:
    x, y = _gaussian_pair(size=40, seed_x=11, seed_y=12, sigma_x=0.01, sigma_y=0.01)
    result = compute_energy_distance_test(x, y, n_permutations=99)
    assert 0.0 <= result.p_value <= 1.0


def test_energy_test_same_dist_high_pvalue() -> None:
    x, y = _gaussian_pair(size=50, seed_x=12, seed_y=13, sigma_x=0.01, sigma_y=0.01)
    result = compute_energy_distance_test(
        x, y, acceptance_floor=0.05, n_permutations=199, random_seed=12
    )
    assert result.passes_floor is (result.p_value >= 0.05)


def test_energy_test_different_dist_low_pvalue() -> None:
    x, y = _gaussian_pair(
        size=60,
        seed_x=13,
        seed_y=14,
        mean_y=0.1,
        sigma_x=0.01,
        sigma_y=0.01,
    )
    result = compute_energy_distance_test(
        x, y, acceptance_floor=0.05, n_permutations=199, random_seed=13
    )
    assert result.p_value < 0.05


def test_energy_test_passes_floor_consistency() -> None:
    x, y = _gaussian_pair(
        size=40,
        seed_x=14,
        seed_y=15,
        mean_y=0.02,
        sigma_x=0.01,
        sigma_y=0.01,
    )
    result = compute_energy_distance_test(
        x, y, acceptance_floor=0.10, n_permutations=99, random_seed=14
    )
    assert result.passes_floor is (result.p_value >= 0.10)


def test_energy_test_counts_correct() -> None:
    x, _ = _gaussian_pair(size=35, seed_x=15, seed_y=16, sigma_x=0.01, sigma_y=0.01)
    _, y = _gaussian_pair(size=45, seed_x=17, seed_y=18, sigma_x=0.01, sigma_y=0.01)
    result = compute_energy_distance_test(x, y, n_permutations=99)
    assert result.n_shadow == 35
    assert result.n_backtest == 45
    assert result.n_permutations == 99


def test_energy_test_reproducible_with_seed() -> None:
    x, y = _gaussian_pair(
        size=50,
        seed_x=99,
        seed_y=100,
        mean_y=0.005,
        sigma_x=0.01,
        sigma_y=0.01,
    )
    r1 = compute_energy_distance_test(x, y, n_permutations=99, random_seed=42)
    r2 = compute_energy_distance_test(x, y, n_permutations=99, random_seed=42)
    assert r1.p_value == r2.p_value
    assert r1.energy_statistic == r2.energy_statistic


def test_energy_test_rejects_fewer_than_2_in_shadow() -> None:
    with pytest.raises(EnergyDistanceError, match="at least 2"):
        compute_energy_distance_test([0.01], [0.01, 0.02, 0.03])


def test_energy_test_rejects_fewer_than_2_in_backtest() -> None:
    with pytest.raises(EnergyDistanceError, match="at least 2"):
        compute_energy_distance_test([0.01, 0.02], [0.01])


def test_energy_test_rejects_non_finite() -> None:
    with pytest.raises(EnergyDistanceError, match="finite"):
        compute_energy_distance_test(
            [0.01, float("inf")], [0.01, 0.02], n_permutations=99
        )


def test_energy_test_rejects_too_few_permutations() -> None:
    with pytest.raises(EnergyDistanceError, match="n_permutations"):
        compute_energy_distance_test([0.01, 0.02], [0.01, 0.02], n_permutations=50)


def test_energy_test_rejects_invalid_floor() -> None:
    with pytest.raises(EnergyDistanceError, match="acceptance_floor"):
        compute_energy_distance_test(
            [0.01, 0.02], [0.01, 0.02], acceptance_floor=2.0, n_permutations=99
        )


def test_energy_distance_same_distribution_uses_scaled_null_envelope() -> None:
    """Closure path B under H0: threshold comes from the scaled seam's own null."""

    threshold = _null_scaled_threshold(size=48, seeds=range(310, 334))
    shadow, backtest = _gaussian_pair(
        size=48,
        seed_x=20240424,
        seed_y=20240425,
    )

    observed = _energy_statistic(shadow, backtest)
    result = compute_energy_distance_test(
        shadow,
        backtest,
        n_permutations=299,
        random_seed=20240424,
        acceptance_floor=0.05,
    )

    assert observed <= threshold
    assert result.p_value > 0.05
    assert result.passes_floor is True


def test_energy_distance_scaled_statistic_separates_shift_from_null_envelope() -> None:
    """Closure path B under H1: strong shift clears the scaled-stat null envelope."""

    threshold = _null_scaled_threshold(size=48, seeds=range(310, 334))
    shadow, backtest = _gaussian_pair(
        size=48,
        seed_x=20240426,
        seed_y=20240427,
        mean_y=0.75,
    )

    observed = _energy_statistic(shadow, backtest)
    result = compute_energy_distance_test(
        shadow,
        backtest,
        n_permutations=299,
        random_seed=20240426,
        acceptance_floor=0.05,
    )

    assert observed > threshold
    assert result.p_value < 0.05
    assert result.passes_floor is False
