from __future__ import annotations

from pathlib import Path

from interface_contracts import ProfileId, RuntimeMode
from interface_contracts.atomic_io import atomic_write_json
from monitoring.local_lab_monitoring_backend import (
    build_local_lab_monitoring_backend_payload,
)
from monitoring.local_lab_monitoring_projection import LocalLabMonitoringProjection
from monitoring.local_lab_observability import build_local_lab_observability_export
from monitoring.local_lab_bundle_discovery import (
    discover_local_lab_monitoring_bundles,
    load_latest_local_lab_monitoring_bundle,
)
from monitoring.local_lab_ingestion import build_local_lab_monitoring_ingestion_summary
from monitoring.local_lab_monitoring_bundle_manifest import build_local_lab_monitoring_bundle_manifest


def _scratch_dir(name: str) -> Path:
    from tests.support_paths import make_repo_scratch_dir

    return make_repo_scratch_dir("pytest-local-lab-bundle-discovery", name)


def _write_bundle(output_dir: Path, *, correlation_id: str, timestamp_ms: int) -> None:
    projection = LocalLabMonitoringProjection(
        status="warning",
        correlation_id=correlation_id,
        run_id=f"run-{correlation_id}",
        export_dir="E:/lab/export_dir",
        dataset_manifest_id="dataset-local-lab",
        artifact_id="edge_gate_thresholds",
        selected_pair="BTCUSDT",
        selected_engine_id="engine_a",
        detail="Local IA Lab monitoring bundle is ready for discovery.",
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
        multiple_testing_family_count=2,
        local_lab_monitoring_bundle_manifest_path=str(output_dir / "local_lab_monitoring_bundle_manifest.json"),
    )
    observability = build_local_lab_observability_export(
        projection=projection,
        profile=ProfileId.COMPLETE,
        runtime_mode=RuntimeMode.LOCAL_REPLAY,
        timestamp_ms=timestamp_ms,
    )
    backend_payload = build_local_lab_monitoring_backend_payload(
        projection=projection,
        observability_export=observability,
        observability_export_ref=str(output_dir / "local_lab_observability_export.json"),
    )
    ingestion_summary = build_local_lab_monitoring_ingestion_summary(
        backend_payload=backend_payload,
        observability_export=observability,
        backend_payload_ref=str(output_dir / "local_lab_monitoring_backend_payload.json"),
        observability_export_ref=str(output_dir / "local_lab_observability_export.json"),
        monitoring_bundle_manifest_ref=str(output_dir / "local_lab_monitoring_bundle_manifest.json"),
    )
    manifest = build_local_lab_monitoring_bundle_manifest(
        backend_payload=backend_payload,
        backend_payload_path=str(output_dir / "local_lab_monitoring_backend_payload.json"),
        observability_export=observability,
        observability_export_path=str(output_dir / "local_lab_observability_export.json"),
        ingestion_summary=ingestion_summary,
        ingestion_summary_path=str(output_dir / "local_lab_monitoring_ingestion_summary.json"),
    )
    atomic_write_json(output_dir / "local_lab_monitoring_backend_payload.json", backend_payload.model_dump(mode="json"), indent=2)
    atomic_write_json(output_dir / "local_lab_observability_export.json", observability.model_dump(mode="json"), indent=2)
    atomic_write_json(output_dir / "local_lab_monitoring_ingestion_summary.json", ingestion_summary.model_dump(mode="json"), indent=2)
    atomic_write_json(output_dir / "local_lab_monitoring_bundle_manifest.json", manifest.model_dump(mode="json"), indent=2)


def test_discover_local_lab_monitoring_bundles_sorts_latest_first():
    scratch = _scratch_dir("discover")
    older = scratch / "older"
    newer = scratch / "newer"
    older.mkdir(parents=True, exist_ok=True)
    newer.mkdir(parents=True, exist_ok=True)
    _write_bundle(older, correlation_id="corr-older", timestamp_ms=1_800_000_000_000)
    _write_bundle(newer, correlation_id="corr-newer", timestamp_ms=1_800_000_000_100)

    discovery = discover_local_lab_monitoring_bundles(scratch)

    assert discovery.bundle_count == 2
    assert discovery.latest_correlation_id == "corr-newer"
    assert discovery.bundles[0].correlation_id == "corr-newer"
    assert discovery.bundles[1].correlation_id == "corr-older"
    assert discovery.bundles[0].calibration_methods_review_status == "partial"
    assert discovery.bundles[0].calibration_methods_review_ready is False
    assert discovery.bundles[0].execution_review_status == "partial"
    assert discovery.bundles[0].execution_partial_threshold_count == 2
    assert discovery.bundles[0].multiple_testing_review_status == "ready"
    assert discovery.bundles[0].multiple_testing_review_ready is True


def test_load_latest_local_lab_monitoring_bundle_reads_latest_bundle():
    scratch = _scratch_dir("load_latest")
    older = scratch / "older"
    newer = scratch / "newer"
    older.mkdir(parents=True, exist_ok=True)
    newer.mkdir(parents=True, exist_ok=True)
    _write_bundle(older, correlation_id="corr-old", timestamp_ms=1_800_000_000_000)
    _write_bundle(newer, correlation_id="corr-new", timestamp_ms=1_800_000_000_200)

    bundle = load_latest_local_lab_monitoring_bundle(scratch)

    assert bundle.manifest.correlation_id == "corr-new"
    assert bundle.backend_payload.correlation_id == "corr-new"
    assert bundle.manifest.calibration_methods_review_status == "partial"
    assert bundle.manifest.execution_review_status == "partial"
    assert bundle.manifest.multiple_testing_review_status == "ready"
