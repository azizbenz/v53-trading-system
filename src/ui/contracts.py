"""Contracts for the locked Build-10 Light UI backend surface."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from interface_contracts import ProfileId, RuntimeMode, TimestampedModel


DashboardStatus = Literal["healthy", "warning", "critical", "info", "planned"]


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


class LightDashboardView(TimestampedModel):
    """Final structured view consumed by the locked Light UI."""

    correlation_id: str = Field(..., min_length=1)
    profile: ProfileId
    runtime_mode: RuntimeMode
    sections: tuple[DashboardSection, ...]
    control_surface: LockedControlSurface = LockedControlSurface()
    future_panels: tuple[str, ...] = ()


__all__ = [
    "DashboardCard",
    "DashboardSection",
    "DashboardStatus",
    "LockedControlSurface",
    "LightDashboardView",
]
