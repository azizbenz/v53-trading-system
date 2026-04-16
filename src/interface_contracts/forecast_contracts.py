"""
V5.3 - FORECAST_CONTRACTS
Additive Narang-grade forecast contract seam on top of the canonical decision signal.
"""

from __future__ import annotations

from collections.abc import Mapping
from enum import Enum, unique

from pydantic import ConfigDict, Field, field_validator

from .decision_contracts import SignalCandidate as DecisionSignalCandidate
from .domain_types import EngineId, Side, TimestampedModel


@unique
class ForecastTargetClass(str, Enum):
    DIRECTION_ONLY = "direction_only"
    DIRECTION_PLUS_STRENGTH = "direction_plus_strength"
    DIRECTION_PLUS_STRENGTH_PLUS_HORIZON = "direction_plus_strength_plus_horizon"
    RELATIVE_FORECAST = "relative_forecast"
    INTRINSIC_FORECAST = "intrinsic_forecast"


@unique
class ForecastHorizonClass(str, Enum):
    INTRABAR = "intrabar"
    SHORT = "short"
    MEDIUM = "medium"
    LONG = "long"


@unique
class BetStructure(str, Enum):
    DIRECTIONAL_LONG = "directional_long"
    DIRECTIONAL_SHORT = "directional_short"
    MEAN_REVERT = "mean_revert"
    BREAKOUT = "breakout"
    CARRY = "carry"


@unique
class ConditioningFamily(str, Enum):
    ENGINE_INTERNAL = "engine_internal"
    SCORING = "scoring"
    HARD_BLOCK = "hard_block"
    PORTFOLIO = "portfolio"


class ConditioningRecord(TimestampedModel):
    family: ConditioningFamily
    code: str = Field(..., min_length=1)
    value: float | None = None
    triggered_no_trade: bool = False

    model_config = ConfigDict(frozen=True, extra="forbid")

    @field_validator("code")
    @classmethod
    def _normalize_code(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("ConditioningRecord.code must not be blank")
        return normalized


class ForecastSignalCandidate(TimestampedModel):
    """Additive enriched signal contract without replacing the canonical decision signal."""

    strategy_id: str = Field(..., min_length=1)
    engine_id: EngineId
    pair: str = Field(..., min_length=1)
    side: Side
    forecast_direction: float = Field(..., ge=-1.0, le=1.0)
    forecast_strength: float = Field(..., ge=0.0, le=20.0)
    forecast_horizon_class: ForecastHorizonClass
    forecast_target_class: ForecastTargetClass
    bet_structure: BetStructure
    confidence_band: float | None = Field(default=None, ge=0.0, le=1.0)
    conditioning_state: tuple[ConditioningRecord, ...]
    expected_cost: float = Field(..., ge=0.0)
    expected_break_even: float = Field(..., ge=0.0)
    expected_ce: float
    expected_gain: float
    invalidation_ref: str | None = None
    reason_codes: tuple[str, ...] = ()
    versions: dict[str, str]

    model_config = ConfigDict(frozen=True, extra="forbid")

    @field_validator("strategy_id")
    @classmethod
    def _normalize_strategy_id(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("strategy_id must not be blank")
        return normalized

    @field_validator("pair")
    @classmethod
    def _normalize_pair(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("pair must not be blank")
        return normalized

    @field_validator("conditioning_state")
    @classmethod
    def _require_conditioning_state(
        cls,
        value: tuple[ConditioningRecord, ...],
    ) -> tuple[ConditioningRecord, ...]:
        if not value:
            raise ValueError("conditioning_state must contain at least one record")
        return value

    @field_validator("invalidation_ref")
    @classmethod
    def _normalize_invalidation_ref(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("invalidation_ref must not be blank")
        return normalized

    @field_validator("reason_codes")
    @classmethod
    def _normalize_reason_codes(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized: list[str] = []
        for code in value:
            stripped = code.strip()
            if not stripped:
                raise ValueError("reason_codes must not contain blank values")
            normalized.append(stripped)
        return tuple(normalized)

    @field_validator("versions")
    @classmethod
    def _normalize_versions(cls, value: Mapping[str, str]) -> dict[str, str]:
        normalized: dict[str, str] = {}
        for key, raw_value in value.items():
            normalized_key = key.strip()
            normalized_value = raw_value.strip()
            if not normalized_key:
                raise ValueError("versions must not contain blank keys")
            if not normalized_value:
                raise ValueError("versions must not contain blank values")
            normalized[normalized_key] = normalized_value
        if not normalized:
            raise ValueError("versions must contain at least one entry")
        return normalized

    @classmethod
    def from_decision_signal(
        cls,
        signal: DecisionSignalCandidate,
        *,
        strategy_id: str,
        forecast_direction: float,
        forecast_strength: float,
        forecast_horizon_class: ForecastHorizonClass,
        forecast_target_class: ForecastTargetClass,
        bet_structure: BetStructure,
        conditioning_state: tuple[ConditioningRecord, ...],
        expected_cost: float,
        expected_break_even: float,
        expected_ce: float,
        expected_gain: float,
        versions: Mapping[str, str],
        confidence_band: float | None = None,
        invalidation_ref: str | None = None,
        reason_codes: tuple[str, ...] = (),
    ) -> "ForecastSignalCandidate":
        return cls(
            timestamp_ms=signal.timestamp_ms,
            strategy_id=strategy_id,
            engine_id=signal.engine_id,
            pair=signal.pair,
            side=signal.side,
            forecast_direction=forecast_direction,
            forecast_strength=forecast_strength,
            forecast_horizon_class=forecast_horizon_class,
            forecast_target_class=forecast_target_class,
            bet_structure=bet_structure,
            confidence_band=confidence_band,
            conditioning_state=conditioning_state,
            expected_cost=expected_cost,
            expected_break_even=expected_break_even,
            expected_ce=expected_ce,
            expected_gain=expected_gain,
            invalidation_ref=invalidation_ref,
            reason_codes=reason_codes,
            versions=dict(versions),
        )


# Module-local alias matching the doctrinal docs; package export remains ForecastSignalCandidate.
SignalCandidate = ForecastSignalCandidate

__all__ = [
    "ForecastTargetClass",
    "ForecastHorizonClass",
    "BetStructure",
    "ConditioningFamily",
    "ConditioningRecord",
    "ForecastSignalCandidate",
]
