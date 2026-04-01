"""Integration tests for Build-6 Engine A across scoring and portfolio gates."""

from engines.engine_a.engine_a_runner import EngineADecision, EngineAInput, run_engine_a
from scoring_backbone.hard_block_gate.blocker_decision_builder import build_decision
from scoring_backbone.hard_block_gate.blocker_reason_encoder import encode_reasons
from scoring_backbone.penalty_aggregator.penalty_cap_guard import evaluate_penalty_cap
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


def _good_inputs(**overrides) -> EngineAInput:
    defaults = dict(
        pair="BTCUSDT",
        direction_score=0.8,
        continuation_score=0.9,
        structure_quality=0.85,
        zone_proximity=0.7,
        trend_stability=0.8,
        regime="trending_up",
        regime_favorability=0.9,
        regime_confidence=0.8,
        pair_health=0.9,
        data_freshness=0.95,
        flow_coherence=0.8,
        flow_score=0.5,
        cost_preference_score=0.4,
        expected_gain=0.005,
        expected_cost=0.001,
        candidate_size=1000.0,
        holding_period=4.0,
        entry_price=50000.0,
        atr=500.0,
        scoring_version="v1.0",
    )
    defaults.update(overrides)
    return EngineAInput(**defaults)


def _penalty_registry() -> PenaltyRegistry:
    reg = PenaltyRegistry()
    reg.register(PenaltyDefinition(penalty_id="context_soft", name="Context soft", penalty_type=PenaltyType.SCORE))
    reg.register(PenaltyDefinition(penalty_id="microstructure_soft", name="Microstructure soft", penalty_type=PenaltyType.SCORE))
    reg.register(PenaltyDefinition(penalty_id="size_context", name="Context sizing", penalty_type=PenaltyType.SIZE))
    return reg


def test_engine_a_signal_can_be_penalized_then_ranked_against_other_candidates():
    output = run_engine_a(_good_inputs())
    assert output.decision == EngineADecision.EMIT

    registry = _penalty_registry()
    score_penalty = build_score_penalty(
        raw_score=output.raw_score,
        penalties=(
            ScorePenaltyItem(penalty_id="context_soft", value=0.15, reason="context not perfect"),
            ScorePenaltyItem(penalty_id="microstructure_soft", value=0.10, reason="microstructure average"),
        ),
        registry=registry,
    )
    size_penalty = build_size_penalty(
        penalties=(SizePenaltyItem(penalty_id="size_context", multiplier=0.85, reason="size prudence"),),
        registry=registry,
    )
    cap = evaluate_penalty_cap(
        score_penalty=score_penalty.total_penalty,
        size_multiplier=size_penalty.total_multiplier,
        max_score_penalty=2.0,
        min_size_multiplier=0.1,
        raw_score=output.raw_score,
        expected_cost=output.expected_cost,
    )
    assert cap.verdict.value in {"normal", "capped", "phantom_risk"}

    hard_block = build_decision(output.pair, output.engine_id, encode_reasons(()))
    assert hard_block.is_blocked is False

    candidates = (
        RankingCandidate(
            engine_id=output.engine_id,
            pair=output.pair,
            penalized_score=score_penalty.adjusted_score,
            size_multiplier=size_penalty.total_multiplier,
            expected_cost=output.expected_cost,
            expected_ce=output.ce_expected,
            projected_risk=0.05,
            cluster_id="majors",
        ),
        RankingCandidate(
            engine_id="engine_b",
            pair="ETHUSDT",
            penalized_score=output.raw_score,
            size_multiplier=1.0,
            expected_cost=max(0.0, output.expected_cost - 0.0002),
            expected_ce=output.ce_expected + 0.0002,
            projected_risk=0.03,
            cluster_id="majors",
        ),
    )
    pool = build_candidate_pool(candidates, blocked_keys=frozenset())

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
        portfolio_rejected_keys=frozenset(),
    )

    assert result.selected_count == 1
    assert result.rejected_by_ranking == 1
    engine_a_entry = next(entry for entry in result.entries if entry.engine_id == "engine_a")
    assert engine_a_entry.outcome == SelectionOutcome.REJECTED_RANKING


def test_engine_a_signal_cannot_bypass_portfolio_caps():
    output = run_engine_a(_good_inputs())
    assert output.decision == EngineADecision.EMIT

    candidate = RankingCandidate(
        engine_id=output.engine_id,
        pair=output.pair,
        penalized_score=output.raw_score,
        size_multiplier=1.0,
        expected_cost=output.expected_cost,
        expected_ce=output.ce_expected,
        projected_risk=0.05,
        cluster_id="majors",
    )
    portfolio = PortfolioState(
        remaining_gross_capacity=10.0,
        remaining_loss_capacity=100.0,
        remaining_beta_capacity=1.0,
        remaining_cluster_capacity={"majors": 500.0},
    )
    compatibility = check_portfolio_compatibility(
        candidate.engine_id,
        candidate.pair,
        projected_size=100.0,
        projected_loss=5.0,
        projected_beta_impact=0.05,
        cluster_id=candidate.cluster_id,
        portfolio=portfolio,
    )
    assert compatibility.verdict.value == "rejected_exposure"

    ranked = compute_ranking_scores(
        (
            {
                "engine_id": candidate.engine_id,
                "pair": candidate.pair,
                "penalized_score": candidate.penalized_score,
                "expected_ce": candidate.expected_ce,
                "expected_cost": candidate.expected_cost,
                "risk_penalty": candidate.projected_risk,
            },
        ),
        RankingWeights(),
    )
    result = resolve_selection(
        (
            {
                "engine_id": ranked[0].engine_id,
                "pair": ranked[0].pair,
                "ranking_score": ranked[0].ranking_score,
                "rank": ranked[0].rank,
            },
        ),
        max_selections=1,
        portfolio_rejected_keys=frozenset({(candidate.engine_id, candidate.pair)}),
    )

    assert result.selected_count == 0
    assert result.rejected_by_portfolio == 1
    assert result.entries[0].outcome == SelectionOutcome.REJECTED_PORTFOLIO
