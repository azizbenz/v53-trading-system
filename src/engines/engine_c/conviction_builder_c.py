"""Pure conviction helpers for Engine C."""

from __future__ import annotations

from pydantic import BaseModel


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


_CONVICTION_EPSILON = 1e-12


class ConvictionResultC(BaseModel, frozen=True):
    ce_component: float
    raw_score: float
    conviction_score: float
    conviction_name: str
    tier_name: str
    is_emittable: bool


def build_conviction_c(
    *,
    breakout_score: float,
    continuation_score: float,
    context_score: float,
    ce_expected: float,
    ce_min: float,
    fake_breakout_risk: float,
) -> ConvictionResultC:
    ce_component = min(1.0, max(0.0, ce_expected / max(ce_min, 1e-6)))
    raw_score = _clamp(
        0.40 * breakout_score
        + 0.30 * continuation_score
        + 0.20 * context_score
        + 0.10 * ce_component
    )
    conviction_score = max(0.0, raw_score - fake_breakout_risk * 0.10)

    if conviction_score >= 0.82 - _CONVICTION_EPSILON:
        conviction_name = "high"
        tier_name = "tier_2"
        is_emittable = True
    elif conviction_score >= 0.67 - _CONVICTION_EPSILON:
        conviction_name = "medium"
        tier_name = "tier_1"
        is_emittable = True
    else:
        conviction_name = "low"
        tier_name = "no_trade"
        is_emittable = False

    return ConvictionResultC(
        ce_component=ce_component,
        raw_score=raw_score,
        conviction_score=conviction_score,
        conviction_name=conviction_name,
        tier_name=tier_name,
        is_emittable=is_emittable,
    )


__all__ = [
    "ConvictionResultC",
    "build_conviction_c",
]
