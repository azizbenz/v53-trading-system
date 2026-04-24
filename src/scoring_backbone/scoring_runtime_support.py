"""Support contracts and helpers for the Build-5 scoring runtime."""

from __future__ import annotations

import math
from typing import Protocol

from pydantic import BaseModel, Field, field_validator

from data_backbone.market_physics_math import (
    execution_survivability_score_v1,
    fragility_score_v1,
    micro_friction_score_v1,
    toxicity_score_v1,
)

from .hard_block_gate.blocker_evaluator import BlockerCondition
from .hard_block_gate.blocker_decision_builder import HardBlockDecision
from .hard_block_gate.blocker_reporter import BlockerStats
from .penalty_aggregator.penalty_cap_guard import PenaltyCapResult, PenaltyCapVerdict
from .penalty_aggregator.penalty_registry import PenaltyRegistry
from .penalty_aggregator.penalty_reporter import PenaltyStats
from .penalty_aggregator.score_penalty_builder import ScorePenaltyItem, ScorePenaltyResult
from .penalty_aggregator.size_penalty_builder import SizePenaltyItem, SizePenaltyResult
from .ranking_router.candidate_pool_builder import CandidatePool
from .ranking_router.portfolio_compatibility_checker import CompatibilityResult
from .ranking_router.ranking_reporter import RankingStats
from .ranking_router.selection_resolver import SelectionEntry, SelectionResult
from .raw_score_builder.feature_selector import FeatureSelection
from .raw_score_builder.raw_score_calculator import RawScoreResult
from .raw_score_builder.score_reporter import ScorePayload, ScoreStats


class ScoringCandidateInput(BaseModel, frozen=True):
    engine_id: str
    pair: str
    raw_features: dict[str, float]
    supplementary_refs: tuple[str, ...] = ()
    allowed_features: frozenset[str]
    weights: dict[str, float]
    scoring_version: str
    raw_score_multiplier: float = Field(default=1.0, ge=0.0)
    raw_score_add: float = 0.0
    raw_score_cap: float | None = Field(default=None, ge=0.0)
    score_penalties: tuple[ScorePenaltyItem, ...] = ()
    size_penalties: tuple[SizePenaltyItem, ...] = ()
    blocker_conditions: BlockerCondition = Field(default_factory=BlockerCondition)
    expected_cost: float = 0.0
    expected_ce: float = 0.0
    projected_size: float = 0.0
    projected_loss: float = 0.0
    projected_beta_impact: float = 0.0
    cluster_id: str = ""
    corr_penalty: float = 0.0
    risk_penalty: float = 0.0
    execution_fragility: float = 0.0
    market_toxicity: float = 0.0
    spread_regime_penalty: float = 0.0
    participation_penalty: float = 0.0

    @field_validator("scoring_version")
    @classmethod
    def _validate_scoring_version(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("scoring_version must be non-empty")
        return normalized

    @field_validator("raw_score_multiplier", "raw_score_add", "raw_score_cap")
    @classmethod
    def _validate_finite_adjustments(cls, value: float | None) -> float | None:
        if value is None:
            return value
        if not math.isfinite(value):
            raise ValueError("raw score adjustments must be finite")
        return value


class ScoringSoftPenaltyLayerInput(BaseModel, frozen=True):
    """Bounded typed input for the runtime-open scoring soft-penalty hook."""

    context_id: str = Field(..., min_length=1)
    pair: str = Field(..., min_length=1)
    engine_id: str = Field(..., min_length=1)
    scoring_version: str = Field(..., min_length=1)
    feature_values: dict[str, float] = Field(default_factory=dict)
    supplementary_refs: tuple[str, ...] = ()
    expected_cost: float = 0.0
    expected_ce: float = 0.0
    corr_penalty: float = 0.0
    risk_penalty: float = 0.0
    fragility_score: float = 0.0
    toxicity_score: float = 0.0
    execution_survivability_score: float = 1.0
    micro_friction_score: float = 0.0
    pressure_state: str = "nominal"

    @field_validator("feature_values")
    @classmethod
    def _validate_hook_feature_values(cls, value: dict[str, float]) -> dict[str, float]:
        normalized: dict[str, float] = {}
        for key, item in value.items():
            normalized_key = key.strip()
            if not normalized_key:
                raise ValueError("ScoringSoftPenaltyLayerInput feature names must not be blank")
            if not math.isfinite(item):
                raise ValueError("ScoringSoftPenaltyLayerInput feature values must be finite")
            normalized[normalized_key] = float(item)
        return normalized


class ScoringSoftPenaltyLayerOutcome(BaseModel, frozen=True):
    """Deterministic outcome of the bounded scoring soft-penalty hook."""

    raw_score_multiplier_delta: float = 0.0
    raw_score_add: float = 0.0
    raw_score_cap: float | None = Field(default=None, ge=0.0)
    reason_codes: tuple[str, ...] = ()
    detail: str = ""

    @field_validator("raw_score_multiplier_delta", "raw_score_add", "raw_score_cap")
    @classmethod
    def _validate_finite_hook_adjustments(cls, value: float | None) -> float | None:
        if value is None:
            return value
        if not math.isfinite(value):
            raise ValueError("soft penalty hook adjustments must be finite")
        return value


class ScoringSoftPenaltyLayerHook(Protocol):
    """Bounded hook surface injected into the real Build-5 scoring runtime rail."""

    def __call__(
        self,
        hook_input: ScoringSoftPenaltyLayerInput,
    ) -> ScoringSoftPenaltyLayerOutcome:
        ...


class ScoringExplainability(BaseModel, frozen=True):
    """Structured Build-5 explanation emitted with each candidate audit."""

    dominant_feature_keys: tuple[str, ...] = ()
    dominant_score_penalty_ids: tuple[str, ...] = ()
    dominant_size_penalty_ids: tuple[str, ...] = ()
    artifact_hook_reason_codes: tuple[str, ...] = ()
    hard_block_codes: tuple[str, ...] = ()
    portfolio_verdict_code: str = ""
    selection_outcome_code: str = ""
    physics_pressure_state: str = "nominal"
    summary: str = "score=unexplained"


class ScoringEconomicsProjection(BaseModel, frozen=True):
    """Stable Build-5 economics/projection surface for monitoring and replay audits."""

    expected_cost: float = 0.0
    expected_ce: float = 0.0
    corr_penalty: float = 0.0
    risk_penalty: float = 0.0
    penalized_score: float = 0.0
    ranking_score: float | None = None
    final_size_multiplier: float = 1.0
    artifact_raw_score_multiplier_delta: float = 0.0
    artifact_raw_score_add: float = 0.0
    artifact_raw_score_cap: float | None = None
    phantom_trade: bool = False
    phantom_reason_code: str = ""
    hard_blocked: bool = False
    portfolio_verdict_code: str = ""
    selection_outcome_code: str = ""
    physics_pressure_state: str = "nominal"
    fragility_score: float = 0.0
    toxicity_score: float = 0.0
    execution_survivability_score: float = 1.0
    micro_friction_score: float = 0.0


class ScoringPhysicsProjection(BaseModel, frozen=True):
    fragility_score: float = 0.0
    toxicity_score: float = 0.0
    execution_survivability_score: float = 1.0
    micro_friction_score: float = 0.0
    pressure_state: str = "nominal"


class ScoringCandidateAudit(BaseModel, frozen=True):
    engine_id: str
    pair: str
    feature_selection: FeatureSelection
    raw_score_result: RawScoreResult
    score_payload: ScorePayload
    score_penalty_result: ScorePenaltyResult
    size_penalty_result: SizePenaltyResult
    penalty_cap_result: PenaltyCapResult
    hard_block_decision: HardBlockDecision
    portfolio_result: CompatibilityResult | None = None
    selection_entry: SelectionEntry | None = None
    is_phantom: bool = False
    explainability: ScoringExplainability = Field(default_factory=ScoringExplainability)
    economics: ScoringEconomicsProjection = Field(default_factory=ScoringEconomicsProjection)


class ScoringRoundResult(BaseModel, frozen=True):
    audits: tuple[ScoringCandidateAudit, ...]
    candidate_pool: CandidatePool
    selection_result: SelectionResult
    score_stats: ScoreStats
    penalty_stats: PenaltyStats
    blocker_stats: BlockerStats
    ranking_stats: RankingStats


def require_runtime_timestamp(now: float | None, *, context: str) -> float:
    """Reject implicit epoch timestamps on the open scoring rail."""

    if now is None:
        raise ValueError(f"{context} requires explicit now")
    if not math.isfinite(now):
        raise ValueError(f"{context} requires finite now")
    if now <= 0.0:
        raise ValueError(f"{context} requires now > 0")
    return now


def build_candidate_index(
    candidates: tuple[ScoringCandidateInput, ...],
) -> dict[tuple[str, str], ScoringCandidateInput]:
    """Build a stable candidate index for the scoring round."""

    index: dict[tuple[str, str], ScoringCandidateInput] = {}
    for candidate in candidates:
        key = (candidate.engine_id, candidate.pair)
        if key in index:
            raise ValueError(
                "ScoringRuntime.run_round received duplicate candidate key "
                f"{candidate.engine_id}:{candidate.pair}"
            )
        index[key] = candidate
    return index


def get_candidate(
    candidate_index: dict[tuple[str, str], ScoringCandidateInput],
    key: tuple[str, str],
    *,
    context: str,
) -> ScoringCandidateInput:
    """Resolve a governed candidate with explicit failure semantics."""

    candidate = candidate_index.get(key)
    if candidate is None:
        engine_id, pair = key
        raise ValueError(f"{context} references unknown candidate {engine_id}:{pair}")
    return candidate


def get_physics_projection(
    physics_projection_by_key: dict[tuple[str, str], ScoringPhysicsProjection],
    key: tuple[str, str],
    *,
    context: str,
) -> ScoringPhysicsProjection:
    """Resolve cached physics projections with explicit failure semantics."""

    projection = physics_projection_by_key.get(key)
    if projection is None:
        engine_id, pair = key
        raise ValueError(f"{context} is missing physics projection for {engine_id}:{pair}")
    return projection


def build_explainability(
    *,
    candidate: ScoringCandidateInput,
    raw_score_result: RawScoreResult,
    score_penalty_result: ScorePenaltyResult,
    size_penalty_result: SizePenaltyResult,
    hard_block_decision: HardBlockDecision,
    hook_outcome: ScoringSoftPenaltyLayerOutcome | None = None,
    portfolio_result: CompatibilityResult | None = None,
    selection_entry: SelectionEntry | None = None,
    physics_projection: ScoringPhysicsProjection | None = None,
) -> ScoringExplainability:
    dominant_feature_keys = tuple(
        feature
        for feature, _ in sorted(
            raw_score_result.weighted_contributions.items(),
            key=lambda item: abs(item[1]),
            reverse=True,
        )[:3]
    )
    dominant_score_penalty_ids = tuple(
        item.penalty_id
        for item in sorted(
            score_penalty_result.penalties,
            key=lambda penalty: penalty.value,
            reverse=True,
        )[:3]
    )
    dominant_size_penalty_ids = tuple(
        item.penalty_id
        for item in sorted(
            size_penalty_result.penalties,
            key=lambda penalty: penalty.multiplier,
        )[:3]
    )
    artifact_hook_reason_codes = () if hook_outcome is None else hook_outcome.reason_codes
    hard_block_codes = tuple(reason.code for reason in hard_block_decision.reasons)
    portfolio_verdict_code = portfolio_result.verdict.value if portfolio_result is not None else ""
    selection_outcome_code = selection_entry.outcome.value if selection_entry is not None else ""

    summary_parts = [
        f"features={','.join(dominant_feature_keys) if dominant_feature_keys else 'n/a'}",
        f"score_penalties={','.join(dominant_score_penalty_ids) if dominant_score_penalty_ids else 'none'}",
        f"size_penalties={','.join(dominant_size_penalty_ids) if dominant_size_penalty_ids else 'none'}",
        f"cost={candidate.expected_cost:.4f}",
        f"ce={candidate.expected_ce:.4f}",
    ]
    if hook_outcome is not None and (
        hook_outcome.raw_score_multiplier_delta != 0.0
        or hook_outcome.raw_score_add != 0.0
        or hook_outcome.raw_score_cap is not None
    ):
        summary_parts.append(
            "artifact="
            f"mult={hook_outcome.raw_score_multiplier_delta:+.4f},"
            f"add={hook_outcome.raw_score_add:+.4f},"
            f"cap={hook_outcome.raw_score_cap if hook_outcome.raw_score_cap is not None else 'none'}"
        )
    if artifact_hook_reason_codes:
        summary_parts.append(f"artifact_codes={','.join(artifact_hook_reason_codes)}")
    if hard_block_codes:
        summary_parts.append(f"hard_block={hard_block_codes[0]}")
    if portfolio_verdict_code:
        summary_parts.append(f"portfolio={portfolio_verdict_code}")
    if selection_outcome_code:
        summary_parts.append(f"selection={selection_outcome_code}")
    physics_pressure_state = "nominal" if physics_projection is None else physics_projection.pressure_state
    if physics_pressure_state != "nominal":
        summary_parts.append(f"physics={physics_pressure_state}")
    phantom_reason_code = (
        "PHANTOM_RISK"
        if score_penalty_result.total_penalty > 0.0
        and size_penalty_result.total_multiplier <= 0.1
        and not hard_block_codes
        else ""
    )
    if phantom_reason_code:
        summary_parts.append(f"phantom={phantom_reason_code}")

    return ScoringExplainability(
        dominant_feature_keys=dominant_feature_keys,
        dominant_score_penalty_ids=dominant_score_penalty_ids,
        dominant_size_penalty_ids=dominant_size_penalty_ids,
        artifact_hook_reason_codes=artifact_hook_reason_codes,
        hard_block_codes=hard_block_codes,
        portfolio_verdict_code=portfolio_verdict_code,
        selection_outcome_code=selection_outcome_code,
        physics_pressure_state=physics_pressure_state,
        summary=" / ".join(summary_parts),
    )


def build_economics_projection(
    *,
    candidate: ScoringCandidateInput,
    raw_score_result: RawScoreResult,
    penalty_cap_result: PenaltyCapResult,
    hard_block_decision: HardBlockDecision,
    hook_outcome: ScoringSoftPenaltyLayerOutcome | None = None,
    portfolio_result: CompatibilityResult | None = None,
    selection_entry: SelectionEntry | None = None,
    physics_projection: ScoringPhysicsProjection | None = None,
) -> ScoringEconomicsProjection:
    phantom_reason_code = (
        "PHANTOM_RISK"
        if penalty_cap_result.verdict == PenaltyCapVerdict.PHANTOM_RISK
        else ""
    )
    return ScoringEconomicsProjection(
        expected_cost=candidate.expected_cost,
        expected_ce=candidate.expected_ce,
        corr_penalty=candidate.corr_penalty,
        risk_penalty=candidate.risk_penalty,
        penalized_score=raw_score_result.raw_score - penalty_cap_result.capped_score_penalty,
        ranking_score=selection_entry.ranking_score if selection_entry is not None else None,
        final_size_multiplier=penalty_cap_result.capped_size_multiplier,
        artifact_raw_score_multiplier_delta=0.0 if hook_outcome is None else hook_outcome.raw_score_multiplier_delta,
        artifact_raw_score_add=0.0 if hook_outcome is None else hook_outcome.raw_score_add,
        artifact_raw_score_cap=None if hook_outcome is None else hook_outcome.raw_score_cap,
        phantom_trade=penalty_cap_result.verdict == PenaltyCapVerdict.PHANTOM_RISK,
        phantom_reason_code=phantom_reason_code,
        hard_blocked=hard_block_decision.is_blocked,
        portfolio_verdict_code=portfolio_result.verdict.value if portfolio_result is not None else "",
        selection_outcome_code=selection_entry.outcome.value if selection_entry is not None else "",
        physics_pressure_state="nominal" if physics_projection is None else physics_projection.pressure_state,
        fragility_score=0.0 if physics_projection is None else physics_projection.fragility_score,
        toxicity_score=0.0 if physics_projection is None else physics_projection.toxicity_score,
        execution_survivability_score=1.0 if physics_projection is None else physics_projection.execution_survivability_score,
        micro_friction_score=0.0 if physics_projection is None else physics_projection.micro_friction_score,
    )


def build_physics_projection(candidate: ScoringCandidateInput) -> ScoringPhysicsProjection:
    fragility = fragility_score_v1(
        candidate.execution_fragility,
        spread_regime_penalty=candidate.spread_regime_penalty,
    )
    toxicity = toxicity_score_v1(
        candidate.market_toxicity,
        fragility_score=fragility,
        spread_regime_penalty=candidate.spread_regime_penalty,
    )
    execution_survivability = execution_survivability_score_v1(
        fragility_score=fragility,
        toxicity_score=toxicity,
        spread_regime_penalty=candidate.spread_regime_penalty,
        participation_penalty=candidate.participation_penalty,
    )
    micro_friction = micro_friction_score_v1(
        spread_regime_penalty=candidate.spread_regime_penalty,
        fragility_score=fragility,
        toxicity_score=toxicity,
        participation_penalty=candidate.participation_penalty,
    )
    pressure_state = "nominal"
    if execution_survivability <= 0.20 or micro_friction >= 0.80:
        pressure_state = "severe"
    elif execution_survivability <= 0.40 or micro_friction >= 0.60 or toxicity >= 0.70:
        pressure_state = "elevated"
    return ScoringPhysicsProjection(
        fragility_score=fragility,
        toxicity_score=toxicity,
        execution_survivability_score=execution_survivability,
        micro_friction_score=micro_friction,
        pressure_state=pressure_state,
    )


def build_scoring_soft_penalty_hook_input(
    candidate: ScoringCandidateInput,
    physics_projection: ScoringPhysicsProjection,
) -> ScoringSoftPenaltyLayerInput:
    return ScoringSoftPenaltyLayerInput(
        context_id=f"{candidate.engine_id}:{candidate.pair}:{candidate.scoring_version}",
        pair=candidate.pair,
        engine_id=candidate.engine_id,
        scoring_version=candidate.scoring_version,
        feature_values=dict(candidate.raw_features),
        supplementary_refs=candidate.supplementary_refs,
        expected_cost=candidate.expected_cost,
        expected_ce=candidate.expected_ce,
        corr_penalty=candidate.corr_penalty,
        risk_penalty=candidate.risk_penalty,
        fragility_score=physics_projection.fragility_score,
        toxicity_score=physics_projection.toxicity_score,
        execution_survivability_score=physics_projection.execution_survivability_score,
        micro_friction_score=physics_projection.micro_friction_score,
        pressure_state=physics_projection.pressure_state,
    )


def apply_soft_penalty_hook(
    candidate: ScoringCandidateInput,
    hook_outcome: ScoringSoftPenaltyLayerOutcome | None,
) -> ScoringCandidateInput:
    if hook_outcome is None:
        return candidate
    if (
        hook_outcome.raw_score_multiplier_delta == 0.0
        and hook_outcome.raw_score_add == 0.0
        and hook_outcome.raw_score_cap is None
    ):
        return candidate

    merged_cap = hook_outcome.raw_score_cap
    if candidate.raw_score_cap is not None:
        merged_cap = candidate.raw_score_cap if merged_cap is None else min(candidate.raw_score_cap, merged_cap)

    return candidate.model_copy(
        update={
            "raw_score_multiplier": max(
                0.0,
                candidate.raw_score_multiplier + hook_outcome.raw_score_multiplier_delta,
            ),
            "raw_score_add": candidate.raw_score_add + hook_outcome.raw_score_add,
            "raw_score_cap": merged_cap,
        }
    )
