"""Judgment and comparison helpers for the governed Shadow runtime."""

from __future__ import annotations

from typing import Mapping

from monitoring import EngineMetrics, TechnicalDashboardPayload
from protocols.contracts import (
    ShadowComparison,
    ShadowComponentAssessment,
    ShadowEngineJudgment,
    ShadowEngineJudgmentSummary,
    ShadowEngineReport,
    ShadowInput,
    ShadowReportArtifact,
    ShadowRunSummary,
)
from protocols.enums import (
    ShadowComponentKind,
    ShadowComponentVerdict,
    ShadowComparisonStatus,
    ShadowDivergenceSeverity,
)
from protocols.shadow_runtime_portfolio import (
    _engine_physics_pressure,
    _shadow_payload_engines,
    derive_shadow_portfolio_judgment,
)
from protocols.shadow_runtime_shared import _REQUIRED_SHADOW_ENGINES


def _shadow_engine_verdict(
    *,
    assessment: ShadowComponentAssessment | None,
    report: ShadowEngineReport | None,
    payload_engine: EngineMetrics | None,
    shadow_summary: ShadowRunSummary,
    report_complete: bool,
    ce_expected: float | None,
    physics_pressure_state: str,
) -> tuple[str, str]:
    if assessment is not None and assessment.verdict == ShadowComponentVerdict.DORMANT:
        return "dormant", "component marked dormant by the Shadow component verdicts"
    if report is None or assessment is None:
        return "shadow-only", "Shadow evidence is incomplete for this engine"
    if (
        shadow_summary.shadow_days_completed < shadow_summary.shadow_required_days
        or not shadow_summary.shadow_report_ready
        or not report_complete
    ):
        return (
            "shadow-only",
            f"Shadow gate incomplete: {shadow_summary.shadow_days_completed}/"
            f"{shadow_summary.shadow_required_days} day(s), report_complete={report_complete}",
        )
    if payload_engine is not None and (
        payload_engine.hard_blocked
        or payload_engine.phantom_trade
        or payload_engine.portfolio_verdict_code.startswith("rejected_")
        or payload_engine.selection_outcome_code == "rejected_portfolio"
    ):
        return (
            "rewrite-required",
            "risk, phantom-trade, or portfolio compatibility rejected this engine in the governed payload",
        )
    if physics_pressure_state == "critical":
        return (
            "rewrite-required",
            "execution fragility, toxicity, survivability, or micro-friction stayed above the governed rewrite threshold",
        )
    if physics_pressure_state == "elevated":
        return (
            "shadow-only",
            "execution physics pressure remained elevated, so Shadow must continue before governed promotion",
        )
    if payload_engine is not None and (
        payload_engine.selection_outcome_code == "rejected_ranking"
        or payload_engine.risk_decision_severity == "critical"
        or payload_engine.scoring_final_size_multiplier <= 0.1
    ):
        return (
            "shadow-only",
            "engine remained selection-limited or size-capped in the governed payload",
        )
    if (
        report.economic_pass_rate <= 0.5
        or report.marginal_edge <= 0.0
        or report.conflict_rate >= 0.5
        or (ce_expected is not None and ce_expected <= 0.0)
    ):
        return (
            "rewrite-required",
            "economic pass-rate, CE, marginal edge, or conflict-rate stayed below the supervised threshold",
        )
    return "promotable", "Shadow gate complete with positive supervised engine metrics"


def _build_shadow_engine_judgment(
    engine_id: str,
    *,
    assessment: ShadowComponentAssessment | None,
    report: ShadowEngineReport | None,
    payload_engine: EngineMetrics | None,
    shadow_summary: ShadowRunSummary,
    report_complete: bool,
    ce_expected_by_engine: Mapping[str, float],
) -> ShadowEngineJudgment:
    component_verdict = assessment.verdict.value if assessment is not None else "missing"
    ce_expected = ce_expected_by_engine.get(engine_id)
    if ce_expected is None and payload_engine is not None:
        ce_expected = payload_engine.ce_expected
    physics_pressure_state = _engine_physics_pressure(payload_engine)
    fragility_score = payload_engine.physics.fragility_score if payload_engine is not None else None
    toxicity_score = payload_engine.physics.toxicity_score if payload_engine is not None else None
    execution_survivability_score = (
        payload_engine.physics.execution_survivability_score if payload_engine is not None else None
    )
    micro_friction_score = (
        payload_engine.physics.micro_friction_score if payload_engine is not None else None
    )
    judgment_verdict, rationale = _shadow_engine_verdict(
        assessment=assessment,
        report=report,
        payload_engine=payload_engine,
        shadow_summary=shadow_summary,
        report_complete=report_complete,
        ce_expected=ce_expected,
        physics_pressure_state=physics_pressure_state,
    )
    return ShadowEngineJudgment(
        engine_id=engine_id,
        component_verdict=component_verdict,
        judgment_verdict=judgment_verdict,
        useful_frequency=report.useful_frequency if report is not None else 0.0,
        ce_expected=ce_expected,
        estimated_cost_bps=report.estimated_cost_bps if report is not None else 0.0,
        edge_net=report.edge_net if report is not None else 0.0,
        economic_pass_rate=report.economic_pass_rate if report is not None else 0.0,
        conflict_rate=report.conflict_rate if report is not None else 0.0,
        marginal_edge=report.marginal_edge if report is not None else 0.0,
        redundancy_score=report.conflict_rate if report is not None else 0.0,
        portfolio_contribution=report.marginal_edge if report is not None else 0.0,
        final_size_multiplier=(
            payload_engine.scoring_final_size_multiplier if payload_engine is not None else None
        ),
        selection_outcome_code=payload_engine.selection_outcome_code if payload_engine is not None else "",
        portfolio_verdict_code=payload_engine.portfolio_verdict_code if payload_engine is not None else "",
        phantom_trade=payload_engine.phantom_trade if payload_engine is not None else False,
        hard_blocked=payload_engine.hard_blocked if payload_engine is not None else False,
        risk_decision_severity=payload_engine.risk_decision_severity if payload_engine is not None else "",
        physics_pressure_state=physics_pressure_state,  # type: ignore[arg-type]
        fragility_score=fragility_score,
        toxicity_score=toxicity_score,
        execution_survivability_score=execution_survivability_score,
        micro_friction_score=micro_friction_score,
        observations=report.observations if report is not None else 0,
        rationale=rationale,
        evidence_summary=assessment.evidence_summary if assessment is not None else "",
    )


def derive_shadow_engine_judgment_summary(
    shadow_summary: ShadowRunSummary,
    shadow_report: ShadowReportArtifact | None,
    *,
    ce_by_engine: Mapping[str, float] | None = None,
    shadow_payload: TechnicalDashboardPayload | None = None,
) -> ShadowEngineJudgmentSummary:
    """Derive per-engine promotion judgments from the governed Shadow artifacts."""

    if shadow_report is None:
        return ShadowEngineJudgmentSummary(
            source_shadow_run_id=shadow_summary.run_id,
            source_shadow_days_completed=shadow_summary.shadow_days_completed,
            source_shadow_required_days=shadow_summary.shadow_required_days,
            judgments=(),
        )

    assessments = {
        assessment.component_id: assessment
        for assessment in shadow_summary.component_assessments
        if assessment.component_kind == ShadowComponentKind.ENGINE
    }
    reports = {report.engine_id: report for report in shadow_report.inter_engine_comparison}
    payload_engines = _shadow_payload_engines(shadow_payload)
    ce_expected_by_engine = dict(ce_by_engine or {})
    judgments = tuple(
        _build_shadow_engine_judgment(
            engine_id,
            assessment=assessments.get(engine_id),
            report=reports.get(engine_id),
            payload_engine=payload_engines.get(engine_id),
            shadow_summary=shadow_summary,
            report_complete=shadow_report.is_complete,
            ce_expected_by_engine=ce_expected_by_engine,
        )
        for engine_id in sorted(_REQUIRED_SHADOW_ENGINES)
    )
    return ShadowEngineJudgmentSummary(
        source_report_id=shadow_report.report_id,
        source_shadow_run_id=shadow_summary.run_id,
        source_shadow_days_completed=shadow_summary.shadow_days_completed,
        source_shadow_required_days=shadow_summary.shadow_required_days,
        portfolio_judgment=derive_shadow_portfolio_judgment(
            shadow_payload,
            shadow_report=shadow_report,
            judgments=judgments,
        ),
        judgments=judgments,
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


__all__ = [
    "derive_shadow_engine_judgment_summary",
    "compare_shadow_candidate",
]
