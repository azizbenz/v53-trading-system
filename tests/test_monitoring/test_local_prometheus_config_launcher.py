from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import shutil
import sys
from uuid import uuid4


def _load_launcher_module():
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "scripts" / "run_local_prometheus_config.py"
    module_name = "test_run_local_prometheus_config"
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _scratch_dir(label: str) -> Path:
    repo_root = Path(__file__).resolve().parents[2]
    base_dir = repo_root / "build" / "pytest-local-prometheus-config"
    base_dir.mkdir(parents=True, exist_ok=True)
    output_dir = base_dir / f"{label}_{uuid4().hex}"
    output_dir.mkdir(parents=True, exist_ok=False)
    return output_dir


def test_local_prometheus_config_launcher_writes_yaml_and_summary():
    launcher = _load_launcher_module()
    scratch = _scratch_dir("launcher")
    try:
        vps_file_sd_path = scratch / "shadow_vps_prometheus_file_sd.json"
        output_dir = scratch / "output"
        vps_file_sd_path.write_text(
            json.dumps(
                [
                    {
                        "targets": ["10.0.0.5:9100"],
                        "labels": {"job": "v53_shadow_vps", "vps_id": "vps-paris-01"},
                    }
                ],
                indent=2,
            ),
            encoding="utf-8",
        )

        exit_code = launcher.main(
            [
                "--vps-file-sd-path",
                str(vps_file_sd_path),
                "--output-dir",
                str(output_dir),
                "--local-node-exporter-target",
                "127.0.0.1:9100",
            ]
        )

        assert exit_code == 0
        config_text = (output_dir / "prometheus.local.generated.yml").read_text(
            encoding="utf-8"
        )
        summary = json.loads(
            (output_dir / "prometheus.local.config.summary.json").read_text(
                encoding="utf-8"
            )
        )

        assert "job_name: v53_shadow_vps" in config_text
        assert str(vps_file_sd_path) in config_text
        assert "127.0.0.1:9100" in config_text
        assert summary["scrape_job_count"] == 2
        assert summary["includes_local_node_exporter"] is True
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_local_prometheus_config_launcher_writes_windows_exporter_job_when_requested():
    launcher = _load_launcher_module()
    scratch = _scratch_dir("windows")
    try:
        vps_file_sd_path = scratch / "shadow_vps_prometheus_file_sd.json"
        output_dir = scratch / "output"
        vps_file_sd_path.write_text(
            json.dumps(
                [
                    {
                        "targets": ["127.0.0.1:9100"],
                        "labels": {"job": "v53_shadow_vps", "vps_id": "dev-box-01"},
                    }
                ],
                indent=2,
            ),
            encoding="utf-8",
        )

        exit_code = launcher.main(
            [
                "--vps-file-sd-path",
                str(vps_file_sd_path),
                "--output-dir",
                str(output_dir),
                "--local-windows-exporter-target",
                "127.0.0.1:9182",
            ]
        )

        assert exit_code == 0
        config_text = (output_dir / "prometheus.local.generated.yml").read_text(
            encoding="utf-8"
        )
        summary = json.loads(
            (output_dir / "prometheus.local.config.summary.json").read_text(
                encoding="utf-8"
            )
        )

        assert "job_name: v53_local_windows" in config_text
        assert "127.0.0.1:9182" in config_text
        assert summary["scrape_job_count"] == 2
        assert summary["includes_local_windows_exporter"] is True
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_local_prometheus_config_launcher_writes_local_lab_job_when_requested():
    launcher = _load_launcher_module()
    scratch = _scratch_dir("local_lab")
    try:
        vps_file_sd_path = scratch / "shadow_vps_prometheus_file_sd.json"
        output_dir = scratch / "output"
        vps_file_sd_path.write_text(
            json.dumps(
                [
                    {
                        "targets": ["127.0.0.1:9100"],
                        "labels": {"job": "v53_shadow_vps", "vps_id": "dev-box-01"},
                    }
                ],
                indent=2,
            ),
            encoding="utf-8",
        )

        exit_code = launcher.main(
            [
                "--vps-file-sd-path",
                str(vps_file_sd_path),
                "--output-dir",
                str(output_dir),
                "--local-lab-target",
                "127.0.0.1:9200",
            ]
        )

        assert exit_code == 0
        config_text = (output_dir / "prometheus.local.generated.yml").read_text(
            encoding="utf-8"
        )
        summary = json.loads(
            (output_dir / "prometheus.local.config.summary.json").read_text(
                encoding="utf-8"
            )
        )

        assert "job_name: v53_local_lab" in config_text
        assert "127.0.0.1:9200" in config_text
        assert summary["scrape_job_count"] == 2
        assert summary["includes_local_lab_bridge"] is True
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
