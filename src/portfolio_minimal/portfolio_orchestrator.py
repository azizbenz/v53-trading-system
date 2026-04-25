"""
Build-8 / portfolio_orchestrator
End-to-end portfolio allocation pipeline.

Pipeline:
1. candidate_pool_builder  → filter positive score + size
2. conflict_checker         → deduplicate pairs by ranking_score
3. comparative_ranker       → rank by composite R_i
4. selection_resolver       → select eligible (fail-closed cluster mapping)
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

import math
from typing import Protocol

from pydantic import BaseModel

from portfolio_minimal.opportunity_selector.candidate_pool_builder import (
    CandidatePoolFreshnessPolicy,
    CandidatePoolRejection,
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
from portfolio_minimal.arbitration_record import (
    PortfolioArbitrationRecord,
    PortfolioArbitrationVerdict,
    build_arbitration_record,
    build_arbitration_snapshot,
)
from portfolio_minimal.allocation_router.base_size_builder import (
    SizeProfile,
    compute_base_size,
)
from portfolio_minimal.allocation_router.score_size_mapper import compute_modulated_size
from portfolio_minimal.allocation_router.portfolio_cap_applier import (
    CapApplicationResult,
    apply_caps,
)
from portfolio_minimal.allocation_router.phantom_trade_guard import (
    PhantomVerdict,
    check_phantom,
)
from portfolio_minimal.allocation_router.allocation_reporter import (
    AllocationEntry,
    AllocationReport,
    build_report,
)
from portfolio_minimal.allocation_router.vol_target_sizer import (
    VolTargetCandidateInput,
    VolTargetProfile,
    VolTargetSizeResult,
    compute_vol_target_size,
)


class OrchestratorConfig(BaseModel, frozen=True):
    """Configuration for the portfolio orchestrator."""

    size_profile: SizeProfile
    initial_snapshot: PortfolioSnapshot
    freshness_policy: CandidatePoolFreshnessPolicy
    position_cap: float = 500.0
    min_viable_size: float = 10.0
    cluster_crowding_threshold: int = 3
    vol_target_profile: VolTargetProfile | None = None


class OrchestratorResult(BaseModel, frozen=True):
    """Full result of the portfolio orchestration pipeline."""

    # Stage outputs for audit
    pool_size: int = 0
    pool_rejections: tuple[CandidatePoolRejection, ...] = ()
    conflicts: ConflictCheckResult | None = None
    selection: SelectionResult | None = None
    report: AllocationReport = AllocationReport()
    arbitration_records: tuple[PortfolioArbitrationRecord, ...] = ()


class PortfolioRelativeRankAdjustmentInput(BaseModel, frozen=True):
    """Bounded typed input for the runtime-open portfolio relative-rank hook."""

    context_id: str
    pair: str
    engine_id: str
    ranking_score: float
    rank: int
    ranking_version: str
    penalized_score: float
    expected_cost: float
    expected_ce: float
    ev_net: float
    cluster_id: str
    tier_suggestion: str


class PortfolioRelativeRankAdjustmentOutcome(BaseModel, frozen=True):
    """Deterministic outcome of the bounded portfolio relative-rank hook."""

    rank_delta: float = 0.0
    reason_codes: tuple[str, ...] = ()
    detail: str = ""


class PortfolioRelativeRankAdjustmentHook(Protocol):
    """Bounded hook surface injected into the real Build-8 portfolio pipeline rail."""

    def __call__(
        self,
        hook_input: PortfolioRelativeRankAdjustmentInput,
    ) -> PortfolioRelativeRankAdjustmentOutcome:
        ...


def _build_allocation_entry(
    *,
    candidate: OpportunityCandidate,
    ranking_score: float,
    base_size: float,
    modulated_size: float,
    capped: CapApplicationResult,
    is_phantom: bool,
    viability_reason: str,
    sizing_method: str,
    vol_target_result: VolTargetSizeResult | None,
    arbitration_record: PortfolioArbitrationRecord | None = None,
) -> AllocationEntry:
    return AllocationEntry(
        pair=candidate.pair,
        engine_id=candidate.engine_id,
        base_size=base_size,
        modulated_size=modulated_size,
        final_size=capped.final_size,
        tier=candidate.tier_suggestion,
        ranking_score=ranking_score,
        is_phantom=is_phantom,
        cap_reason=capped.cap_reason,
        viability_reason=viability_reason,
        sizing_method=sizing_method,
        vol_target_position_size=(
            None if vol_target_result is None else vol_target_result.position_size
        ),
        arbitration_record=arbitration_record,
    )


def _consume_viable_budgets(
    *,
    candidate: OpportunityCandidate,
    capped: CapApplicationResult,
    is_phantom: bool,
    remaining_gross: float,
    remaining_loss: float,
    remaining_beta: float,
    remaining_cluster: dict[str, float],
) -> tuple[float, float, float]:
    if is_phantom:
        return remaining_gross, remaining_loss, remaining_beta
    remaining_gross -= capped.final_size
    if candidate.cluster_id in remaining_cluster:
        remaining_cluster[candidate.cluster_id] -= capped.final_size
    if candidate.candidate_size > 0.0:
        size_ratio = capped.final_size / candidate.candidate_size
        if candidate.estimated_loss > 0.0:
            remaining_loss -= candidate.estimated_loss * size_ratio
        if abs(candidate.beta_impact) > 0.0:
            remaining_beta -= abs(candidate.beta_impact) * size_ratio
    return remaining_gross, remaining_loss, remaining_beta


def _resolve_base_size(
    *,
    candidate: OpportunityCandidate,
    config: OrchestratorConfig,
) -> tuple[float, str, VolTargetSizeResult | None]:
    if (
        config.vol_target_profile is not None
        and candidate.forecast_strength is not None
        and candidate.instrument_price is not None
        and candidate.instrument_pct_vol is not None
    ):
        vol_target_result = compute_vol_target_size(
            VolTargetCandidateInput(
                pair=candidate.pair,
                available_capital=config.size_profile.available_capital,
                forecast_strength=candidate.forecast_strength,
                instrument_price=candidate.instrument_price,
                instrument_pct_vol=candidate.instrument_pct_vol,
                point_value=candidate.point_value,
            ),
            config.vol_target_profile,
        )
        return (
            vol_target_result.position_size,
            "carver_vol_target",
            vol_target_result,
        )

    base = compute_base_size(candidate.pair, config.size_profile)
    return base.base_size, "fixed_fraction", None


def _compose_arbitration_reason_codes(
    *,
    promoted: bool,
    selection_reason: str = "",
    selection_verdict: str = "",
    cap_reason: str = "",
    viability_reason: str = "",
) -> tuple[str, ...]:
    reason_codes: list[str] = []
    if promoted:
        reason_codes.append("portfolio.promoted")
    else:
        reason_codes.append("portfolio_rejected")
    for value in (selection_verdict, selection_reason, cap_reason, viability_reason):
        if value:
            reason_codes.append(value)
    return tuple(reason_codes)


def _build_arbitration_records(
    *,
    selection: SelectionResult,
    entries: tuple[AllocationEntry, ...],
    config: OrchestratorConfig,
) -> tuple[PortfolioArbitrationRecord, ...]:
    entry_map = {
        (entry.pair, entry.engine_id): entry
        for entry in entries
    }

    selected_snapshots = tuple(
        build_arbitration_snapshot(
            candidate=selected.candidate,
            rank=selected.rank,
            ranking_score=selected.ranking_score,
            final_size=entry_map[(selected.pair, selected.engine_id)].final_size,
            initial_snapshot=config.initial_snapshot,
        )
        for selected in selection.selected
        if (selected.pair, selected.engine_id) in entry_map
    )

    records: list[PortfolioArbitrationRecord] = []
    for selected in selection.selected:
        entry = entry_map[(selected.pair, selected.engine_id)]
        snapshot = build_arbitration_snapshot(
            candidate=selected.candidate,
            rank=selected.rank,
            ranking_score=selected.ranking_score,
            final_size=entry.final_size,
            initial_snapshot=config.initial_snapshot,
        )
        promoted = not entry.is_phantom and entry.final_size > 0.0
        verdict = (
            PortfolioArbitrationVerdict.PROMOTED
            if promoted
            else PortfolioArbitrationVerdict.REJECTED_ALLOCATION
        )
        records.append(
            build_arbitration_record(
                snapshot=snapshot,
                peers=selected_snapshots,
                verdict=verdict,
                reason_codes=_compose_arbitration_reason_codes(
                    promoted=promoted,
                    cap_reason=entry.cap_reason,
                    viability_reason=entry.viability_reason,
                ),
            )
        )

    for rejected in selection.rejected:
        snapshot = build_arbitration_snapshot(
            candidate=rejected.candidate,
            rank=rejected.rank,
            ranking_score=rejected.ranking_score,
            final_size=0.0,
            initial_snapshot=config.initial_snapshot,
        )
        records.append(
            build_arbitration_record(
                snapshot=snapshot,
                peers=selected_snapshots,
                verdict=PortfolioArbitrationVerdict.REJECTED_SELECTION,
                reason_codes=_compose_arbitration_reason_codes(
                    promoted=False,
                    selection_reason=rejected.reason,
                    selection_verdict=rejected.verdict.value,
                ),
            )
        )

    return tuple(records)


def run_portfolio_pipeline(
    candidates: tuple[OpportunityCandidate, ...],
    config: OrchestratorConfig,
    *,
    relative_rank_hook: PortfolioRelativeRankAdjustmentHook | None = None,
) -> OrchestratorResult:
    """Run the full Build-8 portfolio pipeline.

    1. Pool → 2. Conflict dedup → 3. Rank → 4. Select (structural only)
    → 5-7. Size + cap per trade → 8. Phantom check → 9. Report
    """
    # ── 1. Build candidate pool ──
    pool = build_candidate_pool(
        candidates,
        freshness_policy=config.freshness_policy,
    )
    if pool.pool_size == 0:
        return OrchestratorResult(
            pool_size=0,
            pool_rejections=pool.rejected_candidates,
        )

    # ── 2. Conflict resolution (dedup by ranking_score) ──
    conflict_result = check_conflicts(
        pool.candidates,
        cluster_crowding_threshold=config.cluster_crowding_threshold,
    )

    # ── 3. Rank survivors ──
    ranked = rank_candidates(conflict_result.survivors)
    ranked = _apply_relative_rank_adjustments(ranked, relative_rank_hook)

    # ── 4. Selection (only structural rejections: cluster mapping fail-close) ──
    selection = resolve_selection(ranked, config.initial_snapshot)

    # ── 5-8. Allocation pipeline for each selected candidate ──
    remaining_gross = config.initial_snapshot.remaining_gross_capacity
    remaining_loss = config.initial_snapshot.remaining_loss_capacity
    remaining_beta = config.initial_snapshot.remaining_beta_capacity
    remaining_cluster: dict[str, float] = dict(config.initial_snapshot.remaining_cluster_capacity)

    entries: list[AllocationEntry] = []

    for se in selection.selected:
        c = se.candidate

        # 5. Base size (fixed-fraction or Carver-style vol-target)
        base_size, sizing_method, vol_target_result = _resolve_base_size(
            candidate=c,
            config=config,
        )

        # 6. Score modulation
        modulated = compute_modulated_size(
            c.pair,
            base_size,
            c.tier_suggestion,
            ranking_score=0.0 if vol_target_result is not None else se.ranking_score,
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
            candidate_size=c.candidate_size,
            expected_cost=c.expected_cost,
            ev_net=c.ev_net,
        )
        is_phantom = phantom.verdict != PhantomVerdict.VIABLE

        entry = _build_allocation_entry(
            candidate=c,
            ranking_score=se.ranking_score,
            base_size=base_size,
            modulated_size=modulated.modulated_size,
            capped=capped,
            is_phantom=is_phantom,
            viability_reason=phantom.reason,
            sizing_method=sizing_method,
            vol_target_result=vol_target_result,
        )
        entries.append(entry)

        remaining_gross, remaining_loss, remaining_beta = _consume_viable_budgets(
            candidate=c,
            capped=capped,
            is_phantom=is_phantom,
            remaining_gross=remaining_gross,
            remaining_loss=remaining_loss,
            remaining_beta=remaining_beta,
            remaining_cluster=remaining_cluster,
        )

    # ── 9. Final report ──
    arbitration_records = _build_arbitration_records(
        selection=selection,
        entries=tuple(entries),
        config=config,
    )
    record_map = {
        (record.pair, record.engine_id): record
        for record in arbitration_records
        if record.verdict != PortfolioArbitrationVerdict.REJECTED_SELECTION
    }
    entries = [
        entry.model_copy(
            update={
                "arbitration_record": record_map.get((entry.pair, entry.engine_id))
            }
        )
        for entry in entries
    ]
    report = build_report(
        tuple(entries),
        capital_remaining=remaining_gross,
        remaining_loss_capacity=remaining_loss,
        remaining_beta_capacity=remaining_beta,
        remaining_cluster_capacity=remaining_cluster,
    )

    return OrchestratorResult(
        pool_size=pool.pool_size,
        pool_rejections=pool.rejected_candidates,
        conflicts=conflict_result,
        selection=selection,
        report=report,
        arbitration_records=arbitration_records,
    )


def _apply_relative_rank_adjustments(
    ranked: tuple[RankedCandidate, ...],
    relative_rank_hook: PortfolioRelativeRankAdjustmentHook | None,
) -> tuple[RankedCandidate, ...]:
    if relative_rank_hook is None or not ranked:
        return ranked

    adjusted: list[RankedCandidate] = []
    for entry in ranked:
        outcome = relative_rank_hook(
            PortfolioRelativeRankAdjustmentInput(
                context_id=(
                    f"{entry.candidate.engine_id}:{entry.candidate.pair}:"
                    f"{entry.ranking_version}:{entry.rank}"
                ),
                pair=entry.candidate.pair,
                engine_id=entry.candidate.engine_id,
                ranking_score=entry.ranking_score,
                rank=entry.rank,
                ranking_version=entry.ranking_version,
                penalized_score=entry.candidate.penalized_score,
                expected_cost=entry.candidate.expected_cost,
                expected_ce=entry.candidate.ce_expected,
                ev_net=entry.candidate.ev_net,
                cluster_id=entry.candidate.cluster_id,
                tier_suggestion=entry.candidate.tier_suggestion,
            )
        )
        if not math.isfinite(outcome.rank_delta):
            raise ValueError("portfolio relative-rank hook requires finite rank_delta")
        adjusted.append(
            entry.model_copy(
                update={
                    "ranking_score": entry.ranking_score + outcome.rank_delta,
                }
            )
        )

    adjusted.sort(
        key=lambda rc: (
            -rc.ranking_score,
            rc.candidate.pair,
            rc.candidate.engine_id,
            rc.candidate.direction,
            rc.candidate.emitted_at,
        )
    )
    return tuple(
        candidate.model_copy(update={"rank": index + 1})
        for index, candidate in enumerate(adjusted)
    )
