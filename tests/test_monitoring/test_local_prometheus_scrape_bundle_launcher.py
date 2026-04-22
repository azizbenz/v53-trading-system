from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import shutil
import sys
from uuid import uuid4

from interface_contracts import ProfileId, RuntimeMode
from interface_contracts.atomic_io import atomic_write_json
from monitoring.contracts import (
    DiskUsageSample,
    ProcessMetricsSample,
    ShadowVpsServiceMonitoringPayload,
)
from monitoring.shadow_vps_service_scrape_manifest import (
    build_shadow_vps_service_scrape_manifest,
)


def _load_launcher_module():
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "scripts" / "run_local_prometheus_scrape_bundle.py"
    module_name = "test_run_local_prometheus_scrape_bundle"
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _scratch_dir(label: str) -> Path:
    from tests.support_paths import make_repo_scratch_dir

    return make_repo_scratch_dir("pytest-local-prometheus-scrape-bundle", label)


def _payload(timestamp_ms: int) -> ShadowVpsServiceMonitoringPayload:
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


def _write_manifest(path: Path, *, timestamp_ms: int, scrape_host: str, vps_id: str) -> None:
    manifest = build_shadow_vps_service_scrape_manifest(
        _payload(timestamp_ms),
        scrape_host=scrape_host,
        vps_id=vps_id,
        monitoring_backend_payload_ref="E:/shadow/backend.json",
        observability_export_ref="E:/shadow/observability.json",
    )
    atomic_write_json(path, manifest.model_dump(mode="json"), indent=2)


def test_local_prometheus_scrape_bundle_launcher_writes_discovery_and_file_sd():
    launcher = _load_launcher_module()
    scratch = _scratch_dir("launcher")
    try:
        scrape_root = scratch / "scrape_root"
        output_dir = scratch / "output"
        first_dir = scrape_root / "vps1"
        second_dir = scrape_root / "vps2"
        first_dir.mkdir(parents=True, exist_ok=True)
        second_dir.mkdir(parents=True, exist_ok=True)
        _write_manifest(
            first_dir / "shadow_vps_service_scrape_manifest.json",
            timestamp_ms=1_800_000_000_000,
            scrape_host="10.0.0.5",
            vps_id="vps-paris-01",
        )
        _write_manifest(
            second_dir / "shadow_vps_service_scrape_manifest.json",
            timestamp_ms=1_800_000_000_100,
            scrape_host="10.0.0.6",
            vps_id="vps-paris-02",
        )

        exit_code = launcher.main(
            [
                "--scrape-root",
                str(scrape_root),
                "--output-dir",
                str(output_dir),
            ]
        )

        assert exit_code == 0
        discovery = json.loads(
            (output_dir / "shadow_vps_scrape_discovery.json").read_text(
                encoding="utf-8"
            )
        )
        file_sd = json.loads(
            (output_dir / "shadow_vps_prometheus_file_sd.json").read_text(
                encoding="utf-8"
            )
        )

        assert discovery["manifest_count"] == 2
        assert discovery["target_count"] == 2
        assert discovery["latest_vps_id"] == "vps-paris-02"
        assert {entry["targets"][0] for entry in file_sd} == {
            "10.0.0.5:9100",
            "10.0.0.6:9100",
        }
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
