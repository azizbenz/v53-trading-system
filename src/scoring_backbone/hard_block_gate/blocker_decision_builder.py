"""
Build-5 / hard_block_gate / blocker_decision_builder
Produce final binary verdict: blocked / not blocked.

HB_i = 1(⋃_{b=1}^{B} condition_{b,i})
A_i^HB = 1_{HB_i=0}
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from scoring_backbone.hard_block_gate.blocker_reason_encoder import EncodedBlockReason


class HardBlockDecision(BaseModel, frozen=True):
    """Final hard block verdict."""

    pair: str
    engine_id: str
    is_blocked: bool
    reasons: tuple[EncodedBlockReason, ...] = ()
    reason_count: int = 0
    may_proceed_to_ranking: bool = True


def build_decision(
    pair: str,
    engine_id: str,
    encoded_reasons: tuple[EncodedBlockReason, ...],
) -> HardBlockDecision:
    """Build final hard block decision.

    Blocked if any reason exists. Not blocked → may proceed to ranking.
    """
    is_blocked = len(encoded_reasons) > 0

    return HardBlockDecision(
        pair=pair,
        engine_id=engine_id,
        is_blocked=is_blocked,
        reasons=encoded_reasons,
        reason_count=len(encoded_reasons),
        may_proceed_to_ranking=not is_blocked,
    )
