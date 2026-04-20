"""Governed Engine D coordination-input assembly from historical state."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

from interface_contracts import Side

from .consecutive_stop_counter_d import (
    DEFAULT_D_CONSECUTIVE_STOP_LIMIT,
    DEFAULT_D_RESET_FAILSAFE_NS,
    ConsecutiveStopStateD,
    EngineDResetStateInspection,
    inspect_engine_d_reset_state,
)
from .first_episode_resolver_d import EpisodeJournalLike, FirstEpisodeResolutionD, resolve_first_episode
from .historical_linkage_guard_d import build_engine_d_coordination_input

TCoordinationInput = TypeVar("TCoordinationInput")


@dataclass(frozen=True)
class EngineDCoordinationAssembly(Generic[TCoordinationInput]):
    """Resolved historical linkage plus the caller-ready coordination input."""

    first_episode_resolution: FirstEpisodeResolutionD
    stop_state: ConsecutiveStopStateD
    reset_state_inspection: EngineDResetStateInspection
    coordination_input: TCoordinationInput


def assemble_engine_d_coordination_input(
    *,
    coordination_input_factory: Callable[..., TCoordinationInput],
    journal: EpisodeJournalLike,
    evaluated_at_ns: int,
    pair: str,
    side: Side,
    stop_state: ConsecutiveStopStateD | None = None,
    reference_size: float | None = None,
    lookback_ns: int | None = None,
    d_consecutive_stop_limit: int = DEFAULT_D_CONSECUTIVE_STOP_LIMIT,
    d_reset_failsafe_ns: int = DEFAULT_D_RESET_FAILSAFE_NS,
) -> EngineDCoordinationAssembly[TCoordinationInput]:
    """Resolve D historical evidence and assemble the canonical coordination input."""

    effective_stop_state = stop_state or ConsecutiveStopStateD()
    resolution = resolve_first_episode(
        journal,
        pair=pair,
        side=side,
        as_of_ns=evaluated_at_ns,
        lookback_ns=lookback_ns,
    )
    reset_state_inspection = inspect_engine_d_reset_state(
        effective_stop_state,
        evaluated_at_ns=evaluated_at_ns,
        stop_limit=d_consecutive_stop_limit,
        reset_failsafe_ns=d_reset_failsafe_ns,
    )
    coordination_input = build_engine_d_coordination_input(
        coordination_input_factory=coordination_input_factory,
        evaluated_at_ns=evaluated_at_ns,
        pair=pair,
        side=side,
        first_episode_ref=resolution.episode_ref,
        stop_state=effective_stop_state,
        reference_size=reference_size,
    )
    return EngineDCoordinationAssembly(
        first_episode_resolution=resolution,
        stop_state=effective_stop_state,
        reset_state_inspection=reset_state_inspection,
        coordination_input=coordination_input,
    )


__all__ = [
    "EngineDCoordinationAssembly",
    "assemble_engine_d_coordination_input",
]
