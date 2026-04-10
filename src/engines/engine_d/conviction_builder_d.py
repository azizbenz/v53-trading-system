"""Pure conviction helpers for Engine D."""

from __future__ import annotations

from pydantic import BaseModel


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


class ConvictionResultD(BaseModel, frozen=True):
    raw_score: float
    conviction_score: float
    conviction_name: str
    tier_name: str


def build_conviction_d(
    *,
    history_score: float,
    reformation_score: float,
    marginal_value_score: float,
    ce_expected: float,
    ce_min: float,
    concentration_risk: float,
) -> ConvictionResultD:
    raw_score = _clamp(
        0.30 * history_score
        + 0.30 * reformation_score
        + 0.25 * marginal_value_score
        + 0.15 * min(1.0, max(0.0, ce_expected / max(ce_min, 1e-6)))
    )
    conviction_score = max(0.0, raw_score - concentration_risk * 0.12)

    if conviction_score >= 0.80:
        conviction_name = "high"
        tier_name = "tier_2"
    elif conviction_score >= 0.64:
        conviction_name = "medium"
        tier_name = "tier_1"
    else:
        conviction_name = "low"
        tier_name = "tier_1"

    return ConvictionResultD(
        raw_score=raw_score,
        conviction_score=conviction_score,
        conviction_name=conviction_name,
        tier_name=tier_name,
    )
