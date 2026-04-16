"""Minimal governed Build-12 Micro-live gate and plan builder."""

from __future__ import annotations

from dataclasses import dataclass

from interface_contracts import (
    OperatorSafingRequest,
    PromotionState,
    ReviewState,
    RuntimeMode,
)
from monitoring import TechnicalDashboardPayload
from protocols.contracts import (
    MicroLiveDecision,
    MicroLiveExecutionPlan,
    MicroLiveInput,
    MicroLiveRunSummary,
    ShadowRunSummary,
)
from protocols.enums import (
    MicroLiveRunState,
    MicroLiveVerdict,
    ShadowRunState,
    ShadowVerdict,
)
from protocols.errors import MicroLiveInputError
from protocols.micro_live_runtime_support import (
    _governance_envelope_blocking_reasons,
    _probe_surface_blocking_reasons,
    _resolve_shadow_scope,
    _shadow_engine_scope_blocking_reasons,
    _validate_shadow_import_consistency,
    _validate_shadow_source_payload_scope,
    _shadow_portfolio_blocking_reasons,
    _shadow_temporal_blocking_reasons,
)

@dataclass(frozen=True)
class _MicroLiveOutcome:
    decision: MicroLiveDecision
    execution_plan: MicroLiveExecutionPlan
    run_state: MicroLiveRunState


def _format_operator_safing_reason(request: OperatorSafingRequest) -> str:
    target_mode = (
        f" -> {request.target_runtime_mode.value}"
        if request.target_runtime_mode is not None
        else ""
    )
    return (
        "operator safing request: "
        f"{request.action.value} ({request.source_runtime_mode.value}{target_mode}) "
        f"reason={request.reason}"
    )


def _build_micro_live_import_fields(
    shadow_payload: TechnicalDashboardPayload,
) -> dict[str, object]:
    replay_import = shadow_payload.replay_import
    return {
        "import_artifact_id": replay_import.artifact_id,
        "import_exported_from": replay_import.exported_from,
        "import_lineage_version": replay_import.lineage_version,
        "import_validation_status": replay_import.validation_status,
        "import_source_profile": replay_import.source_profile,
        "import_review_state": replay_import.review_state,
        "import_rejection_reasons": replay_import.rejection_reasons,
        "import_dataset_ref": replay_import.dataset_ref,
        "import_clock_ref": replay_import.clock_ref,
        "import_activation_stage": replay_import.activation_stage,
        "import_health_state": replay_import.health_state,
        "import_compatibility_status": replay_import.compatibility_status,
        "import_compatibility_reasons": replay_import.compatibility_reasons,
        "import_feature_lineage_required": replay_import.feature_lineage_required,
        "import_feature_lineage_present": replay_import.feature_lineage_present,
        "import_feature_lineage_status": replay_import.feature_lineage_status,
        "import_feature_lineage_reasons": replay_import.feature_lineage_reasons,
        "import_transform_whitelist_required": replay_import.transform_whitelist_required,
        "import_transform_whitelist_present": replay_import.transform_whitelist_present,
        "import_transform_whitelist_status": replay_import.transform_whitelist_status,
        "import_transform_whitelist_reasons": replay_import.transform_whitelist_reasons,
        "import_signature_check_status": replay_import.signature_check_status,
        "import_signature_check_reasons": replay_import.signature_check_reasons,
        "import_conflict_resolution_mode": replay_import.conflict_resolution_mode,
        "import_conflict_hard_veto_action": replay_import.conflict_hard_veto_action,
        "import_conflict_score_aggregation_mode": replay_import.conflict_score_aggregation_mode,
        "import_conflict_size_reduce_mode": replay_import.conflict_size_reduce_mode,
        "import_conflict_rank_adjust_mode": replay_import.conflict_rank_adjust_mode,
        "import_conflict_additive_soft_boosts_allowed": replay_import.conflict_additive_soft_boosts_allowed,
        "import_conflict_additive_soft_reduces_allowed": replay_import.conflict_additive_soft_reduces_allowed,
        "import_registry_atomicity_mode": replay_import.registry_atomicity_mode,
        "import_registry_concurrency_model": replay_import.registry_concurrency_model,
        "import_registry_publish_requires_atomic_replace": replay_import.registry_publish_requires_atomic_replace,
        "import_registry_publish_requires_fsync": replay_import.registry_publish_requires_fsync,
        "import_registry_rollback_to_last_known_good": replay_import.registry_rollback_to_last_known_good,
        "import_payload_ref_count": replay_import.payload_ref_count,
        "import_payload_bundle_present": replay_import.payload_bundle_present,
        "import_review_export_ref": replay_import.review_export_ref,
        "import_feature_bridge_ref": replay_import.feature_bridge_ref,
        "import_parity_diagnostics_ref": replay_import.parity_diagnostics_ref,
        "import_replay_metrics_ref": replay_import.replay_metrics_ref,
        "import_replay_dtr_ref": replay_import.replay_dtr_ref,
    }


def _build_micro_live_runtime_fields(
    shadow_summary: ShadowRunSummary,
    shadow_payload: TechnicalDashboardPayload,
) -> dict[str, object]:
    execution_runtime_projection_bridge = shadow_payload.execution_runtime_projection_bridge
    return {
        "execution_runtime_projection_ref": execution_runtime_projection_bridge.projection_path,
        "execution_runtime_projection_status": execution_runtime_projection_bridge.projection_status
        or "not_configured",
        "execution_runtime_projection_ready": (
            execution_runtime_projection_bridge.projection_loaded
            and execution_runtime_projection_bridge.projection_status == "ready"
            and execution_runtime_projection_bridge.partial_consumer_count == 0
            and execution_runtime_projection_bridge.blocked_consumer_count == 0
        ),
        "execution_runtime_projection_consumer_count": execution_runtime_projection_bridge.consumer_count,
        "execution_runtime_projection_ready_consumer_count": execution_runtime_projection_bridge.ready_consumer_count,
        "execution_runtime_projection_partial_consumer_count": execution_runtime_projection_bridge.partial_consumer_count,
        "execution_runtime_projection_blocked_consumer_count": execution_runtime_projection_bridge.blocked_consumer_count,
        "regime_lite_governance": shadow_summary.regime_lite_governance,
        "info_stress_governance": shadow_summary.info_stress_governance,
    }


def _evaluate_shadow_gate(
    micro_live_input: MicroLiveInput,
) -> tuple[tuple[str, ...], bool]:
    reasons: list[str] = []
    needs_review = False
    if micro_live_input.shadow_run_state != ShadowRunState.COMPLETED:
        reasons.append("Build-11 Shadow run must be completed before Micro-live")
    if micro_live_input.shadow_verdict == ShadowVerdict.BLOCKED:
        reasons.append("Build-11 Shadow is blocked and cannot open Micro-live")
    elif micro_live_input.shadow_verdict == ShadowVerdict.REJECTED:
        reasons.append("Build-11 Shadow rejected the candidate")
    elif micro_live_input.shadow_verdict == ShadowVerdict.NEEDS_REVIEW:
        needs_review = True
    reasons.extend(
        f"shadow gate: {reason}" for reason in micro_live_input.shadow_blocking_reasons
    )
    reasons.extend(_shadow_temporal_blocking_reasons(micro_live_input))
    reasons.extend(_shadow_engine_scope_blocking_reasons(micro_live_input))
    reasons.extend(_probe_surface_blocking_reasons(micro_live_input))
    reasons.extend(
        _shadow_portfolio_blocking_reasons(micro_live_input.shadow_portfolio_judgment)
    )
    return tuple(reasons), needs_review


def _micro_live_import_surface_blocking_reasons(
    micro_live_input: MicroLiveInput,
) -> tuple[str, ...]:
    reasons: list[str] = []
    normalized_import_status = micro_live_input.import_validation_status.strip().casefold()
    if normalized_import_status != "accepted":
        reasons.append("Build-12 Micro-live requires an accepted import_validation_status")
    if micro_live_input.import_exported_from != "local":
        reasons.append("Build-12 Micro-live requires import_exported_from=local")
    if micro_live_input.import_source_profile != "complete":
        reasons.append("Build-12 Micro-live requires import_source_profile=complete")
    if micro_live_input.import_rejection_reasons:
        reasons.append("Build-12 Micro-live requires empty import_rejection_reasons")
    if micro_live_input.import_review_state not in {"pending", "approved"}:
        reasons.append(
            "Build-12 Micro-live requires import_review_state to stay pending or approved"
        )
    if not micro_live_input.import_dataset_ref:
        reasons.append("Build-12 Micro-live requires import_dataset_ref")
    if not micro_live_input.import_clock_ref:
        reasons.append("Build-12 Micro-live requires import_clock_ref")
    if micro_live_input.import_activation_stage != "shadow_ready":
        reasons.append("Build-12 Micro-live requires import_activation_stage=shadow_ready")
    if micro_live_input.import_health_state != "active":
        reasons.append("Build-12 Micro-live requires import_health_state=active")
    if micro_live_input.import_compatibility_status == "rejected":
        reasons.append(
            "Build-12 Micro-live requires a non-rejected import_compatibility_status"
        )
    reasons.extend(
        f"import compatibility gate: {reason}"
        for reason in micro_live_input.import_compatibility_reasons
    )
    if not micro_live_input.import_feature_lineage_required:
        reasons.append("Build-12 Micro-live requires import_feature_lineage_required=True")
    if not micro_live_input.import_feature_lineage_present:
        reasons.append("Build-12 Micro-live requires import_feature_lineage_present=True")
    if micro_live_input.import_feature_lineage_status != "ok":
        reasons.append("Build-12 Micro-live requires import_feature_lineage_status=ok")
    reasons.extend(
        f"import feature lineage gate: {reason}"
        for reason in micro_live_input.import_feature_lineage_reasons
    )
    if not micro_live_input.import_transform_whitelist_required:
        reasons.append(
            "Build-12 Micro-live requires import_transform_whitelist_required=True"
        )
    if not micro_live_input.import_transform_whitelist_present:
        reasons.append(
            "Build-12 Micro-live requires import_transform_whitelist_present=True"
        )
    if micro_live_input.import_transform_whitelist_status != "ok":
        reasons.append("Build-12 Micro-live requires import_transform_whitelist_status=ok")
    reasons.extend(
        f"import transform whitelist gate: {reason}"
        for reason in micro_live_input.import_transform_whitelist_reasons
    )
    if micro_live_input.import_signature_check_status != "verified":
        reasons.append(
            "Build-12 Micro-live requires a non-rejected import_signature_check_status"
        )
    reasons.extend(
        f"import signature gate: {reason}"
        for reason in micro_live_input.import_signature_check_reasons
    )
    return tuple(reasons)


def _micro_live_import_contract_blocking_reasons(
    micro_live_input: MicroLiveInput,
) -> tuple[str, ...]:
    reasons: list[str] = []
    if micro_live_input.import_conflict_resolution_mode != "no_trade_then_strictest":
        reasons.append("Build-12 Micro-live requires canonical import_conflict_resolution_mode")
    if micro_live_input.import_conflict_hard_veto_action != "no_trade":
        reasons.append("Build-12 Micro-live requires canonical import_conflict_hard_veto_action")
    if micro_live_input.import_conflict_score_aggregation_mode != "bounded_sum_with_global_cap":
        reasons.append(
            "Build-12 Micro-live requires canonical import_conflict_score_aggregation_mode"
        )
    if micro_live_input.import_conflict_size_reduce_mode != "min_factor_wins":
        reasons.append("Build-12 Micro-live requires canonical import_conflict_size_reduce_mode")
    if micro_live_input.import_conflict_rank_adjust_mode != "bounded_sum":
        reasons.append("Build-12 Micro-live requires canonical import_conflict_rank_adjust_mode")
    if not micro_live_input.import_conflict_additive_soft_boosts_allowed:
        reasons.append(
            "Build-12 Micro-live requires import_conflict_additive_soft_boosts_allowed=True"
        )
    if not micro_live_input.import_conflict_additive_soft_reduces_allowed:
        reasons.append(
            "Build-12 Micro-live requires import_conflict_additive_soft_reduces_allowed=True"
        )
    if micro_live_input.import_registry_atomicity_mode != "atomic_snapshot_swap":
        reasons.append("Build-12 Micro-live requires canonical import_registry_atomicity_mode")
    if micro_live_input.import_registry_concurrency_model != "single_writer_multi_reader":
        reasons.append(
            "Build-12 Micro-live requires canonical import_registry_concurrency_model"
        )
    if not micro_live_input.import_registry_publish_requires_atomic_replace:
        reasons.append(
            "Build-12 Micro-live requires import_registry_publish_requires_atomic_replace=True"
        )
    if not micro_live_input.import_registry_publish_requires_fsync:
        reasons.append(
            "Build-12 Micro-live requires import_registry_publish_requires_fsync=True"
        )
    if not micro_live_input.import_registry_rollback_to_last_known_good:
        reasons.append(
            "Build-12 Micro-live requires import_registry_rollback_to_last_known_good=True"
        )
    if micro_live_input.import_payload_ref_count < 5:
        reasons.append("Build-12 Micro-live requires import_payload_ref_count>=5")
    if not micro_live_input.import_payload_bundle_present:
        reasons.append("Build-12 Micro-live requires import_payload_bundle_present=True")
    if not micro_live_input.import_review_export_ref:
        reasons.append("Build-12 Micro-live requires import_review_export_ref")
    if not micro_live_input.import_feature_bridge_ref:
        reasons.append("Build-12 Micro-live requires import_feature_bridge_ref")
    if not micro_live_input.import_parity_diagnostics_ref:
        reasons.append("Build-12 Micro-live requires import_parity_diagnostics_ref")
    if not micro_live_input.import_replay_metrics_ref:
        reasons.append("Build-12 Micro-live requires import_replay_metrics_ref")
    if not micro_live_input.import_replay_dtr_ref:
        reasons.append("Build-12 Micro-live requires import_replay_dtr_ref")
    if micro_live_input.shadow_import_artifact_id != micro_live_input.import_artifact_id:
        reasons.append("Build-12 Micro-live requires matching Shadow/import artifact_id")
    if micro_live_input.shadow_import_lineage_version != micro_live_input.import_lineage_version:
        reasons.append("Build-12 Micro-live requires matching Shadow/import lineage_version")
    return tuple(reasons)


def _micro_live_operational_blocking_reasons(
    micro_live_input: MicroLiveInput,
) -> tuple[str, ...]:
    reasons: list[str] = []
    if not micro_live_input.onboarding_accepted:
        reasons.append("strategy onboarding must be accepted before Micro-live")
    elif micro_live_input.onboarding_review_state not in {
        ReviewState.PENDING,
        ReviewState.APPROVED,
    }:
        reasons.append("accepted onboarding must keep a pending or approved review_state")
    if micro_live_input.onboarding_reasons and micro_live_input.onboarding_accepted:
        reasons.append("accepted onboarding must not carry rejection reasons")
    if micro_live_input.onboarding_review_state in {
        ReviewState.NEEDS_REVISION,
        ReviewState.REJECTED,
    }:
        reasons.append(
            f"onboarding review_state={micro_live_input.onboarding_review_state.value} is not eligible for Micro-live"
        )
    reasons.extend(
        f"onboarding gate: {reason}" for reason in micro_live_input.onboarding_reasons
    )
    if not micro_live_input.review_export_ready:
        reasons.append("Build-9X review export must be ready before Micro-live capital exposure")
    if not micro_live_input.observability_ready:
        reasons.append("Build-10 observability must be ready before Micro-live capital exposure")
    if not micro_live_input.halt_ready:
        reasons.append("operator halt guard must be ready before Micro-live capital exposure")
    if micro_live_input.operator_safing_request is not None:
        reasons.append(_format_operator_safing_reason(micro_live_input.operator_safing_request))
    return tuple(reasons)


def _build_micro_live_execution_plan(
    micro_live_input: MicroLiveInput,
    *,
    run_id: str | None,
    planned_engines: tuple[str, ...],
    planned_pairs: tuple[str, ...],
    approved_total_notional_usdt: float,
    approved_pair_notional_usdt: float,
    order_probe_limit: int,
    dry_run_only: bool,
) -> MicroLiveExecutionPlan:
    return MicroLiveExecutionPlan(
        plan_id=run_id or f"{micro_live_input.correlation_id}:micro_live_plan",
        import_artifact_id=micro_live_input.import_artifact_id,
        import_lineage_version=micro_live_input.import_lineage_version,
        planned_engines=planned_engines,
        planned_pairs=planned_pairs,
        requested_total_notional_usdt=micro_live_input.requested_total_notional_usdt,
        approved_total_notional_usdt=approved_total_notional_usdt,
        approved_pair_notional_usdt=approved_pair_notional_usdt,
        order_probe_limit=order_probe_limit,
        dry_run_only=dry_run_only,
        halt_guard_required=True,
    )


def _build_blocked_micro_live_outcome(
    micro_live_input: MicroLiveInput,
    *,
    run_id: str | None,
    blocking_reasons: tuple[str, ...],
) -> _MicroLiveOutcome:
    return _MicroLiveOutcome(
        decision=MicroLiveDecision(
            allowed_to_probe=False,
            verdict=MicroLiveVerdict.BLOCKED,
            normalized_promotion_state=PromotionState.REPLAY_ONLY,
            review_state=ReviewState.NEEDS_REVISION,
            approved_total_notional_usdt=0.0,
            approved_pair_notional_usdt=0.0,
            blocking_reasons=blocking_reasons,
            manual_review_required=True,
        ),
        execution_plan=_build_micro_live_execution_plan(
            micro_live_input,
            run_id=run_id,
            planned_engines=(),
            planned_pairs=(),
            approved_total_notional_usdt=0.0,
            approved_pair_notional_usdt=0.0,
            order_probe_limit=0,
            dry_run_only=False,
        ),
        run_state=MicroLiveRunState.BLOCKED,
    )


def _build_review_micro_live_outcome(
    micro_live_input: MicroLiveInput,
    *,
    run_id: str | None,
) -> _MicroLiveOutcome:
    return _MicroLiveOutcome(
        decision=MicroLiveDecision(
            allowed_to_probe=False,
            verdict=MicroLiveVerdict.DRY_RUN_ONLY,
            normalized_promotion_state=PromotionState.SHADOW_CANDIDATE,
            review_state=ReviewState.NEEDS_REVISION,
            approved_total_notional_usdt=0.0,
            approved_pair_notional_usdt=0.0,
            blocking_reasons=(
                "Build-11 Shadow verdict must be accepted before Micro-live can probe capital",
            ),
            manual_review_required=True,
        ),
        execution_plan=_build_micro_live_execution_plan(
            micro_live_input,
            run_id=run_id,
            planned_engines=micro_live_input.active_engines,
            planned_pairs=micro_live_input.probe_pairs,
            approved_total_notional_usdt=0.0,
            approved_pair_notional_usdt=0.0,
            order_probe_limit=micro_live_input.order_probe_limit,
            dry_run_only=True,
        ),
        run_state=MicroLiveRunState.PREPARED,
    )


def _build_ready_micro_live_outcome(
    micro_live_input: MicroLiveInput,
    *,
    run_id: str | None,
) -> _MicroLiveOutcome:
    return _MicroLiveOutcome(
        decision=MicroLiveDecision(
            allowed_to_probe=True,
            verdict=MicroLiveVerdict.ALLOWED_TO_PROBE,
            normalized_promotion_state=PromotionState.MICRO_LIVE_CANDIDATE,
            review_state=ReviewState.PENDING,
            approved_total_notional_usdt=micro_live_input.requested_total_notional_usdt,
            approved_pair_notional_usdt=micro_live_input.requested_pair_notional_usdt,
            blocking_reasons=(),
            manual_review_required=False,
        ),
        execution_plan=_build_micro_live_execution_plan(
            micro_live_input,
            run_id=run_id,
            planned_engines=micro_live_input.active_engines,
            planned_pairs=micro_live_input.probe_pairs,
            approved_total_notional_usdt=micro_live_input.requested_total_notional_usdt,
            approved_pair_notional_usdt=micro_live_input.requested_pair_notional_usdt,
            order_probe_limit=micro_live_input.order_probe_limit,
            dry_run_only=False,
        ),
        run_state=MicroLiveRunState.READY_TO_PROBE,
    )


def _build_micro_live_run_summary(
    micro_live_input: MicroLiveInput,
    *,
    run_id: str | None,
    outcome: _MicroLiveOutcome,
) -> MicroLiveRunSummary:
    return MicroLiveRunSummary(
        run_id=run_id or f"{micro_live_input.correlation_id}:micro_live_run",
        correlation_id=micro_live_input.correlation_id,
        run_state=outcome.run_state,
        shadow_run_id=micro_live_input.shadow_run_id,
        shadow_verdict=micro_live_input.shadow_verdict,
        decision=outcome.decision,
        execution_plan=outcome.execution_plan,
        import_artifact_id=micro_live_input.import_artifact_id,
        import_lineage_version=micro_live_input.import_lineage_version,
        execution_runtime_projection_ref=micro_live_input.execution_runtime_projection_ref,
        execution_runtime_projection_status=micro_live_input.execution_runtime_projection_status,
        execution_runtime_projection_ready=micro_live_input.execution_runtime_projection_ready,
        execution_runtime_projection_consumer_count=micro_live_input.execution_runtime_projection_consumer_count,
        execution_runtime_projection_ready_consumer_count=micro_live_input.execution_runtime_projection_ready_consumer_count,
        execution_runtime_projection_partial_consumer_count=micro_live_input.execution_runtime_projection_partial_consumer_count,
        execution_runtime_projection_blocked_consumer_count=micro_live_input.execution_runtime_projection_blocked_consumer_count,
        regime_lite_governance=micro_live_input.regime_lite_governance,
        info_stress_governance=micro_live_input.info_stress_governance,
        observability_ready=micro_live_input.observability_ready,
        halt_ready=micro_live_input.halt_ready,
        onboarding_ready=micro_live_input.onboarding_accepted,
        operator_safing_request=micro_live_input.operator_safing_request,
        shadow_validated_engines=micro_live_input.shadow_validated_engines,
        shadow_dormant_components=micro_live_input.shadow_dormant_components,
        shadow_promotable_engines=micro_live_input.shadow_promotable_engines,
        shadow_shadow_only_engines=micro_live_input.shadow_shadow_only_engines,
        shadow_rewrite_required_engines=micro_live_input.shadow_rewrite_required_engines,
        shadow_portfolio_judgment=micro_live_input.shadow_portfolio_judgment,
    )


def build_micro_live_input_from_shadow(
    shadow_summary: ShadowRunSummary,
    shadow_payload: TechnicalDashboardPayload,
    *,
    probe_pairs: tuple[str, ...],
    requested_total_notional_usdt: float,
    requested_pair_notional_usdt: float,
    max_total_notional_usdt: float,
    max_pair_notional_usdt: float,
    order_probe_limit: int = 3,
    active_engines: tuple[str, ...] | None = None,
    observability_ready: bool = False,
    halt_ready: bool = False,
    operator_safing_request: OperatorSafingRequest | None = None,
    onboarding_accepted: bool = False,
    onboarding_review_state: ReviewState = ReviewState.PENDING,
    onboarding_reasons: tuple[str, ...] = (),
) -> MicroLiveInput:
    """Build a governed Build-12 input from Build-11 Shadow outputs."""

    _validate_shadow_source_payload_scope(shadow_payload)
    _validate_shadow_import_consistency(shadow_summary, shadow_payload)
    if shadow_summary.shadow_days_completed < shadow_summary.shadow_required_days:
        raise MicroLiveInputError(
            "Build-12 Micro-live requires a completed 30-day Shadow"
        )
    if not shadow_summary.shadow_report_ready:
        raise MicroLiveInputError(
            "Build-12 Micro-live requires shadow_report_ready=True"
        )
    if not shadow_summary.inter_engine_comparison_ready:
        raise MicroLiveInputError(
            "Build-12 Micro-live requires inter-engine A/B/C/D comparison evidence from Build-11"
        )
    if not shadow_summary.build14_contribution_ready:
        raise MicroLiveInputError(
            "Build-12 Micro-live requires Build-14 contribution evidence from Build-11"
        )
    resolved_shadow_scope = _resolve_shadow_scope(
        shadow_summary,
        shadow_payload,
        active_engines=active_engines,
    )

    return MicroLiveInput(
        correlation_id=shadow_summary.correlation_id,
        profile=shadow_payload.profile,
        runtime_mode=RuntimeMode.MICRO_LIVE,
        shadow_run_id=shadow_summary.run_id,
        shadow_truth_set_ref=shadow_summary.truth_set_ref,
        shadow_validation_set_ref=shadow_summary.validation_set_ref,
        shadow_verdict=shadow_summary.decision.verdict,
        shadow_run_state=shadow_summary.run_state,
        shadow_blocking_reasons=shadow_summary.decision.blocking_reasons,
        shadow_days_completed=shadow_summary.shadow_days_completed,
        shadow_required_days=shadow_summary.shadow_required_days,
        shadow_report_ready=shadow_summary.shadow_report_ready,
        inter_engine_comparison_ready=shadow_summary.inter_engine_comparison_ready,
        build14_contribution_ready=shadow_summary.build14_contribution_ready,
        shadow_validated_engines=resolved_shadow_scope.validated_engines,
        shadow_dormant_components=resolved_shadow_scope.dormant_components,
        shadow_promotable_engines=resolved_shadow_scope.promotable_engines,
        shadow_shadow_only_engines=resolved_shadow_scope.shadow_only_engines,
        shadow_rewrite_required_engines=resolved_shadow_scope.rewrite_required_engines,
        shadow_portfolio_judgment=resolved_shadow_scope.portfolio_judgment,
        shadow_import_artifact_id=shadow_summary.import_artifact_id,
        shadow_import_lineage_version=shadow_summary.import_lineage_version,
        onboarding_accepted=onboarding_accepted,
        onboarding_review_state=onboarding_review_state,
        onboarding_reasons=onboarding_reasons,
        review_export_ready=shadow_summary.review_export_ready,
        observability_ready=observability_ready,
        halt_ready=halt_ready,
        operator_safing_request=operator_safing_request,
        active_engines=resolved_shadow_scope.active_engines,
        probe_pairs=probe_pairs,
        requested_total_notional_usdt=requested_total_notional_usdt,
        requested_pair_notional_usdt=requested_pair_notional_usdt,
        max_total_notional_usdt=max_total_notional_usdt,
        max_pair_notional_usdt=max_pair_notional_usdt,
        order_probe_limit=order_probe_limit,
        **_build_micro_live_import_fields(shadow_payload),
        **_build_micro_live_runtime_fields(shadow_summary, shadow_payload),
    )


def run_micro_live_gate(
    micro_live_input: MicroLiveInput,
    *,
    run_id: str | None = None,
) -> MicroLiveRunSummary:
    """Run the minimal Build-12 gate without opening Build-13 or full live execution."""

    hard_blocking_reasons = list(_governance_envelope_blocking_reasons(micro_live_input))
    shadow_reasons, shadow_needs_review = _evaluate_shadow_gate(micro_live_input)
    hard_blocking_reasons.extend(shadow_reasons)
    hard_blocking_reasons.extend(
        _micro_live_import_surface_blocking_reasons(micro_live_input)
    )
    hard_blocking_reasons.extend(
        _micro_live_import_contract_blocking_reasons(micro_live_input)
    )
    hard_blocking_reasons.extend(
        _micro_live_operational_blocking_reasons(micro_live_input)
    )

    if hard_blocking_reasons:
        outcome = _build_blocked_micro_live_outcome(
            micro_live_input,
            run_id=run_id,
            blocking_reasons=tuple(hard_blocking_reasons),
        )
    elif shadow_needs_review:
        outcome = _build_review_micro_live_outcome(
            micro_live_input,
            run_id=run_id,
        )
    else:
        outcome = _build_ready_micro_live_outcome(
            micro_live_input,
            run_id=run_id,
        )

    return _build_micro_live_run_summary(
        micro_live_input,
        run_id=run_id,
        outcome=outcome,
    )


__all__ = [
    "build_micro_live_input_from_shadow",
    "run_micro_live_gate",
]
