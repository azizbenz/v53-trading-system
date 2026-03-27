"""
Build-9 / cra_monitor / sterilization_classifier
Classify a trade as: healthy, reduced_viable, phantom_probable, phantom_confirmed.

Steril_i = 1{A_i=1} · 1{CE_i < CE_min}
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from meta_minimal.cra_monitor.reduction_trace_reader import ReductionTrace
from meta_minimal.cra_monitor.phantom_risk_estimator import PhantomRiskResult


class SterilizationClass(StrEnum):
    HEALTHY = "healthy"
    REDUCED_VIABLE = "reduced_viable"
    PHANTOM_PROBABLE = "phantom_probable"
    PHANTOM_CONFIRMED = "phantom_confirmed"


class SterilizationResult(BaseModel, frozen=True):
    """Classification result for a trade."""

    pair: str
    engine_id: str
    classification: SterilizationClass
    multiplier: float
    phantom_risk_score: float
    reason: str = ""


# Thresholds
_REDUCTION_THRESHOLD = 0.50  # multiplier below 50% = significant reduction
_PHANTOM_PROBABLE_RISK = 0.70
_PHANTOM_CONFIRMED_RISK = 0.90


def classify_sterilization(
    trace: ReductionTrace,
    risk: PhantomRiskResult,
    reduction_threshold: float = _REDUCTION_THRESHOLD,
) -> SterilizationResult:
    """Classify trade sterilization level.

    - HEALTHY: multiplier >= threshold, low phantom risk
    - REDUCED_VIABLE: multiplier < threshold but still economically viable
    - PHANTOM_PROBABLE: high phantom risk score
    - PHANTOM_CONFIRMED: very high risk or net_expected <= 0
    """
    if risk.phantom_risk_score >= _PHANTOM_CONFIRMED_RISK or risk.net_expected <= 0.0:
        cls = SterilizationClass.PHANTOM_CONFIRMED
        reason = f"net_expected={risk.net_expected:.4f}, risk={risk.phantom_risk_score:.2f}"
    elif risk.phantom_risk_score >= _PHANTOM_PROBABLE_RISK:
        cls = SterilizationClass.PHANTOM_PROBABLE
        reason = f"high phantom risk={risk.phantom_risk_score:.2f}"
    elif trace.multiplier < reduction_threshold:
        cls = SterilizationClass.REDUCED_VIABLE
        reason = f"multiplier={trace.multiplier:.2f} < {reduction_threshold}"
    else:
        cls = SterilizationClass.HEALTHY
        reason = ""

    return SterilizationResult(
        pair=trace.pair,
        engine_id=trace.engine_id,
        classification=cls,
        multiplier=trace.multiplier,
        phantom_risk_score=risk.phantom_risk_score,
        reason=reason,
    )
