"""Alert projection for the real Build-10 monitoring backend."""

from __future__ import annotations

from interface_contracts import AlertCategory, AlertRecord, AlertSeverity
from monitoring.contracts import AlertHistoryEntry, MonitoringSnapshot


_PERSISTENCE_REQUIRED_METRICS = frozenset(
    {
        "backlog_high_water_mark",
        "drop_rate_pct",
        "stale_spike_count",
        "recovery_retry_count",
        "kill_switch_active",
    }
)


class AlertLifecycleTracker:
    """Track short alert open/resolution history across monitoring evaluations."""

    def __init__(
        self,
        *,
        history_limit: int = 20,
        history: tuple[AlertHistoryEntry, ...] = (),
    ) -> None:
        self._history_limit = max(1, history_limit)
        self._history_by_id: dict[str, AlertHistoryEntry] = {
            entry.alert_id: entry for entry in history
        }

    def update(
        self,
        alerts: tuple[AlertRecord, ...],
        *,
        timestamp_ms: int,
    ) -> tuple[AlertHistoryEntry, ...]:
        """Refresh short alert lifecycle state from the current open-alert set."""

        current_alert_ids = {alert.alert_id for alert in alerts}
        for alert in alerts:
            previous_entry = self._history_by_id.get(alert.alert_id)
            opened_ms = previous_entry.opened_ms if previous_entry is not None else alert.timestamp_ms
            self._history_by_id[alert.alert_id] = AlertHistoryEntry(
                alert_id=alert.alert_id,
                severity=alert.severity,
                category=alert.category,
                message=alert.message,
                status="resolved" if alert.resolved else "open",
                opened_ms=opened_ms,
                last_seen_ms=timestamp_ms,
                resolved_ms=alert.resolved_ms,
            )

        for alert_id, entry in list(self._history_by_id.items()):
            if entry.status == "open" and alert_id not in current_alert_ids:
                self._history_by_id[alert_id] = entry.model_copy(
                    update={
                        "status": "resolved",
                        "last_seen_ms": timestamp_ms,
                        "resolved_ms": timestamp_ms,
                    }
                )

        return tuple(
            sorted(
                self._history_by_id.values(),
                key=lambda entry: (entry.last_seen_ms, entry.opened_ms),
                reverse=True,
            )[: self._history_limit]
        )


def build_monitoring_alerts(snapshot: MonitoringSnapshot) -> tuple[AlertRecord, ...]:
    """Transform critical monitoring conditions into structured alerts."""

    alerts: list[AlertRecord] = []
    now = snapshot.timestamp_ms

    gross_capacity_used_pct = snapshot.portfolio.gross_capacity_used_pct
    if gross_capacity_used_pct >= 100.0:
        alerts.append(AlertRecord(
            timestamp_ms=now,
            alert_id=f"{snapshot.correlation_id}:gross_cap_full",
            severity=AlertSeverity.CRITICAL,
            category=AlertCategory.RISK,
            message=f"Gross capacity budget is full at {gross_capacity_used_pct:.1f}%",
            module="monitoring",
        ))
    elif gross_capacity_used_pct >= 80.0:
        alerts.append(AlertRecord(
            timestamp_ms=now,
            alert_id=f"{snapshot.correlation_id}:gross_cap_near_full",
            severity=AlertSeverity.WARNING,
            category=AlertCategory.RISK,
            message=f"Gross capacity budget is near full at {gross_capacity_used_pct:.1f}%",
            module="monitoring",
        ))

    loss_capacity_used_pct = snapshot.portfolio.loss_capacity_used_pct
    if loss_capacity_used_pct >= 100.0:
        alerts.append(AlertRecord(
            timestamp_ms=now,
            alert_id=f"{snapshot.correlation_id}:loss_budget_full",
            severity=AlertSeverity.CRITICAL,
            category=AlertCategory.RISK,
            message=f"Loss budget is full at {loss_capacity_used_pct:.1f}%",
            module="monitoring",
        ))
    elif loss_capacity_used_pct >= 80.0:
        alerts.append(AlertRecord(
            timestamp_ms=now,
            alert_id=f"{snapshot.correlation_id}:loss_budget_near_full",
            severity=AlertSeverity.WARNING,
            category=AlertCategory.RISK,
            message=f"Loss budget is near full at {loss_capacity_used_pct:.1f}%",
            module="monitoring",
        ))

    if snapshot.portfolio.beta_utilization >= 1.0:
        alerts.append(AlertRecord(
            timestamp_ms=now,
            alert_id=f"{snapshot.correlation_id}:beta_btc_breach",
            severity=AlertSeverity.WARNING,
            category=AlertCategory.RISK,
            message=(
                "BTC beta utilization breached the governed limit at "
                f"{snapshot.portfolio.beta_utilization:.2f}"
            ),
            module="monitoring",
        ))

    if snapshot.portfolio.breaches:
        alerts.append(AlertRecord(
            timestamp_ms=now,
            alert_id=f"{snapshot.correlation_id}:cluster_breach",
            severity=AlertSeverity.WARNING,
            category=AlertCategory.RISK,
            message=(
                "Risk breach scopes detected: "
                + ", ".join(snapshot.portfolio.breaches)
            ),
            module="monitoring",
        ))

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

    if snapshot.infra.backlog_high_water_mark >= 500 and snapshot.infra.queue_backlog < 50:
        alerts.append(AlertRecord(
            timestamp_ms=now,
            alert_id=f"{snapshot.correlation_id}:snapshot_trompeur",
            severity=AlertSeverity.WARNING,
            category=AlertCategory.INFRA,
            message=(
                "Recent backlog high-water mark remained elevated even though current backlog cooled down"
            ),
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

    if snapshot.infra.kill_switch_active:
        alerts.append(AlertRecord(
            timestamp_ms=now,
            alert_id=f"{snapshot.correlation_id}:kill_switch_active",
            severity=AlertSeverity.CRITICAL,
            category=AlertCategory.RISK,
            message="Emergency kill switch is active; trading must remain halted",
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

    if snapshot.meta.cra_sterilization_rate >= 0.2 or snapshot.meta.cra_alert_count > 0:
        alerts.append(AlertRecord(
            timestamp_ms=now,
            alert_id=f"{snapshot.correlation_id}:sterilization_spike",
            severity=AlertSeverity.WARNING,
            category=AlertCategory.ENGINE,
            message=(
                f"CRA sterilization spike detected at {snapshot.meta.cra_sterilization_rate:.0%} "
                f"(alerts={snapshot.meta.cra_alert_count})"
            ),
            module="monitoring",
        ))

    if snapshot.infra.stale_spike_count > 0 and not snapshot.stale_warning:
        alerts.append(AlertRecord(
            timestamp_ms=now,
            alert_id=f"{snapshot.correlation_id}:stale_spike_recent",
            severity=AlertSeverity.WARNING,
            category=AlertCategory.DATA,
            message=(
                f"Recent stale spike count remains non-zero ({snapshot.infra.stale_spike_count})"
            ),
            module="monitoring",
        ))

    if snapshot.infra.recovery_retry_count >= 3:
        alerts.append(AlertRecord(
            timestamp_ms=now,
            alert_id=f"{snapshot.correlation_id}:recovery_loop",
            severity=AlertSeverity.WARNING,
            category=AlertCategory.INFRA,
            message=(
                f"Recovery retry count reached {snapshot.infra.recovery_retry_count} without a stable success"
            ),
            module="monitoring",
        ))

    # GEM-14: illusion verte — system looks healthy but no real trading activity
    if (
        snapshot.active_alert_count == 0
        and snapshot.portfolio.ce_net <= 0.0
        and snapshot.meta.dtr_coverage < 0.5
    ):
        alerts.append(AlertRecord(
            timestamp_ms=now,
            alert_id=f"{snapshot.correlation_id}:illusion_verte",
            severity=AlertSeverity.WARNING,
            category=AlertCategory.ENGINE,
            message=(
                "Illusion verte: no alerts but CE_net <= 0 and DTR coverage < 50%. "
                "System may appear healthy while not generating value."
            ),
            module="monitoring",
        ))

    # GEM-13: high-water mark breach — queue drop rate above threshold
    resolved_drop_rate_pct = snapshot.infra.drop_rate_pct
    if resolved_drop_rate_pct <= 0.0 and snapshot.infra.total_enqueued > 0:
        resolved_drop_rate_pct = (
            snapshot.infra.total_dropped / snapshot.infra.total_enqueued * 100.0
        )

    if resolved_drop_rate_pct > 5.0:
        alerts.append(AlertRecord(
            timestamp_ms=now,
            alert_id=f"{snapshot.correlation_id}:drop_rate_high",
            severity=AlertSeverity.WARNING,
            category=AlertCategory.INFRA,
            message=f"Queue drop rate {resolved_drop_rate_pct / 100.0:.1%} exceeds 5% threshold",
            module="monitoring",
        ))

    persisted_metrics = set(snapshot.infra.persisted_metric_names)
    missing_persistence = tuple(
        metric_name
        for metric_name in sorted(_PERSISTENCE_REQUIRED_METRICS)
        if metric_name not in persisted_metrics
    )
    if missing_persistence and (
        snapshot.infra.backlog_high_water_mark > 0
        or snapshot.infra.drop_rate_pct > 0.0
        or snapshot.infra.stale_spike_count > 0
        or snapshot.infra.recovery_retry_count > 0
        or snapshot.infra.kill_switch_active
    ):
        alerts.append(AlertRecord(
            timestamp_ms=now,
            alert_id=f"{snapshot.correlation_id}:observability_gap",
            severity=AlertSeverity.WARNING,
            category=AlertCategory.INFRA,
            message=(
                "Critical monitoring metrics are session-only: "
                + ", ".join(missing_persistence)
            ),
            module="monitoring",
        ))

    return tuple(alerts)
__all__ = [
    "AlertLifecycleTracker",
    "build_monitoring_alerts",
]
