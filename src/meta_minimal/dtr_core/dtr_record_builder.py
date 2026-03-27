"""
Build-9 / dtr_core / dtr_record_builder
Build a complete Decision Trace Record for every significant opportunity.

DTR_i = (time, pair, engine, regime, S_raw, Pen, S, HB, Rank, x, c_exp, c_real, state)
"""

from __future__ import annotations

import time as _time

from pydantic import BaseModel, Field

from meta_minimal.dtr_core.decision_state_encoder import DecisionState


class DTRRecord(BaseModel, frozen=True):
    """Complete Decision Trace Record."""

    # Identity
    dtr_id: str  # unique identifier
    timestamp: float
    pair: str
    engine_id: str
    regime: str = ""
    schema_version: str = "1.0"

    # Scores
    raw_score: float = 0.0
    penalized_score: float = 0.0
    final_score: float = 0.0

    # Decision chain
    hard_blocked: bool = False
    hard_block_reasons: tuple[str, ...] = ()
    ranking_position: int = 0  # 0 = not ranked

    # Allocation
    candidate_size: float = 0.0
    final_size: float = 0.0
    tier: str = ""

    # Costs
    expected_cost: float = 0.0
    realized_cost: float = 0.0

    # CE
    ce_expected: float = 0.0

    # State
    decision_state: DecisionState = DecisionState.NOT_EVALUATED

    # Cause
    primary_reason: str = ""
    cause_chain: tuple[str, ...] = ()


def build_dtr(
    dtr_id: str,
    pair: str,
    engine_id: str,
    decision_state: DecisionState,
    raw_score: float = 0.0,
    penalized_score: float = 0.0,
    final_score: float = 0.0,
    hard_blocked: bool = False,
    hard_block_reasons: tuple[str, ...] = (),
    ranking_position: int = 0,
    candidate_size: float = 0.0,
    final_size: float = 0.0,
    tier: str = "",
    expected_cost: float = 0.0,
    realized_cost: float = 0.0,
    ce_expected: float = 0.0,
    regime: str = "",
    primary_reason: str = "",
    cause_chain: tuple[str, ...] = (),
    timestamp: float | None = None,
) -> DTRRecord:
    """Build a complete DTR for a significant opportunity."""
    return DTRRecord(
        dtr_id=dtr_id,
        timestamp=timestamp if timestamp is not None else _time.time(),
        pair=pair,
        engine_id=engine_id,
        regime=regime,
        raw_score=raw_score,
        penalized_score=penalized_score,
        final_score=final_score,
        hard_blocked=hard_blocked,
        hard_block_reasons=hard_block_reasons,
        ranking_position=ranking_position,
        candidate_size=candidate_size,
        final_size=final_size,
        tier=tier,
        expected_cost=expected_cost,
        realized_cost=realized_cost,
        ce_expected=ce_expected,
        decision_state=decision_state,
        primary_reason=primary_reason,
        cause_chain=cause_chain,
    )
