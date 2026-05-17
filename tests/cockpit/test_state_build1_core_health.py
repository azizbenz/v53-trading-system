from __future__ import annotations

import json
from pathlib import Path
import shutil
from uuid import uuid4

from cockpit.state_build1_core_health import read_build1_core_health


def _scratch_dir(label: str) -> Path:
    repo_root = Path(__file__).resolve().parents[2]
    base_dir = repo_root / ".test_tmp"
    base_dir.mkdir(parents=True, exist_ok=True)
    output_dir = base_dir / f"{label}_{uuid4().hex}"
    output_dir.mkdir(parents=True, exist_ok=False)
    return output_dir


def test_build1_core_health_reads_governed_artifact() -> None:
    scratch = _scratch_dir("build1_core_health")
    try:
        artifact_path = scratch / "build9_core_smoke" / "build1_core_health.json"
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        artifact_path.write_text(
            json.dumps(
                {
                    "build1_manifest_status": "PASS",
                    "build1_dag_status": "PASS",
                    "build1_guardrail_status": "PASS",
                    "build1_smoke_status": "PASS",
                    "build1_core_health_status": "PASS",
                    "reason_codes": [],
                },
                indent=2,
            ),
            encoding="utf-8",
        )

        snapshot = read_build1_core_health(scratch)

        assert snapshot.source_status == "ok"
        assert snapshot.build1_manifest_status == "PASS"
        assert snapshot.build1_core_health_status == "PASS"
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_build1_core_health_missing_artifact_blocks_status() -> None:
    scratch = _scratch_dir("build1_core_health_missing")
    try:
        snapshot = read_build1_core_health(scratch)

        assert snapshot.source_status == "missing"
        assert snapshot.build1_core_health_status == "BLOCKED"
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
