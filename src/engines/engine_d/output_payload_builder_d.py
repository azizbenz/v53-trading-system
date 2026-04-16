"""Pure output-payload assembly helpers for Engine D."""

from __future__ import annotations


def build_engine_d_output_payload(
    *,
    context: dict[str, float | str | bool],
    scoring_version: str,
    log_entries: tuple[object, ...],
    **overrides: object,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "origin_context_id": context["origin_context_id"],
        "origin_trade_id": context["origin_trade_id"],
        "link_type": context["link_type"],
        "structure_reformed_detected": context["structure_reformed_detected"],
        "first_episode_id": context["first_episode_id"],
        "first_episode_engine_id": context["first_episode_engine_id"],
        "first_episode_close_reason": context["first_episode_close_reason"],
        "consecutive_stop_count": context["consecutive_stop_count"],
        "last_stop_at_ns": context["last_stop_at_ns"],
        "last_fresh_a_detection_at_ns": context["last_fresh_a_detection_at_ns"],
        "anti_revenge_state": context["anti_revenge_state"],
        "marginal_concentration": context["marginal_concentration"],
        "duplication_possible_with_engine_a": context["duplication_possible_with_engine_a"],
        "duplication_overlap_with_engine_a": context["duplication_overlap_with_engine_a"],
        "marginal_portfolio_gain": context["marginal_portfolio_gain"],
        "covered_share_by_engine_a": context["covered_share_by_engine_a"],
        "scoring_version": scoring_version,
        "log_entries": log_entries,
    }
    payload.update(overrides)
    return payload
