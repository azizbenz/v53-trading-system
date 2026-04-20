"""Governed Engine D runtime-input assembly from historical linkage state."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

from data_backbone.microstructure import compose_engine_d_input_payload
from data_backbone.microstructure.realized_kernel_vol import RealizedKernelVolRecord
from interface_contracts import Side
from scoring_backbone.hard_block_gate.blocker_evaluator import BlockerCondition
from scoring_backbone.penalty_aggregator.score_penalty_builder import ScorePenaltyItem
from scoring_backbone.penalty_aggregator.size_penalty_builder import SizePenaltyItem
from scoring_backbone.ranking_router.portfolio_compatibility_checker import PortfolioState
from scoring_backbone.scoring_runtime import ScoringCandidateInput

from .consecutive_stop_counter_d import (
    DEFAULT_D_CONSECUTIVE_STOP_LIMIT,
    DEFAULT_D_RESET_FAILSAFE_NS,
    ConsecutiveStopStateD,
    EngineDResetStateInspection,
)
from .coordination_input_assembler_d import EngineDCoordinationAssembly, assemble_engine_d_coordination_input
from .engine_d_runner import EngineDInput
from .engine_d_runtime import EngineDRuntimeInput
from .first_episode_resolver_d import EpisodeJournalLike, FirstEpisodeGapInspectionD, inspect_first_episode_gap

TCoordinationInput = TypeVar("TCoordinationInput")


@dataclass(frozen=True)
class EngineDRuntimeInputAssembly(Generic[TCoordinationInput]):
    """Typed result of assembling Engine D runtime input plus coordination evidence."""

    coordination_assembly: EngineDCoordinationAssembly[TCoordinationInput]
    reset_state_inspection: EngineDResetStateInspection
    first_episode_gap_inspection: FirstEpisodeGapInspectionD | None
    runtime_input: EngineDRuntimeInput


def assemble_engine_d_runtime_input(
    *,
    coordination_input_factory: Callable[..., TCoordinationInput],
    journal: EpisodeJournalLike,
    engine_inputs: EngineDInput,
    timestamp_ms: int,
    portfolio: PortfolioState,
    projected_size: float,
    projected_loss: float | None = None,
    current_equity: float,
    session_peak_equity: float,
    pair_beta: float | None = None,
    cluster_id: str,
    stop_state: ConsecutiveStopStateD | None = None,
    reference_size: float | None = None,
    lookback_ns: int | None = None,
    min_gap_ns: int | None = None,
    d_consecutive_stop_limit: int = DEFAULT_D_CONSECUTIVE_STOP_LIMIT,
    d_reset_failsafe_ns: int = DEFAULT_D_RESET_FAILSAFE_NS,
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
) -> EngineDRuntimeInputAssembly[TCoordinationInput]:
    """Assemble Engine D runtime input with governed historical coordination evidence."""

    evaluated_at_ns = timestamp_ms * 1_000_000
    engine_inputs = EngineDInput(
        **compose_engine_d_input_payload(
            engine_inputs.model_dump(mode="python"),
            pair=engine_inputs.pair,
            realized_vol_current_record=realized_vol_current_record,
            realized_vol_post_close_record=realized_vol_post_close_record,
        )
    )
    coordination_assembly = assemble_engine_d_coordination_input(
        coordination_input_factory=coordination_input_factory,
        journal=journal,
        evaluated_at_ns=evaluated_at_ns,
        pair=engine_inputs.pair,
        side=Side.BUY,
        stop_state=stop_state,
        reference_size=projected_size if reference_size is None else reference_size,
        lookback_ns=lookback_ns,
        d_consecutive_stop_limit=d_consecutive_stop_limit,
        d_reset_failsafe_ns=d_reset_failsafe_ns,
    )
    first_episode_gap_inspection = inspect_first_episode_gap(
        first_episode_ref=coordination_assembly.first_episode_resolution.episode_ref,
        evaluated_at_ns=evaluated_at_ns,
        min_gap_ns=min_gap_ns,
    )
    runtime_input = EngineDRuntimeInput(
        engine_inputs=engine_inputs,
        timestamp_ms=timestamp_ms,
        portfolio=portfolio,
        projected_size=projected_size,
        projected_loss=projected_loss,
        current_equity=current_equity,
        session_peak_equity=session_peak_equity,
        pair_beta=pair_beta,
        cluster_id=cluster_id,
        score_penalties=score_penalties,
        size_penalties=size_penalties,
        blocker_conditions=BlockerCondition() if blocker_conditions is None else blocker_conditions,
        peer_candidates=peer_candidates,
        max_selections=max_selections,
        corr_penalty=corr_penalty,
        risk_penalty=risk_penalty,
        coordination_input=coordination_assembly.coordination_input,
        first_episode_gap_inspection=first_episode_gap_inspection,
        strategy_id=strategy_id,
    )
    return EngineDRuntimeInputAssembly(
        coordination_assembly=coordination_assembly,
        reset_state_inspection=coordination_assembly.reset_state_inspection,
        first_episode_gap_inspection=first_episode_gap_inspection,
        runtime_input=runtime_input,
    )


__all__ = [
    "EngineDRuntimeInputAssembly",
    "assemble_engine_d_runtime_input",
]
