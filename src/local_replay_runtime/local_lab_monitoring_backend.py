"""Typed backend payload adapter for Local IA Lab monitoring surfaces."""

from __future__ import annotations

from monitoring.contracts import LocalLabMonitoringBackendPayload, ObservabilityExport

from local_replay_runtime.local_lab_monitoring_projection import LocalLabMonitoringProjection


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
    )


__all__ = ["build_local_lab_monitoring_backend_payload"]
