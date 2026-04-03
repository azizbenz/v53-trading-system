"""False-breakout reader for Build-14 SHADOW_ENABLED enablers."""

from __future__ import annotations

from complete_enablers.contracts import Build14EnablerSnapshot, Build14ObservationInput
from complete_enablers.enums import Build14Severity, Build14SignalFamily


def build_false_breakout_snapshot(observation: Build14ObservationInput) -> Build14EnablerSnapshot:
    """Estimate breakout fragility from governed breakout-support facts only."""

    breakout_component = observation.breakout_failure_rate
    support_component = 1.0 - observation.volume_support_ratio
    sterilization_component = observation.cra_sterilization_rate
    drift_component = 1.0 if observation.break_even_drift_alert else 0.0
    false_breakout_score = round(
        (0.45 * breakout_component)
        + (0.30 * support_component)
        + (0.15 * sterilization_component)
        + (0.10 * drift_component),
        4,
    )
    if false_breakout_score >= 0.70:
        status = Build14Severity.CRITICAL
    elif false_breakout_score >= 0.35:
        status = Build14Severity.ELEVATED
    else:
        status = Build14Severity.NOMINAL

    return Build14EnablerSnapshot(
        correlation_id=observation.correlation_id,
        signal_family=Build14SignalFamily.MICROSTRUCTURE,
        summary="Build-14 false-breakout reader remains SHADOW_ENABLED and never trades autonomously",
        reader_name="false_breakout_model",
        observed_value=false_breakout_score,
        status=status,
        detail=(
            "breakout_failure_rate="
            f"{observation.breakout_failure_rate:.2f} / "
            f"volume_support_ratio={observation.volume_support_ratio:.2f} / "
            f"cra_sterilization_rate={observation.cra_sterilization_rate:.2f}"
        ),
        evidence_refs=(
            f"breakout_failure_rate={observation.breakout_failure_rate:.2f}",
            f"volume_support_ratio={observation.volume_support_ratio:.2f}",
            f"break_even_drift_alert={'yes' if observation.break_even_drift_alert else 'no'}",
        ),
        structured_log_key="build14.shadow_enabled.false_breakout_model",
    )


__all__ = [
    "build_false_breakout_snapshot",
]
