"""Bounded non-positive score-fusion math for the Local-Lab ML confidence layer."""

from __future__ import annotations

import math

from pydantic import BaseModel, Field, field_validator


class MlFusionResult(BaseModel, frozen=True):
    """Typed result of bounded non-positive ML score modulation."""

    base_score: float
    fused_score: float
    ml_confidence: float = Field(..., ge=0.0, le=1.0)
    alpha: float = Field(..., ge=0.0, le=0.5)
    multiplier_delta: float
    applied: bool = True
    reason: str = "applied"

    @field_validator("base_score", "fused_score", "multiplier_delta")
    @classmethod
    def _validate_finite(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("MlFusionResult values must be finite")
        return value


def _clip_ml_confidence(ml_confidence: float) -> float:
    if not math.isfinite(ml_confidence):
        raise ValueError("ml_confidence must be finite")
    return min(1.0, max(0.0, ml_confidence))


def validate_alpha(alpha: float) -> float:
    """Validate the bounded ML fusion alpha."""

    if not math.isfinite(alpha):
        raise ValueError("alpha must be finite")
    if alpha < 0.0:
        raise ValueError("alpha must be >= 0.0")
    if alpha > 0.5:
        raise ValueError("alpha must be <= 0.5")
    return alpha


def confidence_to_multiplier_delta(*, ml_confidence: float, alpha: float) -> float:
    """Return the exact bounded non-positive multiplier delta implied by ML confidence."""

    normalized_alpha = validate_alpha(alpha)
    normalized_confidence = _clip_ml_confidence(ml_confidence)
    return min(
        0.0,
        normalized_alpha * (normalized_confidence - 0.5),
    )


def apply_ml_score_fusion(
    *,
    base_score: float,
    ml_confidence: float | None,
    alpha: float,
    artifact_ready: bool = True,
) -> MlFusionResult:
    """Apply bounded non-positive modulation or degrade gracefully to baseline."""

    if not math.isfinite(base_score):
        raise ValueError("base_score must be finite")
    normalized_alpha = validate_alpha(alpha)
    if not artifact_ready or ml_confidence is None:
        return MlFusionResult(
            base_score=base_score,
            fused_score=base_score,
            ml_confidence=0.5,
            alpha=normalized_alpha,
            multiplier_delta=0.0,
            applied=False,
            reason="artifact_missing_or_unavailable",
        )

    normalized_confidence = _clip_ml_confidence(ml_confidence)
    multiplier_delta = confidence_to_multiplier_delta(
        ml_confidence=normalized_confidence,
        alpha=normalized_alpha,
    )
    fused_score = base_score * (1 + multiplier_delta)
    return MlFusionResult(
        base_score=base_score,
        fused_score=fused_score,
        ml_confidence=normalized_confidence,
        alpha=normalized_alpha,
        multiplier_delta=multiplier_delta,
        applied=True,
        reason="applied",
    )


__all__ = [
    "MlFusionResult",
    "validate_alpha",
    "confidence_to_multiplier_delta",
    "apply_ml_score_fusion",
]
