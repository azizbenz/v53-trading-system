from __future__ import annotations

from datetime import datetime, timezone

from sharia_compliance import build_account_feature_audit_alerts, build_pair_screening_audit_alerts
from sharia_compliance.contracts import (
    AaoifiPairScreeningAuditFinding,
    AaoifiPairScreeningAuditReport,
    AccountFeatureAuditFinding,
    AccountFeaturesAuditReport,
)


def test_build_account_feature_audit_alerts_emits_critical_risk_alerts() -> None:
    report = AccountFeaturesAuditReport(
        scanned_at=datetime(2026, 4, 10, 12, 0, tzinfo=timezone.utc),
        audit_interval_s=604800,
        findings=(
            AccountFeatureAuditFinding(
                reason_code="FORBIDDEN_ACCOUNT_FEATURE_BALANCE",
                detail="forbidden account feature balance detected: simple_earn_usdt=12.5",
                observation="simple_earn_usdt",
            ),
        ),
    )

    alerts = build_account_feature_audit_alerts(report, correlation_id="corr-1")

    assert len(alerts) == 1
    assert alerts[0].alert_id == "corr-1:sharia_account_feature:1"
    assert alerts[0].severity.value == "critical"
    assert alerts[0].category.value == "risk"
    assert "simple_earn_usdt" in alerts[0].message


def test_build_pair_screening_audit_alerts_emits_critical_risk_alerts() -> None:
    report = AaoifiPairScreeningAuditReport(
        scanned_at=datetime(2026, 4, 10, 12, 0, tzinfo=timezone.utc),
        registry_version="registry_v1",
        screened_pairs=("BTCUSDT",),
        findings=(
            AaoifiPairScreeningAuditFinding(
                pair="BTCUSDT",
                reason_code="PAIR_SCREENING_FAILED",
                detail="BTCUSDT failed AAOIFI screening: AAOIFI_DEBT_RATIO_EXCEEDED",
            ),
        ),
    )

    alerts = build_pair_screening_audit_alerts(report, correlation_id="corr-1")

    assert len(alerts) == 1
    assert alerts[0].alert_id == "corr-1:sharia_pair_screening:1"
    assert alerts[0].severity.value == "critical"
    assert alerts[0].category.value == "risk"
    assert "BTCUSDT" in alerts[0].message
