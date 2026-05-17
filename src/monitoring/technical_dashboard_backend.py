"""Normalized Build-10 technical dashboard payload builder."""

from __future__ import annotations

from dataclasses import dataclass

from monitoring.alert_manager import build_monitoring_alerts
from monitoring.challenger_evidence_alerts import (
    build_shadow_challenger_alerts,
    merge_alert_records,
)
from monitoring.contracts import (
    AccountUserDataProjection,
    AlertProjection,
    ArtifactComparisonProjection,
    ArtifactRuntimeVisibilityProjection,
    ArtifactThresholdConsumerProjection,
    ArtifactVerdictBundleProjection,
    Build14Projection,
    Build9MetaProjection,
    Build9XProjection,
    EngineJudgmentProjection,
    ExecutionNoTradeBridgeProjection,
    ExecutionRuntimeProjectionBridgeProjection,
    HybridRouterMetricsProjection,
    LiveProjection,
    LiveLightProjection,
    MicroLiveProjection,
    MonitoringSnapshot,
    OperatorRuntimeProjection,
    RuntimeHookBridgeProjection,
    ReplayImportProjection,
    ShadowProjection,
    SystemProjection,
    TechnicalDashboardPayload,
)
from monitoring.health_dashboard_backend import build_health_dashboard_payload
from monitoring.technical_dashboard_backend_support import (
    apply_operator_safing_to_live_light_projection,
    apply_operator_safing_to_micro_live_projection,
    default_account_user_data_projection,
    default_build14_projection,
    default_build9x_projection,
    default_engine_judgment_projection,
    default_execution_no_trade_bridge_projection,
    default_execution_runtime_projection_bridge_projection,
    default_live_light_projection,
    default_micro_live_projection,
    default_replay_projection,
    default_shadow_projection,
    elevate_headline_status_from_account_user_data,
    elevate_headline_status_from_build14,
    elevate_headline_status_from_build9x,
    elevate_headline_status_from_engine_judgment,
    elevate_headline_status_from_execution_no_trade_bridge,
    elevate_headline_status_from_execution_runtime_projection_bridge,
    elevate_headline_status_from_replay_import,
    elevate_headline_status_from_rollout,
    elevate_headline_status_from_runtime_hook_bridges,
    elevate_headline_status_from_shadow_regime_lite_safing,
    execution_no_trade_bridge_from_runtime_hook_projection,
    normalize_runtime_hook_bridge_projections,
)
from interface_contracts import HookId


@dataclass(frozen=True)
class _ResolvedDashboardState:
    snapshot: MonitoringSnapshot
    headline_status: str
    build9x: Build9XProjection
    build9_meta: Build9MetaProjection
    engine_judgment: EngineJudgmentProjection
    shadow: ShadowProjection
    micro_live: MicroLiveProjection
    live_light: LiveProjection
    build14: Build14Projection
    account_user_data: AccountUserDataProjection
    execution_no_trade_bridge: ExecutionNoTradeBridgeProjection
    execution_runtime_projection_bridge: ExecutionRuntimeProjectionBridgeProjection
    runtime_hook_bridges: tuple[RuntimeHookBridgeProjection, ...]
    replay_import: ReplayImportProjection


@dataclass(frozen=True)
class _ResolvedProjectionState:
    snapshot: MonitoringSnapshot
    headline_status: str
    build9x: Build9XProjection
    build9_meta: Build9MetaProjection
    engine_judgment: EngineJudgmentProjection
    shadow: ShadowProjection
    micro_live: MicroLiveProjection
    live_light: LiveProjection
    build14: Build14Projection
    account_user_data: AccountUserDataProjection


@dataclass(frozen=True)
class _ResolvedBridgeState:
    execution_no_trade_bridge: ExecutionNoTradeBridgeProjection
    execution_runtime_projection_bridge: ExecutionRuntimeProjectionBridgeProjection
    runtime_hook_bridges: tuple[RuntimeHookBridgeProjection, ...]
    replay_import: ReplayImportProjection


def _resolve_snapshot(snapshot: MonitoringSnapshot) -> MonitoringSnapshot:
    if snapshot.alerts:
        return snapshot
    return snapshot.model_copy(update={"alerts": build_monitoring_alerts(snapshot)})


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


def _elevate_headline_status_from_build9_meta(
    headline_status: str,
    *,
    build9_meta: Build9MetaProjection,
) -> str:
    statuses = (
        build9_meta.dtr_status,
        build9_meta.cra_status,
        build9_meta.break_even_status,
        build9_meta.edge_status,
    )
    if "critical" in statuses:
        return "critical"
    if "warning" in statuses and headline_status == "healthy":
        return "warning"
    return headline_status


def _resolve_dashboard_state(
    snapshot: MonitoringSnapshot,
    *,
    active_modules: tuple[str, ...],
    build9x_projection: Build9XProjection | None,
    engine_judgment_projection: EngineJudgmentProjection | None,
    shadow_projection: ShadowProjection | None,
    micro_live_projection: MicroLiveProjection | None,
    live_projection: LiveProjection | None,
    live_light_projection: LiveLightProjection | None,
    build14_projection: Build14Projection | None,
    account_user_data_projection: AccountUserDataProjection | None,
    execution_no_trade_bridge_projection: ExecutionNoTradeBridgeProjection | None,
    execution_runtime_projection_bridge_projection: ExecutionRuntimeProjectionBridgeProjection
    | None,
    runtime_hook_bridge_projections: tuple[RuntimeHookBridgeProjection, ...] | None,
    replay_projection: ReplayImportProjection | None,
    operator_runtime: OperatorRuntimeProjection | None,
) -> _ResolvedDashboardState:
    projection_state = _resolve_projection_state(
        snapshot,
        active_modules=active_modules,
        build9x_projection=build9x_projection,
        engine_judgment_projection=engine_judgment_projection,
        shadow_projection=shadow_projection,
        micro_live_projection=micro_live_projection,
        live_projection=live_projection,
        live_light_projection=live_light_projection,
        build14_projection=build14_projection,
        account_user_data_projection=account_user_data_projection,
        operator_runtime=operator_runtime,
    )
    bridge_state = _resolve_bridge_state(
        active_modules=active_modules,
        execution_no_trade_bridge_projection=execution_no_trade_bridge_projection,
        execution_runtime_projection_bridge_projection=(
            execution_runtime_projection_bridge_projection
        ),
        runtime_hook_bridge_projections=runtime_hook_bridge_projections,
        replay_projection=replay_projection,
    )
    headline_status = _resolve_final_headline_status(
        projection_state.headline_status,
        projection_state=projection_state,
        bridge_state=bridge_state,
    )
    return _ResolvedDashboardState(
        snapshot=projection_state.snapshot,
        headline_status=headline_status,
        build9x=projection_state.build9x,
        build9_meta=projection_state.build9_meta,
        engine_judgment=projection_state.engine_judgment,
        shadow=projection_state.shadow,
        micro_live=projection_state.micro_live,
        live_light=projection_state.live_light,
        build14=projection_state.build14,
        account_user_data=projection_state.account_user_data,
        execution_no_trade_bridge=bridge_state.execution_no_trade_bridge,
        execution_runtime_projection_bridge=bridge_state.execution_runtime_projection_bridge,
        runtime_hook_bridges=bridge_state.runtime_hook_bridges,
        replay_import=bridge_state.replay_import,
    )


def _resolve_projection_state(
    snapshot: MonitoringSnapshot,
    *,
    active_modules: tuple[str, ...],
    build9x_projection: Build9XProjection | None,
    engine_judgment_projection: EngineJudgmentProjection | None,
    shadow_projection: ShadowProjection | None,
    micro_live_projection: MicroLiveProjection | None,
    live_projection: LiveProjection | None,
    live_light_projection: LiveLightProjection | None,
    build14_projection: Build14Projection | None,
    account_user_data_projection: AccountUserDataProjection | None,
    operator_runtime: OperatorRuntimeProjection | None,
) -> _ResolvedProjectionState:
    if live_projection is not None and live_light_projection is not None:
        raise ValueError(
            "Use either live_projection or legacy live_light_projection, not both"
        )
    resolved_snapshot = _resolve_snapshot(snapshot)
    headline_status = build_health_dashboard_payload(
        resolved_snapshot,
        operator_runtime=operator_runtime,
    ).headline_status
    build9x = build9x_projection or default_build9x_projection(active_modules=active_modules)
    headline_status = elevate_headline_status_from_build9x(
        headline_status,
        build9x=build9x,
    )
    engine_judgment = engine_judgment_projection or default_engine_judgment_projection()
    headline_status = elevate_headline_status_from_engine_judgment(
        headline_status,
        engine_judgment=engine_judgment,
    )
    shadow = shadow_projection or default_shadow_projection(active_modules=active_modules)
    headline_status = elevate_headline_status_from_shadow_regime_lite_safing(
        headline_status,
        shadow=shadow,
    )
    micro_live = apply_operator_safing_to_micro_live_projection(
        micro_live_projection or default_micro_live_projection(active_modules=active_modules),
        operator_runtime=operator_runtime,
    )
    live_light = apply_operator_safing_to_live_light_projection(
        live_projection or live_light_projection or default_live_light_projection(
            active_modules=active_modules
        ),
        operator_runtime=operator_runtime,
    )
    build14 = build14_projection or default_build14_projection(active_modules=active_modules)
    headline_status = elevate_headline_status_from_build14(
        headline_status,
        build14=build14,
    )
    account_user_data = (
        account_user_data_projection or default_account_user_data_projection()
    )
    headline_status = elevate_headline_status_from_account_user_data(
        headline_status,
        account_user_data=account_user_data,
    )
    build9_meta = _build_build9_meta_projection(resolved_snapshot)
    return _ResolvedProjectionState(
        snapshot=resolved_snapshot,
        headline_status=headline_status,
        build9x=build9x,
        build9_meta=build9_meta,
        engine_judgment=engine_judgment,
        shadow=shadow,
        micro_live=micro_live,
        live_light=live_light,
        build14=build14,
        account_user_data=account_user_data,
    )


def _resolve_bridge_state(
    *,
    active_modules: tuple[str, ...],
    execution_no_trade_bridge_projection: ExecutionNoTradeBridgeProjection | None,
    execution_runtime_projection_bridge_projection: ExecutionRuntimeProjectionBridgeProjection
    | None,
    runtime_hook_bridge_projections: tuple[RuntimeHookBridgeProjection, ...] | None,
    replay_projection: ReplayImportProjection | None,
) -> _ResolvedBridgeState:
    execution_runtime_hook_projection = None
    if runtime_hook_bridge_projections is not None:
        execution_runtime_hook_projection = next(
            (
                projection
                for projection in runtime_hook_bridge_projections
                if projection.hook_id == HookId.EXECUTION_NO_TRADE_FILTER
            ),
            None,
        )
    execution_no_trade_bridge = execution_no_trade_bridge_projection
    if execution_no_trade_bridge is None and execution_runtime_hook_projection is not None:
        execution_no_trade_bridge = execution_no_trade_bridge_from_runtime_hook_projection(
            execution_runtime_hook_projection
        )
    if execution_no_trade_bridge is None:
        execution_no_trade_bridge = default_execution_no_trade_bridge_projection(
            active_modules=active_modules
        )
    execution_runtime_projection_bridge = (
        execution_runtime_projection_bridge_projection
        or default_execution_runtime_projection_bridge_projection(
            active_modules=active_modules
        )
    )
    runtime_hook_bridges = normalize_runtime_hook_bridge_projections(
        active_modules=active_modules,
        execution_no_trade_bridge=execution_no_trade_bridge,
        runtime_hook_bridge_projections=runtime_hook_bridge_projections,
    )
    replay_import = replay_projection or default_replay_projection(active_modules=active_modules)
    return _ResolvedBridgeState(
        execution_no_trade_bridge=execution_no_trade_bridge,
        execution_runtime_projection_bridge=execution_runtime_projection_bridge,
        runtime_hook_bridges=runtime_hook_bridges,
        replay_import=replay_import,
    )


def _resolve_final_headline_status(
    headline_status: str,
    *,
    projection_state: _ResolvedProjectionState,
    bridge_state: _ResolvedBridgeState,
) -> str:
    for update in (
        lambda status: elevate_headline_status_from_execution_no_trade_bridge(
            status,
            execution_no_trade_bridge=bridge_state.execution_no_trade_bridge,
        ),
        lambda status: elevate_headline_status_from_execution_runtime_projection_bridge(
            status,
            execution_runtime_projection_bridge=bridge_state.execution_runtime_projection_bridge,
        ),
        lambda status: elevate_headline_status_from_runtime_hook_bridges(
            status,
            runtime_hook_bridges=bridge_state.runtime_hook_bridges,
        ),
        lambda status: elevate_headline_status_from_replay_import(
            status,
            replay_import=bridge_state.replay_import,
        ),
        lambda status: elevate_headline_status_from_rollout(
            status,
            shadow=projection_state.shadow,
            micro_live=projection_state.micro_live,
            live_light=projection_state.live_light,
        ),
        lambda status: _elevate_headline_status_from_build9_meta(
            status,
            build9_meta=projection_state.build9_meta,
        ),
    ):
        headline_status = update(headline_status)
    return headline_status


def _build_system_projection(
    state: _ResolvedDashboardState,
    *,
    active_modules: tuple[str, ...],
    active_engines: tuple[str, ...],
) -> SystemProjection:
    stale_engines = tuple(
        engine.engine_id
        for engine in state.snapshot.engines
        if engine.stale and (not active_engines or engine.engine_id in active_engines)
    )
    return SystemProjection(
        headline_status=state.headline_status,
        active_modules=active_modules,
        active_engines=active_engines,
        stale_engines=stale_engines,
        build9x_status=state.build9x.status,
        shadow_status=state.shadow.status,
        micro_live_status=state.micro_live.status,
        live_light_status=state.live_light.status,
        build14_status=state.build14.status,
        replay_import_status=state.replay_import.status,
        governed_extensions_detail=(
            "Build-9X, Shadow, Micro-live, Live (historical label: Live-Light), "
            "replay/import, and Build-14 enablers remain governed. "
            "Complete stays closed and Build-14 does not bypass engines, risk, or portfolio."
        ),
    )


def build_technical_dashboard_payload(
    snapshot: MonitoringSnapshot,
    *,
    active_modules: tuple[str, ...] = (),
    active_engines: tuple[str, ...] = (),
    build9x_projection: Build9XProjection | None = None,
    engine_judgment_projection: EngineJudgmentProjection | None = None,
    shadow_projection: ShadowProjection | None = None,
    micro_live_projection: MicroLiveProjection | None = None,
    live_projection: LiveProjection | None = None,
    live_light_projection: LiveLightProjection | None = None,
    build14_projection: Build14Projection | None = None,
    account_user_data_projection: AccountUserDataProjection | None = None,
    execution_no_trade_bridge_projection: ExecutionNoTradeBridgeProjection | None = None,
    execution_runtime_projection_bridge_projection: ExecutionRuntimeProjectionBridgeProjection
    | None = None,
    hybrid_router_projection: HybridRouterMetricsProjection | None = None,
    artifact_runtime_visibility: tuple[ArtifactRuntimeVisibilityProjection, ...] | None = None,
    artifact_threshold_consumers: tuple[ArtifactThresholdConsumerProjection, ...] | None = None,
    artifact_comparisons: tuple[ArtifactComparisonProjection, ...] | None = None,
    artifact_verdict_bundle: ArtifactVerdictBundleProjection | None = None,
    shadow_last_completed_session_date: str = "",
    runtime_hook_bridge_projections: tuple[RuntimeHookBridgeProjection, ...] | None = None,
    replay_projection: ReplayImportProjection | None = None,
    operator_runtime: OperatorRuntimeProjection | None = None,
) -> TechnicalDashboardPayload:
    """Normalize runtime supervision truth into a typed Build-10 payload."""

    resolved_snapshot = _resolve_snapshot(snapshot)
    resolved_artifact_runtime_visibility = artifact_runtime_visibility or ()
    resolved_artifact_comparisons = artifact_comparisons or ()
    challenger_alerts = build_shadow_challenger_alerts(
        resolved_snapshot,
        artifact_runtime_visibility=resolved_artifact_runtime_visibility,
        artifact_comparisons=resolved_artifact_comparisons,
        artifact_verdict_bundle=artifact_verdict_bundle,
        shadow_last_completed_session_date=shadow_last_completed_session_date,
    )
    snapshot_with_challenger_alerts = resolved_snapshot.model_copy(
        update={
            "alerts": merge_alert_records(
                resolved_snapshot.alerts,
                challenger_alerts,
            )
        }
    )
    state = _resolve_dashboard_state(
        snapshot_with_challenger_alerts,
        active_modules=active_modules,
        build9x_projection=build9x_projection,
        engine_judgment_projection=engine_judgment_projection,
        shadow_projection=shadow_projection,
        micro_live_projection=micro_live_projection,
        live_projection=live_projection,
        live_light_projection=live_light_projection,
        build14_projection=build14_projection,
        account_user_data_projection=account_user_data_projection,
        execution_no_trade_bridge_projection=execution_no_trade_bridge_projection,
        execution_runtime_projection_bridge_projection=(
            execution_runtime_projection_bridge_projection
        ),
        runtime_hook_bridge_projections=runtime_hook_bridge_projections,
        replay_projection=replay_projection,
        operator_runtime=operator_runtime,
    )

    return TechnicalDashboardPayload(
        timestamp_ms=state.snapshot.timestamp_ms,
        correlation_id=state.snapshot.correlation_id,
        profile=state.snapshot.profile,
        runtime_mode=state.snapshot.runtime_mode,
        system=_build_system_projection(
            state,
            active_modules=active_modules,
            active_engines=active_engines,
        ),
        portfolio=state.snapshot.portfolio,
        engines=state.snapshot.engines,
        pairs=state.snapshot.pairs,
        infra=state.snapshot.infra,
        build9_meta=state.build9_meta,
        build9x=state.build9x,
        engine_judgment=state.engine_judgment,
        shadow=state.shadow,
        micro_live=state.micro_live,
        live_light=state.live_light,
        build14=state.build14,
        account_user_data=state.account_user_data,
        execution_no_trade_bridge=state.execution_no_trade_bridge,
        execution_runtime_projection_bridge=state.execution_runtime_projection_bridge,
        hybrid_router=(
            hybrid_router_projection
            if hybrid_router_projection is not None
            else HybridRouterMetricsProjection()
        ),
        artifact_runtime_visibility=resolved_artifact_runtime_visibility,
        artifact_threshold_consumers=(
            artifact_threshold_consumers
            if artifact_threshold_consumers is not None
            else state.execution_runtime_projection_bridge.consumers
        ),
        artifact_comparisons=resolved_artifact_comparisons,
        artifact_verdict_bundle=artifact_verdict_bundle,
        shadow_last_completed_session_date=shadow_last_completed_session_date,
        runtime_hook_bridges=state.runtime_hook_bridges,
        replay_import=state.replay_import,
        alerts=_build_alert_projection(
            state.snapshot,
            headline_status=state.headline_status,
            operator_runtime=operator_runtime,
        ),
    )


__all__ = [
    "build_technical_dashboard_payload",
]
