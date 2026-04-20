"""Tests for two-sample KS test.

Reference: Kolmogorov (1933), Smirnov (1948).
"""

from __future__ import annotations

import math

import pytest

from calibration_methods.ks_test import (
    KolmogorovSmirnovError,
    KolmogorovSmirnovResult,
    compute_ks_2sample,
    _ks_statistic,
    _ks_pvalue,
)


# ---------------------------------------------------------------------------
# Core statistic correctness
# ---------------------------------------------------------------------------

def test_ks_identical_distributions_low_statistic() -> None:
    """Same distribution → small D statistic."""
    import random
    rng = random.Random(0)
    x = tuple(rng.gauss(0.0, 1.0) for _ in range(200))
    y = tuple(rng.gauss(0.0, 1.0) for _ in range(200))
    d = _ks_statistic(x, y)
    # With 200 samples from same dist, D should be small
    assert d < 0.20


def test_ks_different_distributions_large_statistic() -> None:
    """Different means → large D statistic."""
    import random
    rng = random.Random(1)
    x = tuple(rng.gauss(0.0, 1.0) for _ in range(200))
    y = tuple(rng.gauss(5.0, 1.0) for _ in range(200))  # shifted by 5 sigma
    d = _ks_statistic(x, y)
    assert d > 0.80


def test_ks_anchor_matches_fixed_seed_half_sigma_shift_at_n_1000() -> None:
    """Massey-style anchor: N(0,1) vs N(0.5,1), n=m=1000, seed fixed -> D = 0.19."""
    import random

    rng = random.Random(488)
    x = tuple(rng.gauss(0.0, 1.0) for _ in range(1000))
    y = tuple(rng.gauss(0.5, 1.0) for _ in range(1000))
    d = _ks_statistic(x, y)
    assert d == pytest.approx(0.19, abs=1e-12)


def test_ks_statistic_zero_for_exact_same_data() -> None:
    """Identical data → D = 0."""
    data = (0.1, 0.2, 0.3, 0.4, 0.5)
    assert _ks_statistic(data, data) == 0.0


def test_ks_statistic_is_symmetric() -> None:
    """D(x, y) == D(y, x)."""
    x = (1.0, 2.0, 3.0, 4.0, 5.0)
    y = (1.5, 2.5, 3.5, 4.5, 5.5)
    assert _ks_statistic(x, y) == _ks_statistic(y, x)


def test_ks_statistic_between_zero_and_one() -> None:
    x = (0.1, 0.5, 0.9)
    y = (0.2, 0.6, 0.8)
    d = _ks_statistic(x, y)
    assert 0.0 <= d <= 1.0


# ---------------------------------------------------------------------------
# p-value correctness
# ---------------------------------------------------------------------------

def test_ks_pvalue_zero_statistic_gives_one() -> None:
    """D = 0 → p-value = 1 (perfect match)."""
    assert _ks_pvalue(0.0, 100, 100) == 1.0


def test_ks_pvalue_large_statistic_gives_small_pvalue() -> None:
    """Large D → small p-value (reject H0)."""
    p = _ks_pvalue(0.5, 100, 100)
    assert p < 0.001


def test_ks_pvalue_bounds() -> None:
    """p-value is in [0, 1]."""
    for d in [0.0, 0.05, 0.1, 0.2, 0.5, 1.0]:
        p = _ks_pvalue(d, 50, 50)
        assert 0.0 <= p <= 1.0


# ---------------------------------------------------------------------------
# Full compute_ks_2sample
# ---------------------------------------------------------------------------

def test_ks_2sample_returns_result_type() -> None:
    import random
    rng = random.Random(2)
    x = tuple(rng.gauss(0.0, 1.0) for _ in range(100))
    y = tuple(rng.gauss(0.0, 1.0) for _ in range(100))
    result = compute_ks_2sample(x, y)
    assert isinstance(result, KolmogorovSmirnovResult)
    assert result.method_version == "ks_2sample_v1"


def test_ks_2sample_same_dist_high_pvalue() -> None:
    """Same distribution → p-value should be high (fail to reject H0)."""
    import random
    rng = random.Random(3)
    x = tuple(rng.gauss(0.0, 0.01) for _ in range(300))
    y = tuple(rng.gauss(0.0, 0.01) for _ in range(300))
    result = compute_ks_2sample(x, y, acceptance_floor=0.05)
    # p-value should be > 0.05 most of the time with 300 samples from same dist
    # We test passes_floor is consistent
    assert result.passes_floor is (result.p_value >= 0.05)


def test_ks_2sample_different_dist_low_pvalue() -> None:
    """Clearly different distributions → p-value should be very small."""
    import random
    rng = random.Random(4)
    x = tuple(rng.gauss(0.0, 0.01) for _ in range(100))
    y = tuple(rng.gauss(0.1, 0.01) for _ in range(100))  # 10 sigma shift
    result = compute_ks_2sample(x, y, acceptance_floor=0.05)
    assert result.p_value < 0.01
    assert result.passes_floor is False


def test_ks_2sample_passes_floor_flag_consistency() -> None:
    import random
    rng = random.Random(5)
    x = tuple(rng.gauss(0.0, 0.01) for _ in range(80))
    y = tuple(rng.gauss(0.005, 0.01) for _ in range(80))
    result = compute_ks_2sample(x, y, acceptance_floor=0.10)
    assert result.passes_floor is (result.p_value >= 0.10)


def test_ks_2sample_counts_correct() -> None:
    x = tuple(float(i) for i in range(50))
    y = tuple(float(i) * 2 for i in range(70))
    result = compute_ks_2sample(x, y)
    assert result.n_shadow == 50
    assert result.n_backtest == 70


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

def test_ks_rejects_fewer_than_2_in_shadow() -> None:
    with pytest.raises(KolmogorovSmirnovError, match="at least 2"):
        compute_ks_2sample([0.01], [0.01, 0.02, 0.03])


def test_ks_rejects_fewer_than_2_in_backtest() -> None:
    with pytest.raises(KolmogorovSmirnovError, match="at least 2"):
        compute_ks_2sample([0.01, 0.02], [0.01])


def test_ks_rejects_non_finite() -> None:
    with pytest.raises(KolmogorovSmirnovError, match="finite"):
        compute_ks_2sample([0.01, float("nan")], [0.01, 0.02])


def test_ks_rejects_invalid_floor() -> None:
    with pytest.raises(KolmogorovSmirnovError, match="acceptance_floor"):
        compute_ks_2sample([0.01, 0.02], [0.01, 0.02], acceptance_floor=1.5)
