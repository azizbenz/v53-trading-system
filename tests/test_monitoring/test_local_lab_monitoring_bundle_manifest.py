from __future__ import annotations

from interface_contracts import ProfileId, RuntimeMode
from monitoring.local_lab_monitoring_backend import (
    build_local_lab_monitoring_backend_payload,
)
from monitoring.local_lab_monitoring_projection import LocalLabMonitoringProjection
from monitoring.local_lab_observability import build_local_lab_observability_export
from monitoring.local_lab_ingestion import build_local_lab_monitoring_ingestion_summary
from monitoring.local_lab_monitoring_bundle_manifest import (
    build_local_lab_monitoring_bundle_manifest,
)


def _projection() -> LocalLabMonitoringProjection:
    return LocalLabMonitoringProjection(
        status="warning",
        correlation_id="corr-local-lab-monitoring-manifest",
        run_id="run-local-lab-monitoring-manifest",
        export_dir="E:/lab/export_dir",
        dataset_manifest_id="dataset-local-lab",
        artifact_id="edge_gate_thresholds",
        selected_pair="BTCUSDT",
        selected_engine_id="engine_a",
        detail="Local IA Lab monitoring bundle remains local-only pending dry-run handoff.",
        review_ready=True,
        trade_loss_attribution_ready=True,
        walk_forward_review_ready=True,
        artifact_ablation_ready=True,
        artifact_proof_ready=True,
        edge_calibration_ready=True,
        release_ready_for_shadow=True,
        ready_for_shadow_import_dry_run=False,
        release_status="shadow_candidate",
        bridge_status="pending_governance_inputs",
        promotion_readiness_status="shadow_candidate_pending_dry_run",
        activation_stage="shadow_ready",
        normalized_promotion_state="shadow_candidate",
        review_state="pending",
        release_gate_status="proof_backed_no_recalibration_required",
        semantic_status="source_transport_split",
        calibration_methods_review_status="partial",
        calibration_methods_review_ready=False,
        calibration_methods_dsr_pass=None,
        calibration_methods_walk_forward_plan_ready=False,
        execution_review_status="partial",
        execution_review_ready=False,
        execution_ready_threshold_count=0,
        execution_partial_threshold_count=2,
        execution_blocked_threshold_count=0,
        multiple_testing_review_status="ready",
        multiple_testing_review_ready=True,
        multiple_testing_correction_required=False,
        multiple_testing_correction="not_required_interval_publication",
        multiple_testing_family_count=2,
    )


def test_build_local_lab_monitoring_bundle_manifest_aligns_monitoring_sidecars():
    projection = _projection()
    observability = build_local_lab_observability_export(
        projection=projection,
        profile=ProfileId.COMPLETE,
        runtime_mode=RuntimeMode.LOCAL_REPLAY,
        timestamp_ms=1_800_000_000_000,
    )
    backend_payload = build_local_lab_monitoring_backend_payload(
        projection=projection,
        observability_export=observability,
        observability_export_ref="E:/lab/export_dir/local_lab_observability_export.json",
    )
    ingestion_summary = build_local_lab_monitoring_ingestion_summary(
        backend_payload=backend_payload,
        observability_export=observability,
        backend_payload_ref="E:/lab/export_dir/local_lab_monitoring_backend_payload.json",
        observability_export_ref="E:/lab/export_dir/local_lab_observability_export.json",
        monitoring_bundle_manifest_ref="E:/lab/export_dir/local_lab_monitoring_bundle_manifest.json",
    )

    manifest = build_local_lab_monitoring_bundle_manifest(
        backend_payload=backend_payload,
        backend_payload_path="E:/lab/export_dir/local_lab_monitoring_backend_payload.json",
        observability_export=observability,
        observability_export_path="E:/lab/export_dir/local_lab_observability_export.json",
        ingestion_summary=ingestion_summary,
        ingestion_summary_path="E:/lab/export_dir/local_lab_monitoring_ingestion_summary.json",
        replay_workflow_manifest_path="E:/lab/export_dir/local_lab_replay_workflow_manifest.json",
        replay_workflow_manifest_status="ready",
    )

    assert manifest.correlation_id == "corr-local-lab-monitoring-manifest"
    assert manifest.backend_status == "warning"
    assert manifest.ingestion_ready is True
    assert manifest.observability_sample_count > 0
    assert manifest.calibration_methods_review_status == "partial"
    assert manifest.calibration_methods_review_ready is False
    assert manifest.calibration_methods_dsr_pass is None
    assert manifest.calibration_methods_walk_forward_plan_ready is False
    assert manifest.execution_review_status == "partial"
    assert manifest.execution_review_ready is False
    assert manifest.execution_partial_threshold_count == 2
    assert manifest.multiple_testing_review_status == "ready"
    assert manifest.multiple_testing_review_ready is True
    assert manifest.multiple_testing_correction_required is False
    assert manifest.multiple_testing_family_count == 2
    assert manifest.replay_workflow_manifest_status == "ready"
