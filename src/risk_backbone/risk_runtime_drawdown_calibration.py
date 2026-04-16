"""Opt-in calibration seam for RiskLimits drawdown alert thresholds (THR-W01/THR-W02).

These are *alert* thresholds (observe / warn), not hard breakers.
Hard breakers are in daily_pnl_breaker.py (THR-R01).

Calibration may tighten these values but must not relax them beyond the hard caps:
  - drawdown_warning: hard cap 5% (warning fires at or below 5% DD)
  - drawdown_observe: hard cap 10% (observe fires at or below 10% DD)
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from calibration_loader import CalibrationLoader
from calibration_loader.loader import (
    CalibrationArtifactValidationError,
    CalibrationLoaderError,
    CalibrationThresholdNotFoundError,
)


class RiskDrawdownCalibrationConfig(BaseModel, frozen=True):
    """Opt-in calibration seam for THR-W01 (warning) and THR-W02 (observe)."""

    calibration_root: Path | str = "config/calibration"
    calibration_version: str = "v1"
    warning_threshold_id: str = "THR-W01"
    observe_threshold_id: str = "THR-W02"
    hard_cap_warning_pct: float = Field(default=0.05, gt=0.0)
    hard_cap_observe_pct: float = Field(default=0.10, gt=0.0)


class RiskDrawdownThresholds(BaseModel, frozen=True):
    """Resolved drawdown alert thresholds for injection into RiskLimits."""

    drawdown_warning_threshold_pct: float = Field(..., gt=0.0)
    drawdown_observe_threshold_pct: float = Field(..., gt=0.0)

    @classmethod
    def from_documented_defaults(cls) -> "RiskDrawdownThresholds":
        """Return the documented defaults without loading from calibration."""
        return cls(
            drawdown_warning_threshold_pct=0.02,
            drawdown_observe_threshold_pct=0.04,
        )


def resolve_risk_drawdown_thresholds(
    config: RiskDrawdownCalibrationConfig | None = None,
) -> RiskDrawdownThresholds:
    """Resolve THR-W01 and THR-W02 from the shared calibration catalog.

    Falls back gracefully to documented defaults when the calibration
    artifact does not contain these threshold IDs (e.g. during shadow
    ramp-up before the first calibration cycle).
    """
    calibration = config or RiskDrawdownCalibrationConfig()
    loader = CalibrationLoader(calibration.calibration_root)
    try:
        collection = loader.load(version=calibration.calibration_version)
    except CalibrationLoaderError:
        return RiskDrawdownThresholds.from_documented_defaults()

    warning_value = _resolve_optional_threshold(
        loader=loader,
        collection=collection,
        threshold_id=calibration.warning_threshold_id,
        fallback=0.02,
    )
    observe_value = _resolve_optional_threshold(
        loader=loader,
        collection=collection,
        threshold_id=calibration.observe_threshold_id,
        fallback=0.04,
    )

    if warning_value > calibration.hard_cap_warning_pct:
        raise CalibrationArtifactValidationError(
            f"{calibration.warning_threshold_id} value {warning_value:.4f} exceeds "
            f"hard cap {calibration.hard_cap_warning_pct:.4f}; "
            "calibration may tighten THR-W01 but must not relax it beyond 5%"
        )
    if observe_value > calibration.hard_cap_observe_pct:
        raise CalibrationArtifactValidationError(
            f"{calibration.observe_threshold_id} value {observe_value:.4f} exceeds "
            f"hard cap {calibration.hard_cap_observe_pct:.4f}; "
            "calibration may tighten THR-W02 but must not relax it beyond 10%"
        )
    if warning_value >= observe_value:
        raise CalibrationArtifactValidationError(
            f"THR-W01 ({warning_value:.4f}) must be strictly less than "
            f"THR-W02 ({observe_value:.4f})"
        )

    return RiskDrawdownThresholds(
        drawdown_warning_threshold_pct=warning_value,
        drawdown_observe_threshold_pct=observe_value,
    )


def _resolve_optional_threshold(
    *,
    loader: CalibrationLoader,
    collection: object,
    threshold_id: str,
    fallback: float,
) -> float:
    """Return the threshold value from the catalog, or the fallback if absent."""
    try:
        raw = loader.get_value(collection, threshold_id)
    except CalibrationThresholdNotFoundError:
        return fallback
    return _resolve_positive_float(raw, threshold_id=threshold_id)


def _resolve_positive_float(raw_value: object, *, threshold_id: str) -> float:
    if isinstance(raw_value, bool):
        raise CalibrationArtifactValidationError(
            f"{threshold_id} must be numeric, got boolean"
        )
    try:
        value = float(raw_value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise CalibrationArtifactValidationError(
            f"{threshold_id} must be numeric, got {raw_value!r}"
        ) from exc
    import math
    if not math.isfinite(value) or value <= 0.0:
        raise CalibrationArtifactValidationError(
            f"{threshold_id} must be a finite positive float"
        )
    return value


__all__ = [
    "RiskDrawdownCalibrationConfig",
    "RiskDrawdownThresholds",
    "resolve_risk_drawdown_thresholds",
]
