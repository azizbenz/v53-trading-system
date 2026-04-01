"""Normalized Build-10 technical dashboard payload builder."""

from __future__ import annotations

from monitoring.alert_manager import build_monitoring_alerts
from monitoring.contracts import (
    AlertProjection,
    Build14Projection,
    Build9MetaProjection,
    Build9XProjection,
    LiveLightProjection,
    MicroLiveProjection,
    MonitoringSnapshot,
    OperatorRuntimeProjection,
    ReplayImportProjection,
    ShadowProjection,
    SystemProjection,
    TechnicalDashboardPayload,
)
from monitoring.health_dashboard_backend import build_health_dashboard_payload


def _resolve_snapshot(snapshot: MonitoringSnapshot) -> MonitoringSnapshot:
    if snapshot.alerts:
        return snapshot
    return snapshot.model_copy(update={"alerts": build_monitoring_alerts(snapshot)})


def _default_build9x_projection(*, active_modules: tuple[str, ...]) -> Build9XProjection:
    module_active = "meta_learning" in active_modules
    return Build9XProjection(
        status="info" if module_active else "planned",
        diagnostics_count=0,
        diagnostics_summary="No diagnostic report",
        open_hypotheses=0,
        total_hypotheses=0,
        near_miss_count=0,
        replay_candidate_count=0,
        memory_record_count=0,
        latest_memory_summary="No memory records",
        review_export_ready=False,
        review_export_ref="",
        learning_queue_depth=0,
        learning_queue_oldest_age_ms=0,
        learning_worker_cpu_pct=0.0,
        learning_worker_rss_mb=0.0,
        learning_write_latency_ms=0.0,
        learning_export_failures_total=0,
        learning_log_loss_total=0,
        learning_unprocessed_items_count=0,
        learning_backlog_state="normal",
        learning_capture_mode="full_capture",
        learning_observability_reduced=False,
        learning_backpressure_active=False,
        review_blocked_due_to_incomplete_data=False,
        promotion_blocked_due_to_incomplete_data=False,
        learning_capacity_summary="queue=0 / backlog=normal / mode=full_capture",
    )


def _default_replay_projection(*, active_modules: tuple[str, ...]) -> ReplayImportProjection:
    modules_active = {
        "local_replay_runtime",
        "backtest_artifact_import",
    } & set(active_modules)
    return ReplayImportProjection(
        status="info" if modules_active else "planned",
        artifact_id="none",
        artifact_kind="No replay bundle exported",
        lineage_version="n/a",
        lifecycle_state="Awaiting LOCAL_REPLAY artifact",
        validation_status="not_run",
        review_state="No import review executed",
        rejection_reasons=(),
    )


def _default_shadow_projection(*, active_modules: tuple[str, ...]) -> ShadowProjection:
    module_active = "protocols" in active_modules
    return ShadowProjection(
        status="info" if module_active else "planned",
        run_state="not_run",
        verdict="not_run",
        truth_set_ref="",
        validation_set_ref="",
        divergent_comparison_count=0,
        blocking_comparison_count=0,
        total_comparison_count=0,
        build9x_diagnostics_count=0,
        open_hypotheses=0,
        replay_candidate_count=0,
        review_export_ready=False,
        import_artifact_id="none",
        import_lineage_version="n/a",
        blocking_reasons=(),
        manual_review_required=False,
    )


def _default_micro_live_projection(*, active_modules: tuple[str, ...]) -> MicroLiveProjection:
    module_active = "protocols" in active_modules
    return MicroLiveProjection(
        status="info" if module_active else "planned",
        run_state="not_run",
        verdict="not_run",
        shadow_run_id="",
        shadow_verdict="not_run",
        allowed_to_probe=False,
        requested_total_notional_usdt=0.0,
        approved_total_notional_usdt=0.0,
        approved_pair_notional_usdt=0.0,
        order_probe_limit=0,
        planned_pairs=(),
        planned_engines=(),
        import_artifact_id="none",
        import_lineage_version="n/a",
        observability_ready=False,
        halt_ready=False,
        onboarding_ready=False,
        blocking_reasons=(),
    )


def _default_live_light_projection(*, active_modules: tuple[str, ...]) -> LiveLightProjection:
    module_active = "protocols" in active_modules
    return LiveLightProjection(
        status="info" if module_active else "planned",
        run_state="not_run",
        verdict="not_run",
        micro_live_run_id="",
        micro_live_verdict="not_run",
        allowed_to_execute_small=False,
        requested_total_notional_usdt=0.0,
        approved_total_notional_usdt=0.0,
        approved_pair_notional_usdt=0.0,
        execution_order_limit=0,
        planned_pairs=(),
        planned_engines=(),
        import_artifact_id="none",
        import_lineage_version="n/a",
        observability_ready=False,
        halt_ready=False,
        execution_ready=False,
        broker_ready=False,
        exchange_ready=False,
        blocking_reasons=(),
    )


def _default_build14_projection(*, active_modules: tuple[str, ...]) -> Build14Projection:
    module_active = "complete_enablers" in active_modules
    return Build14Projection(
        status="info" if module_active else "planned",
        hard_state="shadow_enabled" if module_active else "coded",
        live_promotion_eligible=False,
        influence_mode="shadow_enabled" if module_active else "read_only",
        action="shadow_apply" if module_active else "observe",
        severity="nominal",
        summary=(
            "Build-14 enablers are SHADOW_ENABLED in Shadow; live promotion remains gated"
            if module_active
            else "Build-14 enablers are not materialized"
        ),
        market_toxicity_value=0.0,
        market_toxicity_status="nominal",
        execution_fragility_value=0.0,
        execution_fragility_status="nominal",
        confidence_penalty_weight=0.0,
        recommended_budget_factor=1.0,
        requires_manual_review=False,
        candidate_effect="observe_only",
        reason_codes=(),
    )


def _build_build9_meta_projection(snapshot: MonitoringSnapshot) -> Build9MetaProjection:
    break_even_state = "drift_alert" if snapshot.meta.break_even_drift_alert else "stable"
    return Build9MetaProjection(
        dtr_coverage=snapshot.meta.dtr_coverage,
        dtr_status="healthy" if snapshot.meta.dtr_coverage >= 0.8 else "warning",
        cra_sterilization_rate=snapshot.meta.cra_sterilization_rate,
        cra_alert_count=snapshot.meta.cra_alert_count,
        cra_status=(
            "warning"
            if snapshot.meta.cra_sterilization_rate >= 0.2 or snapshot.meta.cra_alert_count > 0
            else "healthy"
        ),
        break_even_state=break_even_state,
        break_even_status="warning" if snapshot.meta.break_even_drift_alert else "healthy",
        break_even_drift_scopes=snapshot.meta.break_even_drift_scopes,
        edge_credible_count=snapshot.meta.edge_credible_count,
        edge_degraded_count=snapshot.meta.edge_degraded_count,
        edge_surveillance_count=snapshot.meta.edge_surveillance_count,
        edge_status="warning" if snapshot.meta.edge_degraded_count > 0 else "healthy",
    )


def _build_alert_projection(
    snapshot: MonitoringSnapshot,
    *,
    headline_status: str,
    operator_runtime: OperatorRuntimeProjection | None = None,
) -> AlertProjection:
    return AlertProjection(
        headline_status=headline_status,
        active_alert_count=snapshot.active_alert_count,
        alert_ids=tuple(alert.alert_id for alert in snapshot.alerts),
        queue_backlog=snapshot.infra.queue_backlog,
        backlog_high_water_mark=snapshot.infra.backlog_high_water_mark,
        drop_rate_pct=snapshot.infra.drop_rate_pct,
        stale_pair_count=snapshot.stale_pair_count,
        stale_pairs=snapshot.infra.stale_pairs,
        stale_spike_count=snapshot.infra.stale_spike_count,
        recovery_retry_count=snapshot.infra.recovery_retry_count,
        kill_switch_active=snapshot.infra.kill_switch_active,
        kill_switch_timestamp_ms=snapshot.infra.kill_switch_timestamp_ms,
        persisted_metric_names=snapshot.infra.persisted_metric_names,
        volatile_metric_names=snapshot.infra.volatile_metric_names,
        backlog_stale_status=(
            "warning" if snapshot.backlog_warning or snapshot.stale_warning else "healthy"
        ),
        dtr_loss_count=snapshot.infra.dtr_loss_count,
        log_loss_count=snapshot.infra.log_loss_count,
        break_even_drift_scope_count=len(snapshot.meta.break_even_drift_scopes),
        edge_degraded_count=snapshot.meta.edge_degraded_count,
        loss_drift_status=(
            "critical"
            if snapshot.loss_warning
            else "warning"
            if snapshot.meta.break_even_drift_alert or snapshot.meta.edge_degraded_count > 0
            else "healthy"
        ),
        operator_runtime=operator_runtime or OperatorRuntimeProjection(),
    )


def build_technical_dashboard_payload(
    snapshot: MonitoringSnapshot,
    *,
    active_modules: tuple[str, ...] = (),
    active_engines: tuple[str, ...] = (),
    build9x_projection: Build9XProjection | None = None,
    shadow_projection: ShadowProjection | None = None,
    micro_live_projection: MicroLiveProjection | None = None,
    live_light_projection: LiveLightProjection | None = None,
    build14_projection: Build14Projection | None = None,
    replay_projection: ReplayImportProjection | None = None,
    operator_runtime: OperatorRuntimeProjection | None = None,
) -> TechnicalDashboardPayload:
    """Normalize runtime supervision truth into a typed Build-10 payload."""

    resolved_snapshot = _resolve_snapshot(snapshot)
    headline_status = build_health_dashboard_payload(
        resolved_snapshot,
        operator_runtime=operator_runtime,
    ).headline_status
    build9x = build9x_projection or _default_build9x_projection(active_modules=active_modules)
    shadow = shadow_projection or _default_shadow_projection(active_modules=active_modules)
    micro_live = micro_live_projection or _default_micro_live_projection(active_modules=active_modules)
    live_light = live_light_projection or _default_live_light_projection(active_modules=active_modules)
    build14 = build14_projection or _default_build14_projection(active_modules=active_modules)
    replay_import = replay_projection or _default_replay_projection(active_modules=active_modules)
    stale_engines = tuple(
        engine.engine_id
        for engine in resolved_snapshot.engines
        if engine.stale and (not active_engines or engine.engine_id in active_engines)
    )

    return TechnicalDashboardPayload(
        timestamp_ms=resolved_snapshot.timestamp_ms,
        correlation_id=resolved_snapshot.correlation_id,
        profile=resolved_snapshot.profile,
        runtime_mode=resolved_snapshot.runtime_mode,
        system=SystemProjection(
            headline_status=headline_status,
            active_modules=active_modules,
            active_engines=active_engines,
            stale_engines=stale_engines,
            build9x_status=build9x.status,
            shadow_status=shadow.status,
            micro_live_status=micro_live.status,
            live_light_status=live_light.status,
            build14_status=build14.status,
            replay_import_status=replay_import.status,
            governed_extensions_detail=(
                "Build-9X, Shadow, Micro-live, Live-Light, replay/import, and Build-14 enablers remain governed. "
                "Complete stays closed and Build-14 does not bypass engines, risk, or portfolio."
            ),
        ),
        portfolio=resolved_snapshot.portfolio,
        engines=resolved_snapshot.engines,
        pairs=resolved_snapshot.pairs,
        infra=resolved_snapshot.infra,
        build9_meta=_build_build9_meta_projection(resolved_snapshot),
        build9x=build9x,
        shadow=shadow,
        micro_live=micro_live,
        live_light=live_light,
        build14=build14,
        replay_import=replay_import,
        alerts=_build_alert_projection(
            resolved_snapshot,
            headline_status=headline_status,
            operator_runtime=operator_runtime,
        ),
    )


__all__ = [
    "build_technical_dashboard_payload",
]
