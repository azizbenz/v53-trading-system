"""Tests for bounded Hansen SPA multi-engine selection correction."""

from __future__ import annotations

import random

import pytest

from calibration_methods.hansen_spa import (
    HansenSpaError,
    HansenSpaResult,
    compute_hansen_spa_test,
)


def test_hansen_spa_returns_result_type() -> None:
    result = compute_hansen_spa_test(
        {
            "engine_a": (0.01, 0.02, 0.01, 0.00),
            "engine_b": (0.00, 0.01, 0.00, -0.01),
        },
        bootstrap_samples=199,
        rng_seed=12,
    )
    assert isinstance(result, HansenSpaResult)
    assert result.method_version == "hansen_spa_stationary_bootstrap_v1"


def test_hansen_spa_rejects_empty_candidate_map() -> None:
    with pytest.raises(HansenSpaError, match="at least one candidate"):
        compute_hansen_spa_test({}, bootstrap_samples=199)


def test_hansen_spa_rejects_unequal_series_lengths() -> None:
    with pytest.raises(HansenSpaError, match="same length"):
        compute_hansen_spa_test(
            {
                "engine_a": (0.01, 0.02, 0.03),
                "engine_b": (0.01, 0.02),
            },
            bootstrap_samples=199,
        )


def test_hansen_spa_rejects_non_finite_values() -> None:
    with pytest.raises(HansenSpaError, match="finite observations"):
        compute_hansen_spa_test(
            {
                "engine_a": (0.01, 0.02, float("inf")),
                "engine_b": (0.01, 0.02, 0.03),
            },
            bootstrap_samples=199,
        )


def test_hansen_spa_rejects_best_of_many_random_strategies() -> None:
    rng = random.Random(53)
    random_candidates = {
        f"engine_{index:03d}": tuple(rng.gauss(0.0, 1.0) for _ in range(80))
        for index in range(100)
    }
    result = compute_hansen_spa_test(
        random_candidates,
        acceptance_ceiling=0.10,
        bootstrap_samples=199,
        expected_block_length=5,
        rng_seed=53,
    )
    assert result.candidate_count == 100
    assert result.passes_floor is False
    assert result.p_value > 0.10


def test_hansen_spa_accepts_persistent_superior_candidate() -> None:
    rng = random.Random(77)
    candidates = {
        "engine_a": tuple(rng.gauss(0.08, 0.20) for _ in range(120)),
        "engine_b": tuple(rng.gauss(0.00, 0.20) for _ in range(120)),
        "engine_c": tuple(rng.gauss(-0.01, 0.20) for _ in range(120)),
        "engine_d": tuple(rng.gauss(0.01, 0.20) for _ in range(120)),
    }
    result = compute_hansen_spa_test(
        candidates,
        acceptance_ceiling=0.10,
        bootstrap_samples=199,
        expected_block_length=6,
        rng_seed=77,
    )
    assert result.selected_candidate_id == "engine_a"
    assert result.passes_floor is True
    assert result.p_value <= 0.10
