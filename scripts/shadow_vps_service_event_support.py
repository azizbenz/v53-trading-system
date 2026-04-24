"""Shadow VPS service event helpers."""

from __future__ import annotations

from alerting import TelegramAlerter
from monitoring.shadow_vps_redaction import (
    redact_shadow_vps_event,
    redact_shadow_vps_text,
)
from protocols import ShadowVpsServiceEvent, ShadowVpsServiceStore
from protocols.shadow_vps_service_telegram_alerting import (
    build_shadow_vps_service_alert_record,
)


def _append_service_event(
    *,
    store: ShadowVpsServiceStore,
    event: ShadowVpsServiceEvent,
    telegram_alerter: TelegramAlerter | None,
) -> None:
    sanitized_event = redact_shadow_vps_event(event)
    store.append_event(sanitized_event)
    if telegram_alerter is None or sanitized_event.event_type.startswith("telegram_alert_"):
        return
    alert = build_shadow_vps_service_alert_record(sanitized_event)
    if alert is None:
        return
    result = telegram_alerter.send(alert)
    store.state.last_telegram_alert_delivery_status = (
        "skipped" if result.skipped else "sent" if result.delivered else "failed"
    )
    store.state.last_telegram_alert_delivery_event_type = sanitized_event.event_type
    store.state.last_telegram_alert_delivery_error = (
        ""
        if result.delivered or result.skipped
        else redact_shadow_vps_text(result.reason)
    )
    store.persist()
    if result.skipped:
        return
    store.append_event(
        ShadowVpsServiceEvent(
            event_type=(
                "telegram_alert_sent" if result.delivered else "telegram_alert_failed"
            ),
            message=(
                f"Telegram alert delivered for {sanitized_event.event_type}."
                if result.delivered
                else (
                    "Telegram alert failed for "
                    f"{sanitized_event.event_type}: "
                    f"{redact_shadow_vps_text(result.reason)}"
                )
            ),
            session_date=sanitized_event.session_date,
            export_dir_ref=sanitized_event.export_dir_ref,
            error="" if result.delivered else redact_shadow_vps_text(result.reason),
        )
    )
