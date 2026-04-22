from __future__ import annotations

from pathlib import Path

from interface_contracts import ProfileId, RuntimeMode
from interface_contracts.atomic_io import atomic_write_json
from monitoring.local_lab_monitoring_backend import (
    build_local_lab_monitoring_backend_payload,
)
from monitoring.local_lab_monitoring_projection import LocalLabMonitoringProjection
from monitoring.local_lab_observability import build_local_lab_observability_export
from monitoring.local_lab_bundle_discovery import discover_local_lab_monitoring_bundles
from monitoring.local_lab_ingestion import build_local_lab_monitoring_ingestion_summary
from monitoring.local_lab_monitoring_bundle_manifest import build_local_lab_monitoring_bundle_manifest
from monitoring.local_lab_monitoring_feed import (
    build_local_lab_monitoring_feed,
    build_local_lab_monitoring_feed_from_root,
)


def _scratch_dir(name: str) -> Path:
    from tests.support_paths import make_repo_scratch_dir

    return make_repo_scratch_dir("pytest-local-lab-monitoring-feed", name)


def _write_bundle(
    output_dir: Path,
    *,
    correlation_id: str,
    timestamp_ms: int,
    backend_status: str,
    calibration_status: str,
    calibration_ready: bool,
    calibration_dsr_pass: bool | None,
    calibration_walk_forward_ready: bool,
    multiple_testing_status: str,
    multiple_testing_ready: bool,
    multiple_testing_required: bool,
    multiple_testing_family_count: int,
    execution_status: str = "partial",
    execution_ready: bool = False,
    execution_ready_threshold_count: int = 0,
    execution_partial_threshold_count: int = 2,
    execution_blocked_threshold_count: int = 0,
) -> None:
    projection = LocalLabMonitoringProjection(
        status=backend_status,
        correlation_id=correlation_id,
        run_id=f"run-{correlation_id}",
        export_dir="E:/lab/export_dir",
        dataset_manifest_id="dataset-local-lab",
        artifact_id="edge_gate_thresholds",
        selected_pair="BTCUSDT",
        selected_engine_id="engine_a",
        detail="Local IA Lab monitoring feed test bundle.",
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
        calibration_methods_review_status=calibration_status,
        calibration_methods_review_ready=calibration_ready,
        calibration_methods_dsr_pass=calibration_dsr_pass,
        calibration_methods_walk_forward_plan_ready=calibration_walk_forward_ready,
        execution_review_status=execution_status,
        execution_review_ready=execution_ready,
        execution_ready_threshold_count=execution_ready_threshold_count,
        execution_partial_threshold_count=execution_partial_threshold_count,
        execution_blocked_threshold_count=execution_blocked_threshold_count,
        multiple_testing_review_status=multiple_testing_status,
        multiple_testing_review_ready=multiple_testing_ready,
        multiple_testing_correction_required=multiple_testing_required,
        multiple_testing_family_count=multiple_testing_family_count,
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


def test_build_local_lab_monitoring_feed_summarizes_discovered_bundles():
    scratch = _scratch_dir("feed")
    older = scratch / "older"
    newer = scratch / "newer"
    older.mkdir(parents=True, exist_ok=True)
    newer.mkdir(parents=True, exist_ok=True)
    _write_bundle(
        older,
        correlation_id="corr-older",
        timestamp_ms=1_800_000_000_000,
        backend_status="warning",
        calibration_status="partial",
        calibration_ready=False,
        calibration_dsr_pass=None,
        calibration_walk_forward_ready=False,
        multiple_testing_status="ready",
        multiple_testing_ready=True,
        multiple_testing_required=False,
        multiple_testing_family_count=2,
    )
    _write_bundle(
        newer,
        correlation_id="corr-newer",
        timestamp_ms=1_800_000_000_100,
        backend_status="info",
        calibration_status="ready",
        calibration_ready=True,
        calibration_dsr_pass=True,
        calibration_walk_forward_ready=True,
        multiple_testing_status="partial",
        multiple_testing_ready=False,
        multiple_testing_required=True,
        multiple_testing_family_count=2,
    )

    feed = build_local_lab_monitoring_feed(discover_local_lab_monitoring_bundles(scratch))

    assert feed.bundle_count == 2
    assert feed.latest_correlation_id == "corr-newer"
    assert feed.warning_bundle_count == 1
    assert feed.info_bundle_count == 1
    assert feed.ready_bundle_count == 2
    assert feed.calibration_ready_bundle_count == 1
    assert feed.calibration_partial_bundle_count == 1
    assert feed.calibration_blocked_bundle_count == 0
    assert feed.execution_ready_bundle_count == 0
    assert feed.execution_partial_bundle_count == 2
    assert feed.execution_blocked_bundle_count == 0
    assert feed.multiple_testing_ready_bundle_count == 1
    assert feed.multiple_testing_partial_bundle_count == 1
    assert feed.multiple_testing_blocked_bundle_count == 0
    assert feed.items[0].multiple_testing_review_status == "partial"
    assert feed.items[1].multiple_testing_review_status == "ready"
    assert feed.items[0].calibration_methods_review_status == "ready"
    assert feed.items[1].calibration_methods_review_status == "partial"
    assert feed.items[0].execution_review_status == "partial"


def test_build_local_lab_monitoring_feed_from_root_discovers_latest_bundle():
    scratch = _scratch_dir("feed_from_root")
    older = scratch / "older"
    newer = scratch / "newer"
    older.mkdir(parents=True, exist_ok=True)
    newer.mkdir(parents=True, exist_ok=True)
    _write_bundle(
        older,
        correlation_id="corr-old",
        timestamp_ms=1_800_000_000_000,
        backend_status="warning",
        calibration_status="blocked",
        calibration_ready=False,
        calibration_dsr_pass=False,
        calibration_walk_forward_ready=True,
        multiple_testing_status="blocked",
        multiple_testing_ready=False,
        multiple_testing_required=True,
        multiple_testing_family_count=3,
    )
    _write_bundle(
        newer,
        correlation_id="corr-new",
        timestamp_ms=1_800_000_000_200,
        backend_status="critical",
        calibration_status="ready",
        calibration_ready=True,
        calibration_dsr_pass=True,
        calibration_walk_forward_ready=True,
        multiple_testing_status="ready",
        multiple_testing_ready=True,
        multiple_testing_required=False,
        multiple_testing_family_count=2,
    )

    feed = build_local_lab_monitoring_feed_from_root(str(scratch))

    assert feed.latest_correlation_id == "corr-new"
    assert feed.critical_bundle_count == 1
    assert feed.calibration_ready_bundle_count == 1
    assert feed.calibration_blocked_bundle_count == 1
    assert feed.execution_partial_bundle_count == 2
    assert feed.multiple_testing_ready_bundle_count == 1
    assert feed.multiple_testing_blocked_bundle_count == 1
