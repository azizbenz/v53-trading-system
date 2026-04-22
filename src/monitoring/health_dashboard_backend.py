"""Stable backend payload for the locked Build-10 operator UI."""

from __future__ import annotations

from interface_contracts import AlertRecord, AlertSeverity, DeploymentState, RuntimeMode
from monitoring.contracts import (
    AlertHistoryEntry,
    HealthDashboardPayload,
    MonitoringSnapshot,
    OperatorRuntimeProjection,
)


def _default_projection_status(
    runtime_mode: RuntimeMode,
    *,
    stage: str,
) -> str:
    if stage == "shadow":
        return "healthy" if runtime_mode in {RuntimeMode.SHADOW, RuntimeMode.MICRO_LIVE, RuntimeMode.LIVE} else "planned"
    if stage == "micro_live":
        return "healthy" if runtime_mode in {RuntimeMode.MICRO_LIVE, RuntimeMode.LIVE} else "planned"
    if stage == "live_light":
        return "healthy" if runtime_mode == RuntimeMode.LIVE else "planned"
    raise ValueError(f"Unknown rollout stage: {stage}")


def _operator_halted(operator_runtime: OperatorRuntimeProjection | None) -> bool:
    if operator_runtime is None:
        return False
    if operator_runtime.latest_safing_action == "set_halted":
        return True
    return operator_runtime.latest_event_message.endswith("set_halted")


def _resolve_deployment_state(
    snapshot: MonitoringSnapshot,
    *,
    operator_runtime: OperatorRuntimeProjection | None,
    shadow_status: str,
    micro_live_status: str,
    live_light_status: str,
) -> DeploymentState:
    if snapshot.infra.kill_switch_active or _operator_halted(operator_runtime):
        return DeploymentState.HALTED
    if (
        shadow_status == "warning"
        or micro_live_status == "warning"
        or live_light_status == "warning"
    ):
        return DeploymentState.DEGRADED
    if live_light_status != "planned" or snapshot.runtime_mode == RuntimeMode.LIVE:
        return DeploymentState.LIVE_COMPLETE
    if micro_live_status != "planned" or snapshot.runtime_mode == RuntimeMode.MICRO_LIVE:
        return DeploymentState.MICRO_LIVE
    if shadow_status != "planned" or snapshot.runtime_mode == RuntimeMode.SHADOW:
        return DeploymentState.SHADOW
    return DeploymentState.BOOTSTRAP


def _resolve_last_transition_summary(
    snapshot: MonitoringSnapshot,
    *,
    deployment_state: DeploymentState,
    operator_runtime: OperatorRuntimeProjection | None,
) -> str:
    if (
        operator_runtime is not None
        and operator_runtime.latest_event_type
        and operator_runtime.latest_event_type != "screen_opened"
        and operator_runtime.latest_event_message
    ):
        return operator_runtime.latest_event_message
    if deployment_state == DeploymentState.HALTED and snapshot.infra.kill_switch_active:
        return "kill_switch_active -> halted"
    if deployment_state == DeploymentState.DEGRADED:
        return f"{snapshot.runtime_mode.value} -> degraded"
    if deployment_state == DeploymentState.LIVE_COMPLETE:
        return "entered live_complete"
    if deployment_state == DeploymentState.MICRO_LIVE:
        return "entered micro_live"
    if deployment_state == DeploymentState.SHADOW:
        return "entered shadow"
    return "entered bootstrap"


def build_health_dashboard_payload(
    snapshot: MonitoringSnapshot,
    *,
    alert_history: tuple[AlertHistoryEntry, ...] = (),
    operator_runtime: OperatorRuntimeProjection | None = None,
    shadow_status: str | None = None,
    micro_live_status: str | None = None,
    live_light_status: str | None = None,
) -> HealthDashboardPayload:
    """Structure monitoring truth into a locked UI/backend payload."""

    if snapshot.loss_warning or any(alert.severity == AlertSeverity.CRITICAL for alert in snapshot.alerts):
        headline_status = "critical"
    elif (
        snapshot.backlog_warning
        or snapshot.stale_warning
        or snapshot.meta.break_even_drift_alert
        or snapshot.meta.edge_degraded_count > 0
    ):
        headline_status = "warning"
    else:
        headline_status = "healthy"

    resolved_alert_history = alert_history or tuple(
        _project_alert_history_entry(alert) for alert in snapshot.alerts
    )
    resolved_shadow_status = shadow_status or _default_projection_status(
        snapshot.runtime_mode,
        stage="shadow",
    )
    resolved_micro_live_status = micro_live_status or _default_projection_status(
        snapshot.runtime_mode,
        stage="micro_live",
    )
    resolved_live_light_status = live_light_status or _default_projection_status(
        snapshot.runtime_mode,
        stage="live_light",
    )
    resolved_deployment_state = _resolve_deployment_state(
        snapshot,
        operator_runtime=operator_runtime,
        shadow_status=resolved_shadow_status,
        micro_live_status=resolved_micro_live_status,
        live_light_status=resolved_live_light_status,
    )
    return HealthDashboardPayload(
        timestamp_ms=snapshot.timestamp_ms,
        correlation_id=snapshot.correlation_id,
        profile=snapshot.profile,
        runtime_mode=snapshot.runtime_mode,
        headline_status=headline_status,
        active_alert_count=snapshot.active_alert_count,
        active_alert_ids=tuple(alert.alert_id for alert in snapshot.alerts),
        alert_history=resolved_alert_history,
        stale_pair_count=snapshot.stale_pair_count,
        queue_backlog=snapshot.infra.queue_backlog,
        backlog_high_water_mark=snapshot.infra.backlog_high_water_mark,
        drop_rate_pct=snapshot.infra.drop_rate_pct,
        stale_spike_count=snapshot.infra.stale_spike_count,
        recovery_retry_count=snapshot.infra.recovery_retry_count,
        kill_switch_active=snapshot.infra.kill_switch_active,
        kill_switch_timestamp_ms=snapshot.infra.kill_switch_timestamp_ms,
        persisted_metric_names=snapshot.infra.persisted_metric_names,
        volatile_metric_names=snapshot.infra.volatile_metric_names,
        capital_deployed_usdt=snapshot.portfolio.capital_deployed_usdt,
        pnl_net_usdt=snapshot.portfolio.pnl_net_usdt,
        gross_capacity_used_pct=snapshot.portfolio.gross_capacity_used_pct,
        loss_capacity_used_pct=snapshot.portfolio.loss_capacity_used_pct,
        beta_utilization=snapshot.portfolio.beta_utilization,
        ce_net=snapshot.portfolio.ce_net,
        dominant_cluster=snapshot.portfolio.dominant_cluster,
        risk_breaches=snapshot.portfolio.breaches,
        pairs=snapshot.pairs,
        engines=snapshot.engines,
        reconnect_count=snapshot.infra.reconnect_count,
        dtr_loss_count=snapshot.infra.dtr_loss_count,
        log_loss_count=snapshot.infra.log_loss_count,
        elw_bps=snapshot.infra.elw_bps,
        expected_cost_bps=snapshot.infra.expected_cost_bps,
        realized_cost_bps=snapshot.infra.realized_cost_bps,
        partial_fill_count=snapshot.infra.partial_fill_count,
        fill_latency_ms_p95=snapshot.infra.fill_latency_ms_p95,
        signal_to_submit_ms_p90=snapshot.infra.signal_to_submit_ms_p90,
        signal_to_scoring_ms_p90=snapshot.infra.signal_to_scoring_ms_p90,
        scoring_to_risk_ms_p90=snapshot.infra.scoring_to_risk_ms_p90,
        risk_to_portfolio_ms_p90=snapshot.infra.risk_to_portfolio_ms_p90,
        portfolio_to_submit_ms_p90=snapshot.infra.portfolio_to_submit_ms_p90,
        reconciliation_alert_count=snapshot.infra.reconciliation_alert_count,
        cpu_pct=snapshot.infra.cpu_pct,
        ram_pct=snapshot.infra.ram_pct,
        dtr_coverage=snapshot.meta.dtr_coverage,
        cra_sterilization_rate=snapshot.meta.cra_sterilization_rate,
        cra_alert_count=snapshot.meta.cra_alert_count,
        break_even_drift_scopes=snapshot.meta.break_even_drift_scopes,
        edge_credible_count=snapshot.meta.edge_credible_count,
        edge_degraded_count=snapshot.meta.edge_degraded_count,
        edge_surveillance_count=snapshot.meta.edge_surveillance_count,
        future_learning_diagnostics=snapshot.meta.future_learning_diagnostics,
        future_learning_hypotheses=snapshot.meta.future_learning_hypotheses,
        deployment_state=resolved_deployment_state,
        last_transition_summary=_resolve_last_transition_summary(
            snapshot,
            deployment_state=resolved_deployment_state,
            operator_runtime=operator_runtime,
        ),
        shadow_status=resolved_shadow_status,
        micro_live_status=resolved_micro_live_status,
        live_light_status=resolved_live_light_status,
        operator_runtime=operator_runtime or OperatorRuntimeProjection(),
    )


def _project_alert_history_entry(alert: AlertRecord) -> AlertHistoryEntry:
    return AlertHistoryEntry(
        alert_id=alert.alert_id,
        severity=alert.severity,
        category=alert.category,
        message=alert.message,
        status="resolved" if alert.resolved else "open",
        opened_ms=alert.timestamp_ms,
        last_seen_ms=alert.resolved_ms or alert.timestamp_ms,
        resolved_ms=alert.resolved_ms,
    )


__all__ = [
    "build_health_dashboard_payload",
]
