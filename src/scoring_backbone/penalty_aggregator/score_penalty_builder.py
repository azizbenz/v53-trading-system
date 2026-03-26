"""
Build-5 / penalty_aggregator / score_penalty_builder
Build additive penalty on score.

Pen_i = Σ pen_{i,ℓ}
S_i = S_i^raw - Pen_i
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ScorePenaltyItem(BaseModel, frozen=True):
    """A single score penalty contribution."""

    penalty_id: str
    value: float
    reason: str = ""


class ScorePenaltyResult(BaseModel, frozen=True):
    """Aggregated score penalty."""

    raw_score: float
    total_penalty: float
    adjusted_score: float
    penalties: tuple[ScorePenaltyItem, ...] = ()


def build_score_penalty(
    raw_score: float,
    penalties: tuple[ScorePenaltyItem, ...],
) -> ScorePenaltyResult:
    """Compute S_i = S_i^raw - Pen_i where Pen_i = Σ pen_{i,ℓ}."""
    total = sum(p.value for p in penalties)
    adjusted = raw_score - total

    return ScorePenaltyResult(
        raw_score=raw_score,
        total_penalty=total,
        adjusted_score=adjusted,
        penalties=penalties,
    )
