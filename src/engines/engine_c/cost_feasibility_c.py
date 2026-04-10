"""Pure cost-feasibility helpers for Engine C."""

from __future__ import annotations

from pydantic import BaseModel


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


class CostMetricsC(BaseModel, frozen=True):
    expected_cost: float
    ce_expected: float
    ev_net: float
    is_feasible: bool
    cost_preference_score: float


def evaluate_cost_feasibility_c(
    *,
    expected_gain: float,
    expected_cost: float,
    candidate_size: float,
    holding_period: float,
    delta_safe: float,
    ce_min: float,
) -> CostMetricsC:
    ev_net = candidate_size * (expected_gain - expected_cost)
    ce_expected = 0.0
    if holding_period > 0:
        ce_expected = (expected_gain - expected_cost) / holding_period

    return CostMetricsC(
        expected_cost=expected_cost,
        ce_expected=ce_expected,
        ev_net=ev_net,
        is_feasible=expected_gain > expected_cost + delta_safe and ce_expected >= ce_min,
        cost_preference_score=_clamp((expected_gain - expected_cost) / max(expected_gain, delta_safe)),
    )
