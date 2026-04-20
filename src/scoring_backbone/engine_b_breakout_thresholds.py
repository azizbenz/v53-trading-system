"""Allowed upstream signed-threshold resolver for Engine B anti-breakout thresholds."""

from __future__ import annotations

import math
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from calibration_loader import CalibrationLoader
from calibration_loader.loader import CalibrationArtifactValidationError


class EngineBBreakoutThresholdResolverConfig(BaseModel, frozen=True):
    """Signed calibration lookup config for Engine B anti-breakout thresholds."""

    calibration_root: Path | str = "config/calibration"
    calibration_version: str = "v1"
    warning_threshold_id: str = Field(..., min_length=1)
    blocked_threshold_id: str = Field(..., min_length=1)
    warning_hard_cap: float = Field(default=1.0, gt=0.0, le=1.0)
    blocked_hard_cap: float = Field(default=1.0, gt=0.0, le=1.0)


class EngineBBreakoutThresholdResolution(BaseModel):
    """Resolved signed thresholds for the current Engine B anti-breakout seam."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    warning: float = Field(..., ge=0.0, le=1.0)
    blocked: float = Field(..., ge=0.0, le=1.0)
    warning_threshold_id: str = Field(..., min_length=1)
    blocked_threshold_id: str = Field(..., min_length=1)
    calibration_root: str = ""
    calibration_version: str = Field(..., min_length=1)

    def to_engine_b_breakout_threshold_updates(self) -> dict[str, float]:
        """Return additive updates for a caller-owned Engine B breakout payload."""

        return {
            "warning": self.warning,
            "blocked": self.blocked,
        }


def resolve_engine_b_breakout_thresholds(
    config: EngineBBreakoutThresholdResolverConfig,
) -> EngineBBreakoutThresholdResolution:
    """Resolve signed Engine B anti-breakout thresholds through an allowed seam."""

    loader = CalibrationLoader(config.calibration_root)
    collection = loader.load(version=config.calibration_version)
    warning = _resolve_unit_interval_float(
        loader.get_value(collection, config.warning_threshold_id),
        threshold_id=config.warning_threshold_id,
    )
    blocked = _resolve_unit_interval_float(
        loader.get_value(collection, config.blocked_threshold_id),
        threshold_id=config.blocked_threshold_id,
    )
    if warning > config.warning_hard_cap:
        raise CalibrationArtifactValidationError(
            f"{config.warning_threshold_id} value {warning:.6f} exceeds "
            f"Engine B breakout warning hard cap {config.warning_hard_cap:.6f}"
        )
    if blocked > config.blocked_hard_cap:
        raise CalibrationArtifactValidationError(
            f"{config.blocked_threshold_id} value {blocked:.6f} exceeds "
            f"Engine B breakout blocked hard cap {config.blocked_hard_cap:.6f}"
        )
    if warning >= blocked:
        raise CalibrationArtifactValidationError(
            "Engine B breakout warning threshold must be strictly below blocked threshold"
        )
    return EngineBBreakoutThresholdResolution(
        warning=warning,
        blocked=blocked,
        warning_threshold_id=config.warning_threshold_id,
        blocked_threshold_id=config.blocked_threshold_id,
        calibration_root=str(config.calibration_root),
        calibration_version=config.calibration_version,
    )


def build_engine_b_breakout_threshold_updates(
    config: EngineBBreakoutThresholdResolverConfig,
) -> dict[str, float]:
    """Caller-facing update payload for Engine B breakout threshold injection."""

    return resolve_engine_b_breakout_thresholds(
        config
    ).to_engine_b_breakout_threshold_updates()


def _resolve_unit_interval_float(raw_value: object, *, threshold_id: str) -> float:
    if isinstance(raw_value, bool):
        raise CalibrationArtifactValidationError(
            f"{threshold_id} must be numeric, got boolean"
        )
    if not isinstance(raw_value, int | float | str):
        raise CalibrationArtifactValidationError(
            f"{threshold_id} must be numeric, got {raw_value!r}"
        )
    numeric = float(raw_value)
    if not math.isfinite(numeric) or numeric < 0.0 or numeric > 1.0:
        raise CalibrationArtifactValidationError(
            f"{threshold_id} must be a finite float in [0, 1]"
        )
    return numeric


__all__ = [
    "EngineBBreakoutThresholdResolution",
    "EngineBBreakoutThresholdResolverConfig",
    "build_engine_b_breakout_threshold_updates",
    "resolve_engine_b_breakout_thresholds",
]
