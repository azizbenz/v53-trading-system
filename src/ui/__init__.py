"""Locked Build-10 Light UI backend surface."""

from ui.contracts import (
    DashboardCard,
    DashboardSection,
    LightDashboardView,
    LockedControlSurface,
    NotificationDeliveryState,
    OperatorActionLogEntry,
    OperatorActionOutcome,
    OperatorActionRequest,
    OperatorActionType,
    OperatorNotificationRecord,
    OperatorEventType,
    OperatorNotificationContract,
)
from ui.light_ui_runtime import LightUIRuntime, LightUIRuntimeConfig, LightUIRuntimeResult, LightUIRuntimeState
from ui.operator_actions import build_light_allowed_actions, evaluate_light_operator_action, record_screen_open
from ui.complete_dashboard_view import (
    CompleteDashboardSupplement,
    CompleteEngineMetadata,
    CompletePairMetadata,
    build_complete_dashboard_sections,
)
from ui.technical_dashboard_html import render_technical_dashboard_html
from ui.ui_light_locked import build_light_dashboard_view
from ui.technical_dashboard_view import build_technical_dashboard_view

__all__ = [
    "DashboardCard",
    "DashboardSection",
    "LockedControlSurface",
    "LightDashboardView",
    "NotificationDeliveryState",
    "OperatorActionType",
    "OperatorEventType",
    "OperatorActionRequest",
    "OperatorActionLogEntry",
    "OperatorActionOutcome",
    "OperatorNotificationContract",
    "OperatorNotificationRecord",
    "LightUIRuntimeConfig",
    "LightUIRuntimeState",
    "LightUIRuntimeResult",
    "LightUIRuntime",
    "CompletePairMetadata",
    "CompleteEngineMetadata",
    "CompleteDashboardSupplement",
    "build_complete_dashboard_sections",
    "build_light_allowed_actions",
    "evaluate_light_operator_action",
    "record_screen_open",
    "build_light_dashboard_view",
    "build_technical_dashboard_view",
    "render_technical_dashboard_html",
]
