from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import shutil
import sys
from types import ModuleType
from uuid import uuid4

from interface_contracts.shadow_vps_service_contracts import (
    ShadowVpsServiceEvent,
    ShadowVpsServiceState,
    ShadowVpsServiceStatus,
)
from monitoring.contracts import ProcessMetricsSample
from protocols import ShadowVpsServiceStore


def _load_script_module() -> ModuleType:
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "scripts" / "shadow_vps_service_monitoring_support.py"
    module_name = "test_shadow_vps_service_monitoring_support"
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class _FixedSampler:
    def __init__(self, sample: ProcessMetricsSample) -> None:
        self._sample = sample

    def sample(self) -> ProcessMetricsSample:
        return self._sample


def _scratch_dir(label: str) -> Path:
    repo_root = Path(__file__).resolve().parents[2]
    base_dir = repo_root / ".test_tmp"
    assert base_dir.is_dir()
    output_dir = base_dir / f"{label}_{uuid4().hex}"
    output_dir.mkdir(parents=True, exist_ok=False)
    return output_dir


def test_write_monitoring_artifacts_writes_vps_process_and_prometheus_outputs() -> None:
    module = _load_script_module()
    scratch = _scratch_dir("full")
    try:
        service_dir = scratch / "service"
        node_exporter_dir = scratch / "node_exporter"
        store = ShadowVpsServiceStore(service_dir)
        store._state = ShadowVpsServiceState(
            service_status=ShadowVpsServiceStatus.RUNNING,
            last_heartbeat_at=1_700_000_000.0,
            loop_count=5,
            success_count=4,
            idle_count=1,
            last_execution_telemetry_status="written",
        )
        store.persist()
        store.append_event(
            ShadowVpsServiceEvent(
                event_type="shadow_day_completed",
                timestamp=1_700_000_001.0,
                message="shadow service completed one iteration",
                session_date="2026-04-17",
                accepted=False,
                consecutive_days=3,
                remaining_days=27,
            )
        )

        (
            backend_payload_path,
            observability_export_path,
            observability_text_path,
            recent_events_summary_path,
            node_exporter_textfile_path,
            scrape_manifest_path,
            prometheus_file_sd_path,
        ) = module._write_monitoring_artifacts(
            service_dir=service_dir,
            store=store,
            sampler=_FixedSampler(
                ProcessMetricsSample(
                    pid=4321,
                    cpu_pct=7.5,
                    ram_pct=12.5,
                    rss_mb=256.0,
                    thread_count=9,
                    sampling_mode="test_mode",
                )
            ),
            node_exporter_textfile_dir=node_exporter_dir,
            scrape_host="127.0.0.1",
            vps_id="shadow-vps-1",
            node_exporter_port=9100,
            node_exporter_scheme="http",
            node_exporter_metrics_path="/metrics",
            prometheus_job_name="v53_shadow_vps",
        )

        assert backend_payload_path.exists()
        assert observability_export_path.exists()
        assert observability_text_path.exists()
        assert recent_events_summary_path.exists()
        assert node_exporter_textfile_path is not None
        assert node_exporter_textfile_path.exists()
        assert scrape_manifest_path is not None
        assert scrape_manifest_path.exists()
        assert prometheus_file_sd_path is not None
        assert prometheus_file_sd_path.exists()

        backend_payload = json.loads(backend_payload_path.read_text(encoding="utf-8"))
        observability_export = json.loads(
            observability_export_path.read_text(encoding="utf-8")
        )
        scrape_manifest = json.loads(scrape_manifest_path.read_text(encoding="utf-8"))
        file_sd_payload = json.loads(prometheus_file_sd_path.read_text(encoding="utf-8"))

        assert backend_payload["service_status"] == "running"
        assert backend_payload["process"]["pid"] == 4321
        assert backend_payload["process"]["cpu_pct"] == 7.5
        assert backend_payload["process"]["ram_pct"] == 12.5
        assert backend_payload["process"]["thread_count"] == 9
        assert backend_payload["node_exporter_textfile_ref"].endswith(
            "v53_shadow_vps_service.prom"
        )

        assert "v53_shadow_vps_process_cpu_pct" in observability_export["text_payload"]
        assert "v53_shadow_vps_process_ram_pct" in observability_export["text_payload"]
        assert "v53_shadow_vps_process_rss_mb" in observability_export["text_payload"]
        assert "v53_shadow_vps_service_status" in observability_export["text_payload"]

        node_exporter_text = node_exporter_textfile_path.read_text(encoding="utf-8")
        assert "v53_shadow_vps_process_cpu_pct" in node_exporter_text
        assert "v53_shadow_vps_process_ram_pct" in node_exporter_text

        assert scrape_manifest["prometheus_job_name"] == "v53_shadow_vps"
        assert scrape_manifest["observability_export_ref"].endswith(
            "shadow_vps_service_observability_export.json"
        )
        assert len(file_sd_payload) == 1
        assert all(
            entry["labels"]["job"] == "v53_shadow_vps" for entry in file_sd_payload
        )
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_write_monitoring_artifacts_skips_optional_outputs_without_node_exporter_or_scrape() -> None:
    module = _load_script_module()
    scratch = _scratch_dir("minimal")
    try:
        service_dir = scratch / "service"
        store = ShadowVpsServiceStore(service_dir)
        store._state = ShadowVpsServiceState(
            service_status=ShadowVpsServiceStatus.IDLE,
            last_heartbeat_at=1_700_000_100.0,
        )
        store.persist()

        (
            backend_payload_path,
            observability_export_path,
            observability_text_path,
            recent_events_summary_path,
            node_exporter_textfile_path,
            scrape_manifest_path,
            prometheus_file_sd_path,
        ) = module._write_monitoring_artifacts(
            service_dir=service_dir,
            store=store,
            sampler=_FixedSampler(
                ProcessMetricsSample(
                    pid=9876,
                    cpu_pct=0.0,
                    ram_pct=1.0,
                    rss_mb=32.0,
                    thread_count=3,
                    sampling_mode="test_mode",
                )
            )
        )

        assert backend_payload_path.exists()
        assert observability_export_path.exists()
        assert observability_text_path.exists()
        assert recent_events_summary_path.exists()
        assert node_exporter_textfile_path is None
        assert scrape_manifest_path is None
        assert prometheus_file_sd_path is None
        assert not (service_dir / "shadow_vps_service_scrape_manifest.json").exists()
        assert not (service_dir / "shadow_vps_service_prometheus_file_sd.json").exists()
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
