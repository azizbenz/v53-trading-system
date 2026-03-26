"""
Build-4 / btc_factor_guard / projected_beta_checker
Calculate projected β_port after adding a candidate trade.

|β_port_proj| ≤ B_max
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from .portfolio_beta_calculator import calculate_portfolio_beta


class ProjectedBeta(BaseModel, frozen=True):
    """Projected portfolio beta after adding a candidate."""

    current_beta: float
    projected_beta: float
    candidate_pair: str
    candidate_beta: float
    candidate_size: float
    beta_cap: float
    within_cap: bool


def check_projected_beta(
    current_positions: dict[str, float],  # pair -> size
    betas: dict[str, float],  # pair -> β_j
    candidate_pair: str,
    candidate_size: float,
    candidate_beta: float,
    beta_cap: float,
) -> ProjectedBeta:
    """Check if adding a candidate stays within beta cap.

    |β_port_proj| ≤ B_max
    """
    current = calculate_portfolio_beta(current_positions, betas)

    projected_positions = dict(current_positions)
    projected_positions[candidate_pair] = projected_positions.get(candidate_pair, 0.0) + candidate_size
    projected_betas = dict(betas)
    projected_betas[candidate_pair] = candidate_beta
    projected = calculate_portfolio_beta(projected_positions, projected_betas)

    return ProjectedBeta(
        current_beta=current.beta_port,
        projected_beta=projected.beta_port,
        candidate_pair=candidate_pair,
        candidate_beta=candidate_beta,
        candidate_size=candidate_size,
        beta_cap=beta_cap,
        within_cap=abs(projected.beta_port) <= beta_cap,
    )
