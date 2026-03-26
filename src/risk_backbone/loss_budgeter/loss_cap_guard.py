"""
Build-4 / loss_budgeter / loss_cap_guard
Refuse trade if loss budget would be exceeded.

Invariant: no trade accepted without known loss impact. Refusal is explicit.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class LossCapVerdict(StrEnum):
    ACCEPTED = "accepted"
    REJECTED_NO_LOSS_ESTIMATE = "rejected_no_loss_estimate"
    REJECTED_BUDGET_EXCEEDED = "rejected_budget_exceeded"


class LossCapResult(BaseModel, frozen=True):
    """Result of loss cap evaluation."""

    pair: str
    candidate_loss: float
    current_budget: float
    projected_budget: float
    loss_cap: float
    verdict: LossCapVerdict
    reason: str = ""


def evaluate_loss_cap(
    pair: str,
    candidate_loss: float | None,
    current_budget: float,
    loss_cap: float,
) -> LossCapResult:
    """Evaluate whether a trade is acceptable from a loss budget perspective.

    - If candidate_loss is None → rejected (no estimate)
    - If LossBudget + L_new > LB_max → rejected
    """
    if candidate_loss is None:
        return LossCapResult(
            pair=pair,
            candidate_loss=0.0,
            current_budget=current_budget,
            projected_budget=current_budget,
            loss_cap=loss_cap,
            verdict=LossCapVerdict.REJECTED_NO_LOSS_ESTIMATE,
            reason=f"{pair}: no L_i estimate provided — trade rejected",
        )

    projected = current_budget + candidate_loss
    if projected > loss_cap:
        return LossCapResult(
            pair=pair,
            candidate_loss=candidate_loss,
            current_budget=current_budget,
            projected_budget=projected,
            loss_cap=loss_cap,
            verdict=LossCapVerdict.REJECTED_BUDGET_EXCEEDED,
            reason=f"{pair}: projected loss budget {projected:.4f} exceeds cap {loss_cap:.4f}",
        )

    return LossCapResult(
        pair=pair,
        candidate_loss=candidate_loss,
        current_budget=current_budget,
        projected_budget=projected,
        loss_cap=loss_cap,
        verdict=LossCapVerdict.ACCEPTED,
    )
