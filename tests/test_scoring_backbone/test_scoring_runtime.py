"""Runtime tests for Build-5 scoring backbone."""

import pytest

import scoring_backbone.scoring_runtime as scoring_runtime_module
from scoring_backbone import ScoringCandidateInput, ScoringRuntime
from scoring_backbone.hard_block_gate.blocker_evaluator import BlockerCondition
from scoring_backbone.penalty_aggregator.penalty_registry import PenaltyDefinition, PenaltyRegistry, PenaltyType
from scoring_backbone.ranking_router.candidate_pool_builder import CandidatePool, RankingCandidate
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
    execution_fragility: float = 0.0,
    market_toxicity: float = 0.0,
    spread_regime_penalty: float = 0.0,
    participation_penalty: float = 0.0,
    scoring_version: str = "5.0",
) -> ScoringCandidateInput:
    return ScoringCandidateInput(
        engine_id=engine_id,
        pair=pair,
        raw_features=raw_features,
        allowed_features=frozenset({"momentum", "flow"}),
        weights={"momentum": 2.0, "flow": 1.0},
        scoring_version=scoring_version,
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
        execution_fragility=execution_fragility,
        market_toxicity=market_toxicity,
        spread_regime_penalty=spread_regime_penalty,
        participation_penalty=participation_penalty,
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
        assert btc.explainability.dominant_feature_keys == ("momentum", "flow")
        assert btc.explainability.dominant_score_penalty_ids == ("stale", "spread")
        assert btc.explainability.dominant_size_penalty_ids == ("size_stale",)
        assert btc.explainability.selection_outcome_code == "rejected_ranking"
        assert "selection=rejected_ranking" in btc.explainability.summary
        assert "cost=0.2000" in btc.explainability.summary
        assert "ce=0.1000" in btc.explainability.summary
        assert btc.economics.expected_cost == pytest.approx(0.2)
        assert btc.economics.expected_ce == pytest.approx(0.1)
        assert btc.economics.penalized_score == pytest.approx(0.3)
        assert btc.economics.final_size_multiplier == pytest.approx(0.1)
        assert btc.economics.phantom_trade is True
        assert btc.economics.phantom_reason_code == "PHANTOM_RISK"
        assert btc.economics.selection_outcome_code == "rejected_ranking"
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
        assert audit.explainability.hard_block_codes == ("HB_PAIR_SUSPENDED",)
        assert "hard_block=HB_PAIR_SUSPENDED" in audit.explainability.summary
        assert audit.economics.hard_blocked is True
        assert audit.economics.selection_outcome_code == ""
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
        assert audit.explainability.portfolio_verdict_code == "rejected_exposure"
        assert audit.explainability.selection_outcome_code == "rejected_portfolio"
        assert audit.economics.portfolio_verdict_code == "rejected_exposure"
        assert audit.economics.selection_outcome_code == "rejected_portfolio"
        assert audit.economics.ranking_score is not None

    def test_runtime_projects_market_physics_scores_without_changing_selection_logic(self):
        runtime = ScoringRuntime(_registry())
        result = runtime.run_round(
            (
                _candidate(
                    engine_id="eng_a",
                    pair="BTCUSDT",
                    raw_features={"momentum": 1.1, "flow": 0.9},
                    expected_ce=0.2,
                    expected_cost=0.05,
                    projected_size=50.0,
                    projected_loss=5.0,
                    projected_beta_impact=0.05,
                    cluster_id="majors",
                    execution_fragility=0.8,
                    market_toxicity=0.8,
                    spread_regime_penalty=0.6,
                ),
            ),
            portfolio=PortfolioState(
                remaining_gross_capacity=1000.0,
                remaining_loss_capacity=100.0,
                remaining_beta_capacity=1.0,
                remaining_cluster_capacity={"majors": 500.0},
            ),
            max_selections=1,
            now=35.0,
        )
        audit = result.audits[0]
        assert audit.selection_entry is not None
        assert audit.selection_entry.outcome == SelectionOutcome.SELECTED
        assert audit.explainability.physics_pressure_state == "elevated"
        assert "physics=elevated" in audit.explainability.summary
        assert audit.economics.physics_pressure_state == "elevated"
        assert audit.economics.execution_survivability_score < 1.0
        assert audit.economics.micro_friction_score > 0.0

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

    def test_runtime_requires_explicit_now(self):
        runtime = ScoringRuntime(_registry())

        with pytest.raises(ValueError, match="requires explicit now"):
            runtime.run_round(
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
                    ),
                ),
                portfolio=PortfolioState(
                    remaining_gross_capacity=100.0,
                    remaining_loss_capacity=100.0,
                    remaining_beta_capacity=1.0,
                    remaining_cluster_capacity={"majors": 100.0},
                ),
                max_selections=1,
            )

    def test_runtime_rejects_blank_scoring_version_candidate(self):
        with pytest.raises(ValueError, match="scoring_version must be non-empty"):
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
                scoring_version="   ",
            )

    def test_runtime_rejects_duplicate_candidate_keys(self):
        runtime = ScoringRuntime(_registry())
        candidate = _candidate(
            engine_id="eng_a",
            pair="BTCUSDT",
            raw_features={"momentum": 1.0, "flow": 1.0},
            expected_ce=0.2,
            expected_cost=0.1,
            projected_size=10.0,
            projected_loss=1.0,
            projected_beta_impact=0.01,
            cluster_id="majors",
        )

        with pytest.raises(ValueError, match="duplicate candidate key eng_a:BTCUSDT"):
            runtime.run_round(
                (candidate, candidate),
                portfolio=PortfolioState(
                    remaining_gross_capacity=100.0,
                    remaining_loss_capacity=100.0,
                    remaining_beta_capacity=1.0,
                    remaining_cluster_capacity={"majors": 100.0},
                ),
                max_selections=1,
                now=50.0,
            )

    def test_runtime_fails_explicitly_on_candidate_pool_desync(self, monkeypatch):
        runtime = ScoringRuntime(_registry())

        def _broken_build_candidate_pool(
            all_candidates: tuple[RankingCandidate, ...],
            blocked_keys: frozenset[tuple[str, str]],
        ) -> CandidatePool:
            return CandidatePool(
                candidates=(
                    RankingCandidate(
                        engine_id="ghost_engine",
                        pair="BTCUSDT",
                        penalized_score=1.0,
                        size_multiplier=1.0,
                        expected_cost=0.1,
                        expected_ce=0.2,
                        projected_risk=0.0,
                        cluster_id="majors",
                    ),
                ),
                total_submitted=len(all_candidates),
                hard_blocked=0,
            )

        monkeypatch.setattr(scoring_runtime_module, "build_candidate_pool", _broken_build_candidate_pool)

        with pytest.raises(
            ValueError,
            match="ScoringRuntime.run_round candidate pool references unknown candidate ghost_engine:BTCUSDT",
        ):
            runtime.run_round(
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
                    ),
                ),
                portfolio=PortfolioState(
                    remaining_gross_capacity=100.0,
                    remaining_loss_capacity=100.0,
                    remaining_beta_capacity=1.0,
                    remaining_cluster_capacity={"majors": 100.0},
                ),
                max_selections=1,
                now=60.0,
            )
