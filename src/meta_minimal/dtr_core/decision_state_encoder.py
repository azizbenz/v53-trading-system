"""
Build-9 / dtr_core / decision_state_encoder
Encode the final state of a trading decision.

States:
- NOT_EVALUATED: opportunity not yet processed
- EVALUATED: scored but no further action
- HARD_BLOCKED: rejected by hard blocker
- REJECTED_RANKING: rejected by relative ranking
- SELECTED: selected for allocation
- REDUCED: selected but size reduced by caps
- PHANTOM: reduced to economically sterile size
- EXECUTED: order sent to exchange
"""

from __future__ import annotations

from enum import StrEnum


class DecisionState(StrEnum):
    NOT_EVALUATED = "not_evaluated"
    EVALUATED = "evaluated"
    HARD_BLOCKED = "hard_blocked"
    REJECTED_RANKING = "rejected_ranking"
    SELECTED = "selected"
    REDUCED = "reduced"
    PHANTOM = "phantom"
    EXECUTED = "executed"


# Severity ordering for aggregation
_STATE_SEVERITY: dict[DecisionState, int] = {
    DecisionState.NOT_EVALUATED: 0,
    DecisionState.EVALUATED: 1,
    DecisionState.HARD_BLOCKED: 2,
    DecisionState.REJECTED_RANKING: 3,
    DecisionState.SELECTED: 4,
    DecisionState.REDUCED: 5,
    DecisionState.PHANTOM: 6,
    DecisionState.EXECUTED: 7,
}


def encode_state(
    hard_blocked: bool = False,
    ranking_rejected: bool = False,
    selected: bool = False,
    was_reduced: bool = False,
    is_phantom: bool = False,
    was_executed: bool = False,
) -> DecisionState:
    """Encode decision state from boolean flags.

    Priority: executed > phantom > reduced > selected > ranking_rejected > hard_blocked > evaluated.
    """
    if was_executed:
        return DecisionState.EXECUTED
    if is_phantom:
        return DecisionState.PHANTOM
    if was_reduced:
        return DecisionState.REDUCED
    if selected:
        return DecisionState.SELECTED
    if ranking_rejected:
        return DecisionState.REJECTED_RANKING
    if hard_blocked:
        return DecisionState.HARD_BLOCKED
    return DecisionState.EVALUATED


def state_severity(state: DecisionState) -> int:
    """Return numeric severity for state ordering."""
    return _STATE_SEVERITY.get(state, 0)
