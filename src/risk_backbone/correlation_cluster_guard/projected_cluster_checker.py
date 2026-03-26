"""
Build-4 / correlation_cluster_guard / projected_cluster_checker
Calculate projected cluster exposure after adding a candidate trade.

ClusterExp_c + x_new ≤ X_cluster,c_max
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ProjectedClusterExposure(BaseModel, frozen=True):
    """Projected cluster exposure after adding a candidate."""

    cluster_id: str
    current_exposure: float
    candidate_size: float
    projected_exposure: float
    cluster_cap: float
    within_cap: bool


def check_projected_cluster(
    cluster_id: str,
    current_exposure: float,
    candidate_size: float,
    cluster_cap: float,
) -> ProjectedClusterExposure:
    """Check if adding a candidate stays within cluster cap.

    ClusterExp_c + x_new ≤ X_cluster,c_max
    """
    projected = current_exposure + candidate_size
    return ProjectedClusterExposure(
        cluster_id=cluster_id,
        current_exposure=current_exposure,
        candidate_size=candidate_size,
        projected_exposure=projected,
        cluster_cap=cluster_cap,
        within_cap=projected <= cluster_cap,
    )
