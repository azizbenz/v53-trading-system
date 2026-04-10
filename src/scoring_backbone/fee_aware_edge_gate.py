"""Fee-aware edge gate resolved from shared calibration artifacts."""

from __future__ import annotations

import math
from pathlib import Path

from pydantic import BaseModel, Field

from calibration_loader.loader import CalibrationArtifactValidationError, CalibrationLoader


class FeeAwareEdgeGateConfig(BaseModel, frozen=True):
    """Shared-core lookup config for the future fee-aware scoring gate."""

    calibration_root: Path | str = "config/calibration"
    calibration_version: str = "v1"
    edge_multiplier_threshold_id: str = "THR-E01"
    min_absolute_edge_threshold_id: str = "THR-E02"


class FeeAwareEdgeThresholds(BaseModel, frozen=True):
    """Resolved runtime thresholds for fee-aware minimum-edge gating."""

    edge_multiplier: float = Field(..., gt=0.0)
    min_absolute_edge_bps: float = Field(..., ge=0.0)


class FeeAwareEdgeDecision(BaseModel, frozen=True):
    """Deterministic outcome of fee-aware edge validation."""

    allowed: bool
    reason_code: str = ""
    expected_edge_bps: float = 0.0
    expected_cost_fraction: float = 0.0
    expected_cost_bps: float = 0.0
    edge_multiplier: float = 0.0
    min_absolute_edge_bps: float = 0.0
    threshold_bps: float = 0.0
    detail: str = ""


def resolve_fee_aware_edge_thresholds(
    config: FeeAwareEdgeGateConfig | None = None,
) -> FeeAwareEdgeThresholds:
    calibration = config or FeeAwareEdgeGateConfig()
    loader = CalibrationLoader(calibration.calibration_root)
    collection = loader.load(version=calibration.calibration_version)
    edge_multiplier = _resolve_numeric_threshold(
        loader,
        collection,
        calibration.edge_multiplier_threshold_id,
    )
    min_absolute_edge_bps = _resolve_numeric_threshold(
        loader,
        collection,
        calibration.min_absolute_edge_threshold_id,
    )
    if edge_multiplier <= 0.0:
        raise CalibrationArtifactValidationError(
            f"Calibration threshold {calibration.edge_multiplier_threshold_id!r} must be > 0"
        )
    if min_absolute_edge_bps < 0.0:
        raise CalibrationArtifactValidationError(
            f"Calibration threshold {calibration.min_absolute_edge_threshold_id!r} must be >= 0"
        )
    return FeeAwareEdgeThresholds(
        edge_multiplier=edge_multiplier,
        min_absolute_edge_bps=min_absolute_edge_bps,
    )


def evaluate_fee_aware_edge(
    *,
    expected_edge_bps: float,
    expected_cost: float,
    config: FeeAwareEdgeGateConfig | None = None,
) -> FeeAwareEdgeDecision:
    """Check whether expected edge clears calibrated fee-aware minima.

    The repo stores `expected_cost` as a fractional return, so this helper converts it
    explicitly to bps before comparing it against the calibrated EDGE thresholds.
    """

    if not math.isfinite(expected_edge_bps):
        raise ValueError("expected_edge_bps must be finite")
    if not math.isfinite(expected_cost) or expected_cost < 0.0:
        raise ValueError("expected_cost must be finite and >= 0")

    thresholds = resolve_fee_aware_edge_thresholds(config)
    expected_cost_bps = expected_cost * 10_000.0
    threshold_bps = max(
        thresholds.edge_multiplier * expected_cost_bps,
        thresholds.min_absolute_edge_bps,
    )
    allowed = expected_edge_bps >= threshold_bps
    detail = (
        f"edge={expected_edge_bps:.2f}bps vs threshold={threshold_bps:.2f}bps "
        f"(cost={expected_cost_bps:.2f}bps, multiplier={thresholds.edge_multiplier:.4f}, "
        f"absolute_floor={thresholds.min_absolute_edge_bps:.2f}bps)"
    )
    return FeeAwareEdgeDecision(
        allowed=allowed,
        reason_code="" if allowed else "EDGE_INSUFFICIENT_VS_FEES",
        expected_edge_bps=expected_edge_bps,
        expected_cost_fraction=expected_cost,
        expected_cost_bps=round(expected_cost_bps, 6),
        edge_multiplier=thresholds.edge_multiplier,
        min_absolute_edge_bps=thresholds.min_absolute_edge_bps,
        threshold_bps=round(threshold_bps, 6),
        detail=detail,
    )


def _resolve_numeric_threshold(
    loader: CalibrationLoader,
    collection,
    threshold_id: str,
) -> float:
    value = loader.get_value(collection, threshold_id)
    if isinstance(value, bool) or not isinstance(value, int | float | str):
        raise CalibrationArtifactValidationError(
            f"Calibration threshold {threshold_id!r} must be numeric"
        )
    numeric = float(value)
    if not math.isfinite(numeric):
        raise CalibrationArtifactValidationError(
            f"Calibration threshold {threshold_id!r} must be finite"
        )
    return numeric


__all__ = [
    "FeeAwareEdgeDecision",
    "FeeAwareEdgeGateConfig",
    "FeeAwareEdgeThresholds",
    "evaluate_fee_aware_edge",
    "resolve_fee_aware_edge_thresholds",
]
