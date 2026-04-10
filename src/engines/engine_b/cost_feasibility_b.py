"""
Build-7 / engine_b / cost_feasibility_B
Cost check for mean-reversion, stricter than Engine A.

Condition: E[g_i | B,j,s] > E[c_i | B,j,s] + delta_safe_B
           EV_net_B = x * (E[g] - E[c]) > eps
           CE_B > CE_min_B
"""

from __future__ import annotations

from enum import StrEnum

from data_backbone import TO_CALIBRATE
from pydantic import BaseModel


class CostVerdictB(StrEnum):
    FEASIBLE = "feasible"
    MARGINAL = "marginal"
    INFEASIBLE = "infeasible"


ENGINE_B_COST_PROFILE_ID = "engine_b_cost.to_calibrate.v1"
ENGINE_B_COST_CALIBRATION_STATUS = TO_CALIBRATE
ENGINE_B_COST_DEFAULTS: dict[str, float] = {
    "holding_period": 2.0,
    "delta_safe": 0.0008,
    "ce_min": 0.0002,
}


class CostInputB(BaseModel, frozen=True):
    """Cost inputs for Engine B, stricter defaults than A."""

    pair: str
    expected_gain: float
    expected_cost: float
    candidate_size: float
    holding_period: float = ENGINE_B_COST_DEFAULTS["holding_period"]
    delta_safe: float = ENGINE_B_COST_DEFAULTS["delta_safe"]
    ce_min: float = ENGINE_B_COST_DEFAULTS["ce_min"]


class CostResultB(BaseModel, frozen=True):
    """Result of B's cost feasibility check."""

    pair: str
    verdict: CostVerdictB
    expected_cost: float
    break_even: float
    ev_net: float
    ce_expected: float
    reason: str = ""
    calibration_profile_id: str = ENGINE_B_COST_PROFILE_ID
    calibration_status: str = ENGINE_B_COST_CALIBRATION_STATUS


def check_cost_feasibility_b(inputs: CostInputB) -> CostResultB:
    """Check if the expected edge covers cost with B's stricter safety margin."""

    break_even = inputs.expected_cost + inputs.delta_safe
    edge = inputs.expected_gain - inputs.expected_cost
    ev_net = inputs.candidate_size * edge

    ce = edge / inputs.holding_period if inputs.holding_period > 0 and inputs.candidate_size > 0 else 0.0

    if inputs.expected_gain <= break_even:
        verdict = CostVerdictB.INFEASIBLE
        reason = f"gain {inputs.expected_gain:.6f} <= break-even {break_even:.6f}"
    elif ce < inputs.ce_min:
        verdict = CostVerdictB.MARGINAL
        reason = f"CE {ce:.6f} < CE_min {inputs.ce_min:.6f}"
    else:
        verdict = CostVerdictB.FEASIBLE
        reason = ""

    return CostResultB(
        pair=inputs.pair,
        verdict=verdict,
        expected_cost=inputs.expected_cost,
        break_even=break_even,
        ev_net=ev_net,
        ce_expected=ce,
        reason=reason,
        calibration_profile_id=ENGINE_B_COST_PROFILE_ID,
        calibration_status=ENGINE_B_COST_CALIBRATION_STATUS,
    )
