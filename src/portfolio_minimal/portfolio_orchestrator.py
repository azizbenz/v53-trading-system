"""
Build-8 / portfolio_orchestrator
End-to-end portfolio allocation pipeline.

Pipeline:
1. candidate_pool_builder  → filter positive score + size
2. conflict_checker         → deduplicate pairs by ranking_score
3. comparative_ranker       → rank by composite R_i
4. selection_resolver       → select eligible (fail-closed no-cluster)
5. base_size_builder        → base size from profile
6. score_size_mapper        → tier + score modulation
7. portfolio_cap_applier    → apply gross/cluster/loss/beta caps
8. phantom_trade_guard      → sterilize non-viable allocations
9. allocation_reporter      → final report (viable + phantoms separated)

IMPORTANT: Trades are only rejected definitively after cap application +
phantom check. The selector never rejects a trade for being "too big" —
allocation_router reduces it first.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from portfolio_minimal.opportunity_selector.candidate_pool_builder import (
    OpportunityCandidate,
    build_candidate_pool,
)
from portfolio_minimal.opportunity_selector.correlation_conflict_checker import (
    ConflictCheckResult,
    check_conflicts,
)
from portfolio_minimal.opportunity_selector.comparative_ranker import (
    RankedCandidate,
    rank_candidates,
)
from portfolio_minimal.opportunity_selector.selection_resolver import (
    SelectionResult,
    resolve_selection,
)
from portfolio_minimal.opportunity_selector.eligibility_filter import PortfolioSnapshot
from portfolio_minimal.allocation_router.base_size_builder import (
    SizeProfile,
    compute_base_size,
)
from portfolio_minimal.allocation_router.score_size_mapper import compute_modulated_size
from portfolio_minimal.allocation_router.portfolio_cap_applier import apply_caps
from portfolio_minimal.allocation_router.phantom_trade_guard import (
    PhantomVerdict,
    check_phantom,
)
from portfolio_minimal.allocation_router.allocation_reporter import (
    AllocationEntry,
    AllocationReport,
    build_report,
)


class OrchestratorConfig(BaseModel, frozen=True):
    """Configuration for the portfolio orchestrator."""

    size_profile: SizeProfile
    initial_snapshot: PortfolioSnapshot
    position_cap: float = 500.0
    min_viable_size: float = 10.0
    cluster_crowding_threshold: int = 3


class OrchestratorResult(BaseModel, frozen=True):
    """Full result of the portfolio orchestration pipeline."""

    # Stage outputs for audit
    pool_size: int = 0
    conflicts: ConflictCheckResult | None = None
    selection: SelectionResult | None = None
    report: AllocationReport = AllocationReport()


def run_portfolio_pipeline(
    candidates: tuple[OpportunityCandidate, ...],
    config: OrchestratorConfig,
) -> OrchestratorResult:
    """Run the full Build-8 portfolio pipeline.

    1. Pool → 2. Conflict dedup → 3. Rank → 4. Select (structural only)
    → 5-7. Size + cap per trade → 8. Phantom check → 9. Report
    """
    # ── 1. Build candidate pool ──
    pool = build_candidate_pool(candidates)
    if pool.pool_size == 0:
        return OrchestratorResult(pool_size=0)

    # ── 2. Conflict resolution (dedup by ranking_score) ──
    conflict_result = check_conflicts(
        pool.candidates,
        cluster_crowding_threshold=config.cluster_crowding_threshold,
    )

    # ── 3. Rank survivors ──
    ranked = rank_candidates(conflict_result.survivors)

    # ── 4. Selection (only structural rejection: no-cluster) ──
    selection = resolve_selection(ranked, config.initial_snapshot)

    # ── 5-8. Allocation pipeline for each selected candidate ──
    remaining_gross = config.initial_snapshot.remaining_gross_capacity
    remaining_loss = config.initial_snapshot.remaining_loss_capacity
    remaining_beta = config.initial_snapshot.remaining_beta_capacity
    remaining_cluster: dict[str, float] = dict(config.initial_snapshot.remaining_cluster_capacity)

    entries: list[AllocationEntry] = []

    for se in selection.selected:
        c = se.candidate

        # 5. Base size
        base = compute_base_size(c.pair, config.size_profile)

        # 6. Score modulation
        modulated = compute_modulated_size(
            c.pair,
            base.base_size,
            c.tier_suggestion,
            ranking_score=se.ranking_score,
        )

        # 7. Apply all caps (gross, cluster, loss, beta)
        cluster_remaining = remaining_cluster.get(c.cluster_id, 0.0)
        capped = apply_caps(
            pair=c.pair,
            modulated_size=modulated.modulated_size,
            remaining_gross_capacity=remaining_gross,
            remaining_cluster_capacity=cluster_remaining,
            position_cap=config.position_cap,
            remaining_loss_capacity=remaining_loss,
            remaining_beta_capacity=remaining_beta,
            estimated_loss_at_candidate_size=c.estimated_loss,
            beta_impact_at_candidate_size=c.beta_impact,
            candidate_size=c.candidate_size,
        )

        # 8. Phantom check — sterilize non-viable
        phantom = check_phantom(
            c.pair,
            capped.final_size,
            min_viable_size=config.min_viable_size,
        )
        is_phantom = phantom.verdict == PhantomVerdict.PHANTOM

        entry = AllocationEntry(
            pair=c.pair,
            engine_id=c.engine_id,
            base_size=base.base_size,
            modulated_size=modulated.modulated_size,
            final_size=capped.final_size,
            tier=c.tier_suggestion,
            ranking_score=se.ranking_score,
            is_phantom=is_phantom,
            cap_reason=capped.cap_reason,
        )
        entries.append(entry)

        # Decrement remaining budgets only for viable trades
        if not is_phantom:
            remaining_gross -= capped.final_size
            if c.cluster_id in remaining_cluster:
                remaining_cluster[c.cluster_id] -= capped.final_size
            # Decrement loss and beta budgets proportionally
            if c.candidate_size > 0.0:
                size_ratio = capped.final_size / c.candidate_size
                if c.estimated_loss > 0.0:
                    remaining_loss -= c.estimated_loss * size_ratio
                if abs(c.beta_impact) > 0.0:
                    remaining_beta -= abs(c.beta_impact) * size_ratio

    # ── 9. Final report ──
    report = build_report(tuple(entries))

    return OrchestratorResult(
        pool_size=pool.pool_size,
        conflicts=conflict_result,
        selection=selection,
        report=report,
    )
