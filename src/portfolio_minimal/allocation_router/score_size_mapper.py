"""
Build-8 / allocation_router / score_size_mapper
Transform score / conviction into size modulation.

modulated_size = base_size × multiplier

Multiplier table by tier:
- tier_1: 1.0  (full size)
- tier_2: 0.6  (reduced)
- no_trade: 0.0

Score boost: if ranking_score > high_score_threshold, add up to +20%.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class SizeModulationResult(BaseModel, frozen=True):
    """Result of score-based size modulation."""

    pair: str
    base_size: float
    multiplier: float
    score_boost: float = 0.0
    modulated_size: float


# Tier multipliers
_TIER_MULTIPLIERS: dict[str, float] = {
    "tier_1": 1.0,
    "tier_2": 0.6,
    "no_trade": 0.0,
}

# Score boost parameters
_HIGH_SCORE_THRESHOLD = 0.7
_MAX_SCORE_BOOST = 0.20


def compute_modulated_size(
    pair: str,
    base_size: float,
    tier_suggestion: str,
    ranking_score: float = 0.0,
) -> SizeModulationResult:
    """Modulate base size by tier and optional score boost.

    1. Apply tier multiplier (1.0 for tier_1, 0.6 for tier_2, 0.0 for no_trade)
    2. If ranking_score > threshold, add proportional boost (up to +20%)
    """
    multiplier = _TIER_MULTIPLIERS.get(tier_suggestion, 0.0)

    score_boost = 0.0
    if ranking_score > _HIGH_SCORE_THRESHOLD and multiplier > 0.0:
        # Linear boost: (score - threshold) / (1 - threshold) × max_boost
        score_boost = min(
            (ranking_score - _HIGH_SCORE_THRESHOLD) / (1.0 - _HIGH_SCORE_THRESHOLD) * _MAX_SCORE_BOOST,
            _MAX_SCORE_BOOST,
        )

    effective_multiplier = multiplier + score_boost
    modulated = base_size * effective_multiplier

    return SizeModulationResult(
        pair=pair,
        base_size=base_size,
        multiplier=multiplier,
        score_boost=score_boost,
        modulated_size=modulated,
    )
