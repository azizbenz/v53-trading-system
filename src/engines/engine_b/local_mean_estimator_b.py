"""
Build-7 / engine_b / local_mean_estimator_B
Estimate the local mean and dispersion for mean-reversion detection.

μ_t^loc  — local mean (e.g. EMA/SMA over recent window)
σ_t^loc  — local dispersion (std dev over same window)
z_t      = (p_t - μ_t^loc) / σ_t^loc
"""

from __future__ import annotations

from pydantic import BaseModel


class LocalMeanInput(BaseModel, frozen=True):
    """Inputs for local mean estimation."""

    pair: str
    current_price: float
    local_mean: float  # μ_t^loc — pre-computed by data layer
    local_std: float  # σ_t^loc — pre-computed by data layer


class LocalMeanResult(BaseModel, frozen=True):
    """Result of local mean estimation with z-score."""

    pair: str
    current_price: float
    local_mean: float
    local_std: float
    deviation: float  # p_t - μ_t^loc
    z_score: float  # (p_t - μ) / σ
    valid: bool  # False if σ ≤ 0

    @property
    def abs_z(self) -> float:
        return abs(self.z_score)


_MIN_STD = 1e-12


def estimate_local_mean(inputs: LocalMeanInput) -> LocalMeanResult:
    """Compute local deviation and z-score.

    z_t = (p_t - μ_t^loc) / σ_t^loc

    Returns valid=False if local_std <= 0 (no meaningful dispersion).
    """
    deviation = inputs.current_price - inputs.local_mean

    if inputs.local_std <= _MIN_STD:
        return LocalMeanResult(
            pair=inputs.pair,
            current_price=inputs.current_price,
            local_mean=inputs.local_mean,
            local_std=inputs.local_std,
            deviation=deviation,
            z_score=0.0,
            valid=False,
        )

    z = deviation / inputs.local_std

    return LocalMeanResult(
        pair=inputs.pair,
        current_price=inputs.current_price,
        local_mean=inputs.local_mean,
        local_std=inputs.local_std,
        deviation=deviation,
        z_score=z,
        valid=True,
    )
