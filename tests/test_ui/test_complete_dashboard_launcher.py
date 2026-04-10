"""Tests for the local Complete dashboard launcher."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import shutil
import sys
from uuid import uuid4


def _load_launcher_module():
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "scripts" / "run_complete_dashboard.py"
    module_name = "test_run_complete_dashboard_launcher"
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _scratch_dir(label: str) -> Path:
    repo_root = Path(__file__).resolve().parents[2]
    base_dir = repo_root / "build" / "complete_dashboard_launcher_tests"
    base_dir.mkdir(parents=True, exist_ok=True)
    output_dir = base_dir / f"{label}_{uuid4().hex}"
    output_dir.mkdir(parents=True, exist_ok=False)
    return output_dir


def test_export_complete_dashboard_writes_availability_view():
    launcher = _load_launcher_module()
    output_dir = _scratch_dir("availability")

    try:
        artifacts = launcher.export_complete_dashboard(output_dir)

        assert artifacts.html_path.exists()
        html = artifacts.html_path.read_text(encoding="utf-8")
        assert "availability_only" in html
        assert "Overview Portefeuille Complete" in html
        assert "Pairs (12 Pairs)" in html
        assert "Controlled Complete Administration" in html
        assert "No live Complete runtime snapshot" in html
        assert "Governed Complete Pair Selection" in html
        assert artifacts.payload_json_path is None
        assert artifacts.view_json_path is None
        assert artifacts.observability_text_path is None
        assert artifacts.supplement_json_path is None
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_export_complete_dashboard_writes_demo_sidecars():
    launcher = _load_launcher_module()
    output_dir = _scratch_dir("demo")

    try:
        artifacts = launcher.export_complete_dashboard(output_dir, demo=True)

        assert artifacts.html_path.exists()
        assert artifacts.payload_json_path is not None and artifacts.payload_json_path.exists()
        assert artifacts.view_json_path is not None and artifacts.view_json_path.exists()
        assert artifacts.observability_text_path is not None and artifacts.observability_text_path.exists()
        assert artifacts.supplement_json_path is not None and artifacts.supplement_json_path.exists()

        html = artifacts.html_path.read_text(encoding="utf-8")
        payload_json = artifacts.payload_json_path.read_text(encoding="utf-8")
        supplement_json = artifacts.supplement_json_path.read_text(encoding="utf-8")
        observability_text = artifacts.observability_text_path.read_text(encoding="utf-8")

        assert "demo_payload" in html
        assert "Overview Portefeuille Complete" in html
        assert "Engines (A/B/C/D)" in html
        assert "Covariance &amp; Risk Contributions" in html
        assert "Effective Edge Diversity" in html
        assert "Controlled Complete Administration" in html
        assert "Governed Complete Pair Selection" in html
        assert "Copy PowerShell Command" in html
        assert '"profile": "complete"' in payload_json
        assert '"engine_c"' in payload_json
        assert '"engine_d"' in payload_json
        assert '"deployment_state": "live_complete"' in supplement_json
        assert '"c_marginal_contribution"' in supplement_json
        assert "v53_system_headline_status" in observability_text
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_export_complete_dashboard_respects_selected_pairs():
    launcher = _load_launcher_module()
    output_dir = _scratch_dir("demo_selected_pairs")

    try:
        artifacts = launcher.export_complete_dashboard(
            output_dir,
            demo=True,
            selected_pairs=("BTCUSDT", "SOLUSDT", "NEARUSDT"),
        )

        assert artifacts.payload_json_path is not None and artifacts.payload_json_path.exists()
        assert artifacts.supplement_json_path is not None and artifacts.supplement_json_path.exists()

        payload = json.loads(artifacts.payload_json_path.read_text(encoding="utf-8"))
        supplement = json.loads(artifacts.supplement_json_path.read_text(encoding="utf-8"))
        html = artifacts.html_path.read_text(encoding="utf-8")

        assert [pair["pair"] for pair in payload["pairs"]] == ["BTCUSDT", "SOLUSDT", "NEARUSDT"]
        assert supplement["selected_pairs"] == ["BTCUSDT", "SOLUSDT", "NEARUSDT"]
        assert "3/12 selected" in html
        assert "selected=BTCUSDT, SOLUSDT, NEARUSDT" in html
        assert "--pair BTCUSDT --pair SOLUSDT --pair NEARUSDT" in html
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_complete_launcher_main_accepts_demo_output_dir():
    launcher = _load_launcher_module()
    output_dir = _scratch_dir("cli")

    try:
        exit_code = launcher.main(["--demo", "--output-dir", str(output_dir)])

        assert exit_code == 0
        assert (output_dir / "complete_dashboard.html").exists()
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_complete_launcher_main_accepts_explicit_pair_selection():
    launcher = _load_launcher_module()
    output_dir = _scratch_dir("cli_pairs")

    try:
        exit_code = launcher.main(
            [
                "--demo",
                "--output-dir",
                str(output_dir),
                "--pair",
                "BTCUSDT",
                "--pair",
                "ETHUSDT",
                "--pair",
                "SOLUSDT",
            ]
        )

        assert exit_code == 0
        payload = json.loads((output_dir / "complete_dashboard.payload.json").read_text(encoding="utf-8"))
        assert [pair["pair"] for pair in payload["pairs"]] == ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_complete_launcher_main_accepts_pair_count():
    launcher = _load_launcher_module()
    output_dir = _scratch_dir("cli_pair_count")

    try:
        exit_code = launcher.main(
            [
                "--demo",
                "--output-dir",
                str(output_dir),
                "--pair-count",
                "4",
            ]
        )

        assert exit_code == 0
        payload = json.loads((output_dir / "complete_dashboard.payload.json").read_text(encoding="utf-8"))
        supplement = json.loads((output_dir / "complete_dashboard.supplement.json").read_text(encoding="utf-8"))
        assert [pair["pair"] for pair in payload["pairs"]] == ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT"]
        assert supplement["selected_pairs"] == ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT"]
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
