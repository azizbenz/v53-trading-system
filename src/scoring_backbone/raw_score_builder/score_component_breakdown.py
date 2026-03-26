"""
Build-5 / raw_score_builder / score_component_breakdown
Decompose raw score into interpretable blocks.

S_i^raw = S_i^structure + S_i^context + S_i^flow + S_i^cost_preference
"""

from __future__ import annotations

from pydantic import BaseModel, Field


# Canonical blocks — each feature maps to one block
BLOCK_STRUCTURE = "structure"
BLOCK_CONTEXT = "context"
BLOCK_FLOW = "flow"
BLOCK_COST_PREFERENCE = "cost_preference"

ALL_BLOCKS = frozenset({BLOCK_STRUCTURE, BLOCK_CONTEXT, BLOCK_FLOW, BLOCK_COST_PREFERENCE})


class ScoreBreakdown(BaseModel, frozen=True):
    """Score decomposed by interpretable blocks."""

    engine_id: str
    pair: str
    raw_score: float
    block_scores: dict[str, float] = Field(default_factory=dict)
    block_features: dict[str, tuple[str, ...]] = Field(default_factory=dict)
    unassigned_contribution: float = 0.0


def decompose_score(
    engine_id: str,
    pair: str,
    contributions: dict[str, float],
    feature_to_block: dict[str, str],
) -> ScoreBreakdown:
    """Decompose weighted contributions into interpretable blocks."""
    block_scores: dict[str, float] = {}
    block_features: dict[str, list[str]] = {}
    unassigned = 0.0

    for feature, contrib in contributions.items():
        block = feature_to_block.get(feature)
        if block is not None:
            block_scores[block] = block_scores.get(block, 0.0) + contrib
            block_features.setdefault(block, []).append(feature)
        else:
            unassigned += contrib

    raw_score = sum(contributions.values())

    return ScoreBreakdown(
        engine_id=engine_id,
        pair=pair,
        raw_score=raw_score,
        block_scores=block_scores,
        block_features={k: tuple(sorted(v)) for k, v in block_features.items()},
        unassigned_contribution=unassigned,
    )
