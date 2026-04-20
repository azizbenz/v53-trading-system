"""Bounded Hansen SPA test for multi-engine shadow promotion.

H0: the best candidate is not significantly better than the benchmark once the
"best-of-N" selection effect is accounted for.

This implementation stays deliberately narrow:
- inputs are already loss-differential series against a benchmark
- stationary bootstrap is applied jointly across candidates to preserve
  time alignment and cross-candidate dependence
- the null is recentered with the positive-part adjustment `d - max(mean(d), 0)`

Reference: Hansen (2005), Journal of Business & Economic Statistics.
DOI: 10.1198/073500105000000063
"""

from __future__ import annotations

import math
import random
from collections.abc import Mapping
from typing import Iterable

from pydantic import BaseModel, Field

from calibration_methods.bootstrap import infer_stationary_block_length


class HansenSpaError(ValueError):
    """Raised when Hansen SPA inputs are mathematically unusable."""


class HansenSpaResult(BaseModel, frozen=True):
    """Audit-ready bounded Hansen SPA result."""

    method_version: str = "hansen_spa_stationary_bootstrap_v1"
    candidate_count: int = Field(..., ge=1)
    observation_count: int = Field(..., ge=2)
    selected_candidate_id: str = Field(..., min_length=1)
    selected_candidate_mean_differential: float
    selected_candidate_omega_hat: float = Field(..., ge=0.0)
    test_statistic: float = Field(..., ge=0.0)
    p_value: float = Field(..., ge=0.0, le=1.0)
    passes_floor: bool
    acceptance_ceiling: float = Field(..., gt=0.0, lt=1.0)
    bootstrap_samples: int = Field(..., ge=100)
    expected_block_length: int = Field(..., ge=1)
    rng_seed: int


def compute_hansen_spa_test(
    loss_differentials_by_candidate: Mapping[str, Iterable[float]],
    *,
    acceptance_ceiling: float = 0.10,
    bootstrap_samples: int = 1_000,
    expected_block_length: int | None = None,
    rng_seed: int = 53,
) -> HansenSpaResult:
    """Compute a bounded Hansen SPA p-value for the selected best candidate."""

    if not (0.0 < acceptance_ceiling < 1.0):
        raise HansenSpaError("acceptance_ceiling must be in (0, 1)")
    if bootstrap_samples < 100:
        raise HansenSpaError("bootstrap_samples must be >= 100")
    if expected_block_length is not None and expected_block_length <= 0:
        raise HansenSpaError("expected_block_length must be > 0 when provided")

    candidate_series = _validated_candidate_series(loss_differentials_by_candidate)
    candidate_ids = tuple(candidate_series.keys())
    observation_count = len(next(iter(candidate_series.values())))
    block_length = expected_block_length or _infer_joint_block_length(candidate_series)
    rng = random.Random(rng_seed)

    means = {
        candidate_id: _mean(series)
        for candidate_id, series in candidate_series.items()
    }
    omega_hats = _estimate_omega_hats(
        candidate_series,
        expected_block_length=block_length,
        bootstrap_samples=bootstrap_samples,
        rng=rng,
    )
    observed_stats = {
        candidate_id: _studentized_mean(
            mean_value=means[candidate_id],
            omega_hat=omega_hats[candidate_id],
            observation_count=observation_count,
        )
        for candidate_id in candidate_ids
    }
    selected_candidate_id = max(
        candidate_ids,
        key=lambda candidate_id: observed_stats[candidate_id],
    )
    observed_statistic = max(observed_stats[selected_candidate_id], 0.0)

    p_value = _bootstrap_p_value(
        candidate_series,
        means=means,
        omega_hats=omega_hats,
        observed_statistic=observed_statistic,
        bootstrap_samples=bootstrap_samples,
        expected_block_length=block_length,
        rng=rng,
    )

    return HansenSpaResult(
        candidate_count=len(candidate_ids),
        observation_count=observation_count,
        selected_candidate_id=selected_candidate_id,
        selected_candidate_mean_differential=means[selected_candidate_id],
        selected_candidate_omega_hat=omega_hats[selected_candidate_id],
        test_statistic=observed_statistic,
        p_value=p_value,
        passes_floor=p_value <= acceptance_ceiling,
        acceptance_ceiling=acceptance_ceiling,
        bootstrap_samples=bootstrap_samples,
        expected_block_length=block_length,
        rng_seed=rng_seed,
    )


def _validated_candidate_series(
    loss_differentials_by_candidate: Mapping[str, Iterable[float]],
) -> dict[str, tuple[float, ...]]:
    if not loss_differentials_by_candidate:
        raise HansenSpaError("Hansen SPA requires at least one candidate series")

    candidate_series: dict[str, tuple[float, ...]] = {}
    expected_length: int | None = None
    for candidate_id, values in loss_differentials_by_candidate.items():
        if not candidate_id.strip():
            raise HansenSpaError("candidate ids must be non-empty")
        series = tuple(float(value) for value in values)
        if len(series) < 2:
            raise HansenSpaError(
                f"Hansen SPA requires at least two observations in {candidate_id}"
            )
        if not all(math.isfinite(value) for value in series):
            raise HansenSpaError(
                f"Hansen SPA requires only finite observations in {candidate_id}"
            )
        if expected_length is None:
            expected_length = len(series)
        elif len(series) != expected_length:
            raise HansenSpaError("all candidate series must share the same length")
        candidate_series[candidate_id] = series
    return candidate_series


def _infer_joint_block_length(candidate_series: Mapping[str, tuple[float, ...]]) -> int:
    return max(
        1,
        max(
            infer_stationary_block_length(series)
            for series in candidate_series.values()
        ),
    )


def _estimate_omega_hats(
    candidate_series: Mapping[str, tuple[float, ...]],
    *,
    expected_block_length: int,
    bootstrap_samples: int,
    rng: random.Random,
) -> dict[str, float]:
    observation_count = len(next(iter(candidate_series.values())))
    centered_series = {
        candidate_id: _center_series(series)
        for candidate_id, series in candidate_series.items()
    }
    replicates_by_candidate: dict[str, list[float]] = {
        candidate_id: []
        for candidate_id in candidate_series
    }
    for _ in range(bootstrap_samples):
        indices = _draw_stationary_bootstrap_indices(
            sample_count=observation_count,
            expected_block_length=expected_block_length,
            rng=rng,
        )
        for candidate_id, series in centered_series.items():
            sample_mean = _mean(series[index] for index in indices)
            replicates_by_candidate[candidate_id].append(
                math.sqrt(observation_count) * sample_mean
            )

    return {
        candidate_id: max(_population_std(tuple(replicates)), 1e-12)
        for candidate_id, replicates in replicates_by_candidate.items()
    }


def _bootstrap_p_value(
    candidate_series: Mapping[str, tuple[float, ...]],
    *,
    means: Mapping[str, float],
    omega_hats: Mapping[str, float],
    observed_statistic: float,
    bootstrap_samples: int,
    expected_block_length: int,
    rng: random.Random,
) -> float:
    if observed_statistic <= 0.0:
        return 1.0

    observation_count = len(next(iter(candidate_series.values())))
    null_centered_series = {
        candidate_id: tuple(
            value - max(means[candidate_id], 0.0)
            for value in series
        )
        for candidate_id, series in candidate_series.items()
    }
    exceedances = 0
    for _ in range(bootstrap_samples):
        indices = _draw_stationary_bootstrap_indices(
            sample_count=observation_count,
            expected_block_length=expected_block_length,
            rng=rng,
        )
        bootstrap_statistic = max(
            _studentized_mean(
                mean_value=_mean(series[index] for index in indices),
                omega_hat=omega_hats[candidate_id],
                observation_count=observation_count,
            )
            for candidate_id, series in null_centered_series.items()
        )
        if bootstrap_statistic >= observed_statistic - 1e-12:
            exceedances += 1
    return exceedances / float(bootstrap_samples)


def _studentized_mean(
    *,
    mean_value: float,
    omega_hat: float,
    observation_count: int,
) -> float:
    if omega_hat <= 0.0:
        return 0.0 if mean_value <= 0.0 else math.inf
    return max(0.0, math.sqrt(observation_count) * mean_value / omega_hat)


def _draw_stationary_bootstrap_indices(
    *,
    sample_count: int,
    expected_block_length: int,
    rng: random.Random,
) -> tuple[int, ...]:
    restart_probability = 1.0 / float(expected_block_length)
    indices: list[int] = []
    current_index = rng.randrange(sample_count)
    for position in range(sample_count):
        if position == 0 or rng.random() < restart_probability:
            current_index = rng.randrange(sample_count)
        else:
            current_index = (current_index + 1) % sample_count
        indices.append(current_index)
    return tuple(indices)


def _mean(values: Iterable[float]) -> float:
    materialized = tuple(float(value) for value in values)
    if not materialized:
        raise HansenSpaError("mean requires at least one value")
    return sum(materialized) / len(materialized)


def _center_series(series: tuple[float, ...]) -> tuple[float, ...]:
    mean_value = _mean(series)
    return tuple(value - mean_value for value in series)


def _population_std(values: tuple[float, ...]) -> float:
    if not values:
        return 0.0
    mean_value = _mean(values)
    variance = sum((value - mean_value) ** 2 for value in values) / len(values)
    return math.sqrt(max(variance, 0.0))


__all__ = [
    "HansenSpaError",
    "HansenSpaResult",
    "compute_hansen_spa_test",
]
