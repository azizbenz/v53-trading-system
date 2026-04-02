"""Contracts for the locked Build-10 Light UI backend surface."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field

from interface_contracts import AlertSeverity, ProfileId, RuntimeMode, TimestampedModel


DashboardStatus = Literal["healthy", "warning", "critical", "info", "planned"]


class OperatorActionType(StrEnum):
    """Governed operator actions exposed or rejected by the Light UI."""

    VIEW_CRITICAL_SCREENS = "view_critical_screens"
    SUSPEND_PAIR = "suspend_pair"
    REQUEST_PAIR_RESUME = "request_pair_resume"
    SUSPEND_ENGINE = "suspend_engine"
    SET_HALTED = "set_halted"
    DOWNGRADE_TO_MICRO_LIVE = "downgrade_to_micro_live"
    DOWNGRADE_TO_SHADOW = "downgrade_to_shadow"
    VIEW_ALERT_HISTORY = "view_alert_history"
    ACKNOWLEDGE_CRITICAL_ALERT = "acknowledge_critical_alert"
    LOAD_COMPLETE = "load_complete"
    ACTIVATE_ENGINE = "activate_engine"
    ACTIVATE_PAIRS = "activate_pairs"
    MODIFY_RISK_CAPS = "modify_risk_caps"
    BYPASS_HARD_BLOCKER = "bypass_hard_blocker"
    INJECT_CONFIG = "inject_config"


class OperatorEventType(StrEnum):
    """Audit log event kinds emitted by the locked Light UI."""

    ACTION_REQUESTED = "operator_action_requested"
    ACTION_ACCEPTED = "operator_action_accepted"
    ACTION_REJECTED = "operator_action_rejected"
    SCREEN_OPENED = "screen_opened"
    CRITICAL_ALERT_ACKNOWLEDGED = "critical_alert_acknowledged"


class NotificationDeliveryState(StrEnum):
    """Local delivery state for deferred operator notifications."""

    PENDING_CONTRACT = "pending_contract"
    ACKNOWLEDGED = "acknowledged"


class DashboardCard(BaseModel, frozen=True):
    """Single card displayed in the locked Light UI."""

    key: str = Field(..., min_length=1)
    label: str = Field(..., min_length=1)
    value: str = Field(..., min_length=1)
    status: DashboardStatus
    detail: str = ""


class DashboardSection(BaseModel, frozen=True):
    """Logical section rendered by the locked UI."""

    title: str = Field(..., min_length=1)
    cards: tuple[DashboardCard, ...] = ()


class LockedControlSurface(BaseModel, frozen=True):
    """Controls that remain intentionally locked in Build-10 Light."""

    profile_selector_enabled: bool = False
    engine_cd_toggle_enabled: bool = False
    complete_pairs_enabled: bool = False
    hard_guard_override_enabled: bool = False
    max_light_pairs: int = Field(default=6, ge=0)
    suspendable_engines: tuple[str, ...] = ("engine_a", "engine_b")


class OperatorActionRequest(TimestampedModel):
    """Governed operator request routed through the locked Light UI."""

    correlation_id: str = Field(..., min_length=1)
    profile: ProfileId
    runtime_mode: RuntimeMode
    action: OperatorActionType
    target: str = ""
    requested_by: str = Field(default="operator", min_length=1)
    requested_pair_count: int = Field(default=0, ge=0)
    reason: str = ""
    version_ref: str = ""


class OperatorActionLogEntry(TimestampedModel):
    """Audit-ready operator event log entry for Build-10."""

    correlation_id: str = Field(..., min_length=1)
    event_type: OperatorEventType
    action: OperatorActionType
    source_runtime_mode: RuntimeMode | None = None
    target_runtime_mode: RuntimeMode | None = None
    target: str = ""
    accepted: bool = False
    message: str = Field(..., min_length=1)
    operator_reason: str = ""
    rejection_reason: str = ""


class OperatorActionOutcome(BaseModel, frozen=True):
    """Structured decision returned by the locked Light UI governance layer."""

    accepted: bool
    resulting_state: str = ""
    rejection_reason: str = ""
    log_entries: tuple[OperatorActionLogEntry, ...] = ()


class OperatorNotificationContract(BaseModel, frozen=True):
    """Deferred-but-defined operator notification contract for critical alerts."""

    critical_delivery_required: bool = True
    implementation_status: Literal["contract_only", "integrated"] = "contract_only"
    supported_channels: tuple[str, ...] = ()
    escalation_target: str = "human_operator"
    delivery_expectation: str = "immediate_for_critical"


class OperatorNotificationRecord(TimestampedModel):
    """Critical alert notification tracked by the locked Light UI runtime."""

    correlation_id: str = Field(..., min_length=1)
    alert_id: str = Field(..., min_length=1)
    severity: AlertSeverity
    message: str = Field(..., min_length=1)
    channels: tuple[str, ...] = ()
    delivery_state: NotificationDeliveryState = NotificationDeliveryState.PENDING_CONTRACT
    acknowledged: bool = False
    acknowledged_ms: int | None = Field(default=None, ge=0)


class LightDashboardView(TimestampedModel):
    """Final structured view consumed by the locked Light UI."""

    correlation_id: str = Field(..., min_length=1)
    profile: ProfileId
    runtime_mode: RuntimeMode
    sections: tuple[DashboardSection, ...]
    control_surface: LockedControlSurface = LockedControlSurface()
    allowed_actions: tuple[OperatorActionType, ...] = ()
    event_log: tuple[OperatorActionLogEntry, ...] = ()
    notification_contract: OperatorNotificationContract = OperatorNotificationContract()
    pending_notifications: tuple[OperatorNotificationRecord, ...] = ()
    future_panels: tuple[str, ...] = ()


__all__ = [
    "DashboardCard",
    "DashboardSection",
    "DashboardStatus",
    "LockedControlSurface",
    "OperatorActionType",
    "OperatorEventType",
    "OperatorActionRequest",
    "OperatorActionLogEntry",
    "OperatorActionOutcome",
    "OperatorNotificationContract",
    "NotificationDeliveryState",
    "OperatorNotificationRecord",
    "LightDashboardView",
]
