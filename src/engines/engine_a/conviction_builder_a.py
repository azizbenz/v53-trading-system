"""
Build-6 / engine_a / conviction_builder_A
Build Engine A conviction level from structure, context, cost.

S_A^raw = S_A^structure + S_A^context + S_A^flow + S_A^cost_preference

Conviction reflects quality relative to the signal, not absolute certainty.
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


class ConvictionLevel(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"


class TierSuggestion(StrEnum):
    TIER_3 = "tier_3"
    TIER_2 = "tier_2"
    TIER_1 = "tier_1"
    NO_TRADE = "no_trade"


class ConvictionInput(BaseModel, frozen=True):
    """Inputs for conviction building."""

    pair: str
    engine_id: str = "engine_a"
    structure_score: float
    context_score: float
    flow_score: float = 0.0
    cost_preference_score: float = 0.0
    delta_confirmation: float = 0.5
    execution_fragility: float = 0.0
    market_toxicity: float = 0.0
    spread_regime_penalty: float = 0.0
    competition_density: float = 0.5
    scoring_version: str = ""


class ConvictionResult(BaseModel, frozen=True):
    """Conviction output with full score decomposition."""

    pair: str
    engine_id: str
    raw_score: float
    block_scores: dict[str, float] = Field(default_factory=dict)
    conviction: ConvictionLevel
    tier_suggestion: TierSuggestion
    scoring_version: str = ""


_HIGH_THRESHOLD = 0.70
_MEDIUM_THRESHOLD = 0.45
_LOW_THRESHOLD = 0.25


def build_conviction(inputs: ConvictionInput) -> ConvictionResult:
    """Build conviction from component scores.

    S_A^raw = S_A^structure + S_A^context + S_A^flow + S_A^cost_preference
    All components are expected in [0, 1] range; raw score in [0, 4] conceptually.
    Normalized to [0, 1] for conviction thresholds.
    """
    competition_support = clip01(1.0 - inputs.competition_density)
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
        "structure": inputs.structure_score,
        "context": inputs.context_score,
        "flow": inputs.flow_score,
        "cost_preference": inputs.cost_preference_score,
        "delta_confirmation": inputs.delta_confirmation,
        "execution_fragility": inputs.execution_fragility,
        "market_toxicity": inputs.market_toxicity,
        "spread_regime_penalty": inputs.spread_regime_penalty,
        "competition_support": competition_support,
        "fragility_score": fragility_score,
        "toxicity_score": toxicity_score,
        "execution_survivability_score": execution_survivability_score,
        "micro_friction_score": micro_friction_score,
    }

    legacy_raw = (
        0.40 * inputs.structure_score
        + 0.25 * inputs.context_score
        + 0.15 * inputs.flow_score
        + 0.20 * inputs.cost_preference_score
    )
    delta_adjustment = 0.12 * (inputs.delta_confirmation - 0.5)
    competition_adjustment = 0.08 * (competition_support - 0.5)
    execution_penalty = 0.10 * fragility_score
    toxicity_penalty = 0.08 * toxicity_score
    spread_penalty = 0.07 * micro_friction_score
    raw = clip01(
        legacy_raw
        + delta_adjustment
        + competition_adjustment
        - execution_penalty
        - toxicity_penalty
        - spread_penalty
    )

    if raw >= _HIGH_THRESHOLD:
        conviction = ConvictionLevel.HIGH
        tier = TierSuggestion.TIER_3
    elif raw >= _MEDIUM_THRESHOLD:
        conviction = ConvictionLevel.MEDIUM
        tier = TierSuggestion.TIER_2
    elif raw >= _LOW_THRESHOLD:
        conviction = ConvictionLevel.LOW
        tier = TierSuggestion.TIER_1
    else:
        conviction = ConvictionLevel.NONE
        tier = TierSuggestion.NO_TRADE

    return ConvictionResult(
        pair=inputs.pair,
        engine_id=inputs.engine_id,
        raw_score=raw,
        block_scores=block_scores,
        conviction=conviction,
        tier_suggestion=tier,
        scoring_version=inputs.scoring_version,
    )
