"""Allowed upstream signed-threshold resolver for Engine B excess thresholds."""

from __future__ import annotations

import math
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from calibration_loader import CalibrationLoader
from calibration_loader.loader import CalibrationArtifactValidationError


class EngineBExcessThresholdResolverConfig(BaseModel, frozen=True):
    """Signed calibration lookup config for Engine B excess thresholds."""

    calibration_root: Path | str = "config/calibration"
    calibration_version: str = "v1"
    z_marginal_threshold_id: str = Field(..., min_length=1)
    z_star_threshold_id: str = Field(..., min_length=1)
    z_max_threshold_id: str = Field(..., min_length=1)
    vpin_toxic_threshold_id: str = Field(..., min_length=1)
    max_intra_family_correlation_threshold_id: str = Field(..., min_length=1)
    z_marginal_hard_cap: float = Field(default=10.0, gt=0.0)
    z_star_hard_cap: float = Field(default=10.0, gt=0.0)
    z_max_hard_cap: float = Field(default=20.0, gt=0.0)
    vpin_toxic_hard_cap: float = Field(default=1.0, gt=0.0, le=1.0)
    max_intra_family_correlation_hard_cap: float = Field(default=1.0, gt=0.0, le=1.0)


class EngineBExcessThresholdResolution(BaseModel):
    """Resolved signed thresholds for the current Engine B excess seam."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    z_marginal: float = Field(..., gt=0.0)
    z_star: float = Field(..., gt=0.0)
    z_max: float = Field(..., gt=0.0)
    vpin_toxic: float = Field(..., ge=0.0, le=1.0)
    max_intra_family_correlation: float = Field(..., ge=0.0, le=1.0)
    z_marginal_threshold_id: str = Field(..., min_length=1)
    z_star_threshold_id: str = Field(..., min_length=1)
    z_max_threshold_id: str = Field(..., min_length=1)
    vpin_toxic_threshold_id: str = Field(..., min_length=1)
    max_intra_family_correlation_threshold_id: str = Field(..., min_length=1)
    calibration_root: str = ""
    calibration_version: str = Field(..., min_length=1)

    def to_engine_b_excess_threshold_updates(self) -> dict[str, float]:
        """Return additive updates for a caller-owned Engine B excess payload."""

        return {
            "z_marginal": self.z_marginal,
            "z_star": self.z_star,
            "z_max": self.z_max,
            "vpin_toxic": self.vpin_toxic,
            "max_intra_family_correlation": self.max_intra_family_correlation,
        }


def resolve_engine_b_excess_thresholds(
    config: EngineBExcessThresholdResolverConfig,
) -> EngineBExcessThresholdResolution:
    """Resolve signed Engine B excess thresholds through an allowed seam."""

    loader = CalibrationLoader(config.calibration_root)
    collection = loader.load(version=config.calibration_version)
    z_marginal = _resolve_positive_float(
        loader.get_value(collection, config.z_marginal_threshold_id),
        threshold_id=config.z_marginal_threshold_id,
    )
    z_star = _resolve_positive_float(
        loader.get_value(collection, config.z_star_threshold_id),
        threshold_id=config.z_star_threshold_id,
    )
    z_max = _resolve_positive_float(
        loader.get_value(collection, config.z_max_threshold_id),
        threshold_id=config.z_max_threshold_id,
    )
    vpin_toxic = _resolve_unit_interval_float(
        loader.get_value(collection, config.vpin_toxic_threshold_id),
        threshold_id=config.vpin_toxic_threshold_id,
    )
    max_intra_family_correlation = _resolve_unit_interval_float(
        loader.get_value(collection, config.max_intra_family_correlation_threshold_id),
        threshold_id=config.max_intra_family_correlation_threshold_id,
    )
    if z_marginal > config.z_marginal_hard_cap:
        raise CalibrationArtifactValidationError(
            f"{config.z_marginal_threshold_id} value {z_marginal:.6f} exceeds "
            f"Engine B z_marginal hard cap {config.z_marginal_hard_cap:.6f}"
        )
    if z_star > config.z_star_hard_cap:
        raise CalibrationArtifactValidationError(
            f"{config.z_star_threshold_id} value {z_star:.6f} exceeds "
            f"Engine B z_star hard cap {config.z_star_hard_cap:.6f}"
        )
    if z_max > config.z_max_hard_cap:
        raise CalibrationArtifactValidationError(
            f"{config.z_max_threshold_id} value {z_max:.6f} exceeds "
            f"Engine B z_max hard cap {config.z_max_hard_cap:.6f}"
        )
    if vpin_toxic > config.vpin_toxic_hard_cap:
        raise CalibrationArtifactValidationError(
            f"{config.vpin_toxic_threshold_id} value {vpin_toxic:.6f} exceeds "
            f"Engine B vpin_toxic hard cap {config.vpin_toxic_hard_cap:.6f}"
        )
    if max_intra_family_correlation > config.max_intra_family_correlation_hard_cap:
        raise CalibrationArtifactValidationError(
            f"{config.max_intra_family_correlation_threshold_id} value "
            f"{max_intra_family_correlation:.6f} exceeds Engine B max_intra_family_correlation "
            f"hard cap {config.max_intra_family_correlation_hard_cap:.6f}"
        )
    if not (z_marginal < z_star < z_max):
        raise CalibrationArtifactValidationError(
            "Engine B excess thresholds must satisfy z_marginal < z_star < z_max"
        )
    return EngineBExcessThresholdResolution(
        z_marginal=z_marginal,
        z_star=z_star,
        z_max=z_max,
        vpin_toxic=vpin_toxic,
        max_intra_family_correlation=max_intra_family_correlation,
        z_marginal_threshold_id=config.z_marginal_threshold_id,
        z_star_threshold_id=config.z_star_threshold_id,
        z_max_threshold_id=config.z_max_threshold_id,
        vpin_toxic_threshold_id=config.vpin_toxic_threshold_id,
        max_intra_family_correlation_threshold_id=config.max_intra_family_correlation_threshold_id,
        calibration_root=str(config.calibration_root),
        calibration_version=config.calibration_version,
    )


def build_engine_b_excess_threshold_updates(
    config: EngineBExcessThresholdResolverConfig,
) -> dict[str, float]:
    """Caller-facing update payload for Engine B excess threshold injection."""

    return resolve_engine_b_excess_thresholds(config).to_engine_b_excess_threshold_updates()


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
    "EngineBExcessThresholdResolution",
    "EngineBExcessThresholdResolverConfig",
    "build_engine_b_excess_threshold_updates",
    "resolve_engine_b_excess_thresholds",
]
