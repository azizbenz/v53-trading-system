"""Local IA Lab EDGE calibration from governed replay DTR evidence."""

from __future__ import annotations

from datetime import datetime, timezone
import math
from pathlib import Path
from typing import Iterable

from pydantic import BaseModel, Field
import yaml

from calibration_methods import (
    StationaryBootstrapConfig,
    apply_human_minimum_floor,
    stationary_bootstrap_confidence_interval,
)
from interface_contracts.atomic_io import atomic_write_text
from calibration_loader import (
    CalibrationArtifact,
    CalibrationManualSignature,
    CalibrationThresholdEntry,
)
from meta_minimal.dtr_core.decision_state_encoder import DecisionState
from meta_minimal.dtr_core.dtr_record_builder import DTRRecord


class EdgeGateCalibrationError(ValueError):
    """Base error for Local IA Lab EDGE calibration failures."""


class EdgeGateCalibrationInsufficientDataError(EdgeGateCalibrationError):
    """Raised when replay evidence is too weak to publish EDGE thresholds."""


class EdgeGateCalibrationValidationError(EdgeGateCalibrationError):
    """Raised when replay evidence is contradictory or mathematically unusable."""


class EdgeGateCalibrationConfig(BaseModel, frozen=True):
    """Bounded calibration config for THR-E01 / THR-E02."""

    produced_by: str = Field(default="local_ia_lab", min_length=1)
    artifact_id: str = Field(default="edge_gate_thresholds", min_length=1)
    calibration_version: str = Field(default="v1", min_length=1)
    calibration_artifact_path: str = Field(
        default="config/calibration/v1/edge_gate.yml",
        min_length=1,
    )
    source_module: str = Field(
        default="src/scoring_backbone/fee_aware_edge_gate.py",
        min_length=1,
    )
    edge_multiplier_threshold_id: str = Field(default="THR-E01", min_length=1)
    min_absolute_edge_threshold_id: str = Field(default="THR-E02", min_length=1)
    positive_edge_coverage_target: float = Field(default=0.70, gt=0.0, lt=1.0)
    human_multiplier_floor: float = Field(default=2.0, gt=0.0)
    human_absolute_floor_bps: float = Field(default=15.0, ge=0.0)
    absolute_edge_margin_bps: float = Field(default=5.0, ge=0.0)
    min_positive_trades: int = Field(default=200, ge=1)
    min_cost_observations: int = Field(default=500, ge=1)
    bootstrap_samples: int = Field(default=2_000, ge=100)
    confidence_level: float = Field(default=0.95, gt=0.50, lt=1.0)
    max_relative_ic_width: float = Field(default=0.50, gt=0.0)
    rng_seed: int = 53


class EdgeGateThresholdCalibration(BaseModel, frozen=True):
    """Single calibrated EDGE threshold with conservative publication fields."""

    threshold_id: str = Field(..., min_length=1)
    unit: str = Field(..., min_length=1)
    method_version: str = "stationary_block_bootstrap_v1"
    point_estimate: float
    ic95_lower: float
    ic95_upper: float
    published_value: float
    observation_count: int = Field(..., ge=0)
    bootstrap_block_length: int = Field(..., ge=1)
    hard_cap_human: float = Field(..., ge=0.0)
    hard_cap_satisfied: bool
    hard_cap_binding: bool
    description: str = ""
    notes: tuple[str, ...] = ()


class EdgeGateCalibrationReport(BaseModel, frozen=True):
    """Audit-ready Local IA Lab report for THR-E01 / THR-E02."""

    produced_by: str = Field(..., min_length=1)
    generated_at: datetime
    total_record_count: int = Field(..., ge=0)
    executed_record_count: int = Field(..., ge=0)
    positive_trade_count: int = Field(..., ge=0)
    cost_observation_count: int = Field(..., ge=0)
    pair_scope: tuple[str, ...] = ()
    engine_scope: tuple[str, ...] = ()
    runtime_modes: tuple[str, ...] = ()
    cost_reference_policy: str = Field(..., min_length=1)
    positive_trade_definition: str = Field(..., min_length=1)
    thresholds: tuple[EdgeGateThresholdCalibration, ...]
    notes: tuple[str, ...] = ()

    def get_threshold(self, threshold_id: str) -> EdgeGateThresholdCalibration:
        for threshold in self.thresholds:
            if threshold.threshold_id == threshold_id:
                return threshold
        raise KeyError(f"Unknown threshold_id {threshold_id!r}")


def calibrate_edge_gate_thresholds(
    records: tuple[DTRRecord, ...],
    *,
    config: EdgeGateCalibrationConfig | None = None,
    generated_at: datetime | None = None,
) -> EdgeGateCalibrationReport:
    """Calibrate THR-E01 / THR-E02 from governed replay DTR evidence.

    The Local IA Lab path remains conservative:
    - only executed replay records are considered
    - THR-E01 uses realized positive net returns divided by ex-ante expected cost
    - THR-E02 uses ex-ante expected cost only, converted explicitly to bps
    - publication always uses the conservative upper CI bound, never the point estimate
    """

    calibration = config or EdgeGateCalibrationConfig()
    executed = tuple(
        record for record in records if record.decision_state == DecisionState.EXECUTED
    )
    if not executed:
        raise EdgeGateCalibrationInsufficientDataError(
            "EDGE calibration requires at least one executed DTR record"
        )

    ratio_values: list[float] = []
    cost_bps_values: list[float] = []
    for record in executed:
        if not _is_finite_non_negative(record.expected_cost):
            continue
        if record.expected_cost <= 0.0:
            continue
        cost_bps_values.append(record.expected_cost * 10_000.0)
        net_return = record.gross_return - record.realized_cost
        if math.isfinite(net_return) and net_return > 0.0:
            ratio_values.append(net_return / record.expected_cost)

    if len(ratio_values) < calibration.min_positive_trades:
        raise EdgeGateCalibrationInsufficientDataError(
            "THR-E01 calibration requires more positive executed trades "
            f"({len(ratio_values)} < {calibration.min_positive_trades})"
        )
    if len(cost_bps_values) < calibration.min_cost_observations:
        raise EdgeGateCalibrationInsufficientDataError(
            "THR-E02 calibration requires more expected-cost observations "
            f"({len(cost_bps_values)} < {calibration.min_cost_observations})"
        )

    ratio_quantile = 1.0 - calibration.positive_edge_coverage_target
    e01 = _calibrate_multiplier_threshold(
        ratio_values=tuple(ratio_values),
        quantile=ratio_quantile,
        calibration=calibration,
    )
    e02 = _calibrate_absolute_threshold_bps(
        cost_bps_values=tuple(cost_bps_values),
        calibration=calibration,
    )

    notes = (
        "THR-E01 uses realized positive net return divided by ex-ante expected_cost.",
        "THR-E02 uses ex-ante expected_cost converted from return fraction to bps.",
        "Published values are conservative upper bootstrap CI bounds floored by human safety minima.",
    )
    return EdgeGateCalibrationReport(
        produced_by=calibration.produced_by,
        generated_at=generated_at or datetime.now(timezone.utc),
        total_record_count=len(records),
        executed_record_count=len(executed),
        positive_trade_count=len(ratio_values),
        cost_observation_count=len(cost_bps_values),
        pair_scope=tuple(sorted({record.pair for record in executed})),
        engine_scope=tuple(sorted({record.engine_id for record in executed})),
        runtime_modes=tuple(sorted({record.runtime_mode for record in executed if record.runtime_mode})),
        cost_reference_policy="expected_cost only (fractional return units, explicitly converted to bps for THR-E02)",
        positive_trade_definition="DecisionState.EXECUTED and (gross_return - realized_cost) > 0 and expected_cost > 0",
        thresholds=(e01, e02),
        notes=notes,
    )


def build_edge_gate_calibration_artifact(
    report: EdgeGateCalibrationReport,
    *,
    signed_by: str,
    signature_note: str = "",
    config: EdgeGateCalibrationConfig | None = None,
    signed_at: datetime | None = None,
) -> CalibrationArtifact:
    """Convert a Local IA Lab EDGE report into a shared calibration artifact."""

    calibration = config or EdgeGateCalibrationConfig(produced_by=report.produced_by)
    thresholds = (
        CalibrationThresholdEntry(
            threshold_id=calibration.edge_multiplier_threshold_id,
            value=round(
                report.get_threshold(calibration.edge_multiplier_threshold_id).published_value,
                6,
            ),
            description="Minimum multiplier between expected edge and expected cost.",
            source_module=calibration.source_module,
            calibration_artifact=calibration.calibration_artifact_path,
            notes="Local IA Lab replay calibration; published conservatively from upper CI.",
        ),
        CalibrationThresholdEntry(
            threshold_id=calibration.min_absolute_edge_threshold_id,
            value=round(
                report.get_threshold(calibration.min_absolute_edge_threshold_id).published_value,
                6,
            ),
            description="Absolute expected-edge floor in bps.",
            source_module=calibration.source_module,
            calibration_artifact=calibration.calibration_artifact_path,
            notes="Local IA Lab replay calibration; published conservatively from upper CI.",
        ),
    )
    unsigned_artifact = CalibrationArtifact(
        artifact_id=calibration.artifact_id,
        version=calibration.calibration_version,
        produced_by=calibration.produced_by,
        generated_at=report.generated_at,
        thresholds=thresholds,
        signature=CalibrationManualSignature(
            signed_by=signed_by,
            signed_at=signed_at or datetime.now(timezone.utc),
            note=signature_note,
        ),
    )
    return unsigned_artifact.model_copy(
        update={
            "signature": unsigned_artifact.signature.model_copy(
                update={"payload_hash_sha256": unsigned_artifact.payload_hash_sha256()}
            )
        }
    )


def write_edge_gate_calibration_artifact(
    artifact: CalibrationArtifact,
    path: Path | str,
) -> Path:
    """Persist a signed EDGE calibration artifact as YAML."""

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(
        target,
        yaml.safe_dump(artifact.model_dump(mode="json"), sort_keys=False),
    )
    return target


def _calibrate_multiplier_threshold(
    *,
    ratio_values: tuple[float, ...],
    quantile: float,
    calibration: EdgeGateCalibrationConfig,
) -> EdgeGateThresholdCalibration:
    point_estimate = _quantile(ratio_values, quantile)
    bootstrap_interval = stationary_bootstrap_confidence_interval(
        ratio_values,
        estimator=lambda sample: _quantile(sample, quantile),
        config=StationaryBootstrapConfig(
            bootstrap_samples=calibration.bootstrap_samples,
            confidence_level=calibration.confidence_level,
            rng_seed=calibration.rng_seed,
        ),
    )
    ci_lower = bootstrap_interval.ci_lower
    ci_upper = bootstrap_interval.ci_upper
    _validate_relative_ic_width(
        point_estimate=point_estimate,
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        calibration=calibration,
        threshold_id=calibration.edge_multiplier_threshold_id,
    )
    hard_cap_policy = apply_human_minimum_floor(ci_upper, calibration.human_multiplier_floor)
    return EdgeGateThresholdCalibration(
        threshold_id=calibration.edge_multiplier_threshold_id,
        unit="multiplier",
        point_estimate=round(point_estimate, 6),
        ic95_lower=round(ci_lower, 6),
        ic95_upper=round(ci_upper, 6),
        published_value=round(hard_cap_policy.published_value, 6),
        observation_count=len(ratio_values),
        bootstrap_block_length=bootstrap_interval.expected_block_length,
        hard_cap_human=round(calibration.human_multiplier_floor, 6),
        hard_cap_satisfied=hard_cap_policy.hard_cap_satisfied,
        hard_cap_binding=hard_cap_policy.hard_cap_binding,
        description="Minimum multiplier between expected edge and round-trip expected cost.",
        notes=(
            f"quantile={quantile:.2f} over positive realized net edge ratios",
            f"human_floor={calibration.human_multiplier_floor:.2f}",
            f"hard_cap_binding={hard_cap_policy.hard_cap_binding}",
            f"bootstrap_block_length={bootstrap_interval.expected_block_length}",
        ),
    )


def _calibrate_absolute_threshold_bps(
    *,
    cost_bps_values: tuple[float, ...],
    calibration: EdgeGateCalibrationConfig,
) -> EdgeGateThresholdCalibration:
    quantile = 0.90
    point_estimate = _quantile(cost_bps_values, quantile) + calibration.absolute_edge_margin_bps
    bootstrap_interval = stationary_bootstrap_confidence_interval(
        cost_bps_values,
        estimator=lambda sample: _quantile(sample, quantile) + calibration.absolute_edge_margin_bps,
        config=StationaryBootstrapConfig(
            bootstrap_samples=calibration.bootstrap_samples,
            confidence_level=calibration.confidence_level,
            rng_seed=calibration.rng_seed + 1,
        ),
    )
    ci_lower = bootstrap_interval.ci_lower
    ci_upper = bootstrap_interval.ci_upper
    hard_cap_policy = apply_human_minimum_floor(ci_upper, calibration.human_absolute_floor_bps)
    return EdgeGateThresholdCalibration(
        threshold_id=calibration.min_absolute_edge_threshold_id,
        unit="bps",
        point_estimate=round(point_estimate, 6),
        ic95_lower=round(ci_lower, 6),
        ic95_upper=round(ci_upper, 6),
        published_value=round(hard_cap_policy.published_value, 6),
        observation_count=len(cost_bps_values),
        bootstrap_block_length=bootstrap_interval.expected_block_length,
        hard_cap_human=round(calibration.human_absolute_floor_bps, 6),
        hard_cap_satisfied=hard_cap_policy.hard_cap_satisfied,
        hard_cap_binding=hard_cap_policy.hard_cap_binding,
        description="Absolute expected-edge floor in bps.",
        notes=(
            f"q90(expected_cost_bps)+margin where margin={calibration.absolute_edge_margin_bps:.2f}bps",
            f"human_floor={calibration.human_absolute_floor_bps:.2f}bps",
            f"hard_cap_binding={hard_cap_policy.hard_cap_binding}",
            f"bootstrap_block_length={bootstrap_interval.expected_block_length}",
        ),
    )


def _validate_relative_ic_width(
    *,
    point_estimate: float,
    ci_lower: float,
    ci_upper: float,
    calibration: EdgeGateCalibrationConfig,
    threshold_id: str,
) -> None:
    if point_estimate <= 0.0:
        raise EdgeGateCalibrationValidationError(
            f"{threshold_id} point estimate must be > 0, got {point_estimate:.6f}"
        )
    if (ci_upper - ci_lower) > calibration.max_relative_ic_width * point_estimate:
        raise EdgeGateCalibrationValidationError(
            f"{threshold_id} bootstrap interval too wide for safe publication"
        )


def _quantile(values: Iterable[float], quantile: float) -> float:
    ordered = tuple(sorted(values))
    if not ordered:
        raise EdgeGateCalibrationValidationError("quantile requires at least one finite value")
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * quantile
    lower_index = int(math.floor(position))
    upper_index = int(math.ceil(position))
    if lower_index == upper_index:
        return ordered[lower_index]
    lower = ordered[lower_index]
    upper = ordered[upper_index]
    weight = position - lower_index
    return lower + (upper - lower) * weight


def _is_finite_non_negative(value: float) -> bool:
    return math.isfinite(value) and value >= 0.0


__all__ = [
    "EdgeGateCalibrationConfig",
    "EdgeGateCalibrationError",
    "EdgeGateCalibrationInsufficientDataError",
    "EdgeGateCalibrationReport",
    "EdgeGateCalibrationValidationError",
    "EdgeGateThresholdCalibration",
    "build_edge_gate_calibration_artifact",
    "calibrate_edge_gate_thresholds",
    "write_edge_gate_calibration_artifact",
]
