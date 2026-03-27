"""
Build-9 / cra_monitor / phantom_risk_estimator
Estimate the risk of economic sterilization.

Phantom condition: x_i · E[r_i] <= c_i^op + epsilon
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from meta_minimal.cra_monitor.reduction_trace_reader import ReductionTrace


class PhantomRiskResult(BaseModel, frozen=True):
    """Result of phantom risk estimation."""

    pair: str
    engine_id: str
    expected_pnl: float  # final_size * ce_expected * holding_hours
    operational_cost: float
    net_expected: float  # expected_pnl - operational_cost
    phantom_risk_score: float  # 0.0=safe, 1.0=certain phantom
    is_high_risk: bool = False


# Epsilon: minimum net expected to be considered viable
_EPSILON = 0.50  # USD


def estimate_phantom_risk(
    trace: ReductionTrace,
    operational_cost: float = 0.0,
    epsilon: float = _EPSILON,
) -> PhantomRiskResult:
    """Estimate phantom trade risk from reduction trace.

    Phantom if: final_size * CE * hours <= cost + epsilon.
    Risk score: 1 - (net_expected / epsilon) clamped to [0, 1].
    """
    expected_pnl = trace.final_size * trace.ce_expected * max(trace.holding_hours, 1.0)
    cost = operational_cost if operational_cost > 0.0 else trace.expected_cost
    net = expected_pnl - cost

    if epsilon > 0.0:
        risk = max(0.0, min(1.0, 1.0 - net / epsilon))
    else:
        risk = 0.0 if net > 0.0 else 1.0

    return PhantomRiskResult(
        pair=trace.pair,
        engine_id=trace.engine_id,
        expected_pnl=expected_pnl,
        operational_cost=cost,
        net_expected=net,
        phantom_risk_score=risk,
        is_high_risk=(net <= epsilon),
    )
