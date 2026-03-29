"""Read-only execution fragility reader for Build-14."""

from __future__ import annotations

from complete_enablers.contracts import Build14EnablerSnapshot, Build14ObservationInput
from complete_enablers.enums import Build14Severity, Build14SignalFamily


def build_execution_fragility_score(observation: Build14ObservationInput) -> Build14EnablerSnapshot:
    """Estimate execution fragility from existing Build-9/10 facts."""

    drift_component = 1.0 if observation.break_even_drift_alert else 0.0
    degraded_component = min(observation.edge_degraded_count / 2.0, 1.0)
    ce_component = 1.0 if observation.ce_net < 0 else 0.5 if observation.ce_net < 0.001 else 0.0
    loss_component = min((observation.dtr_loss_count + observation.log_loss_count) / 2.0, 1.0)
    fragility_score = round(
        (0.35 * drift_component)
        + (0.30 * degraded_component)
        + (0.20 * ce_component)
        + (0.15 * loss_component),
        4,
    )

    if fragility_score >= 0.75:
        status = Build14Severity.CRITICAL
    elif fragility_score >= 0.40:
        status = Build14Severity.ELEVATED
    else:
        status = Build14Severity.NOMINAL

    return Build14EnablerSnapshot(
        correlation_id=observation.correlation_id,
        signal_family=Build14SignalFamily.AI_EDGE,
        summary=f"Execution fragility {status} at {fragility_score:.2f}",
        reader_name="execution_fragility_score",
        observed_value=fragility_score,
        status=status,
        detail=(
            f"break_even_drift={observation.break_even_drift_alert}, "
            f"edge_degraded={observation.edge_degraded_count}, ce_net={observation.ce_net:.6f}"
        ),
        evidence_refs=(
            f"break_even_drift:{int(observation.break_even_drift_alert)}",
            f"edge_degraded_count:{observation.edge_degraded_count}",
            f"ce_net:{observation.ce_net:.6f}",
        ),
        structured_log_key="build14.read_only.execution_fragility",
    )


__all__ = [
    "build_execution_fragility_score",
]
