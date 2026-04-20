"""Pure scoring helpers for Engine C signal evaluation."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .engine_c_runner import EngineCInput


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def compute_breakout_score(inputs: "EngineCInput") -> float:
    """0.35*breakout + 0.25*range + 0.20*compression + 0.20*volume."""
    return _clamp(
        0.35 * inputs.breakout_strength
        + 0.25 * inputs.range_quality
        + 0.20 * inputs.compression_quality
        + 0.20 * inputs.volume_confirmation
    )


def compute_context_score(inputs: "EngineCInput") -> float:
    """0.35*regime + 0.25*health + 0.20*freshness + 0.20*flow."""
    return _clamp(
        0.35 * inputs.regime_favorability
        + 0.25 * inputs.pair_health
        + 0.20 * inputs.data_freshness
        + 0.20 * inputs.flow_coherence
    )


def compute_continuation_score_components(
    *,
    followthrough_room: float,
    extension_pct: float,
    context_score: float,
) -> float:
    """0.45*followthrough + 0.25*(1-extension) + 0.30*context."""
    return _clamp(
        0.45 * followthrough_room
        + 0.25 * (1.0 - extension_pct)
        + 0.30 * context_score
    )


def compute_continuation_score(
    inputs: "EngineCInput",
    *,
    context_score: float,
) -> float:
    return compute_continuation_score_components(
        followthrough_room=inputs.followthrough_room,
        extension_pct=inputs.extension_pct,
        context_score=context_score,
    )


def compute_fake_breakout_risk(inputs: "EngineCInput") -> float:
    """0.45*retrace + 0.30*wick + 0.25*(1-volume)."""
    return _clamp(
        0.45 * inputs.retrace_risk
        + 0.30 * inputs.rejection_wick_ratio
        + 0.25 * (1.0 - inputs.volume_confirmation)
    )


__all__ = [
    "compute_breakout_score",
    "compute_context_score",
    "compute_continuation_score",
    "compute_continuation_score_components",
    "compute_fake_breakout_risk",
]
