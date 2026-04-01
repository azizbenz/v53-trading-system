"""Runtime tests for Build-5 scoring backbone."""

import pytest

from scoring_backbone import ScoringCandidateInput, ScoringRuntime
from scoring_backbone.hard_block_gate.blocker_evaluator import BlockerCondition
from scoring_backbone.penalty_aggregator.penalty_registry import PenaltyDefinition, PenaltyRegistry, PenaltyType
from scoring_backbone.penalty_aggregator.score_penalty_builder import ScorePenaltyItem
from scoring_backbone.penalty_aggregator.size_penalty_builder import SizePenaltyItem
from scoring_backbone.ranking_router.portfolio_compatibility_checker import PortfolioState
from scoring_backbone.ranking_router.selection_resolver import SelectionOutcome


pytestmark = pytest.mark.build5


def _registry() -> PenaltyRegistry:
    registry = PenaltyRegistry()
    registry.register(PenaltyDefinition(penalty_id="stale", name="Staleness", penalty_type=PenaltyType.SCORE))
    registry.register(PenaltyDefinition(penalty_id="spread", name="Spread", penalty_type=PenaltyType.SCORE))
    registry.register(PenaltyDefinition(penalty_id="size_stale", name="Staleness sizing", penalty_type=PenaltyType.SIZE))
    return registry


def _candidate(
    *,
    engine_id: str,
    pair: str,
    raw_features: dict[str, float],
    expected_ce: float,
    expected_cost: float,
    projected_size: float,
    projected_loss: float,
    projected_beta_impact: float,
    cluster_id: str,
    score_penalties: tuple[ScorePenaltyItem, ...] = (),
    size_penalties: tuple[SizePenaltyItem, ...] = (),
    blocker_conditions: BlockerCondition | None = None,
    corr_penalty: float = 0.0,
    risk_penalty: float = 0.0,
) -> ScoringCandidateInput:
    return ScoringCandidateInput(
        engine_id=engine_id,
        pair=pair,
        raw_features=raw_features,
        allowed_features=frozenset({"momentum", "flow"}),
        weights={"momentum": 2.0, "flow": 1.0},
        scoring_version="5.0",
        score_penalties=score_penalties,
        size_penalties=size_penalties,
        blocker_conditions=blocker_conditions or BlockerCondition(),
        expected_cost=expected_cost,
        expected_ce=expected_ce,
        projected_size=projected_size,
        projected_loss=projected_loss,
        projected_beta_impact=projected_beta_impact,
        cluster_id=cluster_id,
        corr_penalty=corr_penalty,
        risk_penalty=risk_penalty,
    )


class TestScoringRuntime:
    def test_runtime_distinguishes_penalty_from_relative_ranking_rejection(self):
        runtime = ScoringRuntime(_registry())
        portfolio = PortfolioState(
            remaining_gross_capacity=1000.0,
            remaining_loss_capacity=100.0,
            remaining_beta_capacity=1.0,
            remaining_cluster_capacity={"majors": 500.0},
        )
        result = runtime.run_round(
            (
                _candidate(
                    engine_id="eng_a",
                    pair="BTCUSDT",
                    raw_features={"momentum": 1.2, "flow": 0.8, "forbidden": 9.0},
                    expected_ce=0.1,
                    expected_cost=0.2,
                    projected_size=50.0,
                    projected_loss=5.0,
                    projected_beta_impact=0.05,
                    cluster_id="majors",
                    score_penalties=(
                        ScorePenaltyItem(penalty_id="stale", value=2.8, reason="data stale"),
                        ScorePenaltyItem(penalty_id="spread", value=0.1, reason="wide spread"),
                    ),
                    size_penalties=(SizePenaltyItem(penalty_id="size_stale", multiplier=0.1, reason="stale sizing"),),
                ),
                _candidate(
                    engine_id="eng_b",
                    pair="ETHUSDT",
                    raw_features={"momentum": 1.3, "flow": 1.0},
                    expected_ce=0.2,
                    expected_cost=0.1,
                    projected_size=50.0,
                    projected_loss=5.0,
                    projected_beta_impact=0.05,
                    cluster_id="majors",
                ),
            ),
            portfolio=portfolio,
            max_selections=1,
            now=10.0,
        )
        btc = next(audit for audit in result.audits if audit.pair == "BTCUSDT")
        eth = next(audit for audit in result.audits if audit.pair == "ETHUSDT")
        assert btc.is_phantom is True
        assert btc.hard_block_decision.is_blocked is False
        assert btc.selection_entry is not None
        assert btc.selection_entry.outcome == SelectionOutcome.REJECTED_RANKING
        assert eth.selection_entry is not None
        assert eth.selection_entry.outcome == SelectionOutcome.SELECTED

    def test_runtime_explicit_hard_block_never_reaches_ranking(self):
        runtime = ScoringRuntime(_registry())
        result = runtime.run_round(
            (
                _candidate(
                    engine_id="eng_a",
                    pair="BTCUSDT",
                    raw_features={"momentum": 1.0, "flow": 1.0},
                    expected_ce=0.2,
                    expected_cost=0.1,
                    projected_size=10.0,
                    projected_loss=1.0,
                    projected_beta_impact=0.01,
                    cluster_id="majors",
                    blocker_conditions=BlockerCondition(is_pair_suspended=True),
                ),
            ),
            portfolio=PortfolioState(
                remaining_gross_capacity=100.0,
                remaining_loss_capacity=100.0,
                remaining_beta_capacity=1.0,
                remaining_cluster_capacity={"majors": 100.0},
            ),
            max_selections=1,
            now=20.0,
        )
        audit = result.audits[0]
        assert audit.hard_block_decision.is_blocked is True
        assert audit.selection_entry is None
        assert result.candidate_pool.pool_size == 0

    def test_runtime_respects_portfolio_rejection_without_hiding_it_as_hard_block(self):
        runtime = ScoringRuntime(_registry())
        result = runtime.run_round(
            (
                _candidate(
                    engine_id="eng_a",
                    pair="BTCUSDT",
                    raw_features={"momentum": 1.1, "flow": 0.9},
                    expected_ce=0.2,
                    expected_cost=0.05,
                    projected_size=150.0,
                    projected_loss=10.0,
                    projected_beta_impact=0.05,
                    cluster_id="majors",
                ),
            ),
            portfolio=PortfolioState(
                remaining_gross_capacity=100.0,
                remaining_loss_capacity=100.0,
                remaining_beta_capacity=1.0,
                remaining_cluster_capacity={"majors": 100.0},
            ),
            max_selections=1,
            now=30.0,
        )
        audit = result.audits[0]
        assert audit.hard_block_decision.is_blocked is False
        assert audit.portfolio_result is not None
        assert audit.portfolio_result.verdict.value == "rejected_exposure"
        assert audit.selection_entry is not None
        assert audit.selection_entry.outcome == SelectionOutcome.REJECTED_PORTFOLIO

    def test_runtime_is_reproducible_for_identical_round_inputs(self):
        candidates = (
            _candidate(
                engine_id="eng_a",
                pair="BTCUSDT",
                raw_features={"momentum": 1.2, "flow": 0.8},
                expected_ce=0.2,
                expected_cost=0.05,
                projected_size=20.0,
                projected_loss=2.0,
                projected_beta_impact=0.02,
                cluster_id="majors",
            ),
            _candidate(
                engine_id="eng_b",
                pair="ETHUSDT",
                raw_features={"momentum": 0.8, "flow": 0.7},
                expected_ce=0.15,
                expected_cost=0.07,
                projected_size=20.0,
                projected_loss=2.0,
                projected_beta_impact=0.02,
                cluster_id="alts",
            ),
        )
        portfolio = PortfolioState(
            remaining_gross_capacity=1000.0,
            remaining_loss_capacity=100.0,
            remaining_beta_capacity=1.0,
            remaining_cluster_capacity={"majors": 500.0, "alts": 500.0},
        )
        result_a = ScoringRuntime(_registry()).run_round(candidates, portfolio=portfolio, max_selections=1, now=40.0)
        result_b = ScoringRuntime(_registry()).run_round(candidates, portfolio=portfolio, max_selections=1, now=40.0)

        assert result_a.selection_result.entries == result_b.selection_result.entries
        assert tuple((audit.pair, audit.score_payload.raw_score) for audit in result_a.audits) == tuple(
            (audit.pair, audit.score_payload.raw_score) for audit in result_b.audits
        )
