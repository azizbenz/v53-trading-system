"""Typed regression tests for Build-8 opportunity selector components."""

from __future__ import annotations

import pytest

from portfolio_minimal.opportunity_selector.candidate_pool_builder import (
    CANDIDATE_POOL_FRESHNESS_DISABLED,
    CandidatePoolFreshnessMode,
    CandidatePoolFreshnessPolicy,
    CandidatePoolRejectReason,
    build_candidate_pool,
    build_enforced_candidate_pool_freshness,
)
from portfolio_minimal.opportunity_selector.comparative_ranker import (
    RANKING_VERSION,
    compute_ranking_score,
    rank_candidates,
)
from portfolio_minimal.opportunity_selector.correlation_conflict_checker import (
    ConflictType,
    check_conflicts,
)
from portfolio_minimal.opportunity_selector.eligibility_filter import (
    EligibilityVerdict,
    PortfolioSnapshot,
    check_eligibility,
)
from portfolio_minimal.opportunity_selector.selection_resolver import (
    SelectionVerdict,
    resolve_selection,
)

from ._portfolio_support import build_candidate, build_snapshot


class TestCandidatePoolBuilder:
    def test_valid_candidates_included(self) -> None:
        pool = build_candidate_pool(
            (build_candidate(),),
            freshness_policy=CANDIDATE_POOL_FRESHNESS_DISABLED,
        )
        assert pool.pool_size == 1
        assert pool.candidates[0].pair == "BTC/USDT"

    def test_zero_score_excluded(self) -> None:
        pool = build_candidate_pool(
            (build_candidate(score=0.0),),
            freshness_policy=CANDIDATE_POOL_FRESHNESS_DISABLED,
        )
        assert pool.pool_size == 0

    def test_negative_score_excluded(self) -> None:
        pool = build_candidate_pool(
            (build_candidate(score=-0.1),),
            freshness_policy=CANDIDATE_POOL_FRESHNESS_DISABLED,
        )
        assert pool.pool_size == 0

    def test_zero_size_excluded(self) -> None:
        pool = build_candidate_pool(
            (build_candidate(size=0.0),),
            freshness_policy=CANDIDATE_POOL_FRESHNESS_DISABLED,
        )
        assert pool.pool_size == 0

    def test_engines_present_deduped(self) -> None:
        pool = build_candidate_pool(
            (
                build_candidate(pair="A", engine="engine_a"),
                build_candidate(pair="B", engine="engine_b"),
                build_candidate(pair="C", engine="engine_a"),
            ),
            freshness_policy=CANDIDATE_POOL_FRESHNESS_DISABLED,
        )
        assert pool.engines_present == ("engine_a", "engine_b")

    def test_empty_pool(self) -> None:
        pool = build_candidate_pool(
            (),
            freshness_policy=CANDIDATE_POOL_FRESHNESS_DISABLED,
        )
        assert pool.pool_size == 0
        assert pool.engines_present == ()

    def test_expired_signal_rejected_with_audit(self) -> None:
        pool = build_candidate_pool(
            (
                build_candidate(
                    pair="BTC/USDT",
                    engine="engine_a",
                    emitted_at=100.0,
                ),
            ),
            freshness_policy=build_enforced_candidate_pool_freshness(
                now_ts=500.0,
                max_signal_age_s=60.0,
            ),
        )
        assert pool.pool_size == 0
        assert pool.rejected_count == 1
        assert (
            pool.rejected_candidates[0].reason
            == CandidatePoolRejectReason.SIGNAL_EXPIRED
        )

    def test_signal_not_rejected_with_explicitly_disabled_freshness(self) -> None:
        pool = build_candidate_pool(
            (
                build_candidate(
                    pair="BTC/USDT",
                    engine="engine_a",
                    emitted_at=100.0,
                ),
            ),
            freshness_policy=CANDIDATE_POOL_FRESHNESS_DISABLED,
        )
        assert pool.pool_size == 1
        assert pool.rejected_count == 0

    def test_disabled_freshness_policy_rejects_hidden_values(self) -> None:
        with pytest.raises(ValueError, match="disabled candidate-pool freshness policy"):
            CandidatePoolFreshnessPolicy(
                mode=CandidatePoolFreshnessMode.DISABLED,
                now_ts=500.0,
            )


class TestEligibilityFilter:
    def test_eligible(self) -> None:
        result = check_eligibility(
            build_candidate(size=100.0),
            build_snapshot(),
        )
        assert result.verdict == EligibilityVerdict.ELIGIBLE

    def test_rejected_no_cluster(self) -> None:
        result = check_eligibility(
            build_candidate(cluster=""),
            build_snapshot(),
        )
        assert result.verdict == EligibilityVerdict.REJECTED_NO_CLUSTER

    def test_oversized_not_rejected_by_selector(self) -> None:
        result = check_eligibility(
            build_candidate(size=2000.0),
            build_snapshot(gross=100.0),
        )
        assert result.verdict == EligibilityVerdict.ELIGIBLE

    def test_oversized_cluster_not_rejected_by_selector(self) -> None:
        result = check_eligibility(
            build_candidate(size=2000.0),
            build_snapshot(cluster_capacities={"btc_cluster": 100.0}),
        )
        assert result.verdict == EligibilityVerdict.ELIGIBLE

    def test_unknown_cluster_rejected_fail_closed(self) -> None:
        snapshot = PortfolioSnapshot(
            remaining_gross_capacity=1000.0,
            remaining_cluster_capacity={},
        )
        result = check_eligibility(build_candidate(cluster="unknown"), snapshot)
        assert result.verdict == EligibilityVerdict.REJECTED_UNKNOWN_CLUSTER
        assert "unknown cluster mapping" in result.reason


class TestComparativeRanker:
    def test_score_formula(self) -> None:
        ranking_score = compute_ranking_score(
            build_candidate(score=1.0, ce=1.0, cost=0.0),
            cluster_utilization=0.0,
        )
        assert abs(ranking_score - 0.65) < 1e-9

    def test_cost_penalizes(self) -> None:
        ranking_score = compute_ranking_score(
            build_candidate(score=1.0, ce=1.0, cost=1.0),
            cluster_utilization=0.0,
        )
        assert abs(ranking_score - 0.45) < 1e-9

    def test_cluster_utilization_penalizes(self) -> None:
        ranking_score = compute_ranking_score(
            build_candidate(score=1.0, ce=1.0, cost=0.0),
            cluster_utilization=1.0,
        )
        assert abs(ranking_score - 0.50) < 1e-9

    def test_rank_order(self) -> None:
        ranked = rank_candidates(
            (
                build_candidate(pair="LOW", score=0.2, ce=0.01),
                build_candidate(pair="HIGH", score=0.9, ce=0.10),
                build_candidate(pair="MID", score=0.5, ce=0.05),
            )
        )
        assert ranked[0].candidate.pair == "HIGH"
        assert ranked[0].rank == 1
        assert ranked[-1].candidate.pair == "LOW"
        assert ranked[-1].rank == 3

    def test_rank_with_cluster_utils(self) -> None:
        ranked = rank_candidates(
            (
                build_candidate(pair="A", score=0.8, cluster="c1"),
                build_candidate(pair="B", score=0.8, cluster="c2"),
            ),
            cluster_utilizations={"c1": 1.0, "c2": 0.0},
        )
        assert ranked[0].candidate.pair == "B"

    def test_rank_is_deterministic_on_exact_tie(self) -> None:
        ranked = rank_candidates(
            (
                build_candidate(
                    pair="ETH/USDT",
                    engine="engine_b",
                    score=0.8,
                    ce=0.1,
                    cost=0.01,
                ),
                build_candidate(
                    pair="BTC/USDT",
                    engine="engine_a",
                    score=0.8,
                    ce=0.1,
                    cost=0.01,
                ),
            )
        )
        assert tuple(entry.candidate.pair for entry in ranked) == (
            "BTC/USDT",
            "ETH/USDT",
        )
        assert all(entry.ranking_version == RANKING_VERSION for entry in ranked)


class TestConflictChecker:
    def test_no_conflicts(self) -> None:
        result = check_conflicts((build_candidate(pair="A"), build_candidate(pair="B")))
        assert result.duplicates_removed == 0
        assert len(result.survivors) == 2

    def test_duplicate_pair_keeps_best_by_ranking_score(self) -> None:
        result = check_conflicts(
            (
                build_candidate(pair="BTC/USDT", engine="engine_a", score=0.9, ce=0.01),
                build_candidate(pair="BTC/USDT", engine="engine_b", score=0.5, ce=0.50),
            )
        )
        assert result.duplicates_removed == 1
        assert len(result.survivors) == 1
        assert any(
            conflict.conflict_type == ConflictType.DUPLICATE_PAIR
            for conflict in result.conflicts
        )

    def test_duplicate_pair_reverse_order(self) -> None:
        result = check_conflicts(
            (
                build_candidate(pair="X", engine="engine_b", score=0.3),
                build_candidate(pair="X", engine="engine_a", score=0.7),
            )
        )
        assert len(result.survivors) == 1
        assert result.survivors[0].penalized_score == 0.7

    def test_cluster_crowding_flagged(self) -> None:
        candidates = tuple(build_candidate(pair=f"P{i}", cluster="crowded") for i in range(5))
        result = check_conflicts(candidates, cluster_crowding_threshold=3)
        assert any(
            conflict.conflict_type == ConflictType.CLUSTER_CROWDING
            for conflict in result.conflicts
        )

    def test_cluster_crowding_not_flagged_below_threshold(self) -> None:
        candidates = tuple(build_candidate(pair=f"P{i}", cluster="ok") for i in range(3))
        result = check_conflicts(candidates, cluster_crowding_threshold=3)
        assert not any(
            conflict.conflict_type == ConflictType.CLUSTER_CROWDING
            for conflict in result.conflicts
        )

    def test_empty_input(self) -> None:
        result = check_conflicts(())
        assert len(result.survivors) == 0
        assert result.duplicates_removed == 0

    def test_dedup_uses_composite_not_just_score(self) -> None:
        result = check_conflicts(
            (
                build_candidate(pair="X", engine="engine_a", score=0.9, ce=0.01, cost=0.01),
                build_candidate(pair="X", engine="engine_b", score=0.5, ce=0.50, cost=0.01),
            )
        )
        assert result.survivors[0].engine_id == "engine_b"

    def test_contradictory_pair_is_neutralized_with_full_audit(self) -> None:
        result = check_conflicts(
            (
                build_candidate(
                    pair="BTC/USDT",
                    engine="engine_a",
                    direction="long",
                    emitted_at=100.0,
                    score=0.8,
                ),
                build_candidate(
                    pair="BTC/USDT",
                    engine="engine_b",
                    direction="short",
                    emitted_at=120.0,
                    score=0.7,
                ),
            )
        )
        assert len(result.survivors) == 0
        assert any(
            conflict.conflict_type == ConflictType.CONTRADICTORY_SIGNAL
            for conflict in result.conflicts
        )
        assert len(result.rejection_audit) == 2
        assert {entry.engine_id for entry in result.rejection_audit} == {
            "engine_a",
            "engine_b",
        }

    def test_contradictory_pair_outside_window_is_not_neutralized(self) -> None:
        result = check_conflicts(
            (
                build_candidate(
                    pair="BTC/USDT",
                    engine="engine_a",
                    direction="long",
                    emitted_at=100.0,
                    score=0.8,
                ),
                build_candidate(
                    pair="BTC/USDT",
                    engine="engine_b",
                    direction="short",
                    emitted_at=1000.0,
                    score=0.7,
                ),
            ),
            contradiction_window_s=60.0,
        )
        assert len(result.survivors) == 1
        assert not any(
            conflict.conflict_type == ConflictType.CONTRADICTORY_SIGNAL
            for conflict in result.conflicts
        )


class TestSelectionResolver:
    def test_all_selected_with_cluster(self) -> None:
        ranked = rank_candidates(
            (
                build_candidate(pair="A", size=100),
                build_candidate(pair="B", size=100),
            )
        )
        result = resolve_selection(
            ranked,
            build_snapshot(gross=1000.0, cluster_capacities={"btc_cluster": 1000.0}),
        )
        assert len(result.selected) == 2
        assert len(result.rejected) == 0

    def test_oversized_still_selected(self) -> None:
        ranked = rank_candidates((build_candidate(pair="A", size=5000),))
        result = resolve_selection(
            ranked,
            build_snapshot(gross=100.0, cluster_capacities={"btc_cluster": 50.0}),
        )
        assert len(result.selected) == 1
        assert len(result.rejected) == 0

    def test_rejected_no_cluster(self) -> None:
        ranked = rank_candidates((build_candidate(pair="X", cluster=""),))
        result = resolve_selection(
            ranked,
            PortfolioSnapshot(remaining_gross_capacity=1000.0),
        )
        assert len(result.rejected) == 1
        assert result.rejected[0].verdict == SelectionVerdict.REJECTED_NO_CLUSTER

    def test_rejected_unknown_cluster(self) -> None:
        ranked = rank_candidates((build_candidate(pair="X", cluster="unknown"),))
        result = resolve_selection(
            ranked,
            PortfolioSnapshot(
                remaining_gross_capacity=1000.0,
                remaining_cluster_capacity={},
            ),
        )
        assert len(result.selected) == 0
        assert len(result.rejected) == 1
        assert result.rejected[0].verdict == SelectionVerdict.REJECTED_UNKNOWN_CLUSTER
        assert "unknown cluster mapping" in result.rejected[0].reason

    def test_mixed_cluster_and_no_cluster(self) -> None:
        ranked = rank_candidates(
            (
                build_candidate(pair="A", cluster="c1"),
                build_candidate(pair="B", cluster=""),
            )
        )
        result = resolve_selection(
            ranked,
            build_snapshot(gross=1000.0, cluster_capacities={"c1": 500.0}),
        )
        assert len(result.selected) == 1
        assert len(result.rejected) == 1

    def test_empty_ranked(self) -> None:
        result = resolve_selection(
            (),
            PortfolioSnapshot(remaining_gross_capacity=1000.0),
        )
        assert len(result.selected) == 0

    def test_selection_exposes_versions(self) -> None:
        ranked = rank_candidates((build_candidate(pair="A", cluster="c1"),))
        result = resolve_selection(
            ranked,
            build_snapshot(gross=1000.0, cluster_capacities={"c1": 500.0}),
        )
        assert result.selection_version == "build8_selection_v1"
        assert result.ranking_version == RANKING_VERSION
