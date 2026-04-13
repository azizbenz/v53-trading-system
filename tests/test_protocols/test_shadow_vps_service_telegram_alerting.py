from __future__ import annotations

from interface_contracts import AlertCategory, AlertSeverity
from protocols.shadow_vps_service import ShadowVpsServiceEvent
from protocols.shadow_vps_service_telegram_alerting import (
    build_shadow_vps_service_alert_record,
)


def test_build_shadow_vps_service_alert_record_projects_failure_event() -> None:
    alert = build_shadow_vps_service_alert_record(
        ShadowVpsServiceEvent(
            event_type="shadow_day_failed",
            timestamp=1_700_000_000.0,
            message="Governed Shadow day failed.",
            session_date="2026-04-12",
            export_dir_ref="E:/shadow/exports/2026-04-12",
            error="network timeout",
        )
    )

    assert alert is not None
    assert alert.severity == AlertSeverity.CRITICAL
    assert alert.category == AlertCategory.INFRA
    assert alert.module == "shadow_vps_service"
    assert "session_date=2026-04-12" in alert.message
    assert "error=network timeout" in alert.message


def test_build_shadow_vps_service_alert_record_ignores_non_mapped_event() -> None:
    alert = build_shadow_vps_service_alert_record(
        ShadowVpsServiceEvent(
            event_type="runtime_evidence_bundle_written",
            timestamp=1_700_000_000.0,
            message="bundle written",
        )
    )

    assert alert is None
