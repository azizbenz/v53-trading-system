"""Explicit Engine D historical-linkage guard wrapping the canonical coordination rule."""

from __future__ import annotations

from typing import Callable, TypeVar

from interface_contracts import Side

from .consecutive_stop_counter_d import ConsecutiveStopStateD, to_coordination_fields

TCoordinationInput = TypeVar("TCoordinationInput")
TCoordinationOutcome = TypeVar("TCoordinationOutcome")


def build_engine_d_coordination_input(
    *,
    coordination_input_factory: Callable[..., TCoordinationInput],
    evaluated_at_ns: int,
    pair: str,
    side: Side,
    first_episode_ref: object | None,
    stop_state: ConsecutiveStopStateD | None = None,
    reference_size: float | None = None,
) -> TCoordinationInput:
    """Build the bounded Engine D coordination input from explicit historical state."""

    coordination_fields = to_coordination_fields(stop_state or ConsecutiveStopStateD())
    return coordination_input_factory(
        evaluated_at_ns=evaluated_at_ns,
        engine_id="engine_d",
        pair=pair,
        side=side,
        first_episode_ref=first_episode_ref,
        reference_size=reference_size,
        **coordination_fields,
    )


def evaluate_engine_d_historical_linkage(
    coordination_input: object,
    *,
    thresholds: object | None = None,
    evaluator: Callable[..., TCoordinationOutcome],
) -> TCoordinationOutcome:
    """Evaluate Engine D linkage through the canonical coordination seam only."""

    engine_id = getattr(coordination_input, "engine_id", "")
    if getattr(engine_id, "value", engine_id) != "engine_d":
        raise ValueError("evaluate_engine_d_historical_linkage requires engine_id=engine_d")
    return evaluator(coordination_input, thresholds=thresholds)


__all__ = [
    "build_engine_d_coordination_input",
    "evaluate_engine_d_historical_linkage",
]
