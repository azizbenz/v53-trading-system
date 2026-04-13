"""Micro-edge entry timing reader for Build-14 SHADOW_ENABLED enablers."""

from __future__ import annotations

from complete_enablers.contracts import Build14EnablerSnapshot, Build14ObservationInput
from complete_enablers.enums import Build14Severity, Build14SignalFamily


def build_micro_edge_entry_timing_snapshot(
    observation: Build14ObservationInput,
) -> Build14EnablerSnapshot:
    """Estimate whether the current entry timing has become economically fragile."""

    support_component = 1.0 - observation.volume_support_ratio
    pressure_component = observation.adverse_obi_pressure
    sterilization_component = observation.cra_sterilization_rate
    backlog_component = min(observation.queue_backlog / 80.0, 1.0)
    stale_component = min(observation.stale_pair_count / 2.0, 1.0)
    cost_component = 1.0 if observation.break_even_drift_alert else 0.0
    ce_component = 1.0 if observation.ce_net < 0 else 0.5 if observation.ce_net < 0.001 else 0.0
    timing_score = round(
        (0.24 * support_component)
        + (0.18 * pressure_component)
        + (0.18 * sterilization_component)
        + (0.14 * backlog_component)
        + (0.10 * stale_component)
        + (0.08 * cost_component)
        + (0.08 * ce_component),
        4,
    )

    if timing_score >= 0.72:
        status = Build14Severity.CRITICAL
    elif timing_score >= 0.38:
        status = Build14Severity.ELEVATED
    else:
        status = Build14Severity.NOMINAL

    return Build14EnablerSnapshot(
        correlation_id=observation.correlation_id,
        signal_family=Build14SignalFamily.MICROSTRUCTURE,
        summary=(
            "Build-14 entry timing layer remains SHADOW_ENABLED and only contributes "
            "bounded timing context"
        ),
        reader_name="micro_edge_entry_timing_layer",
        observed_value=timing_score,
        status=status,
        detail=(
            f"volume_support_ratio={observation.volume_support_ratio:.2f} / "
            f"adverse_obi_pressure={observation.adverse_obi_pressure:.2f} / "
            f"cra_sterilization_rate={observation.cra_sterilization_rate:.2f} / "
            f"queue_backlog={observation.queue_backlog}"
        ),
        evidence_refs=(
            f"volume_support_ratio={observation.volume_support_ratio:.2f}",
            f"adverse_obi_pressure={observation.adverse_obi_pressure:.2f}",
            f"cra_sterilization_rate={observation.cra_sterilization_rate:.2f}",
            f"queue_backlog={observation.queue_backlog}",
        ),
        structured_log_key="build14.shadow_enabled.micro_edge_entry_timing_layer",
    )


__all__ = [
    "build_micro_edge_entry_timing_snapshot",
]
