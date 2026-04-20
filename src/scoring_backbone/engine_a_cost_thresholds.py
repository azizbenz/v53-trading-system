"""Allowed upstream signed-threshold resolver for Engine A cost inputs."""

from __future__ import annotations

import math
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from calibration_loader import CalibrationLoader
from calibration_loader.loader import CalibrationArtifactValidationError


class EngineACostThresholdResolverConfig(BaseModel, frozen=True):
    """Signed calibration lookup config for Engine A cost thresholds."""

    calibration_root: Path | str = "config/calibration"
    calibration_version: str = "v1"
    delta_safe_threshold_id: str = Field(..., min_length=1)
    ce_min_threshold_id: str = Field(..., min_length=1)
    delta_safe_hard_cap: float = Field(default=0.01, gt=0.0)
    ce_min_hard_cap: float = Field(default=0.01, gt=0.0)


class EngineACostThresholdResolution(BaseModel):
    """Resolved signed thresholds for the current Engine A cost seam."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    delta_safe: float = Field(..., ge=0.0)
    ce_min: float = Field(..., ge=0.0)
    delta_safe_threshold_id: str = Field(..., min_length=1)
    ce_min_threshold_id: str = Field(..., min_length=1)
    calibration_root: str = ""
    calibration_version: str = Field(..., min_length=1)

    def to_engine_a_input_updates(self) -> dict[str, float]:
        """Return additive updates for an Engine A caller-owned payload."""

        return {
            "delta_safe": self.delta_safe,
            "ce_min": self.ce_min,
        }


def resolve_engine_a_cost_thresholds(
    config: EngineACostThresholdResolverConfig,
) -> EngineACostThresholdResolution:
    """Resolve signed Engine A cost thresholds through an allowed upstream seam."""

    loader = CalibrationLoader(config.calibration_root)
    collection = loader.load(version=config.calibration_version)
    delta_safe = _resolve_non_negative_float(
        loader.get_value(collection, config.delta_safe_threshold_id),
        threshold_id=config.delta_safe_threshold_id,
    )
    ce_min = _resolve_non_negative_float(
        loader.get_value(collection, config.ce_min_threshold_id),
        threshold_id=config.ce_min_threshold_id,
    )
    if delta_safe > config.delta_safe_hard_cap:
        raise CalibrationArtifactValidationError(
            f"{config.delta_safe_threshold_id} value {delta_safe:.6f} exceeds "
            f"Engine A delta_safe hard cap {config.delta_safe_hard_cap:.6f}"
        )
    if ce_min > config.ce_min_hard_cap:
        raise CalibrationArtifactValidationError(
            f"{config.ce_min_threshold_id} value {ce_min:.6f} exceeds "
            f"Engine A ce_min hard cap {config.ce_min_hard_cap:.6f}"
        )
    return EngineACostThresholdResolution(
        delta_safe=delta_safe,
        ce_min=ce_min,
        delta_safe_threshold_id=config.delta_safe_threshold_id,
        ce_min_threshold_id=config.ce_min_threshold_id,
        calibration_root=str(config.calibration_root),
        calibration_version=config.calibration_version,
    )


def build_engine_a_cost_threshold_updates(
    config: EngineACostThresholdResolverConfig,
) -> dict[str, float]:
    """Caller-facing update payload for Engine A threshold injection."""

    return resolve_engine_a_cost_thresholds(config).to_engine_a_input_updates()


def _resolve_non_negative_float(raw_value: object, *, threshold_id: str) -> float:
    if isinstance(raw_value, bool):
        raise CalibrationArtifactValidationError(
            f"{threshold_id} must be numeric, got boolean"
        )
    if not isinstance(raw_value, int | float | str):
        raise CalibrationArtifactValidationError(
            f"{threshold_id} must be numeric, got {raw_value!r}"
        )
    numeric = float(raw_value)
    if not math.isfinite(numeric) or numeric < 0.0:
        raise CalibrationArtifactValidationError(
            f"{threshold_id} must be a finite non-negative float"
        )
    return numeric


__all__ = [
    "EngineACostThresholdResolution",
    "EngineACostThresholdResolverConfig",
    "build_engine_a_cost_threshold_updates",
    "resolve_engine_a_cost_thresholds",
]
