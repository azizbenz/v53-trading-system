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
    structure_score: float = Field(..., ge=0.0, le=1.0)
    context_score: float = Field(..., ge=0.0, le=1.0)
    flow_score: float = Field(default=0.0, ge=0.0, le=1.0)
    ofi_flow_score: float | None = Field(default=None, ge=0.0, le=1.0)
    cost_preference_score: float = Field(default=0.0, ge=0.0, le=1.0)
    delta_confirmation: float = Field(default=0.5, ge=0.0, le=1.0)
    execution_fragility: float = Field(default=0.0, ge=0.0, le=1.0)
    market_toxicity: float = Field(default=0.0, ge=0.0, le=1.0)
    spread_regime_penalty: float = Field(default=0.0, ge=0.0, le=1.0)
    competition_density: float = Field(default=0.5, ge=0.0, le=1.0)
    scoring_version: str = ""


class ConvictionResult(BaseModel, frozen=True):
    """Conviction output with full score decomposition."""

    pair: str
    engine_id: str
    raw_score: float
    block_scores: dict[str, float] = Field(default_factory=dict)
    conviction: ConvictionLevel
    tier_suggestion: TierSuggestion
    is_emittable: bool = False
    scoring_version: str = ""
    calibration_profile_id: str = "engine_a_conviction.to_calibrate.v1"
    calibration_status: str = TO_CALIBRATE
    physics_calibration_profile_id: str = MARKET_PHYSICS_CALIBRATION_PROFILE_ID
    physics_calibration_status: str = MARKET_PHYSICS_CALIBRATION_STATUS


ENGINE_A_CONVICTION_PROFILE_ID = "engine_a_conviction.to_calibrate.v1"
ENGINE_A_CONVICTION_CALIBRATION_STATUS = TO_CALIBRATE
ENGINE_A_CONVICTION_INPUT_DEFAULTS: dict[str, float | str | None] = {
    "flow_score": 0.0,
    "ofi_flow_score": None,
    "cost_preference_score": 0.0,
    "delta_confirmation": 0.5,
    "execution_fragility": 0.0,
    "market_toxicity": 0.0,
    "spread_regime_penalty": 0.0,
    "competition_density": 0.5,
    "scoring_version": "",
}
ENGINE_A_CONVICTION_NORMALIZATION: dict[str, float] = {
    "neutral_midpoint": 0.5,
}
ENGINE_A_CONVICTION_FEATURE_WEIGHTS: dict[str, float] = {
    "structure": 0.40,
    "context": 0.25,
    "flow": 0.15,
    "cost_preference": 0.20,
}
ENGINE_A_CONVICTION_ADJUSTMENT_WEIGHTS: dict[str, float] = {
    "delta_confirmation": 0.12,
    "competition_support": 0.08,
    **ENGINE_CONVICTION_PHYSICS_PENALTY_WEIGHTS,
}
ENGINE_A_CONVICTION_THRESHOLDS: dict[str, float] = {
    "high": 0.70,
    "medium": 0.45,
    "low": 0.25,
}

ConvictionInput.model_fields["flow_score"].default = ENGINE_A_CONVICTION_INPUT_DEFAULTS["flow_score"]
ConvictionInput.model_fields["ofi_flow_score"].default = ENGINE_A_CONVICTION_INPUT_DEFAULTS["ofi_flow_score"]
ConvictionInput.model_fields["cost_preference_score"].default = ENGINE_A_CONVICTION_INPUT_DEFAULTS["cost_preference_score"]
ConvictionInput.model_fields["delta_confirmation"].default = ENGINE_A_CONVICTION_INPUT_DEFAULTS["delta_confirmation"]
ConvictionInput.model_fields["execution_fragility"].default = ENGINE_A_CONVICTION_INPUT_DEFAULTS["execution_fragility"]
ConvictionInput.model_fields["market_toxicity"].default = ENGINE_A_CONVICTION_INPUT_DEFAULTS["market_toxicity"]
ConvictionInput.model_fields["spread_regime_penalty"].default = ENGINE_A_CONVICTION_INPUT_DEFAULTS["spread_regime_penalty"]
ConvictionInput.model_fields["competition_density"].default = ENGINE_A_CONVICTION_INPUT_DEFAULTS["competition_density"]
ConvictionInput.model_fields["scoring_version"].default = ENGINE_A_CONVICTION_INPUT_DEFAULTS["scoring_version"]


def build_conviction(inputs: ConvictionInput) -> ConvictionResult:
    """Build conviction from component scores.

    S_A^raw = S_A^structure + S_A^context + S_A^flow + S_A^cost_preference
    All components are expected in [0, 1] range; raw score in [0, 4] conceptually.
    Normalized to [0, 1] for conviction thresholds.
    """
    neutral_midpoint = ENGINE_A_CONVICTION_NORMALIZATION["neutral_midpoint"]
    effective_flow_score = (
        inputs.flow_score
        if inputs.ofi_flow_score is None
        else inputs.ofi_flow_score
    )
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
        "flow": effective_flow_score,
        "flow_legacy_score": inputs.flow_score,
        "flow_source_is_ofi": 1.0 if inputs.ofi_flow_score is not None else 0.0,
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
    if inputs.ofi_flow_score is not None:
        block_scores["ofi_flow_score"] = inputs.ofi_flow_score

    legacy_raw = (
        ENGINE_A_CONVICTION_FEATURE_WEIGHTS["structure"] * inputs.structure_score
        + ENGINE_A_CONVICTION_FEATURE_WEIGHTS["context"] * inputs.context_score
        + ENGINE_A_CONVICTION_FEATURE_WEIGHTS["flow"] * effective_flow_score
        + ENGINE_A_CONVICTION_FEATURE_WEIGHTS["cost_preference"]
        * inputs.cost_preference_score
    )
    delta_adjustment = (
        ENGINE_A_CONVICTION_ADJUSTMENT_WEIGHTS["delta_confirmation"]
        * (inputs.delta_confirmation - neutral_midpoint)
    )
    competition_adjustment = (
        ENGINE_A_CONVICTION_ADJUSTMENT_WEIGHTS["competition_support"]
        * (competition_support - neutral_midpoint)
    )
    execution_penalty = (
        ENGINE_A_CONVICTION_ADJUSTMENT_WEIGHTS["fragility_penalty"] * fragility_score
    )
    toxicity_penalty = (
        ENGINE_A_CONVICTION_ADJUSTMENT_WEIGHTS["toxicity_penalty"] * toxicity_score
    )
    spread_penalty = (
        ENGINE_A_CONVICTION_ADJUSTMENT_WEIGHTS["micro_friction_penalty"]
        * micro_friction_score
    )
    raw = clip01(
        legacy_raw
        + delta_adjustment
        + competition_adjustment
        - execution_penalty
        - toxicity_penalty
        - spread_penalty
    )

    if raw >= ENGINE_A_CONVICTION_THRESHOLDS["high"]:
        conviction = ConvictionLevel.HIGH
        tier = TierSuggestion.TIER_3
        is_emittable = True
    elif raw >= ENGINE_A_CONVICTION_THRESHOLDS["medium"]:
        conviction = ConvictionLevel.MEDIUM
        tier = TierSuggestion.TIER_2
        is_emittable = True
    elif raw >= ENGINE_A_CONVICTION_THRESHOLDS["low"]:
        conviction = ConvictionLevel.LOW
        tier = TierSuggestion.NO_TRADE
        is_emittable = False
    else:
        conviction = ConvictionLevel.NONE
        tier = TierSuggestion.NO_TRADE
        is_emittable = False

    return ConvictionResult(
        pair=inputs.pair,
        engine_id=inputs.engine_id,
        raw_score=raw,
        block_scores=block_scores,
        conviction=conviction,
        tier_suggestion=tier,
        is_emittable=is_emittable,
        scoring_version=inputs.scoring_version,
        calibration_profile_id=ENGINE_A_CONVICTION_PROFILE_ID,
        calibration_status=ENGINE_A_CONVICTION_CALIBRATION_STATUS,
        physics_calibration_profile_id=MARKET_PHYSICS_CALIBRATION_PROFILE_ID,
        physics_calibration_status=MARKET_PHYSICS_CALIBRATION_STATUS,
    )
