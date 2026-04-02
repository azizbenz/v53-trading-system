"""Minimal governed Build-12 Micro-live gate and plan builder."""

from __future__ import annotations

from interface_contracts import PromotionState, ProfileId, ReviewState, RuntimeMode
from monitoring import TechnicalDashboardPayload
from protocols.contracts import (
    MicroLiveDecision,
    MicroLiveExecutionPlan,
    MicroLiveInput,
    MicroLiveRunSummary,
    ShadowRunSummary,
)
from protocols.enums import (
    ShadowComponentKind,
    ShadowComponentVerdict,
    MicroLiveRunState,
    MicroLiveVerdict,
    ShadowRunState,
    ShadowVerdict,
)
from protocols.errors import MicroLiveInputError


def _format_operator_safing_reason(request) -> str:
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


def _validate_shadow_source_payload_scope(payload: TechnicalDashboardPayload) -> None:
    if payload.profile != ProfileId.LIGHT:
        raise MicroLiveInputError(
            "Build-12 Micro-live source payload must stay on profile=LIGHT"
        )
    if payload.runtime_mode != RuntimeMode.SHADOW:
        raise MicroLiveInputError(
            "Build-12 Micro-live source payload must originate from runtime_mode=SHADOW"
        )


def _validate_shadow_import_consistency(
    shadow_summary: ShadowRunSummary,
    shadow_payload: TechnicalDashboardPayload,
) -> None:
    replay_import = shadow_payload.replay_import
    normalized_status = replay_import.validation_status.strip().casefold()

    if shadow_summary.correlation_id != shadow_payload.correlation_id:
        raise MicroLiveInputError(
            "Build-12 Micro-live requires matching correlation_id between Shadow summary and payload"
        )
    if normalized_status != "accepted":
        raise MicroLiveInputError(
            "Build-12 Micro-live requires an accepted replay import_validation_status"
        )
    if replay_import.rejection_reasons:
        raise MicroLiveInputError(
            "Build-12 Micro-live requires empty replay import_rejection_reasons"
        )
    if not replay_import.artifact_id or replay_import.artifact_id == "none":
        raise MicroLiveInputError(
            "Build-12 Micro-live requires a concrete replay import_artifact_id"
        )
    if not replay_import.lineage_version or replay_import.lineage_version == "n/a":
        raise MicroLiveInputError(
            "Build-12 Micro-live requires a concrete replay lineage_version"
        )
    if shadow_summary.import_artifact_id != replay_import.artifact_id:
        raise MicroLiveInputError(
            "Build-12 Micro-live requires matching Shadow/import artifact_id"
        )
    if shadow_summary.import_lineage_version != replay_import.lineage_version:
        raise MicroLiveInputError(
            "Build-12 Micro-live requires matching Shadow/import lineage_version"
        )


def _resolve_shadow_component_verdicts(
    shadow_summary: ShadowRunSummary,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    if not shadow_summary.component_assessments:
        raise MicroLiveInputError(
            "Build-12 Micro-live requires component verdicts from the Build-11 Shadow report"
        )

    validated_light_engines = tuple(
        assessment.component_id
        for assessment in shadow_summary.component_assessments
        if assessment.component_kind == ShadowComponentKind.ENGINE
        and assessment.component_id in {"engine_a", "engine_b"}
        and assessment.verdict == ShadowComponentVerdict.SHADOW_VALIDATED
    )
    dormant_components = tuple(
        assessment.component_id
        for assessment in shadow_summary.component_assessments
        if assessment.verdict == ShadowComponentVerdict.DORMANT
    )

    if not validated_light_engines:
        raise MicroLiveInputError(
            "Build-12 Micro-live requires at least one SHADOW_VALIDATED Light engine from Build-11"
        )

    return validated_light_engines, dormant_components


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
    operator_safing_request=None,
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
            "Build-12 Micro-live requires inter-engine A/B comparison evidence from Build-11"
        )
    if not shadow_summary.build14_contribution_ready:
        raise MicroLiveInputError(
            "Build-12 Micro-live requires Build-14 contribution evidence from Build-11"
        )
    validated_light_engines, dormant_components = _resolve_shadow_component_verdicts(
        shadow_summary
    )
    resolved_active_engines = active_engines or validated_light_engines
    if not set(resolved_active_engines).issubset(set(validated_light_engines)):
        raise MicroLiveInputError(
            "Build-12 Micro-live active_engines must be SHADOW_VALIDATED in Build-11"
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
        shadow_validated_engines=validated_light_engines,
        shadow_dormant_components=dormant_components,
        shadow_import_artifact_id=shadow_summary.import_artifact_id,
        shadow_import_lineage_version=shadow_summary.import_lineage_version,
        import_artifact_id=shadow_payload.replay_import.artifact_id,
        import_lineage_version=shadow_payload.replay_import.lineage_version,
        import_validation_status=shadow_payload.replay_import.validation_status,
        import_rejection_reasons=shadow_payload.replay_import.rejection_reasons,
        onboarding_accepted=onboarding_accepted,
        onboarding_review_state=onboarding_review_state,
        onboarding_reasons=onboarding_reasons,
        review_export_ready=shadow_summary.review_export_ready,
        observability_ready=observability_ready,
        halt_ready=halt_ready,
        operator_safing_request=operator_safing_request,
        active_engines=resolved_active_engines,
        probe_pairs=probe_pairs,
        requested_total_notional_usdt=requested_total_notional_usdt,
        requested_pair_notional_usdt=requested_pair_notional_usdt,
        max_total_notional_usdt=max_total_notional_usdt,
        max_pair_notional_usdt=max_pair_notional_usdt,
        order_probe_limit=order_probe_limit,
    )


def run_micro_live_gate(
    micro_live_input: MicroLiveInput,
    *,
    run_id: str | None = None,
) -> MicroLiveRunSummary:
    """Run the minimal Build-12 gate without opening Build-13 or full live execution."""

    hard_blocking_reasons: list[str] = []
    shadow_needs_review = False
    normalized_import_status = micro_live_input.import_validation_status.strip().casefold()

    if micro_live_input.shadow_run_state != ShadowRunState.COMPLETED:
        hard_blocking_reasons.append(
            "Build-11 Shadow run must be completed before Micro-live"
        )
    if micro_live_input.shadow_verdict == ShadowVerdict.BLOCKED:
        hard_blocking_reasons.append(
            "Build-11 Shadow is blocked and cannot open Micro-live"
        )
    elif micro_live_input.shadow_verdict == ShadowVerdict.REJECTED:
        hard_blocking_reasons.append("Build-11 Shadow rejected the candidate")
    elif micro_live_input.shadow_verdict == ShadowVerdict.NEEDS_REVIEW:
        shadow_needs_review = True

    if micro_live_input.shadow_blocking_reasons:
        hard_blocking_reasons.extend(
            f"shadow gate: {reason}" for reason in micro_live_input.shadow_blocking_reasons
        )

    if normalized_import_status != "accepted":
        hard_blocking_reasons.append(
            "Build-12 Micro-live requires an accepted import_validation_status"
        )
    if micro_live_input.import_rejection_reasons:
        hard_blocking_reasons.append(
            "Build-12 Micro-live requires empty import_rejection_reasons"
        )
    if micro_live_input.shadow_import_artifact_id != micro_live_input.import_artifact_id:
        hard_blocking_reasons.append(
            "Build-12 Micro-live requires matching Shadow/import artifact_id"
        )
    if (
        micro_live_input.shadow_import_lineage_version
        != micro_live_input.import_lineage_version
    ):
        hard_blocking_reasons.append(
            "Build-12 Micro-live requires matching Shadow/import lineage_version"
        )

    if not micro_live_input.onboarding_accepted:
        hard_blocking_reasons.append(
            "strategy onboarding must be accepted before Micro-live"
        )
    elif micro_live_input.onboarding_review_state not in {
        ReviewState.PENDING,
        ReviewState.APPROVED,
    }:
        hard_blocking_reasons.append(
            "accepted onboarding must keep a pending or approved review_state"
        )
    if micro_live_input.onboarding_reasons and micro_live_input.onboarding_accepted:
        hard_blocking_reasons.append(
            "accepted onboarding must not carry rejection reasons"
        )
    if micro_live_input.onboarding_review_state in {
        ReviewState.NEEDS_REVISION,
        ReviewState.REJECTED,
    }:
        hard_blocking_reasons.append(
            f"onboarding review_state={micro_live_input.onboarding_review_state.value} is not eligible for Micro-live"
        )
    hard_blocking_reasons.extend(
        f"onboarding gate: {reason}" for reason in micro_live_input.onboarding_reasons
    )

    if not micro_live_input.review_export_ready:
        hard_blocking_reasons.append(
            "Build-9X review export must be ready before Micro-live capital exposure"
        )
    if not micro_live_input.observability_ready:
        hard_blocking_reasons.append(
            "Build-10 observability must be ready before Micro-live capital exposure"
        )
    if not micro_live_input.halt_ready:
        hard_blocking_reasons.append(
            "operator halt guard must be ready before Micro-live capital exposure"
        )
    if micro_live_input.operator_safing_request is not None:
        hard_blocking_reasons.append(
            _format_operator_safing_reason(micro_live_input.operator_safing_request)
        )

    if hard_blocking_reasons:
        decision = MicroLiveDecision(
            allowed_to_probe=False,
            verdict=MicroLiveVerdict.BLOCKED,
            normalized_promotion_state=PromotionState.REPLAY_ONLY,
            review_state=ReviewState.NEEDS_REVISION,
            approved_total_notional_usdt=0.0,
            approved_pair_notional_usdt=0.0,
            blocking_reasons=tuple(hard_blocking_reasons),
            manual_review_required=True,
        )
        execution_plan = MicroLiveExecutionPlan(
            plan_id=run_id or f"{micro_live_input.correlation_id}:micro_live_plan",
            import_artifact_id=micro_live_input.import_artifact_id,
            import_lineage_version=micro_live_input.import_lineage_version,
            planned_engines=(),
            planned_pairs=(),
            requested_total_notional_usdt=micro_live_input.requested_total_notional_usdt,
            approved_total_notional_usdt=0.0,
            approved_pair_notional_usdt=0.0,
            order_probe_limit=0,
            dry_run_only=False,
            halt_guard_required=True,
        )
        run_state = MicroLiveRunState.BLOCKED
    elif shadow_needs_review:
        decision = MicroLiveDecision(
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
        )
        execution_plan = MicroLiveExecutionPlan(
            plan_id=run_id or f"{micro_live_input.correlation_id}:micro_live_plan",
            import_artifact_id=micro_live_input.import_artifact_id,
            import_lineage_version=micro_live_input.import_lineage_version,
            planned_engines=micro_live_input.active_engines,
            planned_pairs=micro_live_input.probe_pairs,
            requested_total_notional_usdt=micro_live_input.requested_total_notional_usdt,
            approved_total_notional_usdt=0.0,
            approved_pair_notional_usdt=0.0,
            order_probe_limit=micro_live_input.order_probe_limit,
            dry_run_only=True,
            halt_guard_required=True,
        )
        run_state = MicroLiveRunState.PREPARED
    else:
        decision = MicroLiveDecision(
            allowed_to_probe=True,
            verdict=MicroLiveVerdict.ALLOWED_TO_PROBE,
            normalized_promotion_state=PromotionState.MICRO_LIVE_CANDIDATE,
            review_state=ReviewState.PENDING,
            approved_total_notional_usdt=micro_live_input.requested_total_notional_usdt,
            approved_pair_notional_usdt=micro_live_input.requested_pair_notional_usdt,
            blocking_reasons=(),
            manual_review_required=False,
        )
        execution_plan = MicroLiveExecutionPlan(
            plan_id=run_id or f"{micro_live_input.correlation_id}:micro_live_plan",
            import_artifact_id=micro_live_input.import_artifact_id,
            import_lineage_version=micro_live_input.import_lineage_version,
            planned_engines=micro_live_input.active_engines,
            planned_pairs=micro_live_input.probe_pairs,
            requested_total_notional_usdt=micro_live_input.requested_total_notional_usdt,
            approved_total_notional_usdt=micro_live_input.requested_total_notional_usdt,
            approved_pair_notional_usdt=micro_live_input.requested_pair_notional_usdt,
            order_probe_limit=micro_live_input.order_probe_limit,
            dry_run_only=False,
            halt_guard_required=True,
        )
        run_state = MicroLiveRunState.READY_TO_PROBE

    return MicroLiveRunSummary(
        run_id=run_id or f"{micro_live_input.correlation_id}:micro_live_run",
        correlation_id=micro_live_input.correlation_id,
        run_state=run_state,
        shadow_run_id=micro_live_input.shadow_run_id,
        shadow_verdict=micro_live_input.shadow_verdict,
        decision=decision,
        execution_plan=execution_plan,
        import_artifact_id=micro_live_input.import_artifact_id,
        import_lineage_version=micro_live_input.import_lineage_version,
        observability_ready=micro_live_input.observability_ready,
        halt_ready=micro_live_input.halt_ready,
        onboarding_ready=micro_live_input.onboarding_accepted,
        operator_safing_request=micro_live_input.operator_safing_request,
        shadow_validated_engines=micro_live_input.shadow_validated_engines,
        shadow_dormant_components=micro_live_input.shadow_dormant_components,
    )


__all__ = [
    "build_micro_live_input_from_shadow",
    "run_micro_live_gate",
]
