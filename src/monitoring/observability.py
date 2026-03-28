"""Minimal structured observability export for Build-10 supervision."""

from __future__ import annotations

from monitoring.contracts import MetricSample, MonitoringSnapshot, ObservabilityExport
from monitoring.health_dashboard_backend import build_health_dashboard_payload


def _sample(
    name: str,
    *,
    kind: str,
    value: float,
    unit: str = "",
    labels: dict[str, str] | None = None,
) -> MetricSample:
    return MetricSample(
        name=name,
        kind=kind,
        value=value,
        unit=unit,
        labels=labels or {},
    )


def _labels(snapshot: MonitoringSnapshot) -> dict[str, str]:
    return {
        "correlation_id": snapshot.correlation_id,
        "profile": snapshot.profile.value,
        "runtime_mode": snapshot.runtime_mode.value,
    }


def _format_labels(labels: dict[str, str]) -> str:
    if not labels:
        return ""
    joined = ",".join(f'{key}="{value}"' for key, value in sorted(labels.items()))
    return f"{{{joined}}}"


def build_observability_export(
    snapshot: MonitoringSnapshot,
    *,
    active_modules: tuple[str, ...] = (),
    active_engines: tuple[str, ...] = (),
    recent_diagnostics: int = 0,
    open_hypotheses: int = 0,
    replay_candidates: int = 0,
    artifact_present: bool = False,
    import_accepted: bool | None = None,
) -> ObservabilityExport:
    """Emit a minimal metrics surface without opening a full observability stack."""

    base_labels = _labels(snapshot)
    headline_status = build_health_dashboard_payload(snapshot).headline_status
    samples: list[MetricSample] = [
        _sample("v53_headline_status", kind="state", value=1.0, labels={**base_labels, "status": headline_status}),
        _sample("v53_active_alert_count", kind="gauge", value=float(snapshot.active_alert_count), unit="count", labels=base_labels),
        _sample("v53_stale_pair_count", kind="gauge", value=float(snapshot.stale_pair_count), unit="count", labels=base_labels),
        _sample("v53_queue_backlog", kind="gauge", value=float(snapshot.infra.queue_backlog), unit="count", labels=base_labels),
        _sample("v53_dtr_loss_count", kind="gauge", value=float(snapshot.infra.dtr_loss_count), unit="count", labels=base_labels),
        _sample("v53_log_loss_count", kind="gauge", value=float(snapshot.infra.log_loss_count), unit="count", labels=base_labels),
        _sample("v53_dtr_coverage_ratio", kind="gauge", value=snapshot.meta.dtr_coverage, unit="ratio", labels=base_labels),
        _sample("v53_cra_sterilization_ratio", kind="gauge", value=snapshot.meta.cra_sterilization_rate, unit="ratio", labels=base_labels),
        _sample("v53_edge_degraded_count", kind="gauge", value=float(snapshot.meta.edge_degraded_count), unit="count", labels=base_labels),
        _sample("v53_build9x_recent_diagnostics", kind="gauge", value=float(recent_diagnostics), unit="count", labels=base_labels),
        _sample("v53_build9x_open_hypotheses", kind="gauge", value=float(open_hypotheses), unit="count", labels=base_labels),
        _sample("v53_build9x_replay_candidates", kind="gauge", value=float(replay_candidates), unit="count", labels=base_labels),
        _sample("v53_replay_artifact_present", kind="state", value=1.0 if artifact_present else 0.0, labels=base_labels),
        _sample("v53_artifact_import_review_started", kind="state", value=1.0 if import_accepted is not None else 0.0, labels=base_labels),
        _sample("v53_artifact_import_accepted", kind="state", value=1.0 if import_accepted else 0.0, labels=base_labels),
    ]

    for module_name in active_modules:
        samples.append(
            _sample(
                "v53_module_active",
                kind="state",
                value=1.0,
                labels={**base_labels, "module": module_name},
            )
        )

    stale_engines = {engine.engine_id for engine in snapshot.engines if engine.stale}
    for engine_id in active_engines:
        samples.append(
            _sample(
                "v53_engine_stale",
                kind="state",
                value=1.0 if engine_id in stale_engines else 0.0,
                labels={**base_labels, "engine": engine_id},
            )
        )

    lines = ["# V5.3 monitoring export"]
    for sample in samples:
        lines.append(f"{sample.name}{_format_labels(sample.labels)} {sample.value}")

    return ObservabilityExport(
        timestamp_ms=snapshot.timestamp_ms,
        correlation_id=snapshot.correlation_id,
        profile=snapshot.profile,
        runtime_mode=snapshot.runtime_mode,
        samples=tuple(samples),
        text_payload="\n".join(lines),
    )


__all__ = [
    "build_observability_export",
]
