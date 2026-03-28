"""Tests for the local technical dashboard launcher."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import shutil
import sys
from uuid import uuid4


def _load_launcher_module():
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "scripts" / "run_technical_dashboard.py"
    module_name = "test_run_technical_dashboard_launcher"
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _scratch_dir(label: str) -> Path:
    repo_root = Path(__file__).resolve().parents[2]
    base_dir = repo_root / "build" / "technical_dashboard_launcher_tests"
    base_dir.mkdir(parents=True, exist_ok=True)
    output_dir = base_dir / f"{label}_{uuid4().hex}"
    output_dir.mkdir(parents=True, exist_ok=False)
    return output_dir


def test_export_technical_dashboard_writes_availability_view():
    launcher = _load_launcher_module()
    output_dir = _scratch_dir("availability")

    try:
        artifacts = launcher.export_technical_dashboard(output_dir)

        assert artifacts.html_path.exists()
        html = artifacts.html_path.read_text(encoding="utf-8")
        assert "availability_only" in html
        assert "No monitoring snapshot loaded" in html
        assert "Build-11 Shadow" in html
        assert "Build-12 Micro-live" in html
        assert "Build-13 Live-Light" in html
        assert "Build-14 Read-only" in html
        assert "Governance &amp; Readiness" in html
        assert artifacts.payload_json_path is None
        assert artifacts.view_json_path is None
        assert artifacts.observability_text_path is None
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_export_technical_dashboard_writes_demo_sidecars():
    launcher = _load_launcher_module()
    output_dir = _scratch_dir("demo")

    try:
        artifacts = launcher.export_technical_dashboard(output_dir, demo=True)

        assert artifacts.html_path.exists()
        assert artifacts.payload_json_path is not None and artifacts.payload_json_path.exists()
        assert artifacts.view_json_path is not None and artifacts.view_json_path.exists()
        assert artifacts.observability_text_path is not None and artifacts.observability_text_path.exists()

        html = artifacts.html_path.read_text(encoding="utf-8")
        payload_json = artifacts.payload_json_path.read_text(encoding="utf-8")
        observability_text = artifacts.observability_text_path.read_text(encoding="utf-8")

        assert "demo payload" in html.lower()
        assert "Build-11 Shadow" in html
        assert "Build-12 Micro-live" in html
        assert "Build-13 Live-Light" in html
        assert "Strategy Onboarding" in html
        assert "Build-14 Read-only" in html
        assert "Observability Export" in html
        assert '"correlation_id": "corr-tech-demo"' in payload_json
        assert '"shadow"' in payload_json
        assert '"micro_live"' in payload_json
        assert '"live_light"' in payload_json
        assert "v53_system_headline_status" in observability_text
        assert "v53_shadow_run_state" in observability_text
        assert "v53_micro_live_run_state" in observability_text
        assert "v53_live_light_run_state" in observability_text
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_launcher_main_accepts_demo_output_dir():
    launcher = _load_launcher_module()
    output_dir = _scratch_dir("cli")

    try:
        exit_code = launcher.main(["--demo", "--output-dir", str(output_dir)])

        assert exit_code == 0
        assert (output_dir / "technical_dashboard.html").exists()
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
