"""
Build-7 / engine_b / anti_breakout_filter_B
Prevent Engine B from trading against genuine breakouts.

Reject or penalize when:
P(continuation hostile | context) > P(reversion exploitable | context)

Components: regime, volume anomaly, structural confirmation, microstructure.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel


class BreakoutVerdict(StrEnum):
    CLEAR = "clear"  # no breakout detected, safe for reversion
    WARNING = "warning"  # possible breakout, penalize
    BLOCKED = "blocked"  # confirmed breakout, reject reversion


class BreakoutInput(BaseModel, frozen=True):
    """Inputs for anti-breakout filter."""

    pair: str
    regime_trend_strength: float = 0.0  # [0,1] — how strongly trending
    volume_anomaly: float = 0.0  # [0,1] — abnormal volume in move direction
    structural_break: float = 0.0  # [0,1] — confirmation of level breach
    continuation_momentum: float = 0.0  # [0,1] — momentum continuation signal


class BreakoutResult(BaseModel, frozen=True):
    """Result of anti-breakout evaluation."""

    pair: str
    verdict: BreakoutVerdict
    breakout_score: float  # [0,1] — combined breakout risk
    reason: str = ""


_BLOCKED_THRESHOLD = 0.65
_WARNING_THRESHOLD = 0.35


def evaluate_breakout_risk(inputs: BreakoutInput) -> BreakoutResult:
    """Evaluate breakout risk for a mean-reversion candidate.

    breakout_score = 0.30·regime_trend + 0.25·volume_anomaly
                   + 0.25·structural_break + 0.20·continuation_momentum

    BLOCKED if score >= 0.65 (hostile continuation likely)
    WARNING if score >= 0.35 (ambiguous, penalize)
    CLEAR otherwise (safe for reversion)
    """
    score = (
        0.30 * inputs.regime_trend_strength
        + 0.25 * inputs.volume_anomaly
        + 0.25 * inputs.structural_break
        + 0.20 * inputs.continuation_momentum
    )

    if score >= _BLOCKED_THRESHOLD:
        verdict = BreakoutVerdict.BLOCKED
        reason = f"breakout risk {score:.3f} >= {_BLOCKED_THRESHOLD} — hostile continuation"
    elif score >= _WARNING_THRESHOLD:
        verdict = BreakoutVerdict.WARNING
        reason = f"breakout risk {score:.3f} — ambiguous, penalizing"
    else:
        verdict = BreakoutVerdict.CLEAR
        reason = ""

    return BreakoutResult(
        pair=inputs.pair,
        verdict=verdict,
        breakout_score=score,
        reason=reason,
    )
