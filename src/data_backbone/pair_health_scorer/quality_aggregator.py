"""
10.5.1 — Quality Aggregator: aggregate freshness + consistency + latency + recovery.

Produces health score H_j per pair.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class QualityInputs(BaseModel, frozen=True):
    """Inputs for quality aggregation."""

    pair: str
    freshness_score: float = 1.0  # 1.0 = fresh, 0.0 = stale
    consistency_score: float = 1.0  # from consistency_checker
    latency_score: float = 1.0  # 1.0 = low latency, 0.0 = high
    recovery_score: float = 1.0  # 1.0 = stable, 0.0 = in recovery


class HealthScore(BaseModel, frozen=True):
    """Aggregated health score for a pair."""

    pair: str
    score: float  # H_j ∈ [0, 1]
    freshness_score: float
    consistency_score: float
    latency_score: float
    recovery_score: float


def compute_health_score(
    inputs: QualityInputs,
    w_freshness: float = 0.3,
    w_consistency: float = 0.3,
    w_latency: float = 0.2,
    w_recovery: float = 0.2,
) -> HealthScore:
    """Compute weighted health score H_j for a pair.

    H_j = w1*freshness + w2*consistency + w3*latency + w4*recovery
    """
    score = (
        w_freshness * inputs.freshness_score
        + w_consistency * inputs.consistency_score
        + w_latency * inputs.latency_score
        + w_recovery * inputs.recovery_score
    )
    score = max(0.0, min(1.0, score))

    return HealthScore(
        pair=inputs.pair,
        score=score,
        freshness_score=inputs.freshness_score,
        consistency_score=inputs.consistency_score,
        latency_score=inputs.latency_score,
        recovery_score=inputs.recovery_score,
    )
