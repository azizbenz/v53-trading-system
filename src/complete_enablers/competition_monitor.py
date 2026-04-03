"""Competition monitor reader for Build-14 SHADOW_ENABLED enablers."""

from __future__ import annotations

from complete_enablers.contracts import Build14EnablerSnapshot, Build14ObservationInput
from complete_enablers.enums import Build14Severity, Build14SignalFamily


def build_competition_monitor_snapshot(
    observation: Build14ObservationInput,
) -> Build14EnablerSnapshot:
    """Estimate capital/risk crowding from governed competition-density facts."""

    competition_component = observation.competition_density
    stale_component = min(observation.stale_pair_count / 2.0, 1.0)
    ce_component = 1.0 if observation.ce_net < 0 else 0.0
    crowding_score = round(
        (0.60 * competition_component)
        + (0.20 * stale_component)
        + (0.20 * ce_component),
        4,
    )
    if crowding_score >= 0.70:
        status = Build14Severity.CRITICAL
    elif crowding_score >= 0.35:
        status = Build14Severity.ELEVATED
    else:
        status = Build14Severity.NOMINAL

    return Build14EnablerSnapshot(
        correlation_id=observation.correlation_id,
        signal_family=Build14SignalFamily.RISK,
        summary="Build-14 competition monitor remains SHADOW_ENABLED and only enriches risk-contribution interpretation",
        reader_name="competition_monitor",
        observed_value=crowding_score,
        status=status,
        detail=(
            f"competition_density={observation.competition_density:.2f} / "
            f"stale_pair_count={observation.stale_pair_count} / "
            f"ce_net={observation.ce_net:.4f}"
        ),
        evidence_refs=(
            f"competition_density={observation.competition_density:.2f}",
            f"stale_pair_count={observation.stale_pair_count}",
            f"ce_net={observation.ce_net:.4f}",
        ),
        structured_log_key="build14.shadow_enabled.competition_monitor",
    )


__all__ = [
    "build_competition_monitor_snapshot",
]
