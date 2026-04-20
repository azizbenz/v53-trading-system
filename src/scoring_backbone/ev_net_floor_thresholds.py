"""Shared signed-threshold resolver for the canonical EV-net floor seam."""

from __future__ import annotations

import math
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from calibration_loader import CalibrationLoader
from calibration_loader.loader import CalibrationArtifactValidationError


ENGINE_SHARED_EV_NET_FLOOR_THRESHOLD_ID = "THR-E05"


class EvNetFloorThresholdResolverConfig(BaseModel, frozen=True):
    """Signed calibration lookup config for the shared EV-net floor seam."""

    calibration_root: Path | str = "config/calibration"
    calibration_version: str = "v1"
    ev_net_floor_threshold_id: str = Field(
        default=ENGINE_SHARED_EV_NET_FLOOR_THRESHOLD_ID,
        min_length=1,
    )


class EvNetFloorThresholdResolution(BaseModel):
    """Resolved signed threshold for EV-net floor governance."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    min_ev_net: float = Field(..., ge=0.0)
    ev_net_floor_threshold_id: str = Field(..., min_length=1)
    calibration_root: str = ""
    calibration_version: str = Field(..., min_length=1)

    def to_break_even_filter_config_updates(self) -> dict[str, float]:
        """Return additive updates for BreakEvenFilterConfig callers."""

        return {"min_ev_net": self.min_ev_net}


def resolve_ev_net_floor_threshold(
    config: EvNetFloorThresholdResolverConfig,
) -> EvNetFloorThresholdResolution:
    """Resolve the shared EV-net floor through the allowed upstream seam."""

    loader = CalibrationLoader(config.calibration_root)
    collection = loader.load(version=config.calibration_version)
    min_ev_net = _resolve_non_negative_float(
        loader.get_value(collection, config.ev_net_floor_threshold_id),
        threshold_id=config.ev_net_floor_threshold_id,
    )
    return EvNetFloorThresholdResolution(
        min_ev_net=min_ev_net,
        ev_net_floor_threshold_id=config.ev_net_floor_threshold_id,
        calibration_root=str(config.calibration_root),
        calibration_version=config.calibration_version,
    )


def build_ev_net_floor_threshold_updates(
    config: EvNetFloorThresholdResolverConfig,
) -> dict[str, float]:
    """Caller-facing update payload for BreakEvenFilterConfig injection."""

    return resolve_ev_net_floor_threshold(config).to_break_even_filter_config_updates()


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
    "ENGINE_SHARED_EV_NET_FLOOR_THRESHOLD_ID",
    "EvNetFloorThresholdResolution",
    "EvNetFloorThresholdResolverConfig",
    "build_ev_net_floor_threshold_updates",
    "resolve_ev_net_floor_threshold",
]
