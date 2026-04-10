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
    base_raw_score: float = 0.0
    raw_score_multiplier: float = 1.0
    raw_score_add: float = 0.0
    raw_score_cap: float | None = None
    weighted_contributions: dict[str, float] = Field(default_factory=dict)
    features_used: tuple[str, ...] = ()
    scoring_version: str = ""


def calculate_raw_score(
    engine_id: str,
    pair: str,
    features: dict[str, float],
    weights: dict[str, float],
    scoring_version: str = "",
    *,
    raw_score_multiplier: float = 1.0,
    raw_score_add: float = 0.0,
    raw_score_cap: float | None = None,
) -> RawScoreResult:
    """Compute S_i^raw = Σ α_m · F_{i,m}.

    Features without a weight are ignored.
    Weights without a feature contribute 0.
    """
    normalized_scoring_version = _require_scoring_version(scoring_version, context="calculate_raw_score")
    normalized_multiplier = _require_raw_score_multiplier(
        raw_score_multiplier,
        context="calculate_raw_score",
    )
    normalized_add = _require_finite_value(
        raw_score_add,
        context="calculate_raw_score raw_score_add",
    )
    normalized_cap = _require_raw_score_cap(
        raw_score_cap,
        context="calculate_raw_score",
    )
    contributions: dict[str, float] = {}
    features_used: list[str] = []

    for name, value in features.items():
        w = weights.get(name)
        if w is not None:
            contributions[name] = w * value
            features_used.append(name)

    base_raw_score = sum(contributions.values())
    raw_score = base_raw_score * normalized_multiplier + normalized_add
    if normalized_cap is not None:
        raw_score = min(raw_score, normalized_cap)

    return RawScoreResult(
        engine_id=engine_id,
        pair=pair,
        raw_score=raw_score,
        base_raw_score=base_raw_score,
        raw_score_multiplier=normalized_multiplier,
        raw_score_add=normalized_add,
        raw_score_cap=normalized_cap,
        weighted_contributions=contributions,
        features_used=tuple(sorted(features_used)),
        scoring_version=normalized_scoring_version,
    )


def _require_scoring_version(scoring_version: str, *, context: str) -> str:
    """Reject blank score versions on the governed scoring rail."""

    normalized = scoring_version.strip()
    if not normalized:
        raise ValueError(f"{context} requires non-empty scoring_version")
    return normalized


def _require_finite_value(value: float, *, context: str) -> float:
    if value != value or value in {float("inf"), float("-inf")}:
        raise ValueError(f"{context} requires a finite value")
    return value


def _require_raw_score_multiplier(raw_score_multiplier: float, *, context: str) -> float:
    normalized = _require_finite_value(
        raw_score_multiplier,
        context=f"{context} raw_score_multiplier",
    )
    if normalized < 0.0:
        raise ValueError(f"{context} requires raw_score_multiplier >= 0")
    return normalized


def _require_raw_score_cap(raw_score_cap: float | None, *, context: str) -> float | None:
    if raw_score_cap is None:
        return None
    normalized = _require_finite_value(
        raw_score_cap,
        context=f"{context} raw_score_cap",
    )
    if normalized < 0.0:
        raise ValueError(f"{context} requires raw_score_cap >= 0")
    return normalized
