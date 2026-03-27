"""
Build-9 / edge_tracker_prudent_minimal / uncertainty_estimator
Estimate prudent uncertainty around edge.

sigma_hat^2 = (1/(N-1)) * sum((r_i - mu_hat)^2)
SE(mu_hat) = sigma_hat / sqrt(N)
Sharpe per trade = mu_hat / sigma_hat
"""

from __future__ import annotations

import math

from pydantic import BaseModel, Field


class UncertaintyEstimate(BaseModel, frozen=True):
    """Uncertainty estimate for edge."""

    scope: str
    mean_return: float = 0.0
    variance: float = 0.0
    std_dev: float = 0.0
    standard_error: float = 0.0
    sharpe_per_trade: float = 0.0
    sample_size: int = 0
    confidence_lower: float = 0.0  # mu - 2*SE (approx 95%)
    confidence_upper: float = 0.0  # mu + 2*SE


def estimate_uncertainty(
    scope: str,
    net_returns: tuple[float, ...],
) -> UncertaintyEstimate:
    """Estimate uncertainty from observed net returns.

    Uses sample variance (N-1 denominator) and standard error.
    """
    n = len(net_returns)
    if n < 2:
        mean = net_returns[0] if n == 1 else 0.0
        return UncertaintyEstimate(
            scope=scope,
            mean_return=mean,
            sample_size=n,
        )

    mean = sum(net_returns) / n
    var = sum((r - mean) ** 2 for r in net_returns) / (n - 1)
    std = math.sqrt(var)
    se = std / math.sqrt(n)
    sharpe = mean / std if std > 0.0 else 0.0

    return UncertaintyEstimate(
        scope=scope,
        mean_return=mean,
        variance=var,
        std_dev=std,
        standard_error=se,
        sharpe_per_trade=sharpe,
        sample_size=n,
        confidence_lower=mean - 2.0 * se,
        confidence_upper=mean + 2.0 * se,
    )
