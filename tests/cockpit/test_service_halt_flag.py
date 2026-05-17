"""P0-1 — service Shadow HALT.flag watcher tests.

The HALT.flag channel is the Windows-friendly equivalent of SIGTERM. It is
also the redundant kill path on Linux — when the cockpit cannot match the
PID file, dropping the flag still triggers an orderly stop.
"""

from __future__ import annotations

import sys
from pathlib import Path

from ._operational_helpers import cleanup_scratch, scratch_dir

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_ROOT = REPO_ROOT / "scripts"
SRC_ROOT = REPO_ROOT / "src"
for candidate in (str(SCRIPTS_ROOT), str(SRC_ROOT)):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

import run_shadow_vps_service as svc  # noqa: E402


def test_should_stop_returns_false_without_flag() -> None:
    scratch = scratch_dir("service_halt_flag_absent")
    try:
        flag = scratch / "HALT.flag"
        controller = svc._ShadowVpsSignalController()
        should_stop = svc._build_should_stop_callable(
            signal_controller=controller, halt_flag_file=flag
        )
        assert should_stop() is False
        assert controller.stop_requested() is False
    finally:
        cleanup_scratch(scratch)


def test_flag_present_triggers_stop_and_self_clears() -> None:
    scratch = scratch_dir("service_halt_flag_present")
    try:
        flag = scratch / "HALT.flag"
        flag.write_text("kill", encoding="utf-8")
        controller = svc._ShadowVpsSignalController()
        should_stop = svc._build_should_stop_callable(
            signal_controller=controller, halt_flag_file=flag
        )
        assert should_stop() is True
        assert controller.stop_requested() is True
        assert "HALT_FLAG_OBSERVED" in controller.stop_reason()
        assert not flag.exists()
    finally:
        cleanup_scratch(scratch)


def test_signal_already_requested_propagates_without_flag() -> None:
    scratch = scratch_dir("service_halt_flag_signal")
    try:
        flag = scratch / "HALT.flag"
        controller = svc._ShadowVpsSignalController()
        controller.request_stop("SIGTERM")
        should_stop = svc._build_should_stop_callable(
            signal_controller=controller, halt_flag_file=flag
        )
        assert should_stop() is True
        assert not flag.exists()
    finally:
        cleanup_scratch(scratch)


def test_no_flag_path_means_signal_only() -> None:
    controller = svc._ShadowVpsSignalController()
    should_stop = svc._build_should_stop_callable(
        signal_controller=controller, halt_flag_file=None
    )
    assert should_stop() is False
    controller.request_stop("SIGINT")
    assert should_stop() is True


def test_observed_flag_survives_unlink_failure() -> None:
    """Even if the flag cannot be deleted, the controller stops the loop."""

    scratch = scratch_dir("service_halt_flag_unlink")
    try:
        flag = scratch / "HALT.flag"
        flag.write_text("kill", encoding="utf-8")
        controller = svc._ShadowVpsSignalController()
        should_stop = svc._build_should_stop_callable(
            signal_controller=controller, halt_flag_file=flag
        )

        flag.unlink()
        flag.write_text("kill", encoding="utf-8")
        assert should_stop() is True
        assert controller.stop_requested() is True
    finally:
        cleanup_scratch(scratch)
