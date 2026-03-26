"""
Build-4 / correlation_cluster_guard / cluster_registry
Define official correlation clusters and their members.

Invariant: every active pair belongs to an explicit cluster.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class CorrelationCluster(BaseModel, frozen=True):
    """An official correlation cluster."""

    cluster_id: str
    name: str
    members: frozenset[str]  # pairs in this cluster
    description: str = ""


# Default clusters for crypto (audited, simple, documented)
DEFAULT_CLUSTERS: tuple[CorrelationCluster, ...] = (
    CorrelationCluster(
        cluster_id="btc_majors",
        name="BTC Majors",
        members=frozenset({"BTCUSDT"}),
        description="BTC and direct BTC derivatives",
    ),
    CorrelationCluster(
        cluster_id="eth_ecosystem",
        name="ETH Ecosystem",
        members=frozenset({"ETHUSDT", "LINKUSDT"}),
        description="ETH and closely correlated ETH ecosystem tokens",
    ),
    CorrelationCluster(
        cluster_id="alt_l1",
        name="Alt L1s",
        members=frozenset({"SOLUSDT", "BNBUSDT"}),
        description="Alternative Layer 1 chains",
    ),
    CorrelationCluster(
        cluster_id="payments",
        name="Payment Tokens",
        members=frozenset({"XRPUSDT"}),
        description="Payment-focused tokens",
    ),
)


class ClusterRegistry:
    """Registry of correlation clusters."""

    def __init__(self, clusters: tuple[CorrelationCluster, ...] = DEFAULT_CLUSTERS) -> None:
        self._clusters: dict[str, CorrelationCluster] = {c.cluster_id: c for c in clusters}
        self._pair_to_clusters: dict[str, list[str]] = {}
        for c in clusters:
            for pair in c.members:
                self._pair_to_clusters.setdefault(pair, []).append(c.cluster_id)

    def get_cluster(self, cluster_id: str) -> CorrelationCluster | None:
        return self._clusters.get(cluster_id)

    def get_clusters_for_pair(self, pair: str) -> tuple[str, ...]:
        """Get cluster IDs that contain this pair."""
        return tuple(self._pair_to_clusters.get(pair, []))

    def get_all_clusters(self) -> tuple[CorrelationCluster, ...]:
        return tuple(self._clusters.values())

    def pair_has_cluster(self, pair: str) -> bool:
        return pair in self._pair_to_clusters

    @property
    def cluster_count(self) -> int:
        return len(self._clusters)
