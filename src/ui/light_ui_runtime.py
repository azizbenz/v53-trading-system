"""Stateful runtime for the locked Build-10 Light UI."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel, Field

from interface_contracts import AlertRecord, AlertSeverity
from interface_contracts.atomic_io import atomic_write_json
from monitoring.contracts import (
    HealthDashboardPayload,
    OperatorRuntimeEvent,
    OperatorRuntimeProjection,
)
from ui.contracts import (
    NotificationDeliveryState,
    OperatorActionLogEntry,
    OperatorActionOutcome,
    OperatorActionRequest,
    OperatorActionType,
    OperatorEventType,
    OperatorNotificationContract,
    OperatorNotificationRecord,
    LightDashboardView,
)
from ui.operator_actions import build_light_allowed_actions, evaluate_light_operator_action, record_screen_open
from ui.ui_light_locked import build_light_dashboard_view


_OPERATOR_PROJECTION_EVENT_LIMIT = 10
_OPERATOR_SAFING_ACTIONS = frozenset(
    {
        OperatorActionType.SET_HALTED.value,
        OperatorActionType.DOWNGRADE_TO_MICRO_LIVE.value,
        OperatorActionType.DOWNGRADE_TO_SHADOW.value,
    }
)


class LightUIRuntimeConfig(BaseModel, frozen=True):
    """Runtime configuration for the locked Build-10 Light UI."""

    state_dir: Path | None = None
    persist_history: bool = False
    supported_channels: tuple[str, ...] = ("slack_webhook_contract", "telegram_contract")
    event_log_limit: int = Field(default=200, ge=1)
    state_filename: str = "light_ui_runtime_state.json"


class LightUIRuntimeState(BaseModel):
    """Persisted state for the locked Light UI runtime."""

    session_id: str
    active_view: str = "overview"
    last_action: str = ""
    consultation_filters: tuple[str, ...] = ()
    event_log: list[OperatorActionLogEntry] = Field(default_factory=list)
    notifications: list[OperatorNotificationRecord] = Field(default_factory=list)
    visible_critical_alert_ids: tuple[str, ...] = ()


class LightUIRuntimeResult(BaseModel, frozen=True):
    """Audit-ready Build-10 Light UI runtime result."""

    view: LightDashboardView
    visible_critical_alert_ids: tuple[str, ...] = ()
    state_path: str = ""


class LightUIRuntime:
    """Stateful Build-10 runtime for locked UI actions and critical notifications."""

    def __init__(self, *, config: LightUIRuntimeConfig | None = None) -> None:
        self._config = config or LightUIRuntimeConfig()
        self._state_path = (
            self._config.state_dir / self._config.state_filename
            if self._config.state_dir is not None
            else None
        )
        self._state = self._load_or_create()

    def build_view(
        self,
        payload: HealthDashboardPayload,
        *,
        alerts: tuple[AlertRecord, ...] = (),
        active_view: str = "overview",
    ) -> LightUIRuntimeResult:
        """Project the Light UI with stateful history and notification records."""

        self._record_screen_open(
            correlation_id=payload.correlation_id,
            timestamp_ms=payload.timestamp_ms,
            screen_id=active_view,
        )
        visible_critical_alert_ids = tuple(
            alert.alert_id
            for alert in alerts
            if alert.severity == AlertSeverity.CRITICAL and not alert.resolved
        )
        self._state.visible_critical_alert_ids = visible_critical_alert_ids
        self._sync_notifications(
            correlation_id=payload.correlation_id,
            timestamp_ms=payload.timestamp_ms,
            alerts=alerts,
        )
        self._persist()

        base_view = build_light_dashboard_view(
            payload.model_copy(update={"operator_runtime": self._project_operator_runtime()})
        )
        return LightUIRuntimeResult(
            view=base_view.model_copy(
                update={
                    "event_log": tuple(self._tail_events()),
                    "allowed_actions": build_light_allowed_actions(payload.runtime_mode),
                    "notification_contract": OperatorNotificationContract(
                        critical_delivery_required=True,
                        implementation_status="contract_only",
                        supported_channels=self._config.supported_channels,
                        escalation_target="human_operator",
                        delivery_expectation="immediate_for_critical",
                    ),
                    "pending_notifications": tuple(
                        notification
                        for notification in self._state.notifications
                        if not notification.acknowledged
                    ),
                }
            ),
            visible_critical_alert_ids=visible_critical_alert_ids,
            state_path=str(self._state_path) if self._state_path is not None else "",
        )

    def submit_action(
        self,
        request: OperatorActionRequest,
        *,
        allowed_pairs: tuple[str, ...] = (),
        resumable_pairs: tuple[str, ...] = (),
    ) -> OperatorActionOutcome:
        """Evaluate and record an operator action through the locked Light UI."""

        outcome = evaluate_light_operator_action(
            request,
            allowed_pairs=allowed_pairs,
            resumable_pairs=resumable_pairs,
            critical_alert_ids=self._state.visible_critical_alert_ids,
        )
        self._append_logs(outcome.log_entries)
        self._state.last_action = request.action.value
        if outcome.accepted and request.action == OperatorActionType.ACKNOWLEDGE_CRITICAL_ALERT:
            self._acknowledge_notification(
                alert_id=request.target,
                timestamp_ms=request.timestamp_ms,
            )
        self._persist()
        return outcome

    def get_state(self) -> LightUIRuntimeState:
        """Return the current UI runtime state."""

        return self._state

    def get_operator_projection(self) -> OperatorRuntimeProjection:
        """Return the typed monitoring projection of the current operator state."""

        return self._project_operator_runtime()

    def _load_or_create(self) -> LightUIRuntimeState:
        if self._state_path is not None and self._state_path.exists():
            try:
                data = json.loads(self._state_path.read_text(encoding="utf-8"))
                return LightUIRuntimeState(**data)
            except (json.JSONDecodeError, ValueError, OSError):
                pass
        return LightUIRuntimeState(session_id=f"light-ui-session-{uuid4().hex}")

    def _persist(self) -> None:
        if not self._config.persist_history or self._state_path is None:
            return
        if self._config.state_dir is not None:
            self._config.state_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_json(self._state_path, self._state.model_dump(mode="json"))

    def _record_screen_open(
        self,
        *,
        correlation_id: str,
        timestamp_ms: int,
        screen_id: str,
    ) -> None:
        self._state.active_view = screen_id
        should_append = (
            not self._state.event_log
            or self._state.event_log[-1].event_type.value != "screen_opened"
            or self._state.event_log[-1].target != screen_id
            or self._state.event_log[-1].correlation_id != correlation_id
        )
        if should_append:
            self._state.event_log.append(
                record_screen_open(
                    correlation_id=correlation_id,
                    timestamp_ms=timestamp_ms,
                    screen_id=screen_id,
                )
            )

    def _sync_notifications(
        self,
        *,
        correlation_id: str,
        timestamp_ms: int,
        alerts: tuple[AlertRecord, ...],
    ) -> None:
        existing_ids = {notification.alert_id for notification in self._state.notifications}
        for alert in alerts:
            if alert.severity != AlertSeverity.CRITICAL or alert.resolved:
                continue
            if alert.alert_id in existing_ids:
                continue
            self._state.notifications.append(
                OperatorNotificationRecord(
                    timestamp_ms=timestamp_ms,
                    correlation_id=correlation_id,
                    alert_id=alert.alert_id,
                    severity=alert.severity,
                    message=alert.message,
                    channels=self._config.supported_channels,
                    delivery_state=NotificationDeliveryState.PENDING_CONTRACT,
                )
            )

    def _append_logs(self, entries: tuple[OperatorActionLogEntry, ...]) -> None:
        self._state.event_log.extend(entries)

    def _acknowledge_notification(self, *, alert_id: str, timestamp_ms: int) -> None:
        updated: list[OperatorNotificationRecord] = []
        for notification in self._state.notifications:
            if notification.alert_id == alert_id:
                updated.append(
                    notification.model_copy(
                        update={
                            "acknowledged": True,
                            "acknowledged_ms": timestamp_ms,
                            "delivery_state": NotificationDeliveryState.ACKNOWLEDGED,
                        }
                    )
                )
            else:
                updated.append(notification)
        self._state.notifications = updated

    def _tail_events(self) -> list[OperatorActionLogEntry]:
        return self._state.event_log[-self._config.event_log_limit :]

    def _project_operator_runtime(self) -> OperatorRuntimeProjection:
        latest_event = next(
            (
                event
                for event in reversed(self._state.event_log)
                if event.event_type != OperatorEventType.SCREEN_OPENED
            ),
            self._state.event_log[-1] if self._state.event_log else None,
        )
        pending_notifications = tuple(
            notification
            for notification in self._state.notifications
            if not notification.acknowledged
        )
        acknowledged_notifications = tuple(
            notification
            for notification in self._state.notifications
            if notification.acknowledged
        )
        recent_events = tuple(
            OperatorRuntimeEvent(
                timestamp_ms=event.timestamp_ms,
                correlation_id=event.correlation_id,
                event_type=event.event_type.value,
                action=event.action.value,
                source_runtime_mode=(
                    event.source_runtime_mode.value
                    if event.source_runtime_mode is not None
                    else ""
                ),
                target_runtime_mode=(
                    event.target_runtime_mode.value
                    if event.target_runtime_mode is not None
                    else ""
                ),
                target=event.target,
                accepted=event.accepted,
                message=event.message,
                operator_reason=event.operator_reason,
                rejection_reason=event.rejection_reason,
            )
            for event in self._tail_events()[-_OPERATOR_PROJECTION_EVENT_LIMIT :]
        )
        rejection_events = tuple(
            event
            for event in recent_events
            if event.rejection_reason
        )
        latest_acknowledged = max(
            acknowledged_notifications,
            key=lambda notification: notification.acknowledged_ms or 0,
            default=None,
        )
        latest_safing_event = next(
            (
                event
                for event in reversed(self._state.event_log)
                if event.accepted
                and event.action.value in _OPERATOR_SAFING_ACTIONS
            ),
            None,
        )
        return OperatorRuntimeProjection(
            event_count=len(self._state.event_log),
            latest_event_type=(
                latest_event.event_type.value
                if latest_event is not None
                else ""
            ),
            latest_event_message=latest_event.message if latest_event is not None else "",
            recent_event_log=recent_events,
            rejection_event_count=len(rejection_events),
            latest_rejection_reason=(
                rejection_events[-1].rejection_reason if rejection_events else ""
            ),
            pending_notification_count=len(pending_notifications),
            pending_notification_alert_ids=tuple(
                notification.alert_id for notification in pending_notifications
            ),
            acknowledged_notification_count=len(acknowledged_notifications),
            latest_acknowledged_alert_id=(
                latest_acknowledged.alert_id if latest_acknowledged is not None else ""
            ),
            latest_safing_action=(
                latest_safing_event.action.value if latest_safing_event is not None else ""
            ),
            latest_safing_source_runtime_mode=(
                latest_safing_event.source_runtime_mode.value
                if latest_safing_event is not None
                and latest_safing_event.source_runtime_mode is not None
                else ""
            ),
            latest_safing_target_runtime_mode=(
                latest_safing_event.target_runtime_mode.value
                if latest_safing_event is not None
                and latest_safing_event.target_runtime_mode is not None
                else ""
            ),
            latest_safing_reason=(
                latest_safing_event.operator_reason
                if latest_safing_event is not None
                else ""
            ),
        )


__all__ = [
    "LightUIRuntimeConfig",
    "LightUIRuntimeState",
    "LightUIRuntimeResult",
    "LightUIRuntime",
]
