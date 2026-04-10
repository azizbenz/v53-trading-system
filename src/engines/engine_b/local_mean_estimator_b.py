"""
Build-7 / engine_b / local_mean_estimator_B
Estimate the local mean and dispersion for mean-reversion detection.

mu_loc  = local mean over recent window
sigma_loc = local dispersion over the same window
z_t = (p_t - mu_loc) / sigma_loc
"""

from __future__ import annotations

from data_backbone import TO_CALIBRATE
from pydantic import BaseModel


ENGINE_B_LOCAL_MEAN_PROFILE_ID = "engine_b_local_mean.to_calibrate.v1"
ENGINE_B_LOCAL_MEAN_CALIBRATION_STATUS = TO_CALIBRATE
ENGINE_B_LOCAL_MEAN_DEFAULTS: dict[str, float] = {
    "min_std": 1e-12,
}


class LocalMeanInput(BaseModel, frozen=True):
    """Inputs for local mean estimation."""

    pair: str
    current_price: float
    local_mean: float
    local_std: float


class LocalMeanResult(BaseModel, frozen=True):
    """Result of local mean estimation with z-score."""

    pair: str
    current_price: float
    local_mean: float
    local_std: float
    deviation: float
    z_score: float
    valid: bool
    calibration_profile_id: str = ENGINE_B_LOCAL_MEAN_PROFILE_ID
    calibration_status: str = ENGINE_B_LOCAL_MEAN_CALIBRATION_STATUS

    @property
    def abs_z(self) -> float:
        return abs(self.z_score)


def estimate_local_mean(inputs: LocalMeanInput) -> LocalMeanResult:
    """Compute local deviation and z-score."""

    deviation = inputs.current_price - inputs.local_mean
    min_std = ENGINE_B_LOCAL_MEAN_DEFAULTS["min_std"]

    if inputs.local_std <= min_std:
        return LocalMeanResult(
            pair=inputs.pair,
            current_price=inputs.current_price,
            local_mean=inputs.local_mean,
            local_std=inputs.local_std,
            deviation=deviation,
            z_score=0.0,
            valid=False,
            calibration_profile_id=ENGINE_B_LOCAL_MEAN_PROFILE_ID,
            calibration_status=ENGINE_B_LOCAL_MEAN_CALIBRATION_STATUS,
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
        calibration_profile_id=ENGINE_B_LOCAL_MEAN_PROFILE_ID,
        calibration_status=ENGINE_B_LOCAL_MEAN_CALIBRATION_STATUS,
    )
