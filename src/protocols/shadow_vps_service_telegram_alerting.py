"""Build-11 operated Telegram alerting seam for the Shadow VPS service."""

from __future__ import annotations

from interface_contracts import AlertCategory, AlertRecord, AlertSeverity
from protocols.shadow_vps_service import ShadowVpsServiceEvent


_CATEGORY_BY_EVENT_TYPE: dict[str, AlertCategory] = {
    "service_started": AlertCategory.INFRA,
    "service_stopped": AlertCategory.INFRA,
    "shadow_day_completed": AlertCategory.INFRA,
    "shadow_day_failed": AlertCategory.INFRA,
    "execution_telemetry_failed": AlertCategory.INFRA,
}

_SEVERITY_BY_EVENT_TYPE: dict[str, AlertSeverity] = {
    "service_started": AlertSeverity.INFO,
    "service_stopped": AlertSeverity.INFO,
    "shadow_day_completed": AlertSeverity.INFO,
    "shadow_day_failed": AlertSeverity.CRITICAL,
    "execution_telemetry_failed": AlertSeverity.CRITICAL,
}


def build_shadow_vps_service_alert_record(
    event: ShadowVpsServiceEvent,
) -> AlertRecord | None:
    """Project an operated Shadow service event into a canonical external alert."""

    severity = _SEVERITY_BY_EVENT_TYPE.get(event.event_type)
    category = _CATEGORY_BY_EVENT_TYPE.get(event.event_type)
    if severity is None or category is None:
        return None

    detail_parts: list[str] = [event.message]
    if event.session_date:
        detail_parts.append(f"session_date={event.session_date}")
    if event.export_dir_ref:
        detail_parts.append(f"export_dir_ref={event.export_dir_ref}")
    if event.error:
        detail_parts.append(f"error={event.error}")

    return AlertRecord(
        timestamp_ms=max(1, int(event.timestamp * 1000)),
        alert_id=(
            f"shadow_vps_service:{event.event_type}:"
            f"{max(1, int(event.timestamp * 1000))}"
        ),
        severity=severity,
        category=category,
        message=" | ".join(detail_parts),
        module="shadow_vps_service",
        resolved=False,
    )


__all__ = ["build_shadow_vps_service_alert_record"]
