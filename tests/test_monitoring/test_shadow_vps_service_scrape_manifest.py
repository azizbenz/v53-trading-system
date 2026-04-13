from __future__ import annotations

from interface_contracts import ProfileId, RuntimeMode
from monitoring.contracts import (
    DiskUsageSample,
    ProcessMetricsSample,
    ShadowVpsServiceMonitoringPayload,
)
from monitoring.shadow_vps_service_scrape_manifest import (
    build_shadow_vps_service_prometheus_file_sd,
    build_shadow_vps_service_scrape_manifest,
)


def _payload() -> ShadowVpsServiceMonitoringPayload:
    return ShadowVpsServiceMonitoringPayload(
        timestamp_ms=1_800_000_000_000,
        correlation_id="shadow-vps-service",
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
        state_path="E:/shadow/shadow_vps_service.state.json",
        events_path="E:/shadow/shadow_vps_service.events.jsonl",
        campaign_summary_ref="E:/shadow/shadow_vps_service.campaign_summary.json",
        runtime_evidence_bundle_ref="E:/shadow/runtime_evidence.json",
        export_dir_ref="E:/shadow/export",
        recent_events_summary_ref="E:/shadow/shadow_vps_service_recent_events.json",
        node_exporter_textfile_ref="E:/node_textfile/v53_shadow_vps_service.prom",
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


def test_build_shadow_vps_service_scrape_manifest_projects_scrape_target():
    manifest = build_shadow_vps_service_scrape_manifest(
        _payload(),
        scrape_host="10.0.0.5",
        vps_id="vps-paris-01",
        node_exporter_port=9100,
        node_exporter_scheme="http",
        node_exporter_metrics_path="/metrics",
        prometheus_job_name="v53_shadow_vps",
        monitoring_backend_payload_ref="E:/shadow/backend.json",
        observability_export_ref="E:/shadow/observability.json",
    )

    assert manifest.node_exporter_target == "10.0.0.5:9100"
    assert manifest.vps_id == "vps-paris-01"
    assert manifest.node_exporter_textfile_ready is True
    assert manifest.labels["job"] == "v53_shadow_vps"
    assert manifest.labels["runtime_mode"] == "shadow"


def test_build_shadow_vps_service_prometheus_file_sd_projects_single_target():
    entries = build_shadow_vps_service_prometheus_file_sd(
        build_shadow_vps_service_scrape_manifest(
            _payload(),
            scrape_host="10.0.0.5",
            vps_id="vps-paris-01",
        )
    )

    assert len(entries) == 1
    assert entries[0].targets == ("10.0.0.5:9100",)
    assert entries[0].labels["vps_id"] == "vps-paris-01"
