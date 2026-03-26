"""
Build-5 / hard_block_gate / blocker_evaluator
Evaluate each fatal condition independently.
"""

from __future__ import annotations

from pydantic import BaseModel

from scoring_backbone.hard_block_gate.blocker_registry import BlockerID


class BlockerCondition(BaseModel, frozen=True):
    """Input conditions for hard block evaluation."""

    is_stale_hard: bool = False
    is_pair_suspended: bool = False
    is_risk_budget_exceeded: bool = False
    is_reconciliation_critical: bool = False
    is_infra_down: bool = False


class BlockerEvaluation(BaseModel, frozen=True):
    """Evaluation result for a single blocker."""

    blocker_id: BlockerID
    triggered: bool
    reason: str = ""


def evaluate_blockers(conditions: BlockerCondition) -> tuple[BlockerEvaluation, ...]:
    """Evaluate all fatal conditions. Return all evaluations (triggered or not)."""
    evaluations: list[BlockerEvaluation] = []

    checks = (
        (BlockerID.STALE_HARD, conditions.is_stale_hard, "data hard-stale"),
        (BlockerID.PAIR_SUSPENDED, conditions.is_pair_suspended, "pair suspended"),
        (BlockerID.RISK_BUDGET_EXCEEDED, conditions.is_risk_budget_exceeded, "risk budget exhausted"),
        (BlockerID.RECONCILIATION_CRITICAL, conditions.is_reconciliation_critical, "reconciliation critical"),
        (BlockerID.INFRA_DOWN, conditions.is_infra_down, "infrastructure down"),
    )

    for blocker_id, is_triggered, reason in checks:
        evaluations.append(BlockerEvaluation(
            blocker_id=blocker_id,
            triggered=is_triggered,
            reason=reason if is_triggered else "",
        ))

    return tuple(evaluations)
