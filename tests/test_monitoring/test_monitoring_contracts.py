from __future__ import annotations

import pytest
from pydantic import ValidationError

from interface_contracts import RuntimeMode
from monitoring import (
    FleetNodeProjection,
    FleetOverviewProjection,
    LocalLabMonitoringBackendPayload,
    LocalLabMonitoringIngestionSummary,
)


def test_fleet_overview_projection_accepts_read_only_summary():
    overview = FleetOverviewProjection(
        timestamp_ms=1_776_000_000_000,
        active_vps_id="vps-par-1",
        nodes=(
            FleetNodeProjection(
                vps_id="vps-par-1",
                health_status="healthy",
                runtime_mode=RuntimeMode.SHADOW,
                artifact_version="calibration_v1",
                heartbeat_age_ms=1_500,
                alert_state="healthy",
            ),
            FleetNodeProjection(
                vps_id="vps-par-2",
                health_status="warning",
                runtime_mode=RuntimeMode.MICRO_LIVE,
                artifact_version="calibration_v1",
                heartbeat_age_ms=4_000,
                alert_state="warning",
            ),
        ),
    )

    assert overview.active_vps_id == "vps-par-1"
    assert overview.nodes[0].runtime_mode == RuntimeMode.SHADOW
    assert overview.nodes[1].alert_state == "warning"


def test_fleet_overview_projection_rejects_duplicate_vps_ids():
    with pytest.raises(
        ValidationError,
        match="FleetOverviewProjection nodes must have unique vps_id values",
    ):
        FleetOverviewProjection(
            timestamp_ms=1_776_000_000_000,
            nodes=(
                FleetNodeProjection(vps_id="vps-par-1", health_status="healthy"),
                FleetNodeProjection(vps_id="vps-par-1", health_status="warning"),
            ),
        )


def test_fleet_overview_projection_rejects_unknown_active_vps():
    with pytest.raises(
        ValidationError,
        match="FleetOverviewProjection active_vps_id must reference a node in nodes",
    ):
        FleetOverviewProjection(
            timestamp_ms=1_776_000_000_000,
            active_vps_id="vps-par-2",
            nodes=(FleetNodeProjection(vps_id="vps-par-1", health_status="healthy"),),
        )


def test_local_lab_monitoring_backend_payload_accepts_descriptive_local_surface():
    payload = LocalLabMonitoringBackendPayload(
        timestamp_ms=1_800_000_000_000,
        correlation_id="corr-local-lab-backend",
        profile="complete",
        runtime_mode=RuntimeMode.LOCAL_REPLAY,
        status="warning",
        detail="Local IA Lab dry-run handoff remains pending governance inputs.",
        run_id="run-local-lab-backend",
        export_dir="E:/lab/export_dir",
        dataset_manifest_id="dataset-local-lab",
        artifact_id="edge_gate_thresholds",
        release_status="shadow_candidate",
        bridge_status="pending_governance_inputs",
        promotion_readiness_status="shadow_candidate_pending_dry_run",
        activation_stage="replay_only",
        normalized_promotion_state="replay_only",
        review_state="pending_review",
        release_gate_status="proof_gate_ready",
        semantic_status="source_transport_split",
        review_ready=True,
        artifact_proof_ready=True,
        edge_calibration_ready=True,
        scope_count=2,
        observability_sample_count=4,
        blocking_reason_count=1,
        release_gate_reason_count=1,
    )

    assert payload.profile.value == "complete"
    assert payload.runtime_mode == RuntimeMode.LOCAL_REPLAY
    assert payload.status == "warning"
    assert payload.observability_sample_count == 4


def test_local_lab_monitoring_ingestion_summary_accepts_descriptive_ingestion_surface():
    summary = LocalLabMonitoringIngestionSummary(
        timestamp_ms=1_800_000_000_000,
        correlation_id="corr-local-lab-ingestion",
        profile="complete",
        runtime_mode=RuntimeMode.LOCAL_REPLAY,
        projection_status="healthy",
        release_status="shadow_candidate",
        bridge_status="dry_run_ready",
        promotion_readiness_status="shadow_candidate_dry_run_ready",
        release_ready_for_shadow=True,
        ready_for_shadow_import_dry_run=True,
        sample_count=8,
        text_payload_present=True,
        text_payload_line_count=10,
        scope_count=2,
        release_scope_ready_count=2,
        release_scope_blocked_count=0,
        blocking_reason_count=0,
        release_gate_reason_count=2,
        ingestion_ready=True,
        ingestion_detail="Local IA Lab monitoring bundle is ready for backend ingestion.",
    )

    assert summary.profile.value == "complete"
    assert summary.runtime_mode == RuntimeMode.LOCAL_REPLAY
    assert summary.ingestion_ready is True
