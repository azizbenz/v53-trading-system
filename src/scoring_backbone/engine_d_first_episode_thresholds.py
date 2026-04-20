"""Allowed upstream signed-threshold resolver for Engine D first-episode linkage."""

from __future__ import annotations

import math
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from calibration_loader import CalibrationLoader
from calibration_loader.loader import CalibrationArtifactValidationError


_NS_PER_HOUR = 3_600_000_000_000
_NS_PER_MINUTE = 60_000_000_000


class EngineDFirstEpisodeThresholdResolverConfig(BaseModel, frozen=True):
    """Signed calibration lookup config for Engine D first-episode thresholds."""

    calibration_root: Path | str = "config/calibration"
    calibration_version: str = "v1"
    lookback_threshold_id: str = Field(..., min_length=1)
    min_gap_threshold_id: str | None = Field(default=None, min_length=1)
    lookback_hours_hard_cap: float = Field(default=48.0, gt=0.0)
    min_gap_minutes_hard_cap: float = Field(default=120.0, gt=0.0)


class EngineDFirstEpisodeThresholdResolution(BaseModel):
    """Resolved signed threshold for the current Engine D first-episode seam."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    lookback_hours: float = Field(..., gt=0.0)
    lookback_ns: int = Field(..., gt=0)
    lookback_threshold_id: str = Field(..., min_length=1)
    min_gap_minutes: float | None = Field(default=None, gt=0.0)
    min_gap_ns: int | None = Field(default=None, gt=0)
    min_gap_threshold_id: str | None = Field(default=None, min_length=1)
    calibration_root: str = ""
    calibration_version: str = Field(..., min_length=1)

    def to_engine_d_first_episode_updates(self) -> dict[str, int]:
        """Return additive updates for a caller-owned Engine D historical payload."""

        updates = {"lookback_ns": self.lookback_ns}
        if self.min_gap_ns is not None:
            updates["min_gap_ns"] = self.min_gap_ns
        return updates


def resolve_engine_d_first_episode_thresholds(
    config: EngineDFirstEpisodeThresholdResolverConfig,
) -> EngineDFirstEpisodeThresholdResolution:
    """Resolve signed Engine D lookback threshold through an allowed upstream seam."""

    loader = CalibrationLoader(config.calibration_root)
    collection = loader.load(version=config.calibration_version)
    lookback_hours = _resolve_positive_float(
        loader.get_value(collection, config.lookback_threshold_id),
        threshold_id=config.lookback_threshold_id,
    )
    min_gap_minutes = None
    if config.min_gap_threshold_id is not None:
        min_gap_minutes = _resolve_positive_float(
            loader.get_value(collection, config.min_gap_threshold_id),
            threshold_id=config.min_gap_threshold_id,
        )
    if lookback_hours > config.lookback_hours_hard_cap:
        raise CalibrationArtifactValidationError(
            f"{config.lookback_threshold_id} value {lookback_hours:.6f} exceeds "
            f"Engine D lookback hard cap {config.lookback_hours_hard_cap:.6f} hours"
        )
    if min_gap_minutes is not None and min_gap_minutes > config.min_gap_minutes_hard_cap:
        raise CalibrationArtifactValidationError(
            f"{config.min_gap_threshold_id} value {min_gap_minutes:.6f} exceeds "
            f"Engine D min-gap hard cap {config.min_gap_minutes_hard_cap:.6f} minutes"
        )
    return EngineDFirstEpisodeThresholdResolution(
        lookback_hours=lookback_hours,
        lookback_ns=int(lookback_hours * _NS_PER_HOUR),
        lookback_threshold_id=config.lookback_threshold_id,
        min_gap_minutes=min_gap_minutes,
        min_gap_ns=(
            None if min_gap_minutes is None else int(min_gap_minutes * _NS_PER_MINUTE)
        ),
        min_gap_threshold_id=config.min_gap_threshold_id,
        calibration_root=str(config.calibration_root),
        calibration_version=config.calibration_version,
    )


def build_engine_d_first_episode_threshold_updates(
    config: EngineDFirstEpisodeThresholdResolverConfig,
) -> dict[str, int]:
    """Caller-facing update payload for Engine D first-episode threshold injection."""

    return resolve_engine_d_first_episode_thresholds(
        config
    ).to_engine_d_first_episode_updates()


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


__all__ = [
    "EngineDFirstEpisodeThresholdResolution",
    "EngineDFirstEpisodeThresholdResolverConfig",
    "build_engine_d_first_episode_threshold_updates",
    "resolve_engine_d_first_episode_thresholds",
]
