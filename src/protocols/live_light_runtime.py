"""Minimal governed Build-13 Live-Light gate and execution-intent builder."""

from __future__ import annotations

from interface_contracts import PromotionState, ProfileId, ReviewState, RuntimeMode
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


def _validate_micro_live_source_payload_scope(payload: TechnicalDashboardPayload) -> None:
    if payload.profile != ProfileId.LIGHT:
        raise LiveLightInputError(
            "Build-13 Live-Light source payload must stay on profile=LIGHT"
        )
    if payload.runtime_mode != RuntimeMode.MICRO_LIVE:
        raise LiveLightInputError(
            "Build-13 Live-Light source payload must originate from runtime_mode=MICRO_LIVE"
        )


def _validate_micro_live_consistency(
    micro_live_summary: MicroLiveRunSummary,
    micro_live_payload: TechnicalDashboardPayload,
) -> None:
    replay_import = micro_live_payload.replay_import
    projection = micro_live_payload.micro_live
    normalized_status = replay_import.validation_status.strip().casefold()

    if micro_live_summary.correlation_id != micro_live_payload.correlation_id:
        raise LiveLightInputError(
            "Build-13 Live-Light requires matching correlation_id between Micro-live summary and payload"
        )
    if projection.run_state not in {"", "not_run"} and projection.run_state != micro_live_summary.run_state.value:
        raise LiveLightInputError(
            "Build-13 Live-Light requires matching Micro-live run_state between summary and payload"
        )
    if projection.verdict not in {"", "not_run"} and projection.verdict != micro_live_summary.decision.verdict.value:
        raise LiveLightInputError(
            "Build-13 Live-Light requires matching Micro-live verdict between summary and payload"
        )
    if projection.allowed_to_probe != micro_live_summary.decision.allowed_to_probe:
        raise LiveLightInputError(
            "Build-13 Live-Light requires matching Micro-live allowed_to_probe between summary and payload"
        )
    if projection.shadow_run_id and projection.shadow_run_id != micro_live_summary.shadow_run_id:
        raise LiveLightInputError(
            "Build-13 Live-Light requires matching shadow_run_id between Micro-live summary and payload"
        )
    if projection.import_artifact_id not in {"", "none"} and projection.import_artifact_id != micro_live_summary.import_artifact_id:
        raise LiveLightInputError(
            "Build-13 Live-Light requires matching Micro-live/import artifact_id"
        )
    if projection.import_lineage_version not in {"", "n/a"} and projection.import_lineage_version != micro_live_summary.import_lineage_version:
        raise LiveLightInputError(
            "Build-13 Live-Light requires matching Micro-live/import lineage_version"
        )
    if normalized_status != "accepted":
        raise LiveLightInputError(
            "Build-13 Live-Light requires an accepted replay import_validation_status"
        )
    if replay_import.rejection_reasons:
        raise LiveLightInputError(
            "Build-13 Live-Light requires empty replay import_rejection_reasons"
        )
    if not replay_import.artifact_id or replay_import.artifact_id == "none":
        raise LiveLightInputError(
            "Build-13 Live-Light requires a concrete replay import_artifact_id"
        )
    if not replay_import.lineage_version or replay_import.lineage_version == "n/a":
        raise LiveLightInputError(
            "Build-13 Live-Light requires a concrete replay lineage_version"
        )
    if micro_live_summary.import_artifact_id != replay_import.artifact_id:
        raise LiveLightInputError(
            "Build-13 Live-Light requires matching Micro-live/import artifact_id"
        )
    if micro_live_summary.import_lineage_version != replay_import.lineage_version:
        raise LiveLightInputError(
            "Build-13 Live-Light requires matching Micro-live/import lineage_version"
        )


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
    observability_ready: bool = False,
    halt_ready: bool = False,
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
    return LiveLightInput(
        correlation_id=micro_live_summary.correlation_id,
        profile=micro_live_payload.profile,
        runtime_mode=RuntimeMode.LIVE,
        micro_live_run_id=micro_live_summary.run_id,
        shadow_run_id=micro_live_summary.shadow_run_id,
        micro_live_verdict=micro_live_summary.decision.verdict,
        micro_live_run_state=micro_live_summary.run_state,
        micro_live_blocking_reasons=micro_live_summary.decision.blocking_reasons,
        micro_live_import_artifact_id=micro_live_summary.import_artifact_id,
        micro_live_import_lineage_version=micro_live_summary.import_lineage_version,
        import_artifact_id=micro_live_payload.replay_import.artifact_id,
        import_lineage_version=micro_live_payload.replay_import.lineage_version,
        import_validation_status=micro_live_payload.replay_import.validation_status,
        import_rejection_reasons=micro_live_payload.replay_import.rejection_reasons,
        onboarding_accepted=onboarding_accepted,
        onboarding_review_state=onboarding_review_state,
        onboarding_reasons=onboarding_reasons,
        review_export_ready=micro_live_payload.shadow.review_export_ready,
        observability_ready=observability_ready,
        halt_ready=halt_ready,
        execution_ready=execution_ready,
        broker_ready=broker_ready,
        exchange_ready=exchange_ready,
        active_engines=active_engines or micro_live_summary.execution_plan.planned_engines,
        live_pairs=live_pairs,
        requested_total_notional_usdt=requested_total_notional_usdt,
        requested_pair_notional_usdt=requested_pair_notional_usdt,
        max_total_notional_usdt=max_total_notional_usdt,
        max_pair_notional_usdt=max_pair_notional_usdt,
        execution_order_limit=execution_order_limit,
    )


def run_live_light_gate(
    live_light_input: LiveLightInput,
    *,
    run_id: str | None = None,
) -> LiveLightRunSummary:
    """Run the minimal Build-13 gate without opening Complete or full live execution."""

    hard_blocking_reasons: list[str] = []
    micro_live_needs_review = False
    normalized_import_status = live_light_input.import_validation_status.strip().casefold()

    if live_light_input.micro_live_run_state != MicroLiveRunState.READY_TO_PROBE:
        hard_blocking_reasons.append(
            "Build-12 Micro-live run must be ready_to_probe before Live-Light"
        )
    if live_light_input.micro_live_verdict == MicroLiveVerdict.BLOCKED:
        hard_blocking_reasons.append(
            "Build-12 Micro-live is blocked and cannot open Live-Light"
        )
    elif live_light_input.micro_live_verdict == MicroLiveVerdict.DRY_RUN_ONLY:
        micro_live_needs_review = True

    if live_light_input.micro_live_blocking_reasons:
        hard_blocking_reasons.extend(
            f"micro-live gate: {reason}"
            for reason in live_light_input.micro_live_blocking_reasons
        )

    if normalized_import_status != "accepted":
        hard_blocking_reasons.append(
            "Build-13 Live-Light requires an accepted import_validation_status"
        )
    if live_light_input.import_rejection_reasons:
        hard_blocking_reasons.append(
            "Build-13 Live-Light requires empty import_rejection_reasons"
        )
    if (
        live_light_input.micro_live_import_artifact_id
        != live_light_input.import_artifact_id
    ):
        hard_blocking_reasons.append(
            "Build-13 Live-Light requires matching Micro-live/import artifact_id"
        )
    if (
        live_light_input.micro_live_import_lineage_version
        != live_light_input.import_lineage_version
    ):
        hard_blocking_reasons.append(
            "Build-13 Live-Light requires matching Micro-live/import lineage_version"
        )

    if not live_light_input.onboarding_accepted:
        hard_blocking_reasons.append(
            "strategy onboarding must be accepted before Live-Light"
        )
    elif live_light_input.onboarding_review_state not in {
        ReviewState.PENDING,
        ReviewState.APPROVED,
    }:
        hard_blocking_reasons.append(
            "accepted onboarding must keep a pending or approved review_state"
        )
    if live_light_input.onboarding_reasons and live_light_input.onboarding_accepted:
        hard_blocking_reasons.append(
            "accepted onboarding must not carry rejection reasons"
        )
    if live_light_input.onboarding_review_state in {
        ReviewState.NEEDS_REVISION,
        ReviewState.REJECTED,
    }:
        hard_blocking_reasons.append(
            f"onboarding review_state={live_light_input.onboarding_review_state.value} is not eligible for Live-Light"
        )
    hard_blocking_reasons.extend(
        f"onboarding gate: {reason}" for reason in live_light_input.onboarding_reasons
    )

    if not live_light_input.review_export_ready:
        hard_blocking_reasons.append(
            "Build-11/9X review export must be ready before Live-Light execution"
        )
    if not live_light_input.observability_ready:
        hard_blocking_reasons.append(
            "Build-10 observability must be ready before Live-Light execution"
        )
    if not live_light_input.halt_ready:
        hard_blocking_reasons.append(
            "operator halt guard must be ready before Live-Light execution"
        )
    if not live_light_input.execution_ready:
        hard_blocking_reasons.append(
            "execution readiness must be confirmed before Live-Light execution"
        )
    if not live_light_input.broker_ready:
        hard_blocking_reasons.append(
            "broker readiness must be confirmed before Live-Light execution"
        )
    if not live_light_input.exchange_ready:
        hard_blocking_reasons.append(
            "exchange readiness must be confirmed before Live-Light execution"
        )

    if hard_blocking_reasons:
        decision = LiveLightDecision(
            allowed_to_execute_small=False,
            verdict=LiveLightVerdict.BLOCKED,
            normalized_promotion_state=PromotionState.MICRO_LIVE_CANDIDATE,
            review_state=ReviewState.NEEDS_REVISION,
            approved_total_notional_usdt=0.0,
            approved_pair_notional_usdt=0.0,
            blocking_reasons=tuple(hard_blocking_reasons),
            manual_review_required=True,
        )
        execution_intent = LiveLightExecutionIntent(
            intent_id=run_id or f"{live_light_input.correlation_id}:live_light_intent",
            import_artifact_id=live_light_input.import_artifact_id,
            import_lineage_version=live_light_input.import_lineage_version,
            planned_engines=(),
            planned_pairs=(),
            requested_total_notional_usdt=live_light_input.requested_total_notional_usdt,
            approved_total_notional_usdt=0.0,
            approved_pair_notional_usdt=0.0,
            execution_order_limit=0,
            dry_run_only=False,
            halt_guard_required=True,
            broker_ready_required=True,
            exchange_ready_required=True,
        )
        run_state = LiveLightRunState.BLOCKED
    elif micro_live_needs_review:
        decision = LiveLightDecision(
            allowed_to_execute_small=False,
            verdict=LiveLightVerdict.DRY_RUN_ONLY,
            normalized_promotion_state=PromotionState.MICRO_LIVE_CANDIDATE,
            review_state=ReviewState.NEEDS_REVISION,
            approved_total_notional_usdt=0.0,
            approved_pair_notional_usdt=0.0,
            blocking_reasons=(
                "Build-12 Micro-live verdict must be allowed_to_probe before Live-Light can execute small size",
            ),
            manual_review_required=True,
        )
        execution_intent = LiveLightExecutionIntent(
            intent_id=run_id or f"{live_light_input.correlation_id}:live_light_intent",
            import_artifact_id=live_light_input.import_artifact_id,
            import_lineage_version=live_light_input.import_lineage_version,
            planned_engines=live_light_input.active_engines,
            planned_pairs=live_light_input.live_pairs,
            requested_total_notional_usdt=live_light_input.requested_total_notional_usdt,
            approved_total_notional_usdt=0.0,
            approved_pair_notional_usdt=0.0,
            execution_order_limit=live_light_input.execution_order_limit,
            dry_run_only=True,
            halt_guard_required=True,
            broker_ready_required=True,
            exchange_ready_required=True,
        )
        run_state = LiveLightRunState.PREPARED
    else:
        decision = LiveLightDecision(
            allowed_to_execute_small=True,
            verdict=LiveLightVerdict.ALLOWED_TO_EXECUTE_SMALL,
            normalized_promotion_state=PromotionState.LIVE_CANDIDATE,
            review_state=ReviewState.PENDING,
            approved_total_notional_usdt=live_light_input.requested_total_notional_usdt,
            approved_pair_notional_usdt=live_light_input.requested_pair_notional_usdt,
            blocking_reasons=(),
            manual_review_required=False,
        )
        execution_intent = LiveLightExecutionIntent(
            intent_id=run_id or f"{live_light_input.correlation_id}:live_light_intent",
            import_artifact_id=live_light_input.import_artifact_id,
            import_lineage_version=live_light_input.import_lineage_version,
            planned_engines=live_light_input.active_engines,
            planned_pairs=live_light_input.live_pairs,
            requested_total_notional_usdt=live_light_input.requested_total_notional_usdt,
            approved_total_notional_usdt=live_light_input.requested_total_notional_usdt,
            approved_pair_notional_usdt=live_light_input.requested_pair_notional_usdt,
            execution_order_limit=live_light_input.execution_order_limit,
            dry_run_only=False,
            halt_guard_required=True,
            broker_ready_required=True,
            exchange_ready_required=True,
        )
        run_state = LiveLightRunState.READY_TO_EXECUTE_SMALL

    return LiveLightRunSummary(
        run_id=run_id or f"{live_light_input.correlation_id}:live_light_run",
        correlation_id=live_light_input.correlation_id,
        run_state=run_state,
        micro_live_run_id=live_light_input.micro_live_run_id,
        shadow_run_id=live_light_input.shadow_run_id,
        micro_live_verdict=live_light_input.micro_live_verdict,
        decision=decision,
        execution_intent=execution_intent,
        import_artifact_id=live_light_input.import_artifact_id,
        import_lineage_version=live_light_input.import_lineage_version,
        observability_ready=live_light_input.observability_ready,
        halt_ready=live_light_input.halt_ready,
        execution_ready=live_light_input.execution_ready,
        broker_ready=live_light_input.broker_ready,
        exchange_ready=live_light_input.exchange_ready,
        onboarding_ready=live_light_input.onboarding_accepted,
    )


__all__ = [
    "build_live_light_input_from_micro_live",
    "run_live_light_gate",
]
