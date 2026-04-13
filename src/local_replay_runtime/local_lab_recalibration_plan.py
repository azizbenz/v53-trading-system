"""Typed Local IA Lab recalibration planning from governed loss attribution evidence."""

from __future__ import annotations

from collections import Counter

from pydantic import BaseModel, Field

from local_replay_runtime.local_lab_loss_surrogate import LocalLabLossSurrogateReport
from local_replay_runtime.local_lab_scope_matrix import LocalLabScopeAnalysisMatrix
from meta_learning.contracts import TradeLossAttribution, TradeLossAttributionReport


class LocalLabRecalibrationAction(BaseModel, frozen=True):
    """Single bounded recalibration action proposed by the Local IA Lab."""

    action_type: str = Field(..., min_length=1)
    action_scope: str = Field(..., min_length=1)
    affected_scope_count: int = Field(default=0, ge=0)
    linked_failure_modes: tuple[str, ...] = ()
    rationale: tuple[str, ...] = ()
    recommended_threshold_ids: tuple[str, ...] = ()
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    blocking_reasons: tuple[str, ...] = ()


class LocalLabFailureModeAggregate(BaseModel, frozen=True):
    """Aggregated failure mode count across one Local IA Lab analysis bundle."""

    failure_mode: str = Field(..., min_length=1)
    count: int = Field(..., ge=0)


class LocalLabRecalibrationPlan(BaseModel, frozen=True):
    """Future-dashboard-ready recalibration plan derived from loss attribution."""

    correlation_id: str = Field(..., min_length=1)
    export_dir: str = Field(..., min_length=1)
    report_count: int = Field(default=0, ge=0)
    scope_count: int = Field(default=0, ge=0)
    ready_scope_count: int = Field(default=0, ge=0)
    blocked_scope_count: int = Field(default=0, ge=0)
    executed_records: int = Field(default=0, ge=0)
    losing_trade_count: int = Field(default=0, ge=0)
    dominant_failure_modes: tuple[LocalLabFailureModeAggregate, ...] = ()
    recommended_threshold_ids: tuple[str, ...] = ()
    loss_surrogate_status: str = Field(default="not_evaluated", min_length=1)
    loss_surrogate_ready: bool = False
    surrogate_high_risk_scope_count: int = Field(default=0, ge=0)
    surrogate_top_scope_slug: str = ""
    surrogate_top_probability: float = Field(default=0.0, ge=0.0, le=1.0)
    action_count: int = Field(default=0, ge=0)
    calibration_candidate_ready: bool = False
    blocking_reasons: tuple[str, ...] = ()
    actions: tuple[LocalLabRecalibrationAction, ...] = ()


def build_local_lab_recalibration_plan(
    *,
    correlation_id: str,
    export_dir: str,
    loss_reports: tuple[TradeLossAttributionReport, ...],
    scope_matrix: LocalLabScopeAnalysisMatrix | None = None,
    loss_surrogate_report: LocalLabLossSurrogateReport | None = None,
) -> LocalLabRecalibrationPlan:
    """Build a bounded recalibration plan from governed Local IA Lab loss evidence."""

    all_ready = bool(loss_reports) and all(report.attribution_ready for report in loss_reports)
    all_attributions = tuple(
        attribution
        for report in loss_reports
        for attribution in report.attributions
    )
    losses = tuple(
        attribution
        for attribution in all_attributions
        if attribution.attribution_status == "loss"
    )
    failure_mode_counts: Counter[str] = Counter(
        attribution.primary_failure_mode for attribution in losses
    )
    recommended_threshold_ids = tuple(
        sorted(
            {
                threshold_id
                for attribution in losses
                for threshold_id in attribution.recommended_threshold_ids
            }
        )
    )
    surrogate_status = "not_evaluated" if loss_surrogate_report is None else loss_surrogate_report.status
    surrogate_ready = False if loss_surrogate_report is None else loss_surrogate_report.ready
    surrogate_high_risk_scopes = (
        ()
        if loss_surrogate_report is None
        else tuple(
            scope
            for scope in loss_surrogate_report.scopes
            if scope.risk_band in {"elevated_risk", "high_risk"}
        )
    )
    surrogate_top_scope_slug = (
        "" if loss_surrogate_report is None else loss_surrogate_report.highest_risk_scope_slug
    )
    surrogate_top_probability = (
        0.0 if loss_surrogate_report is None else loss_surrogate_report.highest_risk_probability
    )

    blocking_reasons: list[str] = []
    if not all_ready:
        blocking_reasons.append("LOSS_ATTRIBUTION_NOT_READY")
    if not losses:
        blocking_reasons.append("NO_LOSING_TRADES_TO_RECALIBRATE")
    if "trace_coverage" in failure_mode_counts:
        blocking_reasons.append("TRACE_COVERAGE_BLOCKS_RECALIBRATION")
    if scope_matrix is not None and scope_matrix.blocked_scope_count > 0:
        blocking_reasons.append("SCOPE_MATRIX_NOT_FULLY_READY")
    if losses and not recommended_threshold_ids:
        blocking_reasons.append("NO_THRESHOLD_RECOMMENDATION_FROM_LOSS_ATTRIBUTION")

    actions: list[LocalLabRecalibrationAction] = []
    threshold_recommendations = tuple(
        attribution for attribution in losses if attribution.recommended_threshold_ids
    )
    if threshold_recommendations:
        action_blockers: list[str] = []
        if "trace_coverage" in failure_mode_counts:
            action_blockers.append("TRACE_COVERAGE_BLOCKS_RECALIBRATION")
        if scope_matrix is not None and scope_matrix.blocked_scope_count > 0:
            action_blockers.append("SCOPE_MATRIX_NOT_FULLY_READY")
        actions.append(
            LocalLabRecalibrationAction(
                action_type="recalibrate_edge_gate",
                action_scope=_aggregate_action_scope(threshold_recommendations),
                affected_scope_count=_affected_scope_count(threshold_recommendations),
                linked_failure_modes=tuple(
                    sorted({attribution.primary_failure_mode for attribution in threshold_recommendations})
                ),
                rationale=(
                    "loss_attribution_recommended_edge_threshold_adjustment",
                    "local_lab_should_backtest_recalibrated_edge_gate_before_artifact_export",
                ),
                recommended_threshold_ids=recommended_threshold_ids,
                confidence=round(
                    sum(attribution.confidence for attribution in threshold_recommendations)
                    / len(threshold_recommendations),
                    6,
                ),
                blocking_reasons=tuple(dict.fromkeys(action_blockers)),
            )
        )
    if failure_mode_counts.get("sterilization", 0) > 0:
        sterilization_attributions = tuple(
            attribution for attribution in losses if attribution.primary_failure_mode == "sterilization"
        )
        actions.append(
            LocalLabRecalibrationAction(
                action_type="review_scope_sterilization",
                action_scope=_aggregate_action_scope(sterilization_attributions),
                affected_scope_count=_affected_scope_count(sterilization_attributions),
                linked_failure_modes=("sterilization",),
                rationale=(
                    "size_and_execution_pressure_destroyed_realized_value",
                    "scope_requires_human_review_before_runtime_promotion",
                ),
                confidence=round(
                    sum(attribution.confidence for attribution in sterilization_attributions)
                    / len(sterilization_attributions),
                    6,
                ),
            )
        )
    if failure_mode_counts.get("trace_coverage", 0) > 0:
        trace_attributions = tuple(
            attribution for attribution in losses if attribution.primary_failure_mode == "trace_coverage"
        )
        actions.append(
            LocalLabRecalibrationAction(
                action_type="improve_trace_capture",
                action_scope=_aggregate_action_scope(trace_attributions),
                affected_scope_count=_affected_scope_count(trace_attributions),
                linked_failure_modes=("trace_coverage",),
                rationale=(
                    "diagnostic_trace_is_incomplete",
                    "do_not_publish_recalibration_until_trace_quality_improves",
                ),
                confidence=round(
                    sum(attribution.confidence for attribution in trace_attributions)
                    / len(trace_attributions),
                    6,
                ),
                blocking_reasons=("TRACE_COVERAGE_BLOCKS_RECALIBRATION",),
            )
        )
    if surrogate_ready and surrogate_high_risk_scopes:
        replay_blockers: list[str] = []
        if "trace_coverage" in failure_mode_counts:
            replay_blockers.append("TRACE_COVERAGE_BLOCKS_RECALIBRATION")
        actions.append(
            LocalLabRecalibrationAction(
                action_type="replay_surrogate_high_risk_scope",
                action_scope=(
                    surrogate_top_scope_slug
                    if len(surrogate_high_risk_scopes) == 1
                    else "multi_scope"
                ),
                affected_scope_count=len({scope.scope_slug for scope in surrogate_high_risk_scopes}),
                linked_failure_modes=("modeled_loss_risk",),
                rationale=(
                    "transparent_local_loss_surrogate_identified_elevated_loss_pressure",
                    "run_bounded_replay_before_publishing_new_thresholds",
                ),
                confidence=round(surrogate_top_probability, 6),
                blocking_reasons=tuple(dict.fromkeys(replay_blockers)),
            )
        )

    calibration_candidate_ready = (
        all_ready
        and bool(recommended_threshold_ids)
        and "trace_coverage" not in failure_mode_counts
        and (scope_matrix is None or scope_matrix.blocked_scope_count == 0)
    )
    aggregates = tuple(
        LocalLabFailureModeAggregate(failure_mode=failure_mode, count=count)
        for failure_mode, count in sorted(
            failure_mode_counts.items(),
            key=lambda item: (-item[1], item[0]),
        )
    )
    return LocalLabRecalibrationPlan(
        correlation_id=correlation_id,
        export_dir=export_dir,
        report_count=len(loss_reports),
        scope_count=0 if scope_matrix is None else scope_matrix.scope_count,
        ready_scope_count=0 if scope_matrix is None else scope_matrix.ready_scope_count,
        blocked_scope_count=0 if scope_matrix is None else scope_matrix.blocked_scope_count,
        executed_records=sum(report.executed_records for report in loss_reports),
        losing_trade_count=sum(report.losing_trade_count for report in loss_reports),
        dominant_failure_modes=aggregates,
        recommended_threshold_ids=recommended_threshold_ids,
        loss_surrogate_status=surrogate_status,
        loss_surrogate_ready=surrogate_ready,
        surrogate_high_risk_scope_count=len(surrogate_high_risk_scopes),
        surrogate_top_scope_slug=surrogate_top_scope_slug,
        surrogate_top_probability=surrogate_top_probability,
        action_count=len(actions),
        calibration_candidate_ready=calibration_candidate_ready,
        blocking_reasons=tuple(dict.fromkeys(blocking_reasons)),
        actions=tuple(actions),
    )


def _aggregate_action_scope(attributions: tuple[TradeLossAttribution, ...]) -> str:
    scopes = sorted({attribution.action_scope for attribution in attributions if attribution.action_scope})
    if not scopes:
        return "unknown_scope"
    if len(scopes) == 1:
        return scopes[0]
    return "multi_scope"


def _affected_scope_count(attributions: tuple[TradeLossAttribution, ...]) -> int:
    return len({attribution.action_scope for attribution in attributions if attribution.action_scope})


__all__ = [
    "LocalLabFailureModeAggregate",
    "LocalLabRecalibrationAction",
    "LocalLabRecalibrationPlan",
    "build_local_lab_recalibration_plan",
]
