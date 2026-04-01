"""Integration tests for Build-5 scoring backbone."""

from scoring_backbone.hard_block_gate.blocker_decision_builder import build_decision
from scoring_backbone.hard_block_gate.blocker_evaluator import (
    BlockerCondition,
    evaluate_blockers,
)
from scoring_backbone.hard_block_gate.blocker_reason_encoder import encode_reasons
from scoring_backbone.penalty_aggregator.penalty_cap_guard import (
    PenaltyCapVerdict,
    evaluate_penalty_cap,
)
from scoring_backbone.penalty_aggregator.penalty_registry import (
    PenaltyDefinition,
    PenaltyRegistry,
    PenaltyType,
)
from scoring_backbone.penalty_aggregator.score_penalty_builder import (
    ScorePenaltyItem,
    build_score_penalty,
)
from scoring_backbone.penalty_aggregator.size_penalty_builder import (
    SizePenaltyItem,
    build_size_penalty,
)
from scoring_backbone.ranking_router.candidate_pool_builder import (
    RankingCandidate,
    build_candidate_pool,
)
from scoring_backbone.ranking_router.portfolio_compatibility_checker import (
    PortfolioState,
    check_portfolio_compatibility,
)
from scoring_backbone.ranking_router.ranking_score_builder import (
    RankingWeights,
    compute_ranking_scores,
)
from scoring_backbone.ranking_router.selection_resolver import (
    SelectionOutcome,
    resolve_selection,
)
from scoring_backbone.raw_score_builder.feature_selector import select_features
from scoring_backbone.raw_score_builder.raw_score_calculator import calculate_raw_score


def build_registry() -> PenaltyRegistry:
    reg = PenaltyRegistry()
    reg.register(PenaltyDefinition(penalty_id="stale", name="Staleness", penalty_type=PenaltyType.SCORE))
    reg.register(PenaltyDefinition(penalty_id="spread", name="Spread", penalty_type=PenaltyType.SCORE))
    reg.register(PenaltyDefinition(penalty_id="size_stale", name="Staleness sizing", penalty_type=PenaltyType.SIZE))
    return reg


def test_soft_penalties_reduce_priority_without_becoming_hidden_hard_block():
    registry = build_registry()
    selection = select_features(
        engine_id="eng_a",
        raw_features={"momentum": 1.2, "flow": 0.8, "forbidden": 9.0},
        allowed_features=frozenset({"momentum", "flow"}),
    )
    raw = calculate_raw_score(
        engine_id="eng_a",
        pair="BTCUSDT",
        features=selection.selected,
        weights={"momentum": 2.0, "flow": 1.0},
        scoring_version="5.0",
    )

    score_penalty = build_score_penalty(
        raw_score=raw.raw_score,
        penalties=(
            ScorePenaltyItem(penalty_id="stale", value=2.8, reason="data stale"),
            ScorePenaltyItem(penalty_id="spread", value=0.1, reason="wide spread"),
        ),
        registry=registry,
    )
    size_penalty = build_size_penalty(
        penalties=(SizePenaltyItem(penalty_id="size_stale", multiplier=0.1, reason="stale sizing"),),
        registry=registry,
    )
    cap = evaluate_penalty_cap(
        score_penalty=score_penalty.total_penalty,
        size_multiplier=size_penalty.total_multiplier,
        max_score_penalty=3.0,
        min_size_multiplier=0.05,
        raw_score=raw.raw_score,
        expected_cost=0.2,
    )
    assert cap.verdict == PenaltyCapVerdict.PHANTOM_RISK

    evaluations = evaluate_blockers(BlockerCondition())
    triggered = tuple((e.blocker_id, e.reason) for e in evaluations if e.triggered)
    decision = build_decision("BTCUSDT", "eng_a", encode_reasons(triggered))
    assert decision.is_blocked is False
    assert decision.may_proceed_to_ranking is True

    candidates = (
        RankingCandidate(
            engine_id="eng_a",
            pair="BTCUSDT",
            penalized_score=score_penalty.adjusted_score,
            size_multiplier=size_penalty.total_multiplier,
            expected_cost=0.2,
            expected_ce=0.1,
            projected_risk=0.05,
            cluster_id="majors",
        ),
        RankingCandidate(
            engine_id="eng_b",
            pair="ETHUSDT",
            penalized_score=2.5,
            size_multiplier=1.0,
            expected_cost=0.1,
            expected_ce=0.2,
            projected_risk=0.05,
            cluster_id="majors",
        ),
    )

    pool = build_candidate_pool(candidates, blocked_keys=frozenset())
    assert pool.pool_size == 2

    portfolio = PortfolioState(
        remaining_gross_capacity=1000.0,
        remaining_loss_capacity=100.0,
        remaining_beta_capacity=1.0,
        remaining_cluster_capacity={"majors": 500.0},
    )
    portfolio_rejected = frozenset(
        (candidate.engine_id, candidate.pair)
        for candidate in pool.candidates
        if check_portfolio_compatibility(
            candidate.engine_id,
            candidate.pair,
            projected_size=50.0 * candidate.size_multiplier,
            projected_loss=5.0,
            projected_beta_impact=0.05,
            cluster_id=candidate.cluster_id,
            portfolio=portfolio,
        ).verdict
        != "compatible"
    )
    assert portfolio_rejected == frozenset()

    ranked = compute_ranking_scores(
        tuple(
            {
                "engine_id": candidate.engine_id,
                "pair": candidate.pair,
                "penalized_score": candidate.penalized_score,
                "expected_ce": candidate.expected_ce,
                "expected_cost": candidate.expected_cost,
                "risk_penalty": candidate.projected_risk,
            }
            for candidate in pool.candidates
        ),
        RankingWeights(),
    )
    result = resolve_selection(
        tuple(
            {
                "engine_id": candidate.engine_id,
                "pair": candidate.pair,
                "ranking_score": candidate.ranking_score,
                "rank": candidate.rank,
            }
            for candidate in ranked
        ),
        max_selections=1,
        portfolio_rejected_keys=portfolio_rejected,
    )

    assert result.selected_count == 1
    assert result.rejected_by_ranking == 1
    btc_entry = next(entry for entry in result.entries if entry.pair == "BTCUSDT")
    assert btc_entry.outcome == SelectionOutcome.REJECTED_RANKING


def test_explicit_hard_block_removes_candidate_before_ranking():
    candidate = RankingCandidate(
        engine_id="eng_a",
        pair="BTCUSDT",
        penalized_score=2.0,
        size_multiplier=1.0,
        expected_cost=0.1,
        expected_ce=0.2,
        projected_risk=0.05,
        cluster_id="majors",
    )

    evaluations = evaluate_blockers(BlockerCondition(is_pair_suspended=True))
    triggered = tuple((e.blocker_id, e.reason) for e in evaluations if e.triggered)
    decision = build_decision("BTCUSDT", "eng_a", encode_reasons(triggered))
    blocked_keys = frozenset({(decision.engine_id, decision.pair)}) if decision.is_blocked else frozenset()

    pool = build_candidate_pool((candidate,), blocked_keys=blocked_keys)

    assert decision.is_blocked is True
    assert decision.may_proceed_to_ranking is False
    assert pool.pool_size == 0
    assert pool.hard_blocked == 1
