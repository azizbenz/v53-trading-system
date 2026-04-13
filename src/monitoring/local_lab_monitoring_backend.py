"""Typed backend payload adapter for Local IA Lab monitoring surfaces."""

from __future__ import annotations

from monitoring.contracts import LocalLabMonitoringBackendPayload, ObservabilityExport
from monitoring.local_lab_monitoring_projection import LocalLabMonitoringProjection


def build_local_lab_monitoring_backend_payload(
    *,
    projection: LocalLabMonitoringProjection,
    observability_export: ObservabilityExport,
    observability_export_ref: str = "",
) -> LocalLabMonitoringBackendPayload:
    """Normalize Local IA Lab monitoring state into one backend-consumable payload."""

    if observability_export.correlation_id != projection.correlation_id:
        raise ValueError(
            "Local IA Lab observability export correlation_id must match the monitoring projection"
        )

    return LocalLabMonitoringBackendPayload(
        timestamp_ms=observability_export.timestamp_ms,
        correlation_id=projection.correlation_id,
        profile=observability_export.profile,
        runtime_mode=observability_export.runtime_mode,
        status=projection.status,
        detail=projection.detail,
        run_id=projection.run_id,
        export_dir=projection.export_dir,
        dataset_manifest_id=projection.dataset_manifest_id,
        artifact_id=projection.artifact_id,
        selected_pair=projection.selected_pair or "",
        selected_engine_id=projection.selected_engine_id or "",
        release_status=projection.release_status,
        bridge_status=projection.bridge_status,
        promotion_readiness_status=projection.promotion_readiness_status,
        activation_stage=projection.activation_stage,
        normalized_promotion_state=projection.normalized_promotion_state,
        review_state=projection.review_state,
        release_gate_status=projection.release_gate_status,
        semantic_status=projection.semantic_status,
        review_ready=projection.review_ready,
        trade_loss_attribution_ready=projection.trade_loss_attribution_ready,
        walk_forward_review_ready=projection.walk_forward_review_ready,
        artifact_ablation_ready=projection.artifact_ablation_ready,
        artifact_proof_ready=projection.artifact_proof_ready,
        edge_calibration_ready=projection.edge_calibration_ready,
        release_ready_for_shadow=projection.release_ready_for_shadow,
        ready_for_shadow_import_dry_run=projection.ready_for_shadow_import_dry_run,
        scope_count=projection.scope_count,
        scope_ready_count=projection.scope_ready_count,
        scope_blocked_count=projection.scope_blocked_count,
        release_scope_ready_count=projection.release_scope_ready_count,
        release_scope_blocked_count=projection.release_scope_blocked_count,
        loss_surrogate_status=projection.loss_surrogate_status,
        loss_surrogate_ready=projection.loss_surrogate_ready,
        loss_surrogate_scope_count=projection.loss_surrogate_scope_count,
        loss_surrogate_top_scope_slug=projection.loss_surrogate_top_scope_slug,
        loss_surrogate_top_probability=projection.loss_surrogate_top_probability,
        calibration_methods_review_status=projection.calibration_methods_review_status,
        calibration_methods_review_ready=projection.calibration_methods_review_ready,
        calibration_methods_dsr_pass=projection.calibration_methods_dsr_pass,
        calibration_methods_walk_forward_plan_ready=projection.calibration_methods_walk_forward_plan_ready,
        calibration_methods_stationarity_status=projection.calibration_methods_stationarity_status,
        calibration_methods_stationarity_pass=projection.calibration_methods_stationarity_pass,
        execution_review_status=projection.execution_review_status,
        execution_review_ready=projection.execution_review_ready,
        execution_ready_threshold_count=projection.execution_ready_threshold_count,
        execution_partial_threshold_count=projection.execution_partial_threshold_count,
        execution_blocked_threshold_count=projection.execution_blocked_threshold_count,
        multiple_testing_review_status=projection.multiple_testing_review_status,
        multiple_testing_review_ready=projection.multiple_testing_review_ready,
        multiple_testing_correction_required=projection.multiple_testing_correction_required,
        multiple_testing_correction=projection.multiple_testing_correction,
        multiple_testing_family_count=projection.multiple_testing_family_count,
        calibration_normalized_report_status=projection.calibration_normalized_report_status,
        calibration_normalized_report_ready=projection.calibration_normalized_report_ready,
        calibration_normalized_threshold_count=projection.calibration_normalized_threshold_count,
        tail_risk_review_status=projection.tail_risk_review_status,
        tail_risk_review_ready=projection.tail_risk_review_ready,
        tail_risk_ready_breaker_count=projection.tail_risk_ready_breaker_count,
        tail_risk_partial_breaker_count=projection.tail_risk_partial_breaker_count,
        tail_risk_blocked_breaker_count=projection.tail_risk_blocked_breaker_count,
        research_priority_status=projection.research_priority_status,
        research_priority_scope_count=projection.research_priority_scope_count,
        research_priority_top_scope_slug=projection.research_priority_top_scope_slug,
        research_priority_top_score=projection.research_priority_top_score,
        replay_candidate_queue_status=projection.replay_candidate_queue_status,
        replay_candidate_count=projection.replay_candidate_count,
        replay_candidate_ready_count=projection.replay_candidate_ready_count,
        replay_candidate_top_scope_slug=projection.replay_candidate_top_scope_slug,
        replay_ticket_index_status=projection.replay_ticket_index_status,
        replay_ticket_count=projection.replay_ticket_count,
        replay_ticket_ready_count=projection.replay_ticket_ready_count,
        replay_ticket_top_scope_slug=projection.replay_ticket_top_scope_slug,
        replay_dispatch_plan_status=projection.replay_dispatch_plan_status,
        replay_dispatch_ready_count=projection.replay_dispatch_ready_count,
        replay_dispatch_blocked_count=projection.replay_dispatch_blocked_count,
        replay_dispatch_top_ticket_id=projection.replay_dispatch_top_ticket_id,
        observability_sample_count=len(observability_export.samples),
        blocking_reason_count=len(projection.blocking_reasons),
        release_gate_reason_count=len(projection.release_gate_reasons),
        blocking_reasons=projection.blocking_reasons,
        artifact_proof_validation_reasons=projection.artifact_proof_validation_reasons,
        recalibration_blocking_reasons=projection.recalibration_blocking_reasons,
        release_gate_reasons=projection.release_gate_reasons,
        bridge_blocking_reasons=projection.bridge_blocking_reasons,
        observability_export_ref=observability_export_ref,
        scope_matrix_ref=projection.scope_matrix_path or "",
        artifact_release_candidate_ref=projection.artifact_release_candidate_path or "",
        artifact_import_dry_run_bridge_ref=projection.artifact_import_dry_run_bridge_path or "",
        artifact_promotion_readiness_summary_ref=(
            projection.artifact_promotion_readiness_summary_path or ""
        ),
        local_lab_loss_surrogate_ref=projection.local_lab_loss_surrogate_path or "",
        local_lab_calibration_methods_review_ref=(
            projection.local_lab_calibration_methods_review_path or ""
        ),
        local_lab_execution_review_ref=projection.local_lab_execution_review_path or "",
        local_lab_multiple_testing_review_ref=(
            projection.local_lab_multiple_testing_review_path or ""
        ),
        local_lab_tail_risk_review_ref=projection.local_lab_tail_risk_review_path or "",
        local_lab_calibration_normalized_report_ref=(
            projection.local_lab_calibration_normalized_report_path or ""
        ),
        local_lab_research_priority_ref=projection.local_lab_research_priority_path or "",
        local_lab_replay_candidate_queue_ref=projection.local_lab_replay_candidate_queue_path or "",
        local_lab_replay_ticket_index_ref=projection.local_lab_replay_ticket_index_path or "",
        local_lab_replay_dispatch_plan_ref=projection.local_lab_replay_dispatch_plan_path or "",
        local_lab_replay_workflow_manifest_ref=projection.local_lab_replay_workflow_manifest_path or "",
        local_lab_monitoring_bundle_manifest_ref=projection.local_lab_monitoring_bundle_manifest_path or "",
    )


__all__ = ["build_local_lab_monitoring_backend_payload"]
