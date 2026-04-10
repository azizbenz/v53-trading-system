"""Pure conviction helpers for Engine C."""

from __future__ import annotations

from pydantic import BaseModel


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


class ConvictionResultC(BaseModel, frozen=True):
    raw_score: float
    conviction_score: float
    conviction_name: str
    tier_name: str


def build_conviction_c(
    *,
    breakout_score: float,
    continuation_score: float,
    context_score: float,
    ce_expected: float,
    ce_min: float,
    fake_breakout_risk: float,
) -> ConvictionResultC:
    raw_score = _clamp(
        0.40 * breakout_score
        + 0.30 * continuation_score
        + 0.20 * context_score
        + 0.10 * min(1.0, max(0.0, ce_expected / max(ce_min, 1e-6)))
    )
    conviction_score = max(0.0, raw_score - fake_breakout_risk * 0.10)

    if conviction_score >= 0.82:
        conviction_name = "high"
        tier_name = "tier_2"
    elif conviction_score >= 0.67:
        conviction_name = "medium"
        tier_name = "tier_1"
    else:
        conviction_name = "low"
        tier_name = "tier_1"

    return ConvictionResultC(
        raw_score=raw_score,
        conviction_score=conviction_score,
        conviction_name=conviction_name,
        tier_name=tier_name,
    )
