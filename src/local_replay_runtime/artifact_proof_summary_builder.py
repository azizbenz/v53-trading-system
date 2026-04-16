"""Conservative Local IA Lab proof-summary builder for governed artifact export."""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel, Field

from interface_contracts import ArtifactProofSummary, validate_artifact_proof_summary
from meta_learning.contracts import TradeLossAttributionReport
from meta_minimal.meta_runtime import MetaRuntimeResult

from local_replay_runtime.artifact_ablation_study import LocalLabAblationStudy
from local_replay_runtime.local_lab_calibration_methods_review import (
    LocalLabCalibrationMethodsReview,
)
from local_replay_runtime.local_lab_execution_runtime_projection import (
    LocalLabExecutionRuntimeProjection,
)
from local_replay_runtime.local_lab_multiple_testing_review import (
    LocalLabMultipleTestingReview,
)
from local_replay_runtime.walk_forward_review import WalkForwardReviewSummary


class LocalLabArtifactProofAssessment(BaseModel, frozen=True):
    """Audit-ready assessment of the current Local IA Lab proof surface."""

    correlation_id: str = Field(..., min_length=1)
    export_dir: str = Field(..., min_length=1)
    run_id: str = Field(..., min_length=1)
    proof_summary: ArtifactProofSummary
    ready_for_vps_import: bool = False
    validation_reasons: tuple[str, ...] = ()
    pending_dimensions: tuple[str, ...] = ()
    caution_flags: tuple[str, ...] = ()
    dtr_coverage: float = Field(default=0.0, ge=0.0)
    incomplete_path_count: int = Field(default=0, ge=0)
    executed_records: int = Field(default=0, ge=0)
    losing_trade_count: int = Field(default=0, ge=0)
    regime_count: int = Field(default=0, ge=0)
    friction_regret_ratio: float = Field(default=0.0, ge=0.0)
    observed_block_rate_proxy: float = Field(default=0.0, ge=0.0)
    capital_efficiency_ratio: float | None = None
    calibration_methods_review_status: str = Field(default="not_evaluated", min_length=1)
    calibration_methods_review_ready: bool = False
    calibration_methods_blocking_reasons: tuple[str, ...] = ()
    calibration_methods_dsr_pass: bool | None = None
    calibration_methods_dsr_value: float | None = None
    calibration_methods_walk_forward_plan_ready: bool = False
    calibration_methods_stationarity_pass: bool | None = None
    calibration_methods_stationarity_status: str = Field(default="not_evaluated", min_length=1)
    execution_runtime_projection_status: str = Field(default="not_evaluated", min_length=1)
    execution_runtime_projection_ready: bool = False
    execution_runtime_projection_consumer_count: int = Field(default=0, ge=0)
    execution_runtime_projection_ready_consumer_count: int = Field(default=0, ge=0)
    execution_runtime_projection_partial_consumer_count: int = Field(default=0, ge=0)
    execution_runtime_projection_blocked_consumer_count: int = Field(default=0, ge=0)
    execution_runtime_projection_blocking_reasons: tuple[str, ...] = ()
    multiple_testing_review_status: str = Field(default="not_evaluated", min_length=1)
    multiple_testing_review_ready: bool = False
    multiple_testing_correction_required: bool = False
    multiple_testing_correction: str = Field(default="not_evaluated", min_length=1)
    multiple_testing_family_count: int = Field(default=0, ge=0)
    multiple_testing_blocking_reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class _AblationAssessmentState:
    delta_net_pnl: float
    delta_ce: float | None
    block_rate_value: float
    ready: bool
    blocking_reasons: tuple[str, ...]


@dataclass(frozen=True)
class _CoreAssessmentState:
    proof_summary: ArtifactProofSummary
    regime_count: int
    dtr_coverage: float
    incomplete_path_count: int
    executed_records: int
    losing_trade_count: int
    friction_regret_ratio: float
    observed_block_rate_proxy: float
    capital_efficiency_ratio: float | None
    pending_dimensions: tuple[str, ...]
    caution_flags: tuple[str, ...]


@dataclass(frozen=True)
class _CalibrationMethodsAssessmentState:
    review_status: str
    review_ready: bool
    blocking_reasons: tuple[str, ...]
    dsr_pass: bool | None
    dsr_value: float | None
    walk_forward_plan_ready: bool
    stationarity_pass: bool | None
    stationarity_status: str
    pending_dimensions: tuple[str, ...]
    caution_flags: tuple[str, ...]
    validation_reasons: tuple[str, ...]


@dataclass(frozen=True)
class _ExecutionRuntimeProjectionAssessmentState:
    projection_status: str
    projection_ready: bool
    consumer_count: int
    ready_consumer_count: int
    partial_consumer_count: int
    blocked_consumer_count: int
    blocking_reasons: tuple[str, ...]
    caution_flags: tuple[str, ...]


@dataclass(frozen=True)
class _MultipleTestingAssessmentState:
    review_status: str
    review_ready: bool
    correction_required: bool
    correction: str
    family_count: int
    blocking_reasons: tuple[str, ...]
    pending_dimensions: tuple[str, ...]
    caution_flags: tuple[str, ...]
    validation_reasons: tuple[str, ...]


def _build_friction_regret_ratio(meta_result: MetaRuntimeResult) -> tuple[float, tuple[str, ...]]:
    ratios = tuple(
        max(record.realized_cost - record.expected_cost, 0.0) / record.expected_cost
        for record in meta_result.records
        if record.decision_state == "executed" and record.expected_cost > 0.0
    )
    if not ratios:
        return 1.0, ("FRICTION_REGRET_EVIDENCE_MISSING",)
    return sum(ratios) / len(ratios), ()


def _build_block_rate_proxy(meta_result: MetaRuntimeResult) -> float:
    total_records = meta_result.dtr_summary.total_records
    if total_records <= 0:
        return 1.0
    executed_records = meta_result.dtr_summary.by_state.get("executed", 0)
    return max(0.0, min(1.0, 1.0 - (executed_records / total_records)))


def _build_capital_efficiency_ratio(meta_result: MetaRuntimeResult) -> float | None:
    ratios = tuple(
        record.final_size / record.candidate_size
        for record in meta_result.records
        if record.decision_state == "executed" and record.candidate_size > 0.0
    )
    if not ratios:
        return None
    return sum(ratios) / len(ratios)


def _resolve_ablation_state(
    ablation_study: LocalLabAblationStudy | None,
    *,
    observed_block_rate_proxy: float,
) -> _AblationAssessmentState:
    if ablation_study is None:
        return _AblationAssessmentState(
            delta_net_pnl=0.0,
            delta_ce=None,
            block_rate_value=observed_block_rate_proxy,
            ready=False,
            blocking_reasons=(),
        )
    if not ablation_study.study_ready:
        return _AblationAssessmentState(
            delta_net_pnl=0.0,
            delta_ce=None,
            block_rate_value=observed_block_rate_proxy,
            ready=False,
            blocking_reasons=ablation_study.blocking_reasons,
        )
    return _AblationAssessmentState(
        delta_net_pnl=ablation_study.ablation_delta_net_pnl,
        delta_ce=ablation_study.ablation_delta_ce,
        block_rate_value=ablation_study.block_rate_delta,
        ready=True,
        blocking_reasons=ablation_study.blocking_reasons,
    )


def _build_core_assessment_state(
    *,
    meta_result: MetaRuntimeResult,
    trade_loss_attribution: TradeLossAttributionReport,
    walk_forward_review: WalkForwardReviewSummary,
    ablation_study: LocalLabAblationStudy | None,
) -> _CoreAssessmentState:
    regime_count = len(tuple(dict.fromkeys(record.regime for record in meta_result.records if record.regime)))
    dtr_coverage = meta_result.dtr_summary.dtr_coverage
    incomplete_path_count = meta_result.dtr_summary.incomplete_path_count
    executed_records = trade_loss_attribution.executed_records
    losing_trade_count = trade_loss_attribution.losing_trade_count
    friction_regret_ratio, friction_flags = _build_friction_regret_ratio(meta_result)
    observed_block_rate_proxy = _build_block_rate_proxy(meta_result)
    capital_efficiency_ratio = _build_capital_efficiency_ratio(meta_result)
    ablation_state = _resolve_ablation_state(
        ablation_study,
        observed_block_rate_proxy=observed_block_rate_proxy,
    )
    has_unclassified_loss = any(
        attribution.attribution_status == "loss"
        and attribution.primary_failure_mode == "unclassified_loss"
        for attribution in trade_loss_attribution.attributions
    )
    proof_summary = ArtifactProofSummary(
        anti_cowardice_pass=(
            dtr_coverage >= 0.95
            and incomplete_path_count == 0
            and meta_result.dtr_summary.synthetic_input_count == 0
        ),
        friction_regret_pass=(
            not meta_result.break_even_report.has_cost_drift_alert
            and friction_regret_ratio <= 0.05
        ),
        walk_forward_pass=walk_forward_review.walk_forward_pass,
        regime_segmentation_pass=regime_count >= 2,
        operational_burden_pass=(
            meta_result.dtr_summary.total_records > 0
            and ablation_state.block_rate_value <= 0.10
            and not has_unclassified_loss
        ),
        capital_efficiency_pass=(
            None if capital_efficiency_ratio is None else capital_efficiency_ratio >= 0.80
        ),
        ablation_delta_net_pnl=ablation_state.delta_net_pnl,
        ablation_delta_ce=ablation_state.delta_ce,
        friction_regret_value=friction_regret_ratio,
        block_rate_delta=ablation_state.block_rate_value,
    )

    pending_dimensions: list[str] = []
    caution_flags: list[str] = [
        "ANTI_COWARDICE_COVERAGE_PROXY_USED",
        "BLOCK_RATE_PROXY_USED",
        *friction_flags,
    ]
    if not ablation_state.ready:
        pending_dimensions.extend(["ABLATION_DELTA_NET_PNL", "ABLATION_DELTA_CE"])
        caution_flags.append("ABLATION_STUDY_NOT_READY")
        caution_flags.extend(ablation_state.blocking_reasons)
    if regime_count < 2:
        pending_dimensions.append("REGIME_SEGMENTATION")
    if capital_efficiency_ratio is None:
        pending_dimensions.append("CAPITAL_EFFICIENCY")
        caution_flags.append("CAPITAL_EFFICIENCY_EVIDENCE_MISSING")
    if not walk_forward_review.walk_forward_pass:
        pending_dimensions.append("WALK_FORWARD_HUMAN_REVIEW")
    if has_unclassified_loss:
        caution_flags.append("UNCLASSIFIED_LOSS_PRESENT")

    return _CoreAssessmentState(
        proof_summary=proof_summary,
        regime_count=regime_count,
        dtr_coverage=dtr_coverage,
        incomplete_path_count=incomplete_path_count,
        executed_records=executed_records,
        losing_trade_count=losing_trade_count,
        friction_regret_ratio=friction_regret_ratio,
        observed_block_rate_proxy=observed_block_rate_proxy,
        capital_efficiency_ratio=capital_efficiency_ratio,
        pending_dimensions=tuple(pending_dimensions),
        caution_flags=tuple(caution_flags),
    )


def _resolve_calibration_methods_assessment_state(
    review: LocalLabCalibrationMethodsReview | None,
) -> _CalibrationMethodsAssessmentState:
    if review is None:
        return _CalibrationMethodsAssessmentState(
            review_status="not_evaluated",
            review_ready=False,
            blocking_reasons=(),
            dsr_pass=None,
            dsr_value=None,
            walk_forward_plan_ready=False,
            stationarity_pass=None,
            stationarity_status="not_evaluated",
            pending_dimensions=("CALIBRATION_METHODS_REVIEW",),
            caution_flags=("CALIBRATION_METHODS_REVIEW_MISSING",),
            validation_reasons=(),
        )

    pending_dimensions: list[str] = []
    validation_reasons: list[str] = []
    if not review.walk_forward_plan_ready:
        pending_dimensions.append("CALIBRATION_METHODS_WALK_FORWARD_GEOMETRY")
    if review.stationarity_ready is False:
        pending_dimensions.append("CALIBRATION_METHODS_STATIONARITY")
    if review.dsr_ready is False:
        pending_dimensions.append("CALIBRATION_METHODS_DSR")
    if "CALIBRATION_METHODS_DSR_BELOW_FLOOR" in review.blocking_reasons:
        validation_reasons.append("LOCAL_LAB_DSR_REQUIRED")
    if "CALIBRATION_METHODS_DSR_INVALID" in review.blocking_reasons:
        validation_reasons.append("LOCAL_LAB_DSR_INVALID")
    if "CALIBRATION_METHODS_STATIONARITY_FAILED" in review.blocking_reasons:
        validation_reasons.append("LOCAL_LAB_STATIONARITY_REQUIRED")
    if "CALIBRATION_METHODS_STATIONARITY_INVALID" in review.blocking_reasons:
        validation_reasons.append("LOCAL_LAB_STATIONARITY_INVALID")
    if "CALIBRATION_METHODS_WALK_FORWARD_PLAN_INVALID" in review.blocking_reasons:
        validation_reasons.append("LOCAL_LAB_WALK_FORWARD_PLAN_INVALID")

    return _CalibrationMethodsAssessmentState(
        review_status=review.review_status.value,
        review_ready=review.review_ready,
        blocking_reasons=review.blocking_reasons,
        dsr_pass=review.dsr_pass,
        dsr_value=None if review.dsr_result is None else review.dsr_result.dsr,
        walk_forward_plan_ready=review.walk_forward_plan_ready,
        stationarity_pass=review.stationarity_pass,
        stationarity_status=review.stationarity_status,
        pending_dimensions=tuple(pending_dimensions),
        caution_flags=review.caution_flags,
        validation_reasons=tuple(validation_reasons),
    )


def _resolve_execution_runtime_projection_assessment_state(
    projection: LocalLabExecutionRuntimeProjection | None,
) -> _ExecutionRuntimeProjectionAssessmentState:
    if projection is None:
        return _ExecutionRuntimeProjectionAssessmentState(
            projection_status="not_evaluated",
            projection_ready=False,
            consumer_count=0,
            ready_consumer_count=0,
            partial_consumer_count=0,
            blocked_consumer_count=0,
            blocking_reasons=(),
            caution_flags=(),
        )
    return _ExecutionRuntimeProjectionAssessmentState(
        projection_status=projection.projection_status.value,
        projection_ready=projection.projection_ready,
        consumer_count=projection.consumer_count,
        ready_consumer_count=projection.ready_consumer_count,
        partial_consumer_count=projection.partial_consumer_count,
        blocked_consumer_count=projection.blocked_consumer_count,
        blocking_reasons=projection.blocking_reasons,
        caution_flags=projection.caution_flags,
    )


def _resolve_multiple_testing_assessment_state(
    review: LocalLabMultipleTestingReview | None,
) -> _MultipleTestingAssessmentState:
    if review is None:
        return _MultipleTestingAssessmentState(
            review_status="not_evaluated",
            review_ready=False,
            correction_required=False,
            correction="not_evaluated",
            family_count=0,
            blocking_reasons=(),
            pending_dimensions=(),
            caution_flags=("MULTI_TEST_REVIEW_MISSING",),
            validation_reasons=(),
        )

    pending_dimensions: list[str] = []
    validation_reasons: list[str] = []
    if review.review_status.value == "partial":
        pending_dimensions.append("MULTI_TEST_CORRECTION")
    if "MULTI_TEST_CORRECTION_INVALID" in review.blocking_reasons:
        validation_reasons.append("LOCAL_LAB_MULTI_TEST_CORRECTION_INVALID")
    if "MULTI_TEST_CORRECTION_REQUIRED" in review.blocking_reasons:
        validation_reasons.append("LOCAL_LAB_MULTI_TEST_CORRECTION_REQUIRED")

    return _MultipleTestingAssessmentState(
        review_status=review.review_status.value,
        review_ready=review.review_ready,
        correction_required=review.correction_required,
        correction=review.multi_test_correction,
        family_count=review.family_count,
        blocking_reasons=review.blocking_reasons,
        pending_dimensions=tuple(pending_dimensions),
        caution_flags=review.caution_flags,
        validation_reasons=tuple(validation_reasons),
    )


def _build_core_assessment_payload(core: _CoreAssessmentState) -> dict[str, object]:
    return {
        "proof_summary": core.proof_summary,
        "dtr_coverage": core.dtr_coverage,
        "incomplete_path_count": core.incomplete_path_count,
        "executed_records": core.executed_records,
        "losing_trade_count": core.losing_trade_count,
        "regime_count": core.regime_count,
        "friction_regret_ratio": core.friction_regret_ratio,
        "observed_block_rate_proxy": core.observed_block_rate_proxy,
        "capital_efficiency_ratio": core.capital_efficiency_ratio,
    }


def _build_calibration_assessment_payload(
    state: _CalibrationMethodsAssessmentState,
) -> dict[str, object]:
    return {
        "calibration_methods_review_status": state.review_status,
        "calibration_methods_review_ready": state.review_ready,
        "calibration_methods_blocking_reasons": state.blocking_reasons,
        "calibration_methods_dsr_pass": state.dsr_pass,
        "calibration_methods_dsr_value": state.dsr_value,
        "calibration_methods_walk_forward_plan_ready": state.walk_forward_plan_ready,
        "calibration_methods_stationarity_pass": state.stationarity_pass,
        "calibration_methods_stationarity_status": state.stationarity_status,
    }


def _build_execution_runtime_projection_payload(
    state: _ExecutionRuntimeProjectionAssessmentState,
) -> dict[str, object]:
    return {
        "execution_runtime_projection_status": state.projection_status,
        "execution_runtime_projection_ready": state.projection_ready,
        "execution_runtime_projection_consumer_count": state.consumer_count,
        "execution_runtime_projection_ready_consumer_count": state.ready_consumer_count,
        "execution_runtime_projection_partial_consumer_count": state.partial_consumer_count,
        "execution_runtime_projection_blocked_consumer_count": state.blocked_consumer_count,
        "execution_runtime_projection_blocking_reasons": state.blocking_reasons,
    }


def _build_multiple_testing_assessment_payload(
    state: _MultipleTestingAssessmentState,
) -> dict[str, object]:
    return {
        "multiple_testing_review_status": state.review_status,
        "multiple_testing_review_ready": state.review_ready,
        "multiple_testing_correction_required": state.correction_required,
        "multiple_testing_correction": state.correction,
        "multiple_testing_family_count": state.family_count,
        "multiple_testing_blocking_reasons": state.blocking_reasons,
    }


def build_local_lab_artifact_proof_assessment(
    *,
    correlation_id: str,
    export_dir: str,
    run_id: str,
    meta_result: MetaRuntimeResult,
    trade_loss_attribution: TradeLossAttributionReport,
    walk_forward_review: WalkForwardReviewSummary,
    ablation_study: LocalLabAblationStudy | None = None,
    calibration_methods_review: LocalLabCalibrationMethodsReview | None = None,
    execution_runtime_projection: LocalLabExecutionRuntimeProjection | None = None,
    multiple_testing_review: LocalLabMultipleTestingReview | None = None,
) -> LocalLabArtifactProofAssessment:
    """Build a conservative canonical proof summary from current Local IA Lab evidence."""

    core_state = _build_core_assessment_state(
        meta_result=meta_result,
        trade_loss_attribution=trade_loss_attribution,
        walk_forward_review=walk_forward_review,
        ablation_study=ablation_study,
    )
    validation_reasons = list(validate_artifact_proof_summary(core_state.proof_summary))
    pending_dimensions = list(core_state.pending_dimensions)
    caution_flags = list(core_state.caution_flags)

    calibration_state = _resolve_calibration_methods_assessment_state(calibration_methods_review)
    pending_dimensions.extend(calibration_state.pending_dimensions)
    caution_flags.extend(calibration_state.caution_flags)
    validation_reasons.extend(calibration_state.validation_reasons)

    execution_state = _resolve_execution_runtime_projection_assessment_state(
        execution_runtime_projection
    )
    caution_flags.extend(execution_state.caution_flags)

    multiple_testing_state = _resolve_multiple_testing_assessment_state(multiple_testing_review)
    pending_dimensions.extend(multiple_testing_state.pending_dimensions)
    caution_flags.extend(multiple_testing_state.caution_flags)
    validation_reasons.extend(multiple_testing_state.validation_reasons)

    return LocalLabArtifactProofAssessment(
        correlation_id=correlation_id,
        export_dir=export_dir,
        run_id=run_id,
        **_build_core_assessment_payload(core_state),
        ready_for_vps_import=not validation_reasons,
        validation_reasons=tuple(dict.fromkeys(validation_reasons)),
        pending_dimensions=tuple(dict.fromkeys(pending_dimensions)),
        caution_flags=tuple(dict.fromkeys(caution_flags)),
        **_build_calibration_assessment_payload(calibration_state),
        **_build_execution_runtime_projection_payload(execution_state),
        **_build_multiple_testing_assessment_payload(multiple_testing_state),
    )


__all__ = [
    "LocalLabArtifactProofAssessment",
    "build_local_lab_artifact_proof_assessment",
]
