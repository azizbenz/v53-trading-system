from __future__ import annotations

from pathlib import Path

import pytest

from interface_contracts import ProfileId, RuntimeMode
from interface_contracts.atomic_io import atomic_write_json
from local_replay_runtime.local_lab_monitoring_backend import (
    build_local_lab_monitoring_backend_payload,
)
from local_replay_runtime.local_lab_monitoring_projection import LocalLabMonitoringProjection
from local_replay_runtime.local_lab_observability import build_local_lab_observability_export
from monitoring.local_lab_bundle_loader import load_local_lab_monitoring_bundle
from monitoring.local_lab_ingestion import build_local_lab_monitoring_ingestion_summary


def _scratch_dir(name: str) -> Path:
    repo_root = Path(__file__).resolve().parents[2]
    return repo_root / "build" / "pytest-local-lab-bundle-loader" / name


def _projection() -> LocalLabMonitoringProjection:
    return LocalLabMonitoringProjection(
        status="warning",
        correlation_id="corr-local-lab-bundle",
        run_id="run-local-lab-bundle",
        export_dir="E:/lab/export_dir",
        dataset_manifest_id="dataset-local-lab",
        artifact_id="edge_gate_thresholds",
        selected_pair="BTCUSDT",
        selected_engine_id="engine_a",
        detail="Local IA Lab release candidate is proof-backed locally, but dry-run stays pending.",
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
        scope_count=2,
        scope_ready_count=2,
        scope_blocked_count=0,
        release_scope_ready_count=1,
        release_scope_blocked_count=1,
        blocking_reasons=("TRAINING_END_REQUIRED",),
        artifact_proof_validation_reasons=(),
        recalibration_blocking_reasons=("NO_LOSING_TRADES_TO_RECALIBRATE",),
        release_gate_reasons=("PROOF_GATE_PASSED", "RECALIBRATION_NOT_REQUIRED"),
        bridge_blocking_reasons=("TRAINING_END_REQUIRED",),
    )


def _write_bundle(output_dir: Path) -> None:
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
        observability_export_ref=str(output_dir / "local_lab_observability_export.json"),
    )
    ingestion_summary = build_local_lab_monitoring_ingestion_summary(
        backend_payload=backend_payload,
        observability_export=observability,
        backend_payload_ref=str(output_dir / "local_lab_monitoring_backend_payload.json"),
        observability_export_ref=str(output_dir / "local_lab_observability_export.json"),
    )
    atomic_write_json(
        output_dir / "local_lab_observability_export.json",
        observability.model_dump(mode="json"),
        indent=2,
    )
    atomic_write_json(
        output_dir / "local_lab_monitoring_backend_payload.json",
        backend_payload.model_dump(mode="json"),
        indent=2,
    )
    atomic_write_json(
        output_dir / "local_lab_monitoring_ingestion_summary.json",
        ingestion_summary.model_dump(mode="json"),
        indent=2,
    )


def test_load_local_lab_monitoring_bundle_reads_valid_bundle():
    scratch = _scratch_dir("valid")
    scratch.mkdir(parents=True, exist_ok=True)
    _write_bundle(scratch)

    bundle = load_local_lab_monitoring_bundle(scratch)

    assert bundle.backend_payload.correlation_id == "corr-local-lab-bundle"
    assert bundle.observability_export.runtime_mode == RuntimeMode.LOCAL_REPLAY
    assert bundle.ingestion_summary.ingestion_ready is True


def test_load_local_lab_monitoring_bundle_rejects_misaligned_summary_timestamp():
    scratch = _scratch_dir("misaligned")
    scratch.mkdir(parents=True, exist_ok=True)
    _write_bundle(scratch)

    payload = (scratch / "local_lab_monitoring_ingestion_summary.json").read_text(encoding="utf-8")
    (scratch / "local_lab_monitoring_ingestion_summary.json").write_text(
        payload.replace('"timestamp_ms": 1800000000000', '"timestamp_ms": 1800000000001'),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="Local IA Lab monitoring bundle requires matching timestamp_ms",
    ):
        load_local_lab_monitoring_bundle(scratch)
