"""LOB deep-filter / VWA reader for Build-14 SHADOW_ENABLED enablers."""

from __future__ import annotations

from complete_enablers.contracts import Build14EnablerSnapshot, Build14ObservationInput
from complete_enablers.enums import Build14Severity, Build14SignalFamily


def build_lob_deep_filter_vwa_snapshot(
    observation: Build14ObservationInput,
) -> Build14EnablerSnapshot:
    """Estimate spoofing / weak absorption risk from governed depth facts."""

    weak_absorption_component = 1.0 - observation.vwa_absorption_ratio
    ghost_liquidity_component = observation.ghost_liquidity_ratio
    stale_component = min(observation.stale_pair_count / 2.0, 1.0)
    backlog_component = min(observation.queue_backlog / 100.0, 1.0)
    depth_fragility_score = round(
        (0.40 * weak_absorption_component)
        + (0.35 * ghost_liquidity_component)
        + (0.15 * stale_component)
        + (0.10 * backlog_component),
        4,
    )
    if depth_fragility_score >= 0.70:
        status = Build14Severity.CRITICAL
    elif depth_fragility_score >= 0.35:
        status = Build14Severity.ELEVATED
    else:
        status = Build14Severity.NOMINAL

    return Build14EnablerSnapshot(
        correlation_id=observation.correlation_id,
        signal_family=Build14SignalFamily.MICROSTRUCTURE,
        summary="Build-14 LOB/VWA reader remains SHADOW_ENABLED and only enriches microstructure interpretation",
        reader_name="lob_deep_filter_vwa",
        observed_value=depth_fragility_score,
        status=status,
        detail=(
            "vwa_absorption_ratio="
            f"{observation.vwa_absorption_ratio:.2f} / "
            f"ghost_liquidity_ratio={observation.ghost_liquidity_ratio:.2f} / "
            f"stale_pair_count={observation.stale_pair_count}"
        ),
        evidence_refs=(
            f"vwa_absorption_ratio={observation.vwa_absorption_ratio:.2f}",
            f"ghost_liquidity_ratio={observation.ghost_liquidity_ratio:.2f}",
            f"queue_backlog={observation.queue_backlog}",
        ),
        structured_log_key="build14.shadow_enabled.lob_deep_filter_vwa",
    )


__all__ = [
    "build_lob_deep_filter_vwa_snapshot",
]
