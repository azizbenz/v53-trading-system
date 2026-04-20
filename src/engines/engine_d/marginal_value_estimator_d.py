"""Local marginal-value setup-quality threshold seam for Engine D.

Current repo truth: Engine D still gates on ``marginal_value_score`` in the
runner. It does *not* expose a separately modeled ``marginal_EV`` object.

For this slice, Engine D stays on Model A:
- Gate 1 = history / reformation / marginal-value setup quality
- Gate 2 = separate economics via ``cost_feasibility_d.py``

So this threshold is explicitly local setup-quality governance, not an
economics threshold and not a shared EV-net floor.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


ENGINE_D_MARGINAL_VALUE_SCORE_MIN_THRESHOLD_ID = "THR-D_MARGINAL_VALUE_SCORE_MIN"
ENGINE_D_MARGINAL_VALUE_PROFILE_ID = "engine_d_marginal_value.model_a_local.v1"


class EngineDMarginalValueCallerThresholds(BaseModel):
    """Caller-owned Engine D setup-quality gate on marginal_value_score."""

    marginal_value_score_min: float = Field(default=0.56, ge=0.0, le=1.0)
    marginal_value_score_min_threshold_id: str = (
        ENGINE_D_MARGINAL_VALUE_SCORE_MIN_THRESHOLD_ID
    )
    calibration_profile_id: str = ENGINE_D_MARGINAL_VALUE_PROFILE_ID
    calibration_status: str = "LOCAL_MODEL_A_GOVERNANCE"

    model_config = ConfigDict(frozen=True, extra="forbid")


ENGINE_D_MARGINAL_VALUE_CALLER_THRESHOLDS_MODEL_A = (
    EngineDMarginalValueCallerThresholds()
)
ENGINE_D_MARGINAL_VALUE_CALLER_THRESHOLDS = (
    ENGINE_D_MARGINAL_VALUE_CALLER_THRESHOLDS_MODEL_A
)


def marginal_value_floor_cleared(
    marginal_value_score: float,
    *,
    thresholds: EngineDMarginalValueCallerThresholds = (
        ENGINE_D_MARGINAL_VALUE_CALLER_THRESHOLDS_MODEL_A
    ),
) -> bool:
    """Return whether the current Engine D score-floor seam is cleared."""

    return marginal_value_score >= thresholds.marginal_value_score_min


__all__ = [
    "ENGINE_D_MARGINAL_VALUE_CALLER_THRESHOLDS",
    "ENGINE_D_MARGINAL_VALUE_CALLER_THRESHOLDS_MODEL_A",
    "ENGINE_D_MARGINAL_VALUE_PROFILE_ID",
    "ENGINE_D_MARGINAL_VALUE_SCORE_MIN_THRESHOLD_ID",
    "EngineDMarginalValueCallerThresholds",
    "marginal_value_floor_cleared",
]
