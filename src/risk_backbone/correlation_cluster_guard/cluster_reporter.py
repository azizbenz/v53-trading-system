"""
Build-4 / correlation_cluster_guard / cluster_reporter
Report correlation concentration, cluster dominance, refusals.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ClusterEvent(BaseModel, frozen=True):
    pair: str
    cluster_id: str
    accepted: bool
    reason: str = ""
    timestamp: float = 0.0


class ClusterStats(BaseModel, frozen=True):
    cluster_exposures: dict[str, float] = Field(default_factory=dict)
    dominant_cluster: str = ""
    total_accepted: int = 0
    total_refused: int = 0


class ClusterReporter:
    """Track and report cluster guard events."""

    def __init__(self) -> None:
        self._events: list[ClusterEvent] = []
        self._accepted: int = 0
        self._refused: int = 0
        self._cluster_sizes: dict[str, float] = {}

    def record_accepted(self, pair: str, cluster_id: str, size: float = 0.0, timestamp: float = 0.0) -> None:
        self._accepted += 1
        if cluster_id:
            self._cluster_sizes[cluster_id] = self._cluster_sizes.get(cluster_id, 0.0) + size
        self._events.append(ClusterEvent(
            pair=pair, cluster_id=cluster_id, accepted=True, timestamp=timestamp,
        ))

    def record_refused(self, pair: str, cluster_id: str, reason: str, timestamp: float = 0.0) -> None:
        self._refused += 1
        self._events.append(ClusterEvent(
            pair=pair, cluster_id=cluster_id, accepted=False, reason=reason, timestamp=timestamp,
        ))

    def get_stats(self) -> ClusterStats:
        dominant = ""
        dominant_exp = 0.0
        for cid, exp in self._cluster_sizes.items():
            if exp > dominant_exp:
                dominant_exp = exp
                dominant = cid

        return ClusterStats(
            cluster_exposures=dict(self._cluster_sizes),
            dominant_cluster=dominant,
            total_accepted=self._accepted,
            total_refused=self._refused,
        )

    def get_events(self, cluster_id: str | None = None) -> tuple[ClusterEvent, ...]:
        if cluster_id is None:
            return tuple(self._events)
        return tuple(e for e in self._events if e.cluster_id == cluster_id)
