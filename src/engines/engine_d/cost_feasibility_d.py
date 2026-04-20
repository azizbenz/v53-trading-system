"""Pure cost-feasibility helpers for Engine D."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


ENGINE_D_CE_MIN_THRESHOLD_FAMILY_ID = "THR-E03"
ENGINE_D_DELTA_SAFE_THRESHOLD_FAMILY_ID = "THR-E04"
ENGINE_D_COST_PROFILE_ID = "engine_d_cost.to_calibrate.v1"


class EngineDCostCallerThresholds(BaseModel):
    """Caller-owned Engine D cost thresholds pending signed upstream governance."""

    delta_safe: float = Field(default=0.0005, ge=0.0)
    ce_min: float = Field(default=0.00012, ge=0.0)
    delta_safe_threshold_family_id: str = ENGINE_D_DELTA_SAFE_THRESHOLD_FAMILY_ID
    ce_min_threshold_family_id: str = ENGINE_D_CE_MIN_THRESHOLD_FAMILY_ID
    calibration_profile_id: str = ENGINE_D_COST_PROFILE_ID
    calibration_status: str = "TO_CALIBRATE"

    model_config = ConfigDict(frozen=True, extra="forbid")


ENGINE_D_COST_CALLER_THRESHOLDS_TO_CALIBRATE = EngineDCostCallerThresholds()
ENGINE_D_COST_CALLER_THRESHOLDS = ENGINE_D_COST_CALLER_THRESHOLDS_TO_CALIBRATE


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


class CostReasonCodeD(StrEnum):
    INVALID_CANDIDATE_SIZE = "invalid_candidate_size"
    INVALID_HOLDING_PERIOD = "invalid_holding_period"
    EDGE_BELOW_COST_BUFFER = "edge_below_cost_buffer"
    CE_BELOW_MIN = "ce_below_min"
    NON_POSITIVE_EV_NET = "non_positive_ev_net"


class CostMetricsD(BaseModel, frozen=True):
    expected_cost: float
    ce_expected: float
    ev_net: float
    is_feasible: bool
    cost_preference_score: float
    reason_codes: tuple[CostReasonCodeD, ...] = ()


def evaluate_cost_feasibility_d(
    *,
    expected_gain: float,
    expected_cost: float,
    candidate_size: float,
    holding_period: float,
    delta_safe: float,
    ce_min: float,
) -> CostMetricsD:
    """Evaluate cost feasibility using caller-governed thresholds.

    `delta_safe` and `ce_min` remain transitional TO_CALIBRATE inputs on this seam.
    """
    if candidate_size < 0.0:
        raise ValueError("candidate_size must be >= 0")
    if holding_period < 0.0:
        raise ValueError("holding_period must be >= 0")
    if expected_gain < 0.0:
        raise ValueError("expected_gain must be >= 0")
    if expected_cost < 0.0:
        raise ValueError("expected_cost must be >= 0")
    if delta_safe < 0.0:
        raise ValueError("delta_safe must be >= 0")
    if ce_min < 0.0:
        raise ValueError("ce_min must be >= 0")

    ev_net = candidate_size * (expected_gain - expected_cost)
    ce_expected = 0.0
    if holding_period > 0:
        ce_expected = (expected_gain - expected_cost) / holding_period

    reason_codes: list[CostReasonCodeD] = []
    if candidate_size == 0.0:
        reason_codes.append(CostReasonCodeD.INVALID_CANDIDATE_SIZE)
    if holding_period == 0.0:
        reason_codes.append(CostReasonCodeD.INVALID_HOLDING_PERIOD)
    if expected_gain <= expected_cost + delta_safe:
        reason_codes.append(CostReasonCodeD.EDGE_BELOW_COST_BUFFER)
    if ce_expected < ce_min:
        reason_codes.append(CostReasonCodeD.CE_BELOW_MIN)
    if ev_net <= 0.0:
        reason_codes.append(CostReasonCodeD.NON_POSITIVE_EV_NET)

    if expected_gain <= 0.0:
        cost_preference_score = 0.0
    else:
        cost_preference_score = _clamp(
            (expected_gain - expected_cost) / max(expected_gain, delta_safe, 1e-6)
        )

    return CostMetricsD(
        expected_cost=expected_cost,
        ce_expected=ce_expected,
        ev_net=ev_net,
        is_feasible=not reason_codes,
        cost_preference_score=cost_preference_score,
        reason_codes=tuple(dict.fromkeys(reason_codes)),
    )


__all__ = [
    "CostMetricsD",
    "CostReasonCodeD",
    "ENGINE_D_CE_MIN_THRESHOLD_FAMILY_ID",
    "ENGINE_D_COST_CALLER_THRESHOLDS",
    "ENGINE_D_COST_CALLER_THRESHOLDS_TO_CALIBRATE",
    "ENGINE_D_COST_PROFILE_ID",
    "ENGINE_D_DELTA_SAFE_THRESHOLD_FAMILY_ID",
    "EngineDCostCallerThresholds",
    "evaluate_cost_feasibility_d",
]
