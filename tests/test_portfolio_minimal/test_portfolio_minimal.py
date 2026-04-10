"""
Build-8 tests — portfolio_minimal (opportunity_selector + allocation_router + orchestrator).

Post-audit: P0-1 (selector no longer rejects reducible trades),
P0-2 (loss + beta budgets applied), P1-1/2/3 (orchestrator, ranking dedup, phantom sterilization).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

# ── opportunity_selector imports ──
from portfolio_minimal.opportunity_selector.candidate_pool_builder import (
    CANDIDATE_POOL_FRESHNESS_DISABLED,
    CandidatePool,
    CandidatePoolFreshnessPolicy,
    CandidatePoolFreshnessMode,
    CandidatePoolRejectReason,
    OpportunityCandidate,
    build_enforced_candidate_pool_freshness,
    build_candidate_pool,
)
from portfolio_minimal.opportunity_selector.eligibility_filter import (
    EligibilityResult,
    EligibilityVerdict,
    PortfolioSnapshot,
    check_eligibility,
)
from portfolio_minimal.opportunity_selector.comparative_ranker import (
    RANKING_VERSION,
    RankedCandidate,
    compute_ranking_score,
    rank_candidates,
)
from portfolio_minimal.opportunity_selector.correlation_conflict_checker import (
    ConflictCheckResult,
    ConflictType,
    check_conflicts,
)
from portfolio_minimal.opportunity_selector.selection_resolver import (
    SelectionResult,
    SelectionVerdict,
    resolve_selection,
)

# ── allocation_router imports ──
from portfolio_minimal.allocation_router.base_size_builder import (
    BaseSizeResult,
    SizeProfile,
    compute_base_size,
)
from portfolio_minimal.allocation_router.score_size_mapper import (
    SizeModulationResult,
    compute_modulated_size,
)
from portfolio_minimal.allocation_router.portfolio_cap_applier import (
    CapApplicationResult,
    apply_caps,
)
from portfolio_minimal.allocation_router.phantom_trade_guard import (
    PhantomCheckResult,
    PhantomVerdict,
    check_phantom,
)
from portfolio_minimal.allocation_router.allocation_reporter import (
    AllocationEntry,
    AllocationReport,
    build_report,
)

# ── orchestrator import ──
from portfolio_minimal.portfolio_orchestrator import (
    OrchestratorConfig,
    OrchestratorResult,
    PortfolioRelativeRankAdjustmentOutcome,
    run_portfolio_pipeline,
)


# ═══════════════════════════════════════════════════════════════
# Helper: build a candidate quickly
# ═══════════════════════════════════════════════════════════════

def _cand(
    pair: str = "BTC/USDT",
    engine: str = "engine_a",
    direction: str = "long",
    emitted_at: float = 0.0,
    score: float = 0.8,
    ce: float = 0.05,
    cost: float = 0.01,
    ev_net: float = 4.0,
    size: float = 100.0,
    tier: str = "tier_1",
    cluster: str = "btc_cluster",
    estimated_loss: float = 0.0,
    beta_impact: float = 0.0,
) -> OpportunityCandidate:
    return OpportunityCandidate(
        pair=pair,
        engine_id=engine,
        direction=direction,
        emitted_at=emitted_at,
        penalized_score=score,
        raw_score=score,
        ce_expected=ce,
        expected_cost=cost,
        ev_net=ev_net,
        candidate_size=size,
        tier_suggestion=tier,
        cluster_id=cluster,
        estimated_loss=estimated_loss,
        beta_impact=beta_impact,
    )


# ═══════════════════════════════════════════════════════════════
# 1. candidate_pool_builder (6 tests)
# ═══════════════════════════════════════════════════════════════

class TestCandidatePoolBuilder:
    def test_valid_candidates_included(self):
        pool = build_candidate_pool(
            (_cand(),),
            freshness_policy=CANDIDATE_POOL_FRESHNESS_DISABLED,
        )
        assert pool.pool_size == 1
        assert pool.candidates[0].pair == "BTC/USDT"

    def test_zero_score_excluded(self):
        pool = build_candidate_pool(
            (_cand(score=0.0),),
            freshness_policy=CANDIDATE_POOL_FRESHNESS_DISABLED,
        )
        assert pool.pool_size == 0

    def test_negative_score_excluded(self):
        pool = build_candidate_pool(
            (_cand(score=-0.1),),
            freshness_policy=CANDIDATE_POOL_FRESHNESS_DISABLED,
        )
        assert pool.pool_size == 0

    def test_zero_size_excluded(self):
        pool = build_candidate_pool(
            (_cand(size=0.0),),
            freshness_policy=CANDIDATE_POOL_FRESHNESS_DISABLED,
        )
        assert pool.pool_size == 0

    def test_engines_present_deduped(self):
        pool = build_candidate_pool(
            (
                _cand(pair="A", engine="engine_a"),
                _cand(pair="B", engine="engine_b"),
                _cand(pair="C", engine="engine_a"),
            ),
            freshness_policy=CANDIDATE_POOL_FRESHNESS_DISABLED,
        )
        assert pool.engines_present == ("engine_a", "engine_b")

    def test_empty_pool(self):
        pool = build_candidate_pool(
            (),
            freshness_policy=CANDIDATE_POOL_FRESHNESS_DISABLED,
        )
        assert pool.pool_size == 0
        assert pool.engines_present == ()

    def test_expired_signal_rejected_with_audit(self):
        pool = build_candidate_pool(
            (_cand(pair="BTC/USDT", engine="engine_a", emitted_at=100.0),),
            freshness_policy=build_enforced_candidate_pool_freshness(
                now_ts=500.0,
                max_signal_age_s=60.0,
            ),
        )
        assert pool.pool_size == 0
        assert pool.rejected_count == 1
        assert pool.rejected_candidates[0].reason == CandidatePoolRejectReason.SIGNAL_EXPIRED

    def test_signal_not_rejected_with_explicitly_disabled_freshness(self):
        pool = build_candidate_pool(
            (_cand(pair="BTC/USDT", engine="engine_a", emitted_at=100.0),),
            freshness_policy=CANDIDATE_POOL_FRESHNESS_DISABLED,
        )
        assert pool.pool_size == 1
        assert pool.rejected_count == 0

    def test_disabled_freshness_policy_rejects_hidden_values(self):
        with pytest.raises(ValueError, match="disabled candidate-pool freshness policy"):
            CandidatePoolFreshnessPolicy(
                mode=CandidatePoolFreshnessMode.DISABLED,
                now_ts=500.0,
            )


# ═══════════════════════════════════════════════════════════════
# 2. eligibility_filter — P0-1 fix: no size-based rejection
# ═══════════════════════════════════════════════════════════════

class TestEligibilityFilter:
    def _snapshot(self, gross=1000.0, cluster_cap=500.0):
        return PortfolioSnapshot(
            remaining_gross_capacity=gross,
            remaining_cluster_capacity={"btc_cluster": cluster_cap},
        )

    def test_eligible(self):
        r = check_eligibility(_cand(size=100.0), self._snapshot())
        assert r.verdict == EligibilityVerdict.ELIGIBLE

    def test_rejected_no_cluster(self):
        r = check_eligibility(_cand(cluster=""), self._snapshot())
        assert r.verdict == EligibilityVerdict.REJECTED_NO_CLUSTER

    def test_oversized_NOT_rejected_by_selector(self):
        """P0-1: candidate bigger than gross cap is NOT rejected here."""
        r = check_eligibility(_cand(size=2000.0), self._snapshot(gross=100.0))
        assert r.verdict == EligibilityVerdict.ELIGIBLE

    def test_oversized_cluster_NOT_rejected_by_selector(self):
        """P0-1: candidate bigger than cluster cap is NOT rejected here."""
        r = check_eligibility(_cand(size=2000.0), self._snapshot(cluster_cap=100.0))
        assert r.verdict == EligibilityVerdict.ELIGIBLE

    def test_unknown_cluster_rejected_fail_closed(self):
        """Unknown cluster mapping is rejected before allocation."""
        snap = PortfolioSnapshot(
            remaining_gross_capacity=1000.0,
            remaining_cluster_capacity={},
        )
        r = check_eligibility(_cand(cluster="unknown"), snap)
        assert r.verdict == EligibilityVerdict.REJECTED_UNKNOWN_CLUSTER
        assert "unknown cluster mapping" in r.reason


# ═══════════════════════════════════════════════════════════════
# 3. comparative_ranker (5 tests)
# ═══════════════════════════════════════════════════════════════

class TestComparativeRanker:
    def test_score_formula(self):
        c = _cand(score=1.0, ce=1.0, cost=0.0)
        rs = compute_ranking_score(c, cluster_utilization=0.0)
        assert abs(rs - 0.65) < 1e-9

    def test_cost_penalizes(self):
        c = _cand(score=1.0, ce=1.0, cost=1.0)
        rs = compute_ranking_score(c, cluster_utilization=0.0)
        assert abs(rs - 0.45) < 1e-9

    def test_cluster_utilization_penalizes(self):
        c = _cand(score=1.0, ce=1.0, cost=0.0)
        rs = compute_ranking_score(c, cluster_utilization=1.0)
        assert abs(rs - 0.50) < 1e-9

    def test_rank_order(self):
        candidates = (
            _cand(pair="LOW", score=0.2, ce=0.01),
            _cand(pair="HIGH", score=0.9, ce=0.10),
            _cand(pair="MID", score=0.5, ce=0.05),
        )
        ranked = rank_candidates(candidates)
        assert ranked[0].candidate.pair == "HIGH"
        assert ranked[0].rank == 1
        assert ranked[-1].candidate.pair == "LOW"
        assert ranked[-1].rank == 3

    def test_rank_with_cluster_utils(self):
        candidates = (
            _cand(pair="A", score=0.8, cluster="c1"),
            _cand(pair="B", score=0.8, cluster="c2"),
        )
        ranked = rank_candidates(candidates, cluster_utilizations={"c1": 1.0, "c2": 0.0})
        assert ranked[0].candidate.pair == "B"

    def test_rank_is_deterministic_on_exact_tie(self):
        candidates = (
            _cand(pair="ETH/USDT", engine="engine_b", score=0.8, ce=0.1, cost=0.01),
            _cand(pair="BTC/USDT", engine="engine_a", score=0.8, ce=0.1, cost=0.01),
        )
        ranked = rank_candidates(candidates)
        assert tuple(entry.candidate.pair for entry in ranked) == ("BTC/USDT", "ETH/USDT")
        assert all(entry.ranking_version == RANKING_VERSION for entry in ranked)


# ═══════════════════════════════════════════════════════════════
# 4. correlation_conflict_checker — P1-2: ranking_score dedup
# ═══════════════════════════════════════════════════════════════

class TestConflictChecker:
    def test_no_conflicts(self):
        r = check_conflicts((_cand(pair="A"), _cand(pair="B")))
        assert r.duplicates_removed == 0
        assert len(r.survivors) == 2

    def test_duplicate_pair_keeps_best_by_ranking_score(self):
        """P1-2: dedup uses ranking_score (composite), not penalized_score alone."""
        r = check_conflicts((
            _cand(pair="BTC/USDT", engine="engine_a", score=0.9, ce=0.01),
            _cand(pair="BTC/USDT", engine="engine_b", score=0.5, ce=0.50),
        ))
        assert r.duplicates_removed == 1
        assert len(r.survivors) == 1
        assert any(c.conflict_type == ConflictType.DUPLICATE_PAIR for c in r.conflicts)

    def test_duplicate_pair_reverse_order(self):
        r = check_conflicts((
            _cand(pair="X", engine="engine_b", score=0.3),
            _cand(pair="X", engine="engine_a", score=0.7),
        ))
        assert len(r.survivors) == 1
        assert r.survivors[0].penalized_score == 0.7

    def test_cluster_crowding_flagged(self):
        candidates = tuple(
            _cand(pair=f"P{i}", cluster="crowded") for i in range(5)
        )
        r = check_conflicts(candidates, cluster_crowding_threshold=3)
        assert any(c.conflict_type == ConflictType.CLUSTER_CROWDING for c in r.conflicts)

    def test_cluster_crowding_not_flagged_below_threshold(self):
        candidates = tuple(
            _cand(pair=f"P{i}", cluster="ok") for i in range(3)
        )
        r = check_conflicts(candidates, cluster_crowding_threshold=3)
        assert not any(c.conflict_type == ConflictType.CLUSTER_CROWDING for c in r.conflicts)

    def test_empty_input(self):
        r = check_conflicts(())
        assert len(r.survivors) == 0
        assert r.duplicates_removed == 0

    def test_dedup_uses_composite_not_just_score(self):
        """Engine A: high score, low CE. Engine B: lower score, much higher CE.
        Ranking_score composite can prefer B even if A has higher penalized_score."""
        # A: 0.35*0.9 + 0.30*0.01 - 0.20*0.01 = 0.316
        # B: 0.35*0.5 + 0.30*0.50 - 0.20*0.01 = 0.323
        r = check_conflicts((
            _cand(pair="X", engine="engine_a", score=0.9, ce=0.01, cost=0.01),
            _cand(pair="X", engine="engine_b", score=0.5, ce=0.50, cost=0.01),
        ))
        assert r.survivors[0].engine_id == "engine_b"

    def test_contradictory_pair_is_neutralized_with_full_audit(self):
        r = check_conflicts((
            _cand(pair="BTC/USDT", engine="engine_a", direction="long", emitted_at=100.0, score=0.8),
            _cand(pair="BTC/USDT", engine="engine_b", direction="short", emitted_at=120.0, score=0.7),
        ))
        assert len(r.survivors) == 0
        assert any(c.conflict_type == ConflictType.CONTRADICTORY_SIGNAL for c in r.conflicts)
        assert len(r.rejection_audit) == 2
        assert {entry.engine_id for entry in r.rejection_audit} == {"engine_a", "engine_b"}

    def test_contradictory_pair_outside_window_is_not_neutralized(self):
        r = check_conflicts(
            (
                _cand(pair="BTC/USDT", engine="engine_a", direction="long", emitted_at=100.0, score=0.8),
                _cand(pair="BTC/USDT", engine="engine_b", direction="short", emitted_at=1000.0, score=0.7),
            ),
            contradiction_window_s=60.0,
        )
        assert len(r.survivors) == 1
        assert not any(c.conflict_type == ConflictType.CONTRADICTORY_SIGNAL for c in r.conflicts)


# ═══════════════════════════════════════════════════════════════
# 5. selection_resolver — P0-1: no capacity rejection
# ═══════════════════════════════════════════════════════════════

class TestSelectionResolver:
    def _ranked(self, candidates):
        return rank_candidates(candidates)

    def test_all_selected_with_cluster(self):
        ranked = self._ranked((_cand(pair="A", size=100), _cand(pair="B", size=100)))
        snap = PortfolioSnapshot(
            remaining_gross_capacity=1000.0,
            remaining_cluster_capacity={"btc_cluster": 1000.0},
        )
        r = resolve_selection(ranked, snap)
        assert len(r.selected) == 2
        assert len(r.rejected) == 0

    def test_oversized_still_selected(self):
        """P0-1: oversized candidates are NOT rejected by selector."""
        ranked = self._ranked((_cand(pair="A", size=5000),))
        snap = PortfolioSnapshot(
            remaining_gross_capacity=100.0,
            remaining_cluster_capacity={"btc_cluster": 50.0},
        )
        r = resolve_selection(ranked, snap)
        assert len(r.selected) == 1
        assert len(r.rejected) == 0

    def test_rejected_no_cluster(self):
        ranked = self._ranked((_cand(pair="X", cluster=""),))
        snap = PortfolioSnapshot(remaining_gross_capacity=1000.0)
        r = resolve_selection(ranked, snap)
        assert len(r.rejected) == 1
        assert r.rejected[0].verdict == SelectionVerdict.REJECTED_NO_CLUSTER

    def test_rejected_unknown_cluster(self):
        ranked = self._ranked((_cand(pair="X", cluster="unknown"),))
        snap = PortfolioSnapshot(
            remaining_gross_capacity=1000.0,
            remaining_cluster_capacity={},
        )
        r = resolve_selection(ranked, snap)
        assert len(r.selected) == 0
        assert len(r.rejected) == 1
        assert r.rejected[0].verdict == SelectionVerdict.REJECTED_UNKNOWN_CLUSTER
        assert "unknown cluster mapping" in r.rejected[0].reason

    def test_mixed_cluster_and_no_cluster(self):
        ranked = self._ranked((
            _cand(pair="A", cluster="c1"),
            _cand(pair="B", cluster=""),
        ))
        snap = PortfolioSnapshot(remaining_gross_capacity=1000.0, remaining_cluster_capacity={"c1": 500.0})
        r = resolve_selection(ranked, snap)
        assert len(r.selected) == 1
        assert len(r.rejected) == 1

    def test_empty_ranked(self):
        r = resolve_selection((), PortfolioSnapshot(remaining_gross_capacity=1000.0))
        assert len(r.selected) == 0

    def test_selection_exposes_versions(self):
        ranked = self._ranked((_cand(pair="A", cluster="c1"),))
        snap = PortfolioSnapshot(remaining_gross_capacity=1000.0, remaining_cluster_capacity={"c1": 500.0})
        r = resolve_selection(ranked, snap)
        assert r.selection_version == "build8_selection_v1"
        assert r.ranking_version == RANKING_VERSION


# ═══════════════════════════════════════════════════════════════
# 6. base_size_builder (5 tests)
# ═══════════════════════════════════════════════════════════════

class TestBaseSizeBuilder:
    def test_normal_base_size(self):
        profile = SizeProfile(available_capital=10000.0)
        r = compute_base_size("BTC/USDT", profile)
        assert r.base_size == 200.0
        assert not r.clamped

    def test_clamped_to_max(self):
        profile = SizeProfile(available_capital=100000.0, max_size=500.0)
        r = compute_base_size("BTC/USDT", profile)
        assert r.base_size == 500.0
        assert r.clamped

    def test_clamped_to_min(self):
        profile = SizeProfile(available_capital=100.0, min_size=10.0)
        r = compute_base_size("BTC/USDT", profile)
        assert r.base_size == 10.0
        assert r.clamped

    def test_custom_fraction(self):
        profile = SizeProfile(available_capital=10000.0, base_fraction=0.05)
        r = compute_base_size("X", profile)
        assert r.base_size == 500.0

    def test_raw_base_preserved(self):
        profile = SizeProfile(available_capital=100.0, min_size=10.0)
        r = compute_base_size("X", profile)
        assert r.raw_base_size == 2.0
        assert r.base_size == 10.0


# ═══════════════════════════════════════════════════════════════
# 7. score_size_mapper (7 tests)
# ═══════════════════════════════════════════════════════════════

class TestScoreSizeMapper:
    def test_tier_1_full_size(self):
        r = compute_modulated_size("X", 100.0, "tier_1")
        assert r.modulated_size == 100.0

    def test_tier_2_reduced(self):
        r = compute_modulated_size("X", 100.0, "tier_2")
        assert r.modulated_size == 60.0

    def test_no_trade_zero(self):
        r = compute_modulated_size("X", 100.0, "no_trade")
        assert r.modulated_size == 0.0

    def test_unknown_tier_zero(self):
        r = compute_modulated_size("X", 100.0, "tier_99")
        assert r.modulated_size == 0.0

    def test_score_boost_applied(self):
        r = compute_modulated_size("X", 100.0, "tier_1", ranking_score=0.85)
        assert r.score_boost > 0.0
        assert r.modulated_size > 100.0

    def test_no_boost_below_threshold(self):
        r = compute_modulated_size("X", 100.0, "tier_1", ranking_score=0.5)
        assert r.score_boost == 0.0
        assert r.modulated_size == 100.0

    def test_max_boost_capped(self):
        r = compute_modulated_size("X", 100.0, "tier_1", ranking_score=1.0)
        assert r.score_boost == pytest.approx(0.20, abs=1e-9)
        assert r.modulated_size == pytest.approx(120.0, abs=1e-6)


# ═══════════════════════════════════════════════════════════════
# 8. portfolio_cap_applier — P0-2: loss + beta caps
# ═══════════════════════════════════════════════════════════════

class TestPortfolioCapApplier:
    def test_no_cap_needed(self):
        r = apply_caps("X", 100.0, remaining_gross_capacity=500.0, remaining_cluster_capacity=500.0)
        assert r.final_size == 100.0
        assert not r.was_capped

    def test_gross_cap(self):
        r = apply_caps("X", 200.0, remaining_gross_capacity=50.0, remaining_cluster_capacity=500.0)
        assert r.final_size == 50.0
        assert r.was_capped

    def test_cluster_cap(self):
        r = apply_caps("X", 200.0, remaining_gross_capacity=500.0, remaining_cluster_capacity=30.0)
        assert r.final_size == 30.0
        assert r.was_capped

    def test_position_cap(self):
        r = apply_caps("X", 600.0, remaining_gross_capacity=1000.0, remaining_cluster_capacity=1000.0, position_cap=500.0)
        assert r.final_size == 500.0
        assert r.was_capped

    def test_tightest_cap_wins(self):
        r = apply_caps("X", 200.0, remaining_gross_capacity=150.0, remaining_cluster_capacity=100.0, position_cap=80.0)
        assert r.final_size == 80.0

    def test_zero_floor(self):
        r = apply_caps("X", 200.0, remaining_gross_capacity=-10.0, remaining_cluster_capacity=500.0)
        assert r.final_size == 0.0

    def test_loss_budget_reduces_size(self):
        """P0-2: loss budget cap reduces allocation proportionally."""
        # estimated_loss=10 at candidate_size=100 → loss_per_unit = 0.1
        # remaining_loss=5 → max_size = 5/0.1 = 50
        r = apply_caps(
            "X", 100.0,
            remaining_gross_capacity=500.0,
            remaining_cluster_capacity=500.0,
            remaining_loss_capacity=5.0,
            estimated_loss_at_candidate_size=10.0,
            candidate_size=100.0,
        )
        assert r.final_size == pytest.approx(50.0)
        assert r.was_capped
        assert "loss_budget" in r.cap_reason

    def test_beta_budget_reduces_size(self):
        """P0-2: beta budget cap reduces allocation proportionally."""
        # beta_impact=0.5 at candidate_size=100 → beta_per_unit = 0.005
        # remaining_beta=0.1 → max_size = 0.1/0.005 = 20
        r = apply_caps(
            "X", 100.0,
            remaining_gross_capacity=500.0,
            remaining_cluster_capacity=500.0,
            remaining_beta_capacity=0.1,
            beta_impact_at_candidate_size=0.5,
            candidate_size=100.0,
        )
        assert r.final_size == pytest.approx(20.0)
        assert r.was_capped
        assert "beta_budget" in r.cap_reason

    def test_loss_and_beta_combined_tightest_wins(self):
        """P0-2: when both loss and beta constrain, tightest wins."""
        # loss: 10/100=0.1 per unit, remaining=5 → max=50
        # beta: 0.5/100=0.005 per unit, remaining=0.1 → max=20
        # beta is tighter → 20
        r = apply_caps(
            "X", 100.0,
            remaining_gross_capacity=500.0,
            remaining_cluster_capacity=500.0,
            remaining_loss_capacity=5.0,
            remaining_beta_capacity=0.1,
            estimated_loss_at_candidate_size=10.0,
            beta_impact_at_candidate_size=0.5,
            candidate_size=100.0,
        )
        assert r.final_size == pytest.approx(20.0)

    def test_no_loss_budget_when_no_loss_estimate(self):
        """No loss reduction when estimated_loss is 0."""
        r = apply_caps(
            "X", 100.0,
            remaining_gross_capacity=500.0,
            remaining_cluster_capacity=500.0,
            remaining_loss_capacity=5.0,
            estimated_loss_at_candidate_size=0.0,
            candidate_size=100.0,
        )
        assert r.final_size == 100.0
        assert not r.was_capped

    def test_negative_beta_uses_abs(self):
        """P0-2: negative beta_impact handled via abs()."""
        r = apply_caps(
            "X", 100.0,
            remaining_gross_capacity=500.0,
            remaining_cluster_capacity=500.0,
            remaining_beta_capacity=0.1,
            beta_impact_at_candidate_size=-0.5,
            candidate_size=100.0,
        )
        assert r.final_size == pytest.approx(20.0)
        assert r.was_capped


# ═══════════════════════════════════════════════════════════════
# 9. phantom_trade_guard (5 tests)
# ═══════════════════════════════════════════════════════════════

class TestPhantomTradeGuard:
    def test_viable(self):
        r = check_phantom("X", 50.0)
        assert r.verdict == PhantomVerdict.VIABLE

    def test_phantom(self):
        r = check_phantom("X", 5.0)
        assert r.verdict == PhantomVerdict.PHANTOM

    def test_exact_boundary_viable(self):
        r = check_phantom("X", 10.0)
        assert r.verdict == PhantomVerdict.VIABLE

    def test_just_below_phantom(self):
        r = check_phantom("X", 9.99)
        assert r.verdict == PhantomVerdict.PHANTOM

    def test_custom_min_viable(self):
        r = check_phantom("X", 15.0, min_viable_size=20.0)
        assert r.verdict == PhantomVerdict.PHANTOM

    def test_cost_exceeds_edge_after_allocation(self):
        r = check_phantom(
            "X",
            100.0,
            candidate_size=100.0,
            expected_cost=0.02,
            ev_net=0.01,
        )
        assert r.verdict == PhantomVerdict.COST_EXCEEDS_EDGE_AFTER_ALLOCATION
        assert "COST_EXCEEDS_EDGE_AFTER_ALLOCATION" in r.reason


# ═══════════════════════════════════════════════════════════════
# 10. allocation_reporter (4 tests)
# ═══════════════════════════════════════════════════════════════

class TestAllocationReporter:
    def _entry(self, pair="X", size=100.0, phantom=False):
        return AllocationEntry(
            pair=pair, engine_id="engine_a", base_size=100.0,
            modulated_size=size, final_size=size, tier="tier_1",
            ranking_score=0.5, is_phantom=phantom,
        )

    def test_all_viable(self):
        entries = (self._entry("A", 100), self._entry("B", 200))
        r = build_report(entries)
        assert r.count_allocated == 2
        assert r.count_phantom == 0
        assert r.total_allocated == 300.0

    def test_mix_viable_phantom(self):
        entries = (
            self._entry("A", 100),
            self._entry("B", 5, phantom=True),
        )
        r = build_report(entries)
        assert r.count_allocated == 1
        assert r.count_phantom == 1
        assert r.total_allocated == 100.0
        assert r.total_phantom == 5.0

    def test_all_phantom(self):
        entries = (self._entry("A", 3, phantom=True),)
        r = build_report(entries)
        assert r.count_allocated == 0
        assert r.count_phantom == 1

    def test_empty(self):
        r = build_report(())
        assert r.count_allocated == 0
        assert r.total_allocated == 0.0

    def test_remaining_capacities_exposed(self):
        entries = (self._entry("A", 100),)
        r = build_report(
            entries,
            capital_remaining=900.0,
            remaining_loss_capacity=40.0,
            remaining_beta_capacity=0.8,
            remaining_cluster_capacity={"btc_cluster": 400.0},
        )
        assert r.capital_remaining == 900.0
        assert r.remaining_loss_capacity == 40.0
        assert r.remaining_beta_capacity == 0.8
        assert r.remaining_cluster_capacity["btc_cluster"] == 400.0


# ═══════════════════════════════════════════════════════════════
# 11. E2E portfolio_orchestrator — P1-1
# ═══════════════════════════════════════════════════════════════

class TestPortfolioOrchestrator:
    def _config(
        self,
        capital=10000.0,
        gross=1000.0,
        cluster_cap=500.0,
        loss_cap=50.0,
        beta_cap=1.0,
    ):
        return OrchestratorConfig(
            size_profile=SizeProfile(available_capital=capital),
            initial_snapshot=PortfolioSnapshot(
                remaining_gross_capacity=gross,
                remaining_loss_capacity=loss_cap,
                remaining_beta_capacity=beta_cap,
                remaining_cluster_capacity={"btc_cluster": cluster_cap, "eth_cluster": cluster_cap},
            ),
            freshness_policy=CANDIDATE_POOL_FRESHNESS_DISABLED,
        )

    def test_orchestrator_requires_explicit_freshness_policy(self):
        with pytest.raises(ValidationError, match="freshness_policy"):
            OrchestratorConfig(
                size_profile=SizeProfile(available_capital=10_000.0),
                initial_snapshot=PortfolioSnapshot(
                    remaining_gross_capacity=1_000.0,
                    remaining_loss_capacity=50.0,
                    remaining_beta_capacity=1.0,
                    remaining_cluster_capacity={"btc_cluster": 500.0},
                ),
            )

    def test_basic_e2e_pipeline(self):
        """Full pipeline: 2 candidates → both allocated."""
        candidates = (
            _cand(pair="BTC/USDT", score=0.8, size=100, cluster="btc_cluster"),
            _cand(pair="ETH/USDT", score=0.6, size=100, cluster="eth_cluster"),
        )
        r = run_portfolio_pipeline(candidates, self._config())
        assert r.pool_size == 2
        assert r.report.count_allocated == 2
        assert r.report.count_phantom == 0

    def test_portfolio_relative_rank_hook_reorders_candidates_before_selection(self):
        candidates = (
            _cand(pair="BTC/USDT", score=0.8, ce=0.05, cluster="btc_cluster"),
            _cand(pair="ETH/USDT", score=0.6, ce=0.10, cluster="eth_cluster"),
        )

        def _hook(hook_input):
            if hook_input.pair == "ETH/USDT":
                return PortfolioRelativeRankAdjustmentOutcome(
                    rank_delta=0.5,
                    reason_codes=("ARTIFACT_PORTFOLIO_RANK_BOOST",),
                    detail="artifact promoted ETH in relative rank",
                )
            return PortfolioRelativeRankAdjustmentOutcome()

        result = run_portfolio_pipeline(
            candidates,
            self._config(),
            relative_rank_hook=_hook,
        )

        assert result.selection is not None
        assert tuple(entry.pair for entry in result.selection.selected) == ("ETH/USDT", "BTC/USDT")
        assert result.selection.selected[0].rank == 1
        assert result.selection.selected[1].rank == 2
        assert result.report.allocations[0].pair == "ETH/USDT"

    def test_empty_candidates(self):
        r = run_portfolio_pipeline((), self._config())
        assert r.pool_size == 0
        assert r.report.count_allocated == 0

    def test_no_cluster_rejected_in_pipeline(self):
        """No-cluster candidate rejected at selection, never reaches allocation."""
        candidates = (_cand(pair="X", cluster=""),)
        r = run_portfolio_pipeline(candidates, self._config())
        assert r.report.count_allocated == 0
        assert r.selection is not None
        assert len(r.selection.rejected) == 1

    def test_unknown_cluster_rejected_in_pipeline(self):
        """Unknown cluster candidate is rejected at selection, never capped to zero downstream."""
        candidates = (_cand(pair="X", cluster="unknown"),)
        r = run_portfolio_pipeline(candidates, self._config())
        assert r.report.count_allocated == 0
        assert r.selection is not None
        assert len(r.selection.rejected) == 1
        assert r.selection.rejected[0].verdict == SelectionVerdict.REJECTED_UNKNOWN_CLUSTER
        assert r.report.count_phantom == 0

    def test_oversized_reduced_not_rejected(self):
        """P0-1: oversized candidate is reduced by cap, not rejected by selector."""
        candidates = (
            _cand(pair="BTC/USDT", score=0.8, size=5000, cluster="btc_cluster"),
        )
        config = self._config(capital=50000.0, gross=200.0, cluster_cap=500.0)
        r = run_portfolio_pipeline(candidates, config)
        # selector accepts it, allocation_router caps to gross=200
        assert r.selection is not None
        assert len(r.selection.selected) == 1
        assert r.report.count_allocated == 1
        assert r.report.total_allocated <= 200.0

    def test_loss_budget_reduces_allocation(self):
        """P0-2: loss budget reduces final size via cap applier."""
        # candidate: loss=10 at size=100 → loss_per_unit=0.1
        # base_size = 10000*0.02 = 200 (tier_1 → 200)
        # loss cap: remaining=5 → max_size=50
        candidates = (
            _cand(pair="BTC/USDT", score=0.8, size=100, cluster="btc_cluster",
                  estimated_loss=10.0),
        )
        config = self._config(loss_cap=5.0)
        r = run_portfolio_pipeline(candidates, config)
        assert r.report.count_allocated == 1
        assert r.report.total_allocated <= 50.0 + 1e-6

    def test_beta_budget_reduces_allocation(self):
        """P0-2: beta budget reduces final size via cap applier."""
        # candidate: beta=0.5 at size=100 → beta_per_unit=0.005
        # base_size=200, remaining_beta=0.1 → max_size=20
        candidates = (
            _cand(pair="BTC/USDT", score=0.8, size=100, cluster="btc_cluster",
                  beta_impact=0.5),
        )
        config = self._config(beta_cap=0.1)
        r = run_portfolio_pipeline(candidates, config)
        assert r.report.count_allocated == 1
        assert r.report.total_allocated <= 20.0 + 1e-6

    def test_phantom_sterilized_in_pipeline(self):
        """P1-3: trade reduced below min viable → phantom, not allocated."""
        # beta cap makes size tiny → phantom
        candidates = (
            _cand(pair="BTC/USDT", score=0.8, size=100, cluster="btc_cluster",
                  beta_impact=0.5),
        )
        config = self._config(beta_cap=0.01)
        # max_size = 0.01/0.005 = 2.0 < min_viable=10 → phantom
        r = run_portfolio_pipeline(candidates, config)
        assert r.report.count_phantom == 1
        assert r.report.count_allocated == 0

    def test_cost_exceeds_edge_after_allocation_sterilized(self):
        candidates = (
            _cand(
                pair="BTC/USDT",
                score=0.8,
                size=100.0,
                cluster="btc_cluster",
                cost=0.02,
                ev_net=0.01,
                estimated_loss=1.0,
                beta_impact=0.01,
            ),
        )
        r = run_portfolio_pipeline(candidates, self._config())
        assert r.report.count_phantom == 1
        assert r.report.count_allocated == 0
        assert "COST_EXCEEDS_EDGE_AFTER_ALLOCATION" in r.report.phantoms[0].viability_reason

    def test_duplicate_pair_deduped_in_pipeline(self):
        """Duplicate pair from two engines → only 1 survives conflict check."""
        candidates = (
            _cand(pair="BTC/USDT", engine="engine_a", score=0.9, cluster="btc_cluster"),
            _cand(pair="BTC/USDT", engine="engine_b", score=0.5, cluster="btc_cluster"),
        )
        r = run_portfolio_pipeline(candidates, self._config())
        assert r.conflicts is not None
        assert r.conflicts.duplicates_removed == 1
        assert r.report.count_allocated == 1

    def test_multiple_trades_budget_decremented(self):
        """Second trade sees reduced budgets after first allocation."""
        candidates = (
            _cand(pair="BTC/USDT", score=0.9, size=100, cluster="btc_cluster",
                  estimated_loss=5.0, beta_impact=0.2),
            _cand(pair="ETH/USDT", score=0.7, size=100, cluster="eth_cluster",
                  estimated_loss=5.0, beta_impact=0.2),
        )
        # loss_cap=8: first trade uses ~5 loss at full size, second constrained
        config = self._config(loss_cap=8.0, beta_cap=10.0)
        r = run_portfolio_pipeline(candidates, config)
        assert r.report.count_allocated >= 1

    def test_orchestrator_result_has_all_stages(self):
        """OrchestratorResult exposes all pipeline stages for audit."""
        candidates = (_cand(pair="BTC/USDT", cluster="btc_cluster"),)
        r = run_portfolio_pipeline(candidates, self._config())
        assert r.pool_size == 1
        assert r.conflicts is not None
        assert r.selection is not None
        assert r.report is not None

    def test_contradictory_a_b_signals_are_neutralized_in_pipeline(self):
        candidates = (
            _cand(pair="BTC/USDT", engine="engine_a", direction="long", emitted_at=100.0, cluster="btc_cluster"),
            _cand(pair="BTC/USDT", engine="engine_b", direction="short", emitted_at=120.0, cluster="btc_cluster"),
        )
        r = run_portfolio_pipeline(candidates, self._config())
        assert r.conflicts is not None
        assert any(c.conflict_type == ConflictType.CONTRADICTORY_SIGNAL for c in r.conflicts.conflicts)
        assert r.report.count_allocated == 0
        assert len(r.conflicts.rejection_audit) == 2

    def test_expired_signal_is_visible_and_not_allocated(self):
        candidates = (
            _cand(pair="BTC/USDT", engine="engine_a", emitted_at=100.0, cluster="btc_cluster"),
        )
        config = self._config()
        config = config.model_copy(
            update={
                "freshness_policy": build_enforced_candidate_pool_freshness(
                    now_ts=500.0,
                    max_signal_age_s=60.0,
                )
            }
        )
        r = run_portfolio_pipeline(candidates, config)
        assert r.pool_size == 0
        assert len(r.pool_rejections) == 1
        assert r.pool_rejections[0].reason == CandidatePoolRejectReason.SIGNAL_EXPIRED
        assert r.report.count_allocated == 0

    def test_report_exposes_remaining_capital_after_allocation(self):
        candidates = (
            _cand(pair="BTC/USDT", score=0.8, size=100, cluster="btc_cluster"),
        )
        r = run_portfolio_pipeline(candidates, self._config(gross=1000.0))
        assert r.report.count_allocated == 1
        assert r.report.capital_remaining < 1000.0
