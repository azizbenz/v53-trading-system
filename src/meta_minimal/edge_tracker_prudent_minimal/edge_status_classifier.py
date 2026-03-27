"""
Build-9 / edge_tracker_prudent_minimal / edge_status_classifier
Classify edge status: insufficient, credible, under_surveillance, degraded.

Never conclude "engine validated" from mu_hat > 0 alone.
Minimum reading: mu_hat, N, SE, cost mean/p90, CE, portfolio context.
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


class EdgeClassification(BaseModel, frozen=True):
    """Edge status classification result."""

    scope: str
    status: EdgeStatus
    mean_net_return: float = 0.0
    standard_error: float = 0.0
    sample_size: int = 0
    sharpe_per_trade: float = 0.0
    reason: str = ""


# Thresholds
_MIN_SHARPE_CREDIBLE = 0.10  # minimum Sharpe for "credible"


def classify_edge(
    uncertainty: UncertaintyEstimate,
    sample: SampleSizeResult,
    mean_cost_p90: float = 0.0,
) -> EdgeClassification:
    """Classify edge status with prudence.

    Rules:
    - INSUFFICIENT if sample inadequate
    - DEGRADED if mean_return <= 0 or confidence_upper <= 0
    - UNDER_SURVEILLANCE if positive but high SE or low Sharpe
    - CREDIBLE if positive, adequate sample, decent Sharpe
    """
    scope = uncertainty.scope

    # Insufficient sample
    if sample.adequacy == SampleAdequacy.INSUFFICIENT:
        return EdgeClassification(
            scope=scope,
            status=EdgeStatus.INSUFFICIENT,
            mean_net_return=uncertainty.mean_return,
            standard_error=uncertainty.standard_error,
            sample_size=uncertainty.sample_size,
            sharpe_per_trade=uncertainty.sharpe_per_trade,
            reason=f"insufficient sample: N={uncertainty.sample_size} < {sample.min_required}",
        )

    # Degraded: negative edge
    if uncertainty.mean_return <= 0.0:
        return EdgeClassification(
            scope=scope,
            status=EdgeStatus.DEGRADED,
            mean_net_return=uncertainty.mean_return,
            standard_error=uncertainty.standard_error,
            sample_size=uncertainty.sample_size,
            sharpe_per_trade=uncertainty.sharpe_per_trade,
            reason=f"negative net edge: mu={uncertainty.mean_return:.6f}",
        )

    # Degraded: confidence interval includes zero
    if uncertainty.confidence_lower <= 0.0:
        return EdgeClassification(
            scope=scope,
            status=EdgeStatus.UNDER_SURVEILLANCE,
            mean_net_return=uncertainty.mean_return,
            standard_error=uncertainty.standard_error,
            sample_size=uncertainty.sample_size,
            sharpe_per_trade=uncertainty.sharpe_per_trade,
            reason=f"CI includes zero: [{uncertainty.confidence_lower:.6f}, {uncertainty.confidence_upper:.6f}]",
        )

    # Under surveillance: marginal sample or low Sharpe
    if sample.adequacy == SampleAdequacy.MARGINAL or uncertainty.sharpe_per_trade < _MIN_SHARPE_CREDIBLE:
        return EdgeClassification(
            scope=scope,
            status=EdgeStatus.UNDER_SURVEILLANCE,
            mean_net_return=uncertainty.mean_return,
            standard_error=uncertainty.standard_error,
            sample_size=uncertainty.sample_size,
            sharpe_per_trade=uncertainty.sharpe_per_trade,
            reason=f"marginal: Sharpe={uncertainty.sharpe_per_trade:.4f}, sample={sample.adequacy}",
        )

    # Credible
    return EdgeClassification(
        scope=scope,
        status=EdgeStatus.CREDIBLE,
        mean_net_return=uncertainty.mean_return,
        standard_error=uncertainty.standard_error,
        sample_size=uncertainty.sample_size,
        sharpe_per_trade=uncertainty.sharpe_per_trade,
    )
