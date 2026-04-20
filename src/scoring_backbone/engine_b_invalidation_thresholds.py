"""Allowed upstream signed-threshold resolver for Engine B invalidation thresholds."""

from __future__ import annotations

import math
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from calibration_loader import CalibrationLoader
from calibration_loader.loader import CalibrationArtifactValidationError


class EngineBInvalidationThresholdResolverConfig(BaseModel, frozen=True):
    """Signed calibration lookup config for Engine B invalidation thresholds."""

    calibration_root: Path | str = "config/calibration"
    calibration_version: str = "v1"
    max_holding_hours_threshold_id: str = Field(..., min_length=1)
    fallback_stop_ratio_threshold_id: str = Field(..., min_length=1)
    stop_multiplier_threshold_id: str = Field(..., min_length=1)
    max_holding_hours_hard_cap: float = Field(default=168.0, gt=0.0)
    fallback_stop_ratio_hard_cap: float = Field(default=1.0, gt=0.0, le=1.0)
    stop_multiplier_hard_cap: float = Field(default=10.0, gt=0.0)


class EngineBInvalidationThresholdResolution(BaseModel):
    """Resolved signed thresholds for the current Engine B invalidation seam."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    max_holding_hours: float = Field(..., gt=0.0)
    fallback_stop_ratio: float = Field(..., gt=0.0, lt=1.0)
    stop_multiplier: float = Field(..., gt=0.0)
    max_holding_hours_threshold_id: str = Field(..., min_length=1)
    fallback_stop_ratio_threshold_id: str = Field(..., min_length=1)
    stop_multiplier_threshold_id: str = Field(..., min_length=1)
    calibration_root: str = ""
    calibration_version: str = Field(..., min_length=1)

    def to_engine_b_invalidation_threshold_updates(self) -> dict[str, float]:
        """Return additive updates for a caller-owned Engine B invalidation payload."""

        return {
            "max_holding_hours": self.max_holding_hours,
            "fallback_stop_ratio": self.fallback_stop_ratio,
            "stop_multiplier": self.stop_multiplier,
        }


def resolve_engine_b_invalidation_thresholds(
    config: EngineBInvalidationThresholdResolverConfig,
) -> EngineBInvalidationThresholdResolution:
    """Resolve signed Engine B invalidation thresholds through an allowed seam."""

    loader = CalibrationLoader(config.calibration_root)
    collection = loader.load(version=config.calibration_version)
    max_holding_hours = _resolve_positive_float(
        loader.get_value(collection, config.max_holding_hours_threshold_id),
        threshold_id=config.max_holding_hours_threshold_id,
    )
    fallback_stop_ratio = _resolve_open_unit_interval_float(
        loader.get_value(collection, config.fallback_stop_ratio_threshold_id),
        threshold_id=config.fallback_stop_ratio_threshold_id,
    )
    stop_multiplier = _resolve_positive_float(
        loader.get_value(collection, config.stop_multiplier_threshold_id),
        threshold_id=config.stop_multiplier_threshold_id,
    )
    if max_holding_hours > config.max_holding_hours_hard_cap:
        raise CalibrationArtifactValidationError(
            f"{config.max_holding_hours_threshold_id} value {max_holding_hours:.6f} exceeds "
            f"Engine B max_holding_hours hard cap {config.max_holding_hours_hard_cap:.6f}"
        )
    if fallback_stop_ratio >= config.fallback_stop_ratio_hard_cap:
        raise CalibrationArtifactValidationError(
            f"{config.fallback_stop_ratio_threshold_id} value {fallback_stop_ratio:.6f} exceeds "
            f"Engine B fallback_stop_ratio hard cap {config.fallback_stop_ratio_hard_cap:.6f}"
        )
    if stop_multiplier > config.stop_multiplier_hard_cap:
        raise CalibrationArtifactValidationError(
            f"{config.stop_multiplier_threshold_id} value {stop_multiplier:.6f} exceeds "
            f"Engine B stop_multiplier hard cap {config.stop_multiplier_hard_cap:.6f}"
        )
    return EngineBInvalidationThresholdResolution(
        max_holding_hours=max_holding_hours,
        fallback_stop_ratio=fallback_stop_ratio,
        stop_multiplier=stop_multiplier,
        max_holding_hours_threshold_id=config.max_holding_hours_threshold_id,
        fallback_stop_ratio_threshold_id=config.fallback_stop_ratio_threshold_id,
        stop_multiplier_threshold_id=config.stop_multiplier_threshold_id,
        calibration_root=str(config.calibration_root),
        calibration_version=config.calibration_version,
    )


def build_engine_b_invalidation_threshold_updates(
    config: EngineBInvalidationThresholdResolverConfig,
) -> dict[str, float]:
    """Caller-facing update payload for Engine B invalidation threshold injection."""

    return resolve_engine_b_invalidation_thresholds(
        config
    ).to_engine_b_invalidation_threshold_updates()


def _resolve_positive_float(raw_value: object, *, threshold_id: str) -> float:
    if isinstance(raw_value, bool):
        raise CalibrationArtifactValidationError(
            f"{threshold_id} must be numeric, got boolean"
        )
    if not isinstance(raw_value, int | float | str):
        raise CalibrationArtifactValidationError(
            f"{threshold_id} must be numeric, got {raw_value!r}"
        )
    numeric = float(raw_value)
    if not math.isfinite(numeric) or numeric <= 0.0:
        raise CalibrationArtifactValidationError(
            f"{threshold_id} must be a finite positive float"
        )
    return numeric


def _resolve_open_unit_interval_float(raw_value: object, *, threshold_id: str) -> float:
    if isinstance(raw_value, bool):
        raise CalibrationArtifactValidationError(
            f"{threshold_id} must be numeric, got boolean"
        )
    if not isinstance(raw_value, int | float | str):
        raise CalibrationArtifactValidationError(
            f"{threshold_id} must be numeric, got {raw_value!r}"
        )
    numeric = float(raw_value)
    if not math.isfinite(numeric) or numeric <= 0.0 or numeric >= 1.0:
        raise CalibrationArtifactValidationError(
            f"{threshold_id} must be a finite float in (0, 1)"
        )
    return numeric


__all__ = [
    "EngineBInvalidationThresholdResolution",
    "EngineBInvalidationThresholdResolverConfig",
    "build_engine_b_invalidation_threshold_updates",
    "resolve_engine_b_invalidation_thresholds",
]
