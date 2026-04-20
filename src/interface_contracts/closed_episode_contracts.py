"""Typed closed-episode contracts shared across protocols and engines."""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .domain_types import EngineId, Side
from .forecast_contracts import BetStructure, ForecastHorizonClass, ForecastTargetClass


_MIN_EPOCH_NS = 1_000_000_000_000_000_000
_MAX_EPOCH_NS = 9_999_999_999_999_999_999


class EpisodeCloseReason(StrEnum):
    """Canonical terminal reason of a closed A/C episode."""

    TAKE_PROFIT = "take_profit"
    STRUCTURAL_EXIT = "structural_exit"
    TIME_STOP = "time_stop"
    STOP_OUT = "stop_out"


class EpisodeRef(BaseModel):
    """Frozen reference to a closed A/C episode consumed by Engine D governance."""

    model_config = ConfigDict(frozen=True)

    episode_id: UUID
    engine_id_of_origin: EngineId
    pair: str = Field(..., min_length=1)
    side: Side
    entry_level: Decimal
    exit_level: Decimal
    bet_structure: BetStructure
    forecast_horizon_class: ForecastHorizonClass
    forecast_target_class: ForecastTargetClass
    closed_at_ns: int = Field(..., ge=_MIN_EPOCH_NS, le=_MAX_EPOCH_NS)
    close_reason: EpisodeCloseReason
    realized_pnl_decimal: Decimal

    @field_validator("engine_id_of_origin")
    @classmethod
    def _validate_origin_engine(cls, value: EngineId) -> EngineId:
        if value not in {EngineId.A, EngineId.C}:
            raise ValueError("EpisodeRef.engine_id_of_origin must be engine_a or engine_c")
        return value

    @field_validator("pair")
    @classmethod
    def _normalize_pair(cls, value: str) -> str:
        normalized = value.upper().strip()
        if not normalized:
            raise ValueError("EpisodeRef.pair must be non-empty")
        return normalized

    @field_validator("entry_level", "exit_level")
    @classmethod
    def _validate_level(cls, value: Decimal) -> Decimal:
        if value <= Decimal("0"):
            raise ValueError("EpisodeRef levels must be positive decimals")
        return value

    @property
    def is_d_eligible(self) -> bool:
        return self.close_reason != EpisodeCloseReason.STOP_OUT


__all__ = [
    "EpisodeCloseReason",
    "EpisodeRef",
]
