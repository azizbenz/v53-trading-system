"""
Build-7 / engine_b / conviction_builder_B
Build Engine B conviction from excess, structure, context, cost preference.

S_B^raw = S_B^excess + S_B^structure + S_B^context + S_B^cost_preference

Engine B conviction is capped at MEDIUM — Tier 1-2 max, never Tier 3.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field
from data_backbone.market_physics_math import (
    clip01,
    execution_survivability_score_v1,
    fragility_score_v1,
    micro_friction_score_v1,
    toxicity_score_v1,
)


class ConvictionLevelB(StrEnum):
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"


class TierSuggestionB(StrEnum):
    TIER_2 = "tier_2"
    TIER_1 = "tier_1"
    NO_TRADE = "no_trade"


class ConvictionInputB(BaseModel, frozen=True):
    """Inputs for Engine B conviction building."""

    pair: str
    engine_id: str = "engine_b"
    excess_score: float  # from excess_detector
    structure_score: float  # range compatibility
    context_score: float  # regime/health/freshness
    cost_preference_score: float = 0.0  # cleaner = better
    sweep_score: float = 0.5
    absorption_score: float = 0.5
    poc_reversion_score: float = 0.5
    false_breakout_score: float = 0.0
    execution_fragility: float = 0.0
    market_toxicity: float = 0.0
    spread_regime_penalty: float = 0.0
    scoring_version: str = ""


class ConvictionResultB(BaseModel, frozen=True):
    """Engine B conviction output — Tier 3 never available."""

    pair: str
    engine_id: str
    raw_score: float
    block_scores: dict[str, float] = Field(default_factory=dict)
    conviction: ConvictionLevelB
    tier_suggestion: TierSuggestionB
    scoring_version: str = ""


_MEDIUM_THRESHOLD = 0.55
_LOW_THRESHOLD = 0.30


def build_conviction_b(inputs: ConvictionInputB) -> ConvictionResultB:
    """Build conviction from B's component scores.

    S_B^raw = 0.35·excess + 0.25·structure + 0.20·context + 0.20·cost_preference

    Conviction is capped at MEDIUM (Tier 2 max) — Engine B never gets Tier 3.
    """
    fragility_score = fragility_score_v1(
        inputs.execution_fragility,
        spread_regime_penalty=inputs.spread_regime_penalty,
    )
    toxicity_score = toxicity_score_v1(
        inputs.market_toxicity,
        fragility_score=fragility_score,
        spread_regime_penalty=inputs.spread_regime_penalty,
    )
    execution_survivability_score = execution_survivability_score_v1(
        fragility_score=fragility_score,
        toxicity_score=toxicity_score,
        spread_regime_penalty=inputs.spread_regime_penalty,
    )
    micro_friction_score = micro_friction_score_v1(
        spread_regime_penalty=inputs.spread_regime_penalty,
        fragility_score=fragility_score,
        toxicity_score=toxicity_score,
    )

    block_scores = {
        "excess": inputs.excess_score,
        "structure": inputs.structure_score,
        "context": inputs.context_score,
        "cost_preference": inputs.cost_preference_score,
        "sweep_score": inputs.sweep_score,
        "absorption_score": inputs.absorption_score,
        "poc_reversion_score": inputs.poc_reversion_score,
        "false_breakout_score": inputs.false_breakout_score,
        "execution_fragility": inputs.execution_fragility,
        "market_toxicity": inputs.market_toxicity,
        "spread_regime_penalty": inputs.spread_regime_penalty,
        "fragility_score": fragility_score,
        "toxicity_score": toxicity_score,
        "execution_survivability_score": execution_survivability_score,
        "micro_friction_score": micro_friction_score,
    }

    legacy_raw = (
        0.35 * inputs.excess_score
        + 0.25 * inputs.structure_score
        + 0.20 * inputs.context_score
        + 0.20 * inputs.cost_preference_score
    )
    sweep_adjustment = 0.08 * (inputs.sweep_score - 0.5)
    absorption_adjustment = 0.06 * (inputs.absorption_score - 0.5)
    poc_adjustment = 0.06 * (inputs.poc_reversion_score - 0.5)
    false_breakout_penalty = 0.10 * inputs.false_breakout_score
    execution_penalty = 0.08 * fragility_score
    toxicity_penalty = 0.07 * toxicity_score
    spread_penalty = 0.05 * micro_friction_score
    raw = clip01(
        legacy_raw
        + sweep_adjustment
        + absorption_adjustment
        + poc_adjustment
        - false_breakout_penalty
        - execution_penalty
        - toxicity_penalty
        - spread_penalty
    )

    if raw >= _MEDIUM_THRESHOLD:
        conviction = ConvictionLevelB.MEDIUM
        tier = TierSuggestionB.TIER_2
    elif raw >= _LOW_THRESHOLD:
        conviction = ConvictionLevelB.LOW
        tier = TierSuggestionB.TIER_1
    else:
        conviction = ConvictionLevelB.NONE
        tier = TierSuggestionB.NO_TRADE

    return ConvictionResultB(
        pair=inputs.pair,
        engine_id=inputs.engine_id,
        raw_score=raw,
        block_scores=block_scores,
        conviction=conviction,
        tier_suggestion=tier,
        scoring_version=inputs.scoring_version,
    )
