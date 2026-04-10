"""Pure scoring helpers for Engine C signal evaluation."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .engine_c_runner import EngineCInput


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def compute_breakout_score(inputs: "EngineCInput") -> float:
    return _clamp(
        0.35 * inputs.breakout_strength
        + 0.25 * inputs.range_quality
        + 0.20 * inputs.compression_quality
        + 0.20 * inputs.volume_confirmation
    )


def compute_context_score(inputs: "EngineCInput") -> float:
    return _clamp(
        0.35 * inputs.regime_favorability
        + 0.25 * inputs.pair_health
        + 0.20 * inputs.data_freshness
        + 0.20 * inputs.flow_coherence
    )


def compute_continuation_score(
    inputs: "EngineCInput",
    *,
    context_score: float,
) -> float:
    return _clamp(
        0.45 * inputs.followthrough_room
        + 0.25 * (1.0 - inputs.extension_pct)
        + 0.30 * context_score
    )


def compute_fake_breakout_risk(inputs: "EngineCInput") -> float:
    return _clamp(
        0.45 * inputs.retrace_risk
        + 0.30 * inputs.rejection_wick_ratio
        + 0.25 * (1.0 - inputs.volume_confirmation)
    )
