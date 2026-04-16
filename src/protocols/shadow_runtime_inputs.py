"""Input and runtime evidence builders for the governed Shadow runtime."""

from __future__ import annotations

from interface_contracts import ProfileId, RuntimeMode
from local_replay_runtime import LocalReplayRuntimeEvidence
from monitoring import TechnicalDashboardPayload
from protocols.contracts import (
    ShadowComponentAssessment,
    ShadowInput,
    ShadowRuntimeEvidence,
    ShadowTruthSet,
    ShadowValidationSet,
)
from protocols.errors import ShadowInputError


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
    if payload.profile != ProfileId.COMPLETE:
        raise ShadowInputError(
            f"Build-11 Shadow {role} payload must stay on profile=COMPLETE"
        )
    if payload.runtime_mode != RuntimeMode.SHADOW:
        raise ShadowInputError(
            f"Build-11 Shadow {role} payload must stay on runtime_mode=SHADOW"
        )


def _build_shadow_truth_set(
    baseline_payload: TechnicalDashboardPayload,
    *,
    truth_ref: str,
) -> ShadowTruthSet:
    return ShadowTruthSet(
        truth_ref=truth_ref,
        dtr_coverage=baseline_payload.build9_meta.dtr_coverage,
        cra_sterilization_rate=baseline_payload.build9_meta.cra_sterilization_rate,
        break_even_drift_scope_count=len(baseline_payload.build9_meta.break_even_drift_scopes),
        edge_degraded_count=baseline_payload.build9_meta.edge_degraded_count,
        ce_net=baseline_payload.portfolio.ce_net,
        active_alert_count=baseline_payload.alerts.active_alert_count,
        queue_backlog=baseline_payload.alerts.queue_backlog,
    )


def _resolve_shadow_runtime_evidence(
    runtime_evidence: ShadowRuntimeEvidence | None,
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
) -> ShadowRuntimeEvidence:
    return runtime_evidence or build_shadow_runtime_evidence(
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


def _build_shadow_validation_set(
    candidate_payload: TechnicalDashboardPayload,
    *,
    validation_ref: str,
    component_assessments: tuple[ShadowComponentAssessment, ...],
    shadow_days_completed: int,
    shadow_report_ready: bool,
    inter_engine_comparison_ready: bool,
    build14_contribution_ready: bool,
    runtime_evidence: ShadowRuntimeEvidence,
) -> ShadowValidationSet:
    build9_meta = candidate_payload.build9_meta
    build9x = candidate_payload.build9x
    replay_import = candidate_payload.replay_import
    alerts = candidate_payload.alerts
    portfolio = candidate_payload.portfolio
    system = candidate_payload.system
    return ShadowValidationSet(
        validation_ref=validation_ref,
        dtr_coverage=build9_meta.dtr_coverage,
        cra_sterilization_rate=build9_meta.cra_sterilization_rate,
        break_even_drift_scope_count=len(build9_meta.break_even_drift_scopes),
        edge_degraded_count=build9_meta.edge_degraded_count,
        ce_net=portfolio.ce_net,
        active_alert_count=alerts.active_alert_count,
        queue_backlog=alerts.queue_backlog,
        accepted_import=replay_import.validation_status == "accepted",
        import_validation_status=replay_import.validation_status,
        import_artifact_id=replay_import.artifact_id,
        import_exported_from=replay_import.exported_from,
        import_lineage_version=replay_import.lineage_version,
        import_source_profile=replay_import.source_profile,
        import_review_state=replay_import.review_state,
        import_rejection_reasons=replay_import.rejection_reasons,
        import_dataset_ref=replay_import.dataset_ref,
        import_clock_ref=replay_import.clock_ref,
        import_activation_stage=replay_import.activation_stage,
        import_health_state=replay_import.health_state,
        import_compatibility_status=replay_import.compatibility_status,
        import_compatibility_reasons=replay_import.compatibility_reasons,
        import_feature_lineage_required=replay_import.feature_lineage_required,
        import_feature_lineage_present=replay_import.feature_lineage_present,
        import_feature_lineage_status=replay_import.feature_lineage_status,
        import_feature_lineage_reasons=replay_import.feature_lineage_reasons,
        import_transform_whitelist_required=replay_import.transform_whitelist_required,
        import_transform_whitelist_present=replay_import.transform_whitelist_present,
        import_transform_whitelist_status=replay_import.transform_whitelist_status,
        import_transform_whitelist_reasons=replay_import.transform_whitelist_reasons,
        import_signature_check_status=replay_import.signature_check_status,
        import_signature_check_reasons=replay_import.signature_check_reasons,
        import_conflict_resolution_mode=replay_import.conflict_resolution_mode,
        import_conflict_hard_veto_action=replay_import.conflict_hard_veto_action,
        import_conflict_score_aggregation_mode=replay_import.conflict_score_aggregation_mode,
        import_conflict_size_reduce_mode=replay_import.conflict_size_reduce_mode,
        import_conflict_rank_adjust_mode=replay_import.conflict_rank_adjust_mode,
        import_conflict_additive_soft_boosts_allowed=replay_import.conflict_additive_soft_boosts_allowed,
        import_conflict_additive_soft_reduces_allowed=replay_import.conflict_additive_soft_reduces_allowed,
        import_registry_atomicity_mode=replay_import.registry_atomicity_mode,
        import_registry_concurrency_model=replay_import.registry_concurrency_model,
        import_registry_publish_requires_atomic_replace=replay_import.registry_publish_requires_atomic_replace,
        import_registry_publish_requires_fsync=replay_import.registry_publish_requires_fsync,
        import_registry_rollback_to_last_known_good=replay_import.registry_rollback_to_last_known_good,
        import_payload_ref_count=replay_import.payload_ref_count,
        import_payload_bundle_present=replay_import.payload_bundle_present,
        import_review_export_ref=replay_import.review_export_ref,
        import_feature_bridge_ref=replay_import.feature_bridge_ref,
        import_parity_diagnostics_ref=replay_import.parity_diagnostics_ref,
        import_replay_metrics_ref=replay_import.replay_metrics_ref,
        import_replay_dtr_ref=replay_import.replay_dtr_ref,
        runtime_data_source=runtime_evidence.data_source,
        runtime_feature_bridge_ready=runtime_evidence.feature_bridge_ready,
        runtime_parity_diagnostics_ready=runtime_evidence.parity_diagnostics_ready,
        runtime_replay_metrics_ready=runtime_evidence.replay_metrics_ready,
        runtime_replay_dtr_ready=runtime_evidence.replay_dtr_ready,
        runtime_event_loop_ready=runtime_evidence.event_loop_ready,
        runtime_config_loaded=runtime_evidence.config_loaded,
        runtime_shadow_dtr_persisted=runtime_evidence.shadow_dtr_persisted,
        runtime_continuous_hours=runtime_evidence.continuous_hours,
        runtime_evidence_summary=runtime_evidence.evidence_summary,
        build9x_diagnostics_count=build9x.diagnostics_count,
        open_hypotheses=build9x.open_hypotheses,
        replay_candidate_count=build9x.replay_candidate_count,
        review_export_ready=build9x.review_export_ready,
        active_engines=system.active_engines,
        build14_status=system.build14_status,
        shadow_days_completed=shadow_days_completed,
        shadow_required_days=30,
        shadow_report_ready=shadow_report_ready,
        inter_engine_comparison_ready=inter_engine_comparison_ready,
        build14_contribution_ready=build14_contribution_ready,
        component_assessments=component_assessments,
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
    truth_set = _build_shadow_truth_set(baseline_payload, truth_ref=truth_ref)
    resolved_runtime_evidence = _resolve_shadow_runtime_evidence(
        runtime_evidence,
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
    validation_set = _build_shadow_validation_set(
        candidate_payload,
        validation_ref=validation_ref,
        component_assessments=component_assessments,
        shadow_days_completed=shadow_days_completed,
        shadow_report_ready=shadow_report_ready,
        inter_engine_comparison_ready=inter_engine_comparison_ready,
        build14_contribution_ready=build14_contribution_ready,
        runtime_evidence=resolved_runtime_evidence,
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


__all__ = [
    "build_shadow_runtime_evidence",
    "build_shadow_input_from_payloads",
]
