"""
6.5.5 — Contract Reporter: produce human + machine-readable contract reports.

Spec 6.13: logs module, contract, status, duration, failure reason.
Spec 6.9: broken contract must fail the build.
"""

from __future__ import annotations

from contract_test_suite.contract_models import (
    ContractStatus,
    ModuleContractReport,
    SuiteReport,
)


def build_suite_report(
    module_reports: list[ModuleContractReport],
) -> SuiteReport:
    """Build a top-level SuiteReport from module reports.

    Spec 6.9: passed=False if ANY critical contract fails.
    """
    has_critical_failure = any(m.has_critical_failure for m in module_reports)
    return SuiteReport(
        module_reports=tuple(module_reports),
        passed=not has_critical_failure,
    )


def format_suite_report(report: SuiteReport) -> str:
    """Format a SuiteReport as human-readable text.

    Spec 6.13: module, contract, status, duration, failure reason.
    """
    lines: list[str] = [
        "=" * 60,
        "  CONTRACT TEST SUITE — REPORT",
        "=" * 60,
        f"Total contracts : {report.total_contracts}",
        f"Passed          : {report.total_passed}",
        f"Failed          : {report.total_failed}",
        "-" * 60,
    ]

    for mod_report in report.module_reports:
        lines.append(f"\n  Module: {mod_report.module_name}")
        lines.append(f"  Tests: {mod_report.total}  Passed: {mod_report.passed_count}  Failed: {mod_report.failed_count}")

        for r in mod_report.results:
            status_icon = r.status.value.upper()  # PASS / FAIL / ERROR / SKIP
            crit = " [CRITICAL]" if r.contract.critical and r.failed else ""
            line = f"    [{status_icon}] {r.contract.contract_name}{crit}"
            if r.duration_ms > 0:
                line += f" ({r.duration_ms:.1f}ms)"
            if r.message and not r.passed:
                line += f"\n           Reason: {r.message}"
            lines.append(line)

    lines.append("\n" + "-" * 60)
    verdict = "PASS" if report.passed else "FAIL"
    lines.append(f"  VERDICT: {verdict}")
    lines.append("=" * 60)

    return "\n".join(lines)
