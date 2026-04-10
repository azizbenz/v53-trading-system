"""Pure scoring helpers for Engine D signal evaluation."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .engine_d_runner import EngineDInput


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def compute_history_score(inputs: "EngineDInput") -> float:
    return _clamp(
        0.55 * inputs.prior_trade_quality
        + 0.25 * inputs.pair_health
        + 0.20 * inputs.data_freshness
    )


def compute_context_score(inputs: "EngineDInput") -> float:
    return _clamp(
        0.35 * inputs.regime_favorability
        + 0.25 * inputs.pair_health
        + 0.20 * inputs.data_freshness
        + 0.20 * inputs.flow_coherence
    )


def compute_reformation_score(
    inputs: "EngineDInput",
    *,
    context_score: float,
) -> float:
    return _clamp(
        0.45 * inputs.reformation_quality
        + 0.30 * inputs.pullback_quality
        + 0.25 * context_score
    )


def compute_marginal_value_score(inputs: "EngineDInput") -> float:
    return _clamp(
        0.35 * inputs.marginal_edge
        + 0.30 * inputs.continuation_room
        + 0.20 * inputs.concentration_headroom
        + 0.15 * (1.0 - inputs.reentry_lateness)
    )
