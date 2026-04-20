"""Scoring candidate builder helpers for Engine A runtime."""

from __future__ import annotations

from typing import TYPE_CHECKING

from scoring_backbone.scoring_runtime import ScoringCandidateInput

from .conviction_builder_a import (
    ENGINE_A_CONVICTION_ADJUSTMENT_WEIGHTS,
    ENGINE_A_CONVICTION_FEATURE_WEIGHTS,
    ENGINE_A_CONVICTION_NORMALIZATION,
)
from .engine_a_runner import EngineAOutput

if TYPE_CHECKING:
    from .engine_a_runtime import EngineARuntimeInput


def _build_scoring_candidate(
    runtime_input: EngineARuntimeInput,
    engine_output: EngineAOutput,
) -> ScoringCandidateInput:
    raw_features = _build_engine_a_scoring_raw_features(engine_output)
    return ScoringCandidateInput(
        engine_id="engine_a",
        pair=engine_output.pair,
        raw_features=raw_features,
        allowed_features=frozenset(raw_features),
        weights=_build_engine_a_scoring_weights(),
        scoring_version=engine_output.scoring_version
        or runtime_input.engine_inputs.scoring_version,
        score_penalties=runtime_input.score_penalties,
        size_penalties=runtime_input.size_penalties,
        blocker_conditions=runtime_input.blocker_conditions,
        expected_cost=engine_output.expected_cost,
        expected_ce=engine_output.ce_expected,
        projected_size=runtime_input.projected_size,
        projected_loss=(
            0.0 if runtime_input.projected_loss is None else runtime_input.projected_loss
        ),
        projected_beta_impact=(
            0.0
            if runtime_input.pair_beta is None
            else runtime_input.pair_beta * runtime_input.projected_size
        ),
        cluster_id=runtime_input.cluster_id,
        corr_penalty=runtime_input.corr_penalty,
        risk_penalty=runtime_input.risk_penalty,
    )


def _build_engine_a_scoring_raw_features(
    engine_output: EngineAOutput,
) -> dict[str, float]:
    neutral_midpoint = ENGINE_A_CONVICTION_NORMALIZATION["neutral_midpoint"]
    block_scores = engine_output.block_scores
    return {
        "structure": block_scores.get("structure", 0.0),
        "context": block_scores.get("context", 0.0),
        "flow": block_scores.get("flow", 0.0),
        "cost_preference": block_scores.get("cost_preference", 0.0),
        "delta_confirmation_centered": (
            block_scores.get("delta_confirmation", neutral_midpoint)
            - neutral_midpoint
        ),
        "competition_support_centered": (
            block_scores.get("competition_support", neutral_midpoint)
            - neutral_midpoint
        ),
        "fragility_score": block_scores.get("fragility_score", 0.0),
        "toxicity_score": block_scores.get("toxicity_score", 0.0),
        "micro_friction_score": block_scores.get("micro_friction_score", 0.0),
    }


def _build_engine_a_scoring_weights() -> dict[str, float]:
    return {
        **ENGINE_A_CONVICTION_FEATURE_WEIGHTS,
        "delta_confirmation_centered": ENGINE_A_CONVICTION_ADJUSTMENT_WEIGHTS[
            "delta_confirmation"
        ],
        "competition_support_centered": ENGINE_A_CONVICTION_ADJUSTMENT_WEIGHTS[
            "competition_support"
        ],
        "fragility_score": -ENGINE_A_CONVICTION_ADJUSTMENT_WEIGHTS[
            "fragility_penalty"
        ],
        "toxicity_score": -ENGINE_A_CONVICTION_ADJUSTMENT_WEIGHTS[
            "toxicity_penalty"
        ],
        "micro_friction_score": -ENGINE_A_CONVICTION_ADJUSTMENT_WEIGHTS[
            "micro_friction_penalty"
        ],
    }
