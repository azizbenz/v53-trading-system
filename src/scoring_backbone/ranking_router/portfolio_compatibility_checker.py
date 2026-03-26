"""
Build-5 / ranking_router / portfolio_compatibility_checker
Check budget and correlation before selection.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel


class CompatibilityVerdict(StrEnum):
    COMPATIBLE = "compatible"
    REJECTED_EXPOSURE = "rejected_exposure"
    REJECTED_CLUSTER = "rejected_cluster"
    REJECTED_BETA = "rejected_beta"
    REJECTED_LOSS_BUDGET = "rejected_loss_budget"


class PortfolioState(BaseModel, frozen=True):
    """Current portfolio state for compatibility check."""

    remaining_gross_capacity: float = 0.0
    remaining_loss_capacity: float = 0.0
    remaining_beta_capacity: float = 0.0
    remaining_cluster_capacity: dict[str, float] = {}


class CompatibilityResult(BaseModel, frozen=True):
    """Result of portfolio compatibility check."""

    engine_id: str
    pair: str
    verdict: CompatibilityVerdict
    reason: str = ""


def check_portfolio_compatibility(
    engine_id: str,
    pair: str,
    projected_size: float,
    projected_loss: float,
    projected_beta_impact: float,
    cluster_id: str,
    portfolio: PortfolioState,
) -> CompatibilityResult:
    """Check if a candidate is compatible with current portfolio budgets."""
    if projected_size > portfolio.remaining_gross_capacity:
        return CompatibilityResult(
            engine_id=engine_id,
            pair=pair,
            verdict=CompatibilityVerdict.REJECTED_EXPOSURE,
            reason=f"size {projected_size:.2f} > remaining gross {portfolio.remaining_gross_capacity:.2f}",
        )

    if projected_loss > portfolio.remaining_loss_capacity:
        return CompatibilityResult(
            engine_id=engine_id,
            pair=pair,
            verdict=CompatibilityVerdict.REJECTED_LOSS_BUDGET,
            reason=f"loss {projected_loss:.2f} > remaining loss budget {portfolio.remaining_loss_capacity:.2f}",
        )

    if abs(projected_beta_impact) > portfolio.remaining_beta_capacity:
        return CompatibilityResult(
            engine_id=engine_id,
            pair=pair,
            verdict=CompatibilityVerdict.REJECTED_BETA,
            reason=f"|beta impact| {abs(projected_beta_impact):.4f} > remaining beta {portfolio.remaining_beta_capacity:.4f}",
        )

    # Fail-closed: no cluster_id means no cluster budget check possible
    if not cluster_id:
        return CompatibilityResult(
            engine_id=engine_id,
            pair=pair,
            verdict=CompatibilityVerdict.REJECTED_CLUSTER,
            reason=f"{pair}: no cluster mapping — fail-closed",
        )

    cluster_remaining = portfolio.remaining_cluster_capacity.get(cluster_id, 0.0)
    if projected_size > cluster_remaining:
        return CompatibilityResult(
            engine_id=engine_id,
            pair=pair,
            verdict=CompatibilityVerdict.REJECTED_CLUSTER,
            reason=f"size {projected_size:.2f} > cluster '{cluster_id}' remaining {cluster_remaining:.2f}",
        )

    return CompatibilityResult(
        engine_id=engine_id,
        pair=pair,
        verdict=CompatibilityVerdict.COMPATIBLE,
    )
