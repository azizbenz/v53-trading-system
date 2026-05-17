"""
7.5.5 — Smoke Reporter: produce human-readable + machine-exploitable smoke reports.

Spec 7.13: logs target module, bootstrap start/end, recovery, config verdict,
final state, anomalies.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from smoke_bootstrap_recovery.smoke_models import (
    BootstrapResult,
    ConfigCheckResult,
    ModuleSmokeReport,
    RecoveryResult,
    SmokeReport,
    SmokeStatus,
    StateSanityResult,
)


def build_smoke_report(
    module_reports: tuple[ModuleSmokeReport, ...],
) -> SmokeReport:
    """Build a top-level SmokeReport from individual module reports.

    Spec 7.9: no partial init considered OK.
    Passed only if ALL module reports pass.
    """
    all_passed = all(m.all_passed for m in module_reports) and len(module_reports) > 0
    return SmokeReport(
        module_reports=module_reports,
        passed=all_passed,
    )


def format_smoke_report(report: SmokeReport) -> str:
    """Format a SmokeReport as human-readable text.

    Spec 7.13: target module, bootstrap, recovery, config, state, anomalies.
    """
    lines: list[str] = [
        "=" * 60,
        "  SMOKE BOOTSTRAP RECOVERY — REPORT",
        "=" * 60,
        f"Modules tested : {report.total_modules}",
        f"Passed         : {report.modules_passed}",
        f"Failed         : {report.modules_failed}",
        "-" * 60,
    ]

    for mr in report.module_reports:
        lines.append(f"\n  Module: {mr.module_name}")
        lines.append(f"  {'─' * 40}")

        if mr.bootstrap is not None:
            lines.append(f"    Bootstrap  : {mr.bootstrap.status.value.upper()}"
                        f"  ({mr.bootstrap.duration_ms:.1f}ms)")
            if mr.bootstrap.message:
                lines.append(f"                 {mr.bootstrap.message}")

        if mr.config_check is not None:
            lines.append(f"    Config     : {mr.config_check.status.value.upper()}")
            if mr.config_check.missing_keys:
                lines.append(f"                 Missing: {list(mr.config_check.missing_keys)}")
            if mr.config_check.invalid_keys:
                lines.append(f"                 Invalid: {list(mr.config_check.invalid_keys)}")

        if mr.recovery is not None:
            lines.append(f"    Recovery   : {mr.recovery.status.value.upper()}"
                        f"  ({mr.recovery.duration_ms:.1f}ms)")
            lines.append(f"                 Pre-state: {'OK' if mr.recovery.pre_state_valid else 'FAIL'}")
            lines.append(f"                 Post-state: {'OK' if mr.recovery.post_state_valid else 'FAIL'}")
            if mr.recovery.message:
                lines.append(f"                 {mr.recovery.message}")

        if mr.state_sanity is not None:
            lines.append(f"    Sanity     : {mr.state_sanity.status.value.upper()}"
                        f"  ({mr.state_sanity.checks_passed}p/{mr.state_sanity.checks_failed}f)")
            for anomaly in mr.state_sanity.anomalies:
                lines.append(f"                 ! {anomaly}")

    lines.append("")
    lines.append("-" * 60)
    verdict = "PASS" if report.passed else "FAIL"
    lines.append(f"  VERDICT: {verdict}")
    lines.append("=" * 60)

    return "\n".join(lines)


def build_build1_core_health_payload(report: SmokeReport) -> dict[str, object]:
    """Build a compact operator-facing Build-1 health payload from a smoke report."""

    module_map = {module.module_name: module for module in report.module_reports}
    manifest_status, manifest_reasons = _extract_named_check_status(
        module_map.get("manifest_registry"),
        "manifest_consistency",
    )
    dag_status, dag_reasons = _extract_named_check_status(
        module_map.get("dag_validator"),
        "dag_clean",
    )
    guardrail_status, guardrail_reasons = _extract_named_check_status(
        module_map.get("smoke_bootstrap_recovery"),
        "engineering_guardrails",
    )
    smoke_status = "PASS" if report.passed else "FAIL"
    core_health_status = (
        "PASS"
        if manifest_status == "PASS"
        and dag_status == "PASS"
        and guardrail_status == "PASS"
        and smoke_status == "PASS"
        else "BLOCKED"
    )
    reason_codes = tuple(
        reason
        for reasons in (
            manifest_reasons,
            dag_reasons,
            guardrail_reasons,
        )
        for reason in reasons
    )
    return {
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "build1_manifest_status": manifest_status,
        "build1_dag_status": dag_status,
        "build1_guardrail_status": guardrail_status,
        "build1_smoke_status": smoke_status,
        "build1_core_health_status": core_health_status,
        "reason_codes": list(reason_codes),
    }


def write_build1_core_health_payload(
    output_path: Path,
    *,
    report: SmokeReport,
) -> Path:
    """Persist the Build-1 core health payload as JSON."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = build_build1_core_health_payload(report)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return output_path


def _extract_named_check_status(
    module_report: ModuleSmokeReport | None,
    check_name: str,
) -> tuple[str, tuple[str, ...]]:
    if module_report is None or module_report.state_sanity is None:
        return "NOT_PROVEN", (f"{check_name}: state_sanity_missing",)
    anomalies = tuple(
        anomaly
        for anomaly in module_report.state_sanity.anomalies
        if anomaly.startswith(f"{check_name}:")
    )
    if anomalies:
        return "FAIL", anomalies
    return "PASS", ()
