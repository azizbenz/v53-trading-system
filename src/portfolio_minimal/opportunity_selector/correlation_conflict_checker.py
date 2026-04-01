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
    CONTRADICTORY_SIGNAL = "contradictory_signal"  # GEM-14: anti-churn A↔B


class ConflictRecord(BaseModel, frozen=True):
    """One detected conflict between candidates."""

    conflict_type: ConflictType
    pair: str
    engine_ids: tuple[str, ...] = ()
    cluster_id: str = ""
    detail: str = ""


class RejectionAuditEntry(BaseModel, frozen=True):
    """GEM-14: auditable rejection record for every dropped candidate."""

    pair: str
    engine_id: str
    ranking_score: float
    conflict_type: ConflictType
    reason: str


class ConflictCheckResult(BaseModel, frozen=True):
    """Result of conflict analysis on a set of candidates."""

    survivors: tuple[OpportunityCandidate, ...] = ()
    conflicts: tuple[ConflictRecord, ...] = ()
    duplicates_removed: int = 0
    rejection_audit: tuple[RejectionAuditEntry, ...] = ()  # GEM-14: full audit trail


# Max candidates from same cluster before crowding flag
_CLUSTER_CROWDING_THRESHOLD = 3
_CONTRADICTION_WINDOW_S = 300.0


def check_conflicts(
    candidates: tuple[OpportunityCandidate, ...],
    cluster_crowding_threshold: int = _CLUSTER_CROWDING_THRESHOLD,
    cluster_utilizations: dict[str, float] | None = None,
    contradiction_window_s: float = _CONTRADICTION_WINDOW_S,
) -> ConflictCheckResult:
    """Detect and resolve conflicts among candidates.

    1. Duplicate pair resolution: if the same pair appears from multiple engines,
       keep only the one with the highest ranking_score (composite economic score),
       not just penalized_score alone.
    2. Cluster crowding: flag when a cluster has more candidates than threshold.

    Returns survivors (deduplicated) and conflict records.
    """
    conflicts: list[ConflictRecord] = []
    rejection_audit: list[RejectionAuditEntry] = []
    duplicates_removed = 0
    utils = cluster_utilizations or {}

    # ── 1. Pair-level resolution: contradictory neutralization, then dedup ──
    by_pair: dict[str, list[tuple[OpportunityCandidate, float]]] = {}
    for c in candidates:
        corr_util = utils.get(c.cluster_id, 0.0)
        rs = compute_ranking_score(c, cluster_utilization=corr_util)
        by_pair.setdefault(c.pair, []).append((c, rs))

    survivor_records: list[tuple[OpportunityCandidate, float]] = []

    for pair, pair_candidates in by_pair.items():
        directions = {candidate.direction for candidate, _ in pair_candidates}
        timestamps = [
            candidate.emitted_at
            for candidate, _ in pair_candidates
            if candidate.emitted_at > 0.0
        ]
        in_window = True
        if len(timestamps) >= 2:
            in_window = max(timestamps) - min(timestamps) <= contradiction_window_s

        if len(directions) > 1 and in_window:
            engine_ids = tuple(sorted({candidate.engine_id for candidate, _ in pair_candidates}))
            conflicts.append(ConflictRecord(
                conflict_type=ConflictType.CONTRADICTORY_SIGNAL,
                pair=pair,
                engine_ids=engine_ids,
                detail=f"neutralized contradictory signals within {contradiction_window_s:.0f}s window",
            ))
            for candidate, rs in pair_candidates:
                rejection_audit.append(RejectionAuditEntry(
                    pair=pair,
                    engine_id=candidate.engine_id,
                    ranking_score=rs,
                    conflict_type=ConflictType.CONTRADICTORY_SIGNAL,
                    reason="neutralized contradictory signals on same pair within anti-churn window",
                ))
            continue

        best_candidate, best_score = max(pair_candidates, key=lambda item: item[1])
        losers = [(candidate, rs) for candidate, rs in pair_candidates if candidate is not best_candidate]

        if losers:
            all_engines = tuple(sorted(
                {best_candidate.engine_id} | {candidate.engine_id for candidate, _ in losers}
            ))
            conflicts.append(ConflictRecord(
                conflict_type=ConflictType.DUPLICATE_PAIR,
                pair=pair,
                engine_ids=all_engines,
                detail=(
                    f"kept {best_candidate.engine_id} (ranking_score={best_score:.4f}), "
                    f"removed {len(losers)} duplicate(s)"
                ),
            ))
            for loser_candidate, loser_score in losers:
                rejection_audit.append(RejectionAuditEntry(
                    pair=pair,
                    engine_id=loser_candidate.engine_id,
                    ranking_score=loser_score,
                    conflict_type=ConflictType.DUPLICATE_PAIR,
                    reason=(
                        f"outranked by {best_candidate.engine_id} "
                        f"(score {best_score:.4f} vs {loser_score:.4f})"
                    ),
                ))
            duplicates_removed += len(losers)

        survivor_records.append((best_candidate, best_score))

    survivors = tuple(candidate for candidate, _ in survivor_records)

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
        rejection_audit=tuple(rejection_audit),
    )
