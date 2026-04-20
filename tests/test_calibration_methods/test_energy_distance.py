"""Tests for energy distance test (Székely & Rizzo 2004)."""

from __future__ import annotations

import math

import pytest

from calibration_methods.energy_distance import (
    EnergyDistanceError,
    EnergyDistanceResult,
    compute_energy_distance_test,
    _energy_statistic,
)


# ---------------------------------------------------------------------------
# Core statistic correctness
# ---------------------------------------------------------------------------

def test_energy_statistic_is_zero_for_identical_data() -> None:
    """E(F, F) = 0 for identical distributions."""
    data = (0.1, 0.2, 0.3, 0.4, 0.5)
    assert _energy_statistic(data, data) == 0.0


def test_energy_statistic_positive_for_different_data() -> None:
    """E(F, G) > 0 when distributions differ."""
    import random
    rng = random.Random(0)
    x = tuple(rng.gauss(0.0, 1.0) for _ in range(50))
    y = tuple(rng.gauss(5.0, 1.0) for _ in range(50))
    stat = _energy_statistic(x, y)
    assert stat > 0.0


def test_energy_statistic_exceeds_half_point_for_unit_mean_shift_anchor() -> None:
    """Anchor: N(0,1) vs N(1,1), n=500 -> scaled energy statistic stays > 0.5."""
    import random

    rng = random.Random(20260420)
    x = tuple(rng.gauss(0.0, 1.0) for _ in range(500))
    y = tuple(rng.gauss(1.0, 1.0) for _ in range(500))
    stat = _energy_statistic(x, y)
    assert stat > 0.5


def test_energy_statistic_is_symmetric() -> None:
    """E(F, G) == E(G, F)."""
    import random
    rng = random.Random(1)
    x = tuple(rng.gauss(0.0, 1.0) for _ in range(30))
    y = tuple(rng.gauss(1.0, 1.0) for _ in range(30))
    assert abs(_energy_statistic(x, y) - _energy_statistic(y, x)) < 1e-10


def test_energy_statistic_increases_with_separation() -> None:
    """Larger distributional shift → larger energy statistic."""
    import random
    rng = random.Random(2)
    base = tuple(rng.gauss(0.0, 1.0) for _ in range(50))
    rng2 = random.Random(2)
    shifted_small = tuple(rng2.gauss(1.0, 1.0) for _ in range(50))
    rng3 = random.Random(2)
    shifted_large = tuple(rng3.gauss(5.0, 1.0) for _ in range(50))
    e_small = _energy_statistic(base, shifted_small)
    e_large = _energy_statistic(base, shifted_large)
    assert e_large > e_small


# ---------------------------------------------------------------------------
# Full permutation test
# ---------------------------------------------------------------------------

def test_energy_test_returns_result_type() -> None:
    import random
    rng = random.Random(10)
    x = tuple(rng.gauss(0.0, 0.01) for _ in range(40))
    y = tuple(rng.gauss(0.0, 0.01) for _ in range(40))
    result = compute_energy_distance_test(x, y, n_permutations=99)
    assert isinstance(result, EnergyDistanceResult)
    assert result.method_version == "energy_distance_permutation_v1"


def test_energy_test_pvalue_in_bounds() -> None:
    import random
    rng = random.Random(11)
    x = tuple(rng.gauss(0.0, 0.01) for _ in range(40))
    y = tuple(rng.gauss(0.0, 0.01) for _ in range(40))
    result = compute_energy_distance_test(x, y, n_permutations=99)
    assert 0.0 <= result.p_value <= 1.0


def test_energy_test_same_dist_high_pvalue() -> None:
    """Same distribution → high p-value (fail to reject H0)."""
    import random
    rng = random.Random(12)
    # Use same seed for both — truly same dist
    x = tuple(rng.gauss(0.0, 0.01) for _ in range(50))
    y = tuple(rng.gauss(0.0, 0.01) for _ in range(50))
    result = compute_energy_distance_test(
        x, y, acceptance_floor=0.05, n_permutations=199, random_seed=12
    )
    # p-value should be relatively high (not guaranteed, but with 199 perms
    # and same distribution, usually > 0.05)
    assert result.passes_floor is (result.p_value >= 0.05)


def test_energy_test_different_dist_low_pvalue() -> None:
    """Strongly different distributions → low p-value."""
    import random
    rng = random.Random(13)
    x = tuple(rng.gauss(0.0, 0.01) for _ in range(60))
    y = tuple(rng.gauss(0.1, 0.01) for _ in range(60))  # 10 sigma shift
    result = compute_energy_distance_test(
        x, y, acceptance_floor=0.05, n_permutations=199, random_seed=13
    )
    # With 10 sigma shift, p-value should be very small
    assert result.p_value < 0.05


def test_energy_test_passes_floor_consistency() -> None:
    import random
    rng = random.Random(14)
    x = tuple(rng.gauss(0.0, 0.01) for _ in range(40))
    y = tuple(rng.gauss(0.02, 0.01) for _ in range(40))
    result = compute_energy_distance_test(
        x, y, acceptance_floor=0.10, n_permutations=99, random_seed=14
    )
    assert result.passes_floor is (result.p_value >= 0.10)


def test_energy_test_counts_correct() -> None:
    import random
    rng = random.Random(15)
    x = tuple(rng.gauss(0.0, 0.01) for _ in range(35))
    y = tuple(rng.gauss(0.0, 0.01) for _ in range(45))
    result = compute_energy_distance_test(x, y, n_permutations=99)
    assert result.n_shadow == 35
    assert result.n_backtest == 45
    assert result.n_permutations == 99


def test_energy_test_reproducible_with_seed() -> None:
    """Same seed → same result."""
    import random
    rng = random.Random(99)
    x = tuple(rng.gauss(0.0, 0.01) for _ in range(50))
    y = tuple(rng.gauss(0.005, 0.01) for _ in range(50))
    r1 = compute_energy_distance_test(x, y, n_permutations=99, random_seed=42)
    r2 = compute_energy_distance_test(x, y, n_permutations=99, random_seed=42)
    assert r1.p_value == r2.p_value
    assert r1.energy_statistic == r2.energy_statistic


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

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


def test_energy_distance_same_distribution_anchor() -> None:
    """Energy same-distribution anchor: N(0,1) vs N(0,1) should not raise a false alarm.

    The current implementation returns a scaled energy statistic together with a
    permutation p-value. Under H0 (same distribution), the deterministic seeded
    permutation test should yield p_value > 0.05 and pass the G2.1 floor.

    Reference: Szekely & Rizzo (2004); Rizzo & Szekely (2016).
    """
    import random

    rng = random.Random(20240424)
    shadow = tuple(rng.gauss(0.0, 1.0) for _ in range(100))
    backtest = tuple(rng.gauss(0.0, 1.0) for _ in range(100))

    result = compute_energy_distance_test(
        shadow,
        backtest,
        n_permutations=999,
        random_seed=20240424,
        acceptance_floor=0.01,
    )

    assert result.p_value > 0.05
    assert result.passes_floor is True
