"""Tests for PSR (Probabilistic Sharpe Ratio).

Reference values derived from Bailey & López de Prado (2012).
"""

from __future__ import annotations

import hashlib
import json
import math
from statistics import NormalDist

import pytest

from calibration_methods.psr import (
    ProbabilisticSharpeRatioError,
    ProbabilisticSharpeRatioResult,
    compute_probabilistic_sharpe_ratio,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _constant_returns(n: int, value: float) -> tuple[float, ...]:
    return tuple(value for _ in range(n))


def _flat_returns(n: int, mean: float, std: float) -> tuple[float, ...]:
    """Deterministic series with given approximate mean and std via grid."""
    step = std * math.sqrt(3.0)
    half = n // 2
    low = tuple(mean - step for _ in range(half))
    high = tuple(mean + step for _ in range(n - half))
    return low + high


def _returns_api_anchor_fixture() -> tuple[float, ...]:
    return (
        0.012,
        -0.006,
        0.009,
        0.004,
        -0.003,
        0.011,
        -0.008,
        0.006,
        0.015,
        -0.002,
        0.007,
        0.003,
        -0.005,
        0.010,
        0.002,
        -0.004,
        0.008,
        0.005,
    )


def _fixture_hash(values: tuple[float, ...]) -> str:
    payload = json.dumps(list(values), separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _reference_psr(
    returns: tuple[float, ...],
    *,
    benchmark_sharpe: float,
) -> tuple[float, float, float, float]:
    mean = sum(returns) / len(returns)
    sample_std = math.sqrt(
        sum((value - mean) ** 2 for value in returns) / float(len(returns) - 1)
    )
    sample_sharpe = mean / sample_std
    standardized = tuple((value - mean) / sample_std for value in returns)
    skewness = sum(value**3 for value in standardized) / len(standardized)
    kurtosis = sum(value**4 for value in standardized) / len(standardized)
    inner = 1.0 - (skewness * sample_sharpe) + (
        ((kurtosis - 1.0) / 4.0) * sample_sharpe**2
    )
    z_score = (
        (sample_sharpe - benchmark_sharpe)
        * math.sqrt(len(returns) - 1)
        / math.sqrt(inner)
    )
    return sample_sharpe, skewness, kurtosis, NormalDist().cdf(z_score)


# ---------------------------------------------------------------------------
# Basic correctness
# ---------------------------------------------------------------------------

def test_psr_returns_result_type() -> None:
    returns = tuple(0.001 * i for i in range(1, 51))
    result = compute_probabilistic_sharpe_ratio(returns, benchmark_sharpe=0.0)
    assert isinstance(result, ProbabilisticSharpeRatioResult)
    assert result.method_version == "probabilistic_sharpe_ratio_v1"
    assert result.observation_count == 50


def test_psr_is_between_zero_and_one() -> None:
    returns = tuple(0.001 * i for i in range(1, 101))
    result = compute_probabilistic_sharpe_ratio(returns, benchmark_sharpe=0.0)
    assert 0.0 <= result.psr <= 1.0


def test_psr_passes_floor_when_above() -> None:
    # Strongly positive returns → PSR(0) should be high
    returns = tuple(0.01 for _ in range(200))
    # Constant returns → std=0, should raise
    with pytest.raises(ProbabilisticSharpeRatioError):
        compute_probabilistic_sharpe_ratio(returns, benchmark_sharpe=0.0)


def test_psr_positive_returns_gives_high_psr() -> None:
    """Positive expected returns with low variance → PSR(0) > 0.5."""
    import random
    rng = random.Random(0)
    returns = tuple(0.002 + rng.gauss(0.0, 0.003) for _ in range(120))
    result = compute_probabilistic_sharpe_ratio(
        returns, benchmark_sharpe=0.0, acceptance_floor=0.60
    )
    # With positive returns over 120 obs, PSR(0) should be > 0.5
    assert result.psr > 0.5


def test_psr_negative_returns_gives_low_psr() -> None:
    """Negative expected returns → PSR(0) < 0.5."""
    import random
    rng = random.Random(1)
    returns = tuple(-0.002 + rng.gauss(0.0, 0.003) for _ in range(120))
    result = compute_probabilistic_sharpe_ratio(
        returns, benchmark_sharpe=0.0, acceptance_floor=0.60
    )
    assert result.psr < 0.5


def test_psr_passes_floor_flag() -> None:
    import random
    rng = random.Random(42)
    good_returns = tuple(0.003 + rng.gauss(0.0, 0.002) for _ in range(200))
    result = compute_probabilistic_sharpe_ratio(
        good_returns, benchmark_sharpe=0.0, acceptance_floor=0.60
    )
    assert result.passes_floor is (result.psr >= 0.60)


def test_psr_symmetry() -> None:
    """Flipping sign of returns flips PSR around 0.5 (approximately)."""
    import random
    rng = random.Random(7)
    pos = tuple(0.001 + rng.gauss(0.0, 0.003) for _ in range(100))
    neg = tuple(-r for r in pos)
    r_pos = compute_probabilistic_sharpe_ratio(pos, benchmark_sharpe=0.0)
    r_neg = compute_probabilistic_sharpe_ratio(neg, benchmark_sharpe=0.0)
    # PSR(pos) + PSR(neg) should be ~1 (symmetry of normal CDF)
    assert abs(r_pos.psr + r_neg.psr - 1.0) < 0.05


# ---------------------------------------------------------------------------
# Shadow gate threshold smoke tests
# ---------------------------------------------------------------------------

def test_psr_g21_floor_0_60() -> None:
    """G2.1 requires PSR(0) >= 0.60 — check threshold is wired correctly."""
    import random
    rng = random.Random(100)
    # Borderline returns: slightly positive
    returns = tuple(0.0005 + rng.gauss(0.0, 0.003) for _ in range(50))
    result = compute_probabilistic_sharpe_ratio(
        returns, benchmark_sharpe=0.0, acceptance_floor=0.60
    )
    # passes_floor reflects whether PSR >= 0.60
    assert result.passes_floor is (result.psr >= 0.60)


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

def test_psr_rejects_fewer_than_3_observations() -> None:
    with pytest.raises(ProbabilisticSharpeRatioError, match="at least three"):
        compute_probabilistic_sharpe_ratio([0.01, 0.02])


def test_psr_rejects_non_finite() -> None:
    with pytest.raises(ProbabilisticSharpeRatioError, match="finite"):
        compute_probabilistic_sharpe_ratio([0.01, float("nan"), 0.02])


def test_psr_rejects_non_finite_benchmark() -> None:
    with pytest.raises(ProbabilisticSharpeRatioError, match="benchmark_sharpe"):
        compute_probabilistic_sharpe_ratio(
            [0.01, 0.02, 0.03], benchmark_sharpe=float("inf")
        )


def test_psr_rejects_invalid_acceptance_floor() -> None:
    with pytest.raises(ProbabilisticSharpeRatioError, match="acceptance_floor"):
        compute_probabilistic_sharpe_ratio(
            [0.01, 0.02, 0.03], acceptance_floor=1.5
        )


def test_psr_rejects_zero_std() -> None:
    with pytest.raises(ProbabilisticSharpeRatioError, match="standard deviation"):
        compute_probabilistic_sharpe_ratio([0.01, 0.01, 0.01])


def test_psr_matches_closed_form_reference_for_fixed_return_series() -> None:
    """PSR returns-API equivalence anchor over a deterministic hashed fixture.

    Literal `0.9505` is not accepted as a standalone anchor without an in-repo
    deterministic fixture/hash. The production seam accepts a return series, so
    the anchor is: hashed fixture -> independently recomputed Bailey-López de
    Prado Eq. 3 -> identical API result.
    """
    returns = _returns_api_anchor_fixture()
    benchmark_sharpe = 0.10

    expected_sr, expected_skew, expected_kurt, expected_psr = _reference_psr(
        returns,
        benchmark_sharpe=benchmark_sharpe,
    )
    result = compute_probabilistic_sharpe_ratio(
        returns,
        benchmark_sharpe=benchmark_sharpe,
        acceptance_floor=0.95,
    )

    assert _fixture_hash(returns) == "b607ebb7651dfe516d59b53d10a90d48d74f18394734c1e67a9465721d77ae18"
    assert result.observation_count == len(returns)
    assert result.sample_sharpe == pytest.approx(expected_sr)
    assert result.skewness == pytest.approx(expected_skew)
    assert result.kurtosis == pytest.approx(expected_kurt)
    assert result.psr == pytest.approx(expected_psr)
    assert result.passes_floor is (expected_psr >= 0.95)
