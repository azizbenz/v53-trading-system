"""Typed models for shadow day counting and promotion readiness."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class ShadowProfile(StrEnum):
    LIGHT = "light"
    COMPLETE = "complete"


class ShadowDayRecord(BaseModel, frozen=True):
    """Record of a single shadow day."""

    day_number: int
    date: str
    timestamp: float
    profile: ShadowProfile
    passed_all_gates: bool
    metrics_summary: dict[str, float | str] = Field(default_factory=dict)


class ShadowCounterState(BaseModel, frozen=True):
    """Persisted counter state."""

    profile: ShadowProfile
    consecutive_days: int = 0
    required_days: int = 30
    last_shadow_timestamp: float | None = None
    started_at: float | None = None
    daily_records: list[ShadowDayRecord] = Field(default_factory=list)
    resets: int = 0
    last_error: str | None = None

    @property
    def is_complete(self) -> bool:
        return self.consecutive_days >= self.required_days

    @property
    def remaining_days(self) -> int:
        return max(0, self.required_days - self.consecutive_days)


__all__ = [
    "ShadowCounterState",
    "ShadowDayRecord",
    "ShadowProfile",
]
