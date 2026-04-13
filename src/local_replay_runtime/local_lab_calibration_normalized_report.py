"""Normalized Local IA Lab calibration report over bounded 13-A/13-B evidence."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

from pydantic import BaseModel, Field

from local_replay_runtime.edge_gate_calibration import (
    EdgeGateCalibrationConfig,
    EdgeGateCalibrationReport,
)
from local_replay_runtime.local_lab_calibration_methods_review import (
    LocalLabCalibrationMethodsReview,
)
from local_replay_runtime.local_lab_multiple_testing_review import (
    LocalLabMultipleTestingReview,
)
from local_replay_runtime.local_lab_tail_risk_review import LocalLabTailRiskReview
from meta_minimal.dtr_core.dtr_record_builder import DTRRecord


class LocalLabCalibrationDataWindow(BaseModel, frozen=True):
    """Bounded calibration data window summary."""

    start: str | None = None
    end: str | None = None


class LocalLabCalibrationOosReservation(BaseModel, frozen=True):
    """Bounded OOS reservation summary for the normalized calibration report."""

    train_share: float | None = Field(default=None, ge=0.0, le=1.0)
    val_share: float | None = Field(default=None, ge=0.0, le=1.0)
    test_reserved_share: float | None = Field(default=None, ge=0.0, le=1.0)
    test_reserved_touched: bool | None = None


class LocalLabCalibrationReproducibility(BaseModel, frozen=True):
    """Reproducibility metadata for the normalized calibration report."""

    rng_seed: int | None = Field(default=None, ge=0)
    data_hash_sha256: str = Field(..., min_length=1)
    code_reference: str = ""
    method_version: str = Field(default="local_lab_calibration_report_v1", min_length=1)


class LocalLabCalibrationThresholdReport(BaseModel, frozen=True):
    """Normalized per-threshold calibration entry."""

    threshold_id: str = Field(..., min_length=1)
    method: str = Field(..., min_length=1)
    unit: str = Field(..., min_length=1)
    observation_count: int = Field(default=0, ge=0)
    value_point: float | None = None
    ic95_lower: float | None = None
    ic95_upper: float | None = None
    published_value: float | None = None
    hard_cap_human: float | None = None
    hard_cap_satisfied: bool | None = None
    hard_cap_binding: bool | None = None
    bootstrap_block_length: int | None = Field(default=None, ge=1)
    threshold_u: float | None = None
    exceedance_count: int = Field(default=0, ge=0)
    xi_hat: float | None = None
    beta_hat: float | None = None
    stationarity_status: str = Field(default="not_evaluated", min_length=1)
    dsr_check: str = Field(default="n/a", min_length=1)
    review_status: str = Field(default="not_evaluated", min_length=1)
    notes: tuple[str, ...] = ()


class LocalLabNormalizedCalibrationReport(BaseModel, frozen=True):
    """Audit-ready normalized Local IA Lab calibration report."""

    correlation_id: str = Field(..., min_length=1)
    export_dir: str = Field(..., min_length=1)
    run_id: str = Field(..., min_length=1)
    artifact_version: str = Field(default="calibration_v3_local_lab", min_length=1)
    produced_at: datetime
    produced_by: str = Field(..., min_length=1)
    data_window: LocalLabCalibrationDataWindow
    method_per_threshold: dict[str, LocalLabCalibrationThresholdReport]
    threshold_count: int = Field(default=0, ge=0)
    review_status: str = Field(..., min_length=1)
    review_ready: bool = False
    global_dsr: float | None = None
    multi_test_correction: str = "not_evaluated"
    oos_reservation: LocalLabCalibrationOosReservation
    reproducibility: LocalLabCalibrationReproducibility
    blocking_reasons: tuple[str, ...] = ()
    caution_flags: tuple[str, ...] = ()


def build_local_lab_calibration_normalized_report(
    *,
    correlation_id: str,
    export_dir: str,
    run_id: str,
    records: tuple[DTRRecord, ...],
    edge_report: EdgeGateCalibrationReport,
    edge_config: EdgeGateCalibrationConfig,
    calibration_methods_review: LocalLabCalibrationMethodsReview,
    multiple_testing_review: LocalLabMultipleTestingReview,
    tail_risk_review: LocalLabTailRiskReview,
) -> LocalLabNormalizedCalibrationReport:
    """Build the bounded normalized Local IA Lab calibration report for 13-A/13-B."""

    method_per_threshold: dict[str, LocalLabCalibrationThresholdReport] = {}
    for threshold in edge_report.thresholds:
        dsr_check = calibration_methods_review.dsr_status
        method_per_threshold[threshold.threshold_id] = LocalLabCalibrationThresholdReport(
            threshold_id=threshold.threshold_id,
            method="stationary_block_bootstrap",
            unit=threshold.unit,
            observation_count=threshold.observation_count,
            value_point=threshold.point_estimate,
            ic95_lower=threshold.ic95_lower,
            ic95_upper=threshold.ic95_upper,
            published_value=threshold.published_value,
            hard_cap_human=threshold.hard_cap_human,
            hard_cap_satisfied=threshold.hard_cap_satisfied,
            hard_cap_binding=threshold.hard_cap_binding,
            bootstrap_block_length=threshold.bootstrap_block_length,
            stationarity_status=calibration_methods_review.stationarity_status,
            dsr_check=dsr_check,
            review_status=calibration_methods_review.review_status.value,
            notes=threshold.notes,
        )

    for breaker in tail_risk_review.breakers:
        fit = breaker.fit_result
        method_per_threshold[breaker.threshold_id] = LocalLabCalibrationThresholdReport(
            threshold_id=breaker.threshold_id,
            method="POT_GPD" if fit is not None else "POT_GPD_UNAVAILABLE",
            unit="loss_fraction",
            observation_count=breaker.period_count,
            value_point=breaker.var_estimate,
            ic95_lower=breaker.var_ci_lower,
            ic95_upper=breaker.var_ci_upper,
            published_value=breaker.published_value,
            hard_cap_human=breaker.hard_cap_human,
            hard_cap_satisfied=breaker.hard_cap_satisfied,
            hard_cap_binding=breaker.hard_cap_binding,
            threshold_u=breaker.threshold_u,
            exceedance_count=breaker.exceedance_count,
            xi_hat=breaker.xi_hat,
            beta_hat=breaker.beta_hat,
            stationarity_status=calibration_methods_review.stationarity_status,
            dsr_check="n/a",
            review_status=breaker.review_status.value,
            notes=breaker.caution_flags,
        )

    review_status = _merge_review_status(
        calibration_methods_review.review_status.value,
        tail_risk_review.review_status.value,
    )
    data_window = _build_data_window(records)
    reproducibility = LocalLabCalibrationReproducibility(
        rng_seed=edge_config.rng_seed,
        data_hash_sha256=_hash_records(records),
        code_reference="not_captured",
    )
    global_dsr = (
        None
        if calibration_methods_review.dsr_result is None
        else calibration_methods_review.dsr_result.dsr
    )

    return LocalLabNormalizedCalibrationReport(
        correlation_id=correlation_id,
        export_dir=export_dir,
        run_id=run_id,
        produced_at=edge_report.generated_at,
        produced_by=edge_report.produced_by,
        data_window=data_window,
        method_per_threshold=method_per_threshold,
        threshold_count=len(method_per_threshold),
        review_status=review_status,
        review_ready=review_status == "ready",
        global_dsr=global_dsr,
        multi_test_correction=multiple_testing_review.multi_test_correction,
        oos_reservation=LocalLabCalibrationOosReservation(),
        reproducibility=reproducibility,
        blocking_reasons=tuple(
            dict.fromkeys(
                [
                    *calibration_methods_review.blocking_reasons,
                    *multiple_testing_review.blocking_reasons,
                    *tail_risk_review.blocking_reasons,
                ]
            )
        ),
        caution_flags=tuple(
            dict.fromkeys(
                [
                    *calibration_methods_review.caution_flags,
                    *multiple_testing_review.caution_flags,
                    *tail_risk_review.caution_flags,
                ]
            )
        ),
    )


def _build_data_window(records: tuple[DTRRecord, ...]) -> LocalLabCalibrationDataWindow:
    if not records:
        return LocalLabCalibrationDataWindow()
    timestamps = sorted(record.timestamp for record in records)
    start = datetime.fromtimestamp(timestamps[0], tz=timezone.utc).date().isoformat()
    end = datetime.fromtimestamp(timestamps[-1], tz=timezone.utc).date().isoformat()
    return LocalLabCalibrationDataWindow(start=start, end=end)


def _hash_records(records: tuple[DTRRecord, ...]) -> str:
    payload = json.dumps(
        [record.model_dump(mode="json") for record in records],
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _merge_review_status(*statuses: str) -> str:
    if any(status == "blocked" for status in statuses):
        return "blocked"
    if any(status == "partial" for status in statuses):
        return "partial"
    if all(status == "ready" for status in statuses):
        return "ready"
    return "not_evaluated"


__all__ = [
    "LocalLabCalibrationDataWindow",
    "LocalLabCalibrationOosReservation",
    "LocalLabCalibrationReproducibility",
    "LocalLabCalibrationThresholdReport",
    "LocalLabNormalizedCalibrationReport",
    "build_local_lab_calibration_normalized_report",
]
