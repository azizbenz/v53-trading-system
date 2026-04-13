"""Micro-edge exit governor reader for Build-14 SHADOW_ENABLED enablers."""

from __future__ import annotations

from complete_enablers.contracts import Build14EnablerSnapshot, Build14ObservationInput
from complete_enablers.enums import Build14Severity, Build14SignalFamily


def build_micro_edge_exit_governor_snapshot(
    observation: Build14ObservationInput,
) -> Build14EnablerSnapshot:
    """Estimate whether current exit conditions have become economically fragile."""

    cost_component = 1.0 if observation.break_even_drift_alert else 0.0
    sterilization_component = observation.cra_sterilization_rate
    ce_component = 1.0 if observation.ce_net < 0 else 0.5 if observation.ce_net < 0.001 else 0.0
    loss_component = min((observation.dtr_loss_count + observation.log_loss_count) / 2.0, 1.0)
    breakout_component = observation.breakout_failure_rate
    ghost_component = observation.ghost_liquidity_ratio
    stale_component = min(observation.stale_pair_count / 2.0, 1.0)
    exit_score = round(
        (0.23 * cost_component)
        + (0.19 * sterilization_component)
        + (0.18 * ce_component)
        + (0.14 * loss_component)
        + (0.12 * breakout_component)
        + (0.08 * ghost_component)
        + (0.06 * stale_component),
        4,
    )

    if exit_score >= 0.72:
        status = Build14Severity.CRITICAL
    elif exit_score >= 0.38:
        status = Build14Severity.ELEVATED
    else:
        status = Build14Severity.NOMINAL

    return Build14EnablerSnapshot(
        correlation_id=observation.correlation_id,
        signal_family=Build14SignalFamily.MICROSTRUCTURE,
        summary=(
            "Build-14 exit governor remains SHADOW_ENABLED and only contributes "
            "bounded exit-quality context"
        ),
        reader_name="micro_edge_exit_governor",
        observed_value=exit_score,
        status=status,
        detail=(
            f"break_even_drift={observation.break_even_drift_alert} / "
            f"cra_sterilization_rate={observation.cra_sterilization_rate:.2f} / "
            f"ce_net={observation.ce_net:.4f} / "
            f"breakout_failure_rate={observation.breakout_failure_rate:.2f}"
        ),
        evidence_refs=(
            f"break_even_drift={int(observation.break_even_drift_alert)}",
            f"cra_sterilization_rate={observation.cra_sterilization_rate:.2f}",
            f"ce_net={observation.ce_net:.4f}",
            f"breakout_failure_rate={observation.breakout_failure_rate:.2f}",
        ),
        structured_log_key="build14.shadow_enabled.micro_edge_exit_governor",
    )


__all__ = [
    "build_micro_edge_exit_governor_snapshot",
]
