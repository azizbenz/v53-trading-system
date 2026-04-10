"""Tests for scoring_backbone.ranking_router — Build-5."""
import pytest

from scoring_backbone.ranking_router.candidate_pool_builder import (
    RankingCandidate,
    CandidatePool,
    build_candidate_pool,
)
from scoring_backbone.ranking_router.ranking_score_builder import (
    RankingWeights,
    RankedCandidate,
    compute_ranking_scores,
)
from scoring_backbone.ranking_router.portfolio_compatibility_checker import (
    CompatibilityVerdict,
    PortfolioState,
    CompatibilityResult,
    check_portfolio_compatibility,
)
from scoring_backbone.ranking_router.selection_resolver import (
    SelectionOutcome,
    SelectionResult,
    resolve_selection,
)
from scoring_backbone.ranking_router.ranking_reporter import (
    RankingEvent,
    RankingReporter,
)


# ── candidate_pool_builder ──


class TestCandidatePoolBuilder:
    def test_single_valid(self):
        """One candidate, not blocked."""
        candidates = (RankingCandidate(engine_id="eng1", pair="BTCUSDT", penalized_score=2.0),)
        pool = build_candidate_pool(candidates, frozenset())
        assert pool.pool_size == 1
        assert pool.hard_blocked == 0

    def test_filter_blocked(self):
        candidates = (
            RankingCandidate(engine_id="eng1", pair="BTCUSDT", penalized_score=2.0),
            RankingCandidate(engine_id="eng1", pair="ETHUSDT", penalized_score=1.5),
        )
        blocked = frozenset({("eng1", "BTCUSDT")})
        pool = build_candidate_pool(candidates, blocked)
        assert pool.pool_size == 1
        assert pool.hard_blocked == 1
        assert pool.candidates[0].pair == "ETHUSDT"

    def test_all_blocked(self):
        candidates = (RankingCandidate(engine_id="eng1", pair="BTC", penalized_score=2.0),)
        blocked = frozenset({("eng1", "BTC")})
        pool = build_candidate_pool(candidates, blocked)
        assert pool.pool_size == 0
        assert pool.hard_blocked == 1

    def test_total_submitted(self):
        candidates = (
            RankingCandidate(engine_id="eng1", pair="BTC", penalized_score=2.0),
            RankingCandidate(engine_id="eng1", pair="ETH", penalized_score=1.5),
        )
        pool = build_candidate_pool(candidates, frozenset({("eng1", "BTC")}))
        assert pool.total_submitted == 2


# ── ranking_score_builder ──


class TestRankingScoreBuilder:
    def test_single_candidate_ranked(self):
        candidates = ({"engine_id": "eng1", "pair": "BTCUSDT", "penalized_score": 2.0, "expected_ce": 0.1, "expected_cost": 0.05},)
        ranked = compute_ranking_scores(candidates, RankingWeights())
        assert len(ranked) == 1
        assert ranked[0].rank == 1

    def test_multiple_sorted_descending(self):
        candidates = (
            {"engine_id": "eng1", "pair": "ETHUSDT", "penalized_score": 1.0, "expected_ce": 0.1, "expected_cost": 0.05},
            {"engine_id": "eng1", "pair": "BTCUSDT", "penalized_score": 3.0, "expected_ce": 0.2, "expected_cost": 0.05},
        )
        ranked = compute_ranking_scores(candidates, RankingWeights())
        assert ranked[0].pair == "BTCUSDT"
        assert ranked[0].rank == 1
        assert ranked[1].rank == 2

    def test_cost_lowers_ranking(self):
        """Higher cost candidate gets lower ranking despite same score."""
        candidates = (
            {"engine_id": "eng1", "pair": "A", "penalized_score": 2.0, "expected_ce": 0.0, "expected_cost": 5.0},
            {"engine_id": "eng1", "pair": "B", "penalized_score": 2.0, "expected_ce": 0.0, "expected_cost": 0.1},
        )
        ranked = compute_ranking_scores(candidates, RankingWeights(w_cost=1.0))
        assert ranked[0].pair == "B"

    def test_lower_score_better_cost_wins(self):
        """Opportunity with lower score but much better cost can win."""
        candidates = (
            {"engine_id": "eng1", "pair": "A", "penalized_score": 3.0, "expected_ce": 0.0, "expected_cost": 10.0},
            {"engine_id": "eng1", "pair": "B", "penalized_score": 2.5, "expected_ce": 0.0, "expected_cost": 0.1},
        )
        ranked = compute_ranking_scores(candidates, RankingWeights(w_score=1.0, w_cost=1.0))
        assert ranked[0].pair == "B"

    def test_reproducibility(self):
        """Same input → same ranking."""
        candidates = (
            {"engine_id": "eng1", "pair": "A", "penalized_score": 2.0, "expected_ce": 0.1, "expected_cost": 0.05},
            {"engine_id": "eng1", "pair": "B", "penalized_score": 3.0, "expected_ce": 0.2, "expected_cost": 0.05},
        )
        w = RankingWeights()
        r1 = compute_ranking_scores(candidates, w)
        r2 = compute_ranking_scores(candidates, w)
        assert r1[0].ranking_score == r2[0].ranking_score

    def test_corr_penalty_applied(self):
        candidates = (
            {"engine_id": "eng1", "pair": "A", "penalized_score": 2.0, "expected_ce": 0.0, "expected_cost": 0.0, "corr_penalty": 5.0},
            {"engine_id": "eng1", "pair": "B", "penalized_score": 2.0, "expected_ce": 0.0, "expected_cost": 0.0, "corr_penalty": 0.0},
        )
        ranked = compute_ranking_scores(candidates, RankingWeights(w_corr=1.0))
        assert ranked[0].pair == "B"


# ── portfolio_compatibility_checker ──


class TestPortfolioCompatibilityChecker:
    def test_compatible(self):
        portfolio = PortfolioState(
            remaining_gross_capacity=1000.0,
            remaining_loss_capacity=100.0,
            remaining_beta_capacity=0.5,
            remaining_cluster_capacity={"btc_majors": 500.0},
        )
        result = check_portfolio_compatibility(
            "eng1", "BTCUSDT", projected_size=100.0,
            projected_loss=10.0, projected_beta_impact=0.1,
            cluster_id="btc_majors", portfolio=portfolio,
        )
        assert result.verdict == CompatibilityVerdict.COMPATIBLE

    def test_rejected_exposure(self):
        portfolio = PortfolioState(remaining_gross_capacity=50.0, remaining_loss_capacity=100.0, remaining_beta_capacity=1.0)
        result = check_portfolio_compatibility(
            "eng1", "BTCUSDT", projected_size=100.0,
            projected_loss=10.0, projected_beta_impact=0.1,
            cluster_id="", portfolio=portfolio,
        )
        assert result.verdict == CompatibilityVerdict.REJECTED_EXPOSURE

    def test_rejected_loss_budget(self):
        portfolio = PortfolioState(remaining_gross_capacity=1000.0, remaining_loss_capacity=5.0, remaining_beta_capacity=1.0)
        result = check_portfolio_compatibility(
            "eng1", "BTCUSDT", projected_size=100.0,
            projected_loss=10.0, projected_beta_impact=0.1,
            cluster_id="", portfolio=portfolio,
        )
        assert result.verdict == CompatibilityVerdict.REJECTED_LOSS_BUDGET

    def test_rejected_cluster(self):
        portfolio = PortfolioState(
            remaining_gross_capacity=1000.0, remaining_loss_capacity=100.0,
            remaining_beta_capacity=1.0,
            remaining_cluster_capacity={"btc_majors": 50.0},
        )
        result = check_portfolio_compatibility(
            "eng1", "BTCUSDT", projected_size=100.0,
            projected_loss=10.0, projected_beta_impact=0.1,
            cluster_id="btc_majors", portfolio=portfolio,
        )
        assert result.verdict == CompatibilityVerdict.REJECTED_CLUSTER

    def test_rejected_beta(self):
        portfolio = PortfolioState(remaining_gross_capacity=1000.0, remaining_loss_capacity=100.0, remaining_beta_capacity=0.05)
        result = check_portfolio_compatibility(
            "eng1", "BTCUSDT", projected_size=100.0,
            projected_loss=10.0, projected_beta_impact=0.1,
            cluster_id="", portfolio=portfolio,
        )
        assert result.verdict == CompatibilityVerdict.REJECTED_BETA

    def test_reason_populated(self):
        portfolio = PortfolioState(remaining_gross_capacity=50.0, remaining_loss_capacity=100.0, remaining_beta_capacity=1.0)
        result = check_portfolio_compatibility(
            "eng1", "BTCUSDT", projected_size=100.0,
            projected_loss=10.0, projected_beta_impact=0.1,
            cluster_id="", portfolio=portfolio,
        )
        assert result.reason != ""

    def test_rejected_negative_beta_out_of_cap(self):
        """Negative beta of large magnitude must be rejected symmetrically."""
        portfolio = PortfolioState(
            remaining_gross_capacity=1000.0, remaining_loss_capacity=100.0,
            remaining_beta_capacity=0.05,
            remaining_cluster_capacity={"btc_majors": 500.0},
        )
        result = check_portfolio_compatibility(
            "eng1", "BTCUSDT", projected_size=100.0,
            projected_loss=10.0, projected_beta_impact=-0.1,
            cluster_id="btc_majors", portfolio=portfolio,
        )
        assert result.verdict == CompatibilityVerdict.REJECTED_BETA
        assert "beta impact" in result.reason

    def test_rejected_empty_cluster_id(self):
        """Empty cluster_id must be rejected — fail-closed."""
        portfolio = PortfolioState(
            remaining_gross_capacity=1000.0, remaining_loss_capacity=100.0,
            remaining_beta_capacity=1.0,
        )
        result = check_portfolio_compatibility(
            "eng1", "DOGEUSDT", projected_size=50.0,
            projected_loss=5.0, projected_beta_impact=0.01,
            cluster_id="", portfolio=portfolio,
        )
        assert result.verdict == CompatibilityVerdict.REJECTED_CLUSTER
        assert "no cluster mapping" in result.reason

    def test_rejected_unknown_cluster_id_is_not_masked_as_zero_capacity(self):
        """Unknown cluster must fail closed as config/mapping absence, not as exhausted budget."""
        portfolio = PortfolioState(
            remaining_gross_capacity=1000.0,
            remaining_loss_capacity=100.0,
            remaining_beta_capacity=1.0,
            remaining_cluster_capacity={"btc_majors": 500.0},
        )
        result = check_portfolio_compatibility(
            "eng1", "SOLUSDT", projected_size=50.0,
            projected_loss=5.0, projected_beta_impact=0.01,
            cluster_id="sol_ecosystem", portfolio=portfolio,
        )

        assert result.verdict == CompatibilityVerdict.REJECTED_CLUSTER
        assert "unknown cluster mapping" in result.reason
        assert "0.00" not in result.reason


# ── selection_resolver ──


class TestSelectionResolver:
    def test_single_selected(self):
        candidates = ({"engine_id": "eng1", "pair": "BTCUSDT", "ranking_score": 5.0, "rank": 1},)
        result = resolve_selection(candidates, max_selections=3, portfolio_rejected_keys=frozenset())
        assert result.selected_count == 1
        assert result.entries[0].outcome == SelectionOutcome.SELECTED

    def test_top_k_selection(self):
        candidates = (
            {"engine_id": "eng1", "pair": "BTC", "ranking_score": 5.0, "rank": 1},
            {"engine_id": "eng1", "pair": "ETH", "ranking_score": 4.0, "rank": 2},
            {"engine_id": "eng1", "pair": "SOL", "ranking_score": 3.0, "rank": 3},
        )
        result = resolve_selection(candidates, max_selections=2, portfolio_rejected_keys=frozenset())
        assert result.selected_count == 2
        assert result.rejected_by_ranking == 1

    def test_portfolio_rejection(self):
        candidates = (
            {"engine_id": "eng1", "pair": "BTC", "ranking_score": 5.0, "rank": 1},
            {"engine_id": "eng1", "pair": "ETH", "ranking_score": 4.0, "rank": 2},
        )
        rejected = frozenset({("eng1", "BTC")})
        result = resolve_selection(candidates, max_selections=5, portfolio_rejected_keys=rejected)
        assert result.rejected_by_portfolio == 1
        assert result.selected_count == 1

    def test_rejection_reasons_visible(self):
        candidates = (
            {"engine_id": "eng1", "pair": "BTC", "ranking_score": 5.0, "rank": 1},
            {"engine_id": "eng1", "pair": "ETH", "ranking_score": 4.0, "rank": 2},
        )
        result = resolve_selection(candidates, max_selections=1, portfolio_rejected_keys=frozenset())
        rejected_entry = [e for e in result.entries if e.outcome == SelectionOutcome.REJECTED_RANKING][0]
        assert rejected_entry.rejection_reason != ""

    def test_reproducibility(self):
        candidates = (
            {"engine_id": "eng1", "pair": "BTC", "ranking_score": 5.0, "rank": 1},
            {"engine_id": "eng1", "pair": "ETH", "ranking_score": 4.0, "rank": 2},
        )
        r1 = resolve_selection(candidates, 1, frozenset())
        r2 = resolve_selection(candidates, 1, frozenset())
        assert r1.selected_count == r2.selected_count


# ── ranking_reporter ──


class TestRankingReporter:
    def test_initial_empty(self):
        reporter = RankingReporter()
        stats = reporter.get_stats()
        assert stats.total_rounds == 0

    def test_record_event(self):
        reporter = RankingReporter()
        reporter.record(RankingEvent(pool_size=5, selected_count=2, rejected_by_ranking=2, rejected_by_portfolio=1))
        stats = reporter.get_stats()
        assert stats.total_rounds == 1
        assert stats.total_selected == 2
        assert stats.mean_pool_size == pytest.approx(5.0)

    def test_selection_rate(self):
        reporter = RankingReporter()
        reporter.record(RankingEvent(pool_size=10, selected_count=3, rejected_by_ranking=5, rejected_by_portfolio=2))
        reporter.record(RankingEvent(pool_size=10, selected_count=5, rejected_by_ranking=3, rejected_by_portfolio=2))
        stats = reporter.get_stats()
        assert stats.selection_rate == pytest.approx(8 / 20)

    def test_get_events(self):
        reporter = RankingReporter()
        reporter.record(RankingEvent(pool_size=5, selected_count=2, rejected_by_ranking=2, rejected_by_portfolio=1))
        assert len(reporter.get_events()) == 1
