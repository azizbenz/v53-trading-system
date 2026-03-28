"""Locked Build-10 Light UI backend surface."""

from ui.contracts import DashboardCard, DashboardSection, LightDashboardView, LockedControlSurface
from ui.ui_light_locked import build_light_dashboard_view
from ui.technical_dashboard_view import build_technical_dashboard_view

__all__ = [
    "DashboardCard",
    "DashboardSection",
    "LockedControlSurface",
    "LightDashboardView",
    "build_light_dashboard_view",
    "build_technical_dashboard_view",
]
