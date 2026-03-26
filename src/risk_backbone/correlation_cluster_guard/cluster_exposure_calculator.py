"""
Build-4 / correlation_cluster_guard / cluster_exposure_calculator
Calculate exposure per cluster.

ClusterExp_c = Σ x_i for i in cluster c
ClusterUtil_c = ClusterExp_c / X_cluster,c_max
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ClusterExposure(BaseModel, frozen=True):
    """Exposure for a single cluster."""

    cluster_id: str
    exposure: float  # ClusterExp_c
    position_count: int
    pairs: tuple[str, ...] = ()


class AllClusterExposures(BaseModel, frozen=True):
    """Exposure across all clusters."""

    clusters: tuple[ClusterExposure, ...] = ()
    dominant_cluster: str = ""
    dominant_exposure: float = 0.0


def calculate_cluster_exposures(
    positions: dict[str, float],  # pair -> size
    pair_to_clusters: dict[str, tuple[str, ...]],  # pair -> cluster IDs
) -> AllClusterExposures:
    """Calculate exposure per cluster.

    ClusterExp_c = Σ x_i for i in cluster c
    """
    cluster_exposure: dict[str, float] = {}
    cluster_pairs: dict[str, list[str]] = {}

    for pair, size in positions.items():
        clusters = pair_to_clusters.get(pair, ())
        for cid in clusters:
            cluster_exposure[cid] = cluster_exposure.get(cid, 0.0) + size
            cluster_pairs.setdefault(cid, []).append(pair)

    results = []
    dominant_id = ""
    dominant_exp = 0.0

    for cid, exp in cluster_exposure.items():
        results.append(ClusterExposure(
            cluster_id=cid,
            exposure=exp,
            position_count=len(cluster_pairs.get(cid, [])),
            pairs=tuple(cluster_pairs.get(cid, [])),
        ))
        if exp > dominant_exp:
            dominant_exp = exp
            dominant_id = cid

    return AllClusterExposures(
        clusters=tuple(results),
        dominant_cluster=dominant_id,
        dominant_exposure=dominant_exp,
    )
