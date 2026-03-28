"""Minimal real Build-11 Shadow orchestration."""

from __future__ import annotations

from interface_contracts import PromotionState, ReviewState
from monitoring import TechnicalDashboardPayload
from protocols.contracts import (
    ShadowComparison,
    ShadowDecision,
    ShadowInput,
    ShadowRunSummary,
    ShadowTruthSet,
    ShadowValidationSet,
)
from protocols.enums import (
    ShadowComparisonStatus,
    ShadowDivergenceSeverity,
    ShadowRunState,
    ShadowVerdict,
)


def build_shadow_input_from_payloads(
    baseline_payload: TechnicalDashboardPayload,
    candidate_payload: TechnicalDashboardPayload,
    *,
    truth_ref: str,
    validation_ref: str,
    max_allowed_dtr_coverage_drop: float = 0.05,
    max_allowed_cra_increase: float = 0.10,
    max_allowed_break_even_drift_scope_increase: int = 0,
    max_allowed_edge_degraded_delta: int = 0,
    max_allowed_ce_net_drop: float = 0.0005,
    max_allowed_alert_count_increase: int = 1,
    max_allowed_queue_backlog_increase: int = 25,
) -> ShadowInput:
    """Build governed Shadow input from normalized Build-10 payloads."""

    truth_set = ShadowTruthSet(
        truth_ref=truth_ref,
        dtr_coverage=baseline_payload.build9_meta.dtr_coverage,
        cra_sterilization_rate=baseline_payload.build9_meta.cra_sterilization_rate,
        break_even_drift_scope_count=len(baseline_payload.build9_meta.break_even_drift_scopes),
        edge_degraded_count=baseline_payload.build9_meta.edge_degraded_count,
        ce_net=baseline_payload.portfolio.ce_net,
        active_alert_count=baseline_payload.alerts.active_alert_count,
        queue_backlog=baseline_payload.alerts.queue_backlog,
    )
    validation_set = ShadowValidationSet(
        validation_ref=validation_ref,
        dtr_coverage=candidate_payload.build9_meta.dtr_coverage,
        cra_sterilization_rate=candidate_payload.build9_meta.cra_sterilization_rate,
        break_even_drift_scope_count=len(candidate_payload.build9_meta.break_even_drift_scopes),
        edge_degraded_count=candidate_payload.build9_meta.edge_degraded_count,
        ce_net=candidate_payload.portfolio.ce_net,
        active_alert_count=candidate_payload.alerts.active_alert_count,
        queue_backlog=candidate_payload.alerts.queue_backlog,
        accepted_import=candidate_payload.replay_import.validation_status == "accepted",
        import_validation_status=candidate_payload.replay_import.validation_status,
        import_artifact_id=candidate_payload.replay_import.artifact_id,
        import_lineage_version=candidate_payload.replay_import.lineage_version,
        import_rejection_reasons=candidate_payload.replay_import.rejection_reasons,
        build9x_diagnostics_count=candidate_payload.build9x.diagnostics_count,
        open_hypotheses=candidate_payload.build9x.open_hypotheses,
        replay_candidate_count=candidate_payload.build9x.replay_candidate_count,
        review_export_ready=candidate_payload.build9x.review_export_ready,
    )
    return ShadowInput(
        correlation_id=candidate_payload.correlation_id,
        profile=candidate_payload.profile,
        runtime_mode=candidate_payload.runtime_mode,
        truth_set=truth_set,
        validation_set=validation_set,
        max_allowed_dtr_coverage_drop=max_allowed_dtr_coverage_drop,
        max_allowed_cra_increase=max_allowed_cra_increase,
        max_allowed_break_even_drift_scope_increase=max_allowed_break_even_drift_scope_increase,
        max_allowed_edge_degraded_delta=max_allowed_edge_degraded_delta,
        max_allowed_ce_net_drop=max_allowed_ce_net_drop,
        max_allowed_alert_count_increase=max_allowed_alert_count_increase,
        max_allowed_queue_backlog_increase=max_allowed_queue_backlog_increase,
    )


def _comparison(
    shadow_input: ShadowInput,
    *,
    metric_name: str,
    baseline_value: float,
    candidate_value: float,
    threshold: float,
    higher_is_better: bool,
) -> ShadowComparison:
    if higher_is_better:
        delta = max(0.0, baseline_value - candidate_value)
    else:
        delta = max(0.0, candidate_value - baseline_value)

    if delta == 0.0:
        status = ShadowComparisonStatus.MATCHING
        severity = ShadowDivergenceSeverity.INFO
        blocking = False
        summary = f"{metric_name} matched or improved the baseline"
    elif delta <= threshold:
        status = ShadowComparisonStatus.DIVERGENT
        severity = ShadowDivergenceSeverity.WARNING
        blocking = False
        summary = f"{metric_name} diverged within the allowed Shadow threshold"
    else:
        status = ShadowComparisonStatus.BLOCKING
        severity = ShadowDivergenceSeverity.CRITICAL
        blocking = True
        summary = f"{metric_name} exceeded the allowed Shadow threshold"

    return ShadowComparison(
        comparison_id=f"{shadow_input.correlation_id}:{metric_name}",
        metric_name=metric_name,
        baseline_value=baseline_value,
        candidate_value=candidate_value,
        delta=round(delta, 6),
        threshold=threshold,
        status=status,
        severity=severity,
        blocking=blocking,
        summary=summary,
    )


def compare_shadow_candidate(shadow_input: ShadowInput) -> tuple[ShadowComparison, ...]:
    """Compare candidate Shadow measurements against the baseline truth set."""

    truth = shadow_input.truth_set
    validation = shadow_input.validation_set
    return (
        _comparison(
            shadow_input,
            metric_name="dtr_coverage_drop",
            baseline_value=truth.dtr_coverage,
            candidate_value=validation.dtr_coverage,
            threshold=shadow_input.max_allowed_dtr_coverage_drop,
            higher_is_better=True,
        ),
        _comparison(
            shadow_input,
            metric_name="cra_sterilization_increase",
            baseline_value=truth.cra_sterilization_rate,
            candidate_value=validation.cra_sterilization_rate,
            threshold=shadow_input.max_allowed_cra_increase,
            higher_is_better=False,
        ),
        _comparison(
            shadow_input,
            metric_name="break_even_drift_scope_increase",
            baseline_value=float(truth.break_even_drift_scope_count),
            candidate_value=float(validation.break_even_drift_scope_count),
            threshold=float(shadow_input.max_allowed_break_even_drift_scope_increase),
            higher_is_better=False,
        ),
        _comparison(
            shadow_input,
            metric_name="edge_degraded_delta",
            baseline_value=float(truth.edge_degraded_count),
            candidate_value=float(validation.edge_degraded_count),
            threshold=float(shadow_input.max_allowed_edge_degraded_delta),
            higher_is_better=False,
        ),
        _comparison(
            shadow_input,
            metric_name="ce_net_drop",
            baseline_value=truth.ce_net,
            candidate_value=validation.ce_net,
            threshold=shadow_input.max_allowed_ce_net_drop,
            higher_is_better=True,
        ),
        _comparison(
            shadow_input,
            metric_name="active_alert_count_increase",
            baseline_value=float(truth.active_alert_count),
            candidate_value=float(validation.active_alert_count),
            threshold=float(shadow_input.max_allowed_alert_count_increase),
            higher_is_better=False,
        ),
        _comparison(
            shadow_input,
            metric_name="queue_backlog_increase",
            baseline_value=float(truth.queue_backlog),
            candidate_value=float(validation.queue_backlog),
            threshold=float(shadow_input.max_allowed_queue_backlog_increase),
            higher_is_better=False,
        ),
    )


def run_shadow_validation(
    shadow_input: ShadowInput,
    *,
    run_id: str | None = None,
) -> ShadowRunSummary:
    """Run the minimal real Build-11 Shadow gating logic."""

    comparisons = compare_shadow_candidate(shadow_input)
    validation = shadow_input.validation_set
    blocking_reasons: list[str] = []
    structurally_blocked = False

    if not validation.accepted_import:
        structurally_blocked = True
        blocking_reasons.append("candidate import must be accepted before Shadow")
    if not validation.import_artifact_id or validation.import_artifact_id == "none":
        structurally_blocked = True
        blocking_reasons.append("candidate import artifact_id is required")
    if not validation.import_lineage_version or validation.import_lineage_version == "n/a":
        structurally_blocked = True
        blocking_reasons.append("candidate lineage_version is required")
    blocking_reasons.extend(
        f"import gate: {reason}" for reason in validation.import_rejection_reasons
    )

    blocking_reasons.extend(
        comparison.summary for comparison in comparisons if comparison.blocking
    )

    manual_review_required = (
        validation.build9x_diagnostics_count > 0
        or validation.open_hypotheses > 0
        or validation.replay_candidate_count > 0
    )

    if structurally_blocked:
        decision = ShadowDecision(
            accepted=False,
            verdict=ShadowVerdict.BLOCKED,
            normalized_promotion_state=PromotionState.REPLAY_ONLY,
            review_state=ReviewState.NEEDS_REVISION,
            blocking_reasons=tuple(blocking_reasons),
            manual_review_required=True,
        )
        run_state = ShadowRunState.BLOCKED
    elif any(comparison.blocking for comparison in comparisons):
        decision = ShadowDecision(
            accepted=False,
            verdict=ShadowVerdict.REJECTED,
            normalized_promotion_state=PromotionState.REPLAY_ONLY,
            review_state=ReviewState.NEEDS_REVISION,
            blocking_reasons=tuple(blocking_reasons),
            manual_review_required=True,
        )
        run_state = ShadowRunState.COMPLETED
    elif manual_review_required and not validation.review_export_ready:
        decision = ShadowDecision(
            accepted=False,
            verdict=ShadowVerdict.NEEDS_REVIEW,
            normalized_promotion_state=PromotionState.REPLAY_ONLY,
            review_state=ReviewState.NEEDS_REVISION,
            blocking_reasons=("Build-9X review export must be ready before accepting Shadow",),
            manual_review_required=True,
        )
        run_state = ShadowRunState.COMPLETED
    else:
        decision = ShadowDecision(
            accepted=True,
            verdict=ShadowVerdict.ACCEPTED,
            normalized_promotion_state=PromotionState.SHADOW_CANDIDATE,
            review_state=ReviewState.PENDING,
            blocking_reasons=(),
            manual_review_required=manual_review_required,
        )
        run_state = ShadowRunState.COMPLETED

    return ShadowRunSummary(
        run_id=run_id or f"{shadow_input.correlation_id}:shadow_run",
        correlation_id=shadow_input.correlation_id,
        run_state=run_state,
        truth_set_ref=shadow_input.truth_set.truth_ref,
        validation_set_ref=shadow_input.validation_set.validation_ref,
        comparisons=comparisons,
        decision=decision,
        import_artifact_id=validation.import_artifact_id,
        import_lineage_version=validation.import_lineage_version,
        build9x_diagnostics_count=validation.build9x_diagnostics_count,
        open_hypotheses=validation.open_hypotheses,
        replay_candidate_count=validation.replay_candidate_count,
        review_export_ready=validation.review_export_ready,
    )


__all__ = [
    "build_shadow_input_from_payloads",
    "compare_shadow_candidate",
    "run_shadow_validation",
]
