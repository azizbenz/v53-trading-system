"""
Build-6 / engine_a / context_validator_A
Validate that context does not contradict the structural signal.

Context does not decide — it confirms, degrades, or blocks (only if fatal).
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel


class ContextVerdict(StrEnum):
    CONFIRMING = "confirming"
    NEUTRAL = "neutral"
    DEGRADED = "degraded"
    FATAL = "fatal"


class ContextInput(BaseModel, frozen=True):
    """Contextual inputs for Engine A validation."""

    pair: str
    regime_favorability: float  # [0, 1] — 1=ideal trend regime
    regime_confidence: float  # [0, 1]
    pair_health: float  # [0, 1]
    data_freshness: float  # [0, 1] — 1=perfectly fresh
    flow_coherence: float  # [0, 1]


class ContextResult(BaseModel, frozen=True):
    """Result of context validation."""

    pair: str
    verdict: ContextVerdict
    context_score: float
    reason: str = ""


_FATAL_THRESHOLD = 0.15
_DEGRADED_THRESHOLD = 0.35
_CONFIRMING_THRESHOLD = 0.65


def validate_context(inputs: ContextInput) -> ContextResult:
    """Evaluate context compatibility for Engine A.

    context_score = 0.30·regime + 0.20·regime_conf + 0.20·health + 0.15·freshness + 0.15·flow
    """
    score = (
        0.30 * inputs.regime_favorability
        + 0.20 * inputs.regime_confidence
        + 0.20 * inputs.pair_health
        + 0.15 * inputs.data_freshness
        + 0.15 * inputs.flow_coherence
    )

    if score < _FATAL_THRESHOLD:
        verdict = ContextVerdict.FATAL
        reason = f"context fatal: score {score:.3f} < {_FATAL_THRESHOLD}"
    elif score < _DEGRADED_THRESHOLD:
        verdict = ContextVerdict.DEGRADED
        reason = f"context degraded: score {score:.3f}"
    elif score >= _CONFIRMING_THRESHOLD:
        verdict = ContextVerdict.CONFIRMING
        reason = ""
    else:
        verdict = ContextVerdict.NEUTRAL
        reason = ""

    return ContextResult(
        pair=inputs.pair,
        verdict=verdict,
        context_score=score,
        reason=reason,
    )
