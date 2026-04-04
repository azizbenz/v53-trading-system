"""Shared Build-14 observation derivation from governed monitoring surfaces."""

from __future__ import annotations

from complete_enablers import Build14ObservationInput
from monitoring.contracts import MonitoringSnapshot, TechnicalDashboardPayload


def _clamp01(value: float) -> float:
    return round(max(0.0, min(1.0, value)), 4)


def _derive_addendum_fields(
    *,
    dtr_coverage: float,
    cra_sterilization_rate: float,
    break_even_drift_alert: bool,
    edge_degraded_count: int,
    queue_backlog: int,
    stale_pair_count: int,
    dtr_loss_count: int,
    log_loss_count: int,
    ce_net: float,
    pair_count: int,
    engine_count: int,
) -> dict[str, float]:
    backlog_norm = min(queue_backlog / 100.0, 1.0)
    stale_ratio = min(stale_pair_count / max(pair_count, 1), 1.0)
    loss_ratio = min((dtr_loss_count + log_loss_count) / 2.0, 1.0)
    edge_ratio = min(edge_degraded_count / max(engine_count, 1), 1.0)
    drift_component = 1.0 if break_even_drift_alert else 0.0
    ce_pressure = 1.0 if ce_net < 0.0 else 0.5 if ce_net < 0.001 else 0.0
    deployment_density = max(engine_count - pair_count, 0) / max(engine_count, 1)

    return {
        "breakout_failure_rate": _clamp01(
            (0.45 * cra_sterilization_rate)
            + (0.25 * edge_ratio)
            + (0.20 * drift_component)
            + (0.10 * backlog_norm)
        ),
        "volume_support_ratio": _clamp01(
            1.0
            - (
                (0.35 * backlog_norm)
                + (0.25 * stale_ratio)
                + (0.15 * loss_ratio)
                + (0.15 * cra_sterilization_rate)
            )
        ),
        "vwa_absorption_ratio": _clamp01(
            1.0
            - (
                (0.30 * backlog_norm)
                + (0.25 * loss_ratio)
                + (0.20 * stale_ratio)
                + (0.10 * edge_ratio)
            )
        ),
        "ghost_liquidity_ratio": _clamp01(
            (0.45 * backlog_norm)
            + (0.25 * stale_ratio)
            + (0.20 * loss_ratio)
            + (0.10 * cra_sterilization_rate)
        ),
        "adverse_obi_pressure": _clamp01(
            (0.40 * cra_sterilization_rate)
            + (0.25 * stale_ratio)
            + (0.20 * backlog_norm)
            + (0.15 * ce_pressure)
        ),
        "hurst_exponent": _clamp01(
            0.50
            + (0.18 * drift_component)
            + (0.20 * edge_ratio)
            + (0.06 * backlog_norm)
            - (0.06 * dtr_coverage)
        ),
        "competition_density": _clamp01(
            (0.20 * deployment_density)
            + (0.25 * stale_ratio)
            + (0.20 * backlog_norm)
            + (0.15 * ce_pressure)
            + (0.10 * edge_ratio)
        ),
    }


def derive_build14_observation_from_snapshot(
    snapshot: MonitoringSnapshot,
) -> Build14ObservationInput:
    """Derive governed Build-14 observation facts from a raw monitoring snapshot."""

    return Build14ObservationInput(
        correlation_id=snapshot.correlation_id,
        dtr_coverage=snapshot.meta.dtr_coverage,
        cra_sterilization_rate=snapshot.meta.cra_sterilization_rate,
        cra_alert_count=snapshot.meta.cra_alert_count,
        break_even_drift_alert=snapshot.meta.break_even_drift_alert,
        edge_degraded_count=snapshot.meta.edge_degraded_count,
        queue_backlog=snapshot.infra.queue_backlog,
        stale_pair_count=len(snapshot.infra.stale_pairs),
        dtr_loss_count=snapshot.infra.dtr_loss_count,
        log_loss_count=snapshot.infra.log_loss_count,
        ce_net=snapshot.portfolio.ce_net,
        **_derive_addendum_fields(
            dtr_coverage=snapshot.meta.dtr_coverage,
            cra_sterilization_rate=snapshot.meta.cra_sterilization_rate,
            break_even_drift_alert=snapshot.meta.break_even_drift_alert,
            edge_degraded_count=snapshot.meta.edge_degraded_count,
            queue_backlog=snapshot.infra.queue_backlog,
            stale_pair_count=len(snapshot.infra.stale_pairs),
            dtr_loss_count=snapshot.infra.dtr_loss_count,
            log_loss_count=snapshot.infra.log_loss_count,
            ce_net=snapshot.portfolio.ce_net,
            pair_count=max(len(snapshot.pairs), 1),
            engine_count=max(len(snapshot.engines), 1),
        ),
    )


def derive_build14_observation_from_payload(
    payload: TechnicalDashboardPayload,
) -> Build14ObservationInput:
    """Derive governed Build-14 observation facts from a normalized dashboard payload."""

    break_even_drift_alert = (
        payload.build9_meta.break_even_state == "drift_alert"
        or bool(payload.build9_meta.break_even_drift_scopes)
    )
    return Build14ObservationInput(
        correlation_id=payload.correlation_id,
        dtr_coverage=payload.build9_meta.dtr_coverage,
        cra_sterilization_rate=payload.build9_meta.cra_sterilization_rate,
        cra_alert_count=payload.build9_meta.cra_alert_count,
        break_even_drift_alert=break_even_drift_alert,
        edge_degraded_count=payload.build9_meta.edge_degraded_count,
        queue_backlog=payload.alerts.queue_backlog,
        stale_pair_count=payload.alerts.stale_pair_count,
        dtr_loss_count=payload.alerts.dtr_loss_count,
        log_loss_count=payload.alerts.log_loss_count,
        ce_net=payload.portfolio.ce_net,
        **_derive_addendum_fields(
            dtr_coverage=payload.build9_meta.dtr_coverage,
            cra_sterilization_rate=payload.build9_meta.cra_sterilization_rate,
            break_even_drift_alert=break_even_drift_alert,
            edge_degraded_count=payload.build9_meta.edge_degraded_count,
            queue_backlog=payload.alerts.queue_backlog,
            stale_pair_count=payload.alerts.stale_pair_count,
            dtr_loss_count=payload.alerts.dtr_loss_count,
            log_loss_count=payload.alerts.log_loss_count,
            ce_net=payload.portfolio.ce_net,
            pair_count=max(len(payload.pairs), 1),
            engine_count=max(len(payload.engines), 1),
        ),
    )


__all__ = [
    "derive_build14_observation_from_snapshot",
    "derive_build14_observation_from_payload",
]
