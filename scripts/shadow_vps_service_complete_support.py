#!/usr/bin/env python3
"""Build-17 supervision helpers for the governed Shadow VPS service."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import time
from pathlib import Path

from interface_contracts import (
    DashboardCommandQueueSnapshot,
    DeploymentState,
    ProfileId,
    PromotionState,
    ReviewState,
    VpsRecoveryReadinessReport,
    VpsWarmupRunSummary,
)
from interface_contracts.atomic_io import atomic_write_json
from local_replay_runtime.live_complete_operator_audit_report import (
    LiveCompleteOperatorAuditReport,
    build_live_complete_operator_audit_report,
    write_live_complete_operator_audit_report,
)
from monitoring import build_shadow_vps_service_recent_events_summary
from protocols import (
    LiveCompleteRunSummary,
    LiveCompleteAllowedAction,
    LiveCompleteForbiddenAction,
    LiveLightDecision,
    LiveLightExecutionIntent,
    LiveLightRunState,
    LiveLightRunSummary,
    MicroLiveVerdict,
    ShadowVpsServiceEvent,
    build_dashboard_command_queue_snapshot,
    build_live_complete_input_from_live_light,
    run_live_complete_gate,
)
from shadow_vps_service_io_support import _read_live_websocket_config
from shadow_vps_service_models import ShadowVpsServiceRuntimeContext


_CANONICAL_ENGINES = ("engine_a", "engine_b", "engine_c", "engine_d")
_ALLOWED_ACTIONS = (
    LiveCompleteAllowedAction.SET_HALTED,
    LiveCompleteAllowedAction.ROLLBACK_TO_LIGHT,
    LiveCompleteAllowedAction.SUSPEND_PAIR,
    LiveCompleteAllowedAction.REQUEST_PAIR_RESUME,
    LiveCompleteAllowedAction.SUSPEND_ENGINE,
    LiveCompleteAllowedAction.REQUEST_ENGINE_RESUME,
    LiveCompleteAllowedAction.REQUEST_UPLOAD_ML_ARTIFACT,
    LiveCompleteAllowedAction.REQUEST_UPLOAD_REGIME_DETECTOR_ARTIFACT,
    LiveCompleteAllowedAction.REQUEST_EXPORT_ACTIVE_ML_ARTIFACT,
    LiveCompleteAllowedAction.REQUEST_EXPORT_ACTIVE_REGIME_DETECTOR_ARTIFACT,
    LiveCompleteAllowedAction.REQUEST_EXPORT_REGIME_DETECTOR_SHADOW_AUDIT_BUNDLE,
    LiveCompleteAllowedAction.REQUEST_UPLOAD_BINANCE_CREDENTIALS_BUNDLE,
    LiveCompleteAllowedAction.REQUEST_ACTIVATE_BINANCE_CREDENTIALS_PROFILE,
    LiveCompleteAllowedAction.REQUEST_EXPORT_BINANCE_CREDENTIAL_INVENTORY,
    LiveCompleteAllowedAction.REQUEST_DEACTIVATE_BINANCE_CREDENTIALS_PROFILE,
    LiveCompleteAllowedAction.VIEW_COMPLETE_GATES,
)
_FORBIDDEN_ACTIONS = (
    LiveCompleteForbiddenAction.MODIFY_RISK_CAPS,
    LiveCompleteForbiddenAction.INJECT_UNVERSIONED_CONFIG,
    LiveCompleteForbiddenAction.BYPASS_HARD_BLOCKER,
)
AppendServiceEvent = Callable[..., None]


@dataclass(frozen=True)
class ShadowVpsGovernedControlSurface:
    """Effective governed execution surface projected from persisted Shadow control state."""

    effective_target_profile: str
    available_pairs: tuple[str, ...]
    effective_selected_pairs: tuple[str, ...]
    effective_engines: tuple[str, ...]
    rollback_active: bool
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class ShadowVpsBuild17Refresh:
    """Typed result returned after refreshing Build-17 Shadow supervision artifacts."""

    control_surface: ShadowVpsGovernedControlSurface
    queue_snapshot: DashboardCommandQueueSnapshot | None
    recovery_report: VpsRecoveryReadinessReport | None
    warmup_summary: VpsWarmupRunSummary | None
    live_complete_summary: LiveCompleteRunSummary
    operator_report: LiveCompleteOperatorAuditReport


def _read_model(path_ref: str, model_type: type[object]) -> object | None:
    if not path_ref:
        return None
    path = Path(path_ref)
    if not path.is_file():
        return None
    return model_type.model_validate_json(path.read_text(encoding="utf-8"))


def _load_queue_snapshot(
    context: ShadowVpsServiceRuntimeContext,
) -> DashboardCommandQueueSnapshot | None:
    if context.dashboard_command_queue_root is None:
        return None
    return build_dashboard_command_queue_snapshot(context.dashboard_command_queue_root)


def _resolve_configured_pairs(
    context: ShadowVpsServiceRuntimeContext,
) -> tuple[str, ...]:
    config_path = context.live_websocket_config_path
    if config_path is None or not config_path.is_file():
        return ()
    return tuple(_read_live_websocket_config(config_path).pairs)


def _resolve_control_surface(
    context: ShadowVpsServiceRuntimeContext,
) -> ShadowVpsGovernedControlSurface:
    state = context.store.state
    configured_pairs = _resolve_configured_pairs(context)
    suspended_pairs = set(state.dashboard_control_suspended_pairs)
    selected_pairs = tuple(pair for pair in configured_pairs if pair not in suspended_pairs)
    suspended_engines = set(state.dashboard_control_suspended_engines)
    effective_engines = tuple(
        engine for engine in _CANONICAL_ENGINES if engine not in suspended_engines
    )
    effective_target_profile = (
        ProfileId.LIGHT.value
        if state.dashboard_control_target_deployment_state == DeploymentState.ROLLBACK.value
        else state.dashboard_control_target_profile or ProfileId.COMPLETE.value
    )
    rollback_active = (
        state.dashboard_control_target_deployment_state == DeploymentState.ROLLBACK.value
        or effective_target_profile == ProfileId.LIGHT.value
    )
    reason_codes = []
    if rollback_active:
        reason_codes.append("shadow.dashboard_control.rollback_active")
    if state.dashboard_control_suspended_pairs:
        reason_codes.append("shadow.dashboard_control.suspended_pairs_active")
    if state.dashboard_control_suspended_engines:
        reason_codes.append("shadow.dashboard_control.suspended_engines_active")
    if configured_pairs and not selected_pairs:
        reason_codes.append("shadow.dashboard_control.all_pairs_suspended")
    if not effective_engines:
        reason_codes.append("shadow.dashboard_control.all_engines_suspended")
    return ShadowVpsGovernedControlSurface(
        effective_target_profile=effective_target_profile,
        available_pairs=configured_pairs,
        effective_selected_pairs=selected_pairs,
        effective_engines=effective_engines,
        rollback_active=rollback_active,
        reason_codes=tuple(dict.fromkeys(reason_codes)),
    )


def _resolve_import_identity(context: ShadowVpsServiceRuntimeContext) -> tuple[str, str]:
    manifests = (
        context.store.state.active_ml_artifact,
        context.store.state.active_regime_detector_artifact,
    )
    for manifest in manifests:
        if manifest is not None and manifest.artifact_id and manifest.lineage_version:
            return manifest.artifact_id, manifest.lineage_version
    return "shadow.synthetic_import", "shadow.synthetic_lineage"


def _build_synthetic_live_light_summary(
    context: ShadowVpsServiceRuntimeContext,
    *,
    control_surface: ShadowVpsGovernedControlSurface,
    queue_snapshot: DashboardCommandQueueSnapshot | None,
    recovery_report: VpsRecoveryReadinessReport | None,
    warmup_summary: VpsWarmupRunSummary | None,
) -> LiveLightRunSummary:
    import_artifact_id, import_lineage_version = _resolve_import_identity(context)
    decision_reasons = list(control_surface.reason_codes)
    if queue_snapshot is None:
        decision_reasons.append("shadow.dashboard_queue.not_attached")
    elif not queue_snapshot.healthy:
        decision_reasons.extend(queue_snapshot.blocking_reasons)
    if recovery_report is not None:
        decision_reasons.extend(recovery_report.blocking_reasons)
    if warmup_summary is not None:
        decision_reasons.extend(warmup_summary.blocking_reasons)
    credential_ready = (
        context.store.state.binance_credential_validation_status == "validated"
    )
    return LiveLightRunSummary(
        run_id="shadow-vps-service.synthetic_live_light",
        correlation_id="shadow-vps-service",
        run_state=LiveLightRunState.PREPARED,
        micro_live_run_id="shadow-vps-service.synthetic_micro_live",
        shadow_run_id="shadow-vps-service.shadow",
        micro_live_verdict=MicroLiveVerdict.ALLOWED_TO_PROBE,
        decision=LiveLightDecision(
            allowed_to_execute_small=False,
            verdict="dry_run_only",
            normalized_promotion_state=PromotionState.REPLAY_ONLY,
            review_state=ReviewState.PENDING,
            blocking_reasons=tuple(dict.fromkeys(decision_reasons)),
            manual_review_required=True,
        ),
        execution_intent=LiveLightExecutionIntent(
            intent_id="shadow-vps-service.synthetic_live_light.intent",
            import_artifact_id=import_artifact_id,
            import_lineage_version=import_lineage_version,
            planned_engines=control_surface.effective_engines,
            planned_pairs=control_surface.effective_selected_pairs,
            requested_total_notional_usdt=0.0,
            approved_total_notional_usdt=0.0,
            approved_pair_notional_usdt=0.0,
            execution_order_limit=0,
            dry_run_only=True,
            halt_guard_required=True,
            broker_ready_required=True,
            exchange_ready_required=True,
        ),
        import_artifact_id=import_artifact_id,
        import_lineage_version=import_lineage_version,
        observability_ready=True,
        halt_ready=True,
        execution_ready=bool(recovery_report and recovery_report.eligible_to_trade),
        broker_ready=credential_ready,
        exchange_ready=bool(warmup_summary and warmup_summary.eligible_to_trade),
        onboarding_ready=bool(queue_snapshot and queue_snapshot.healthy),
        build14_summary="synthetic_shadow_supervision_only",
    )


def _build_complete_gates(
    *,
    control_surface: ShadowVpsGovernedControlSurface,
    queue_snapshot: DashboardCommandQueueSnapshot | None,
    recovery_report: VpsRecoveryReadinessReport | None,
    warmup_summary: VpsWarmupRunSummary | None,
) -> tuple[str, ...]:
    gates = ["gate.shadow.synthetic_live_light"]
    gates.append(
        f"gate.shadow.queue.{queue_snapshot.queue_status.value}"
        if queue_snapshot is not None
        else "gate.shadow.queue.not_configured"
    )
    gates.append(
        "gate.shadow.recovery.not_configured"
        if recovery_report is None
        else f"gate.shadow.recovery.{recovery_report.eligible_to_trade}"
    )
    gates.append(
        "gate.shadow.warmup.not_configured"
        if warmup_summary is None
        else f"gate.shadow.warmup.{warmup_summary.final_state.value}"
    )
    if control_surface.rollback_active:
        gates.append("gate.shadow.rollback_active")
    return tuple(gates)


def _emit_summary_event(
    context: ShadowVpsServiceRuntimeContext,
    *,
    append_service_event: AppendServiceEvent | None,
    live_complete_summary: LiveCompleteRunSummary,
    operator_report: LiveCompleteOperatorAuditReport,
) -> None:
    if append_service_event is None:
        return
    state = context.store.state
    append_service_event(
        store=context.store,
        telegram_alerter=context.telegram_alerter,
        event=ShadowVpsServiceEvent(
            event_type="live_complete_summary_refreshed",
            message=(
                "Build-17 live-complete summary refreshed: "
                f"{live_complete_summary.run_state.value}/{live_complete_summary.decision.verdict.value}."
            ),
            reason_codes=live_complete_summary.decision.blocking_reasons,
        ),
    )
    append_service_event(
        store=context.store,
        telegram_alerter=context.telegram_alerter,
        event=ShadowVpsServiceEvent(
            event_type="operator_report_written",
            message=f"Operator report refreshed with status={operator_report.status}.",
            export_dir_ref=state.last_live_complete_operator_report_ref,
            reason_codes=operator_report.blocking_reasons,
        ),
    )
    append_service_event(
        store=context.store,
        telegram_alerter=context.telegram_alerter,
        event=ShadowVpsServiceEvent(
            event_type=f"operator_report_{operator_report.status}",
            message=(
                "Operator report recommendation="
                f"{operator_report.final_recommendation}."
            ),
            export_dir_ref=state.last_live_complete_operator_report_ref,
            reason_codes=operator_report.blocking_reasons,
        ),
    )


def refresh_shadow_vps_build17_supervision(
    context: ShadowVpsServiceRuntimeContext,
    *,
    append_service_event: AppendServiceEvent | None = None,
) -> ShadowVpsBuild17Refresh:
    """Refresh synthetic Build-17 supervision artifacts from persisted Shadow state."""

    timestamp_ms = int(time.time() * 1000.0)
    queue_snapshot = _load_queue_snapshot(context)
    recovery_report = _read_model(
        context.store.state.last_vps_recovery_readiness_report_ref,
        VpsRecoveryReadinessReport,
    )
    warmup_summary = _read_model(
        context.store.state.last_vps_warmup_summary_ref,
        VpsWarmupRunSummary,
    )
    control_surface = _resolve_control_surface(context)
    live_light_summary = _build_synthetic_live_light_summary(
        context,
        control_surface=control_surface,
        queue_snapshot=queue_snapshot,
        recovery_report=recovery_report,
        warmup_summary=warmup_summary,
    )
    live_complete_summary = run_live_complete_gate(
        build_live_complete_input_from_live_light(
            live_light_summary,
            complete_gates=_build_complete_gates(
                control_surface=control_surface,
                queue_snapshot=queue_snapshot,
                recovery_report=recovery_report,
                warmup_summary=warmup_summary,
            ),
            selected_pairs=control_surface.effective_selected_pairs,
            available_pairs=control_surface.available_pairs,
            allowed_actions=_ALLOWED_ACTIONS,
            forbidden_actions=_FORBIDDEN_ACTIONS,
            command_queue_snapshot=queue_snapshot,
            active_ml_artifact=context.store.state.active_ml_artifact,
            active_regime_detector_artifact=context.store.state.active_regime_detector_artifact,
            recovery_readiness_report=recovery_report,
            warmup_run_summary=warmup_summary,
        ),
        run_id="shadow-vps-service.live_complete",
    )
    summary_path = context.service_dir / "live_complete_run.summary.json"
    recent_events_summary_path = context.service_dir / "shadow_vps_service_recent_events.json"
    recent_events_summary = build_shadow_vps_service_recent_events_summary(
        context.store.events_path,
        max_events=20,
        timestamp_ms=timestamp_ms,
    )
    atomic_write_json(summary_path, live_complete_summary.model_dump(mode="json"))
    operator_report = build_live_complete_operator_audit_report(
        live_complete_summary=live_complete_summary,
        recent_events_summary=recent_events_summary,
        recent_events_summary_ref=str(recent_events_summary_path.resolve()),
    )
    report_path = write_live_complete_operator_audit_report(
        operator_report,
        context.service_dir / "live_complete_operator_audit_report.json",
    )
    previous_summary = (
        context.store.state.last_live_complete_status,
        context.store.state.last_live_complete_verdict,
        context.store.state.last_live_complete_run_state,
        context.store.state.last_live_complete_blocking_reason_count,
        context.store.state.last_live_complete_operator_report_status,
        context.store.state.last_live_complete_operator_report_recommendation,
    )
    context.store.update_state(
        last_live_complete_summary_ref=str(summary_path.resolve()),
        last_live_complete_status=operator_report.status,
        last_live_complete_verdict=live_complete_summary.decision.verdict.value,
        last_live_complete_run_state=live_complete_summary.run_state.value,
        last_live_complete_blocking_reason_count=live_complete_summary.blocking_reason_count,
        last_live_complete_operator_report_ref=str(report_path.resolve()),
        last_live_complete_operator_report_status=operator_report.status,
        last_live_complete_operator_report_recommendation=operator_report.final_recommendation,
    )
    current_summary = (
        context.store.state.last_live_complete_status,
        context.store.state.last_live_complete_verdict,
        context.store.state.last_live_complete_run_state,
        context.store.state.last_live_complete_blocking_reason_count,
        context.store.state.last_live_complete_operator_report_status,
        context.store.state.last_live_complete_operator_report_recommendation,
    )
    if current_summary != previous_summary:
        _emit_summary_event(
            context,
            append_service_event=append_service_event,
            live_complete_summary=live_complete_summary,
            operator_report=operator_report,
        )
    return ShadowVpsBuild17Refresh(
        control_surface=control_surface,
        queue_snapshot=queue_snapshot,
        recovery_report=recovery_report,
        warmup_summary=warmup_summary,
        live_complete_summary=live_complete_summary,
        operator_report=operator_report,
    )


__all__ = [
    "ShadowVpsBuild17Refresh",
    "ShadowVpsGovernedControlSurface",
    "refresh_shadow_vps_build17_supervision",
]
