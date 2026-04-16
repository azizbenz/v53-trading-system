"""Shadow VPS service event helpers."""

from __future__ import annotations

from alerting import TelegramAlerter
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
    store.append_event(event)
    if telegram_alerter is None or event.event_type.startswith("telegram_alert_"):
        return
    alert = build_shadow_vps_service_alert_record(event)
    if alert is None:
        return
    result = telegram_alerter.send(alert)
    store.state.last_telegram_alert_delivery_status = (
        "skipped" if result.skipped else "sent" if result.delivered else "failed"
    )
    store.state.last_telegram_alert_delivery_event_type = event.event_type
    store.state.last_telegram_alert_delivery_error = (
        "" if result.delivered or result.skipped else result.reason
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
                f"Telegram alert delivered for {event.event_type}."
                if result.delivered
                else f"Telegram alert failed for {event.event_type}: {result.reason}"
            ),
            session_date=event.session_date,
            export_dir_ref=event.export_dir_ref,
            error="" if result.delivered else result.reason,
        )
    )
