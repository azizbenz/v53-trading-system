"""
Build-5 / scoring_backbone / scoring_runtime
Drive a reproducible full scoring round across raw score, penalties, hard
blocking and ranking selection.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from .hard_block_gate.blocker_decision_builder import HardBlockDecision, build_decision
from .hard_block_gate.blocker_evaluator import BlockerCondition, evaluate_blockers
from .hard_block_gate.blocker_reason_encoder import encode_reasons
from .hard_block_gate.blocker_reporter import BlockerReporter, BlockerStats
from .penalty_aggregator.penalty_cap_guard import PenaltyCapResult, PenaltyCapVerdict, evaluate_penalty_cap
from .penalty_aggregator.penalty_registry import PenaltyRegistry
from .penalty_aggregator.penalty_reporter import PenaltyEvent, PenaltyReporter, PenaltyStats
from .penalty_aggregator.score_penalty_builder import ScorePenaltyItem, ScorePenaltyResult, build_score_penalty
from .penalty_aggregator.size_penalty_builder import SizePenaltyItem, SizePenaltyResult, build_size_penalty
from .ranking_router.candidate_pool_builder import CandidatePool, RankingCandidate, build_candidate_pool
from .ranking_router.portfolio_compatibility_checker import CompatibilityResult, PortfolioState, check_portfolio_compatibility
from .ranking_router.ranking_reporter import RankingEvent, RankingReporter, RankingStats
from .ranking_router.ranking_score_builder import RankedCandidate, RankingWeights, compute_ranking_scores
from .ranking_router.selection_resolver import SelectionEntry, SelectionResult, resolve_selection
from .raw_score_builder.feature_selector import FeatureSelection, select_features
from .raw_score_builder.raw_score_calculator import RawScoreResult, calculate_raw_score
from .raw_score_builder.score_reporter import ScorePayload, ScoreReporter, ScoreStats


class ScoringCandidateInput(BaseModel, frozen=True):
    engine_id: str
    pair: str
    raw_features: dict[str, float]
    allowed_features: frozenset[str]
    weights: dict[str, float]
    scoring_version: str
    score_penalties: tuple[ScorePenaltyItem, ...] = ()
    size_penalties: tuple[SizePenaltyItem, ...] = ()
    blocker_conditions: BlockerCondition = Field(default_factory=BlockerCondition)
    expected_cost: float = 0.0
    expected_ce: float = 0.0
    projected_size: float = 0.0
    projected_loss: float = 0.0
    projected_beta_impact: float = 0.0
    cluster_id: str = ""
    corr_penalty: float = 0.0
    risk_penalty: float = 0.0


class ScoringCandidateAudit(BaseModel, frozen=True):
    engine_id: str
    pair: str
    feature_selection: FeatureSelection
    raw_score_result: RawScoreResult
    score_payload: ScorePayload
    score_penalty_result: ScorePenaltyResult
    size_penalty_result: SizePenaltyResult
    penalty_cap_result: PenaltyCapResult
    hard_block_decision: HardBlockDecision
    portfolio_result: CompatibilityResult | None = None
    selection_entry: SelectionEntry | None = None
    is_phantom: bool = False


class ScoringRoundResult(BaseModel, frozen=True):
    audits: tuple[ScoringCandidateAudit, ...]
    candidate_pool: CandidatePool
    selection_result: SelectionResult
    score_stats: ScoreStats
    penalty_stats: PenaltyStats
    blocker_stats: BlockerStats
    ranking_stats: RankingStats


class ScoringRuntime:
    """Stateful Build-5 runtime for complete scoring rounds."""

    def __init__(
        self,
        penalty_registry: PenaltyRegistry,
        *,
        ranking_weights: RankingWeights | None = None,
        max_score_penalty: float = 3.0,
        min_size_multiplier: float = 0.05,
        anomaly_low: float = -10.0,
        anomaly_high: float = 10.0,
    ) -> None:
        self._penalty_registry = penalty_registry
        self._ranking_weights = ranking_weights or RankingWeights()
        self._max_score_penalty = max_score_penalty
        self._min_size_multiplier = min_size_multiplier
        self._score_reporter = ScoreReporter(anomaly_low=anomaly_low, anomaly_high=anomaly_high)
        self._penalty_reporter = PenaltyReporter()
        self._blocker_reporter = BlockerReporter()
        self._ranking_reporter = RankingReporter()

    def run_round(
        self,
        candidates: tuple[ScoringCandidateInput, ...],
        *,
        portfolio: PortfolioState,
        max_selections: int,
        now: float = 0.0,
    ) -> ScoringRoundResult:
        """Run a complete Build-5 scoring round."""
        audits_by_key: dict[tuple[str, str], ScoringCandidateAudit] = {}
        ranking_candidates: list[RankingCandidate] = []
        blocked_keys: set[tuple[str, str]] = set()
        portfolio_results: dict[tuple[str, str], CompatibilityResult] = {}

        for candidate in candidates:
            feature_selection = select_features(
                engine_id=candidate.engine_id,
                raw_features=candidate.raw_features,
                allowed_features=candidate.allowed_features,
            )
            raw_score_result = calculate_raw_score(
                engine_id=candidate.engine_id,
                pair=candidate.pair,
                features=feature_selection.selected,
                weights=candidate.weights,
                scoring_version=candidate.scoring_version,
            )
            score_payload = self._score_reporter.evaluate(
                engine_id=candidate.engine_id,
                pair=candidate.pair,
                raw_score=raw_score_result.raw_score,
                block_scores=raw_score_result.weighted_contributions,
                features_used=raw_score_result.features_used,
                scoring_version=raw_score_result.scoring_version,
            )
            score_penalty_result = build_score_penalty(
                raw_score=raw_score_result.raw_score,
                penalties=candidate.score_penalties,
                registry=self._penalty_registry,
            )
            size_penalty_result = build_size_penalty(
                penalties=candidate.size_penalties,
                registry=self._penalty_registry,
            )
            penalty_cap_result = evaluate_penalty_cap(
                score_penalty=score_penalty_result.total_penalty,
                size_multiplier=size_penalty_result.total_multiplier,
                max_score_penalty=self._max_score_penalty,
                min_size_multiplier=self._min_size_multiplier,
                raw_score=raw_score_result.raw_score,
                expected_cost=candidate.expected_cost,
            )
            self._penalty_reporter.record(
                PenaltyEvent(
                    engine_id=candidate.engine_id,
                    pair=candidate.pair,
                    score_penalty=penalty_cap_result.capped_score_penalty,
                    size_multiplier=penalty_cap_result.capped_size_multiplier,
                    is_phantom=penalty_cap_result.verdict == PenaltyCapVerdict.PHANTOM_RISK,
                    is_capped=penalty_cap_result.verdict == PenaltyCapVerdict.CAPPED,
                    timestamp=now,
                ),
            )

            blocker_evaluations = evaluate_blockers(candidate.blocker_conditions)
            triggered = tuple(
                (evaluation.blocker_id, evaluation.reason)
                for evaluation in blocker_evaluations
                if evaluation.triggered
            )
            encoded = encode_reasons(triggered)
            hard_block_decision = build_decision(candidate.pair, candidate.engine_id, encoded)
            key = (candidate.engine_id, candidate.pair)

            if hard_block_decision.is_blocked:
                blocked_keys.add(key)
                self._blocker_reporter.record_blocked(tuple(reason.code for reason in encoded))
            else:
                self._blocker_reporter.record_passed()
                ranking_candidates.append(
                    RankingCandidate(
                        engine_id=candidate.engine_id,
                        pair=candidate.pair,
                        penalized_score=raw_score_result.raw_score - penalty_cap_result.capped_score_penalty,
                        size_multiplier=penalty_cap_result.capped_size_multiplier,
                        expected_cost=candidate.expected_cost,
                        expected_ce=candidate.expected_ce,
                        projected_risk=candidate.risk_penalty,
                        cluster_id=candidate.cluster_id,
                    ),
                )

            audits_by_key[key] = ScoringCandidateAudit(
                engine_id=candidate.engine_id,
                pair=candidate.pair,
                feature_selection=feature_selection,
                raw_score_result=raw_score_result,
                score_payload=score_payload,
                score_penalty_result=score_penalty_result,
                size_penalty_result=size_penalty_result,
                penalty_cap_result=penalty_cap_result,
                hard_block_decision=hard_block_decision,
                is_phantom=penalty_cap_result.verdict == PenaltyCapVerdict.PHANTOM_RISK,
            )

        candidate_pool = build_candidate_pool(tuple(ranking_candidates), blocked_keys=frozenset(blocked_keys))

        portfolio_rejected_keys: set[tuple[str, str]] = set()
        for pool_candidate in candidate_pool.candidates:
            source = next(
                candidate
                for candidate in candidates
                if candidate.engine_id == pool_candidate.engine_id and candidate.pair == pool_candidate.pair
            )
            compatibility = check_portfolio_compatibility(
                engine_id=pool_candidate.engine_id,
                pair=pool_candidate.pair,
                projected_size=source.projected_size * pool_candidate.size_multiplier,
                projected_loss=source.projected_loss,
                projected_beta_impact=source.projected_beta_impact,
                cluster_id=pool_candidate.cluster_id,
                portfolio=portfolio,
            )
            portfolio_results[(pool_candidate.engine_id, pool_candidate.pair)] = compatibility
            if compatibility.verdict != "compatible":
                portfolio_rejected_keys.add((pool_candidate.engine_id, pool_candidate.pair))

        ranked = compute_ranking_scores(
            tuple(
                {
                    "engine_id": pool_candidate.engine_id,
                    "pair": pool_candidate.pair,
                    "penalized_score": pool_candidate.penalized_score,
                    "expected_ce": pool_candidate.expected_ce,
                    "expected_cost": pool_candidate.expected_cost,
                    "corr_penalty": next(
                        candidate.corr_penalty
                        for candidate in candidates
                        if candidate.engine_id == pool_candidate.engine_id and candidate.pair == pool_candidate.pair
                    ),
                    "risk_penalty": next(
                        candidate.risk_penalty
                        for candidate in candidates
                        if candidate.engine_id == pool_candidate.engine_id and candidate.pair == pool_candidate.pair
                    ),
                }
                for pool_candidate in candidate_pool.candidates
            ),
            self._ranking_weights,
        )
        selection_result = resolve_selection(
            tuple(
                {
                    "engine_id": candidate.engine_id,
                    "pair": candidate.pair,
                    "ranking_score": candidate.ranking_score,
                    "rank": candidate.rank,
                }
                for candidate in ranked
            ),
            max_selections=max_selections,
            portfolio_rejected_keys=frozenset(portfolio_rejected_keys),
        )
        self._ranking_reporter.record(
            RankingEvent(
                pool_size=candidate_pool.pool_size,
                selected_count=selection_result.selected_count,
                rejected_by_ranking=selection_result.rejected_by_ranking,
                rejected_by_portfolio=selection_result.rejected_by_portfolio,
                version=self._ranking_weights.version,
                timestamp=now,
            ),
        )

        selection_by_key = {(entry.engine_id, entry.pair): entry for entry in selection_result.entries}
        audits = []
        for key, audit in audits_by_key.items():
            audits.append(
                audit.model_copy(
                    update={
                        "portfolio_result": portfolio_results.get(key),
                        "selection_entry": selection_by_key.get(key),
                    },
                ),
            )

        audits.sort(key=lambda audit: (audit.engine_id, audit.pair))
        return ScoringRoundResult(
            audits=tuple(audits),
            candidate_pool=candidate_pool,
            selection_result=selection_result,
            score_stats=self._score_reporter.get_stats(),
            penalty_stats=self._penalty_reporter.get_stats(),
            blocker_stats=self._blocker_reporter.get_stats(),
            ranking_stats=self._ranking_reporter.get_stats(),
        )
