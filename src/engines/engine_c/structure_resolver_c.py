"""Pure structure-resolution helpers for Engine C.

This module hosts BOTH:
  1. The POST-validation logic `resolve_engine_c_structure(inputs)` that
     consumes an already-built `EngineCInput` and computes range/breakout
     metadata + duplication checks.
  2. The PRE-mapping `build_engine_c_input_from_breakout_features(...)` that
     projects neutral breakout microstructure scores (from
     `data_backbone.microstructure.breakout_microstructure_features`) into
     the 7-float dict required by `EngineCInput.model_validate`.

Layer separation : neutral microstructure primitives live in `data_backbone`
(reusable by any engine). Engine-specific mapping lives here.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from data_backbone.microstructure.breakout_microstructure_features import (
    BreakoutMicrostructureResolution,
)

if TYPE_CHECKING:
    from .engine_c_runner import EngineCInput


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def build_engine_c_input_from_breakout_features(
    resolution: BreakoutMicrostructureResolution,
) -> dict[str, float]:
    """Map neutral breakout microstructure scores → EngineCInput 7-float dict.

    Engine-specific projection: keeps `data_backbone` neutral while enforcing
    the EngineCInput contract (6 required floats + retrace_risk).
    """

    return {
        "breakout_strength": resolution.breakout_strength.value,
        "range_quality": resolution.range_quality.value,
        "compression_quality": resolution.compression_quality.value,
        "volume_confirmation": resolution.volume_confirmation.value,
        "followthrough_room": resolution.followthrough_room.value,
        "extension_pct": resolution.extension_pct.value,
        "retrace_risk": resolution.retrace_risk.value,
    }


def _resolve_realized_vol_reference(inputs: "EngineCInput") -> float:
    if inputs.realized_vol_at_break is not None and inputs.realized_vol_at_break > 0.0:
        return inputs.realized_vol_at_break
    if inputs.realized_vol_current is not None and inputs.realized_vol_current > 0.0:
        return inputs.realized_vol_current
    return 0.0


ENGINE_C_DUPLICATION_OVERLAP_BLOCK_MIN = 0.65
ENGINE_C_COVERED_SHARE_BLOCK_MIN = 0.60


def resolve_engine_c_structure(inputs: "EngineCInput") -> dict[str, float | str | bool]:
    """Resolve breakout structure plus portfolio-awareness metadata.

    Decision contract:
    - duplication overlap / covered share / keff remain local observability heuristics
    - canonical A/C hard-blocks live in engine_coordination_rules, not here
    - local_duplication_policy_triggered is the truthful local flag
    - duplication_blocked is retained as a backward-compatible alias only
    - marginal_portfolio_gain may be explicit from upstream or heuristic fallback
    """

    resolved_range_high_fallback_used = inputs.range_high <= 0.0
    resolved_range_high = (
        inputs.range_high if inputs.range_high > 0.0 else max(inputs.breakout_level, inputs.entry_price)
    )
    if resolved_range_high <= 0.0:
        resolved_range_high = max(inputs.entry_price, 1.0)

    realized_vol_reference = _resolve_realized_vol_reference(inputs)
    fallback_width = max(
        max(inputs.entry_price, resolved_range_high) * realized_vol_reference * 1.5,
        resolved_range_high * max(0.002, inputs.range_quality * 0.01),
    )
    resolved_range_low_fallback_used = not (0.0 < inputs.range_low < resolved_range_high)
    resolved_range_low = (
        inputs.range_low if 0.0 < inputs.range_low < resolved_range_high else resolved_range_high - fallback_width
    )
    resolved_range_low = max(0.0, resolved_range_low)
    range_width_pct = (resolved_range_high - resolved_range_low) / max(resolved_range_high, 1e-6)
    distance_to_breakout_pct = max(
        0.0,
        (inputs.entry_price - inputs.breakout_level) / max(inputs.breakout_level, 1e-6),
    )

    if inputs.volume_confirmation >= 0.80 and inputs.compression_quality >= 0.75:
        breakout_type = "compression_release"
    elif inputs.range_quality >= 0.75:
        breakout_type = "range_expansion"
    else:
        breakout_type = "structured_breakout"

    if inputs.extension_pct <= 0.25:
        continuation_context = "fresh_breakout"
    elif inputs.extension_pct <= 0.55:
        continuation_context = "controlled_extension"
    else:
        continuation_context = "late_extension"

    duplication_overlap_with_engine_a = _clamp(inputs.engine_a_overlap_ratio)
    covered_share_fallback_used = inputs.covered_share_by_engine_a <= 0.0
    covered_share_by_engine_a = _clamp(
        inputs.covered_share_by_engine_a
        if inputs.covered_share_by_engine_a > 0.0
        else duplication_overlap_with_engine_a
    )
    duplication_possible_with_engine_a = (
        duplication_overlap_with_engine_a >= ENGINE_C_DUPLICATION_OVERLAP_BLOCK_MIN
        or covered_share_by_engine_a >= ENGINE_C_COVERED_SHARE_BLOCK_MIN
    )
    marginal_portfolio_gain_fallback_used = inputs.marginal_portfolio_gain == 0.0
    marginal_portfolio_gain = (
        inputs.marginal_portfolio_gain
        if inputs.marginal_portfolio_gain != 0.0
        else max(0.0, inputs.candidate_size * (inputs.expected_gain - inputs.expected_cost))
    )
    duplication_marginality_negative = marginal_portfolio_gain <= 0.0
    local_duplication_policy_triggered = (
        duplication_possible_with_engine_a and duplication_marginality_negative
    )
    keff_fallback_used = inputs.keff_contribution <= 0.0
    keff_contribution = _clamp(
        inputs.keff_contribution
        if inputs.keff_contribution > 0.0
        else max(0.0, 1.0 - duplication_overlap_with_engine_a) * 0.5
    )

    return {
        "range_low": resolved_range_low,
        "range_high": resolved_range_high,
        "range_width_pct": range_width_pct,
        "breakout_type": breakout_type,
        "continuation_context": continuation_context,
        "distance_to_breakout_pct": distance_to_breakout_pct,
        "duplication_possible_with_engine_a": duplication_possible_with_engine_a,
        "duplication_overlap_with_engine_a": duplication_overlap_with_engine_a,
        "local_duplication_policy_triggered": local_duplication_policy_triggered,
        "duplication_blocked": local_duplication_policy_triggered,
        "marginal_portfolio_gain": marginal_portfolio_gain,
        "covered_share_by_engine_a": covered_share_by_engine_a,
        "keff_contribution": keff_contribution,
        "resolved_range_high_fallback_used": resolved_range_high_fallback_used,
        "resolved_range_low_fallback_used": resolved_range_low_fallback_used,
        "covered_share_fallback_used": covered_share_fallback_used,
        "marginal_portfolio_gain_fallback_used": marginal_portfolio_gain_fallback_used,
        "keff_fallback_used": keff_fallback_used,
    }


def build_engine_c_log_context(
    structure: dict[str, float | str | bool],
) -> dict[str, float | str | bool]:
    return {
        "range_low": structure["range_low"],
        "range_high": structure["range_high"],
        "range_width_pct": structure["range_width_pct"],
        "breakout_type": structure["breakout_type"],
        "continuation_context": structure["continuation_context"],
        "distance_to_breakout_pct": structure["distance_to_breakout_pct"],
        "duplication_possible_with_engine_a": structure["duplication_possible_with_engine_a"],
        "duplication_overlap_with_engine_a": structure["duplication_overlap_with_engine_a"],
        "local_duplication_policy_triggered": structure["local_duplication_policy_triggered"],
        "duplication_blocked": structure["duplication_blocked"],
        "marginal_portfolio_gain": structure["marginal_portfolio_gain"],
        "covered_share_by_engine_a": structure["covered_share_by_engine_a"],
        "keff_contribution": structure["keff_contribution"],
    }


__all__ = [
    "ENGINE_C_COVERED_SHARE_BLOCK_MIN",
    "ENGINE_C_DUPLICATION_OVERLAP_BLOCK_MIN",
    "build_engine_c_log_context",
    "resolve_engine_c_structure",
]
