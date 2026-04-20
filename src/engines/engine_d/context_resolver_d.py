"""Pure context-resolution helpers for Engine D."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .engine_d_runner import EngineDInput


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


_ENGINE_D_ANTI_REVENGE_BLOCKING_STATES = frozenset({"blocked", "cooldown_active", "stop_cooldown"})


def _normalize_anti_revenge_state(value: str) -> str:
    return value.strip().lower()


def resolve_engine_d_context(inputs: "EngineDInput") -> dict[str, float | str | bool]:
    link_type = inputs.link_type.strip() or ("prior_trade" if inputs.origin_trade_id else "prior_context")
    duplication_overlap_with_engine_a = _clamp(inputs.duplication_overlap_with_engine_a)
    covered_share_by_engine_a = _clamp(
        inputs.covered_share_by_engine_a
        if inputs.covered_share_by_engine_a > 0.0
        else duplication_overlap_with_engine_a
    )
    duplication_possible_with_engine_a = (
        duplication_overlap_with_engine_a >= 0.65 or covered_share_by_engine_a >= 0.55
    )
    if inputs.marginal_portfolio_gain != 0.0:
        marginal_portfolio_gain = inputs.marginal_portfolio_gain
    else:
        marginal_portfolio_gain = max(0.0, inputs.candidate_size * (inputs.expected_gain - inputs.expected_cost))
    concentration_risk = _clamp(0.60 * (1.0 - inputs.concentration_headroom) + 0.40 * inputs.reentry_lateness)
    anti_revenge_state = _normalize_anti_revenge_state(inputs.anti_revenge_state)
    anti_revenge_blocked = anti_revenge_state in _ENGINE_D_ANTI_REVENGE_BLOCKING_STATES or (
        anti_revenge_state == "reset_required" and inputs.last_fresh_a_detection_at_ns is None
    )
    duplication_blocked = duplication_possible_with_engine_a and marginal_portfolio_gain <= 0.0
    return {
        "origin_context_id": inputs.origin_context_id or f"{inputs.pair}:prior_context",
        "origin_trade_id": inputs.origin_trade_id,
        "link_type": link_type,
        "structure_reformed_detected": inputs.structure_reformed_detected,
        "first_episode_id": inputs.first_episode_id,
        "first_episode_engine_id": inputs.first_episode_engine_id,
        "first_episode_close_reason": inputs.first_episode_close_reason,
        "consecutive_stop_count": inputs.consecutive_stop_count,
        "last_stop_at_ns": inputs.last_stop_at_ns,
        "last_fresh_a_detection_at_ns": inputs.last_fresh_a_detection_at_ns,
        # Decision contract: anti_revenge_state and marginal_portfolio_gain may block D;
        # duplication overlap and covered share remain observability unless duplication_blocked is true.
        "anti_revenge_state": anti_revenge_state,
        "anti_revenge_blocked": anti_revenge_blocked,
        "duplication_possible_with_engine_a": duplication_possible_with_engine_a,
        "duplication_overlap_with_engine_a": duplication_overlap_with_engine_a,
        "duplication_blocked": duplication_blocked,
        "marginal_portfolio_gain": marginal_portfolio_gain,
        "covered_share_by_engine_a": covered_share_by_engine_a,
        "concentration_risk": concentration_risk,
        "marginal_concentration": concentration_risk,
    }


def build_engine_d_log_context(
    context: dict[str, float | str | bool],
) -> dict[str, float | str | bool]:
    return {
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
        "anti_revenge_blocked": context["anti_revenge_blocked"],
        "duplication_possible_with_engine_a": context["duplication_possible_with_engine_a"],
        "duplication_overlap_with_engine_a": context["duplication_overlap_with_engine_a"],
        "duplication_blocked": context["duplication_blocked"],
        "marginal_portfolio_gain": context["marginal_portfolio_gain"],
        "covered_share_by_engine_a": context["covered_share_by_engine_a"],
        "marginal_concentration": context["marginal_concentration"],
    }
