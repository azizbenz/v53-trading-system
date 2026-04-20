"""Internal support helpers for the canonical Engine C runner."""

from __future__ import annotations

from collections.abc import Iterable

from .continuation_validator_c import EngineCContinuationValidationResult
from .conviction_builder_c import ConvictionResultC
from .cost_feasibility_c import CostMetricsC
from .engine_c_runner import (
    ConvictionLevelC,
    EngineCDecision,
    EngineCInput,
    EngineCInvalidation,
    EngineCLogEntry,
    EngineCOutput,
    NoTradeReasonC,
    TierSuggestionC,
)
from .invalidation_mapper_c import (
    INVALID_BREAKOUT_LEVEL_CODE,
    INVALID_RISK_MULTIPLE_CODE,
    INVALID_STOP_GE_ENTRY_CODE,
    INVALID_TARGET_LE_ENTRY_CODE,
    InvalidationLevelsC,
    build_invalidation_levels_c,
)
from .output_payload_builder_c import build_engine_c_output_payload
from .structure_resolver_c import build_engine_c_log_context

EngineCStructure = dict[str, float | str | bool]

_ENGINE_C_NO_TRADE_GATE_REASON_CODES: dict[NoTradeReasonC, str] = {
    NoTradeReasonC.NON_LONG_BREAKOUT: "engine_internal.engine_c.breakout.non_long",
    NoTradeReasonC.INVALID_ENTRY_PRICE: "hard_block.engine_c.input.invalid_entry_price",
    NoTradeReasonC.INVALID_CANDIDATE_SIZE: "hard_block.engine_c.input.invalid_candidate_size",
    NoTradeReasonC.INVALID_HOLDING_PERIOD: "hard_block.engine_c.input.invalid_holding_period",
    NoTradeReasonC.INVALID_BREAKOUT_LEVEL: "hard_block.engine_c.input.invalid_breakout_level",
    NoTradeReasonC.INVALID_STOP_GE_ENTRY: "hard_block.engine_c.invalidation.invalid_stop_ge_entry",
    NoTradeReasonC.INVALID_TARGET_LE_ENTRY: "hard_block.engine_c.invalidation.invalid_target_le_entry",
    NoTradeReasonC.INVALID_RISK_MULTIPLE: "hard_block.engine_c.invalidation.invalid_risk_multiple",
    NoTradeReasonC.INVALID_ATR: "hard_block.engine_c.input.invalid_atr",
    NoTradeReasonC.BREAKOUT_UNSTRUCTURED: "engine_internal.engine_c.breakout.unstructured",
    NoTradeReasonC.CONTINUATION_NOT_VIABLE: "engine_internal.engine_c.continuation.not_viable",
    NoTradeReasonC.MICROSTRUCTURE_UNCONFIRMED: "engine_internal.engine_c.microstructure.unconfirmed",
    NoTradeReasonC.FAKE_BREAKOUT_BLOCKED: "engine_internal.engine_c.fake_breakout.blocked",
    NoTradeReasonC.COST_INFEASIBLE: "economics.engine_c.cost.infeasible",
    NoTradeReasonC.DUPLICATION_BLOCKED: "portfolio.engine_c.duplication.blocked",
    NoTradeReasonC.LOW_CONVICTION: "scoring.engine_c.conviction.low",
}


def _merge_reason_codes(*reason_groups: Iterable[str]) -> tuple[str, ...]:
    merged: list[str] = []
    seen: set[str] = set()
    for group in reason_groups:
        for reason in group:
            normalized = reason.strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            merged.append(normalized)
    return tuple(merged)


def _extract_structured_reason_codes(
    logs: list[EngineCLogEntry],
    *,
    event: str,
) -> tuple[str, ...]:
    for entry in reversed(logs):
        if entry.event != event:
            continue
        return tuple(
            reason.strip()
            for reason in entry.reasons
            if reason.strip() and not any(char.isspace() for char in reason.strip())
        )
    return ()


def build_engine_c_reason_codes(
    *,
    structure: EngineCStructure,
    no_trade_reasons: tuple[NoTradeReasonC, ...] = (),
    conviction: str = "",
    tier: str = "",
    microstructure_gate_applied: bool = False,
    microstructure_required: bool = False,
    microstructure_missing: bool = False,
    microstructure_contradictory: bool = False,
    invalidation_present: bool = False,
    cost_feasible: bool = False,
    log_entries: list[EngineCLogEntry] | None = None,
) -> tuple[str, ...]:
    """Return Engine C reason codes with explicit gate provenance first.

    Gate 0 = hard-block coordination/runtime-invalid.
    Gate 1 = breakout/continuation/microstructure validity.
    Gate 2 = economics/cost feasibility.
    Gate 3 = downstream scoring/portfolio/risk runtime.
    """

    breakout_type = str(structure.get("breakout_type", "")).strip()
    continuation_context = str(structure.get("continuation_context", "")).strip()
    local_duplication_policy_triggered = bool(
        structure.get("local_duplication_policy_triggered", structure.get("duplication_blocked", False))
    )
    if microstructure_missing:
        microstructure_code = "engine_c.microstructure.missing"
    elif microstructure_contradictory:
        microstructure_code = "engine_c.microstructure.contradictory"
    elif microstructure_gate_applied:
        microstructure_code = "engine_c.microstructure.confirmed"
    elif microstructure_required:
        microstructure_code = "engine_c.microstructure.required"
    else:
        microstructure_code = "engine_c.microstructure.not_applied"
    structured_log_reasons = ()
    if log_entries is not None:
        structured_log_reasons = _extract_structured_reason_codes(
            log_entries,
            event="engine_c_no_trade" if no_trade_reasons else "engine_c_emit",
        )
    return _merge_reason_codes(
        tuple(
            _ENGINE_C_NO_TRADE_GATE_REASON_CODES[reason]
            for reason in no_trade_reasons
            if reason in _ENGINE_C_NO_TRADE_GATE_REASON_CODES
        ),
        (
            f"engine_c.no_trade.{reason.value}"
            for reason in no_trade_reasons
        ),
        ((f"engine_internal.engine_c.breakout.{breakout_type}",) if breakout_type else ()),
        ((f"engine_c.breakout.{breakout_type}",) if breakout_type else ()),
        ((f"engine_internal.engine_c.continuation.{continuation_context}",) if continuation_context else ()),
        ((f"engine_c.continuation.{continuation_context}",) if continuation_context else ()),
        ((f"scoring.engine_c.conviction.{conviction}",) if conviction else ()),
        ((f"engine_c.conviction.{conviction}",) if conviction else ()),
        ((f"engine_c.tier.{tier}",) if tier else ()),
        (microstructure_code,),
        (("economics.engine_c.cost.feasible",) if cost_feasible else ()),
        (("portfolio.engine_c.duplication.local_policy_triggered",) if local_duplication_policy_triggered else ()),
        (("engine_c.duplication.local_policy_triggered",) if local_duplication_policy_triggered else ()),
        (("engine_c.invalidation.present",) if invalidation_present else ()),
        structured_log_reasons,
    )


def append_engine_c_log(
    logs: list[EngineCLogEntry],
    inputs: EngineCInput,
    structure: EngineCStructure,
    *,
    event: str,
    raw_score: float = 0.0,
    penalized_score: float = 0.0,
    breakout_score: float = 0.0,
    continuation_score: float = 0.0,
    microstructure_gate_applied: bool = False,
    cumulative_ofi: float | None = None,
    queue_pressure: float | None = None,
    vpin: float | None = None,
    kyle_lambda: float | None = None,
    fake_breakout_risk: float = 0.0,
    expected_cost: float = 0.0,
    ce_expected: float = 0.0,
    ev_net: float = 0.0,
    conviction: str = "",
    tier: str = "",
    holding_hours: float = 0.0,
    reasons: tuple[str, ...] = (),
) -> None:
    logs.append(
        EngineCLogEntry(
            event=event,
            pair=inputs.pair,
            regime=inputs.regime,
            **build_engine_c_log_context(structure),
            raw_score=raw_score,
            penalized_score=penalized_score,
            breakout_score=breakout_score,
            continuation_score=continuation_score,
            cumulative_ofi=inputs.cumulative_ofi if cumulative_ofi is None else cumulative_ofi,
            queue_pressure=inputs.queue_pressure if queue_pressure is None else queue_pressure,
            vpin=inputs.vpin if vpin is None else vpin,
            kyle_lambda=inputs.kyle_lambda if kyle_lambda is None else kyle_lambda,
            microstructure_gate_applied=microstructure_gate_applied,
            fake_breakout_risk=fake_breakout_risk,
            expected_cost=expected_cost,
            ce_expected=ce_expected,
            ev_net=ev_net,
            conviction=conviction,
            tier=tier,
            holding_hours=holding_hours,
            reasons=reasons,
            scoring_version=inputs.scoring_version,
        )
    )


def build_engine_c_no_trade_output(
    inputs: EngineCInput,
    structure: EngineCStructure,
    logs: list[EngineCLogEntry],
    no_trade_reasons: list[NoTradeReasonC],
    *,
    raw_score: float = 0.0,
    penalized_score: float = 0.0,
    breakout_score: float = 0.0,
    continuation_score: float = 0.0,
    microstructure_gate_applied: bool = False,
    microstructure_required: bool = False,
    microstructure_missing: bool = False,
    microstructure_contradictory: bool = False,
    fake_breakout_risk: float = 0.0,
    expected_cost: float = 0.0,
    ce_expected: float = 0.0,
    ev_net: float = 0.0,
    conviction: str = "",
    tier: str = "",
    cost_feasible: bool = False,
) -> EngineCOutput:
    overrides: dict[str, object] = {}
    if conviction:
        overrides["conviction"] = conviction
    if tier:
        overrides["tier_suggestion"] = tier
    return EngineCOutput(
        pair=inputs.pair,
        decision=EngineCDecision.NO_TRADE,
        **build_engine_c_output_payload(
            structure=structure,
            scoring_version=inputs.scoring_version,
            log_entries=tuple(logs),
            raw_score=raw_score,
            penalized_score=penalized_score,
            breakout_score=breakout_score,
            continuation_score=continuation_score,
            cumulative_ofi=inputs.cumulative_ofi,
            queue_pressure=inputs.queue_pressure,
            vpin=inputs.vpin,
            kyle_lambda=inputs.kyle_lambda,
            microstructure_gate_applied=microstructure_gate_applied,
            microstructure_required=microstructure_required,
            microstructure_missing=microstructure_missing,
            microstructure_contradictory=microstructure_contradictory,
            fake_breakout_risk=fake_breakout_risk,
            expected_cost=expected_cost,
            ce_expected=ce_expected,
            ev_net=ev_net,
            reason_codes=build_engine_c_reason_codes(
                structure=structure,
                no_trade_reasons=tuple(no_trade_reasons),
                conviction=conviction,
                tier=tier,
                microstructure_gate_applied=microstructure_gate_applied,
                microstructure_required=microstructure_required,
                microstructure_missing=microstructure_missing,
                microstructure_contradictory=microstructure_contradictory,
                cost_feasible=cost_feasible,
                log_entries=logs,
            ),
            no_trade_reasons=tuple(no_trade_reasons),
            **overrides,
        ),
    )


def build_engine_c_invalidation(invalidation_levels: InvalidationLevelsC) -> EngineCInvalidation:
    return EngineCInvalidation(
        stop_price=invalidation_levels.stop_price,
        target_price=invalidation_levels.target_price,
        risk_multiple=invalidation_levels.risk_multiple,
        reference_source=invalidation_levels.reference_source,
    )


def _resolve_invalidation_error_code(error: ValueError) -> str:
    message = str(error).strip()
    if ":" not in message:
        return INVALID_BREAKOUT_LEVEL_CODE
    return message.split(":", 1)[0].strip() or INVALID_BREAKOUT_LEVEL_CODE


def _resolve_invalidation_no_trade_reason(error: ValueError) -> NoTradeReasonC:
    return {
        INVALID_BREAKOUT_LEVEL_CODE: NoTradeReasonC.INVALID_BREAKOUT_LEVEL,
        INVALID_STOP_GE_ENTRY_CODE: NoTradeReasonC.INVALID_STOP_GE_ENTRY,
        INVALID_TARGET_LE_ENTRY_CODE: NoTradeReasonC.INVALID_TARGET_LE_ENTRY,
        INVALID_RISK_MULTIPLE_CODE: NoTradeReasonC.INVALID_RISK_MULTIPLE,
    }.get(_resolve_invalidation_error_code(error), NoTradeReasonC.INVALID_BREAKOUT_LEVEL)


def _build_invalid_invalidation_no_trade_output(
    inputs: EngineCInput,
    structure: EngineCStructure,
    logs: list[EngineCLogEntry],
    *,
    breakout_score: float,
    continuation_validation: EngineCContinuationValidationResult,
    fake_breakout_risk: float,
    cost_metrics: CostMetricsC,
    conviction: ConvictionLevelC,
    tier: TierSuggestionC,
    conviction_result: ConvictionResultC,
    error: ValueError,
) -> EngineCOutput:
    invalidation_reason = _resolve_invalidation_no_trade_reason(error)
    structured_reason_code = f"engine_c.invalidation.{invalidation_reason.value}"
    no_trade_reasons = [invalidation_reason]
    append_engine_c_log(
        logs,
        inputs,
        structure,
        event="engine_c_no_trade",
        raw_score=conviction_result.raw_score,
        penalized_score=conviction_result.conviction_score,
        breakout_score=breakout_score,
        continuation_score=continuation_validation.continuation_score,
        microstructure_gate_applied=continuation_validation.microstructure_gate_applied,
        fake_breakout_risk=fake_breakout_risk,
        expected_cost=cost_metrics.expected_cost,
        ce_expected=cost_metrics.ce_expected,
        ev_net=cost_metrics.ev_net,
        conviction=conviction.value,
        tier=tier.value,
        reasons=(structured_reason_code, str(error)),
    )
    return build_engine_c_no_trade_output(
        inputs,
        structure,
        logs,
        no_trade_reasons,
        raw_score=conviction_result.raw_score,
        penalized_score=conviction_result.conviction_score,
        breakout_score=breakout_score,
        continuation_score=continuation_validation.continuation_score,
        microstructure_gate_applied=continuation_validation.microstructure_gate_applied,
        microstructure_required=continuation_validation.microstructure_required,
        microstructure_missing=continuation_validation.microstructure_missing,
        microstructure_contradictory=continuation_validation.microstructure_contradictory,
        fake_breakout_risk=fake_breakout_risk,
        expected_cost=cost_metrics.expected_cost,
        ce_expected=cost_metrics.ce_expected,
        ev_net=cost_metrics.ev_net,
        conviction=conviction.value,
        tier=tier.value,
        cost_feasible=True,
    )


def build_engine_c_emit_output(
    inputs: EngineCInput,
    structure: EngineCStructure,
    logs: list[EngineCLogEntry],
    *,
    breakout_score: float,
    context_score: float,
    continuation_validation: EngineCContinuationValidationResult,
    fake_breakout_risk: float,
    cost_metrics: CostMetricsC,
    conviction_result: ConvictionResultC,
) -> EngineCOutput:
    conviction = ConvictionLevelC(conviction_result.conviction_name)
    tier = TierSuggestionC(conviction_result.tier_name)
    try:
        invalidation_levels = build_invalidation_levels_c(
            entry_price=inputs.entry_price,
            breakout_level=inputs.breakout_level,
            realized_vol_current=inputs.realized_vol_current,
            realized_vol_at_break=inputs.realized_vol_at_break,
            expected_gain=inputs.expected_gain,
        )
    except ValueError as exc:
        return _build_invalid_invalidation_no_trade_output(
            inputs,
            structure,
            logs,
            breakout_score=breakout_score,
            continuation_validation=continuation_validation,
            fake_breakout_risk=fake_breakout_risk,
            cost_metrics=cost_metrics,
            conviction=conviction,
            tier=tier,
            conviction_result=conviction_result,
            error=exc,
        )

    invalidation = build_engine_c_invalidation(invalidation_levels)
    block_scores = {
        "breakout": breakout_score,
        "continuation": continuation_validation.continuation_score,
        "context": context_score,
        "ce_component": conviction_result.ce_component,
        "fake_breakout_risk": fake_breakout_risk,
        "cost_preference": cost_metrics.cost_preference_score,
    }
    append_engine_c_log(
        logs,
        inputs,
        structure,
        event="engine_c_emit",
        raw_score=conviction_result.raw_score,
        penalized_score=conviction_result.conviction_score,
        breakout_score=breakout_score,
        continuation_score=continuation_validation.continuation_score,
        microstructure_gate_applied=continuation_validation.microstructure_gate_applied,
        fake_breakout_risk=fake_breakout_risk,
        expected_cost=cost_metrics.expected_cost,
        ce_expected=cost_metrics.ce_expected,
        ev_net=cost_metrics.ev_net,
        conviction=conviction.value,
        tier=tier.value,
        holding_hours=inputs.holding_period,
    )
    return EngineCOutput(
        pair=inputs.pair,
        decision=EngineCDecision.EMIT,
        **build_engine_c_output_payload(
            structure=structure,
            scoring_version=inputs.scoring_version,
            log_entries=tuple(logs),
            raw_score=conviction_result.raw_score,
            penalized_score=conviction_result.conviction_score,
            block_scores=block_scores,
            conviction=conviction,
            tier_suggestion=tier,
            breakout_score=breakout_score,
            continuation_score=continuation_validation.continuation_score,
            cumulative_ofi=inputs.cumulative_ofi,
            queue_pressure=inputs.queue_pressure,
            vpin=inputs.vpin,
            kyle_lambda=inputs.kyle_lambda,
            microstructure_gate_applied=continuation_validation.microstructure_gate_applied,
            microstructure_required=continuation_validation.microstructure_required,
            microstructure_missing=continuation_validation.microstructure_missing,
            microstructure_contradictory=continuation_validation.microstructure_contradictory,
            fake_breakout_risk=fake_breakout_risk,
            expected_cost=cost_metrics.expected_cost,
            ce_expected=cost_metrics.ce_expected,
            ev_net=cost_metrics.ev_net,
            invalidation=invalidation,
            holding_hours=inputs.holding_period,
            reason_codes=build_engine_c_reason_codes(
                structure=structure,
                conviction=conviction.value,
                tier=tier.value,
                microstructure_gate_applied=continuation_validation.microstructure_gate_applied,
                microstructure_required=continuation_validation.microstructure_required,
                microstructure_missing=continuation_validation.microstructure_missing,
                microstructure_contradictory=continuation_validation.microstructure_contradictory,
                invalidation_present=True,
                cost_feasible=True,
            ),
        ),
    )


def evaluate_engine_c_input_guards(
    inputs: EngineCInput,
    structure: EngineCStructure,
    logs: list[EngineCLogEntry],
    no_trade_reasons: list[NoTradeReasonC],
) -> EngineCOutput | None:
    if inputs.entry_price <= 0.0:
        no_trade_reasons.append(NoTradeReasonC.INVALID_ENTRY_PRICE)
        append_engine_c_log(logs, inputs, structure, event="engine_c_no_trade", reasons=("entry_price must be > 0",))
        return build_engine_c_no_trade_output(inputs, structure, logs, no_trade_reasons)
    if inputs.candidate_size <= 0.0:
        no_trade_reasons.append(NoTradeReasonC.INVALID_CANDIDATE_SIZE)
        append_engine_c_log(logs, inputs, structure, event="engine_c_no_trade", reasons=("candidate_size must be > 0",))
        return build_engine_c_no_trade_output(inputs, structure, logs, no_trade_reasons)
    if inputs.holding_period <= 0.0:
        no_trade_reasons.append(NoTradeReasonC.INVALID_HOLDING_PERIOD)
        append_engine_c_log(logs, inputs, structure, event="engine_c_no_trade", reasons=("holding_period must be > 0",))
        return build_engine_c_no_trade_output(inputs, structure, logs, no_trade_reasons)
    if inputs.breakout_level <= 0.0:
        no_trade_reasons.append(NoTradeReasonC.INVALID_BREAKOUT_LEVEL)
        append_engine_c_log(logs, inputs, structure, event="engine_c_no_trade", reasons=("breakout_level must be > 0",))
        return build_engine_c_no_trade_output(inputs, structure, logs, no_trade_reasons)
    if inputs.atr < 0.0:
        no_trade_reasons.append(NoTradeReasonC.INVALID_ATR)
        append_engine_c_log(logs, inputs, structure, event="engine_c_no_trade", reasons=("atr must be >= 0",))
        return build_engine_c_no_trade_output(inputs, structure, logs, no_trade_reasons)
    return None


def evaluate_engine_c_duplication_policy(
    inputs: EngineCInput,
    structure: EngineCStructure,
    logs: list[EngineCLogEntry],
    no_trade_reasons: list[NoTradeReasonC],
    *,
    breakout_score: float,
    continuation_validation: EngineCContinuationValidationResult,
    fake_breakout_risk: float,
    cost_metrics: CostMetricsC,
    microstructure_required: bool,
    microstructure_missing: bool,
    microstructure_contradictory: bool,
) -> EngineCOutput | None:
    if not bool(structure["duplication_blocked"]):
        return None
    append_engine_c_log(
        logs,
        inputs,
        structure,
        event="engine_c_duplication_policy_observed",
        breakout_score=breakout_score,
        continuation_score=continuation_validation.continuation_score,
        microstructure_gate_applied=continuation_validation.microstructure_gate_applied,
        fake_breakout_risk=fake_breakout_risk,
        expected_cost=cost_metrics.expected_cost,
        ce_expected=cost_metrics.ce_expected,
        ev_net=cost_metrics.ev_net,
        reasons=(
            "engine_c.duplication.local_policy_triggered",
            "duplication with engine_a plus non_positive_marginal_gain",
        ),
    )
    return None


__all__ = [
    "append_engine_c_log",
    "build_engine_c_emit_output",
    "build_engine_c_invalidation",
    "build_engine_c_no_trade_output",
    "build_engine_c_reason_codes",
    "evaluate_engine_c_duplication_policy",
    "evaluate_engine_c_input_guards",
]
