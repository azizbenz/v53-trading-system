from __future__ import annotations

from pathlib import Path
import shutil
from uuid import uuid4

from interface_contracts import ProfileId, RuntimeMode
from interface_contracts.atomic_io import atomic_write_json
from monitoring.shadow_vps_scrape_discovery import (
    build_shadow_vps_prometheus_file_sd_from_root,
    discover_shadow_vps_service_scrape_manifests,
)
from monitoring.shadow_vps_service_scrape_manifest import (
    build_shadow_vps_service_scrape_manifest,
)
from monitoring.contracts import (
    DiskUsageSample,
    ProcessMetricsSample,
    ShadowVpsServiceMonitoringPayload,
)


def _scratch_dir(label: str) -> Path:
    from tests.support_paths import make_repo_scratch_dir

    return make_repo_scratch_dir("pytest-shadow-vps-scrape-discovery", label)


def _payload(timestamp_ms: int, *, textfile_ready: bool = True) -> ShadowVpsServiceMonitoringPayload:
    return ShadowVpsServiceMonitoringPayload(
        timestamp_ms=timestamp_ms,
        correlation_id=f"corr-{timestamp_ms}",
        profile=ProfileId.COMPLETE,
        runtime_mode=RuntimeMode.SHADOW,
        status="healthy",
        detail="ok",
        service_status="running",
        heartbeat_age_ms=5000,
        loop_count=3,
        success_count=2,
        idle_count=1,
        failure_count=0,
        acquisition_mode="dated_export",
        runtime_data_source="recorded_replay",
        accepted=False,
        consecutive_days=2,
        remaining_days=28,
        promotion_gate_passed=False,
        live_capture_emitted_message_count=0,
        live_capture_accepted_message_count=0,
        live_capture_rejected_message_count=0,
        live_user_data_authenticated=False,
        live_user_data_event_count=0,
        recent_events_summary_ref="E:/shadow/recent.json",
        node_exporter_textfile_ref=(
            "E:/node_textfile/v53_shadow_vps_service.prom" if textfile_ready else ""
        ),
        process=ProcessMetricsSample(
            pid=123,
            cpu_pct=1.0,
            ram_pct=2.0,
            rss_mb=64.0,
            thread_count=4,
            sampling_mode="test_mode",
        ),
        disk=DiskUsageSample(
            path="E:/shadow",
            total_gb=100.0,
            free_gb=50.0,
            used_pct=50.0,
            sampling_mode="test_mode",
        ),
    )


def _write_manifest(
    path: Path,
    *,
    timestamp_ms: int,
    scrape_host: str,
    vps_id: str,
    node_exporter_port: int = 9100,
) -> None:
    manifest = build_shadow_vps_service_scrape_manifest(
        _payload(timestamp_ms),
        scrape_host=scrape_host,
        vps_id=vps_id,
        node_exporter_port=node_exporter_port,
        monitoring_backend_payload_ref="E:/shadow/backend.json",
        observability_export_ref="E:/shadow/observability.json",
    )
    atomic_write_json(path, manifest.model_dump(mode="json"), indent=2)


def test_discover_shadow_vps_service_scrape_manifests_sorts_latest_first():
    scratch = _scratch_dir("discover")
    try:
        older = scratch / "older"
        newer = scratch / "newer"
        older.mkdir(parents=True, exist_ok=True)
        newer.mkdir(parents=True, exist_ok=True)
        _write_manifest(
            older / "shadow_vps_service_scrape_manifest.json",
            timestamp_ms=1_800_000_000_000,
            scrape_host="10.0.0.5",
            vps_id="vps-old",
        )
        _write_manifest(
            newer / "shadow_vps_service_scrape_manifest.json",
            timestamp_ms=1_800_000_000_100,
            scrape_host="10.0.0.6",
            vps_id="vps-new",
        )

        discovery = discover_shadow_vps_service_scrape_manifests(scratch)

        assert discovery.manifest_count == 2
        assert discovery.target_count == 2
        assert discovery.latest_vps_id == "vps-new"
        assert discovery.latest_target == "10.0.0.6:9100"
        assert discovery.manifests[0].vps_id == "vps-new"
        assert discovery.manifests[1].vps_id == "vps-old"
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_build_shadow_vps_prometheus_file_sd_from_root_deduplicates_latest_target():
    scratch = _scratch_dir("file_sd")
    try:
        older = scratch / "older"
        newer = scratch / "newer"
        older.mkdir(parents=True, exist_ok=True)
        newer.mkdir(parents=True, exist_ok=True)
        _write_manifest(
            older / "shadow_vps_service_scrape_manifest.json",
            timestamp_ms=1_800_000_000_000,
            scrape_host="10.0.0.5",
            vps_id="vps-old",
        )
        _write_manifest(
            newer / "shadow_vps_service_scrape_manifest.json",
            timestamp_ms=1_800_000_000_100,
            scrape_host="10.0.0.5",
            vps_id="vps-new",
        )

        entries = build_shadow_vps_prometheus_file_sd_from_root(scratch)

        assert len(entries) == 1
        assert entries[0].targets == ("10.0.0.5:9100",)
        assert entries[0].labels["vps_id"] == "vps-new"
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
