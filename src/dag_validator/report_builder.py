"""
5.5.5 — Report Builder: produce human-readable + machine-exploitable validation report.

Aggregates results from all sub-validators into a single ValidationReport.
Provides both structured data (for CI) and formatted text (for humans).
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from dag_validator.cycle_detector import CycleResult
from dag_validator.dependency_matcher import MatchResult
from dag_validator.layer_validator import LayerResult


class Severity(StrEnum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ReportEntry(BaseModel, frozen=True):
    """Single line item in the report."""

    severity: Severity
    category: str  # "cycle" | "unauthorized_import" | "missing_from_manifest" | "layer_violation"
    message: str


class ValidationReport(BaseModel, frozen=True):
    """Complete validation report — the final output of dag_validator.

    Spec 5.7: statut pass/fail, violations, cycles, imports suspects, rapport versionné.
    """

    manifest_version: str
    passed: bool
    entries: tuple[ReportEntry, ...]
    cycle_count: int = 0
    violation_count: int = 0
    layer_violation_count: int = 0
    declared_dynamic_import_count: int = 0
    undeclared_dynamic_import_count: int = 0
    files_scanned: int = 0
    total_imports: int = 0
    authorized_imports: int = 0
    scan_errors: tuple[str, ...] = ()

    @property
    def error_count(self) -> int:
        return sum(1 for e in self.entries if e.severity == Severity.ERROR)

    @property
    def warning_count(self) -> int:
        return sum(1 for e in self.entries if e.severity == Severity.WARNING)


def build_report(
    match_result: MatchResult,
    cycle_result: CycleResult,
    layer_result: LayerResult,
    manifest_version: str,
    files_scanned: int = 0,
    scan_errors: tuple[str, ...] = (),
) -> ValidationReport:
    """Build a complete validation report from sub-validator results.

    Spec 5.10: distinction claire entre erreur et warning.
    Spec 5.10: impossible de passer silencieusement une violation critique.

    Critical violations (ERROR) — cause pass=False:
    - Cycles
    - Unauthorized imports
    - Layer hierarchy violations

    Non-critical (WARNING):
    - Scan errors (files that couldn't be parsed)
    """
    entries: list[ReportEntry] = []

    # Cycles are CRITICAL
    for cycle in cycle_result.cycles:
        cycle_str = " -> ".join(cycle) + " -> " + cycle[0]
        entries.append(ReportEntry(
            severity=Severity.ERROR,
            category="cycle",
            message=f"Dependency cycle detected: {cycle_str}",
        ))

    # Dependency violations are CRITICAL
    for v in match_result.violations:
        entries.append(ReportEntry(
            severity=Severity.ERROR,
            category=v.violation_type,
            message=v.message,
        ))

    # Layer violations are CRITICAL
    for lv in layer_result.violations:
        entries.append(ReportEntry(
            severity=Severity.ERROR,
            category="layer_violation",
            message=lv.message,
        ))

    for record in match_result.declared_dynamic_imports:
        entries.append(ReportEntry(
            severity=Severity.INFO,
            category="declared_dynamic_import",
            message=(
                f"Declared dynamic import {record.call_text} "
                f"in {record.source_file}:{record.line_number}"
            ),
        ))

    for record in match_result.undeclared_dynamic_imports:
        entries.append(ReportEntry(
            severity=Severity.WARNING,
            category="dynamic_import",
            message=(
                f"Undeclared dynamic import {record.call_text} "
                f"in {record.source_file}:{record.line_number}"
            ),
        ))

    # Scan errors are warnings
    for err in scan_errors:
        entries.append(ReportEntry(
            severity=Severity.WARNING,
            category="scan_error",
            message=err,
        ))

    # Pass only if zero errors — spec 5.9: aucune violation silencieuse
    has_errors = any(e.severity == Severity.ERROR for e in entries)
    has_undeclared_dynamic_imports = len(match_result.undeclared_dynamic_imports) > 0

    return ValidationReport(
        manifest_version=manifest_version,
        passed=not has_errors and not has_undeclared_dynamic_imports,
        entries=tuple(entries),
        cycle_count=cycle_result.cycle_count,
        violation_count=len(match_result.violations),
        layer_violation_count=len(layer_result.violations),
        declared_dynamic_import_count=len(match_result.declared_dynamic_imports),
        undeclared_dynamic_import_count=len(match_result.undeclared_dynamic_imports),
        files_scanned=files_scanned,
        total_imports=match_result.total_imports,
        authorized_imports=match_result.authorized_count,
        scan_errors=scan_errors,
    )


def format_report(report: ValidationReport) -> str:
    """Format a ValidationReport as human-readable text.

    Spec 5.13: logs attendus (version manifest, violations, warnings, résultat global).
    """
    lines: list[str] = [
        "=" * 60,
        "  DAG VALIDATOR — VALIDATION REPORT",
        "=" * 60,
        f"Manifest version : {report.manifest_version}",
        f"Files scanned    : {report.files_scanned}",
        f"Total imports    : {report.total_imports}",
        f"Authorized       : {report.authorized_imports}",
        f"Cycles           : {report.cycle_count}",
        f"Violations       : {report.violation_count}",
        f"Layer violations : {report.layer_violation_count}",
        f"Declared dyn     : {report.declared_dynamic_import_count}",
        f"Undeclared dyn   : {report.undeclared_dynamic_import_count}",
        "-" * 60,
    ]

    if report.entries:
        for entry in report.entries:
            if entry.severity == Severity.ERROR:
                prefix = "ERROR"
            elif entry.severity == Severity.WARNING:
                prefix = "WARN "
            else:
                prefix = "INFO "
            lines.append(f"  [{prefix}] [{entry.category}] {entry.message}")
    else:
        lines.append("  No issues found.")

    lines.append("-" * 60)
    verdict = "PASS" if report.passed else "FAIL"
    lines.append(f"  VERDICT: {verdict}")
    lines.append("=" * 60)

    return "\n".join(lines)
