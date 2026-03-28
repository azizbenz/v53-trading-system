"""Normalized Build-10 technical dashboard payload builder."""

from __future__ import annotations

from monitoring.alert_manager import build_monitoring_alerts
from monitoring.contracts import (
    AlertProjection,
    Build9MetaProjection,
    Build9XProjection,
    MicroLiveProjection,
    MonitoringSnapshot,
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
) -> AlertProjection:
    return AlertProjection(
        headline_status=headline_status,
        active_alert_count=snapshot.active_alert_count,
        alert_ids=tuple(alert.alert_id for alert in snapshot.alerts),
        queue_backlog=snapshot.infra.queue_backlog,
        stale_pair_count=snapshot.stale_pair_count,
        stale_pairs=snapshot.infra.stale_pairs,
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
    )


def build_technical_dashboard_payload(
    snapshot: MonitoringSnapshot,
    *,
    active_modules: tuple[str, ...] = (),
    active_engines: tuple[str, ...] = (),
    build9x_projection: Build9XProjection | None = None,
    shadow_projection: ShadowProjection | None = None,
    micro_live_projection: MicroLiveProjection | None = None,
    replay_projection: ReplayImportProjection | None = None,
) -> TechnicalDashboardPayload:
    """Normalize runtime supervision truth into a typed Build-10 payload."""

    resolved_snapshot = _resolve_snapshot(snapshot)
    headline_status = build_health_dashboard_payload(resolved_snapshot).headline_status
    build9x = build9x_projection or _default_build9x_projection(active_modules=active_modules)
    shadow = shadow_projection or _default_shadow_projection(active_modules=active_modules)
    micro_live = micro_live_projection or _default_micro_live_projection(active_modules=active_modules)
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
            replay_import_status=replay_import.status,
            governed_extensions_detail=(
                "Build-9X, Shadow, Micro-live, and replay/import remain governed. "
                "Build-13 stays closed."
            ),
        ),
        portfolio=resolved_snapshot.portfolio,
        build9_meta=_build_build9_meta_projection(resolved_snapshot),
        build9x=build9x,
        shadow=shadow,
        micro_live=micro_live,
        replay_import=replay_import,
        alerts=_build_alert_projection(resolved_snapshot, headline_status=headline_status),
    )


__all__ = [
    "build_technical_dashboard_payload",
]
