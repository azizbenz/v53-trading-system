"""
Build-3 / reconciliation_layer / divergence_classifier
Classify divergence severity: warning, blocking, critical.

Invariant: every divergence has a severity. No silent critical divergence.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


class DivergenceSeverity(StrEnum):
    INFO = "info"  # minor, within tolerance
    WARNING = "warning"  # notable but not blocking
    BLOCKING = "blocking"  # prevents new orders
    CRITICAL = "critical"  # requires immediate intervention


class DivergenceSource(StrEnum):
    ORDER = "order"
    FILL = "fill"
    POSITION = "position"


class DivergenceThresholdPolicy(BaseModel, frozen=True):
    """Typed divergence thresholds scoped by source and unit."""

    policy_id: str = Field(..., min_length=1)
    source: DivergenceSource
    unit: str = Field(..., min_length=1)
    warning_threshold: float = Field(..., ge=0.0)
    blocking_threshold: float = Field(..., ge=0.0)
    critical_threshold: float = Field(..., ge=0.0)

    @model_validator(mode="after")
    def validate_threshold_order(self) -> "DivergenceThresholdPolicy":
        if not (
            self.warning_threshold <= self.blocking_threshold <= self.critical_threshold
        ):
            raise ValueError(
                "divergence thresholds must satisfy warning <= blocking <= critical"
            )
        return self


ORDER_DIVERGENCE_THRESHOLD_POLICY = DivergenceThresholdPolicy(
    policy_id="order_divergence.thresholds.v1",
    source=DivergenceSource.ORDER,
    unit="order_divergence_count",
    warning_threshold=1.0,
    blocking_threshold=2.0,
    critical_threshold=5.0,
)

FILL_DIVERGENCE_THRESHOLD_POLICY = DivergenceThresholdPolicy(
    policy_id="fill_divergence.thresholds.v1",
    source=DivergenceSource.FILL,
    unit="filled_quantity_units",
    warning_threshold=0.01,
    blocking_threshold=0.1,
    critical_threshold=1.0,
)

POSITION_DIVERGENCE_THRESHOLD_POLICY = DivergenceThresholdPolicy(
    policy_id="position_divergence.thresholds.v1",
    source=DivergenceSource.POSITION,
    unit="position_quantity_units",
    warning_threshold=0.01,
    blocking_threshold=0.1,
    critical_threshold=1.0,
)

_DIVERGENCE_THRESHOLD_POLICIES = {
    DivergenceSource.ORDER: ORDER_DIVERGENCE_THRESHOLD_POLICY,
    DivergenceSource.FILL: FILL_DIVERGENCE_THRESHOLD_POLICY,
    DivergenceSource.POSITION: POSITION_DIVERGENCE_THRESHOLD_POLICY,
}


def resolve_divergence_threshold_policy(source: str) -> DivergenceThresholdPolicy:
    return _DIVERGENCE_THRESHOLD_POLICIES[DivergenceSource(source)]


class ClassifiedDivergence(BaseModel, frozen=True):
    """A divergence with severity classification."""

    source: str  # "order" | "fill" | "position"
    detail: str
    severity: DivergenceSeverity
    abs_diff: float = 0.0
    policy_id: str = Field(..., min_length=1)
    unit: str = Field(..., min_length=1)
    warning_threshold: float = 0.0
    blocking_threshold: float = 0.0
    critical_threshold: float = 0.0


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
) -> ClassifiedDivergence:
    """Classify a single divergence by source-scoped severity thresholds."""
    policy = resolve_divergence_threshold_policy(source)

    if abs_diff >= policy.critical_threshold:
        severity = DivergenceSeverity.CRITICAL
    elif abs_diff >= policy.blocking_threshold:
        severity = DivergenceSeverity.BLOCKING
    elif abs_diff >= policy.warning_threshold:
        severity = DivergenceSeverity.WARNING
    else:
        severity = DivergenceSeverity.INFO

    return ClassifiedDivergence(
        source=policy.source.value,
        detail=detail,
        severity=severity,
        abs_diff=abs_diff,
        policy_id=policy.policy_id,
        unit=policy.unit,
        warning_threshold=policy.warning_threshold,
        blocking_threshold=policy.blocking_threshold,
        critical_threshold=policy.critical_threshold,
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
