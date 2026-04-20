"""Allowed upstream signed-threshold resolver for Engine C continuation inputs."""

from __future__ import annotations

import math
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from calibration_loader import CalibrationLoader
from calibration_loader.loader import CalibrationArtifactValidationError


class EngineCContinuationThresholdResolverConfig(BaseModel, frozen=True):
    """Signed calibration lookup config for Engine C continuation thresholds."""

    calibration_root: Path | str = "config/calibration"
    calibration_version: str = "v1"
    ofi_min_threshold_id: str = Field(..., min_length=1)
    queue_min_threshold_id: str = Field(..., min_length=1)
    vpin_max_threshold_id: str = Field(..., min_length=1)
    kyle_lambda_max_threshold_id: str | None = Field(default=None, min_length=1)
    # OFI scale is not frozen doctrinally yet; keep a generous sanity cap until the
    # upstream canonical scale is explicitly locked.
    ofi_min_hard_cap: float = Field(default=1_000_000.0, gt=0.0)
    queue_min_hard_cap: float = Field(default=1.0, gt=0.0, le=1.0)
    vpin_max_hard_cap: float = Field(default=0.5, gt=0.0, le=1.0)
    # Kyle lambda scale is market- and estimator-dependent; keep a generous sanity
    # cap until doctrine freezes a canonical threshold family for this seam.
    kyle_lambda_max_hard_cap: float = Field(default=1_000_000.0, gt=0.0)


class EngineCContinuationThresholdResolution(BaseModel):
    """Resolved signed thresholds for the current Engine C continuation seam."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    ofi_min: float = Field(..., ge=0.0)
    queue_min: float = Field(..., ge=0.0, le=1.0)
    vpin_max: float = Field(..., ge=0.0, le=1.0)
    kyle_lambda_max: float | None = Field(default=None, ge=0.0)
    ofi_min_threshold_id: str = Field(..., min_length=1)
    queue_min_threshold_id: str = Field(..., min_length=1)
    vpin_max_threshold_id: str = Field(..., min_length=1)
    kyle_lambda_max_threshold_id: str | None = Field(default=None, min_length=1)
    calibration_root: str = ""
    calibration_version: str = Field(..., min_length=1)

    def to_engine_c_input_updates(self) -> dict[str, float]:
        """Return additive updates for a caller-owned Engine C payload."""

        updates: dict[str, float] = {
            "continuation_ofi_min": self.ofi_min,
            "continuation_queue_min": self.queue_min,
            "continuation_vpin_max": self.vpin_max,
        }
        if self.kyle_lambda_max is not None:
            updates["continuation_kyle_lambda_max"] = self.kyle_lambda_max
        return updates


def resolve_engine_c_continuation_thresholds(
    config: EngineCContinuationThresholdResolverConfig,
) -> EngineCContinuationThresholdResolution:
    """Resolve signed Engine C continuation thresholds through an allowed seam."""

    loader = CalibrationLoader(config.calibration_root)
    collection = loader.load(version=config.calibration_version)
    ofi_min = _resolve_non_negative_float(
        loader.get_value(collection, config.ofi_min_threshold_id),
        threshold_id=config.ofi_min_threshold_id,
    )
    queue_min = _resolve_unit_interval_float(
        loader.get_value(collection, config.queue_min_threshold_id),
        threshold_id=config.queue_min_threshold_id,
    )
    vpin_max = _resolve_unit_interval_float(
        loader.get_value(collection, config.vpin_max_threshold_id),
        threshold_id=config.vpin_max_threshold_id,
    )
    kyle_lambda_max = None
    if config.kyle_lambda_max_threshold_id is not None:
        kyle_lambda_max = _resolve_non_negative_float(
            loader.get_value(collection, config.kyle_lambda_max_threshold_id),
            threshold_id=config.kyle_lambda_max_threshold_id,
        )
    if ofi_min > config.ofi_min_hard_cap:
        raise CalibrationArtifactValidationError(
            f"{config.ofi_min_threshold_id} value {ofi_min:.6f} exceeds "
            f"Engine C ofi_min hard cap {config.ofi_min_hard_cap:.6f}"
        )
    if queue_min > config.queue_min_hard_cap:
        raise CalibrationArtifactValidationError(
            f"{config.queue_min_threshold_id} value {queue_min:.6f} exceeds "
            f"Engine C queue_min hard cap {config.queue_min_hard_cap:.6f}"
        )
    if vpin_max > config.vpin_max_hard_cap:
        raise CalibrationArtifactValidationError(
            f"{config.vpin_max_threshold_id} value {vpin_max:.6f} exceeds "
            f"Engine C vpin_max hard cap {config.vpin_max_hard_cap:.6f}"
        )
    if (
        kyle_lambda_max is not None
        and kyle_lambda_max > config.kyle_lambda_max_hard_cap
    ):
        raise CalibrationArtifactValidationError(
            f"{config.kyle_lambda_max_threshold_id} value {kyle_lambda_max:.6f} exceeds "
            f"Engine C kyle_lambda_max hard cap {config.kyle_lambda_max_hard_cap:.6f}"
        )
    return EngineCContinuationThresholdResolution(
        ofi_min=ofi_min,
        queue_min=queue_min,
        vpin_max=vpin_max,
        kyle_lambda_max=kyle_lambda_max,
        ofi_min_threshold_id=config.ofi_min_threshold_id,
        queue_min_threshold_id=config.queue_min_threshold_id,
        vpin_max_threshold_id=config.vpin_max_threshold_id,
        kyle_lambda_max_threshold_id=config.kyle_lambda_max_threshold_id,
        calibration_root=str(config.calibration_root),
        calibration_version=config.calibration_version,
    )


def build_engine_c_continuation_threshold_updates(
    config: EngineCContinuationThresholdResolverConfig,
) -> dict[str, float]:
    """Caller-facing update payload for Engine C continuation threshold injection."""

    return resolve_engine_c_continuation_thresholds(config).to_engine_c_input_updates()


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
    "EngineCContinuationThresholdResolution",
    "EngineCContinuationThresholdResolverConfig",
    "build_engine_c_continuation_threshold_updates",
    "resolve_engine_c_continuation_thresholds",
]
