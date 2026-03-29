"""Read-only market toxicity reader for Build-14."""

from __future__ import annotations

from complete_enablers.contracts import Build14EnablerSnapshot, Build14ObservationInput
from complete_enablers.enums import Build14Severity, Build14SignalFamily


def build_market_toxicity_snapshot(observation: Build14ObservationInput) -> Build14EnablerSnapshot:
    """Estimate market toxicity from existing Build-9/10 operability facts."""

    backlog_component = min(observation.queue_backlog / 100.0, 1.0)
    stale_component = min(observation.stale_pair_count / 2.0, 1.0)
    loss_component = min((observation.dtr_loss_count + observation.log_loss_count) / 2.0, 1.0)
    cra_component = observation.cra_sterilization_rate
    toxicity_score = round(
        (0.35 * backlog_component)
        + (0.25 * stale_component)
        + (0.20 * loss_component)
        + (0.20 * cra_component),
        4,
    )

    if toxicity_score >= 0.75:
        status = Build14Severity.CRITICAL
    elif toxicity_score >= 0.40:
        status = Build14Severity.ELEVATED
    else:
        status = Build14Severity.NOMINAL

    return Build14EnablerSnapshot(
        correlation_id=observation.correlation_id,
        signal_family=Build14SignalFamily.MICROSTRUCTURE,
        summary=f"Market toxicity {status} at {toxicity_score:.2f}",
        reader_name="market_toxicity_snapshot",
        observed_value=toxicity_score,
        status=status,
        detail=(
            f"backlog={observation.queue_backlog}, stale_pairs={observation.stale_pair_count}, "
            f"losses={observation.dtr_loss_count + observation.log_loss_count}, "
            f"cra={observation.cra_sterilization_rate:.2%}"
        ),
        evidence_refs=(
            f"queue_backlog:{observation.queue_backlog}",
            f"stale_pair_count:{observation.stale_pair_count}",
            f"cra_alert_count:{observation.cra_alert_count}",
        ),
        structured_log_key="build14.read_only.market_toxicity",
    )


__all__ = [
    "build_market_toxicity_snapshot",
]
