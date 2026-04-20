"""
Build-6 / engine_a / cost_feasibility_A
Verify that execution cost does not kill the edge.

Condition: E[g_i | A,j,s] > E[c_i | A,j,s] + delta_safe
           EV_net = x * (E[g] - E[c]) > eps
           CE_A > CE_min
"""

from __future__ import annotations

from enum import StrEnum

from data_backbone import TO_CALIBRATE
from pydantic import BaseModel, Field


class CostVerdict(StrEnum):
    FEASIBLE = "feasible"
    MARGINAL = "marginal"
    INFEASIBLE = "infeasible"


ENGINE_A_COST_PROFILE_ID = "engine_a_cost.to_calibrate.v1"
ENGINE_A_COST_CALIBRATION_STATUS = TO_CALIBRATE
ENGINE_A_DELTA_SAFE_THRESHOLD_ID = "THR-A01"
ENGINE_A_CE_MIN_THRESHOLD_ID = "THR-A02"
ENGINE_A_COST_DEFAULTS: dict[str, float] = {
    "holding_period": 4.0,
    "delta_safe": 0.0005,
    "ce_min": 0.0001,
}


class EngineACostThresholds(BaseModel, frozen=True):
    """Single-source threshold ownership for Engine A cost governance."""

    holding_period: float = Field(default=ENGINE_A_COST_DEFAULTS["holding_period"], gt=0.0)
    delta_safe: float = Field(default=ENGINE_A_COST_DEFAULTS["delta_safe"], ge=0.0)
    ce_min: float = Field(default=ENGINE_A_COST_DEFAULTS["ce_min"], ge=0.0)
    delta_safe_threshold_id: str = ENGINE_A_DELTA_SAFE_THRESHOLD_ID
    ce_min_threshold_id: str = ENGINE_A_CE_MIN_THRESHOLD_ID
    calibration_profile_id: str = ENGINE_A_COST_PROFILE_ID
    calibration_status: str = ENGINE_A_COST_CALIBRATION_STATUS


ENGINE_A_COST_THRESHOLDS_TO_CALIBRATE = EngineACostThresholds()


class CostInput(BaseModel, frozen=True):
    """Cost-related inputs for Engine A."""

    pair: str
    expected_gain: float = Field(..., ge=0.0)
    expected_cost: float = Field(..., ge=0.0)
    kyle_lambda_cost_uplift: float = Field(default=0.0, ge=0.0)
    candidate_size: float = Field(..., ge=0.0)
    holding_period: float = Field(default=ENGINE_A_COST_THRESHOLDS_TO_CALIBRATE.holding_period, gt=0.0)
    delta_safe: float = Field(default=ENGINE_A_COST_THRESHOLDS_TO_CALIBRATE.delta_safe, ge=0.0)
    ce_min: float = Field(default=ENGINE_A_COST_THRESHOLDS_TO_CALIBRATE.ce_min, ge=0.0)


class CostResult(BaseModel, frozen=True):
    """Result of cost feasibility check."""

    pair: str
    verdict: CostVerdict
    is_emittable: bool = False
    base_expected_cost: float
    kyle_lambda_cost_uplift: float = 0.0
    expected_cost: float
    break_even: float
    ev_net: float
    ce_expected: float
    reason: str = ""
    reason_codes: tuple[str, ...] = ()
    calibration_profile_id: str = ENGINE_A_COST_PROFILE_ID
    calibration_status: str = ENGINE_A_COST_CALIBRATION_STATUS


def check_cost_feasibility(inputs: CostInput) -> CostResult:
    """Check if the expected edge covers cost with safety margin."""

    effective_expected_cost = inputs.expected_cost + inputs.kyle_lambda_cost_uplift
    break_even = effective_expected_cost + inputs.delta_safe
    edge = inputs.expected_gain - effective_expected_cost
    ev_net = inputs.candidate_size * edge
    ce = edge / inputs.holding_period if inputs.candidate_size > 0 else 0.0
    reason_codes: tuple[str, ...]

    if inputs.candidate_size <= 0.0:
        verdict = CostVerdict.INFEASIBLE
        is_emittable = False
        reason = "candidate_size must be > 0 for feasible cost evaluation"
        reason_codes = ("engine_a.cost.invalid_candidate_size",)
    elif inputs.delta_safe == 0.0 and ev_net <= 0.0:
        verdict = CostVerdict.INFEASIBLE
        is_emittable = False
        reason = f"EV_net {ev_net:.6f} <= 0"
        reason_codes = ("engine_a.cost.non_positive_ev_net",)
    elif inputs.expected_gain <= break_even:
        verdict = CostVerdict.INFEASIBLE
        is_emittable = False
        uplift_detail = (
            f" (kyle_uplift={inputs.kyle_lambda_cost_uplift:.6f})"
            if inputs.kyle_lambda_cost_uplift > 0.0
            else ""
        )
        reason = f"gain {inputs.expected_gain:.6f} <= break-even {break_even:.6f}{uplift_detail}"
        reason_codes = (
            ("engine_a.cost.kyle_lambda_uplift_applied",)
            if inputs.kyle_lambda_cost_uplift > 0.0
            else ()
        ) + ("engine_a.cost.break_even_not_cleared",)
    elif ce < inputs.ce_min:
        verdict = CostVerdict.MARGINAL
        is_emittable = False
        uplift_detail = (
            f" (kyle_uplift={inputs.kyle_lambda_cost_uplift:.6f})"
            if inputs.kyle_lambda_cost_uplift > 0.0
            else ""
        )
        reason = f"CE {ce:.6f} < CE_min {inputs.ce_min:.6f}{uplift_detail}"
        reason_codes = (
            ("engine_a.cost.kyle_lambda_uplift_applied",)
            if inputs.kyle_lambda_cost_uplift > 0.0
            else ()
        ) + ("engine_a.cost.ce_below_min",)
    else:
        verdict = CostVerdict.FEASIBLE
        is_emittable = True
        reason = ""
        reason_codes = ()

    return CostResult(
        pair=inputs.pair,
        verdict=verdict,
        is_emittable=is_emittable,
        base_expected_cost=inputs.expected_cost,
        kyle_lambda_cost_uplift=inputs.kyle_lambda_cost_uplift,
        expected_cost=effective_expected_cost,
        break_even=break_even,
        ev_net=ev_net,
        ce_expected=ce,
        reason=reason,
        reason_codes=reason_codes,
        calibration_profile_id=ENGINE_A_COST_PROFILE_ID,
        calibration_status=ENGINE_A_COST_CALIBRATION_STATUS,
    )
