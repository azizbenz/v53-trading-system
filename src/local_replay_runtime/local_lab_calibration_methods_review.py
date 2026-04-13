"""Local IA Lab review sidecar over shared calibration-method primitives."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from calibration_methods import (
    DeflatedSharpeRatioResult,
    DualStationarityResult,
    PurgedWalkForwardConfig,
    PurgedWalkForwardPlan,
    build_purged_walk_forward_plan,
    compute_deflated_sharpe_ratio,
    evaluate_dual_stationarity,
)
from meta_minimal.dtr_core.decision_state_encoder import DecisionState
from meta_minimal.dtr_core.dtr_record_builder import DTRRecord


class LocalLabCalibrationMethodsStatus(StrEnum):
    """Bounded review states for the Local IA Lab calibration-methods sidecar."""

    READY = "ready"
    PARTIAL = "partial"
    BLOCKED = "blocked"


class LocalLabCalibrationMethodsReview(BaseModel, frozen=True):
    """Audit-ready Local IA Lab review over walk-forward geometry and DSR."""

    correlation_id: str = Field(..., min_length=1)
    export_dir: str = Field(..., min_length=1)
    run_id: str = Field(..., min_length=1)
    review_status: LocalLabCalibrationMethodsStatus
    review_ready: bool = False
    record_count: int = Field(default=0, ge=0)
    executed_record_count: int = Field(default=0, ge=0)
    distinct_scope_count: int = Field(default=0, ge=0)
    timestamp_count: int = Field(default=0, ge=0)
    walk_forward_plan_status: str = Field(default="not_evaluated", min_length=1)
    walk_forward_plan_ready: bool = False
    walk_forward_plan: PurgedWalkForwardPlan | None = None
    stationarity_status: str = Field(default="not_evaluated", min_length=1)
    stationarity_ready: bool = False
    stationarity_pass: bool | None = None
    stationarity_result: DualStationarityResult | None = None
    dsr_status: str = Field(default="not_evaluated", min_length=1)
    dsr_ready: bool = False
    dsr_pass: bool | None = None
    dsr_floor: float = Field(default=0.95, gt=0.0, lt=1.0)
    dsr_trial_count: int = Field(default=0, ge=0)
    dsr_result: DeflatedSharpeRatioResult | None = None
    blocking_reasons: tuple[str, ...] = ()
    caution_flags: tuple[str, ...] = ()


def build_local_lab_calibration_methods_review(
    *,
    correlation_id: str,
    export_dir: str,
    run_id: str,
    records: tuple[DTRRecord, ...],
    dsr_floor: float = 0.95,
) -> LocalLabCalibrationMethodsReview:
    """Build a bounded Local IA Lab review from shared calibration-method helpers."""

    ordered_timestamps = tuple(sorted({record.timestamp for record in records}))
    executed_returns = tuple(
        record.gross_return - record.realized_cost
        for record in records
        if record.decision_state == DecisionState.EXECUTED
    )
    distinct_scopes = {
        (record.pair, record.engine_id)
        for record in records
    }

    walk_forward_plan_status = "not_evaluated"
    walk_forward_plan_ready = False
    walk_forward_plan: PurgedWalkForwardPlan | None = None
    stationarity_status = "not_evaluated"
    stationarity_ready = False
    stationarity_pass: bool | None = None
    stationarity_result: DualStationarityResult | None = None
    dsr_status = "not_evaluated"
    dsr_ready = False
    dsr_pass: bool | None = None
    dsr_result: DeflatedSharpeRatioResult | None = None
    blocking_reasons: list[str] = []
    caution_flags: list[str] = []

    if len(ordered_timestamps) < 24:
        walk_forward_plan_status = "insufficient_history"
        caution_flags.append("CALIBRATION_METHODS_WALK_FORWARD_HISTORY_INSUFFICIENT")
    else:
        try:
            walk_forward_plan = build_purged_walk_forward_plan(
                len(ordered_timestamps),
                config=_derive_walk_forward_config(len(ordered_timestamps)),
            )
            walk_forward_plan_status = "ready"
            walk_forward_plan_ready = True
        except ValueError as exc:
            walk_forward_plan_status = "invalid_inputs"
            blocking_reasons.append("CALIBRATION_METHODS_WALK_FORWARD_PLAN_INVALID")
            caution_flags.append(str(exc))

    if len(executed_returns) < 24:
        stationarity_status = "insufficient_history"
        caution_flags.append("CALIBRATION_METHODS_STATIONARITY_HISTORY_INSUFFICIENT")
    else:
        try:
            stationarity_result = evaluate_dual_stationarity(executed_returns)
            stationarity_ready = True
            stationarity_pass = stationarity_result.passes_dual_test
            stationarity_status = (
                "ready" if stationarity_result.passes_dual_test else "failed_threshold"
            )
            if stationarity_result.passes_dual_test is False:
                blocking_reasons.append("CALIBRATION_METHODS_STATIONARITY_FAILED")
        except ValueError as exc:
            stationarity_status = "invalid_inputs"
            blocking_reasons.append("CALIBRATION_METHODS_STATIONARITY_INVALID")
            caution_flags.append(str(exc))

    if len(executed_returns) < 24:
        dsr_status = "insufficient_history"
        caution_flags.append("CALIBRATION_METHODS_DSR_HISTORY_INSUFFICIENT")
    else:
        try:
            dsr_result = compute_deflated_sharpe_ratio(
                executed_returns,
                trial_count=max(len(distinct_scopes), 1),
                acceptance_floor=dsr_floor,
            )
            dsr_status = "ready" if dsr_result.passes_floor else "failed_threshold"
            dsr_ready = True
            dsr_pass = dsr_result.passes_floor
            if dsr_result.passes_floor is False:
                blocking_reasons.append("CALIBRATION_METHODS_DSR_BELOW_FLOOR")
        except ValueError as exc:
            dsr_status = "invalid_inputs"
            blocking_reasons.append("CALIBRATION_METHODS_DSR_INVALID")
            caution_flags.append(str(exc))

    review_ready = (
        walk_forward_plan_ready
        and stationarity_ready
        and stationarity_pass is True
        and dsr_ready
        and dsr_pass is True
    )
    if blocking_reasons:
        review_status = LocalLabCalibrationMethodsStatus.BLOCKED
    elif review_ready:
        review_status = LocalLabCalibrationMethodsStatus.READY
    else:
        review_status = LocalLabCalibrationMethodsStatus.PARTIAL

    return LocalLabCalibrationMethodsReview(
        correlation_id=correlation_id,
        export_dir=export_dir,
        run_id=run_id,
        review_status=review_status,
        review_ready=review_ready,
        record_count=len(records),
        executed_record_count=len(executed_returns),
        distinct_scope_count=len(distinct_scopes),
        timestamp_count=len(ordered_timestamps),
        walk_forward_plan_status=walk_forward_plan_status,
        walk_forward_plan_ready=walk_forward_plan_ready,
        walk_forward_plan=walk_forward_plan,
        stationarity_status=stationarity_status,
        stationarity_ready=stationarity_ready,
        stationarity_pass=stationarity_pass,
        stationarity_result=stationarity_result,
        dsr_status=dsr_status,
        dsr_ready=dsr_ready,
        dsr_pass=dsr_pass,
        dsr_floor=dsr_floor,
        dsr_trial_count=max(len(distinct_scopes), 1) if executed_returns else 0,
        dsr_result=dsr_result,
        blocking_reasons=tuple(dict.fromkeys(blocking_reasons)),
        caution_flags=tuple(dict.fromkeys(caution_flags)),
    )


def _derive_walk_forward_config(observation_count: int) -> PurgedWalkForwardConfig:
    if observation_count >= 60:
        fold_count = 5
    else:
        fold_count = 3
    validation_window_size = max(4, observation_count // (fold_count * 4))
    return PurgedWalkForwardConfig(
        fold_count=fold_count,
        validation_window_size=validation_window_size,
        embargo_size=2,
        label_horizon_size=2,
        min_train_size=max(8, observation_count // 3),
    )


__all__ = [
    "LocalLabCalibrationMethodsReview",
    "LocalLabCalibrationMethodsStatus",
    "build_local_lab_calibration_methods_review",
]
