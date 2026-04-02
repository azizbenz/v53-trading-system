"""Minimal real Build-11 Shadow orchestration.

HARD STATEMENT §0.6: 30 consecutive shadow days required before promotion.
"""

from __future__ import annotations

from pathlib import Path

from interface_contracts import ProfileId, PromotionState, ReviewState, RuntimeMode
from local_replay_runtime import LocalReplayRuntimeEvidence
from monitoring import TechnicalDashboardPayload
from protocols.contracts import (
    ShadowComparison,
    ShadowComponentAssessment,
    ShadowDecision,
    ShadowInput,
    ShadowRuntimeEvidence,
    ShadowRunSummary,
    ShadowTruthSet,
    ShadowValidationSet,
)
from protocols.enums import (
    ShadowComponentKind,
    ShadowComparisonStatus,
    ShadowDivergenceSeverity,
    ShadowRunState,
    ShadowVerdict,
)
from protocols.errors import ShadowInputError


_REQUIRED_SHADOW_ENGINES = frozenset({"engine_a", "engine_b"})
_REQUIRED_BUILD14_COMPONENTS = frozenset(
    {
        "build14_microstructure",
        "build14_regime",
        "build14_covariance",
        "build14_risk_contribution",
        "build14_edge_diversity",
    }
)
_RUNTIME_EVIDENCE_ACCEPTED_SOURCES = frozenset({"live_websocket", "recorded_replay"})


def _runtime_evidence_summary(
    *,
    runtime_data_source: str,
    runtime_feature_bridge_ready: bool,
    runtime_parity_diagnostics_ready: bool,
    runtime_replay_metrics_ready: bool,
    runtime_replay_dtr_ready: bool,
    runtime_event_loop_ready: bool,
    runtime_config_loaded: bool,
    runtime_shadow_dtr_persisted: bool,
    runtime_continuous_hours: float,
) -> str:
    return (
        f"source={runtime_data_source or 'unknown'} / "
        f"feature_bridge={'yes' if runtime_feature_bridge_ready else 'no'} / "
        f"parity={'yes' if runtime_parity_diagnostics_ready else 'no'} / "
        f"metrics={'yes' if runtime_replay_metrics_ready else 'no'} / "
        f"replay_dtr={'yes' if runtime_replay_dtr_ready else 'no'} / "
        f"event_loop={'yes' if runtime_event_loop_ready else 'no'} / "
        f"config={'yes' if runtime_config_loaded else 'no'} / "
        f"shadow_dtr={'yes' if runtime_shadow_dtr_persisted else 'no'} / "
        f"hours={runtime_continuous_hours:.1f}"
    )


def build_shadow_runtime_evidence(
    *,
    local_replay_evidence: LocalReplayRuntimeEvidence | None = None,
    runtime_data_source: str = "unknown",
    runtime_feature_bridge_ready: bool = False,
    runtime_parity_diagnostics_ready: bool = False,
    runtime_replay_metrics_ready: bool = False,
    runtime_replay_dtr_ready: bool = False,
    runtime_event_loop_ready: bool = False,
    runtime_config_loaded: bool = False,
    runtime_shadow_dtr_persisted: bool = False,
    runtime_continuous_hours: float = 0.0,
) -> ShadowRuntimeEvidence:
    """Combine replay-usefulness proof with Shadow runtime proof into one evidence object."""

    resolved_data_source = runtime_data_source
    if (
        resolved_data_source == "unknown"
        and local_replay_evidence is not None
        and local_replay_evidence.data_source != "unknown"
    ):
        resolved_data_source = local_replay_evidence.data_source

    feature_bridge_ready = (
        local_replay_evidence.feature_bridge_ready
        if local_replay_evidence is not None
        else runtime_feature_bridge_ready
    )
    parity_diagnostics_ready = (
        local_replay_evidence.parity_diagnostics_ready
        if local_replay_evidence is not None
        else runtime_parity_diagnostics_ready
    )
    replay_metrics_ready = (
        local_replay_evidence.replay_metrics_ready
        if local_replay_evidence is not None
        else runtime_replay_metrics_ready
    )
    replay_dtr_ready = (
        local_replay_evidence.replay_dtr_ready
        if local_replay_evidence is not None
        else runtime_replay_dtr_ready
    )

    return ShadowRuntimeEvidence(
        data_source=resolved_data_source,  # type: ignore[arg-type]
        feature_bridge_ready=feature_bridge_ready,
        parity_diagnostics_ready=parity_diagnostics_ready,
        replay_metrics_ready=replay_metrics_ready,
        replay_dtr_ready=replay_dtr_ready,
        event_loop_ready=runtime_event_loop_ready,
        config_loaded=runtime_config_loaded,
        shadow_dtr_persisted=runtime_shadow_dtr_persisted,
        continuous_hours=runtime_continuous_hours,
        evidence_summary=_runtime_evidence_summary(
            runtime_data_source=resolved_data_source,
            runtime_feature_bridge_ready=feature_bridge_ready,
            runtime_parity_diagnostics_ready=parity_diagnostics_ready,
            runtime_replay_metrics_ready=replay_metrics_ready,
            runtime_replay_dtr_ready=replay_dtr_ready,
            runtime_event_loop_ready=runtime_event_loop_ready,
            runtime_config_loaded=runtime_config_loaded,
            runtime_shadow_dtr_persisted=runtime_shadow_dtr_persisted,
            runtime_continuous_hours=runtime_continuous_hours,
        ),
    )


def _validate_shadow_payload_scope(
    payload: TechnicalDashboardPayload,
    *,
    role: str,
) -> None:
    if payload.profile != ProfileId.LIGHT:
        raise ShadowInputError(
            f"Build-11 Shadow {role} payload must stay on profile=LIGHT"
        )
    if payload.runtime_mode != RuntimeMode.SHADOW:
        raise ShadowInputError(
            f"Build-11 Shadow {role} payload must stay on runtime_mode=SHADOW"
        )


def build_shadow_input_from_payloads(
    baseline_payload: TechnicalDashboardPayload,
    candidate_payload: TechnicalDashboardPayload,
    *,
    truth_ref: str,
    validation_ref: str,
    component_assessments: tuple[ShadowComponentAssessment, ...],
    shadow_days_completed: int,
    shadow_report_ready: bool,
    inter_engine_comparison_ready: bool,
    build14_contribution_ready: bool,
    runtime_evidence: ShadowRuntimeEvidence | None = None,
    runtime_data_source: str = "unknown",
    runtime_feature_bridge_ready: bool = False,
    runtime_parity_diagnostics_ready: bool = False,
    runtime_replay_metrics_ready: bool = False,
    runtime_replay_dtr_ready: bool = False,
    runtime_event_loop_ready: bool = False,
    runtime_config_loaded: bool = False,
    runtime_shadow_dtr_persisted: bool = False,
    runtime_continuous_hours: float = 0.0,
    max_allowed_dtr_coverage_drop: float = 0.05,
    max_allowed_cra_increase: float = 0.10,
    max_allowed_break_even_drift_scope_increase: int = 0,
    max_allowed_edge_degraded_delta: int = 0,
    max_allowed_ce_net_drop: float = 0.0005,
    max_allowed_alert_count_increase: int = 1,
    max_allowed_queue_backlog_increase: int = 25,
) -> ShadowInput:
    """Build governed Shadow input from normalized Build-10 payloads."""

    _validate_shadow_payload_scope(baseline_payload, role="baseline")
    _validate_shadow_payload_scope(candidate_payload, role="candidate")

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
    resolved_runtime_evidence = runtime_evidence or build_shadow_runtime_evidence(
        runtime_data_source=runtime_data_source,
        runtime_feature_bridge_ready=runtime_feature_bridge_ready,
        runtime_parity_diagnostics_ready=runtime_parity_diagnostics_ready,
        runtime_replay_metrics_ready=runtime_replay_metrics_ready,
        runtime_replay_dtr_ready=runtime_replay_dtr_ready,
        runtime_event_loop_ready=runtime_event_loop_ready,
        runtime_config_loaded=runtime_config_loaded,
        runtime_shadow_dtr_persisted=runtime_shadow_dtr_persisted,
        runtime_continuous_hours=runtime_continuous_hours,
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
        runtime_data_source=resolved_runtime_evidence.data_source,
        runtime_feature_bridge_ready=resolved_runtime_evidence.feature_bridge_ready,
        runtime_parity_diagnostics_ready=resolved_runtime_evidence.parity_diagnostics_ready,
        runtime_replay_metrics_ready=resolved_runtime_evidence.replay_metrics_ready,
        runtime_replay_dtr_ready=resolved_runtime_evidence.replay_dtr_ready,
        runtime_event_loop_ready=resolved_runtime_evidence.event_loop_ready,
        runtime_config_loaded=resolved_runtime_evidence.config_loaded,
        runtime_shadow_dtr_persisted=resolved_runtime_evidence.shadow_dtr_persisted,
        runtime_continuous_hours=resolved_runtime_evidence.continuous_hours,
        runtime_evidence_summary=resolved_runtime_evidence.evidence_summary,
        build9x_diagnostics_count=candidate_payload.build9x.diagnostics_count,
        open_hypotheses=candidate_payload.build9x.open_hypotheses,
        replay_candidate_count=candidate_payload.build9x.replay_candidate_count,
        review_export_ready=candidate_payload.build9x.review_export_ready,
        active_engines=candidate_payload.system.active_engines,
        build14_status=candidate_payload.system.build14_status,
        shadow_days_completed=shadow_days_completed,
        shadow_required_days=30,
        shadow_report_ready=shadow_report_ready,
        inter_engine_comparison_ready=inter_engine_comparison_ready,
        build14_contribution_ready=build14_contribution_ready,
        component_assessments=component_assessments,
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


def _missing_shadow_components(
    assessments: tuple[ShadowComponentAssessment, ...],
) -> tuple[str, ...]:
    seen_engines = {
        assessment.component_id
        for assessment in assessments
        if assessment.component_kind == ShadowComponentKind.ENGINE
    }
    seen_build14 = {
        assessment.component_id
        for assessment in assessments
        if assessment.component_kind == ShadowComponentKind.BUILD14_ENABLER
    }
    missing = sorted(
        (_REQUIRED_SHADOW_ENGINES - seen_engines)
        | (_REQUIRED_BUILD14_COMPONENTS - seen_build14)
    )
    return tuple(missing)


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
    normalized_validation_status = validation.import_validation_status.strip().casefold()
    missing_engines = tuple(
        sorted(_REQUIRED_SHADOW_ENGINES - set(validation.active_engines))
    )
    missing_components = _missing_shadow_components(validation.component_assessments)
    normalized_build14_status = validation.build14_status.strip().casefold()
    runtime_evidence_ready = (
        validation.runtime_data_source in _RUNTIME_EVIDENCE_ACCEPTED_SOURCES
        and validation.runtime_feature_bridge_ready
        and validation.runtime_parity_diagnostics_ready
        and validation.runtime_replay_metrics_ready
        and validation.runtime_replay_dtr_ready
        and validation.runtime_event_loop_ready
        and validation.runtime_config_loaded
        and validation.runtime_shadow_dtr_persisted
        and validation.runtime_continuous_hours >= 24.0
    )

    if not validation.accepted_import:
        structurally_blocked = True
        blocking_reasons.append("candidate import must be accepted before Shadow")
    if normalized_validation_status != "accepted":
        structurally_blocked = True
        blocking_reasons.append(
            "candidate import_validation_status must be an accepted status before Shadow"
        )
    if not validation.import_artifact_id or validation.import_artifact_id == "none":
        structurally_blocked = True
        blocking_reasons.append("candidate import artifact_id is required")
    if not validation.import_lineage_version or validation.import_lineage_version == "n/a":
        structurally_blocked = True
        blocking_reasons.append("candidate lineage_version is required")
    if validation.import_rejection_reasons:
        structurally_blocked = True
    blocking_reasons.extend(
        f"import gate: {reason}" for reason in validation.import_rejection_reasons
    )
    if validation.runtime_data_source not in _RUNTIME_EVIDENCE_ACCEPTED_SOURCES:
        structurally_blocked = True
        blocking_reasons.append(
            "Build-11 Shadow requires runtime evidence from live_websocket or recorded_replay"
        )
    if not validation.runtime_feature_bridge_ready:
        structurally_blocked = True
        blocking_reasons.append(
            "Build-11 Shadow requires feature bridge evidence (prices -> features -> engines)"
        )
    if not validation.runtime_parity_diagnostics_ready:
        structurally_blocked = True
        blocking_reasons.append(
            "Build-11 Shadow requires parity diagnostics evidence"
        )
    if not validation.runtime_replay_metrics_ready:
        structurally_blocked = True
        blocking_reasons.append(
            "Build-11 Shadow requires replay metrics evidence"
        )
    if not validation.runtime_replay_dtr_ready:
        structurally_blocked = True
        blocking_reasons.append(
            "Build-11 Shadow requires replay DTR evidence"
        )
    if not validation.runtime_event_loop_ready:
        structurally_blocked = True
        blocking_reasons.append(
            "Build-11 Shadow requires event loop evidence"
        )
    if not validation.runtime_config_loaded:
        structurally_blocked = True
        blocking_reasons.append(
            "Build-11 Shadow requires official config loading evidence"
        )
    if not validation.runtime_shadow_dtr_persisted:
        structurally_blocked = True
        blocking_reasons.append(
            "Build-11 Shadow requires persisted shadow DTR evidence"
        )
    if validation.runtime_continuous_hours < 24.0:
        structurally_blocked = True
        blocking_reasons.append(
            "Build-11 Shadow requires at least 24h of real runtime evidence before the verdict gate"
        )
    if validation.shadow_days_completed < validation.shadow_required_days:
        structurally_blocked = True
        blocking_reasons.append(
            "Build-11 Shadow requires 30 consecutive days before the verdict gate"
        )
    if not validation.shadow_report_ready:
        structurally_blocked = True
        blocking_reasons.append(
            "Build-11 Shadow requires a complete shadow report before the verdict gate"
        )
    if not validation.inter_engine_comparison_ready:
        structurally_blocked = True
        blocking_reasons.append(
            "Build-11 Shadow requires an inter-engine A/B comparison in the report"
        )
    if not validation.build14_contribution_ready:
        structurally_blocked = True
        blocking_reasons.append(
            "Build-11 Shadow requires Build-14 contribution evidence in the report"
        )
    if missing_engines:
        structurally_blocked = True
        blocking_reasons.append(
            "Build-11 Shadow requires A/B active in Shadow: "
            + ", ".join(missing_engines)
        )
    if normalized_build14_status == "planned":
        structurally_blocked = True
        blocking_reasons.append(
            "Build-11 Shadow requires Build-14 to be active, not planned"
        )
    if missing_components:
        structurally_blocked = True
        blocking_reasons.append(
            "Build-11 Shadow requires component verdicts for A/B and all Build-14 enablers: "
            + ", ".join(missing_components)
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
        runtime_data_source=validation.runtime_data_source,
        runtime_feature_bridge_ready=validation.runtime_feature_bridge_ready,
        runtime_parity_diagnostics_ready=validation.runtime_parity_diagnostics_ready,
        runtime_replay_metrics_ready=validation.runtime_replay_metrics_ready,
        runtime_replay_dtr_ready=validation.runtime_replay_dtr_ready,
        runtime_event_loop_ready=validation.runtime_event_loop_ready,
        runtime_config_loaded=validation.runtime_config_loaded,
        runtime_shadow_dtr_persisted=validation.runtime_shadow_dtr_persisted,
        runtime_continuous_hours=validation.runtime_continuous_hours,
        runtime_evidence_ready=runtime_evidence_ready,
        runtime_evidence_summary=validation.runtime_evidence_summary,
        build9x_diagnostics_count=validation.build9x_diagnostics_count,
        open_hypotheses=validation.open_hypotheses,
        replay_candidate_count=validation.replay_candidate_count,
        review_export_ready=validation.review_export_ready,
        active_engines=validation.active_engines,
        build14_status=validation.build14_status,
        shadow_days_completed=validation.shadow_days_completed,
        shadow_required_days=validation.shadow_required_days,
        shadow_report_ready=validation.shadow_report_ready,
        inter_engine_comparison_ready=validation.inter_engine_comparison_ready,
        build14_contribution_ready=validation.build14_contribution_ready,
        component_assessments=validation.component_assessments,
    )


def check_shadow_30j_gate(
    state_dir: Path,
    profile: str = "light",
) -> tuple[bool, dict]:
    """HARD STATEMENT §0.6: check if 30 consecutive shadow days are met.

    Args:
        state_dir: Directory containing persisted shadow counter state.
        profile: "light" or "complete".

    Returns:
        (gate_passed, report_dict)
    """
    from protocols.shadow_day_counter import ShadowDayCounter, ShadowProfile

    shadow_profile = ShadowProfile(profile)
    counter = ShadowDayCounter(state_dir=state_dir, profile=shadow_profile)
    report = counter.generate_report()
    gate_passed = counter.is_promotion_ready() and bool(
        report.get("shadow_report_ready", False)
    )
    return gate_passed, report


__all__ = [
    "build_shadow_runtime_evidence",
    "build_shadow_input_from_payloads",
    "compare_shadow_candidate",
    "run_shadow_validation",
    "check_shadow_30j_gate",
]
