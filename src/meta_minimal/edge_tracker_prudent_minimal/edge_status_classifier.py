"""
Build-9 / edge_tracker_prudent_minimal / edge_status_classifier
Classify edge status: insufficient, credible, under_surveillance, degraded.

Never conclude "engine validated" from mu_hat > 0 alone.
Minimum reading MUST include: mu_hat, N, SE(mu_hat), cost mean/p90, CE, portfolio context.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from meta_minimal.edge_tracker_prudent_minimal.uncertainty_estimator import UncertaintyEstimate
from meta_minimal.edge_tracker_prudent_minimal.sample_size_tracker import (
    SampleAdequacy,
    SampleSizeResult,
)


class EdgeStatus(StrEnum):
    INSUFFICIENT = "insufficient"  # too few data points
    CREDIBLE = "credible"  # positive edge + stable costs + reasonable sample
    UNDER_SURVEILLANCE = "under_surveillance"  # positive but fragile/noisy
    DEGRADED = "degraded"  # negative edge or destructive costs


class PortfolioContext(BaseModel, frozen=True):
    """Minimal portfolio context for edge classification."""

    cluster_utilization: float = 0.0  # [0,1] how full the cluster is
    is_crowded: bool = False  # True if cluster is over-represented


class EdgeClassification(BaseModel, frozen=True):
    """Edge status classification result.

    Includes full minimum reading: mu, N, SE, cost_p90, CE, portfolio context.
    """

    scope: str
    status: EdgeStatus
    mean_net_return: float = 0.0
    standard_error: float = 0.0
    sample_size: int = 0
    sharpe_per_trade: float = 0.0
    mean_cost_p90: float = 0.0
    ce_observed: float = 0.0
    cluster_utilization: float = 0.0
    reason: str = ""


# Thresholds
_MIN_SHARPE_CREDIBLE = 0.10
_MIN_CE_VIABLE = 0.0001  # CE below this → under surveillance
_COST_P90_DESTRUCTIVE_RATIO = 1.5  # cost_p90 > 1.5 × mean_net → destructive


def classify_edge(
    uncertainty: UncertaintyEstimate,
    sample: SampleSizeResult,
    mean_cost_p90: float = 0.0,
    ce_observed: float = 0.0,
    portfolio_context: PortfolioContext | None = None,
) -> EdgeClassification:
    """Classify edge status with prudence.

    Full minimum reading enforced:
    - mu_hat, N, SE(mu_hat) → from uncertainty
    - cost mean / p90 → mean_cost_p90
    - CE → ce_observed
    - portfolio context → cluster utilization / crowding

    Rules (evaluated in order):
    1. INSUFFICIENT if sample inadequate
    2. DEGRADED if mean_return <= 0
    3. DEGRADED if cost_p90 is destructive (cost_p90 > 1.5 × mean_net_return and cost_p90 > 0)
    4. UNDER_SURVEILLANCE if CI includes zero
    5. UNDER_SURVEILLANCE if CE too weak (< CE_min)
    6. UNDER_SURVEILLANCE if portfolio context is crowded
    7. UNDER_SURVEILLANCE if marginal sample or low Sharpe
    8. CREDIBLE otherwise
    """
    scope = uncertainty.scope
    ctx = portfolio_context or PortfolioContext()

    def _result(status: EdgeStatus, reason: str) -> EdgeClassification:
        return EdgeClassification(
            scope=scope,
            status=status,
            mean_net_return=uncertainty.mean_return,
            standard_error=uncertainty.standard_error,
            sample_size=uncertainty.sample_size,
            sharpe_per_trade=uncertainty.sharpe_per_trade,
            mean_cost_p90=mean_cost_p90,
            ce_observed=ce_observed,
            cluster_utilization=ctx.cluster_utilization,
            reason=reason,
        )

    # 1. Insufficient sample
    if sample.adequacy == SampleAdequacy.INSUFFICIENT:
        return _result(
            EdgeStatus.INSUFFICIENT,
            f"insufficient sample: N={uncertainty.sample_size} < {sample.min_required}",
        )

    # 2. Degraded: negative edge
    if uncertainty.mean_return <= 0.0:
        return _result(
            EdgeStatus.DEGRADED,
            f"negative net edge: mu={uncertainty.mean_return:.6f}",
        )

    # 3. Degraded: cost p90 destructive
    if (
        mean_cost_p90 > 0.0
        and uncertainty.mean_return > 0.0
        and mean_cost_p90 > _COST_P90_DESTRUCTIVE_RATIO * uncertainty.mean_return
    ):
        return _result(
            EdgeStatus.DEGRADED,
            f"cost_p90={mean_cost_p90:.6f} > {_COST_P90_DESTRUCTIVE_RATIO}x mean_net={uncertainty.mean_return:.6f} — destructive",
        )

    # 4. Under surveillance: CI includes zero
    if uncertainty.confidence_lower <= 0.0:
        return _result(
            EdgeStatus.UNDER_SURVEILLANCE,
            f"CI includes zero: [{uncertainty.confidence_lower:.6f}, {uncertainty.confidence_upper:.6f}]",
        )

    # 5. Under surveillance: CE too weak
    if 0.0 < ce_observed < _MIN_CE_VIABLE:
        return _result(
            EdgeStatus.UNDER_SURVEILLANCE,
            f"CE={ce_observed:.6f} < min viable {_MIN_CE_VIABLE}",
        )

    # 6. Under surveillance: crowded portfolio context
    if ctx.is_crowded:
        return _result(
            EdgeStatus.UNDER_SURVEILLANCE,
            f"portfolio context crowded: cluster_util={ctx.cluster_utilization:.2f}",
        )

    # 7. Under surveillance: marginal sample or low Sharpe
    if sample.adequacy == SampleAdequacy.MARGINAL or uncertainty.sharpe_per_trade < _MIN_SHARPE_CREDIBLE:
        return _result(
            EdgeStatus.UNDER_SURVEILLANCE,
            f"marginal: Sharpe={uncertainty.sharpe_per_trade:.4f}, sample={sample.adequacy}",
        )

    # 8. Credible
    return _result(EdgeStatus.CREDIBLE, "")
