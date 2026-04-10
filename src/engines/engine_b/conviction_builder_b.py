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
    MARKET_PHYSICS_CALIBRATION_PROFILE_ID,
    MARKET_PHYSICS_CALIBRATION_STATUS,
    TO_CALIBRATE,
    clip01,
    execution_survivability_score_v1,
    fragility_score_v1,
    micro_friction_score_v1,
    toxicity_score_v1,
    ENGINE_CONVICTION_PHYSICS_PENALTY_WEIGHTS,
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
    false_breakout_score: float = 0.5
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
    calibration_profile_id: str = "engine_b_conviction.to_calibrate.v1"
    calibration_status: str = TO_CALIBRATE
    physics_calibration_profile_id: str = MARKET_PHYSICS_CALIBRATION_PROFILE_ID
    physics_calibration_status: str = MARKET_PHYSICS_CALIBRATION_STATUS


ENGINE_B_CONVICTION_PROFILE_ID = "engine_b_conviction.to_calibrate.v1"
ENGINE_B_CONVICTION_CALIBRATION_STATUS = TO_CALIBRATE
ENGINE_B_CONVICTION_INPUT_DEFAULTS: dict[str, float | str] = {
    "cost_preference_score": 0.0,
    "sweep_score": 0.5,
    "absorption_score": 0.5,
    "poc_reversion_score": 0.5,
    "false_breakout_score": 0.5,
    "execution_fragility": 0.0,
    "market_toxicity": 0.0,
    "spread_regime_penalty": 0.0,
    "scoring_version": "",
}
ENGINE_B_CONVICTION_NORMALIZATION: dict[str, float] = {
    "neutral_midpoint": 0.5,
}
ENGINE_B_CONVICTION_FEATURE_WEIGHTS: dict[str, float] = {
    "excess": 0.35,
    "structure": 0.25,
    "context": 0.20,
    "cost_preference": 0.20,
}
ENGINE_B_CONVICTION_ADJUSTMENT_WEIGHTS: dict[str, float] = {
    "sweep_score": 0.08,
    "absorption_score": 0.06,
    "poc_reversion_score": 0.06,
    "false_breakout_penalty": 0.10,
    **ENGINE_CONVICTION_PHYSICS_PENALTY_WEIGHTS,
}
ENGINE_B_CONVICTION_THRESHOLDS: dict[str, float] = {
    "medium": 0.55,
    "low": 0.30,
}

ConvictionInputB.model_fields["cost_preference_score"].default = ENGINE_B_CONVICTION_INPUT_DEFAULTS["cost_preference_score"]
ConvictionInputB.model_fields["sweep_score"].default = ENGINE_B_CONVICTION_INPUT_DEFAULTS["sweep_score"]
ConvictionInputB.model_fields["absorption_score"].default = ENGINE_B_CONVICTION_INPUT_DEFAULTS["absorption_score"]
ConvictionInputB.model_fields["poc_reversion_score"].default = ENGINE_B_CONVICTION_INPUT_DEFAULTS["poc_reversion_score"]
ConvictionInputB.model_fields["false_breakout_score"].default = ENGINE_B_CONVICTION_INPUT_DEFAULTS["false_breakout_score"]
ConvictionInputB.model_fields["execution_fragility"].default = ENGINE_B_CONVICTION_INPUT_DEFAULTS["execution_fragility"]
ConvictionInputB.model_fields["market_toxicity"].default = ENGINE_B_CONVICTION_INPUT_DEFAULTS["market_toxicity"]
ConvictionInputB.model_fields["spread_regime_penalty"].default = ENGINE_B_CONVICTION_INPUT_DEFAULTS["spread_regime_penalty"]
ConvictionInputB.model_fields["scoring_version"].default = ENGINE_B_CONVICTION_INPUT_DEFAULTS["scoring_version"]


def build_conviction_b(inputs: ConvictionInputB) -> ConvictionResultB:
    """Build conviction from B's component scores.

    S_B^raw = 0.35·excess + 0.25·structure + 0.20·context + 0.20·cost_preference

    Conviction is capped at MEDIUM (Tier 2 max) — Engine B never gets Tier 3.
    """
    neutral_midpoint = ENGINE_B_CONVICTION_NORMALIZATION["neutral_midpoint"]
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
        ENGINE_B_CONVICTION_FEATURE_WEIGHTS["excess"] * inputs.excess_score
        + ENGINE_B_CONVICTION_FEATURE_WEIGHTS["structure"] * inputs.structure_score
        + ENGINE_B_CONVICTION_FEATURE_WEIGHTS["context"] * inputs.context_score
        + ENGINE_B_CONVICTION_FEATURE_WEIGHTS["cost_preference"]
        * inputs.cost_preference_score
    )
    sweep_adjustment = (
        ENGINE_B_CONVICTION_ADJUSTMENT_WEIGHTS["sweep_score"]
        * (inputs.sweep_score - neutral_midpoint)
    )
    absorption_adjustment = (
        ENGINE_B_CONVICTION_ADJUSTMENT_WEIGHTS["absorption_score"]
        * (inputs.absorption_score - neutral_midpoint)
    )
    poc_adjustment = (
        ENGINE_B_CONVICTION_ADJUSTMENT_WEIGHTS["poc_reversion_score"]
        * (inputs.poc_reversion_score - neutral_midpoint)
    )
    false_breakout_penalty = (
        ENGINE_B_CONVICTION_ADJUSTMENT_WEIGHTS["false_breakout_penalty"]
        * inputs.false_breakout_score
    )
    execution_penalty = (
        ENGINE_B_CONVICTION_ADJUSTMENT_WEIGHTS["fragility_penalty"] * fragility_score
    )
    toxicity_penalty = (
        ENGINE_B_CONVICTION_ADJUSTMENT_WEIGHTS["toxicity_penalty"] * toxicity_score
    )
    spread_penalty = (
        ENGINE_B_CONVICTION_ADJUSTMENT_WEIGHTS["micro_friction_penalty"]
        * micro_friction_score
    )
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

    if raw >= ENGINE_B_CONVICTION_THRESHOLDS["medium"]:
        conviction = ConvictionLevelB.MEDIUM
        tier = TierSuggestionB.TIER_2
    elif raw >= ENGINE_B_CONVICTION_THRESHOLDS["low"]:
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
        calibration_profile_id=ENGINE_B_CONVICTION_PROFILE_ID,
        calibration_status=ENGINE_B_CONVICTION_CALIBRATION_STATUS,
        physics_calibration_profile_id=MARKET_PHYSICS_CALIBRATION_PROFILE_ID,
        physics_calibration_status=MARKET_PHYSICS_CALIBRATION_STATUS,
    )
