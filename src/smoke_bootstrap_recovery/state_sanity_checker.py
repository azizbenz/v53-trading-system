"""
7.5.4 — State Sanity Checker: verify that restarted state is coherent.

Runs a set of named checks on a module's post-recovery state.
Reports each check individually and aggregates into a StateSanityResult.

Spec 7.9: no partially initialized state considered OK.
"""

from __future__ import annotations

from typing import Callable

from smoke_bootstrap_recovery.smoke_models import SmokeStatus, StateSanityResult


# A sanity check is a callable that returns (passed: bool, detail: str)
SanityCheck = Callable[[], tuple[bool, str]]


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
        return False, f"DAG violations: {report.error_count} errors"

    return _check
