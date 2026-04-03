"""Order-book imbalance reader for Build-14 SHADOW_ENABLED enablers."""

from __future__ import annotations

from complete_enablers.contracts import Build14EnablerSnapshot, Build14ObservationInput
from complete_enablers.enums import Build14Severity, Build14SignalFamily


def build_order_book_imbalance_snapshot(
    observation: Build14ObservationInput,
) -> Build14EnablerSnapshot:
    """Estimate adverse order-book pressure from governed OBI-like facts."""

    adverse_pressure_component = observation.adverse_obi_pressure
    sterilization_component = observation.cra_sterilization_rate
    stale_component = min(observation.stale_pair_count / 2.0, 1.0)
    ce_component = 1.0 if observation.ce_net < 0 else 0.0
    obi_pressure_score = round(
        (0.55 * adverse_pressure_component)
        + (0.20 * sterilization_component)
        + (0.15 * stale_component)
        + (0.10 * ce_component),
        4,
    )
    if obi_pressure_score >= 0.70:
        status = Build14Severity.CRITICAL
    elif obi_pressure_score >= 0.35:
        status = Build14Severity.ELEVATED
    else:
        status = Build14Severity.NOMINAL

    return Build14EnablerSnapshot(
        correlation_id=observation.correlation_id,
        signal_family=Build14SignalFamily.MICROSTRUCTURE,
        summary="Build-14 OBI reader remains SHADOW_ENABLED and only contributes bounded microstructure context",
        reader_name="order_book_imbalance",
        observed_value=obi_pressure_score,
        status=status,
        detail=(
            "adverse_obi_pressure="
            f"{observation.adverse_obi_pressure:.2f} / "
            f"cra_sterilization_rate={observation.cra_sterilization_rate:.2f} / "
            f"ce_net={observation.ce_net:.4f}"
        ),
        evidence_refs=(
            f"adverse_obi_pressure={observation.adverse_obi_pressure:.2f}",
            f"cra_sterilization_rate={observation.cra_sterilization_rate:.2f}",
            f"ce_net={observation.ce_net:.4f}",
        ),
        structured_log_key="build14.shadow_enabled.order_book_imbalance",
    )


__all__ = [
    "build_order_book_imbalance_snapshot",
]
