"""Typed Strategy Ladder proxy/fidelity surfacing for cockpit/report readers.

This module is read-side only. It never upgrades proof; it only makes the
remaining proxy/default/fidelity blockers explicit and machine-checkable.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence

from pydantic import BaseModel, Field


_SMALL_SAMPLE_FEATURE_ROW_THRESHOLD = 30


class ThresholdCalibrationCounts(BaseModel, frozen=True):
    """Compact threshold default/calibration count surface."""

    total_count: int = Field(default=0, ge=0)
    default_count: int = Field(default=0, ge=0)
    calibrated_count: int = Field(default=0, ge=0)
    calibration_not_proven_count: int = Field(default=0, ge=0)


class StrategyLadderProxyFidelitySurface(BaseModel, frozen=True):
    """Derived proxy/fidelity visibility surface for one Strategy Ladder run."""

    feature_store_pipeline_status: str = "FEATURE_STORE_NOT_PROVEN"
    feature_row_sample_status: str = "FEATURE_ROWS_NOT_PROVEN"
    expected_edge_governance_status: str = "EXPECTED_EDGE_NOT_PROVEN"
    execution_fidelity_status: str = "EXECUTION_FIDELITY_NOT_PROVEN"
    threshold_calibration_status: str = "THRESHOLDS_NOT_DECLARED"
    threshold_counts: ThresholdCalibrationCounts = ThresholdCalibrationCounts()
    venue_transfer_status: str = "BINANCE_SHADOW_REQUIRED"
    promotion_artifact_status: str = "PROMOTION_ARTIFACTS_NOT_PROVEN"
    overall_backtest_proof_status: str = "BACKTEST_PROOF_NOT_PROVEN"
    blocker_codes: tuple[str, ...] = ()


def classify_threshold_calibration_counts(
    threshold_rows: Iterable[Mapping[str, object]],
) -> ThresholdCalibrationCounts:
    """Count default/calibrated/not-proven threshold rows from manifest payloads."""

    total_count = 0
    default_count = 0
    calibrated_count = 0
    calibration_not_proven_count = 0
    for row in threshold_rows:
        total_count += 1
        threshold_status = str(row.get("threshold_status") or "")
        calibration_status = str(row.get("calibration_status") or "")
        if threshold_status == "THRESHOLD_DEFAULT":
            default_count += 1
        if threshold_status == "THRESHOLD_CALIBRATED":
            calibrated_count += 1
        if calibration_status != "CALIBRATION_READY":
            calibration_not_proven_count += 1
    return ThresholdCalibrationCounts(
        total_count=total_count,
        default_count=default_count,
        calibrated_count=calibrated_count,
        calibration_not_proven_count=calibration_not_proven_count,
    )


def build_strategy_ladder_proxy_fidelity_surface(
    *,
    feature_store_status: str,
    feature_row_count: int,
    expected_edge_truth_status: str,
    expected_edge_governed_count: int,
    execution_fidelity_gap_codes: Sequence[str],
    threshold_rows: Iterable[Mapping[str, object]],
    historical_replay_venue: str,
    execution_target_venue: str,
    backtest_class: str,
    venue_transfer_status: str,
    promotion_artifact_status: str,
    overall_backtest_proof_status: str,
) -> StrategyLadderProxyFidelitySurface:
    """Materialize the explicit proxy/fidelity blocker surface.

    This is display doctrine only:
    - feature-store readiness is pipeline readiness, never statistical proof
    - expected-edge governance is blocked until governed counts are non-zero
    - threshold defaults remain visible until calibrated
    - venue transfer stays shadow-required for BYBIT replay targeting BINANCE
    """

    blockers: list[str] = []
    threshold_counts = classify_threshold_calibration_counts(threshold_rows)

    if feature_store_status == "FEATURE_STORE_READY":
        feature_store_pipeline_status = "PIPELINE_READY_ONLY"
        if feature_row_count <= 0:
            feature_row_sample_status = "FEATURE_ROWS_NOT_PROVEN"
        elif feature_row_count < _SMALL_SAMPLE_FEATURE_ROW_THRESHOLD:
            feature_row_sample_status = "NOT_PROVEN_SMALL_SAMPLE"
            blockers.append("NOT_PROVEN_SMALL_SAMPLE")
        else:
            feature_row_sample_status = "FEATURE_ROWS_PIPELINE_ONLY"
    else:
        feature_store_pipeline_status = feature_store_status or "FEATURE_STORE_NOT_PROVEN"
        feature_row_sample_status = "FEATURE_ROWS_NOT_PROVEN"

    if expected_edge_governed_count <= 0:
        expected_edge_governance_status = "EXPECTED_EDGE_NOT_GOVERNED"
        blockers.append("EXPECTED_EDGE_NOT_GOVERNED")
    else:
        expected_edge_governance_status = (
            expected_edge_truth_status or "EXPECTED_EDGE_GOVERNED_BACKTEST_TRUTH"
        )

    if execution_fidelity_gap_codes:
        execution_fidelity_status = "EXECUTION_FIDELITY_PARTIAL"
        blockers.append("EXECUTION_FIDELITY_PARTIAL")
        blockers.extend(str(code) for code in execution_fidelity_gap_codes if str(code))
    else:
        execution_fidelity_status = "EXECUTION_FIDELITY_READY"

    if (
        threshold_counts.default_count > 0
        or threshold_counts.calibration_not_proven_count > 0
    ):
        threshold_calibration_status = "THRESHOLDS_DEFAULT_NOT_CALIBRATED"
        blockers.append("THRESHOLDS_DEFAULT_NOT_CALIBRATED")
    elif threshold_counts.total_count > 0:
        threshold_calibration_status = "THRESHOLDS_CALIBRATED"
    else:
        threshold_calibration_status = "THRESHOLDS_NOT_DECLARED"

    normalized_venue_transfer_status = venue_transfer_status or "BINANCE_SHADOW_REQUIRED"
    if (
        backtest_class == "BYBIT_PROXY_BACKTEST"
        and historical_replay_venue == "BYBIT"
        and execution_target_venue == "BINANCE"
    ):
        normalized_venue_transfer_status = "BINANCE_SHADOW_REQUIRED"
    if normalized_venue_transfer_status == "BINANCE_SHADOW_REQUIRED":
        blockers.append("BINANCE_SHADOW_REQUIRED")

    normalized_promotion_artifact_status = promotion_artifact_status
    if blockers and promotion_artifact_status == "PROMOTION_ARTIFACTS_READY":
        normalized_promotion_artifact_status = "PROMOTION_ARTIFACTS_BLOCKED_BY_FIDELITY"

    normalized_overall_backtest_proof_status = overall_backtest_proof_status
    if blockers and overall_backtest_proof_status == "BACKTEST_PROOF_READY":
        normalized_overall_backtest_proof_status = "BACKTEST_PROOF_BLOCKED"

    return StrategyLadderProxyFidelitySurface(
        feature_store_pipeline_status=feature_store_pipeline_status,
        feature_row_sample_status=feature_row_sample_status,
        expected_edge_governance_status=expected_edge_governance_status,
        execution_fidelity_status=execution_fidelity_status,
        threshold_calibration_status=threshold_calibration_status,
        threshold_counts=threshold_counts,
        venue_transfer_status=normalized_venue_transfer_status,
        promotion_artifact_status=normalized_promotion_artifact_status,
        overall_backtest_proof_status=normalized_overall_backtest_proof_status,
        blocker_codes=tuple(dict.fromkeys(code for code in blockers if code)),
    )


__all__ = [
    "StrategyLadderProxyFidelitySurface",
    "ThresholdCalibrationCounts",
    "build_strategy_ladder_proxy_fidelity_surface",
    "classify_threshold_calibration_counts",
]
