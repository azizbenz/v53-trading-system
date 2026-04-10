"""
7.5.4 — State Sanity Checker: verify that restarted state is coherent.

Runs a set of named checks on a module's post-recovery state.
Reports each check individually and aggregates into a StateSanityResult.

Spec 7.9: no partially initialized state considered OK.
"""

from __future__ import annotations

from typing import Any, Callable

from smoke_bootstrap_recovery.smoke_models import SmokeStatus, StateSanityResult


# A sanity check is a callable that returns (passed: bool, detail: str)
SanityCheck = Callable[[], tuple[bool, str]]
FD_LEAK_DELTA_TOLERANCE = 5


def capture_fd_count(fd_counter: Callable[[], int | None] | None = None) -> int | None:
    """Return a platform-appropriate FD/handle count, or None if unavailable."""
    if fd_counter is not None:
        return fd_counter()

    import os

    proc_fd = f"/proc/{os.getpid()}/fd"
    if os.path.isdir(proc_fd):
        return len(os.listdir(proc_fd))

    try:
        import psutil
        proc = psutil.Process(os.getpid())
        if hasattr(proc, "num_fds"):
            return proc.num_fds()
        if hasattr(proc, "num_handles"):
            return proc.num_handles()
    except ImportError:
        return None

    return None


def run_sanity_checks(
    module_name: str,
    checks: dict[str, SanityCheck],
) -> StateSanityResult:
    """Run all sanity checks and aggregate results.

    Args:
        module_name: Name of the module being checked.
        checks: Dict of check_name -> callable that returns (passed, detail).

    Returns:
        StateSanityResult with aggregated pass/fail counts and anomalies.
    """
    passed_count = 0
    failed_count = 0
    anomalies: list[str] = []

    for check_name, check_fn in checks.items():
        try:
            ok, detail = check_fn()
            if ok:
                passed_count += 1
            else:
                failed_count += 1
                anomalies.append(f"{check_name}: {detail}")
        except Exception as exc:
            failed_count += 1
            anomalies.append(f"{check_name}: raised {type(exc).__name__}: {exc}")

    if failed_count > 0:
        status = SmokeStatus.FAIL
        message = f"{failed_count} sanity check(s) failed"
    elif passed_count == 0:
        status = SmokeStatus.SKIP
        message = "No sanity checks defined"
    else:
        status = SmokeStatus.PASS
        message = f"All {passed_count} sanity check(s) passed"

    return StateSanityResult(
        module_name=module_name,
        status=status,
        checks_passed=passed_count,
        checks_failed=failed_count,
        anomalies=tuple(anomalies),
        message=message,
    )


# ─── BUILT-IN CHECKS FOR BUILD-1 ────────────────────────────────────

def check_module_importable(module_name: str) -> SanityCheck:
    """Create a sanity check that verifies a module is importable."""
    def _check() -> tuple[bool, str]:
        try:
            __import__(module_name)
            return True, "importable"
        except Exception as exc:
            return False, f"not importable: {exc}"
    return _check


def check_manifest_consistency() -> SanityCheck:
    """Check that manifest_registry is internally consistent."""
    def _check() -> tuple[bool, str]:
        from manifest_registry.module_inventory import validate_no_duplicates
        from manifest_registry.dependency_registry import (
            validate_all_modules_registered,
            validate_no_self_dependency,
            validate_no_unknown_targets,
        )
        from manifest_registry.build_order_registry import (
            validate_build_order_coherent,
            validate_modules_have_stages,
        )

        errors: list[str] = []
        if not validate_no_duplicates():
            errors.append("duplicate module names")
        missing = validate_all_modules_registered()
        if missing:
            errors.append(f"missing dep entries: {missing}")
        self_deps = validate_no_self_dependency()
        if self_deps:
            errors.append(f"self-deps: {self_deps}")
        unknown = validate_no_unknown_targets()
        if unknown:
            errors.append(f"unknown targets: {unknown}")
        build_errs = validate_build_order_coherent()
        if build_errs:
            errors.append(f"build order: {build_errs}")
        unstaged = validate_modules_have_stages()
        if unstaged:
            errors.append(f"modules without stage: {unstaged}")

        if errors:
            return False, "; ".join(errors)
        return True, "manifest consistent"

    return _check


def check_dag_clean() -> SanityCheck:
    """Check that the DAG validator passes on the real codebase."""
    def _check() -> tuple[bool, str]:
        from pathlib import Path
        from dag_validator import validate_architecture

        src_root = Path(__file__).resolve().parent.parent
        report = validate_architecture(src_root=src_root)
        if report.passed:
            return True, "DAG clean"

        details: list[str] = []
        if report.error_count:
            details.append(f"{report.error_count} error(s)")
        if report.undeclared_dynamic_import_count:
            details.append(
                f"{report.undeclared_dynamic_import_count} undeclared dynamic import(s)"
            )
        if not details:
            details.append("report not clean")
        return False, "DAG violations: " + ", ".join(details)

    return _check


# ─── GEM-19 / GEM-10: ADDITIONAL BUILD-1 SMOKE CHECKS ──────────────

def check_fd_leak(
    before_fd_count: int | None,
    fd_counter: Callable[[], int | None] | None = None,
    *,
    max_total_fd_count: int | None = None,
) -> SanityCheck:
    """GEM-19: verify no file descriptor leak after shutdown/restart cycle.

    Args:
        before_fd_count: FD count captured before the bootstrap cycle.
        max_total_fd_count: Optional absolute FD ceiling used to catch
            cumulative leaks across repeated cycles in the same process.
    """
    def _check() -> tuple[bool, str]:
        try:
            if before_fd_count is None:
                return True, "FD leak check skipped (no baseline available)"

            current = capture_fd_count(fd_counter)
            if current is None:
                return True, "FD leak check skipped (no /proc or psutil)"

            leaked = current - before_fd_count
            if leaked > FD_LEAK_DELTA_TOLERANCE:  # tolerance for transient FDs
                return False, f"FD leak detected: {leaked} extra FDs ({before_fd_count} → {current})"
            if max_total_fd_count is not None and current > max_total_fd_count:
                return (
                    False,
                    f"FD leak detected: cumulative FD count {current} exceeds ceiling "
                    f"{max_total_fd_count} ({before_fd_count} → {current})",
                )
            return True, f"No FD leak ({before_fd_count} → {current})"
        except Exception as exc:
            return False, f"FD check error: {exc}"

    return _check


def check_kill_switch_persisted(
    state_dir_path: str | None,
    breaker_factory: Any = None,
    trip_reason: Any = None,
    tripped_state: Any = None,
) -> SanityCheck:
    """GEM-10: verify kill switch state survives on disk after trip.

    Tests that:
    1. Tripping the kill switch creates a persisted state file.
    2. A new instance reads the tripped state.
    3. Trading is blocked after reload.

    Accepts factory/enum values as parameters to avoid importing
    risk_backbone (which would violate the DAG layering).
    Caller is responsible for passing:
      - breaker_factory: callable(state_dir=Path) -> breaker instance
      - trip_reason: the reason enum value to pass to breaker.trip()
      - tripped_state: the expected state enum value after trip
    """
    def _check() -> tuple[bool, str]:
        if breaker_factory is None or trip_reason is None or tripped_state is None:
            return False, "Kill switch check requires breaker_factory, trip_reason, and tripped_state"

        from pathlib import Path
        import shutil
        from uuid import uuid4

        if not state_dir_path:
            return False, "Kill switch check requires a writable state_dir_path"

        root_dir = Path(state_dir_path)
        root_dir.mkdir(parents=True, exist_ok=True)
        test_dir = root_dir / f"kill_switch_smoke_{uuid4().hex}"
        test_dir.mkdir()
        try:
            # Create and trip
            breaker = breaker_factory(state_dir=test_dir)
            breaker.trip(trip_reason, "smoke test")

            if breaker.is_trading_allowed():
                return False, "Trading still allowed after trip"

            # Verify file exists
            state_file = test_dir / "kill_switch_state.json"
            if not state_file.exists():
                return False, "Kill switch state file not persisted to disk"

            # Simulate restart: new instance should read tripped state
            breaker2 = breaker_factory(state_dir=test_dir)
            if breaker2.is_trading_allowed():
                return False, "New instance did not restore tripped state from disk"
            if breaker2.current_state != tripped_state:
                return False, f"Restored state is {breaker2.current_state}, expected {tripped_state}"

            return True, "Kill switch persistence verified"
        finally:
            # Cleanup
            shutil.rmtree(test_dir, ignore_errors=True)

    return _check
