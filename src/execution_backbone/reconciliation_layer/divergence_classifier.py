"""
Build-3 / reconciliation_layer / divergence_classifier
Classify divergence severity: warning, blocking, critical.

Invariant: every divergence has a severity. No silent critical divergence.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class DivergenceSeverity(StrEnum):
    INFO = "info"  # minor, within tolerance
    WARNING = "warning"  # notable but not blocking
    BLOCKING = "blocking"  # prevents new orders
    CRITICAL = "critical"  # requires immediate intervention


class ClassifiedDivergence(BaseModel, frozen=True):
    """A divergence with severity classification."""

    source: str  # "order" | "fill" | "position"
    detail: str
    severity: DivergenceSeverity
    abs_diff: float = 0.0


class DivergenceClassification(BaseModel, frozen=True):
    """Overall divergence classification result."""

    max_severity: DivergenceSeverity
    is_blocking: bool
    is_critical: bool
    total_divergences: int
    classified: tuple[ClassifiedDivergence, ...] = ()


def classify_divergence(
    source: str,
    detail: str,
    abs_diff: float,
    warning_threshold: float = 0.01,
    blocking_threshold: float = 0.1,
    critical_threshold: float = 1.0,
) -> ClassifiedDivergence:
    """Classify a single divergence by severity thresholds."""
    if abs_diff >= critical_threshold:
        severity = DivergenceSeverity.CRITICAL
    elif abs_diff >= blocking_threshold:
        severity = DivergenceSeverity.BLOCKING
    elif abs_diff >= warning_threshold:
        severity = DivergenceSeverity.WARNING
    else:
        severity = DivergenceSeverity.INFO

    return ClassifiedDivergence(
        source=source,
        detail=detail,
        severity=severity,
        abs_diff=abs_diff,
    )


def classify_all(
    divergences: tuple[ClassifiedDivergence, ...],
) -> DivergenceClassification:
    """Produce overall classification from individual divergences."""
    if not divergences:
        return DivergenceClassification(
            max_severity=DivergenceSeverity.INFO,
            is_blocking=False,
            is_critical=False,
            total_divergences=0,
        )

    severity_order = {
        DivergenceSeverity.INFO: 0,
        DivergenceSeverity.WARNING: 1,
        DivergenceSeverity.BLOCKING: 2,
        DivergenceSeverity.CRITICAL: 3,
    }

    max_sev = max(divergences, key=lambda d: severity_order.get(d.severity, 0)).severity

    return DivergenceClassification(
        max_severity=max_sev,
        is_blocking=severity_order[max_sev] >= severity_order[DivergenceSeverity.BLOCKING],
        is_critical=max_sev == DivergenceSeverity.CRITICAL,
        total_divergences=len(divergences),
        classified=divergences,
    )
