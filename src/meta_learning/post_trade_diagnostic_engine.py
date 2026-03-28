"""Build governed diagnostics from real Build-9 outputs."""

from __future__ import annotations

from meta_learning.contracts import DiagnosticResult, TradeLearningInput
from meta_learning.enums import DiagnosticSeverity
from meta_minimal.break_even_dashboard.break_even_reporter import BreakEvenReport
from meta_minimal.cra_monitor.cra_reporter import CRAReport
from meta_minimal.dtr_core.dtr_reporter import DTRSummary
from meta_minimal.edge_tracker_prudent_minimal.edge_reporter import EdgeReport


def build_post_trade_diagnostics(
    trade_input: TradeLearningInput,
    dtr_summary: DTRSummary,
    cra_report: CRAReport,
    break_even_report: BreakEvenReport,
    edge_report: EdgeReport,
) -> tuple[DiagnosticResult, ...]:
    """Build a governed diagnostic set without touching the live path."""

    diagnostics: list[DiagnosticResult] = []

    if dtr_summary.dtr_coverage < 0.80:
        severity = DiagnosticSeverity.CRITICAL if dtr_summary.dtr_coverage < 0.50 else DiagnosticSeverity.WARNING
        diagnostics.append(DiagnosticResult(
            diagnostic_id=f"{trade_input.correlation_id}:trace_coverage",
            correlation_id=trade_input.correlation_id,
            category="trace_coverage",
            summary=f"DTR coverage too low at {dtr_summary.dtr_coverage:.2%}",
            severity=severity,
            evidence_refs=tuple(trade_input.dtr_ids),
            structured_log_key="build9x.diagnostic.trace_coverage",
        ))

    if cra_report.sterilization_rate >= 0.20:
        severity = DiagnosticSeverity.CRITICAL if cra_report.sterilization_rate >= 0.40 else DiagnosticSeverity.WARNING
        diagnostics.append(DiagnosticResult(
            diagnostic_id=f"{trade_input.correlation_id}:sterilization",
            correlation_id=trade_input.correlation_id,
            category="sterilization",
            summary=f"CRA sterilization elevated at {cra_report.sterilization_rate:.2%}",
            severity=severity,
            evidence_refs=tuple(alert.scope for alert in cra_report.alerts),
            structured_log_key="build9x.diagnostic.sterilization",
        ))

    if break_even_report.has_cost_drift_alert:
        diagnostics.append(DiagnosticResult(
            diagnostic_id=f"{trade_input.correlation_id}:cost_drift",
            correlation_id=trade_input.correlation_id,
            category="cost_drift",
            summary="Break-even dashboard reports material cost drift",
            severity=DiagnosticSeverity.WARNING,
            evidence_refs=break_even_report.cost_drift_alert_scopes,
            structured_log_key="build9x.diagnostic.cost_drift",
        ))

    if edge_report.degraded_count > 0:
        diagnostics.append(DiagnosticResult(
            diagnostic_id=f"{trade_input.correlation_id}:edge_degraded",
            correlation_id=trade_input.correlation_id,
            category="edge_degraded",
            summary=f"{edge_report.degraded_count} degraded edge scope(s) detected",
            severity=DiagnosticSeverity.WARNING,
            evidence_refs=edge_report.drift_scopes,
            structured_log_key="build9x.diagnostic.edge_degraded",
        ))

    if not diagnostics:
        diagnostics.append(DiagnosticResult(
            diagnostic_id=f"{trade_input.correlation_id}:no_issue",
            correlation_id=trade_input.correlation_id,
            category="no_issue",
            summary="No material post-trade issue detected",
            severity=DiagnosticSeverity.INFO,
            evidence_refs=tuple(trade_input.dtr_ids),
            structured_log_key="build9x.diagnostic.no_issue",
        ))

    return tuple(diagnostics)


__all__ = [
    "build_post_trade_diagnostics",
]
