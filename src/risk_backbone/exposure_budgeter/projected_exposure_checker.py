"""
Build-4 / exposure_budgeter / projected_exposure_checker
Calculate projected exposure after adding a candidate trade.

GrossExp + x_new ≤ X_gross,max
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ProjectedExposure(BaseModel, frozen=True):
    """Projected exposure after adding a candidate trade."""

    current_exposure: float
    candidate_size: float
    projected_exposure: float  # current + candidate
    gross_cap: float
    within_cap: bool
    remaining_capacity: float  # cap - projected (can be negative)


def check_projected_exposure(
    current_exposure: float,
    candidate_size: float,
    gross_cap: float,
) -> ProjectedExposure:
    """Check if adding a candidate trade stays within gross cap.

    GrossExp + x_new ≤ X_gross,max
    """
    projected = current_exposure + candidate_size
    return ProjectedExposure(
        current_exposure=current_exposure,
        candidate_size=candidate_size,
        projected_exposure=projected,
        gross_cap=gross_cap,
        within_cap=projected <= gross_cap,
        remaining_capacity=gross_cap - projected,
    )
