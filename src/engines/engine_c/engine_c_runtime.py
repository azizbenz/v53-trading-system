"""Engine C runtime across signal, scoring, ranking and risk."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from interface_contracts import EngineId, RegimeId, Side, SignalCandidate, SignalType
from risk_backbone.risk_runtime import RiskCandidate, RiskEvaluation, RiskRuntime, RiskRuntimeAction
from scoring_backbone.hard_block_gate.blocker_evaluator import BlockerCondition
from scoring_backbone.penalty_aggregator.score_penalty_builder import ScorePenaltyItem
from scoring_backbone.penalty_aggregator.size_penalty_builder import SizePenaltyItem
from scoring_backbone.ranking_router.portfolio_compatibility_checker import PortfolioState
from scoring_backbone.ranking_router.selection_resolver import SelectionOutcome
from scoring_backbone.scoring_runtime import (
    ScoringCandidateAudit,
    ScoringCandidateInput,
    ScoringRoundResult,
    ScoringRuntime,
)

from .engine_c_runner import EngineCInput, EngineCLogEntry, EngineCOutput, run_engine_c


_ENGINE_C_FEATURE_WEIGHTS: dict[str, float] = {
    "breakout": 0.35,
    "continuation": 0.30,
    "context": 0.15,
    "cost_preference": 0.20,
}


class EngineCRuntimeStatus(StrEnum):
    NO_TRADE = "no_trade"
    HARD_BLOCKED = "hard_blocked"
    REJECTED_RANKING = "rejected_ranking"
    REJECTED_PORTFOLIO = "rejected_portfolio"
    RISK_REJECTED = "risk_rejected"
    RISK_REDUCED = "risk_reduced"
    RISK_OBSERVE_ONLY = "risk_observe_only"
    ACCEPTED = "accepted"


class EngineCRuntimeInput(BaseModel, frozen=True):
    engine_inputs: EngineCInput
    timestamp_ms: int
    portfolio: PortfolioState
    projected_size: float
    projected_loss: float | None = None
    current_equity: float
    session_peak_equity: float
    pair_beta: float | None = None
    cluster_id: str
    score_penalties: tuple[ScorePenaltyItem, ...] = ()
    size_penalties: tuple[SizePenaltyItem, ...] = ()
    blocker_conditions: BlockerCondition = Field(default_factory=BlockerCondition)
    peer_candidates: tuple[ScoringCandidateInput, ...] = ()
    max_selections: int = 1
    corr_penalty: float = 0.0
    risk_penalty: float = 0.0


class EngineCRuntimeResult(BaseModel, frozen=True):
    status: EngineCRuntimeStatus
    engine_output: EngineCOutput
    signal_candidate: SignalCandidate | None = None
    scoring_round: ScoringRoundResult | None = None
    scoring_audit: ScoringCandidateAudit | None = None
    risk_evaluation: RiskEvaluation | None = None
    log_entries: tuple[EngineCLogEntry, ...] = ()


def _runtime_log_entry(
    runtime_input: EngineCRuntimeInput,
    engine_output: EngineCOutput,
    **overrides: object,
) -> EngineCLogEntry:
    payload: dict[str, object] = {
        "pair": engine_output.pair,
        "regime": runtime_input.engine_inputs.regime,
        "range_low": engine_output.range_low,
        "range_high": engine_output.range_high,
        "range_width_pct": engine_output.range_width_pct,
        "breakout_type": engine_output.breakout_type,
        "continuation_context": engine_output.continuation_context,
        "distance_to_breakout_pct": engine_output.distance_to_breakout_pct,
        "breakout_score": engine_output.breakout_score,
        "continuation_score": engine_output.continuation_score,
        "fake_breakout_risk": engine_output.fake_breakout_risk,
        "expected_cost": engine_output.expected_cost,
        "ce_expected": engine_output.ce_expected,
        "ev_net": engine_output.ev_net,
        "duplication_possible_with_engine_a": engine_output.duplication_possible_with_engine_a,
        "duplication_overlap_with_engine_a": engine_output.duplication_overlap_with_engine_a,
        "marginal_portfolio_gain": engine_output.marginal_portfolio_gain,
        "covered_share_by_engine_a": engine_output.covered_share_by_engine_a,
        "keff_contribution": engine_output.keff_contribution,
        "conviction": engine_output.conviction.value,
        "tier": engine_output.tier_suggestion.value,
        "holding_hours": engine_output.holding_hours,
        "scoring_version": engine_output.scoring_version,
    }
    payload.update(overrides)
    return EngineCLogEntry(**payload)


class EngineCRuntime:
    def __init__(self, *, scoring_runtime: ScoringRuntime, risk_runtime: RiskRuntime) -> None:
        self._scoring_runtime = scoring_runtime
        self._risk_runtime = risk_runtime

    def evaluate(self, runtime_input: EngineCRuntimeInput, *, now: float = 0.0) -> EngineCRuntimeResult:
        engine_output = run_engine_c(runtime_input.engine_inputs)
        logs = list(engine_output.log_entries)

        if engine_output.decision != "emit":
            return EngineCRuntimeResult(
                status=EngineCRuntimeStatus.NO_TRADE,
                engine_output=engine_output,
                log_entries=tuple(logs),
            )

        signal_candidate = _build_signal_candidate(
            runtime_input.engine_inputs,
            engine_output,
            runtime_input.timestamp_ms,
        )
        scoring_round = self._scoring_runtime.run_round(
            candidates=(_build_scoring_candidate(runtime_input, engine_output), *runtime_input.peer_candidates),
            portfolio=runtime_input.portfolio,
            max_selections=runtime_input.max_selections,
            now=now,
        )
        scoring_audit = next(
            audit
            for audit in scoring_round.audits
            if audit.engine_id == "engine_c" and audit.pair == engine_output.pair
        )
        penalized_score = max(
            0.0,
            scoring_audit.raw_score_result.raw_score - scoring_audit.penalty_cap_result.capped_score_penalty,
        )
        penalty_reasons = tuple(item.penalty_id for item in scoring_audit.score_penalty_result.penalties)
        logs.append(
            _runtime_log_entry(
                runtime_input,
                engine_output,
                event="engine_c_scoring_completed",
                raw_score=scoring_audit.raw_score_result.raw_score,
                penalized_score=penalized_score,
                reasons=penalty_reasons,
            )
        )

        if scoring_audit.hard_block_decision.is_blocked:
            reasons = tuple(reason.human_reason for reason in scoring_audit.hard_block_decision.reasons)
            logs.append(
                _runtime_log_entry(
                    runtime_input,
                    engine_output,
                    event="engine_c_hard_blocked",
                    raw_score=scoring_audit.raw_score_result.raw_score,
                    penalized_score=penalized_score,
                    reasons=reasons,
                )
            )
            return EngineCRuntimeResult(
                status=EngineCRuntimeStatus.HARD_BLOCKED,
                engine_output=engine_output,
                signal_candidate=signal_candidate,
                scoring_round=scoring_round,
                scoring_audit=scoring_audit,
                log_entries=tuple(logs),
            )

        selection_entry = scoring_audit.selection_entry
        if selection_entry is None:
            raise ValueError("Engine C scoring audit is missing its selection entry")
        if selection_entry.outcome == SelectionOutcome.REJECTED_RANKING:
            logs.append(
                _runtime_log_entry(
                    runtime_input,
                    engine_output,
                    event="engine_c_rejected_by_ranking",
                    raw_score=scoring_audit.raw_score_result.raw_score,
                    penalized_score=penalized_score,
                    reasons=(selection_entry.rejection_reason,),
                )
            )
            return EngineCRuntimeResult(
                status=EngineCRuntimeStatus.REJECTED_RANKING,
                engine_output=engine_output,
                signal_candidate=signal_candidate,
                scoring_round=scoring_round,
                scoring_audit=scoring_audit,
                log_entries=tuple(logs),
            )
        if selection_entry.outcome == SelectionOutcome.REJECTED_PORTFOLIO:
            portfolio_reason = selection_entry.rejection_reason
            if scoring_audit.portfolio_result is not None and scoring_audit.portfolio_result.reason:
                portfolio_reason = scoring_audit.portfolio_result.reason
            logs.append(
                _runtime_log_entry(
                    runtime_input,
                    engine_output,
                    event="engine_c_rejected_by_portfolio",
                    raw_score=scoring_audit.raw_score_result.raw_score,
                    penalized_score=penalized_score,
                    reasons=(portfolio_reason,),
                )
            )
            return EngineCRuntimeResult(
                status=EngineCRuntimeStatus.REJECTED_PORTFOLIO,
                engine_output=engine_output,
                signal_candidate=signal_candidate,
                scoring_round=scoring_round,
                scoring_audit=scoring_audit,
                log_entries=tuple(logs),
            )

        size_multiplier = scoring_audit.penalty_cap_result.capped_size_multiplier
        planned_loss = runtime_input.projected_loss
        if planned_loss is not None:
            planned_loss *= size_multiplier
        self._risk_runtime.set_equity(
            current_equity=runtime_input.current_equity,
            session_peak_equity=runtime_input.session_peak_equity,
        )
        risk_evaluation = self._risk_runtime.evaluate_candidate(
            RiskCandidate(
                pair=engine_output.pair,
                engine_id="engine_c",
                size=runtime_input.projected_size * size_multiplier,
                planned_loss=planned_loss,
                pair_beta=runtime_input.pair_beta,
            ),
            now=now,
        )
        if risk_evaluation.action != RiskRuntimeAction.ACCEPT:
            reasons = risk_evaluation.reasons or ("risk runtime rejected candidate",)
            logs.append(
                _runtime_log_entry(
                    runtime_input,
                    engine_output,
                    event="engine_c_risk_rejected",
                    raw_score=scoring_audit.raw_score_result.raw_score,
                    penalized_score=penalized_score,
                    reasons=reasons,
                )
            )
            status = {
                RiskRuntimeAction.REJECT: EngineCRuntimeStatus.RISK_REJECTED,
                RiskRuntimeAction.REDUCE_EXPOSURE: EngineCRuntimeStatus.RISK_REDUCED,
                RiskRuntimeAction.OBSERVE_ONLY: EngineCRuntimeStatus.RISK_OBSERVE_ONLY,
            }.get(risk_evaluation.action, EngineCRuntimeStatus.RISK_REJECTED)
            return EngineCRuntimeResult(
                status=status,
                engine_output=engine_output,
                signal_candidate=signal_candidate,
                scoring_round=scoring_round,
                scoring_audit=scoring_audit,
                risk_evaluation=risk_evaluation,
                log_entries=tuple(logs),
            )

        logs.append(
            _runtime_log_entry(
                runtime_input,
                engine_output,
                event="engine_c_accepted",
                raw_score=scoring_audit.raw_score_result.raw_score,
                penalized_score=penalized_score,
            )
        )
        return EngineCRuntimeResult(
            status=EngineCRuntimeStatus.ACCEPTED,
            engine_output=engine_output,
            signal_candidate=signal_candidate,
            scoring_round=scoring_round,
            scoring_audit=scoring_audit,
            risk_evaluation=risk_evaluation,
            log_entries=tuple(logs),
        )


def _build_scoring_candidate(runtime_input: EngineCRuntimeInput, engine_output: EngineCOutput) -> ScoringCandidateInput:
    return ScoringCandidateInput(
        engine_id="engine_c",
        pair=engine_output.pair,
        raw_features={key: engine_output.block_scores.get(key, 0.0) for key in _ENGINE_C_FEATURE_WEIGHTS},
        allowed_features=frozenset(_ENGINE_C_FEATURE_WEIGHTS),
        weights=dict(_ENGINE_C_FEATURE_WEIGHTS),
        scoring_version=engine_output.scoring_version or runtime_input.engine_inputs.scoring_version or "engine_c.v1",
        score_penalties=runtime_input.score_penalties,
        size_penalties=runtime_input.size_penalties,
        blocker_conditions=runtime_input.blocker_conditions,
        expected_cost=engine_output.expected_cost,
        expected_ce=engine_output.ce_expected,
        projected_size=runtime_input.projected_size,
        projected_loss=0.0 if runtime_input.projected_loss is None else runtime_input.projected_loss,
        projected_beta_impact=0.0 if runtime_input.pair_beta is None else runtime_input.pair_beta * runtime_input.projected_size,
        cluster_id=runtime_input.cluster_id,
        corr_penalty=runtime_input.corr_penalty,
        risk_penalty=runtime_input.risk_penalty,
    )


def _build_signal_candidate(inputs: EngineCInput, engine_output: EngineCOutput, timestamp_ms: int) -> SignalCandidate:
    max_hold_ms = None
    if engine_output.holding_hours > 0:
        max_hold_ms = int(engine_output.holding_hours * 3600 * 1000)
    return SignalCandidate(
        timestamp_ms=timestamp_ms,
        pair=engine_output.pair,
        engine_id=EngineId.C,
        signal_type=SignalType.ENTRY,
        side=Side.BUY,
        confidence=max(0.0, min(1.0, engine_output.penalized_score)),
        regime=_to_regime_id(inputs.regime),
        entry_price=inputs.entry_price,
        stop_loss=engine_output.invalidation.stop_price if engine_output.invalidation is not None else None,
        take_profit=engine_output.invalidation.target_price if engine_output.invalidation is not None else None,
        max_hold_ms=max_hold_ms,
        reason=f"engine_c:{engine_output.conviction.value}:{engine_output.breakout_type or 'breakout'}",
    )


def _to_regime_id(value: str) -> RegimeId:
    normalized = value.strip().lower()
    mapping = {
        "breakout": RegimeId.BREAKOUT,
        "trending_up": RegimeId.TRENDING_UP,
        "trending_down": RegimeId.TRENDING_DOWN,
        "range": RegimeId.RANGE_BOUND,
        "range_bound": RegimeId.RANGE_BOUND,
        "high_volatility": RegimeId.HIGH_VOLATILITY,
        "low_volatility": RegimeId.LOW_VOLATILITY,
    }
    return mapping.get(normalized, RegimeId.UNKNOWN)
