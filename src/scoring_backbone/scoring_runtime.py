"""
Build-5 / scoring_backbone / scoring_runtime
Drive a reproducible full scoring round across raw score, penalties, hard
blocking and ranking selection.
"""

from __future__ import annotations

from dataclasses import dataclass

from .hard_block_gate.blocker_decision_builder import build_decision
from .hard_block_gate.blocker_evaluator import evaluate_blockers
from .hard_block_gate.blocker_reason_encoder import encode_reasons
from .hard_block_gate.blocker_reporter import BlockerReporter
from .penalty_aggregator.penalty_cap_guard import PenaltyCapVerdict, evaluate_penalty_cap
from .penalty_aggregator.penalty_registry import PenaltyRegistry
from .penalty_aggregator.penalty_reporter import PenaltyEvent, PenaltyReporter
from .penalty_aggregator.score_penalty_builder import build_score_penalty
from .penalty_aggregator.size_penalty_builder import build_size_penalty
from .ranking_router.candidate_pool_builder import RankingCandidate, build_candidate_pool
from .ranking_router.portfolio_compatibility_checker import CompatibilityResult, PortfolioState, check_portfolio_compatibility
from .ranking_router.ranking_reporter import RankingEvent, RankingReporter
from .ranking_router.ranking_score_builder import RankingWeights, compute_ranking_scores
from .ranking_router.selection_resolver import SelectionResult, resolve_selection
from .raw_score_builder.feature_selector import select_features
from .raw_score_builder.raw_score_calculator import calculate_raw_score
from .raw_score_builder.score_reporter import ScoreReporter
from .scoring_runtime_support import (
    ScoringCandidateAudit,
    ScoringCandidateInput,
    ScoringPhysicsProjection,
    ScoringRoundResult,
    ScoringSoftPenaltyLayerHook,
    ScoringSoftPenaltyLayerInput,
    ScoringSoftPenaltyLayerOutcome,
    apply_soft_penalty_hook,
    build_candidate_index,
    build_economics_projection,
    build_explainability,
    build_physics_projection,
    build_scoring_soft_penalty_hook_input,
    get_candidate,
    get_physics_projection,
    require_runtime_timestamp,
)


@dataclass(frozen=True)
class _CandidateRoundState:
    key: tuple[str, str]
    adjusted_candidate: ScoringCandidateInput
    physics_projection: ScoringPhysicsProjection
    hook_outcome: ScoringSoftPenaltyLayerOutcome | None
    audit: ScoringCandidateAudit
    ranking_candidate: RankingCandidate | None
    blocked: bool


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
        soft_penalty_hook: ScoringSoftPenaltyLayerHook | None = None,
    ) -> None:
        self._penalty_registry = penalty_registry
        self._ranking_weights = ranking_weights or RankingWeights()
        self._max_score_penalty = max_score_penalty
        self._min_size_multiplier = min_size_multiplier
        self._soft_penalty_hook = soft_penalty_hook
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
        now: float | None = None,
    ) -> ScoringRoundResult:
        """Run a complete Build-5 scoring round."""
        timestamp = require_runtime_timestamp(now, context="ScoringRuntime.run_round")
        candidate_index = build_candidate_index(candidates)
        audits_by_key: dict[tuple[str, str], ScoringCandidateAudit] = {}
        physics_projection_by_key: dict[tuple[str, str], ScoringPhysicsProjection] = {}
        hook_outcomes_by_key: dict[tuple[str, str], ScoringSoftPenaltyLayerOutcome | None] = {}
        ranking_candidates: list[RankingCandidate] = []
        blocked_keys: set[tuple[str, str]] = set()
        for candidate in candidates:
            candidate_state = self._evaluate_candidate_for_round(candidate, timestamp=timestamp)
            physics_projection_by_key[candidate_state.key] = candidate_state.physics_projection
            hook_outcomes_by_key[candidate_state.key] = candidate_state.hook_outcome
            candidate_index[candidate_state.key] = candidate_state.adjusted_candidate
            audits_by_key[candidate_state.key] = candidate_state.audit
            if candidate_state.blocked:
                blocked_keys.add(candidate_state.key)
            elif candidate_state.ranking_candidate is not None:
                ranking_candidates.append(candidate_state.ranking_candidate)
        candidate_pool = build_candidate_pool(tuple(ranking_candidates), blocked_keys=frozenset(blocked_keys))
        portfolio_results, portfolio_rejected_keys = self._evaluate_portfolio_compatibility(
            candidate_pool,
            candidate_index=candidate_index,
            portfolio=portfolio,
        )
        selection_result = self._resolve_selection_result(
            candidate_pool,
            candidate_index=candidate_index,
            portfolio_rejected_keys=portfolio_rejected_keys,
            max_selections=max_selections,
            timestamp=timestamp,
        )
        audits = self._reconcile_round_audits(
            audits_by_key,
            candidate_index=candidate_index,
            physics_projection_by_key=physics_projection_by_key,
            hook_outcomes_by_key=hook_outcomes_by_key,
            portfolio_results=portfolio_results,
            selection_result=selection_result,
        )
        return ScoringRoundResult(
            audits=tuple(audits),
            candidate_pool=candidate_pool,
            selection_result=selection_result,
            score_stats=self._score_reporter.get_stats(),
            penalty_stats=self._penalty_reporter.get_stats(),
            blocker_stats=self._blocker_reporter.get_stats(),
            ranking_stats=self._ranking_reporter.get_stats(),
        )

    def _evaluate_candidate_for_round(
        self,
        candidate: ScoringCandidateInput,
        *,
        timestamp: float,
    ) -> _CandidateRoundState:
        key = (candidate.engine_id, candidate.pair)
        physics_projection = build_physics_projection(candidate)
        hook_outcome = self._run_soft_penalty_hook(candidate, physics_projection)
        adjusted_candidate = apply_soft_penalty_hook(candidate, hook_outcome)
        feature_selection = select_features(
            engine_id=adjusted_candidate.engine_id,
            raw_features=adjusted_candidate.raw_features,
            allowed_features=adjusted_candidate.allowed_features,
        )
        raw_score_result = calculate_raw_score(
            engine_id=adjusted_candidate.engine_id,
            pair=adjusted_candidate.pair,
            features=feature_selection.selected,
            weights=adjusted_candidate.weights,
            scoring_version=adjusted_candidate.scoring_version,
            raw_score_multiplier=adjusted_candidate.raw_score_multiplier,
            raw_score_add=adjusted_candidate.raw_score_add,
            raw_score_cap=adjusted_candidate.raw_score_cap,
        )
        score_payload = self._score_reporter.evaluate(
            engine_id=adjusted_candidate.engine_id,
            pair=adjusted_candidate.pair,
            raw_score=raw_score_result.raw_score,
            block_scores=raw_score_result.weighted_contributions,
            features_used=raw_score_result.features_used,
            scoring_version=raw_score_result.scoring_version,
        )
        score_penalty_result = build_score_penalty(raw_score=raw_score_result.raw_score, penalties=adjusted_candidate.score_penalties, registry=self._penalty_registry)
        size_penalty_result = build_size_penalty(penalties=adjusted_candidate.size_penalties, registry=self._penalty_registry)
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
                engine_id=adjusted_candidate.engine_id,
                pair=adjusted_candidate.pair,
                score_penalty=penalty_cap_result.capped_score_penalty,
                size_multiplier=penalty_cap_result.capped_size_multiplier,
                is_phantom=penalty_cap_result.verdict == PenaltyCapVerdict.PHANTOM_RISK,
                is_capped=penalty_cap_result.verdict == PenaltyCapVerdict.CAPPED,
                timestamp=timestamp,
            ),
        )
        blocker_evaluations = evaluate_blockers(adjusted_candidate.blocker_conditions)
        triggered = tuple(
            (evaluation.blocker_id, evaluation.reason)
            for evaluation in blocker_evaluations
            if evaluation.triggered
        )
        encoded = encode_reasons(triggered)
        hard_block_decision = build_decision(adjusted_candidate.pair, adjusted_candidate.engine_id, encoded)
        ranking_candidate = None
        if hard_block_decision.is_blocked:
            self._blocker_reporter.record_blocked(tuple(reason.code for reason in encoded))
        else:
            self._blocker_reporter.record_passed()
            ranking_candidate = RankingCandidate(
                engine_id=adjusted_candidate.engine_id,
                pair=adjusted_candidate.pair,
                penalized_score=raw_score_result.raw_score - penalty_cap_result.capped_score_penalty,
                size_multiplier=penalty_cap_result.capped_size_multiplier,
                expected_cost=adjusted_candidate.expected_cost,
                expected_ce=adjusted_candidate.expected_ce,
                projected_risk=adjusted_candidate.risk_penalty,
                cluster_id=adjusted_candidate.cluster_id,
            )
        return _CandidateRoundState(
            key=key,
            adjusted_candidate=adjusted_candidate,
            physics_projection=physics_projection,
            hook_outcome=hook_outcome,
            audit=ScoringCandidateAudit(
                engine_id=adjusted_candidate.engine_id,
                pair=adjusted_candidate.pair,
                feature_selection=feature_selection,
                raw_score_result=raw_score_result,
                score_payload=score_payload,
                score_penalty_result=score_penalty_result,
                size_penalty_result=size_penalty_result,
                penalty_cap_result=penalty_cap_result,
                hard_block_decision=hard_block_decision,
                is_phantom=penalty_cap_result.verdict == PenaltyCapVerdict.PHANTOM_RISK,
                explainability=build_explainability(
                    candidate=adjusted_candidate,
                    raw_score_result=raw_score_result,
                    score_penalty_result=score_penalty_result,
                    size_penalty_result=size_penalty_result,
                    hard_block_decision=hard_block_decision,
                    hook_outcome=hook_outcome,
                    physics_projection=physics_projection,
                ),
                economics=build_economics_projection(
                    candidate=adjusted_candidate,
                    raw_score_result=raw_score_result,
                    penalty_cap_result=penalty_cap_result,
                    hard_block_decision=hard_block_decision,
                    hook_outcome=hook_outcome,
                    physics_projection=physics_projection,
                ),
            ),
            ranking_candidate=ranking_candidate,
            blocked=hard_block_decision.is_blocked,
        )

    def _evaluate_portfolio_compatibility(
        self,
        candidate_pool: object,
        *,
        candidate_index: dict[tuple[str, str], ScoringCandidateInput],
        portfolio: PortfolioState,
    ) -> tuple[dict[tuple[str, str], CompatibilityResult], frozenset[tuple[str, str]]]:
        portfolio_results: dict[tuple[str, str], CompatibilityResult] = {}
        portfolio_rejected_keys: set[tuple[str, str]] = set()
        for pool_candidate in candidate_pool.candidates:
            key = (pool_candidate.engine_id, pool_candidate.pair)
            source = get_candidate(candidate_index, key, context="ScoringRuntime.run_round candidate pool")
            compatibility = check_portfolio_compatibility(
                engine_id=pool_candidate.engine_id,
                pair=pool_candidate.pair,
                projected_size=source.projected_size * pool_candidate.size_multiplier,
                projected_loss=source.projected_loss,
                projected_beta_impact=source.projected_beta_impact,
                cluster_id=pool_candidate.cluster_id,
                portfolio=portfolio,
            )
            portfolio_results[key] = compatibility
            if compatibility.verdict != "compatible":
                portfolio_rejected_keys.add(key)
        return portfolio_results, frozenset(portfolio_rejected_keys)

    def _resolve_selection_result(
        self,
        candidate_pool: object,
        *,
        candidate_index: dict[tuple[str, str], ScoringCandidateInput],
        portfolio_rejected_keys: frozenset[tuple[str, str]],
        max_selections: int,
        timestamp: float,
    ) -> SelectionResult:
        ranking_inputs = tuple(
            {
                "engine_id": pool_candidate.engine_id,
                "pair": pool_candidate.pair,
                "penalized_score": pool_candidate.penalized_score,
                "expected_ce": pool_candidate.expected_ce,
                "expected_cost": pool_candidate.expected_cost,
                "corr_penalty": get_candidate(
                    candidate_index,
                    (pool_candidate.engine_id, pool_candidate.pair),
                    context="ScoringRuntime.run_round ranking inputs",
                ).corr_penalty,
                "risk_penalty": get_candidate(
                    candidate_index,
                    (pool_candidate.engine_id, pool_candidate.pair),
                    context="ScoringRuntime.run_round ranking inputs",
                ).risk_penalty,
            }
            for pool_candidate in candidate_pool.candidates
        )
        ranked = compute_ranking_scores(ranking_inputs, self._ranking_weights)
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
            portfolio_rejected_keys=portfolio_rejected_keys,
        )
        self._ranking_reporter.record(
            RankingEvent(
                pool_size=candidate_pool.pool_size,
                selected_count=selection_result.selected_count,
                rejected_by_ranking=selection_result.rejected_by_ranking,
                rejected_by_portfolio=selection_result.rejected_by_portfolio,
                version=self._ranking_weights.version,
                timestamp=timestamp,
            ),
        )
        return selection_result

    def _reconcile_round_audits(
        self,
        audits_by_key: dict[tuple[str, str], ScoringCandidateAudit],
        *,
        candidate_index: dict[tuple[str, str], ScoringCandidateInput],
        physics_projection_by_key: dict[tuple[str, str], ScoringPhysicsProjection],
        hook_outcomes_by_key: dict[tuple[str, str], ScoringSoftPenaltyLayerOutcome | None],
        portfolio_results: dict[tuple[str, str], CompatibilityResult],
        selection_result: SelectionResult,
    ) -> list[ScoringCandidateAudit]:
        selection_by_key = {(entry.engine_id, entry.pair): entry for entry in selection_result.entries}
        audits: list[ScoringCandidateAudit] = []
        for key, audit in audits_by_key.items():
            source = get_candidate(candidate_index, key, context="ScoringRuntime.run_round audit reconciliation")
            physics_projection = get_physics_projection(
                physics_projection_by_key,
                key,
                context="ScoringRuntime.run_round audit reconciliation",
            )
            hook_outcome = hook_outcomes_by_key.get(key)
            portfolio_result = portfolio_results.get(key)
            selection_entry = selection_by_key.get(key)
            audits.append(
                audit.model_copy(
                    update={
                        "portfolio_result": portfolio_result,
                        "selection_entry": selection_entry,
                        "explainability": build_explainability(
                            candidate=source,
                            raw_score_result=audit.raw_score_result,
                            score_penalty_result=audit.score_penalty_result,
                            size_penalty_result=audit.size_penalty_result,
                            hard_block_decision=audit.hard_block_decision,
                            hook_outcome=hook_outcome,
                            portfolio_result=portfolio_result,
                            selection_entry=selection_entry,
                            physics_projection=physics_projection,
                        ),
                        "economics": build_economics_projection(
                            candidate=source,
                            raw_score_result=audit.raw_score_result,
                            penalty_cap_result=audit.penalty_cap_result,
                            hard_block_decision=audit.hard_block_decision,
                            hook_outcome=hook_outcome,
                            portfolio_result=portfolio_result,
                            selection_entry=selection_entry,
                            physics_projection=physics_projection,
                        ),
                    },
                )
            )
        audits.sort(key=lambda audit: (audit.engine_id, audit.pair))
        return audits

    def _run_soft_penalty_hook(
        self,
        candidate: ScoringCandidateInput,
        physics_projection: ScoringPhysicsProjection,
    ) -> ScoringSoftPenaltyLayerOutcome | None:
        if self._soft_penalty_hook is None:
            return None
        return self._soft_penalty_hook(
            build_scoring_soft_penalty_hook_input(candidate, physics_projection)
        )
