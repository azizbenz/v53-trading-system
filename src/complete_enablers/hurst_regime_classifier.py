"""Hurst regime classifier reader for Build-14 SHADOW_ENABLED enablers."""

from __future__ import annotations

from complete_enablers.contracts import Build14EnablerSnapshot, Build14ObservationInput
from complete_enablers.enums import Build14Severity, Build14SignalFamily


def build_hurst_regime_snapshot(
    observation: Build14ObservationInput,
) -> Build14EnablerSnapshot:
    """Estimate regime instability from Hurst-derived drift away from neutral context."""

    hurst_distance = abs(observation.hurst_exponent - 0.50) * 2.0
    edge_component = min(observation.edge_degraded_count / 2.0, 1.0)
    drift_component = 1.0 if observation.break_even_drift_alert else 0.0
    regime_instability_score = round(
        (0.55 * hurst_distance)
        + (0.25 * edge_component)
        + (0.20 * drift_component),
        4,
    )
    if regime_instability_score >= 0.70:
        status = Build14Severity.CRITICAL
    elif regime_instability_score >= 0.35:
        status = Build14Severity.ELEVATED
    else:
        status = Build14Severity.NOMINAL

    return Build14EnablerSnapshot(
        correlation_id=observation.correlation_id,
        signal_family=Build14SignalFamily.REGIME,
        summary="Build-14 Hurst regime reader remains SHADOW_ENABLED and only enriches regime interpretation",
        reader_name="hurst_regime_classifier",
        observed_value=regime_instability_score,
        status=status,
        detail=(
            f"hurst_exponent={observation.hurst_exponent:.2f} / "
            f"edge_degraded_count={observation.edge_degraded_count} / "
            f"break_even_drift_alert={'yes' if observation.break_even_drift_alert else 'no'}"
        ),
        evidence_refs=(
            f"hurst_exponent={observation.hurst_exponent:.2f}",
            f"edge_degraded_count={observation.edge_degraded_count}",
        ),
        structured_log_key="build14.shadow_enabled.hurst_regime_classifier",
    )


__all__ = [
    "build_hurst_regime_snapshot",
]
