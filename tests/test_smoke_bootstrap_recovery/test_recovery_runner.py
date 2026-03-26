"""Tests Module 5 — recovery_runner: recovery after shutdown, partial state."""

import pytest
from typing import Any

from smoke_bootstrap_recovery.recovery_runner import run_recovery_cycle
from smoke_bootstrap_recovery.smoke_models import SmokeStatus


# ─── FIXTURES ────────────────────────────────────────────────────────


class CleanModule:
    """Module that supports clean shutdown and restart."""

    def __init__(self) -> None:
        self.state: dict[str, Any] = {}
        self.boot_count = 0

    def bootstrap(self, config: dict[str, Any]) -> None:
        self.boot_count += 1
        self.state = {"initialized": True, "boot_count": self.boot_count}

    def shutdown(self) -> None:
        self.state = {}

    def is_initialized(self) -> bool:
        return self.state.get("initialized", False)


class CrashOnRestartModule:
    """Module that crashes on second bootstrap (simulates corruption)."""

    def __init__(self) -> None:
        self.boot_count = 0

    def bootstrap(self, config: dict[str, Any]) -> None:
        self.boot_count += 1
        if self.boot_count > 1:
            raise RuntimeError("State corrupted on restart")

    def shutdown(self) -> None:
        pass


class CrashOnShutdownModule:
    """Module that crashes during shutdown."""

    def bootstrap(self, config: dict[str, Any]) -> None:
        pass

    def shutdown(self) -> None:
        raise RuntimeError("Cannot shut down cleanly")


class CorruptedStateModule:
    """Module where post-restart state is invalid."""

    def __init__(self) -> None:
        self.restart_count = 0

    def bootstrap(self, config: dict[str, Any]) -> None:
        self.restart_count += 1

    def shutdown(self) -> None:
        pass

    def post_state_ok(self) -> bool:
        # After restart, state is "corrupted"
        return self.restart_count <= 1


# ─── TESTS ───────────────────────────────────────────────────────────


@pytest.mark.build1
class TestRecoveryAfterShutdown:
    """7.14: recovery after controlled shutdown."""

    def test_clean_recovery_passes(self):
        mod = CleanModule()
        result = run_recovery_cycle("test_clean", mod, {})
        assert result.passed
        assert result.status == SmokeStatus.PASS
        assert result.pre_state_valid
        assert result.post_state_valid
        assert mod.boot_count == 2  # boot, shutdown, re-boot, shutdown

    def test_recovery_duration_tracked(self):
        mod = CleanModule()
        result = run_recovery_cycle("test_clean", mod, {})
        assert result.duration_ms >= 0

    def test_recovery_with_pre_check(self):
        mod = CleanModule()
        result = run_recovery_cycle(
            "test_pre",
            mod,
            {},
            pre_state_checker=mod.is_initialized,
        )
        assert result.passed
        assert result.pre_state_valid


@pytest.mark.build1
class TestRecoveryAfterPartialState:
    """7.14: recovery after partial state / crash."""

    def test_crash_on_restart_fails(self):
        mod = CrashOnRestartModule()
        result = run_recovery_cycle("test_crash", mod, {})
        assert not result.passed
        assert result.status == SmokeStatus.FAIL
        assert "RuntimeError" in result.message

    def test_crash_on_shutdown_fails(self):
        mod = CrashOnShutdownModule()
        result = run_recovery_cycle("test_shutdown_crash", mod, {})
        assert not result.passed
        assert "RuntimeError" in result.message

    def test_corrupted_post_state_fails(self):
        mod = CorruptedStateModule()
        result = run_recovery_cycle(
            "test_corrupt",
            mod,
            {},
            post_state_checker=mod.post_state_ok,
        )
        assert not result.passed
        assert not result.post_state_valid
        assert "Post-restart state" in result.message

    def test_failed_pre_state_fails(self):
        mod = CleanModule()
        result = run_recovery_cycle(
            "test_pre_fail",
            mod,
            {},
            pre_state_checker=lambda: False,
        )
        assert not result.passed
        assert not result.pre_state_valid
