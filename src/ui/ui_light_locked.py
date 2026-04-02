"""Projection layer for the locked Build-10 Light UI."""

from __future__ import annotations

from interface_contracts import DeploymentState
from monitoring.contracts import HealthDashboardPayload
from ui.contracts import DashboardCard, DashboardSection, LightDashboardView
from ui.operator_actions import build_light_allowed_actions, record_screen_open


def build_light_dashboard_view(payload: HealthDashboardPayload) -> LightDashboardView:
    """Render the stable backend payload into a locked UI view model."""

    sections = (
        _build_health_section(payload),
        _build_profile_state_section(payload),
        _build_portfolio_section(payload),
        DashboardSection(title="Pairs", cards=_build_pair_cards(payload)),
        DashboardSection(title="Engines", cards=_build_engine_cards(payload)),
        _build_risk_section(payload),
        _build_execution_section(payload),
        _build_infra_section(payload),
        _build_meta_section(payload),
        _build_alerts_events_section(payload),
        _build_future_learning_section(payload),
    )

    return LightDashboardView(
        timestamp_ms=payload.timestamp_ms,
        correlation_id=payload.correlation_id,
        profile=payload.profile,
        runtime_mode=payload.runtime_mode,
        sections=sections,
        allowed_actions=build_light_allowed_actions(payload.runtime_mode),
        event_log=(
            record_screen_open(
                correlation_id=payload.correlation_id,
                timestamp_ms=payload.timestamp_ms,
                screen_id="overview",
            ),
        ),
        future_panels=("build9x_diagnostics", "strategy_onboarding", "artifact_import"),
    )


def _build_health_section(payload: HealthDashboardPayload) -> DashboardSection:
    return DashboardSection(
        title="Health",
        cards=(
            DashboardCard(
                key="headline_status",
                label="Headline",
                value=payload.headline_status,
                status=payload.headline_status,
                detail=f"{payload.active_alert_count} active alert(s)",
            ),
            DashboardCard(
                key="stale_pairs",
                label="Stale Pairs",
                value=str(payload.stale_pair_count),
                status="warning" if payload.stale_pair_count else "healthy",
                detail=f"Queue backlog {payload.queue_backlog}",
            ),
        ),
    )


def _build_profile_state_section(payload: HealthDashboardPayload) -> DashboardSection:
    rollout_detail = (
        f"shadow={payload.shadow_status} / "
        f"micro={payload.micro_live_status} / "
        f"live={payload.live_light_status}"
    )
    return DashboardSection(
        title="Profile & State",
        cards=(
            DashboardCard(
                key="profile",
                label="Profile",
                value=_enum_label(payload.profile),
                status="healthy",
                detail="Locked Light surface",
            ),
            DashboardCard(
                key="deployment_state",
                label="Deployment State",
                value=_enum_label(payload.deployment_state),
                status=_deployment_state_status(payload.deployment_state),
                detail=rollout_detail,
            ),
            DashboardCard(
                key="last_transition",
                label="Last Transition",
                value=payload.last_transition_summary or "not available",
                status="info",
                detail=f"runtime={_enum_label(payload.runtime_mode)}",
            ),
            DashboardCard(
                key="controls_locked",
                label="Controls",
                value="locked" if payload.controls_locked else "open",
                status="healthy" if payload.controls_locked else "warning",
                detail="No Complete/custom overrides exposed",
            ),
        ),
    )


def _build_portfolio_section(payload: HealthDashboardPayload) -> DashboardSection:
    return DashboardSection(
        title="Portfolio",
        cards=(
            DashboardCard(
                key="capital_deployed",
                label="Capital Deployed",
                value=f"{payload.capital_deployed_usdt:.2f}",
                status="info",
                detail=(
                    f"Gross {payload.gross_capacity_used_pct:.1f}% / "
                    f"Loss {payload.loss_capacity_used_pct:.1f}%"
                ),
            ),
            DashboardCard(
                key="pnl_net",
                label="PnL Net",
                value=f"{payload.pnl_net_usdt:.2f}",
                status="healthy" if payload.pnl_net_usdt >= 0 else "warning",
                detail=f"beta {payload.beta_utilization:.2f}",
            ),
            DashboardCard(
                key="ce_net",
                label="CE Net",
                value=f"{payload.ce_net:.6f}",
                status="healthy" if payload.ce_net >= 0 else "warning",
                detail=f"Dominant cluster: {payload.dominant_cluster or 'n/a'}",
            ),
        ),
    )


def _build_pair_cards(payload: HealthDashboardPayload) -> tuple[DashboardCard, ...]:
    if not payload.pairs:
        return (
            DashboardCard(
                key="pairs_unavailable",
                label="Pairs",
                value="none",
                status="info",
                detail="No pair metrics projected into the locked Light UI",
            ),
        )

    return tuple(
        DashboardCard(
            key=f"pair_{pair.pair.lower()}",
            label=pair.pair,
            value=_enum_label(pair.health),
            status=_pair_status(pair),
            detail=(
                f"active={pair.is_active} backlog={pair.backlog_depth} "
                f"ce={pair.ce_expected:.6f} cost={pair.average_cost_bps:.2f}/{pair.cost_p90_bps:.2f}"
                + (f" reason={pair.suspension_reason}" if pair.suspension_reason else "")
            ),
        )
        for pair in payload.pairs
    )


def _build_engine_cards(payload: HealthDashboardPayload) -> tuple[DashboardCard, ...]:
    if not payload.engines:
        return (
            DashboardCard(
                key="engines_unavailable",
                label="Engines",
                value="none",
                status="info",
                detail="No engine metrics projected into the locked Light UI",
            ),
        )

    return tuple(
        DashboardCard(
            key=f"engine_{engine.engine_id.lower()}",
            label=engine.engine_id,
            value=f"{engine.net_edge_bps:.2f} bps",
            status=_engine_status(engine),
            detail=(
                f"ce={engine.ce_expected:.6f} cost={engine.expected_cost_bps:.2f} "
                f"freq={engine.useful_frequency:.2f}"
                + (f" reason={engine.suspension_reason}" if engine.suspension_reason else "")
            ),
        )
        for engine in payload.engines
    )


def _build_risk_section(payload: HealthDashboardPayload) -> DashboardSection:
    return DashboardSection(
        title="Risk",
        cards=(
            DashboardCard(
                key="risk_capacity",
                label="Capacity",
                value=f"G{payload.gross_capacity_used_pct:.1f}% / L{payload.loss_capacity_used_pct:.1f}%",
                status="warning" if payload.loss_capacity_used_pct >= 80.0 else "healthy",
                detail=f"Capital {payload.capital_deployed_usdt:.2f}",
            ),
            DashboardCard(
                key="beta_cluster",
                label="Beta & Cluster",
                value=f"beta {payload.beta_utilization:.2f}",
                status="warning" if payload.beta_utilization >= 1.0 else "healthy",
                detail=f"Cluster {payload.dominant_cluster or 'n/a'}",
            ),
            DashboardCard(
                key="risk_breaches",
                label="Breaches",
                value=str(len(payload.risk_breaches)),
                status="warning" if payload.risk_breaches else "healthy",
                detail=", ".join(payload.risk_breaches) if payload.risk_breaches else "No active breach",
            ),
        ),
    )


def _build_execution_section(payload: HealthDashboardPayload) -> DashboardSection:
    realized_minus_expected = payload.realized_cost_bps - payload.expected_cost_bps
    return DashboardSection(
        title="Execution",
        cards=(
            DashboardCard(
                key="execution_costs",
                label="Cost Drift",
                value=f"{realized_minus_expected:.2f} bps",
                status="warning" if realized_minus_expected > 0.0 else "healthy",
                detail=(
                    f"Expected {payload.expected_cost_bps:.2f} / "
                    f"Realized {payload.realized_cost_bps:.2f}"
                ),
            ),
            DashboardCard(
                key="execution_elw",
                label="ELW & Partials",
                value=f"ELW {payload.elw_bps:.2f}",
                status="warning" if payload.partial_fill_count > 0 else "healthy",
                detail=f"Partial fills {payload.partial_fill_count}",
            ),
            DashboardCard(
                key="execution_latency",
                label="Latency & Reco",
                value=f"{payload.fill_latency_ms_p95} ms",
                status="warning" if payload.reconciliation_alert_count > 0 else "healthy",
                detail=f"Reconciliation alerts {payload.reconciliation_alert_count}",
            ),
        ),
    )


def _build_infra_section(payload: HealthDashboardPayload) -> DashboardSection:
    persistence_surface = (
        f"persisted={len(payload.persisted_metric_names)} "
        f"volatile={len(payload.volatile_metric_names)}"
    )
    return DashboardSection(
        title="Data & Infra",
        cards=(
            DashboardCard(
                key="infra_backlog",
                label="Backlog & Drop",
                value=f"{payload.queue_backlog}/{payload.backlog_high_water_mark}",
                status="critical" if payload.kill_switch_active else _headline_or_warning(payload),
                detail=f"drop {payload.drop_rate_pct:.2f}%",
            ),
            DashboardCard(
                key="infra_stale_recovery",
                label="Stale & Recovery",
                value=f"{payload.stale_pair_count} stale",
                status="warning" if (payload.stale_pair_count or payload.recovery_retry_count) else "healthy",
                detail=(
                    f"reconnects={payload.reconnect_count} "
                    f"stale_spikes={payload.stale_spike_count} recovery={payload.recovery_retry_count}"
                ),
            ),
            DashboardCard(
                key="infra_losses_runtime",
                label="Losses & Runtime",
                value=f"dtr {payload.dtr_loss_count} / log {payload.log_loss_count}",
                status="critical" if (payload.dtr_loss_count or payload.log_loss_count) else "healthy",
                detail=f"cpu={payload.cpu_pct:.1f}% ram={payload.ram_pct:.1f}%",
            ),
            DashboardCard(
                key="infra_persistence",
                label="Observability",
                value="critical" if payload.kill_switch_active else "tracked",
                status="critical" if payload.kill_switch_active else "info",
                detail=persistence_surface,
            ),
        ),
    )


def _build_meta_section(payload: HealthDashboardPayload) -> DashboardSection:
    return DashboardSection(
        title="Meta",
        cards=(
            DashboardCard(
                key="dtr_coverage",
                label="DTR Coverage",
                value=f"{payload.dtr_coverage:.2%}",
                status="healthy" if payload.dtr_coverage >= 0.8 else "warning",
            ),
            DashboardCard(
                key="cra_sterilization",
                label="CRA Sterilization",
                value=f"{payload.cra_sterilization_rate:.2%}",
                status="warning" if payload.cra_sterilization_rate >= 0.2 else "healthy",
                detail=f"CRA alerts {payload.cra_alert_count}",
            ),
            DashboardCard(
                key="edge_status",
                label="Edge Status",
                value=f"C{payload.edge_credible_count}/D{payload.edge_degraded_count}/S{payload.edge_surveillance_count}",
                status="warning" if payload.edge_degraded_count > 0 else "healthy",
                detail=f"Break-even drift scopes: {len(payload.break_even_drift_scopes)}",
            ),
        ),
    )


def _build_alerts_events_section(payload: HealthDashboardPayload) -> DashboardSection:
    latest_history = payload.alert_history[0] if payload.alert_history else None
    latest_ack_detail = (
        f"latest ack: {payload.operator_runtime.latest_acknowledged_alert_id}"
        if payload.operator_runtime.latest_acknowledged_alert_id
        else "No critical acknowledgement yet"
    )
    pending_detail = (
        ", ".join(payload.operator_runtime.pending_notification_alert_ids)
        if payload.operator_runtime.pending_notification_alert_ids
        else latest_ack_detail
    )
    return DashboardSection(
        title="Alerts & Events",
        cards=(
            DashboardCard(
                key="active_alerts",
                label="Active Alerts",
                value=str(payload.active_alert_count),
                status=(
                    "critical"
                    if payload.headline_status == "critical"
                    else "warning" if payload.active_alert_count else "healthy"
                ),
                detail=", ".join(payload.active_alert_ids[:3]) if payload.active_alert_ids else "No active alert",
            ),
            DashboardCard(
                key="alert_history",
                label="Alert History",
                value=str(len(payload.alert_history)),
                status="warning" if payload.alert_history else "info",
                detail=(
                    f"{latest_history.status}: {latest_history.message}"
                    if latest_history is not None
                    else "No alert lifecycle history yet"
                ),
            ),
            DashboardCard(
                key="operator_events",
                label="Operator Events",
                value=str(payload.operator_runtime.event_count),
                status="warning" if payload.operator_runtime.event_count > 1 else "info",
                detail=payload.operator_runtime.latest_event_message or "No operator event recorded yet",
            ),
            DashboardCard(
                key="critical_notifications",
                label="Critical Notifications",
                value=(
                    f"pending={payload.operator_runtime.pending_notification_count} / "
                    f"ack={payload.operator_runtime.acknowledged_notification_count}"
                ),
                status=(
                    "critical"
                    if payload.operator_runtime.pending_notification_count > 0
                    and payload.headline_status == "critical"
                    else "warning"
                    if payload.operator_runtime.pending_notification_count > 0
                    else "healthy"
                    if payload.operator_runtime.acknowledged_notification_count > 0
                    else "info"
                ),
                detail=pending_detail,
            ),
        ),
    )


def _build_future_learning_section(payload: HealthDashboardPayload) -> DashboardSection:
    return DashboardSection(
        title="Future Learning",
        cards=(
            DashboardCard(
                key="future_learning_diagnostics",
                label="Diagnostics",
                value=str(payload.future_learning_diagnostics),
                status="planned",
                detail="Reserved for Build-9X governed outputs",
            ),
            DashboardCard(
                key="future_learning_hypotheses",
                label="Hypotheses",
                value=str(payload.future_learning_hypotheses),
                status="planned",
                detail="Reserved for LOCAL_REPLAY candidate review",
            ),
        ),
    )


def _pair_status(pair) -> str:
    health_label = _enum_label(pair.health).lower()
    if health_label == "offline":
        return "critical"
    if health_label in {"stale", "suspended"} or not pair.is_active:
        return "warning"
    return "healthy"


def _engine_status(engine) -> str:
    if engine.stale or engine.suspension_reason or engine.net_edge_bps < 0:
        return "warning"
    return "healthy"


def _headline_or_warning(payload: HealthDashboardPayload) -> str:
    if payload.headline_status == "critical":
        return "warning"
    return "warning" if (payload.queue_backlog or payload.backlog_high_water_mark) else "healthy"


def _deployment_state_status(deployment_state: DeploymentState) -> str:
    if deployment_state == DeploymentState.HALTED:
        return "critical"
    if deployment_state == DeploymentState.DEGRADED:
        return "warning"
    return "healthy"


def _enum_label(value) -> str:
    return getattr(value, "value", str(value))


__all__ = [
    "build_light_dashboard_view",
]
