"""
8.5.3 — Stale Penalty Builder: produce gradual staleness penalty.

pen_stale(Δ_i) = λ * max(0, Δ_i - Δ_max)

Invariant: penalty is gradual, not binary. Hard cut is separate (stale_hard_guard).
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class StalePenalty(BaseModel, frozen=True):
    """Staleness penalty for a pair+stream."""

    pair: str
    stream_type: str
    age_s: float
    threshold_s: float
    penalty: float  # 0.0 = fresh, >0 = stale
    lambda_factor: float


def compute_stale_penalty(
    pair: str,
    stream_type: str,
    age_s: float,
    threshold_s: float = 5.0,
    lambda_factor: float = 0.1,
) -> StalePenalty:
    """Compute gradual stale penalty.

    pen_stale(Δ_i) = λ * max(0, Δ_i - Δ_max)

    - age_s < threshold_s → penalty = 0 (fresh)
    - age_s > threshold_s → penalty grows linearly
    """
    penalty = lambda_factor * max(0.0, age_s - threshold_s)

    return StalePenalty(
        pair=pair,
        stream_type=stream_type,
        age_s=age_s,
        threshold_s=threshold_s,
        penalty=penalty,
        lambda_factor=lambda_factor,
    )
