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
from pydantic import BaseModel


class CostVerdict(StrEnum):
    FEASIBLE = "feasible"
    MARGINAL = "marginal"
    INFEASIBLE = "infeasible"


ENGINE_A_COST_PROFILE_ID = "engine_a_cost.to_calibrate.v1"
ENGINE_A_COST_CALIBRATION_STATUS = TO_CALIBRATE
ENGINE_A_COST_DEFAULTS: dict[str, float] = {
    "holding_period": 1.0,
    "delta_safe": 0.0005,
    "ce_min": 0.0001,
}


class CostInput(BaseModel, frozen=True):
    """Cost-related inputs for Engine A."""

    pair: str
    expected_gain: float
    expected_cost: float
    candidate_size: float
    holding_period: float = ENGINE_A_COST_DEFAULTS["holding_period"]
    delta_safe: float = ENGINE_A_COST_DEFAULTS["delta_safe"]
    ce_min: float = ENGINE_A_COST_DEFAULTS["ce_min"]


class CostResult(BaseModel, frozen=True):
    """Result of cost feasibility check."""

    pair: str
    verdict: CostVerdict
    expected_cost: float
    break_even: float
    ev_net: float
    ce_expected: float
    reason: str = ""
    calibration_profile_id: str = ENGINE_A_COST_PROFILE_ID
    calibration_status: str = ENGINE_A_COST_CALIBRATION_STATUS


def check_cost_feasibility(inputs: CostInput) -> CostResult:
    """Check if the expected edge covers cost with safety margin."""

    break_even = inputs.expected_cost + inputs.delta_safe
    edge = inputs.expected_gain - inputs.expected_cost
    ev_net = inputs.candidate_size * edge

    denom = inputs.candidate_size * inputs.holding_period
    ce = edge / inputs.holding_period if denom > 0 and inputs.candidate_size > 0 else 0.0

    if inputs.expected_gain <= break_even:
        verdict = CostVerdict.INFEASIBLE
        reason = f"gain {inputs.expected_gain:.6f} <= break-even {break_even:.6f}"
    elif ce < inputs.ce_min:
        verdict = CostVerdict.MARGINAL
        reason = f"CE {ce:.6f} < CE_min {inputs.ce_min:.6f}"
    else:
        verdict = CostVerdict.FEASIBLE
        reason = ""

    return CostResult(
        pair=inputs.pair,
        verdict=verdict,
        expected_cost=inputs.expected_cost,
        break_even=break_even,
        ev_net=ev_net,
        ce_expected=ce,
        reason=reason,
        calibration_profile_id=ENGINE_A_COST_PROFILE_ID,
        calibration_status=ENGINE_A_COST_CALIBRATION_STATUS,
    )
