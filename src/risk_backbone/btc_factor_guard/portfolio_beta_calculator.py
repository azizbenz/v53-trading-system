"""
Build-4 / btc_factor_guard / portfolio_beta_calculator
Calculate portfolio beta to BTC factor.

β_port = Σ w_j * β_j
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class PortfolioBeta(BaseModel, frozen=True):
    """Portfolio-level BTC beta."""

    beta_port: float  # Σ w_j * β_j
    total_exposure: float
    position_count: int
    contributions: dict[str, float] = Field(default_factory=dict)  # pair -> w_j * β_j


def calculate_portfolio_beta(
    positions: dict[str, float],  # pair -> size (x_j)
    betas: dict[str, float],  # pair -> β_j
) -> PortfolioBeta:
    """Calculate portfolio beta to BTC factor.

    β_port = Σ w_j * β_j
    where w_j = x_j / Σ x_k
    """
    total_exposure = sum(positions.values())
    if total_exposure <= 0:
        return PortfolioBeta(
            beta_port=0.0,
            total_exposure=0.0,
            position_count=0,
        )

    contributions: dict[str, float] = {}
    beta_port = 0.0

    for pair, size in positions.items():
        w_j = size / total_exposure
        beta_j = betas.get(pair, 0.8)  # default beta
        contrib = w_j * beta_j
        contributions[pair] = contrib
        beta_port += contrib

    return PortfolioBeta(
        beta_port=beta_port,
        total_exposure=total_exposure,
        position_count=len(positions),
        contributions=contributions,
    )
