"""Additive doc20 economics seam for break-even / CE / EV-net gating."""

from __future__ import annotations

import math

from pydantic import BaseModel, Field


class BreakEvenFilterConfig(BaseModel, frozen=True):
    """Governed economics floor for additive forecast emission."""

    min_ev_net: float = Field(default=0.0, ge=0.0)
    strict_break_even: bool = True
    require_complete_cost_model: bool = False


class BreakEvenFilterDecision(BaseModel, frozen=True):
    allowed: bool
    reason_code: str = ""
    expected_gain: float
    expected_cost: float
    expected_break_even: float
    expected_ce: float | None = None
    ce_min: float | None = None
    candidate_size: float
    ev_net: float
    cost_model_completeness_status: str = "UNKNOWN"
    fee_source_status: str = "UNKNOWN"
    impact_source_status: str = "UNKNOWN"
    fill_realism_status: str = "UNKNOWN"
    realized_slippage_status: str = "UNKNOWN"
    partial_cost_model: bool = False
    cost_gate_status: str = "UNKNOWN"
    detail: str = ""


def evaluate_break_even_filter(
    *,
    expected_gain: float,
    expected_cost: float,
    candidate_size: float,
    delta_safe: float = 0.0,
    expected_ce: float | None = None,
    ce_min: float | None = None,
    cost_model_completeness_status: str = "UNKNOWN",
    fee_source_status: str = "UNKNOWN",
    impact_source_status: str = "UNKNOWN",
    fill_realism_status: str = "UNKNOWN",
    realized_slippage_status: str = "UNKNOWN",
    config: BreakEvenFilterConfig | None = None,
) -> BreakEvenFilterDecision:
    """Evaluate the additive doc20 economics gate without emitting a fake trade."""

    _require_finite_non_negative("expected_gain", expected_gain)
    _require_finite_non_negative("expected_cost", expected_cost)
    _require_finite_positive("candidate_size", candidate_size)
    _require_finite_non_negative("delta_safe", delta_safe)
    if expected_ce is not None and not math.isfinite(expected_ce):
        raise ValueError("expected_ce must be finite when provided")
    if ce_min is not None:
        _require_finite_non_negative("ce_min", ce_min)

    resolved_config = config or BreakEvenFilterConfig()
    resolved_cost_status = _normalize_status(cost_model_completeness_status, default="UNKNOWN")
    resolved_fee_status = _normalize_status(fee_source_status, default="UNKNOWN")
    resolved_impact_status = _normalize_status(impact_source_status, default="UNKNOWN")
    resolved_fill_status = _normalize_status(fill_realism_status, default="UNKNOWN")
    resolved_realized_slippage_status = _normalize_status(
        realized_slippage_status,
        default="UNKNOWN",
    )
    partial_cost_model = resolved_cost_status != "COMPLETE"
    expected_break_even = expected_cost + delta_safe
    ev_net = candidate_size * (expected_gain - expected_cost)

    if resolved_config.require_complete_cost_model and partial_cost_model:
        return BreakEvenFilterDecision(
            allowed=False,
            reason_code="COST_MODEL_INCOMPLETE",
            expected_gain=expected_gain,
            expected_cost=expected_cost,
            expected_break_even=expected_break_even,
            expected_ce=expected_ce,
            ce_min=ce_min,
            candidate_size=candidate_size,
            ev_net=ev_net,
            cost_model_completeness_status=resolved_cost_status,
            fee_source_status=resolved_fee_status,
            impact_source_status=resolved_impact_status,
            fill_realism_status=resolved_fill_status,
            realized_slippage_status=resolved_realized_slippage_status,
            partial_cost_model=True,
            cost_gate_status="COST_MODEL_INCOMPLETE",
            detail=(
                "cost_model_completeness_status="
                f"{resolved_cost_status}; strict completeness required"
            ),
        )

    edge_cleared = expected_gain > expected_break_even
    if not resolved_config.strict_break_even:
        edge_cleared = expected_gain >= expected_break_even

    ce_cleared = True
    if expected_ce is not None and ce_min is not None:
        ce_cleared = expected_ce >= ce_min

    ev_cleared = ev_net > resolved_config.min_ev_net
    allowed = edge_cleared and ce_cleared and ev_cleared

    reason_code = ""
    if not edge_cleared:
        reason_code = "BREAK_EVEN_NOT_CLEARED"
    elif not ce_cleared:
        reason_code = "CE_BELOW_MINIMUM"
    elif not ev_cleared:
        reason_code = "EV_NET_BELOW_FLOOR"

    detail = (
        f"gain={expected_gain:.6f}, cost={expected_cost:.6f}, "
        f"break_even={expected_break_even:.6f}, ev_net={ev_net:.6f}"
    )
    if expected_ce is not None and ce_min is not None:
        detail += f", ce={expected_ce:.6f}, ce_min={ce_min:.6f}"
    detail += (
        ", cost_status="
        f"{resolved_cost_status}, fee_status={resolved_fee_status}, "
        f"impact_status={resolved_impact_status}, fill_status={resolved_fill_status}, "
        f"realized_slippage_status={resolved_realized_slippage_status}"
    )

    return BreakEvenFilterDecision(
        allowed=allowed,
        reason_code=reason_code,
        expected_gain=expected_gain,
        expected_cost=expected_cost,
        expected_break_even=expected_break_even,
        expected_ce=expected_ce,
        ce_min=ce_min,
        candidate_size=candidate_size,
        ev_net=ev_net,
        cost_model_completeness_status=resolved_cost_status,
        fee_source_status=resolved_fee_status,
        impact_source_status=resolved_impact_status,
        fill_realism_status=resolved_fill_status,
        realized_slippage_status=resolved_realized_slippage_status,
        partial_cost_model=partial_cost_model,
        cost_gate_status="PARTIAL_COST_MODEL" if partial_cost_model else "COMPLETE",
        detail=detail,
    )


def _require_finite_non_negative(name: str, value: float) -> None:
    if not math.isfinite(value) or value < 0.0:
        raise ValueError(f"{name} must be finite and >= 0")


def _require_finite_positive(name: str, value: float) -> None:
    if not math.isfinite(value) or value <= 0.0:
        raise ValueError(f"{name} must be finite and > 0")


def _normalize_status(value: str | None, *, default: str) -> str:
    normalized = "" if value is None else str(value).strip()
    return normalized or default


__all__ = [
    "BreakEvenFilterConfig",
    "BreakEvenFilterDecision",
    "evaluate_break_even_filter",
]
