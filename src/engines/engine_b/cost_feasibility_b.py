"""
Build-7 / engine_b / cost_feasibility_B
Cost check for mean-reversion — stricter than Engine A.

Condition: E[g_i | B,j,s] > E[c_i | B,j,s] + δ_safe,B
           EV_net_B = x · (E[g] - E[c]) > ε
           CE_B > CE_min,B

δ_safe,B > δ_safe,A because Engine B has thinner edge.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel


class CostVerdictB(StrEnum):
    FEASIBLE = "feasible"
    MARGINAL = "marginal"
    INFEASIBLE = "infeasible"


class CostInputB(BaseModel, frozen=True):
    """Cost inputs for Engine B — stricter defaults than A."""

    pair: str
    expected_gain: float  # E[g_i | B,j,s]
    expected_cost: float  # E[c_i | B,j,s]
    candidate_size: float
    holding_period: float = 2.0  # hours — shorter than A
    delta_safe: float = 0.0008  # stricter than A's 0.0005
    ce_min: float = 0.0002  # stricter than A's 0.0001


class CostResultB(BaseModel, frozen=True):
    """Result of B's cost feasibility check."""

    pair: str
    verdict: CostVerdictB
    expected_cost: float
    break_even: float  # E[c] + δ_safe,B
    ev_net: float  # x · (E[g] - E[c])
    ce_expected: float  # edge / holding_period
    reason: str = ""


def check_cost_feasibility_b(inputs: CostInputB) -> CostResultB:
    """Check if the expected edge covers cost with B's stricter safety margin.

    B is more fragile to cost than A — δ_safe,B defaults to 0.0008.
    """
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
    )
