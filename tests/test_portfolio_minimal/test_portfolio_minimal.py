"""
Build-8 tests — portfolio_minimal (opportunity_selector + allocation_router).
"""

from __future__ import annotations

import pytest

# ── opportunity_selector imports ──
from portfolio_minimal.opportunity_selector.candidate_pool_builder import (
    CandidatePool,
    OpportunityCandidate,
    build_candidate_pool,
)
from portfolio_minimal.opportunity_selector.eligibility_filter import (
    EligibilityResult,
    EligibilityVerdict,
    PortfolioSnapshot,
    check_eligibility,
)
from portfolio_minimal.opportunity_selector.comparative_ranker import (
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


# ═══════════════════════════════════════════════════════════════
# Helper: build a candidate quickly
# ═══════════════════════════════════════════════════════════════

def _cand(
    pair: str = "BTC/USDT",
    engine: str = "engine_a",
    score: float = 0.8,
    ce: float = 0.05,
    cost: float = 0.01,
    size: float = 100.0,
    tier: str = "tier_1",
    cluster: str = "btc_cluster",
) -> OpportunityCandidate:
    return OpportunityCandidate(
        pair=pair,
        engine_id=engine,
        penalized_score=score,
        raw_score=score,
        ce_expected=ce,
        expected_cost=cost,
        candidate_size=size,
        tier_suggestion=tier,
        cluster_id=cluster,
    )


# ═══════════════════════════════════════════════════════════════
# 1. candidate_pool_builder
# ═══════════════════════════════════════════════════════════════

class TestCandidatePoolBuilder:
    def test_valid_candidates_included(self):
        pool = build_candidate_pool((_cand(),))
        assert pool.pool_size == 1
        assert pool.candidates[0].pair == "BTC/USDT"

    def test_zero_score_excluded(self):
        pool = build_candidate_pool((_cand(score=0.0),))
        assert pool.pool_size == 0

    def test_negative_score_excluded(self):
        pool = build_candidate_pool((_cand(score=-0.1),))
        assert pool.pool_size == 0

    def test_zero_size_excluded(self):
        pool = build_candidate_pool((_cand(size=0.0),))
        assert pool.pool_size == 0

    def test_engines_present_deduped(self):
        pool = build_candidate_pool((
            _cand(pair="A", engine="engine_a"),
            _cand(pair="B", engine="engine_b"),
            _cand(pair="C", engine="engine_a"),
        ))
        assert pool.engines_present == ("engine_a", "engine_b")

    def test_empty_pool(self):
        pool = build_candidate_pool(())
        assert pool.pool_size == 0
        assert pool.engines_present == ()


# ═══════════════════════════════════════════════════════════════
# 2. eligibility_filter
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

    def test_rejected_gross_cap(self):
        r = check_eligibility(_cand(size=200.0), self._snapshot(gross=100.0))
        assert r.verdict == EligibilityVerdict.REJECTED_GROSS_CAP

    def test_rejected_cluster_cap(self):
        r = check_eligibility(_cand(size=200.0), self._snapshot(cluster_cap=100.0))
        assert r.verdict == EligibilityVerdict.REJECTED_CLUSTER

    def test_rejected_no_cluster(self):
        r = check_eligibility(_cand(cluster=""), self._snapshot())
        assert r.verdict == EligibilityVerdict.REJECTED_NO_CLUSTER

    def test_cluster_not_in_snapshot_rejected(self):
        snap = PortfolioSnapshot(
            remaining_gross_capacity=1000.0,
            remaining_cluster_capacity={},  # no clusters defined
        )
        r = check_eligibility(_cand(cluster="unknown"), snap)
        assert r.verdict == EligibilityVerdict.REJECTED_CLUSTER


# ═══════════════════════════════════════════════════════════════
# 3. comparative_ranker
# ═══════════════════════════════════════════════════════════════

class TestComparativeRanker:
    def test_score_formula(self):
        c = _cand(score=1.0, ce=1.0, cost=0.0)
        rs = compute_ranking_score(c, cluster_utilization=0.0)
        # 0.35*1 + 0.30*1 - 0.20*0 - 0.15*0 = 0.65
        assert abs(rs - 0.65) < 1e-9

    def test_cost_penalizes(self):
        c = _cand(score=1.0, ce=1.0, cost=1.0)
        rs = compute_ranking_score(c, cluster_utilization=0.0)
        # 0.35 + 0.30 - 0.20 = 0.45
        assert abs(rs - 0.45) < 1e-9

    def test_cluster_utilization_penalizes(self):
        c = _cand(score=1.0, ce=1.0, cost=0.0)
        rs = compute_ranking_score(c, cluster_utilization=1.0)
        # 0.35 + 0.30 - 0.15 = 0.50
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
        # B should rank higher (c1 penalized)
        assert ranked[0].candidate.pair == "B"


# ═══════════════════════════════════════════════════════════════
# 4. correlation_conflict_checker
# ═══════════════════════════════════════════════════════════════

class TestConflictChecker:
    def test_no_conflicts(self):
        r = check_conflicts((_cand(pair="A"), _cand(pair="B")))
        assert r.duplicates_removed == 0
        assert len(r.survivors) == 2

    def test_duplicate_pair_keeps_best(self):
        r = check_conflicts((
            _cand(pair="BTC/USDT", engine="engine_a", score=0.9),
            _cand(pair="BTC/USDT", engine="engine_b", score=0.5),
        ))
        assert r.duplicates_removed == 1
        assert len(r.survivors) == 1
        assert r.survivors[0].engine_id == "engine_a"
        assert any(c.conflict_type == ConflictType.DUPLICATE_PAIR for c in r.conflicts)

    def test_duplicate_pair_reverse_order(self):
        """Lower score first, higher second — still keeps higher."""
        r = check_conflicts((
            _cand(pair="X", engine="engine_b", score=0.3),
            _cand(pair="X", engine="engine_a", score=0.7),
        ))
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


# ═══════════════════════════════════════════════════════════════
# 5. selection_resolver
# ═══════════════════════════════════════════════════════════════

class TestSelectionResolver:
    def _ranked(self, candidates):
        return rank_candidates(candidates)

    def test_all_selected_when_capacity(self):
        ranked = self._ranked((_cand(pair="A", size=100), _cand(pair="B", size=100)))
        snap = PortfolioSnapshot(
            remaining_gross_capacity=1000.0,
            remaining_cluster_capacity={"btc_cluster": 1000.0},
        )
        r = resolve_selection(ranked, snap)
        assert len(r.selected) == 2
        assert len(r.rejected) == 0
        assert r.total_selected_size == 200.0

    def test_second_rejected_when_gross_exhausted(self):
        ranked = self._ranked((_cand(pair="A", size=100), _cand(pair="B", size=100)))
        snap = PortfolioSnapshot(
            remaining_gross_capacity=150.0,
            remaining_cluster_capacity={"btc_cluster": 1000.0},
        )
        r = resolve_selection(ranked, snap)
        assert len(r.selected) == 1
        assert len(r.rejected) == 1
        assert r.rejected[0].verdict == SelectionVerdict.REJECTED_CAPACITY

    def test_rejected_no_cluster(self):
        ranked = self._ranked((_cand(pair="X", cluster=""),))
        snap = PortfolioSnapshot(remaining_gross_capacity=1000.0)
        r = resolve_selection(ranked, snap)
        assert len(r.rejected) == 1
        assert r.rejected[0].verdict == SelectionVerdict.REJECTED_NO_CLUSTER

    def test_cluster_capacity_decremented(self):
        ranked = self._ranked((
            _cand(pair="A", size=80, cluster="c1"),
            _cand(pair="B", size=80, cluster="c1"),
        ))
        snap = PortfolioSnapshot(
            remaining_gross_capacity=1000.0,
            remaining_cluster_capacity={"c1": 100.0},
        )
        r = resolve_selection(ranked, snap)
        assert len(r.selected) == 1
        assert len(r.rejected) == 1
        assert r.rejected[0].verdict == SelectionVerdict.REJECTED_CLUSTER

    def test_empty_ranked(self):
        r = resolve_selection((), PortfolioSnapshot(remaining_gross_capacity=1000.0))
        assert len(r.selected) == 0


# ═══════════════════════════════════════════════════════════════
# 6. base_size_builder
# ═══════════════════════════════════════════════════════════════

class TestBaseSizeBuilder:
    def test_normal_base_size(self):
        profile = SizeProfile(available_capital=10000.0)
        r = compute_base_size("BTC/USDT", profile)
        assert r.base_size == 200.0  # 10000 * 0.02
        assert not r.clamped

    def test_clamped_to_max(self):
        profile = SizeProfile(available_capital=100000.0, max_size=500.0)
        r = compute_base_size("BTC/USDT", profile)
        assert r.base_size == 500.0
        assert r.clamped

    def test_clamped_to_min(self):
        profile = SizeProfile(available_capital=100.0, min_size=10.0)
        r = compute_base_size("BTC/USDT", profile)
        assert r.base_size == 10.0  # 100*0.02=2 < min=10
        assert r.clamped

    def test_custom_fraction(self):
        profile = SizeProfile(available_capital=10000.0, base_fraction=0.05)
        r = compute_base_size("X", profile)
        assert r.base_size == 500.0  # 10000 * 0.05 = 500 = max

    def test_raw_base_preserved(self):
        profile = SizeProfile(available_capital=100.0, min_size=10.0)
        r = compute_base_size("X", profile)
        assert r.raw_base_size == 2.0
        assert r.base_size == 10.0


# ═══════════════════════════════════════════════════════════════
# 7. score_size_mapper
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
# 8. portfolio_cap_applier
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


# ═══════════════════════════════════════════════════════════════
# 9. phantom_trade_guard
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


# ═══════════════════════════════════════════════════════════════
# 10. allocation_reporter
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
