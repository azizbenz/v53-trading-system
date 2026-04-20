"""Additive historical-entry helpers for the public Engine D runtime surface."""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from data_backbone.microstructure.realized_kernel_vol import RealizedKernelVolRecord
from scoring_backbone.hard_block_gate.blocker_evaluator import BlockerCondition
from scoring_backbone.penalty_aggregator.score_penalty_builder import ScorePenaltyItem
from scoring_backbone.penalty_aggregator.size_penalty_builder import SizePenaltyItem
from scoring_backbone.ranking_router.portfolio_compatibility_checker import PortfolioState
from scoring_backbone.scoring_runtime import ScoringCandidateInput

from .consecutive_stop_counter_d import DEFAULT_D_CONSECUTIVE_STOP_LIMIT, DEFAULT_D_RESET_FAILSAFE_NS
from .engine_d_runner import EngineDInput

if TYPE_CHECKING:
    from .consecutive_stop_counter_d import ConsecutiveStopStateD
    from .engine_d_runtime import EngineDRuntimeResult


class EngineDRuntimeHistoricalEntryMixin:
    def evaluate_from_historical_state(
        self,
        *,
        coordination_input_factory: Callable[..., object],
        journal: object,
        engine_inputs: EngineDInput,
        timestamp_ms: int,
        portfolio: PortfolioState,
        projected_size: float,
        projected_loss: float | None = None,
        current_equity: float,
        session_peak_equity: float,
        pair_beta: float | None = None,
        cluster_id: str,
        stop_state: "ConsecutiveStopStateD | None" = None,
        reference_size: float | None = None,
        lookback_ns: int | None = None,
        min_gap_ns: int | None = None,
        realized_vol_current_record: RealizedKernelVolRecord | None = None,
        realized_vol_post_close_record: RealizedKernelVolRecord | None = None,
        score_penalties: tuple[ScorePenaltyItem, ...] = (),
        size_penalties: tuple[SizePenaltyItem, ...] = (),
        blocker_conditions: BlockerCondition | None = None,
        peer_candidates: tuple[ScoringCandidateInput, ...] = (),
        max_selections: int = 1,
        corr_penalty: float = 0.0,
        risk_penalty: float = 0.0,
        strategy_id: str | None = None,
        now: float | None = None,
    ) -> "EngineDRuntimeResult":
        from .runtime_input_assembler_d import assemble_engine_d_runtime_input

        thresholds = getattr(self, "_coordination_thresholds", None)
        d_consecutive_stop_limit = (
            DEFAULT_D_CONSECUTIVE_STOP_LIMIT
            if thresholds is None
            else thresholds.d_consecutive_stop_limit
        )
        d_reset_failsafe_ns = (
            DEFAULT_D_RESET_FAILSAFE_NS
            if thresholds is None
            else thresholds.d_reset_failsafe_ns
        )
        effective_lookback_ns = (
            getattr(self, "_first_episode_lookback_ns", None)
            if lookback_ns is None
            else lookback_ns
        )
        effective_min_gap_ns = (
            getattr(self, "_first_episode_min_gap_ns", None)
            if min_gap_ns is None
            else min_gap_ns
        )
        assembly = assemble_engine_d_runtime_input(
            coordination_input_factory=coordination_input_factory,
            journal=journal,
            engine_inputs=engine_inputs,
            timestamp_ms=timestamp_ms,
            portfolio=portfolio,
            projected_size=projected_size,
            projected_loss=projected_loss,
            current_equity=current_equity,
            session_peak_equity=session_peak_equity,
            pair_beta=pair_beta,
            cluster_id=cluster_id,
            stop_state=stop_state,
            reference_size=reference_size,
            lookback_ns=effective_lookback_ns,
            min_gap_ns=effective_min_gap_ns,
            d_consecutive_stop_limit=d_consecutive_stop_limit,
            d_reset_failsafe_ns=d_reset_failsafe_ns,
            realized_vol_current_record=realized_vol_current_record,
            realized_vol_post_close_record=realized_vol_post_close_record,
            score_penalties=score_penalties,
            size_penalties=size_penalties,
            blocker_conditions=blocker_conditions,
            peer_candidates=peer_candidates,
            max_selections=max_selections,
            corr_penalty=corr_penalty,
            risk_penalty=risk_penalty,
            strategy_id=strategy_id,
        )
        result = self.evaluate(assembly.runtime_input, now=now)
        return result.model_copy(
            update={
                "historical_state_inspection": assembly.reset_state_inspection,
                "first_episode_gap_inspection": assembly.first_episode_gap_inspection,
            }
        )


__all__ = ["EngineDRuntimeHistoricalEntryMixin"]
