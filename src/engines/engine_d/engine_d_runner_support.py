"""Internal support helpers for the canonical Engine D runner."""

from __future__ import annotations

from .context_resolver_d import build_engine_d_log_context
from .invalidation_mapper_d import InvalidationLevelsD
from .engine_d_models import (
    EngineDDecision,
    EngineDInput,
    EngineDInvalidation,
    EngineDLogEntry,
    EngineDOutput,
    NoTradeReasonD,
)
from .output_payload_builder_d import build_engine_d_output_payload

EngineDContext = dict[str, float | str | bool]


def _merge_reason_codes(*reason_code_groups: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            code
            for group in reason_code_groups
            for code in group
            if code
        )
    )


def build_engine_d_gate_reason_codes(
    *,
    gate_reason_codes: tuple[str, ...],
    detailed_reason_codes: tuple[str, ...] = (),
) -> tuple[str, ...]:
    """Return Engine D reason codes with explicit gate provenance first.

    Gate 0 = historical linkage / strategy-beta / anti-revenge hard block.
    Gate 1 = history/reformation/marginal-value setup quality.
    Gate 2 = economics/cost feasibility.
    Gate 3 = downstream scoring/portfolio/risk runtime.
    """

    return _merge_reason_codes(gate_reason_codes, detailed_reason_codes)


def append_engine_d_log(
    logs: list[EngineDLogEntry],
    inputs: EngineDInput,
    context: EngineDContext,
    *,
    event: str,
    raw_score: float = 0.0,
    penalized_score: float = 0.0,
    history_score: float = 0.0,
    reformation_score: float = 0.0,
    marginal_value_score: float = 0.0,
    concentration_risk: float = 0.0,
    expected_cost: float = 0.0,
    ce_expected: float = 0.0,
    ev_net: float = 0.0,
    conviction: str = "",
    tier: str = "",
    holding_hours: float = 0.0,
    reasons: tuple[str, ...] = (),
) -> None:
    logs.append(
        EngineDLogEntry(
            event=event,
            pair=inputs.pair,
            regime=inputs.regime,
            **build_engine_d_log_context(context),
            raw_score=raw_score,
            penalized_score=penalized_score,
            history_score=history_score,
            reformation_score=reformation_score,
            marginal_value_score=marginal_value_score,
            concentration_risk=concentration_risk,
            expected_cost=expected_cost,
            ce_expected=ce_expected,
            ev_net=ev_net,
            conviction=conviction,
            tier=tier,
            holding_hours=holding_hours,
            scoring_version=inputs.scoring_version,
            reasons=reasons,
        )
    )


def build_engine_d_no_trade_output(
    inputs: EngineDInput,
    context: EngineDContext,
    logs: list[EngineDLogEntry],
    no_trade_reasons: list[NoTradeReasonD],
    *,
    history_score: float = 0.0,
    reformation_score: float = 0.0,
    marginal_value_score: float = 0.0,
    concentration_risk: float = 0.0,
    expected_cost: float = 0.0,
    ce_expected: float = 0.0,
    ev_net: float = 0.0,
    reason_codes: tuple[str, ...] = (),
) -> EngineDOutput:
    resolved_reason_codes = reason_codes or _merge_reason_codes(
        tuple(f"engine_d.no_trade.{reason.value}" for reason in no_trade_reasons),
    )
    return EngineDOutput(
        pair=inputs.pair,
        decision=EngineDDecision.NO_TRADE,
        **build_engine_d_output_payload(
            context=context,
            scoring_version=inputs.scoring_version,
            log_entries=tuple(logs),
            history_score=history_score,
            reformation_score=reformation_score,
            marginal_value_score=marginal_value_score,
            concentration_risk=concentration_risk,
            expected_cost=expected_cost,
            ce_expected=ce_expected,
            ev_net=ev_net,
            reason_codes=resolved_reason_codes,
            no_trade_reasons=tuple(no_trade_reasons),
        ),
    )


def build_engine_d_invalidation(invalidation_levels: InvalidationLevelsD) -> EngineDInvalidation:
    return EngineDInvalidation(
        stop_price=invalidation_levels.stop_price,
        target_price=invalidation_levels.target_price,
        risk_multiple=invalidation_levels.risk_multiple,
        reference_source=invalidation_levels.reference_source,
    )


__all__ = [
    "append_engine_d_log",
    "build_engine_d_gate_reason_codes",
    "build_engine_d_invalidation",
    "build_engine_d_no_trade_output",
]
