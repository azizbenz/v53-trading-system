"""Typed engine coordination contracts shared across protocols and engines."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .closed_episode_contracts import EpisodeRef
from .domain_types import EngineId, Side
from .forecast_contracts import ConditioningRecord
from .refusal_records import RefusalRecord


_MIN_EPOCH_NS = 1_000_000_000_000_000_000
_MAX_EPOCH_NS = 9_999_999_999_999_999_999
_NS_PER_HOUR = 3_600_000_000_000


class EngineCoordinationAction(StrEnum):
    PERMIT = "permit"
    HARD_BLOCK = "hard_block"
    SIZE_REDUCED = "size_reduced"


class EngineCoordinationInput(BaseModel):
    """Bounded typed input for native cross-engine coordination rules."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    evaluated_at_ns: int = Field(..., ge=_MIN_EPOCH_NS, le=_MAX_EPOCH_NS)
    engine_id: EngineId
    pair: str = Field(..., min_length=1)
    side: Side
    a_holding_block_active: bool = False
    recent_a_fire_same_setup_at_ns: int | None = Field(default=None, ge=_MIN_EPOCH_NS, le=_MAX_EPOCH_NS)
    first_episode_ref: EpisodeRef | None = None
    consecutive_d_stop_count: int = Field(default=0, ge=0)
    last_d_stop_at_ns: int | None = Field(default=None, ge=_MIN_EPOCH_NS, le=_MAX_EPOCH_NS)
    last_fresh_a_detection_at_ns: int | None = Field(default=None, ge=_MIN_EPOCH_NS, le=_MAX_EPOCH_NS)
    d_failsafe_override_available: bool = False
    reference_size: float | None = Field(default=None, gt=0.0)

    @field_validator("pair")
    @classmethod
    def _normalize_pair(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("pair must not be blank")
        return normalized


class EngineCoordinationThresholds(BaseModel):
    """Governed thresholds for the coordination seam."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    recent_fire_block_ns: int = Field(default=4 * _NS_PER_HOUR, gt=0, le=24 * _NS_PER_HOUR)
    d_consecutive_stop_limit: int = Field(default=1, ge=1, le=3)
    d_reset_failsafe_ns: int = Field(default=24 * _NS_PER_HOUR, gt=0, le=48 * _NS_PER_HOUR)
    d_reentry_size_multiplier: float = Field(default=0.5, gt=0.0, le=1.0)


class EngineCoordinationOutcome(BaseModel):
    """Deterministic result of the native coordination seam."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    blocked: bool = False
    action: EngineCoordinationAction = EngineCoordinationAction.PERMIT
    rule_hits: tuple[str, ...] = ()
    reason_codes: tuple[str, ...] = ()
    detail: str = ""
    conditioning_state: tuple[ConditioningRecord, ...] = ()
    refusal_record: RefusalRecord | None = None
    size_multiplier: float = Field(default=1.0, gt=0.0, le=1.0)
    resolved_size: float | None = Field(default=None, gt=0.0)


__all__ = [
    "EngineCoordinationAction",
    "EngineCoordinationInput",
    "EngineCoordinationOutcome",
    "EngineCoordinationThresholds",
]
