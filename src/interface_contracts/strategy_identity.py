"""
V5.3 - STRATEGY_IDENTITY
Canonical typed strategy tuple for governed update work.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .domain_types import EngineId
from .forecast_contracts import BetStructure, ForecastSignalCandidate, ForecastTargetClass


class StrategyIdentity(BaseModel):
    """Typed strategy identity tuple for promotion, refusal, and PnL aggregation."""

    engine_id: EngineId
    pair: str = Field(..., min_length=1)
    regime_bucket: str = Field(..., min_length=1)
    forecast_target_class: ForecastTargetClass
    bet_structure: BetStructure
    calibration_version: str = Field(..., min_length=1)

    model_config = ConfigDict(frozen=True, extra="forbid")

    @field_validator("pair")
    @classmethod
    def _normalize_pair(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("pair must not be blank")
        return normalized

    @field_validator("regime_bucket")
    @classmethod
    def _normalize_regime_bucket(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not normalized:
            raise ValueError("regime_bucket must not be blank")
        return normalized

    @field_validator("calibration_version")
    @classmethod
    def _normalize_calibration_version(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("calibration_version must not be blank")
        return normalized

    @property
    def canonical_key(self) -> str:
        return ":".join(
            (
                self.engine_id.value,
                self.pair,
                self.regime_bucket,
                self.forecast_target_class.value,
                self.bet_structure.value,
                self.calibration_version,
            )
        )

    @classmethod
    def from_forecast_signal(
        cls,
        signal: ForecastSignalCandidate,
        *,
        regime_bucket: str,
        calibration_version: str,
    ) -> "StrategyIdentity":
        return cls(
            engine_id=signal.engine_id,
            pair=signal.pair,
            regime_bucket=regime_bucket,
            forecast_target_class=signal.forecast_target_class,
            bet_structure=signal.bet_structure,
            calibration_version=calibration_version,
        )


__all__ = ["StrategyIdentity"]
