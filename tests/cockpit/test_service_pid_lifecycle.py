"""P0-1 — service Shadow PID file lifecycle tests.

These tests pin the contract used by the cockpit kill switch (Phase 3):
the service must atomically write its PID at start and remove it at exit.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from ._operational_helpers import cleanup_scratch, scratch_dir

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_ROOT = REPO_ROOT / "scripts"
SRC_ROOT = REPO_ROOT / "src"
for candidate in (str(SCRIPTS_ROOT), str(SRC_ROOT)):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

import run_shadow_vps_service as svc  # noqa: E402


def test_write_pid_file_creates_parent_dir_and_atomic_replace() -> None:
    scratch = scratch_dir("service_pid_write")
    try:
        pid_file = scratch / "nested" / "deeper" / "v53_shadow.pid"
        written = svc._write_pid_file_if_configured(pid_file)
        assert written is True
        assert pid_file.is_file()
        assert pid_file.read_text(encoding="utf-8") == str(os.getpid())
        siblings = list(pid_file.parent.iterdir())
        assert siblings == [pid_file]
    finally:
        cleanup_scratch(scratch)


def test_write_pid_file_returns_false_when_path_is_none() -> None:
    assert svc._write_pid_file_if_configured(None) is False


def test_clear_pid_file_idempotent() -> None:
    scratch = scratch_dir("service_pid_clear")
    try:
        pid_file = scratch / "v53.pid"
        pid_file.write_text("42", encoding="utf-8")
        svc._clear_pid_file(pid_file)
        assert not pid_file.exists()
        svc._clear_pid_file(pid_file)
        assert not pid_file.exists()
    finally:
        cleanup_scratch(scratch)


def test_pid_file_round_trip_via_lifecycle() -> None:
    scratch = scratch_dir("service_pid_round_trip")
    try:
        pid_file = scratch / "round.pid"
        written = svc._write_pid_file_if_configured(pid_file)
        assert written is True
        assert pid_file.read_text(encoding="utf-8").isdigit()
        svc._clear_pid_file(pid_file)
        assert not pid_file.exists()
    finally:
        cleanup_scratch(scratch)


def test_write_pid_file_handles_unwritable_parent(monkeypatch: pytest.MonkeyPatch) -> None:
    """When mkdir fails, the helper logs a warning and returns False; never raises."""

    scratch = scratch_dir("service_pid_unwritable")
    try:
        pid_file = scratch / "never.pid"

        def _boom(*_args: object, **_kwargs: object) -> None:
            raise OSError("simulated permission error")

        monkeypatch.setattr("pathlib.Path.mkdir", _boom)
        assert svc._write_pid_file_if_configured(pid_file) is False
        assert not pid_file.exists()
    finally:
        cleanup_scratch(scratch)
