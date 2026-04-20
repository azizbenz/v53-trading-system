"""Minimal governed Build-13 Live-Light gate and execution-intent builder.

HARD STATEMENT §0.6: 30j shadow prerequisite enforced before Live-Light.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path

from interface_contracts import (
    Build14InfluenceSignal,
    OperatorSafingRequest,
    PromotionState,
    ReviewState,
    RuntimeMode,
)
from monitoring import TechnicalDashboardPayload
from protocols.contracts import (
    LiveLightDecision,
    LiveLightExecutionIntent,
    LiveLightInput,
    LiveLightRunSummary,
    MicroLiveRunSummary,
)
from protocols.enums import (
    LiveLightRunState,
    LiveLightVerdict,
    MicroLiveRunState,
    MicroLiveVerdict,
)
from protocols.errors import LiveLightInputError
from protocols.live_light_runtime_gate_support import (
    _build_live_light_import_fields,
    _build_live_light_runtime_fields,
    _format_operator_safing_reason,
    _governance_envelope_blocking_reasons,
    _live_surface_budget_blocking_reasons,
    _micro_live_surface_blocking_reasons,
    _resolve_shadow_surface,
    _rollout_temporal_blocking_reasons,
    _shadow_engine_scope_blocking_reasons,
    _shadow_portfolio_blocking_reasons,
)
from protocols.live_light_runtime_support import (
    _build14_guardrail_reasons,
    _build14_reason_codes,
    _normalized_value,
    _resolve_validated_build14_signal,
    _validate_live_light_surface,
    _validate_micro_live_consistency,
    _validate_micro_live_source_payload_scope,
)
from protocols.runtime_signal_support import run_idle_runtime, runtime_cli_main
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

def build_live_light_input_from_micro_live(
    micro_live_summary: MicroLiveRunSummary,
    micro_live_payload: TechnicalDashboardPayload,
    *,
    live_pairs: tuple[str, ...],
    requested_total_notional_usdt: float,
    requested_pair_notional_usdt: float,
    max_total_notional_usdt: float,
    max_pair_notional_usdt: float,
    execution_order_limit: int = 3,
    active_engines: tuple[str, ...] | None = None,
    shadow_days_completed: int | None = None,
    shadow_required_days: int | None = None,
    component_verdicts_rendered: bool | None = None,
    shadow_report_ready: bool | None = None,
    micro_live_stable_days: int,
    micro_live_required_days: int = 7,
    build14_live_eligible: bool = False,
    observability_ready: bool = False,
    halt_ready: bool = False,
    operator_safing_request: OperatorSafingRequest | None = None,
    execution_ready: bool = False,
    broker_ready: bool = False,
    exchange_ready: bool = False,
    onboarding_accepted: bool = False,
    onboarding_review_state: ReviewState = ReviewState.PENDING,
    onboarding_reasons: tuple[str, ...] = (),
) -> LiveLightInput:
    """Build a governed Build-13 input from Build-12 Micro-live outputs."""

    _validate_micro_live_source_payload_scope(micro_live_payload)
    _validate_micro_live_consistency(micro_live_summary, micro_live_payload)
    resolved_shadow_surface = _resolve_shadow_surface(
        micro_live_summary,
        micro_live_payload,
        active_engines=active_engines,
        shadow_days_completed=shadow_days_completed,
        shadow_required_days=shadow_required_days,
        component_verdicts_rendered=component_verdicts_rendered,
        shadow_report_ready=shadow_report_ready,
    )
    _validate_live_light_surface(
        micro_live_summary,
        live_pairs=live_pairs,
        active_engines=resolved_shadow_surface.active_engines,
    )
    return LiveLightInput(
        correlation_id=micro_live_summary.correlation_id,
        profile=micro_live_payload.profile,
        runtime_mode=RuntimeMode.LIVE,
        micro_live_run_id=micro_live_summary.run_id,
        shadow_run_id=micro_live_summary.shadow_run_id,
        micro_live_verdict=micro_live_summary.decision.verdict,
        micro_live_run_state=micro_live_summary.run_state,
        micro_live_blocking_reasons=micro_live_summary.decision.blocking_reasons,
        shadow_days_completed=resolved_shadow_surface.shadow_days_completed,
        shadow_required_days=resolved_shadow_surface.shadow_required_days,
        component_verdicts_rendered=resolved_shadow_surface.component_verdicts_rendered,
        shadow_report_ready=resolved_shadow_surface.shadow_report_ready,
        shadow_promotable_engines=micro_live_summary.shadow_promotable_engines,
        shadow_shadow_only_engines=micro_live_summary.shadow_shadow_only_engines,
        shadow_rewrite_required_engines=micro_live_summary.shadow_rewrite_required_engines,
        shadow_portfolio_judgment=micro_live_summary.shadow_portfolio_judgment,
        micro_live_planned_engines=micro_live_summary.execution_plan.planned_engines,
        micro_live_planned_pairs=micro_live_summary.execution_plan.planned_pairs,
        micro_live_stable_days=micro_live_stable_days,
        micro_live_required_days=micro_live_required_days,
        build14_live_eligible=build14_live_eligible,
        micro_live_import_artifact_id=micro_live_summary.import_artifact_id,
        micro_live_import_lineage_version=micro_live_summary.import_lineage_version,
        onboarding_accepted=onboarding_accepted,
        onboarding_review_state=onboarding_review_state,
        onboarding_reasons=onboarding_reasons,
        review_export_ready=micro_live_payload.shadow.review_export_ready,
        observability_ready=observability_ready,
        halt_ready=halt_ready,
        operator_safing_request=operator_safing_request,
        execution_ready=execution_ready,
        broker_ready=broker_ready,
        exchange_ready=exchange_ready,
        active_engines=resolved_shadow_surface.active_engines,
        live_pairs=live_pairs,
        requested_total_notional_usdt=requested_total_notional_usdt,
        requested_pair_notional_usdt=requested_pair_notional_usdt,
        max_total_notional_usdt=max_total_notional_usdt,
        max_pair_notional_usdt=max_pair_notional_usdt,
        execution_order_limit=execution_order_limit,
        **_build_live_light_import_fields(micro_live_payload),
        **_build_live_light_runtime_fields(micro_live_summary),
    )


def _shadow_day_gate_blocking_reasons(
    live_light_input: LiveLightInput,
    shadow_state_dir: Path | None,
) -> tuple[str, ...]:
    if shadow_state_dir is None:
        return ()
    from protocols.shadow_runtime import check_shadow_30j_gate

    gate_passed, report = check_shadow_30j_gate(
        shadow_state_dir,
        profile=live_light_input.profile.value,
    )
    if gate_passed:
        return ()
    days = report.get("consecutive_days", 0)
    return (
        f"HARD STATEMENT: {live_light_input.profile.value} shadow requires 30 consecutive days, "
        f"currently at {days}/30",
    )


def _evaluate_build14_influence(
    live_light_input: LiveLightInput,
    *,
    build14_influence: object | None,
) -> _Build14Evaluation:
    signal, validation_reasons = _resolve_validated_build14_signal(
        build14_influence,
        expected_correlation_id=live_light_input.correlation_id,
    )
    influence_mode = _normalized_value(getattr(signal, "influence_mode", None), "read_only")
    action = _normalized_value(getattr(signal, "action", None), "observe")
    severity = _normalized_value(getattr(signal, "severity", None), "nominal")
    summary = str(getattr(signal, "summary", "")) if signal is not None else ""
    reason_codes = _build14_reason_codes(signal)
    blocking_reasons = list(validation_reasons)
    confidence_penalty_weight = 0.0
    recommended_budget_factor = 1.0
    requires_review = False
    reason_lines: tuple[str, ...] = ()

    if signal is not None and not live_light_input.build14_live_eligible:
        blocking_reasons.append(
            "Build-14 live influence requires explicit post-Shadow live eligibility"
        )
    if signal is not None:
        blocking_reasons.extend(_build14_guardrail_reasons(signal))
        reason_lines = tuple(f"build14 gate: {reason}" for reason in reason_codes)
        if action == "downgrade_confidence":
            confidence_penalty_weight = float(
                getattr(signal, "confidence_penalty_weight", 0.0)
            )
            recommended_budget_factor = float(
                getattr(signal, "recommended_budget_factor", 1.0)
            )
        elif action in {"review_only", "soft_veto"}:
            requires_review = True
            confidence_penalty_weight = float(
                getattr(signal, "confidence_penalty_weight", 0.0)
            )
            recommended_budget_factor = float(
                getattr(signal, "recommended_budget_factor", 1.0)
            )

    return _Build14Evaluation(
        signal=signal,
        blocking_reasons=tuple(blocking_reasons),
        influence_mode=influence_mode,
        action=action,
        severity=severity,
        summary=summary,
        reason_codes=reason_codes,
        confidence_penalty_weight=confidence_penalty_weight,
        recommended_budget_factor=recommended_budget_factor,
        requires_review=requires_review,
        reason_lines=reason_lines,
    )


def _evaluate_micro_live_gate(
    live_light_input: LiveLightInput,
) -> tuple[tuple[str, ...], bool]:
    reasons: list[str] = []
    needs_review = False
    if live_light_input.micro_live_run_state != MicroLiveRunState.READY_TO_PROBE:
        reasons.append(
            "Build-12 Micro-live run must be ready_to_probe before Live-Light"
        )
    if live_light_input.micro_live_verdict == MicroLiveVerdict.BLOCKED:
        reasons.append("Build-12 Micro-live is blocked and cannot open Live-Light")
    elif live_light_input.micro_live_verdict == MicroLiveVerdict.DRY_RUN_ONLY:
        needs_review = True
    reasons.extend(
        f"micro-live gate: {reason}"
        for reason in live_light_input.micro_live_blocking_reasons
    )
    reasons.extend(_rollout_temporal_blocking_reasons(live_light_input))
    reasons.extend(_micro_live_surface_blocking_reasons(live_light_input))
    reasons.extend(_live_surface_budget_blocking_reasons(live_light_input))
    reasons.extend(_shadow_engine_scope_blocking_reasons(live_light_input))
    reasons.extend(
        _shadow_portfolio_blocking_reasons(live_light_input.shadow_portfolio_judgment)
    )
    return tuple(reasons), needs_review


def _import_surface_blocking_reasons(
    live_light_input: LiveLightInput,
) -> tuple[str, ...]:
    reasons: list[str] = []
    normalized_import_status = live_light_input.import_validation_status.strip().casefold()
    if normalized_import_status != "accepted":
        reasons.append("Build-13 Live-Light requires an accepted import_validation_status")
    if live_light_input.import_exported_from != "local":
        reasons.append("Build-13 Live-Light requires import_exported_from=local")
    if live_light_input.import_source_profile != "complete":
        reasons.append("Build-13 Live-Light requires import_source_profile=complete")
    if live_light_input.import_rejection_reasons:
        reasons.append("Build-13 Live-Light requires empty import_rejection_reasons")
    if live_light_input.import_review_state not in {"pending", "approved"}:
        reasons.append(
            "Build-13 Live-Light requires import_review_state to stay pending or approved"
        )
    if not live_light_input.import_dataset_ref:
        reasons.append("Build-13 Live-Light requires import_dataset_ref")
    if not live_light_input.import_clock_ref:
        reasons.append("Build-13 Live-Light requires import_clock_ref")
    if live_light_input.import_activation_stage != "shadow_ready":
        reasons.append("Build-13 Live-Light requires import_activation_stage=shadow_ready")
    if live_light_input.import_health_state != "active":
        reasons.append("Build-13 Live-Light requires import_health_state=active")
    if live_light_input.import_compatibility_status == "rejected":
        reasons.append(
            "Build-13 Live-Light requires a non-rejected import_compatibility_status"
        )
    reasons.extend(
        f"import compatibility gate: {reason}"
        for reason in live_light_input.import_compatibility_reasons
    )
    if not live_light_input.import_feature_lineage_required:
        reasons.append("Build-13 Live-Light requires import_feature_lineage_required=True")
    if not live_light_input.import_feature_lineage_present:
        reasons.append("Build-13 Live-Light requires import_feature_lineage_present=True")
    if live_light_input.import_feature_lineage_status != "ok":
        reasons.append("Build-13 Live-Light requires import_feature_lineage_status=ok")
    reasons.extend(
        f"import feature lineage gate: {reason}"
        for reason in live_light_input.import_feature_lineage_reasons
    )
    if not live_light_input.import_transform_whitelist_required:
        reasons.append(
            "Build-13 Live-Light requires import_transform_whitelist_required=True"
        )
    if not live_light_input.import_transform_whitelist_present:
        reasons.append(
            "Build-13 Live-Light requires import_transform_whitelist_present=True"
        )
    if live_light_input.import_transform_whitelist_status != "ok":
        reasons.append("Build-13 Live-Light requires import_transform_whitelist_status=ok")
    reasons.extend(
        f"import transform whitelist gate: {reason}"
        for reason in live_light_input.import_transform_whitelist_reasons
    )
    if live_light_input.import_signature_check_status != "verified":
        reasons.append(
            "Build-13 Live-Light requires a non-rejected import_signature_check_status"
        )
    reasons.extend(
        f"import signature gate: {reason}"
        for reason in live_light_input.import_signature_check_reasons
    )
    return tuple(reasons)


def _import_contract_blocking_reasons(
    live_light_input: LiveLightInput,
) -> tuple[str, ...]:
    reasons: list[str] = []
    if live_light_input.import_conflict_resolution_mode != "no_trade_then_strictest":
        reasons.append("Build-13 Live-Light requires canonical import_conflict_resolution_mode")
    if live_light_input.import_conflict_hard_veto_action != "no_trade":
        reasons.append("Build-13 Live-Light requires canonical import_conflict_hard_veto_action")
    if live_light_input.import_conflict_score_aggregation_mode != "bounded_sum_with_global_cap":
        reasons.append(
            "Build-13 Live-Light requires canonical import_conflict_score_aggregation_mode"
        )
    if live_light_input.import_conflict_size_reduce_mode != "min_factor_wins":
        reasons.append("Build-13 Live-Light requires canonical import_conflict_size_reduce_mode")
    if live_light_input.import_conflict_rank_adjust_mode != "bounded_sum":
        reasons.append("Build-13 Live-Light requires canonical import_conflict_rank_adjust_mode")
    if not live_light_input.import_conflict_additive_soft_boosts_allowed:
        reasons.append(
            "Build-13 Live-Light requires import_conflict_additive_soft_boosts_allowed=True"
        )
    if not live_light_input.import_conflict_additive_soft_reduces_allowed:
        reasons.append(
            "Build-13 Live-Light requires import_conflict_additive_soft_reduces_allowed=True"
        )
    if live_light_input.import_registry_atomicity_mode != "atomic_snapshot_swap":
        reasons.append("Build-13 Live-Light requires canonical import_registry_atomicity_mode")
    if live_light_input.import_registry_concurrency_model != "single_writer_multi_reader":
        reasons.append(
            "Build-13 Live-Light requires canonical import_registry_concurrency_model"
        )
    if not live_light_input.import_registry_publish_requires_atomic_replace:
        reasons.append(
            "Build-13 Live-Light requires import_registry_publish_requires_atomic_replace=True"
        )
    if not live_light_input.import_registry_publish_requires_fsync:
        reasons.append(
            "Build-13 Live-Light requires import_registry_publish_requires_fsync=True"
        )
    if not live_light_input.import_registry_rollback_to_last_known_good:
        reasons.append(
            "Build-13 Live-Light requires import_registry_rollback_to_last_known_good=True"
        )
    if live_light_input.import_payload_ref_count < 5:
        reasons.append("Build-13 Live-Light requires import_payload_ref_count>=5")
    if not live_light_input.import_payload_bundle_present:
        reasons.append("Build-13 Live-Light requires import_payload_bundle_present=True")
    if not live_light_input.import_review_export_ref:
        reasons.append("Build-13 Live-Light requires import_review_export_ref")
    if not live_light_input.import_feature_bridge_ref:
        reasons.append("Build-13 Live-Light requires import_feature_bridge_ref")
    if not live_light_input.import_parity_diagnostics_ref:
        reasons.append("Build-13 Live-Light requires import_parity_diagnostics_ref")
    if not live_light_input.import_replay_metrics_ref:
        reasons.append("Build-13 Live-Light requires import_replay_metrics_ref")
    if not live_light_input.import_replay_dtr_ref:
        reasons.append("Build-13 Live-Light requires import_replay_dtr_ref")
    if live_light_input.micro_live_import_artifact_id != live_light_input.import_artifact_id:
        reasons.append(
            "Build-13 Live-Light requires matching Micro-live/import artifact_id"
        )
    if (
        live_light_input.micro_live_import_lineage_version
        != live_light_input.import_lineage_version
    ):
        reasons.append(
            "Build-13 Live-Light requires matching Micro-live/import lineage_version"
        )
    return tuple(reasons)


def _operational_blocking_reasons(
    live_light_input: LiveLightInput,
) -> tuple[str, ...]:
    reasons: list[str] = []
    if not live_light_input.onboarding_accepted:
        reasons.append("strategy onboarding must be accepted before Live-Light")
    elif live_light_input.onboarding_review_state not in {
        ReviewState.PENDING,
        ReviewState.APPROVED,
    }:
        reasons.append("accepted onboarding must keep a pending or approved review_state")
    if live_light_input.onboarding_reasons and live_light_input.onboarding_accepted:
        reasons.append("accepted onboarding must not carry rejection reasons")
    if live_light_input.onboarding_review_state in {
        ReviewState.NEEDS_REVISION,
        ReviewState.REJECTED,
    }:
        reasons.append(
            f"onboarding review_state={live_light_input.onboarding_review_state.value} is not eligible for Live-Light"
        )
    reasons.extend(
        f"onboarding gate: {reason}" for reason in live_light_input.onboarding_reasons
    )
    if not live_light_input.review_export_ready:
        reasons.append("Build-11/9X review export must be ready before Live-Light execution")
    if not live_light_input.observability_ready:
        reasons.append("Build-10 observability must be ready before Live-Light execution")
    if not live_light_input.halt_ready:
        reasons.append("operator halt guard must be ready before Live-Light execution")
    if live_light_input.operator_safing_request is not None:
        reasons.append(_format_operator_safing_reason(live_light_input.operator_safing_request))
    if not live_light_input.execution_ready:
        reasons.append("execution readiness must be confirmed before Live-Light execution")
    if not live_light_input.broker_ready:
        reasons.append("broker readiness must be confirmed before Live-Light execution")
    if not live_light_input.exchange_ready:
        reasons.append("exchange readiness must be confirmed before Live-Light execution")
    return tuple(reasons)


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


def _build_live_light_run_summary(
    live_light_input: LiveLightInput,
    *,
    run_id: str | None,
    outcome: _LiveLightOutcome,
    build14_evaluation: _Build14Evaluation,
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
    )


def run_live_light_gate(
    live_light_input: LiveLightInput,
    *,
    run_id: str | None = None,
    build14_influence: object | None = None,
    shadow_state_dir: Path | None = None,
) -> LiveLightRunSummary:
    """Run the minimal Build-13 gate without opening Complete or full live execution.

    HARD STATEMENT §0.6: if shadow_state_dir is provided, verifies 30 consecutive
    shadow days before allowing Live-Light promotion.
    """

    hard_blocking_reasons = list(_governance_envelope_blocking_reasons(live_light_input))
    hard_blocking_reasons.extend(
        _shadow_day_gate_blocking_reasons(live_light_input, shadow_state_dir)
    )
    build14_evaluation = _evaluate_build14_influence(
        live_light_input,
        build14_influence=build14_influence,
    )
    hard_blocking_reasons.extend(build14_evaluation.blocking_reasons)
    micro_live_reasons, micro_live_needs_review = _evaluate_micro_live_gate(
        live_light_input
    )
    hard_blocking_reasons.extend(micro_live_reasons)
    hard_blocking_reasons.extend(_import_surface_blocking_reasons(live_light_input))
    hard_blocking_reasons.extend(_import_contract_blocking_reasons(live_light_input))
    hard_blocking_reasons.extend(_operational_blocking_reasons(live_light_input))

    if hard_blocking_reasons:
        outcome = _build_blocked_outcome(
            live_light_input,
            run_id=run_id,
            blocking_reasons=tuple(hard_blocking_reasons) + build14_evaluation.reason_lines,
        )
    elif micro_live_needs_review or build14_evaluation.requires_review:
        outcome = _build_review_outcome(
            live_light_input,
            run_id=run_id,
            build14_evaluation=build14_evaluation,
            micro_live_needs_review=micro_live_needs_review,
        )
    else:
        outcome = _build_ready_outcome(
            live_light_input,
            run_id=run_id,
            recommended_budget_factor=build14_evaluation.recommended_budget_factor,
        )

    return _build_live_light_run_summary(
        live_light_input,
        run_id=run_id,
        outcome=outcome,
        build14_evaluation=build14_evaluation,
    )


__all__ = [
    "build_live_input_from_micro_live",
    "run_live_gate",
    "build_live_light_input_from_micro_live",
    "run_live_light_gate",
    "run",
    "main",
]


build_live_input_from_micro_live = build_live_light_input_from_micro_live
run_live_gate = run_live_light_gate


def run(*, sleep_seconds: float = 0.1) -> int:
    """Run a cooperative Live-Light runtime shell until shutdown is requested."""

    return run_idle_runtime(__name__, sleep_seconds=sleep_seconds)


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for cooperative Live-Light runtime shutdown handling."""

    return runtime_cli_main(__name__, argv=argv)


if __name__ == "__main__":
    raise SystemExit(main())
