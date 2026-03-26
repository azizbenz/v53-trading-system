"""
Build-8 / opportunity_selector / correlation_conflict_checker
Detect obvious exposure or redundancy conflicts between candidates.

Rules:
- Same pair from two engines → keep best by ranking_score (composite), flag duplicate
- Same cluster over-represented → flag crowding
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from portfolio_minimal.opportunity_selector.candidate_pool_builder import OpportunityCandidate
from portfolio_minimal.opportunity_selector.comparative_ranker import (
    RankedCandidate,
    compute_ranking_score,
)


class ConflictType(StrEnum):
    DUPLICATE_PAIR = "duplicate_pair"
    CLUSTER_CROWDING = "cluster_crowding"


class ConflictRecord(BaseModel, frozen=True):
    """One detected conflict between candidates."""

    conflict_type: ConflictType
    pair: str
    engine_ids: tuple[str, ...] = ()
    cluster_id: str = ""
    detail: str = ""


class ConflictCheckResult(BaseModel, frozen=True):
    """Result of conflict analysis on a set of candidates."""

    survivors: tuple[OpportunityCandidate, ...] = ()
    conflicts: tuple[ConflictRecord, ...] = ()
    duplicates_removed: int = 0


# Max candidates from same cluster before crowding flag
_CLUSTER_CROWDING_THRESHOLD = 3


def check_conflicts(
    candidates: tuple[OpportunityCandidate, ...],
    cluster_crowding_threshold: int = _CLUSTER_CROWDING_THRESHOLD,
    cluster_utilizations: dict[str, float] | None = None,
) -> ConflictCheckResult:
    """Detect and resolve conflicts among candidates.

    1. Duplicate pair resolution: if the same pair appears from multiple engines,
       keep only the one with the highest ranking_score (composite economic score),
       not just penalized_score alone.
    2. Cluster crowding: flag when a cluster has more candidates than threshold.

    Returns survivors (deduplicated) and conflict records.
    """
    conflicts: list[ConflictRecord] = []
    duplicates_removed = 0
    utils = cluster_utilizations or {}

    # ── 1. Deduplicate by pair: keep best ranking_score ──
    best_by_pair: dict[str, tuple[OpportunityCandidate, float]] = {}
    dupes_by_pair: dict[str, list[tuple[OpportunityCandidate, float]]] = {}

    for c in candidates:
        corr_util = utils.get(c.cluster_id, 0.0)
        rs = compute_ranking_score(c, cluster_utilization=corr_util)

        if c.pair in best_by_pair:
            existing_c, existing_rs = best_by_pair[c.pair]
            if rs > existing_rs:
                dupes_by_pair.setdefault(c.pair, []).append((existing_c, existing_rs))
                best_by_pair[c.pair] = (c, rs)
            else:
                dupes_by_pair.setdefault(c.pair, []).append((c, rs))
        else:
            best_by_pair[c.pair] = (c, rs)

    for pair, losers in dupes_by_pair.items():
        winner_c, winner_rs = best_by_pair[pair]
        all_engines = tuple(sorted(
            {winner_c.engine_id} | {lc.engine_id for lc, _ in losers}
        ))
        conflicts.append(ConflictRecord(
            conflict_type=ConflictType.DUPLICATE_PAIR,
            pair=pair,
            engine_ids=all_engines,
            detail=(
                f"kept {winner_c.engine_id} (ranking_score={winner_rs:.4f}), "
                f"removed {len(losers)} duplicate(s)"
            ),
        ))
        duplicates_removed += len(losers)

    survivors = tuple(c for c, _ in best_by_pair.values())

    # ── 2. Cluster crowding detection ──
    cluster_counts: dict[str, list[str]] = {}
    for c in survivors:
        if c.cluster_id:
            cluster_counts.setdefault(c.cluster_id, []).append(c.pair)

    for cluster_id, pairs in cluster_counts.items():
        if len(pairs) > cluster_crowding_threshold:
            conflicts.append(ConflictRecord(
                conflict_type=ConflictType.CLUSTER_CROWDING,
                pair=",".join(sorted(pairs)),
                cluster_id=cluster_id,
                detail=f"cluster '{cluster_id}' has {len(pairs)} candidates (threshold={cluster_crowding_threshold})",
            ))

    return ConflictCheckResult(
        survivors=survivors,
        conflicts=tuple(conflicts),
        duplicates_removed=duplicates_removed,
    )
