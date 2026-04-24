"""Outcome builders for the governed Build-13 Live-Light runtime."""

from __future__ import annotations

from dataclasses import dataclass

from interface_contracts import Build14InfluenceSignal, PromotionState, ReviewState
from protocols.contracts import (
    LiveLightDecision,
    LiveLightExecutionIntent,
    LiveLightGateGroupSummary,
    LiveLightInput,
    LiveLightRunSummary,
)
from protocols.enums import LiveLightRunState, LiveLightVerdict


@dataclass(frozen=True)
class _Build14Evaluation:
    signal: Build14InfluenceSignal | None
    blocking_reasons: tuple[str, ...]
    influence_mode: str
    action: str
    severity: str
    summary: str
    reason_codes: tuple[str, ...]
    confidence_penalty_weight: float
    recommended_budget_factor: float
    requires_review: bool
    reason_lines: tuple[str, ...]


@dataclass(frozen=True)
class _LiveLightOutcome:
    decision: LiveLightDecision
    execution_intent: LiveLightExecutionIntent
    run_state: LiveLightRunState


def _build_execution_intent(
    live_light_input: LiveLightInput,
    *,
    run_id: str | None,
    planned_engines: tuple[str, ...],
    planned_pairs: tuple[str, ...],
    approved_total_notional_usdt: float,
    approved_pair_notional_usdt: float,
    execution_order_limit: int,
    dry_run_only: bool,
) -> LiveLightExecutionIntent:
    return LiveLightExecutionIntent(
        intent_id=run_id or f"{live_light_input.correlation_id}:live_light_intent",
        import_artifact_id=live_light_input.import_artifact_id,
        import_lineage_version=live_light_input.import_lineage_version,
        planned_engines=planned_engines,
        planned_pairs=planned_pairs,
        requested_total_notional_usdt=live_light_input.requested_total_notional_usdt,
        approved_total_notional_usdt=approved_total_notional_usdt,
        approved_pair_notional_usdt=approved_pair_notional_usdt,
        execution_order_limit=execution_order_limit,
        dry_run_only=dry_run_only,
        halt_guard_required=True,
        broker_ready_required=True,
        exchange_ready_required=True,
    )


def _build_blocked_outcome(
    live_light_input: LiveLightInput,
    *,
    run_id: str | None,
    blocking_reasons: tuple[str, ...],
) -> _LiveLightOutcome:
    return _LiveLightOutcome(
        decision=LiveLightDecision(
            allowed_to_execute_small=False,
            verdict=LiveLightVerdict.BLOCKED,
            normalized_promotion_state=PromotionState.MICRO_LIVE_CANDIDATE,
            review_state=ReviewState.NEEDS_REVISION,
            approved_total_notional_usdt=0.0,
            approved_pair_notional_usdt=0.0,
            blocking_reasons=blocking_reasons,
            manual_review_required=True,
        ),
        execution_intent=_build_execution_intent(
            live_light_input,
            run_id=run_id,
            planned_engines=(),
            planned_pairs=(),
            approved_total_notional_usdt=0.0,
            approved_pair_notional_usdt=0.0,
            execution_order_limit=0,
            dry_run_only=False,
        ),
        run_state=LiveLightRunState.BLOCKED,
    )


def _build_review_outcome(
    live_light_input: LiveLightInput,
    *,
    run_id: str | None,
    build14_evaluation: _Build14Evaluation,
    micro_live_needs_review: bool,
) -> _LiveLightOutcome:
    review_reasons: list[str] = []
    if micro_live_needs_review:
        review_reasons.append(
            "Build-12 Micro-live verdict must be allowed_to_probe before Live-Light can execute small size"
        )
    if build14_evaluation.signal is not None and build14_evaluation.requires_review:
        review_reasons.append(build14_evaluation.summary)
        review_reasons.extend(build14_evaluation.reason_lines)
    return _LiveLightOutcome(
        decision=LiveLightDecision(
            allowed_to_execute_small=False,
            verdict=LiveLightVerdict.DRY_RUN_ONLY,
            normalized_promotion_state=PromotionState.MICRO_LIVE_CANDIDATE,
            review_state=ReviewState.NEEDS_REVISION,
            approved_total_notional_usdt=0.0,
            approved_pair_notional_usdt=0.0,
            blocking_reasons=tuple(review_reasons),
            manual_review_required=True,
        ),
        execution_intent=_build_execution_intent(
            live_light_input,
            run_id=run_id,
            planned_engines=live_light_input.active_engines,
            planned_pairs=live_light_input.live_pairs,
            approved_total_notional_usdt=0.0,
            approved_pair_notional_usdt=0.0,
            execution_order_limit=live_light_input.execution_order_limit,
            dry_run_only=True,
        ),
        run_state=LiveLightRunState.PREPARED,
    )


def _build_ready_outcome(
    live_light_input: LiveLightInput,
    *,
    run_id: str | None,
    recommended_budget_factor: float,
) -> _LiveLightOutcome:
    approved_total = round(
        live_light_input.requested_total_notional_usdt * recommended_budget_factor,
        8,
    )
    approved_pair = round(
        live_light_input.requested_pair_notional_usdt * recommended_budget_factor,
        8,
    )
    return _LiveLightOutcome(
        decision=LiveLightDecision(
            allowed_to_execute_small=True,
            verdict=LiveLightVerdict.ALLOWED_TO_EXECUTE_SMALL,
            normalized_promotion_state=PromotionState.LIVE_CANDIDATE,
            review_state=ReviewState.PENDING,
            approved_total_notional_usdt=approved_total,
            approved_pair_notional_usdt=approved_pair,
            blocking_reasons=(),
            manual_review_required=False,
        ),
        execution_intent=_build_execution_intent(
            live_light_input,
            run_id=run_id,
            planned_engines=live_light_input.active_engines,
            planned_pairs=live_light_input.live_pairs,
            approved_total_notional_usdt=approved_total,
            approved_pair_notional_usdt=approved_pair,
            execution_order_limit=live_light_input.execution_order_limit,
            dry_run_only=False,
        ),
        run_state=LiveLightRunState.READY_TO_EXECUTE_SMALL,
    )


def _micro_live_review_reasons(micro_live_needs_review: bool) -> tuple[str, ...]:
    if not micro_live_needs_review:
        return ()
    return (
        "Build-12 Micro-live verdict must be allowed_to_probe before Live-Light can execute small size",
    )


def _build14_review_reasons(
    build14_evaluation: _Build14Evaluation,
) -> tuple[str, ...]:
    if build14_evaluation.signal is None or not build14_evaluation.requires_review:
        return ()
    return (build14_evaluation.summary,) + build14_evaluation.reason_lines


def _build14_group_blocking_reasons(
    build14_evaluation: _Build14Evaluation,
) -> tuple[str, ...]:
    if not build14_evaluation.blocking_reasons:
        return ()
    return build14_evaluation.blocking_reasons + build14_evaluation.reason_lines


def _build_gate_group_summary(
    gate_id: str,
    *,
    blocking_reasons: tuple[str, ...] = (),
    review_reasons: tuple[str, ...] = (),
) -> LiveLightGateGroupSummary:
    if blocking_reasons:
        return LiveLightGateGroupSummary(
            gate_id=gate_id,
            status="blocked",
            reasons=blocking_reasons,
        )
    if review_reasons:
        return LiveLightGateGroupSummary(
            gate_id=gate_id,
            status="review_only",
            reasons=review_reasons,
        )
    return LiveLightGateGroupSummary(gate_id=gate_id, status="passed")


def _build_live_light_gate_groups(
    *,
    governance_reasons: tuple[str, ...],
    shadow_day_reasons: tuple[str, ...],
    micro_live_reasons: tuple[str, ...],
    micro_live_needs_review: bool,
    import_surface_reasons: tuple[str, ...],
    import_contract_reasons: tuple[str, ...],
    operational_reasons: tuple[str, ...],
    build14_evaluation: _Build14Evaluation,
) -> tuple[LiveLightGateGroupSummary, ...]:
    return (
        _build_gate_group_summary(
            "governance_envelope",
            blocking_reasons=governance_reasons,
        ),
        _build_gate_group_summary(
            "promotion_history",
            blocking_reasons=shadow_day_reasons + micro_live_reasons,
            review_reasons=_micro_live_review_reasons(micro_live_needs_review),
        ),
        _build_gate_group_summary(
            "import_replay_integrity",
            blocking_reasons=import_surface_reasons + import_contract_reasons,
        ),
        _build_gate_group_summary(
            "operational_readiness",
            blocking_reasons=operational_reasons,
        ),
        _build_gate_group_summary(
            "build14_influence",
            blocking_reasons=_build14_group_blocking_reasons(build14_evaluation),
            review_reasons=_build14_review_reasons(build14_evaluation),
        ),
    )


def _build_live_light_run_summary(
    live_light_input: LiveLightInput,
    *,
    run_id: str | None,
    outcome: _LiveLightOutcome,
    build14_evaluation: _Build14Evaluation,
    gate_groups: tuple[LiveLightGateGroupSummary, ...],
) -> LiveLightRunSummary:
    return LiveLightRunSummary(
        run_id=run_id or f"{live_light_input.correlation_id}:live_light_run",
        correlation_id=live_light_input.correlation_id,
        run_state=outcome.run_state,
        micro_live_run_id=live_light_input.micro_live_run_id,
        shadow_run_id=live_light_input.shadow_run_id,
        micro_live_verdict=live_light_input.micro_live_verdict,
        decision=outcome.decision,
        execution_intent=outcome.execution_intent,
        import_artifact_id=live_light_input.import_artifact_id,
        import_lineage_version=live_light_input.import_lineage_version,
        execution_runtime_projection_ref=live_light_input.execution_runtime_projection_ref,
        execution_runtime_projection_status=live_light_input.execution_runtime_projection_status,
        execution_runtime_projection_ready=live_light_input.execution_runtime_projection_ready,
        execution_runtime_projection_consumer_count=live_light_input.execution_runtime_projection_consumer_count,
        execution_runtime_projection_ready_consumer_count=live_light_input.execution_runtime_projection_ready_consumer_count,
        execution_runtime_projection_partial_consumer_count=live_light_input.execution_runtime_projection_partial_consumer_count,
        execution_runtime_projection_blocked_consumer_count=live_light_input.execution_runtime_projection_blocked_consumer_count,
        regime_lite_governance=live_light_input.regime_lite_governance,
        info_stress_governance=live_light_input.info_stress_governance,
        observability_ready=live_light_input.observability_ready,
        halt_ready=live_light_input.halt_ready,
        operator_safing_request=live_light_input.operator_safing_request,
        execution_ready=live_light_input.execution_ready,
        broker_ready=live_light_input.broker_ready,
        exchange_ready=live_light_input.exchange_ready,
        onboarding_ready=live_light_input.onboarding_accepted,
        build14_influence_mode=build14_evaluation.influence_mode,
        build14_action=build14_evaluation.action,
        build14_severity=build14_evaluation.severity,
        build14_summary=build14_evaluation.summary,
        build14_reason_codes=build14_evaluation.reason_codes,
        build14_confidence_penalty_weight=build14_evaluation.confidence_penalty_weight,
        build14_recommended_budget_factor=build14_evaluation.recommended_budget_factor,
        build14_live_eligible=live_light_input.build14_live_eligible,
        shadow_portfolio_judgment=live_light_input.shadow_portfolio_judgment,
        gate_groups=gate_groups,
    )


__all__ = [
    "_Build14Evaluation",
    "_LiveLightOutcome",
    "_build_blocked_outcome",
    "_build_execution_intent",
    "_build_live_light_gate_groups",
    "_build_live_light_run_summary",
    "_build_ready_outcome",
    "_build_review_outcome",
]
