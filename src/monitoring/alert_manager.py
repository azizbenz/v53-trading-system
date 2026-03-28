"""Alert projection for the real Build-10 monitoring backend."""

from __future__ import annotations

from interface_contracts import AlertCategory, AlertRecord, AlertSeverity
from monitoring.contracts import MonitoringSnapshot


def build_monitoring_alerts(snapshot: MonitoringSnapshot) -> tuple[AlertRecord, ...]:
    """Transform critical monitoring conditions into structured alerts."""

    alerts: list[AlertRecord] = []
    now = snapshot.timestamp_ms

    if snapshot.stale_warning:
        alerts.append(AlertRecord(
            timestamp_ms=now,
            alert_id=f"{snapshot.correlation_id}:stale",
            severity=AlertSeverity.WARNING,
            category=AlertCategory.DATA,
            message=f"{snapshot.stale_pair_count} stale/offline pair(s) detected",
            module="monitoring",
        ))

    if snapshot.backlog_warning:
        severity = AlertSeverity.CRITICAL if snapshot.infra.queue_backlog >= 100 else AlertSeverity.WARNING
        alerts.append(AlertRecord(
            timestamp_ms=now,
            alert_id=f"{snapshot.correlation_id}:backlog",
            severity=severity,
            category=AlertCategory.INFRA,
            message=f"Queue backlog elevated at {snapshot.infra.queue_backlog}",
            module="monitoring",
        ))

    if snapshot.loss_warning:
        alerts.append(AlertRecord(
            timestamp_ms=now,
            alert_id=f"{snapshot.correlation_id}:loss",
            severity=AlertSeverity.CRITICAL,
            category=AlertCategory.INFRA,
            message=(
                f"DTR/log loss detected: dtr={snapshot.infra.dtr_loss_count}, "
                f"log={snapshot.infra.log_loss_count}"
            ),
            module="monitoring",
        ))

    if snapshot.meta.break_even_drift_alert:
        alerts.append(AlertRecord(
            timestamp_ms=now,
            alert_id=f"{snapshot.correlation_id}:cost_drift",
            severity=AlertSeverity.WARNING,
            category=AlertCategory.COST,
            message=(
                "Break-even drift alert on scopes: "
                + ", ".join(snapshot.meta.break_even_drift_scopes)
            ),
            module="monitoring",
        ))

    if snapshot.meta.edge_degraded_count > 0:
        alerts.append(AlertRecord(
            timestamp_ms=now,
            alert_id=f"{snapshot.correlation_id}:edge_degraded",
            severity=AlertSeverity.WARNING,
            category=AlertCategory.ENGINE,
            message=f"{snapshot.meta.edge_degraded_count} degraded edge scope(s) detected",
            module="monitoring",
        ))

    return tuple(alerts)


__all__ = [
    "build_monitoring_alerts",
]
