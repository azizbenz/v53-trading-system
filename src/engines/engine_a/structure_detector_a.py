"""
Build-6 / engine_a / structure_detector_A
Detect exploitable trend/expansion structure.

A premium setup requires:
- readable direction
- coherent continuation
- no major structural contradiction
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class StructureVerdict(StrEnum):
    FAVORABLE = "favorable"
    MARGINAL = "marginal"
    UNFAVORABLE = "unfavorable"


class StructureInput(BaseModel, frozen=True):
    """Structural inputs for Engine A detection."""

    pair: str
    direction_score: float  # [-1, 1] — dominant local direction quality
    continuation_score: float  # [0, 1] — quality of continuation
    structure_quality: float  # [0, 1] — overall structure readability
    zone_proximity: float  # [0, 1] — proximity to relevant zones (higher = closer)
    trend_stability: float  # [0, 1] — stability of the trend


class StructureResult(BaseModel, frozen=True):
    """Result of structure detection."""

    pair: str
    verdict: StructureVerdict
    structure_score: float  # combined structural score
    direction_strength: float
    continuation_strength: float
    reason: str = ""


# Thresholds
_FAVORABLE_THRESHOLD = 0.6
_MARGINAL_THRESHOLD = 0.3
_MIN_DIRECTION = 0.2


def detect_structure(inputs: StructureInput) -> StructureResult:
    """Evaluate whether a premium trend/expansion structure is present.

    structure_score = 0.35·|direction| + 0.25·continuation + 0.25·quality + 0.15·stability
    """
    direction_strength = abs(inputs.direction_score)
    continuation_strength = inputs.continuation_score

    score = (
        0.35 * direction_strength
        + 0.25 * continuation_strength
        + 0.25 * inputs.structure_quality
        + 0.15 * inputs.trend_stability
    )

    if direction_strength < _MIN_DIRECTION:
        verdict = StructureVerdict.UNFAVORABLE
        reason = f"direction too weak: {direction_strength:.3f} < {_MIN_DIRECTION}"
    elif score >= _FAVORABLE_THRESHOLD:
        verdict = StructureVerdict.FAVORABLE
        reason = ""
    elif score >= _MARGINAL_THRESHOLD:
        verdict = StructureVerdict.MARGINAL
        reason = f"structure marginal: score {score:.3f}"
    else:
        verdict = StructureVerdict.UNFAVORABLE
        reason = f"structure insufficient: score {score:.3f} < {_MARGINAL_THRESHOLD}"

    return StructureResult(
        pair=inputs.pair,
        verdict=verdict,
        structure_score=score,
        direction_strength=direction_strength,
        continuation_strength=continuation_strength,
        reason=reason,
    )
