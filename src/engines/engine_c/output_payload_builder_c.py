"""Pure output-payload assembly helpers for Engine C."""

from __future__ import annotations


def build_engine_c_output_payload(
    *,
    structure: dict[str, float | str | bool],
    scoring_version: str,
    log_entries: tuple[object, ...],
    **overrides: object,
) -> dict[str, object]:
    payload: dict[str, object] = {
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
        "scoring_version": scoring_version,
        "log_entries": log_entries,
    }
    payload.update(overrides)
    return payload
