from __future__ import annotations

import pytest

from interface_contracts import ProfileId, RuntimeMode
from local_replay_runtime.local_lab_monitoring_backend import (
    build_local_lab_monitoring_backend_payload,
)
from local_replay_runtime.local_lab_monitoring_projection import LocalLabMonitoringProjection
from local_replay_runtime.local_lab_observability import build_local_lab_observability_export
from monitoring.local_lab_ingestion import build_local_lab_monitoring_ingestion_summary


def _projection() -> LocalLabMonitoringProjection:
    return LocalLabMonitoringProjection(
        status="healthy",
        correlation_id="corr-local-lab-ingestion",
        run_id="run-local-lab-ingestion",
        export_dir="E:/lab/export_dir",
        dataset_manifest_id="dataset-local-lab",
        artifact_id="edge_gate_thresholds",
        selected_pair="BTCUSDT",
        selected_engine_id="engine_a",
        detail="Local IA Lab dry-run handoff is ready for SHADOW import review.",
        review_ready=True,
        trade_loss_attribution_ready=True,
        walk_forward_review_ready=True,
        artifact_ablation_ready=True,
        artifact_proof_ready=True,
        edge_calibration_ready=True,
        release_ready_for_shadow=True,
        ready_for_shadow_import_dry_run=True,
        release_status="shadow_candidate",
        bridge_status="dry_run_ready",
        promotion_readiness_status="shadow_candidate_dry_run_ready",
        activation_stage="shadow_ready",
        normalized_promotion_state="shadow_candidate",
        review_state="pending",
        release_gate_status="proof_backed_no_recalibration_required",
        semantic_status="transport_packet_with_source_artifact_refs",
        scope_count=2,
        scope_ready_count=2,
        scope_blocked_count=0,
        release_scope_ready_count=2,
        release_scope_blocked_count=0,
        blocking_reasons=(),
        artifact_proof_validation_reasons=(),
        recalibration_blocking_reasons=("NO_LOSING_TRADES_TO_RECALIBRATE",),
        release_gate_reasons=("PROOF_GATE_PASSED", "RECALIBRATION_NOT_REQUIRED"),
        bridge_blocking_reasons=(),
    )


def test_local_lab_monitoring_ingestion_summary_is_ready_when_pair_is_coherent():
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
        observability_export_ref="E:/lab/local_lab_observability_export.json",
    )

    summary = build_local_lab_monitoring_ingestion_summary(
        backend_payload=backend_payload,
        observability_export=observability,
        backend_payload_ref="E:/lab/local_lab_monitoring_backend_payload.json",
        observability_export_ref="E:/lab/local_lab_observability_export.json",
    )

    assert summary.ingestion_ready is True
    assert summary.projection_status == "healthy"
    assert summary.sample_count == len(observability.samples)
    assert summary.text_payload_present is True
    assert summary.backend_payload_ref.endswith("local_lab_monitoring_backend_payload.json")


def test_local_lab_monitoring_ingestion_summary_rejects_misaligned_runtime_mode():
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
    ).model_copy(update={"runtime_mode": RuntimeMode.SHADOW})

    with pytest.raises(
        ValueError,
        match="Local IA Lab monitoring ingestion requires matching runtime_mode",
    ):
        build_local_lab_monitoring_ingestion_summary(
            backend_payload=backend_payload,
            observability_export=observability,
        )
