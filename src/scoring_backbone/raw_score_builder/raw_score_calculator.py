"""
Build-5 / raw_score_builder / raw_score_calculator
Compute raw score from selected features and weights.

S_i^raw = Σ α_m · F_{i,m}
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class RawScoreResult(BaseModel, frozen=True):
    """Result of raw score computation."""

    engine_id: str
    pair: str
    raw_score: float
    weighted_contributions: dict[str, float] = Field(default_factory=dict)
    features_used: tuple[str, ...] = ()
    scoring_version: str = ""


def calculate_raw_score(
    engine_id: str,
    pair: str,
    features: dict[str, float],
    weights: dict[str, float],
    scoring_version: str = "",
) -> RawScoreResult:
    """Compute S_i^raw = Σ α_m · F_{i,m}.

    Features without a weight are ignored.
    Weights without a feature contribute 0.
    """
    contributions: dict[str, float] = {}
    features_used: list[str] = []

    for name, value in features.items():
        w = weights.get(name)
        if w is not None:
            contributions[name] = w * value
            features_used.append(name)

    raw_score = sum(contributions.values())

    return RawScoreResult(
        engine_id=engine_id,
        pair=pair,
        raw_score=raw_score,
        weighted_contributions=contributions,
        features_used=tuple(sorted(features_used)),
        scoring_version=scoring_version,
    )
