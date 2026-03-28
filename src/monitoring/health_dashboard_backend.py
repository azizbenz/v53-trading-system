"""Stable backend payload for the locked Build-10 Light UI."""

from __future__ import annotations

from interface_contracts import AlertSeverity
from monitoring.contracts import HealthDashboardPayload, MonitoringSnapshot


def build_health_dashboard_payload(snapshot: MonitoringSnapshot) -> HealthDashboardPayload:
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

    return HealthDashboardPayload(
        timestamp_ms=snapshot.timestamp_ms,
        correlation_id=snapshot.correlation_id,
        profile=snapshot.profile,
        runtime_mode=snapshot.runtime_mode,
        headline_status=headline_status,
        active_alert_count=snapshot.active_alert_count,
        stale_pair_count=snapshot.stale_pair_count,
        queue_backlog=snapshot.infra.queue_backlog,
        capital_deployed_usdt=snapshot.portfolio.capital_deployed_usdt,
        gross_capacity_used_pct=snapshot.portfolio.gross_capacity_used_pct,
        loss_capacity_used_pct=snapshot.portfolio.loss_capacity_used_pct,
        ce_net=snapshot.portfolio.ce_net,
        dtr_coverage=snapshot.meta.dtr_coverage,
        cra_sterilization_rate=snapshot.meta.cra_sterilization_rate,
        break_even_drift_scopes=snapshot.meta.break_even_drift_scopes,
        edge_credible_count=snapshot.meta.edge_credible_count,
        edge_degraded_count=snapshot.meta.edge_degraded_count,
        edge_surveillance_count=snapshot.meta.edge_surveillance_count,
        future_learning_diagnostics=snapshot.meta.future_learning_diagnostics,
        future_learning_hypotheses=snapshot.meta.future_learning_hypotheses,
    )


__all__ = [
    "build_health_dashboard_payload",
]
