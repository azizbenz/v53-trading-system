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
    MicroLiveRunState,
    MicroLiveVerdict,
    ShadowRunState,
    ShadowVerdict,
)
from protocols.errors import MicroLiveInputError


def _validate_shadow_source_payload_scope(payload: TechnicalDashboardPayload) -> None:
    if payload.profile != ProfileId.LIGHT:
        raise MicroLiveInputError(
            "Build-12 Micro-live source payload must stay on profile=LIGHT"
        )
    if payload.runtime_mode != RuntimeMode.SHADOW:
        raise MicroLiveInputError(
            "Build-12 Micro-live source payload must originate from runtime_mode=SHADOW"
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
    onboarding_accepted: bool = False,
    onboarding_review_state: ReviewState = ReviewState.PENDING,
    onboarding_reasons: tuple[str, ...] = (),
) -> MicroLiveInput:
    """Build a governed Build-12 input from Build-11 Shadow outputs."""

    _validate_shadow_source_payload_scope(shadow_payload)
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
        import_artifact_id=shadow_payload.replay_import.artifact_id,
        import_lineage_version=shadow_payload.replay_import.lineage_version,
        import_validation_status=shadow_payload.replay_import.validation_status,
        onboarding_accepted=onboarding_accepted,
        onboarding_review_state=onboarding_review_state,
        onboarding_reasons=onboarding_reasons,
        review_export_ready=shadow_summary.review_export_ready,
        observability_ready=observability_ready,
        halt_ready=halt_ready,
        active_engines=active_engines or shadow_payload.system.active_engines,
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

    if not micro_live_input.onboarding_accepted:
        hard_blocking_reasons.append(
            "strategy onboarding must be accepted before Micro-live"
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
    )


__all__ = [
    "build_micro_live_input_from_shadow",
    "run_micro_live_gate",
]
