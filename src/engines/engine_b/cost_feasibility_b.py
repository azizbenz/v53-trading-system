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
from pydantic import BaseModel, Field


class CostVerdictB(StrEnum):
    FEASIBLE = "feasible"
    MARGINAL = "marginal"
    INFEASIBLE = "infeasible"


class CostReasonCodeB(StrEnum):
    INVALID_CANDIDATE_SIZE = "invalid_candidate_size"
    INVALID_HOLDING_PERIOD = "invalid_holding_period"
    BREAK_EVEN_NOT_CLEARED = "break_even_not_cleared"
    NON_POSITIVE_EV_NET = "non_positive_ev_net"
    CE_BELOW_MINIMUM = "ce_below_minimum"


ENGINE_B_COST_PROFILE_ID = "engine_b_cost.to_calibrate.v1"
ENGINE_B_COST_CALIBRATION_STATUS = TO_CALIBRATE
ENGINE_B_DELTA_SAFE_THRESHOLD_ID = "THR-B01"
ENGINE_B_CE_MIN_THRESHOLD_ID = "THR-B02"
# TO_CALIBRATE: grouped Engine B cost defaults pending signed calibration.
ENGINE_B_COST_DEFAULTS: dict[str, float] = {
    "holding_period": 2.0,
    "delta_safe": 0.0008,
    "ce_min": 0.0002,
}


class EngineBCostThresholds(BaseModel, frozen=True):
    """Single-source threshold ownership for Engine B cost governance."""

    holding_period: float = Field(default=ENGINE_B_COST_DEFAULTS["holding_period"], gt=0.0)
    delta_safe: float = Field(default=ENGINE_B_COST_DEFAULTS["delta_safe"], ge=0.0)
    ce_min: float = Field(default=ENGINE_B_COST_DEFAULTS["ce_min"], ge=0.0)
    delta_safe_threshold_id: str = ENGINE_B_DELTA_SAFE_THRESHOLD_ID
    ce_min_threshold_id: str = ENGINE_B_CE_MIN_THRESHOLD_ID
    calibration_profile_id: str = ENGINE_B_COST_PROFILE_ID
    calibration_status: str = ENGINE_B_COST_CALIBRATION_STATUS


ENGINE_B_COST_THRESHOLDS_TO_CALIBRATE = EngineBCostThresholds()


class CostInputB(BaseModel, frozen=True):
    """Cost inputs for Engine B, stricter defaults than A."""

    pair: str
    expected_gain: float = Field(ge=0.0)
    expected_cost: float = Field(ge=0.0)
    candidate_size: float = Field(ge=0.0)
    holding_period: float = Field(default=ENGINE_B_COST_THRESHOLDS_TO_CALIBRATE.holding_period, ge=0.0)
    delta_safe: float = Field(default=ENGINE_B_COST_THRESHOLDS_TO_CALIBRATE.delta_safe, ge=0.0)
    ce_min: float = Field(default=ENGINE_B_COST_THRESHOLDS_TO_CALIBRATE.ce_min, ge=0.0)


class CostResultB(BaseModel, frozen=True):
    """Result of B's cost feasibility check."""

    pair: str
    verdict: CostVerdictB
    is_emittable: bool
    expected_cost: float
    break_even: float
    ev_net: float
    ce_expected: float
    reason: str = ""
    reason_codes: tuple[CostReasonCodeB, ...] = ()
    calibration_profile_id: str = ENGINE_B_COST_PROFILE_ID
    calibration_status: str = ENGINE_B_COST_CALIBRATION_STATUS


def check_cost_feasibility_b(inputs: CostInputB) -> CostResultB:
    """Check if the expected edge covers cost with B's stricter safety margin."""

    break_even = inputs.expected_cost + inputs.delta_safe
    edge = inputs.expected_gain - inputs.expected_cost
    ev_net = inputs.candidate_size * edge

    ce = edge / inputs.holding_period if inputs.holding_period > 0 and inputs.candidate_size > 0 else 0.0
    reason_codes: tuple[CostReasonCodeB, ...]

    if inputs.candidate_size <= 0.0:
        verdict = CostVerdictB.INFEASIBLE
        reason = "candidate_size must be > 0"
        reason_codes = (CostReasonCodeB.INVALID_CANDIDATE_SIZE,)
    elif inputs.holding_period <= 0.0:
        verdict = CostVerdictB.INFEASIBLE
        reason = "holding_period must be > 0"
        reason_codes = (CostReasonCodeB.INVALID_HOLDING_PERIOD,)
    elif inputs.expected_gain <= break_even:
        verdict = CostVerdictB.INFEASIBLE
        reason = f"gain {inputs.expected_gain:.6f} <= break-even {break_even:.6f}"
        reason_codes = (CostReasonCodeB.BREAK_EVEN_NOT_CLEARED,)
    elif ev_net <= 0.0:
        verdict = CostVerdictB.INFEASIBLE
        reason = f"EV_net {ev_net:.6f} <= 0"
        reason_codes = (CostReasonCodeB.NON_POSITIVE_EV_NET,)
    elif ce < inputs.ce_min:
        verdict = CostVerdictB.MARGINAL
        reason = f"CE {ce:.6f} < CE_min {inputs.ce_min:.6f}"
        reason_codes = (CostReasonCodeB.CE_BELOW_MINIMUM,)
    else:
        verdict = CostVerdictB.FEASIBLE
        reason = ""
        reason_codes = ()

    return CostResultB(
        pair=inputs.pair,
        verdict=verdict,
        is_emittable=verdict == CostVerdictB.FEASIBLE,
        expected_cost=inputs.expected_cost,
        break_even=break_even,
        ev_net=ev_net,
        ce_expected=ce,
        reason=reason,
        reason_codes=reason_codes,
        calibration_profile_id=ENGINE_B_COST_PROFILE_ID,
        calibration_status=ENGINE_B_COST_CALIBRATION_STATUS,
    )
