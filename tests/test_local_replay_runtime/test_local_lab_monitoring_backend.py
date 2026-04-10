from __future__ import annotations

import pytest

from interface_contracts import ProfileId, RuntimeMode
from local_replay_runtime.local_lab_monitoring_backend import (
    build_local_lab_monitoring_backend_payload,
)
from local_replay_runtime.local_lab_monitoring_projection import LocalLabMonitoringProjection
from local_replay_runtime.local_lab_observability import build_local_lab_observability_export


def _projection() -> LocalLabMonitoringProjection:
    return LocalLabMonitoringProjection(
        status="warning",
        correlation_id="corr-local-lab-backend",
        run_id="run-local-lab-backend",
        export_dir="E:/lab/export_dir",
        dataset_manifest_id="dataset-local-lab",
        artifact_id="edge_gate_thresholds",
        selected_pair="BTCUSDT",
        selected_engine_id="engine_a",
        detail="Local IA Lab release candidate is proof-backed locally, but dry-run stays pending.",
        review_ready=True,
        trade_loss_attribution_ready=True,
        walk_forward_review_ready=False,
        artifact_ablation_ready=True,
        artifact_proof_ready=True,
        edge_calibration_ready=True,
        release_ready_for_shadow=True,
        ready_for_shadow_import_dry_run=False,
        release_status="shadow_candidate",
        bridge_status="pending_governance_inputs",
        promotion_readiness_status="shadow_candidate_pending_dry_run",
        activation_stage="replay_only",
        normalized_promotion_state="replay_only",
        review_state="pending_review",
        release_gate_status="proof_gate_ready",
        semantic_status="source_transport_split",
        scope_count=2,
        scope_ready_count=2,
        scope_blocked_count=0,
        release_scope_ready_count=1,
        release_scope_blocked_count=1,
        blocking_reasons=("TRAINING_END_REQUIRED",),
        artifact_proof_validation_reasons=("PROOF_WALK_FORWARD_REQUIRED",),
        recalibration_blocking_reasons=(),
        release_gate_reasons=("RECALIBRATION_NOT_REQUIRED",),
        bridge_blocking_reasons=("TRAINING_END_REQUIRED",),
        scope_matrix_path="E:/lab/local_lab_scope_matrix.json",
        artifact_release_candidate_path="E:/lab/artifact_release_candidate.json",
        artifact_import_dry_run_bridge_path="E:/lab/artifact_import_dry_run_bridge.json",
        artifact_promotion_readiness_summary_path="E:/lab/artifact_promotion_readiness_summary.json",
    )


def test_local_lab_monitoring_backend_payload_projects_backend_facts():
    projection = _projection()
    observability = build_local_lab_observability_export(
        projection=projection,
        profile=ProfileId.COMPLETE,
        runtime_mode=RuntimeMode.LOCAL_REPLAY,
        timestamp_ms=1_800_000_000_000,
    )

    payload = build_local_lab_monitoring_backend_payload(
        projection=projection,
        observability_export=observability,
        observability_export_ref="E:/lab/local_lab_observability_export.json",
    )

    assert payload.status == "warning"
    assert payload.profile == ProfileId.COMPLETE
    assert payload.runtime_mode == RuntimeMode.LOCAL_REPLAY
    assert payload.release_ready_for_shadow is True
    assert payload.ready_for_shadow_import_dry_run is False
    assert payload.observability_sample_count == len(observability.samples)
    assert payload.blocking_reason_count == 1
    assert payload.release_gate_reason_count == 1
    assert payload.observability_export_ref.endswith("local_lab_observability_export.json")
    assert payload.scope_matrix_ref.endswith("local_lab_scope_matrix.json")


def test_local_lab_monitoring_backend_payload_rejects_misaligned_observability():
    projection = _projection()
    observability = build_local_lab_observability_export(
        projection=projection.model_copy(update={"correlation_id": "corr-other"}),
        profile=ProfileId.COMPLETE,
        runtime_mode=RuntimeMode.LOCAL_REPLAY,
        timestamp_ms=1_800_000_000_000,
    )

    with pytest.raises(
        ValueError,
        match="Local IA Lab observability export correlation_id must match the monitoring projection",
    ):
        build_local_lab_monitoring_backend_payload(
            projection=projection,
            observability_export=observability,
        )
