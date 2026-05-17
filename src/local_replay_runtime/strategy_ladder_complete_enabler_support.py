"""Bounded Build-14 support for Strategy Ladder Engine C/D replay inputs."""

from __future__ import annotations

from dataclasses import dataclass, field

from complete_enablers import (
    Build14InfluenceReport,
    Build14ObservationInput,
    Build14Severity,
    Build14SignalFamily,
    evaluate_build14_shadow_activation,
)


@dataclass(frozen=True)
class StrategyLadderBuild14Application:
    """Traceable Build-14 replay-side application over one Engine C/D payload."""

    activation_status: str
    observation_input: Build14ObservationInput
    shadow_report: Build14InfluenceReport
    adjusted_engine_input_payload: dict[str, object] = field(default_factory=dict)
    applied_fields: tuple[str, ...] = ()
    adjustment_factors: dict[str, float] = field(default_factory=dict)
    reason_codes: tuple[str, ...] = ()


def apply_build14_shadow_context(
    *,
    engine_id: str,
    candidate_id: str,
    pair: str,
    candidate_payload: dict[str, object] | None,
    engine_input_payload: dict[str, object],
) -> StrategyLadderBuild14Application:
    """Materialize replay-safe Build-14 context and apply bounded C/D input adjustments."""

    compat_payload = candidate_payload if isinstance(candidate_payload, dict) else {}
    observation = _build_observation_input(
        engine_id=engine_id,
        candidate_id=candidate_id,
        pair=pair,
        compat_payload=compat_payload,
        engine_input_payload=engine_input_payload,
    )
    shadow_report = evaluate_build14_shadow_activation(observation)
    adjusted_payload = dict(engine_input_payload)
    adjustment_factors: dict[str, float] = {}
    applied_fields: list[str] = []

    active_families = {
        snapshot.signal_family
        for snapshot in shadow_report.snapshots
        if snapshot.status != Build14Severity.NOMINAL
    }
    confidence_factor = max(0.0, 1.0 - shadow_report.signal.confidence_penalty_weight)
    budget_factor = shadow_report.signal.recommended_budget_factor
    stale_factor = confidence_factor if observation.stale_pair_count > 0 else 1.0

    if Build14SignalFamily.AI_EDGE in active_families:
        adjusted_payload["expected_gain"] = round(
            _coerce_float(engine_input_payload.get("expected_gain"), 0.0) * confidence_factor,
            8,
        )
        adjustment_factors["expected_gain_factor"] = round(confidence_factor, 6)
        applied_fields.append("expected_gain")
    if Build14SignalFamily.REGIME in active_families:
        adjusted_payload["regime_favorability"] = _clamp01(
            _coerce_float(engine_input_payload.get("regime_favorability"), 0.5)
            * confidence_factor
        )
        adjustment_factors["regime_favorability_factor"] = round(confidence_factor, 6)
        applied_fields.append("regime_favorability")
    if Build14SignalFamily.RISK in active_families:
        adjusted_payload["pair_health"] = _clamp01(
            _coerce_float(engine_input_payload.get("pair_health"), 0.5) * budget_factor
        )
        adjustment_factors["pair_health_factor"] = round(budget_factor, 6)
        applied_fields.append("pair_health")
    if Build14SignalFamily.MICROSTRUCTURE in active_families:
        micro_factor = min(confidence_factor, budget_factor)
        adjusted_payload["flow_coherence"] = _clamp01(
            _coerce_float(engine_input_payload.get("flow_coherence"), 0.5) * micro_factor
        )
        adjusted_payload["data_freshness"] = _clamp01(
            _coerce_float(engine_input_payload.get("data_freshness"), 0.5)
            * min(micro_factor, stale_factor)
        )
        adjustment_factors["flow_coherence_factor"] = round(micro_factor, 6)
        adjustment_factors["data_freshness_factor"] = round(min(micro_factor, stale_factor), 6)
        applied_fields.extend(("flow_coherence", "data_freshness"))

    active_snapshots = tuple(
        snapshot
        for snapshot in shadow_report.snapshots
        if snapshot.status != Build14Severity.NOMINAL
    )
    reason_codes = tuple(
        dict.fromkeys(
            (
                "BUILD14_SHADOW_ENABLED_ACTIVE",
                *(
                    f"BUILD14_READER:{snapshot.reader_name}:{snapshot.status.value.upper()}"
                    for snapshot in active_snapshots
                ),
                *(
                    f"BUILD14_APPLIED:{field.upper()}"
                    for field in applied_fields
                ),
            )
        )
    )
    return StrategyLadderBuild14Application(
        activation_status="BUILD14_SHADOW_ENABLED_ACTIVE",
        observation_input=observation,
        shadow_report=shadow_report,
        adjusted_engine_input_payload=adjusted_payload,
        applied_fields=tuple(dict.fromkeys(applied_fields)),
        adjustment_factors=adjustment_factors,
        reason_codes=reason_codes,
    )


def _build_observation_input(
    *,
    engine_id: str,
    candidate_id: str,
    pair: str,
    compat_payload: dict[str, object],
    engine_input_payload: dict[str, object],
) -> Build14ObservationInput:
    feature_values = compat_payload.get("feature_values")
    feature_map = feature_values if isinstance(feature_values, dict) else {}
    override_map = _resolve_build14_overrides(compat_payload, feature_map)
    queue_pressure = _coerce_float(
        engine_input_payload.get("queue_pressure"),
        _coerce_float(feature_map.get("queue_pressure"), 0.0),
    )
    book_depth_levels = _coerce_int(
        compat_payload.get("book_depth_levels"),
        _coerce_int(feature_map.get("book_depth_levels"), 0),
    )
    book_depth_status = str(
        compat_payload.get("book_depth_source_status")
        or feature_map.get("book_depth_source_status")
        or "BOOK_DEPTH_NOT_PROVEN"
    )
    stale_pair_count_default = (
        1
        if book_depth_status in {
            "BOOK_DEPTH_MISSING",
            "BOOK_DEPTH_NOT_PROVEN",
            "BOOK_DEPTH_STALE",
        }
        else 0
    )
    expected_gain = _coerce_float(engine_input_payload.get("expected_gain"), 0.0)
    expected_cost = _coerce_float(engine_input_payload.get("expected_cost"), 0.0)
    ce_net_default = expected_gain - expected_cost
    volume_support_default = _coerce_float(
        engine_input_payload.get("volume_confirmation"),
        _coerce_float(engine_input_payload.get("reformation_quality"), 1.0),
    )
    breakout_failure_default = _coerce_float(
        engine_input_payload.get("retrace_risk"),
        1.0 - _coerce_float(engine_input_payload.get("reformation_quality"), 1.0),
    )
    adverse_obi_pressure_default = _clamp01(max(0.0, -queue_pressure))
    observation_payload = {
        "correlation_id": str(
            override_map.get("correlation_id")
            or f"{candidate_id}:{pair}:{engine_id}:build14_shadow"
        ),
        "dtr_coverage": _coerce_float(override_map.get("dtr_coverage"), 1.0),
        "cra_sterilization_rate": _clamp01(
            _coerce_float(override_map.get("cra_sterilization_rate"), 0.0)
        ),
        "cra_alert_count": _coerce_int(override_map.get("cra_alert_count"), 0),
        "break_even_drift_alert": _coerce_bool(
            override_map.get("break_even_drift_alert"),
            default=expected_gain <= expected_cost,
        ),
        "edge_degraded_count": _coerce_int(
            override_map.get("edge_degraded_count"),
            len(_tuple_like(compat_payload.get("economic_measurement_warnings"))),
        ),
        "queue_backlog": _coerce_int(
            override_map.get("queue_backlog"),
            int(round(adverse_obi_pressure_default * 100.0)),
        ),
        "stale_pair_count": _coerce_int(
            override_map.get("stale_pair_count"),
            stale_pair_count_default,
        ),
        "dtr_loss_count": _coerce_int(override_map.get("dtr_loss_count"), 0),
        "log_loss_count": _coerce_int(override_map.get("log_loss_count"), 0),
        "ce_net": _coerce_float(override_map.get("ce_net"), ce_net_default),
        "breakout_failure_rate": _clamp01(
            _coerce_float(override_map.get("breakout_failure_rate"), breakout_failure_default)
        ),
        "volume_support_ratio": _clamp01(
            _coerce_float(override_map.get("volume_support_ratio"), volume_support_default)
        ),
        "vwa_absorption_ratio": _clamp01(
            _coerce_float(
                override_map.get("vwa_absorption_ratio"),
                1.0 - adverse_obi_pressure_default,
            )
        ),
        "ghost_liquidity_ratio": _clamp01(
            _coerce_float(
                override_map.get("ghost_liquidity_ratio"),
                1.0 - min(max(book_depth_levels, 0), 20) / 20.0
                if book_depth_levels > 0
                else 1.0,
            )
        ),
        "adverse_obi_pressure": _clamp01(
            _coerce_float(
                override_map.get("adverse_obi_pressure"),
                adverse_obi_pressure_default,
            )
        ),
        "hurst_exponent": _clamp01(
            _coerce_float(override_map.get("hurst_exponent"), 0.5)
        ),
        "competition_density": _clamp01(
            _coerce_float(override_map.get("competition_density"), 0.0)
        ),
    }
    return Build14ObservationInput.model_validate(observation_payload)


def _resolve_build14_overrides(
    compat_payload: dict[str, object],
    feature_map: dict[str, object],
) -> dict[str, object]:
    overrides: dict[str, object] = {}
    for container in (compat_payload.get("build14_shadow_observation"),):
        if isinstance(container, dict):
            overrides.update(container)
    observation_fields = (
        "correlation_id",
        "dtr_coverage",
        "cra_sterilization_rate",
        "cra_alert_count",
        "break_even_drift_alert",
        "edge_degraded_count",
        "queue_backlog",
        "stale_pair_count",
        "dtr_loss_count",
        "log_loss_count",
        "ce_net",
        "breakout_failure_rate",
        "volume_support_ratio",
        "vwa_absorption_ratio",
        "ghost_liquidity_ratio",
        "adverse_obi_pressure",
        "hurst_exponent",
        "competition_density",
    )
    for source in (compat_payload, feature_map):
        for field_name in observation_fields:
            for key in (f"build14_{field_name}", f"build14_shadow_{field_name}"):
                if key in source and field_name not in overrides:
                    overrides[field_name] = source[key]
                    break
    return overrides


def _tuple_like(value: object) -> tuple[object, ...]:
    if isinstance(value, tuple):
        return value
    if isinstance(value, list):
        return tuple(value)
    if isinstance(value, str):
        stripped = value.strip()
        return tuple(part for part in stripped.split("|") if part) if stripped else ()
    return ()


def _coerce_bool(value: object, *, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    return default


def _coerce_int(value: object, default: int) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return max(value, 0)
    try:
        return max(int(value), 0)
    except (TypeError, ValueError):
        return default


def _coerce_float(value: object, default: float) -> float:
    if isinstance(value, bool):
        return default
    if isinstance(value, (float, int)):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _clamp01(value: float) -> float:
    if value != value:
        return 0.0
    return max(0.0, min(1.0, value))


__all__ = [
    "StrategyLadderBuild14Application",
    "apply_build14_shadow_context",
]
