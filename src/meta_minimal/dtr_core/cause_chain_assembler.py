"""
Build-9 / dtr_core / cause_chain_assembler
Assemble the full causal chain: score, penalties, blockers, ranking, allocation, execution.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class CauseChain(BaseModel, frozen=True):
    """Assembled causal chain for a decision."""

    steps: tuple[str, ...] = ()
    primary_reason: str = ""
    penalty_total: float = 0.0
    blocker_count: int = 0
    was_reduced: bool = False
    reduction_reason: str = ""


def assemble_cause_chain(
    score_step: str = "",
    penalty_steps: tuple[str, ...] = (),
    penalty_total: float = 0.0,
    blocker_steps: tuple[str, ...] = (),
    ranking_step: str = "",
    allocation_step: str = "",
    execution_step: str = "",
    reduction_reason: str = "",
) -> CauseChain:
    """Assemble all causal steps into a structured chain.

    Returns steps in order: score → penalties → blockers → ranking → allocation → execution.
    Primary reason = first non-empty terminal step.
    """
    steps: list[str] = []

    if score_step:
        steps.append(f"score: {score_step}")

    for ps in penalty_steps:
        steps.append(f"penalty: {ps}")

    for bs in blocker_steps:
        steps.append(f"blocker: {bs}")

    if ranking_step:
        steps.append(f"ranking: {ranking_step}")

    if allocation_step:
        steps.append(f"allocation: {allocation_step}")

    if execution_step:
        steps.append(f"execution: {execution_step}")

    # Primary reason: last significant step
    primary = ""
    if blocker_steps:
        primary = f"blocked: {blocker_steps[0]}"
    elif ranking_step:
        primary = ranking_step
    elif allocation_step:
        primary = allocation_step
    elif execution_step:
        primary = execution_step
    elif score_step:
        primary = score_step

    return CauseChain(
        steps=tuple(steps),
        primary_reason=primary,
        penalty_total=penalty_total,
        blocker_count=len(blocker_steps),
        was_reduced=bool(reduction_reason),
        reduction_reason=reduction_reason,
    )
