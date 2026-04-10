"""Typed alert projection for the bounded halal account audit."""

from __future__ import annotations

from interface_contracts import AlertCategory, AlertRecord, AlertSeverity

from .contracts import AccountFeaturesAuditReport, AaoifiPairScreeningAuditReport


def build_account_feature_audit_alerts(
    report: AccountFeaturesAuditReport,
    *,
    correlation_id: str,
    module: str = "sharia_account_audit",
) -> tuple[AlertRecord, ...]:
    alerts: list[AlertRecord] = []
    for index, finding in enumerate(report.findings, start=1):
        alerts.append(
            AlertRecord(
                timestamp_ms=int(report.scanned_at.timestamp() * 1000),
                alert_id=f"{correlation_id}:sharia_account_feature:{index}",
                severity=AlertSeverity.CRITICAL,
                category=AlertCategory.RISK,
                message=finding.detail,
                module=module,
            )
        )
    return tuple(alerts)


def build_pair_screening_audit_alerts(
    report: AaoifiPairScreeningAuditReport,
    *,
    correlation_id: str,
    module: str = "sharia_pair_screening_audit",
) -> tuple[AlertRecord, ...]:
    alerts: list[AlertRecord] = []
    for index, finding in enumerate(report.findings, start=1):
        alerts.append(
            AlertRecord(
                timestamp_ms=int(report.scanned_at.timestamp() * 1000),
                alert_id=f"{correlation_id}:sharia_pair_screening:{index}",
                severity=AlertSeverity.CRITICAL,
                category=AlertCategory.RISK,
                message=f"{finding.pair}: {finding.detail}",
                module=module,
            )
        )
    return tuple(alerts)


__all__ = ["build_account_feature_audit_alerts", "build_pair_screening_audit_alerts"]
