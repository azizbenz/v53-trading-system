"""
Build-4 / correlation_cluster_guard / cluster_cap_guard
Refuse trade if cluster cap would be exceeded.

Invariant: cluster refusals are explicit.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class ClusterCapVerdict(StrEnum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    REJECTED_NO_CLUSTER = "rejected_no_cluster"


class ClusterCapResult(BaseModel, frozen=True):
    pair: str
    cluster_id: str
    current_exposure: float
    projected_exposure: float
    cluster_cap: float
    verdict: ClusterCapVerdict
    reason: str = ""


def evaluate_cluster_cap(
    pair: str,
    cluster_id: str | None,
    current_exposure: float,
    candidate_size: float,
    cluster_cap: float,
) -> ClusterCapResult:
    """Evaluate whether a trade is acceptable from cluster perspective.

    Fail-closed: if cluster_id is None (pair has no explicit cluster), reject.
    """
    if cluster_id is None:
        return ClusterCapResult(
            pair=pair,
            cluster_id="",
            current_exposure=current_exposure,
            projected_exposure=current_exposure + candidate_size,
            cluster_cap=cluster_cap,
            verdict=ClusterCapVerdict.REJECTED_NO_CLUSTER,
            reason=f"{pair}: no explicit cluster mapping — fail-closed",
        )

    projected = current_exposure + candidate_size

    if projected <= cluster_cap:
        return ClusterCapResult(
            pair=pair,
            cluster_id=cluster_id,
            current_exposure=current_exposure,
            projected_exposure=projected,
            cluster_cap=cluster_cap,
            verdict=ClusterCapVerdict.ACCEPTED,
        )

    return ClusterCapResult(
        pair=pair,
        cluster_id=cluster_id,
        current_exposure=current_exposure,
        projected_exposure=projected,
        cluster_cap=cluster_cap,
        verdict=ClusterCapVerdict.REJECTED,
        reason=f"{pair}: cluster '{cluster_id}' projected {projected:.2f} > cap {cluster_cap:.2f}",
    )
