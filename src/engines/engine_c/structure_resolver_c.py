"""Pure structure-resolution helpers for Engine C."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .engine_c_runner import EngineCInput


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def resolve_engine_c_structure(inputs: "EngineCInput") -> dict[str, float | str | bool]:
    resolved_range_high = inputs.range_high if inputs.range_high > 0.0 else max(inputs.breakout_level, inputs.entry_price)
    if resolved_range_high <= 0.0:
        resolved_range_high = max(inputs.entry_price, 1.0)

    fallback_width = max(inputs.atr * 1.5, resolved_range_high * max(0.002, inputs.range_quality * 0.01))
    resolved_range_low = (
        inputs.range_low if 0.0 < inputs.range_low < resolved_range_high else resolved_range_high - fallback_width
    )
    resolved_range_low = max(0.0, resolved_range_low)
    range_width_pct = (resolved_range_high - resolved_range_low) / max(resolved_range_high, 1e-6)
    distance_to_breakout_pct = max(0.0, (inputs.entry_price - inputs.breakout_level) / max(inputs.breakout_level, 1e-6))

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
    covered_share_by_engine_a = _clamp(
        inputs.covered_share_by_engine_a
        if inputs.covered_share_by_engine_a > 0.0
        else duplication_overlap_with_engine_a
    )
    duplication_possible_with_engine_a = (
        duplication_overlap_with_engine_a >= 0.65 or covered_share_by_engine_a >= 0.60
    )
    marginal_portfolio_gain = (
        inputs.marginal_portfolio_gain
        if inputs.marginal_portfolio_gain > 0.0
        else max(0.0, inputs.candidate_size * (inputs.expected_gain - inputs.expected_cost))
    )
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
        "marginal_portfolio_gain": marginal_portfolio_gain,
        "covered_share_by_engine_a": covered_share_by_engine_a,
        "keff_contribution": keff_contribution,
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
        "marginal_portfolio_gain": structure["marginal_portfolio_gain"],
        "covered_share_by_engine_a": structure["covered_share_by_engine_a"],
        "keff_contribution": structure["keff_contribution"],
    }
