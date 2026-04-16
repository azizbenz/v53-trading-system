"""Mann-Kendall monotonic trend test for shadow gate drift detection.

Shadow gate thresholds (14_SHADOW_GATE_MATH.md):
  G2.1: reject descending trend if p-value < 0.05
  G2.2: reject descending trend if p-value < 0.10
  G2.3: reject descending trend if p-value < 0.20

Reference: Mann (1945); Kendall (1975).
"""

from __future__ import annotations

import math
from collections import Counter
from statistics import NormalDist
from typing import Iterable

from pydantic import BaseModel, Field


class MannKendallError(ValueError):
    """Raised when Mann-Kendall inputs are mathematically unusable."""


class MannKendallResult(BaseModel, frozen=True):
    """Audit-ready Mann-Kendall computation result."""

    method_version: str = "mann_kendall_v1"
    observation_count: int = Field(..., ge=2)
    s_statistic: int
    kendall_tau: float = Field(..., ge=-1.0, le=1.0)
    variance_s: float = Field(..., ge=0.0)
    z_score: float
    p_value: float = Field(..., ge=0.0, le=1.0)
    trend_direction: str = Field(..., min_length=1)
    has_significant_trend: bool
    descending_trend_detected: bool
    passes_floor: bool
    acceptance_floor: float = Field(..., gt=0.0, lt=1.0)


def compute_mann_kendall_test(
    values: Iterable[float],
    *,
    acceptance_floor: float = 0.05,
) -> MannKendallResult:
    """Compute Mann-Kendall monotonic trend test over an ordered value series."""

    if not (0.0 < acceptance_floor < 1.0):
        raise MannKendallError("acceptance_floor must be in (0, 1)")

    series = _validated_values(values)
    s_statistic = _mann_kendall_s(series)
    observation_count = len(series)
    denominator = observation_count * (observation_count - 1) / 2.0
    kendall_tau = 0.0 if denominator <= 0.0 else s_statistic / denominator
    variance_s = _variance_s_with_ties(series)
    z_score, p_value = _z_score_and_p_value(s_statistic, variance_s)
    trend_direction = _trend_direction(kendall_tau)
    has_significant_trend = trend_direction != "flat" and p_value < acceptance_floor
    descending_trend_detected = (
        trend_direction == "descending" and has_significant_trend
    )

    return MannKendallResult(
        observation_count=observation_count,
        s_statistic=s_statistic,
        kendall_tau=kendall_tau,
        variance_s=variance_s,
        z_score=z_score,
        p_value=p_value,
        trend_direction=trend_direction,
        has_significant_trend=has_significant_trend,
        descending_trend_detected=descending_trend_detected,
        passes_floor=not descending_trend_detected,
        acceptance_floor=acceptance_floor,
    )


def _validated_values(values: Iterable[float]) -> tuple[float, ...]:
    series = tuple(float(value) for value in values)
    if len(series) < 2:
        raise MannKendallError(
            "Mann-Kendall test requires at least two observations"
        )
    if not all(math.isfinite(value) for value in series):
        raise MannKendallError(
            "Mann-Kendall test requires only finite observations"
        )
    return series


def _mann_kendall_s(series: tuple[float, ...]) -> int:
    s_statistic = 0
    for left_index, left_value in enumerate(series[:-1]):
        for right_value in series[left_index + 1 :]:
            if right_value > left_value:
                s_statistic += 1
            elif right_value < left_value:
                s_statistic -= 1
    return s_statistic


def _variance_s_with_ties(series: tuple[float, ...]) -> float:
    observation_count = len(series)
    tie_penalty = sum(
        count * (count - 1) * (2 * count + 5)
        for count in Counter(series).values()
        if count > 1
    )
    variance_s = (
        observation_count
        * (observation_count - 1)
        * (2 * observation_count + 5)
        - tie_penalty
    ) / 18.0
    return max(variance_s, 0.0)


def _z_score_and_p_value(s_statistic: int, variance_s: float) -> tuple[float, float]:
    if variance_s <= 0.0 or s_statistic == 0:
        return 0.0, 1.0

    variance_root = math.sqrt(variance_s)
    if s_statistic > 0:
        z_score = (s_statistic - 1.0) / variance_root
    else:
        z_score = (s_statistic + 1.0) / variance_root
    p_value = 2.0 * (1.0 - NormalDist().cdf(abs(z_score)))
    return z_score, max(0.0, min(1.0, p_value))


def _trend_direction(kendall_tau: float) -> str:
    if kendall_tau > 0.0:
        return "ascending"
    if kendall_tau < 0.0:
        return "descending"
    return "flat"


__all__ = [
    "MannKendallError",
    "MannKendallResult",
    "compute_mann_kendall_test",
]
