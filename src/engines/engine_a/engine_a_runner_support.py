"""Small pure helpers supporting the Engine A runner."""

from __future__ import annotations

def _merge_reason_codes(*reason_code_groups: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            code
            for group in reason_code_groups
            for code in group
            if code
        )
    )


def build_engine_a_gate_reason_codes(
    *,
    gate_reason_codes: tuple[str, ...],
    detailed_reason_codes: tuple[str, ...] = (),
) -> tuple[str, ...]:
    """Return Engine A reason codes with explicit gate provenance first.

    Gate 0 = hard-block/runtime-invalid.
    Gate 1 = structure/context setup quality.
    Gate 2 = economics/cost feasibility.
    Gate 3 = downstream scoring/portfolio/risk runtime.
    """

    return _merge_reason_codes(gate_reason_codes, detailed_reason_codes)


def append_engine_a_log(
    logs: list[object],
    log_entry_cls: type[object],
    *,
    event: str,
    pair: str,
    regime: str,
    raw_score: float = 0.0,
    penalized_score: float = 0.0,
    block_scores: dict[str, float] | None = None,
    expected_cost: float = 0.0,
    ce_expected: float = 0.0,
    ev_net: float = 0.0,
    conviction: str = "",
    tier: str = "",
    invalidation: str = "",
    holding_hours: float = 0.0,
    reasons: tuple[str, ...] = (),
    scoring_version: str = "",
) -> None:
    """Append one structured Engine A log entry."""

    logs.append(
        log_entry_cls(
            event=event,
            pair=pair,
            regime=regime,
            raw_score=raw_score,
            penalized_score=penalized_score,
            block_scores={} if block_scores is None else block_scores,
            expected_cost=expected_cost,
            ce_expected=ce_expected,
            ev_net=ev_net,
            conviction=conviction,
            tier=tier,
            invalidation=invalidation,
            holding_hours=holding_hours,
            reasons=reasons,
            scoring_version=scoring_version,
        )
    )


def build_engine_a_no_trade_output(
    output_cls: type[object],
    *,
    decision_no_trade: object,
    inputs: object,
    logs: list[object],
    no_trade_reasons: list[object],
    reason_codes: tuple[str, ...] = (),
    raw_score: float = 0.0,
    block_scores: dict[str, float] | None = None,
    conviction: object,
    tier_suggestion: object,
    structure_verdict: object,
    context_verdict: object,
    cost_verdict: object,
    expected_cost: float = 0.0,
    ce_expected: float = 0.0,
    ev_net: float = 0.0,
) -> object:
    """Build a canonical Engine A no-trade output."""

    return output_cls(
        pair=inputs.pair,
        decision=decision_no_trade,
        raw_score=raw_score,
        block_scores={} if block_scores is None else block_scores,
        conviction=conviction,
        tier_suggestion=tier_suggestion,
        structure_verdict=structure_verdict,
        context_verdict=context_verdict,
        cost_verdict=cost_verdict,
        expected_cost=expected_cost,
        ce_expected=ce_expected,
        ev_net=ev_net,
        no_trade_reasons=tuple(no_trade_reasons),
        reason_codes=reason_codes,
        scoring_version=inputs.scoring_version,
        log_entries=tuple(logs),
    )


def early_exit_engine_a_no_trade(
    output_cls: type[object],
    log_entry_cls: type[object],
    *,
    decision_no_trade: object,
    inputs: object,
    logs: list[object],
    no_trade_reasons: list[object],
    reason: object,
    reason_codes: tuple[str, ...] = (),
    log_reasons: tuple[str, ...] | None = None,
    raw_score: float = 0.0,
    block_scores: dict[str, float] | None = None,
    conviction: object,
    tier_suggestion: object,
    structure_verdict: object,
    context_verdict: object,
    cost_verdict: object,
    expected_cost: float = 0.0,
    ce_expected: float = 0.0,
    ev_net: float = 0.0,
) -> object:
    """Append the terminal no-trade log and build the canonical output."""

    no_trade_reasons.append(reason)
    append_engine_a_log(
        logs,
        log_entry_cls,
        event="engine_a_no_trade",
        pair=inputs.pair,
        regime=inputs.regime,
        reasons=(
            reason_codes
            if log_reasons is None and reason_codes
            else tuple(str(recorded_reason) for recorded_reason in no_trade_reasons)
            if log_reasons is None
            else log_reasons
        ),
    )
    return build_engine_a_no_trade_output(
        output_cls,
        decision_no_trade=decision_no_trade,
        inputs=inputs,
        logs=logs,
        no_trade_reasons=no_trade_reasons,
        reason_codes=reason_codes,
        raw_score=raw_score,
        block_scores=block_scores,
        conviction=conviction,
        tier_suggestion=tier_suggestion,
        structure_verdict=structure_verdict,
        context_verdict=context_verdict,
        cost_verdict=cost_verdict,
        expected_cost=expected_cost,
        ce_expected=ce_expected,
        ev_net=ev_net,
    )


def build_engine_a_guard_log_reasons(code: str, detail: str) -> tuple[str, ...]:
    """Return stable log reasons for one guarded input failure."""

    return (code, detail)


def build_engine_a_branch_log_reasons(
    reason_codes: tuple[str, ...],
    detail: str | None = None,
) -> tuple[str, ...]:
    """Return stable log reasons for one semantic no-trade branch."""

    return tuple(part for part in (*reason_codes, detail or "") if part)


def build_engine_a_cost_log_reasons(
    *,
    reason_codes: tuple[str, ...],
    reason: str,
    kyle_lambda_cost_uplift: float,
) -> tuple[str, ...]:
    """Return stable cost-stage audit reasons."""

    uplift_detail = (
        f"kyle_lambda_cost_uplift={kyle_lambda_cost_uplift:.6f}"
        if kyle_lambda_cost_uplift > 0.0
        else ""
    )
    return tuple(part for part in (*reason_codes, reason, uplift_detail) if part)


def build_engine_a_emit_reason_codes(
    *,
    structure_verdict: str,
    context_verdict: str,
    cost_verdict: str,
    conviction: str,
) -> tuple[str, ...]:
    """Return stable emit-side reason codes for Engine A."""

    return tuple(
        dict.fromkeys(
            (
                "engine_a.emit.valid",
                f"engine_internal.engine_a.structure.{structure_verdict}",
                f"engine_internal.engine_a.context.{context_verdict}",
                f"economics.engine_a.cost.{cost_verdict}",
                f"scoring.engine_a.conviction.{conviction}",
                f"engine_a.structure.{structure_verdict}",
                f"engine_a.context.{context_verdict}",
                f"engine_a.cost.{cost_verdict}",
                f"engine_a.conviction.{conviction}",
            )
        )
    )


__all__ = [
    "append_engine_a_log",
    "build_engine_a_branch_log_reasons",
    "build_engine_a_cost_log_reasons",
    "build_engine_a_emit_reason_codes",
    "build_engine_a_gate_reason_codes",
    "build_engine_a_guard_log_reasons",
    "build_engine_a_no_trade_output",
    "early_exit_engine_a_no_trade",
]
