"""
Build-4 / loss_budgeter / projected_loss_checker
Calculate projected loss budget after adding a candidate trade.

LossBudget + L_new ≤ LB_max
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ProjectedLoss(BaseModel, frozen=True):
    """Projected loss budget after adding a candidate."""

    current_loss_budget: float
    candidate_loss: float  # L_new
    projected_loss_budget: float
    loss_cap: float
    within_cap: bool
    remaining_capacity: float


def check_projected_loss(
    current_loss_budget: float,
    candidate_loss: float,
    loss_cap: float,
) -> ProjectedLoss:
    """Check if adding a candidate loss stays within cap.

    LossBudget + L_new ≤ LB_max
    """
    projected = current_loss_budget + candidate_loss
    return ProjectedLoss(
        current_loss_budget=current_loss_budget,
        candidate_loss=candidate_loss,
        projected_loss_budget=projected,
        loss_cap=loss_cap,
        within_cap=projected <= loss_cap,
        remaining_capacity=loss_cap - projected,
    )
