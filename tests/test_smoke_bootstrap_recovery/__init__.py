"""Tests Module 5 â€” state_sanity_checker: coherent post-recovery state."""

import pytest

from smoke_bootstrap_recovery.state_sanity_checker import (
    check_fd_leak,
    check_dag_clean,
    check_kill_switch_persisted,
    check_manifest_consistency,
    check_module_importable,
    run_sanity_checks,
)
from smoke_bootstrap_recovery.smoke_models import SmokeStatus


@pytest.mark.build1
class TestRunSanityChecks:
    """run_sanity_checks aggregation."""

    def test_all_checks_pass(self):
        checks = {
            "check_a": lambda: (True, "ok"),
            "check_b": lambda: (True, "fine"),
        }
        result = run_sanity_checks("test_mod", checks)
        assert result.passed
        assert result.checks_passed == 2
        assert result.checks_failed == 0
        assert len(result.anomalies) == 0

    def test_one_check_fails(self):
        checks = {
            "check_ok": lambda: (True, "ok"),
            "check_bad": lambda: (False, "something wrong"),
        }
        result = run_sanity_checks("test_mod", checks)
        assert not result.passed
        assert result.checks_passed == 1
        assert result.checks_failed == 1
        assert "check_bad" in result.anomalies[0]

    def test_check_raises_exception(self):
        def boom() -> tuple[bool, str]:
            raise ValueError("kaboom")

        checks = {"check_boom": boom}
        result = run_sanity_checks("test_mod", checks)
        assert not result.passed
        assert result.checks_failed == 1
        assert "ValueError" in result.anomalies[0]

    def test_no_checks_returns_skip(self):
        result = run_sanity_checks("test_mod", {})
        assert result.status == SmokeStatus.SKIP
        assert result.checks_passed == 0

    def test_all_fail(self):
        checks = {
            "a": lambda: (False, "bad a"),
            "b": lambda: (False, "bad b"),
        }
        result = run_sanity_checks("test_mod", checks)
        assert result.checks_failed == 2
        assert len(result.anomalies) == 2


@pytest.mark.build1
class TestBuiltInChecks:
    """Built-in sanity checks for Build-1."""

    def test_importable_check_passes(self):
        check = check_module_importable("interface_contracts")
        ok, detail = check()
        assert ok
        assert "importable" in detail

    def test_importable_check_fails(self):
        check = check_module_importable("nonexistent_xyz")
        ok, detail = check()
        assert not ok
        assert "not importable" in detail

    def test_manifest_consistency_passes(self):
        check = check_manifest_consistency()
        ok, detail = check()
        assert ok, f"Manifest inconsistent: {detail}"

    def test_dag_clean_passes(self):
        check = check_dag_clean()
        ok, detail = check()
        assert ok, f"DAG not clean: {detail}"

    def test_fd_leak_check_uses_injected_counter(self):
        check = check_fd_leak(10, fd_counter=lambda: 12)
        ok, detail = check()
        assert ok
        assert "No FD leak" in detail

    def test_fd_leak_check_fails_when_delta_exceeds_tolerance(self):
        check = check_fd_leak(10, fd_counter=lambda: 20)
        ok, detail = check()
        assert not ok
        assert "FD leak detected" in detail

    def test_fd_leak_check_fails_when_cumulative_count_exceeds_ceiling(self):
        check = check_fd_leak(10, fd_counter=lambda: 14, max_total_fd_count=13)
        ok, detail = check()
        assert not ok
        assert "cumulative FD count" in detail

    def test_kill_switch_persistence_with_fake_factory(self, repo_tmp_path):
        class FakeBreaker:
            def __init__(self, state_dir):
                self._state_dir = state_dir
                self._state_file = state_dir / "kill_switch_state.json"
                self.current_state = "armed"
                if self._state_file.exists():
                    self.current_state = "tripped"

            def trip(self, reason, detail):
                self.current_state = "tripped"
                self._state_file.write_text("tripped", encoding="utf-8")

            def is_trading_allowed(self):
                return self.current_state != "tripped"

        check = check_kill_switch_persisted(
            str(repo_tmp_path),
            breaker_factory=FakeBreaker,
            trip_reason="reason",
            tripped_state="tripped",
        )
        ok, detail = check()
        assert ok
        assert "verified" in detail.lower()
