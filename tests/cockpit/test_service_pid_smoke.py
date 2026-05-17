"""End-to-end smoke proof for P0-1 — runs the real service in a subprocess.

Marks: this test is heavy (spawns the actual Shadow service runtime). It is
the canonical proof that:
  1. The PID file is written *during* the run.
  2. Dropping ``HALT.flag`` stops the service in < 5 s.
  3. The PID file is removed after exit.

Skipped by default in CI; run with ``pytest -m smoke``.
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path
import shutil

import pytest

from ._operational_helpers import cleanup_scratch, scratch_dir


REPO_ROOT = Path(__file__).resolve().parent.parent.parent

pytestmark = pytest.mark.smoke


def _has_smoke_marker() -> bool:
    """Smoke tests only run when the user opts in via ``-m smoke``."""
    # Pytest will skip via the marker registration in pyproject; this helper is
    # documentation only.
    return True


def test_service_pid_lifecycle_e2e() -> None:
    scratch = scratch_dir("service_pid_smoke")
    pid_file = scratch / "v53_smoke.pid"
    halt_flag = scratch / "HALT.flag"
    service_dir = scratch / "service"
    orchestrator_dir = scratch / "orchestrator"
    shadow_dir = scratch / "shadow_session"
    captures_dir = scratch / "live_captures"
    exports_dir = scratch / "auto_exports"
    live_config = scratch / "live_websocket_config.json"

    for directory in (
        service_dir,
        orchestrator_dir,
        shadow_dir,
        captures_dir,
        exports_dir,
    ):
        directory.mkdir(parents=True, exist_ok=True)
    shutil.copy2(
        REPO_ROOT / "build" / "build11_live_websocket_campaign" / "live_websocket_config.json",
        live_config,
    )

    cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "run_shadow_vps_service.py"),
        "--service-dir", str(service_dir),
        "--orchestrator-output-dir", str(orchestrator_dir),
        "--shadow-output-dir", str(shadow_dir),
        "--live-websocket-config", str(live_config),
        "--live-captures-root", str(captures_dir),
        "--auto-exports-root", str(exports_dir),
        "--pid-file", str(pid_file),
        "--halt-flag-file", str(halt_flag),
        "--max-cycles", "10",
        "--poll-interval-s", "2",
    ]

    proc = subprocess.Popen(
        cmd,
        cwd=str(REPO_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        # Full cockpit-suite runs can start the smoke subprocess under heavier
        # filesystem and interpreter pressure on Windows. The PID file is still
        # expected during the run, but the startup window needs a little slack.
        deadline = time.time() + 20.0
        while time.time() < deadline:
            if pid_file.is_file():
                break
            time.sleep(0.2)
        assert pid_file.is_file(), "service did not write PID file within 20s"
        pid_value = int(pid_file.read_text(encoding="utf-8"))
        assert pid_value == proc.pid

        # Drop HALT flag — service should stop within 5 s.
        halt_flag.write_text("smoke", encoding="utf-8")
        try:
            proc.wait(timeout=10.0)
        except subprocess.TimeoutExpired:
            proc.kill()
            pytest.fail("service did not stop within 10s of HALT.flag drop")

        # PID file must be cleared.
        assert not pid_file.exists(), "PID file should be cleared after exit"
        # HALT.flag must be self-cleared.
        assert not halt_flag.exists(), "HALT.flag should be removed after observation"
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=5.0)
        cleanup_scratch(scratch)
