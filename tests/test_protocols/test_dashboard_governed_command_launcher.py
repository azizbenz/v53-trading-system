from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import shutil
import sys
from types import ModuleType


def _load_launcher_module() -> ModuleType:
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "scripts" / "run_dashboard_governed_command.py"
    module_name = "test_run_dashboard_governed_command"
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _scratch_dir(label: str) -> Path:
    from tests.support_paths import make_repo_scratch_dir

    return make_repo_scratch_dir("dashboard_governed_command_launcher", label)


def test_dashboard_governed_command_launcher_writes_halt_request() -> None:
    launcher = _load_launcher_module()
    queue_root = _scratch_dir("halt")

    try:
        exit_code = launcher.main(
            [
                "--queue-root",
                str(queue_root),
                "--command-kind",
                "set_halted",
                "--operator-reason",
                "manual halt from grafana",
            ]
        )

        assert exit_code == 0
        request_files = tuple(sorted((queue_root / "requests").glob("*.json")))
        assert len(request_files) == 1
        request = json.loads(request_files[0].read_text(encoding="utf-8"))
        assert request["command_kind"] == "set_halted"
        assert request["operator_reason"] == "manual halt from grafana"
        assert request["requested_by"] == "grafana_operator"
        assert request["target_runtime_mode"] == "live"
    finally:
        shutil.rmtree(queue_root, ignore_errors=True)


def test_dashboard_governed_command_launcher_writes_regime_upload_request() -> None:
    launcher = _load_launcher_module()
    queue_root = _scratch_dir("upload_regime")

    try:
        exit_code = launcher.main(
            [
                "--queue-root",
                str(queue_root),
                "--command-kind",
                "request_upload_regime_detector_artifact",
                "--artifact-hash",
                "b" * 64,
                "--artifact-id",
                "regime-v2",
                "--feature-set-version",
                "lob_regime_feature_set.v2",
                "--feature-profile",
                "extended_v2",
                "--lineage-version",
                "regime.v2.r1",
                "--review-state",
                "approved",
                "--validation-status",
                "validated",
                "--source-ref",
                "exports/regime_detector_artifact.json",
                "--payload-ref",
                "exports/regime_detector_artifact.summary.json",
            ]
        )

        assert exit_code == 0
        request_files = tuple(sorted((queue_root / "requests").glob("*.json")))
        assert len(request_files) == 1
        request = json.loads(request_files[0].read_text(encoding="utf-8"))
        assert request["command_kind"] == "request_upload_regime_detector_artifact"
        assert request["artifact_manifest"]["artifact_kind"] == "regime_detector_artifact"
        assert request["artifact_manifest"]["artifact_hash"] == "b" * 64
        assert request["artifact_manifest"]["feature_profile"] == "extended_v2"
        assert request["artifact_manifest"]["payload_refs"] == [
            "exports/regime_detector_artifact.summary.json"
        ]
    finally:
        shutil.rmtree(queue_root, ignore_errors=True)
