"""Deterministic VPS shadow audit aggregation for RegimeDetectorML."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence

from interface_contracts import (
    RegimeDetectorFeatureSetVersion,
    RegimeDetectorShadowAuditBundle,
    RegimeDetectorShadowAuditDurationCounts,
    RegimeDetectorShadowAuditMetricSummary,
    RegimeDetectorShadowAuditReasonCodeCount,
    RegimeDetectorShadowAuditSample,
    RegimeDetectorShadowAuditSchemaMatchStatus,
    RegimeDetectorShadowAuditStatusCount,
    RegimeDurationBucket,
)


def _signal_value(signal_payload: Mapping[str, object], key: str, default: object) -> object:
    value = signal_payload.get(key, default)
    if hasattr(value, "value"):
        return value.value
    return value


def build_regime_detector_shadow_audit_sample(
    *,
    artifact_status: str,
    signal_payload: Mapping[str, object],
    observation_coverage_ratio: float | None = None,
) -> RegimeDetectorShadowAuditSample:
    """Build one typed shadow-audit sample from serialized runtime signal data."""

    return RegimeDetectorShadowAuditSample(
        artifact_status=artifact_status,
        signal_status=str(_signal_value(signal_payload, "status", "neutral")),
        pair=str(_signal_value(signal_payload, "pair", "")),
        computed_at_ns=int(_signal_value(signal_payload, "computed_at_ns", 0)),
        artifact_hash=str(_signal_value(signal_payload, "artifact_hash", "")),
        feature_hash=str(_signal_value(signal_payload, "feature_hash", "")),
        regime_transition_risk=float(
            _signal_value(signal_payload, "regime_transition_risk", 0.0)
        ),
        regime_stability_score=float(
            _signal_value(signal_payload, "regime_stability_score", 1.0)
        ),
        market_toxicity_score=float(
            _signal_value(signal_payload, "market_toxicity_score", 0.0)
        ),
        expected_duration_bucket=RegimeDurationBucket(
            str(
                _signal_value(
                    signal_payload,
                    "expected_duration_bucket",
                    RegimeDurationBucket.PERSISTENT.value,
                )
            )
        ),
        observation_coverage_ratio=observation_coverage_ratio,
        reason_codes=tuple(str(item) for item in signal_payload.get("reason_codes", ())),
    )


def _ordered_samples(
    samples: Sequence[RegimeDetectorShadowAuditSample],
) -> tuple[RegimeDetectorShadowAuditSample, ...]:
    return tuple(
        sorted(
            samples,
            key=lambda sample: (
                sample.computed_at_ns,
                sample.artifact_status,
                sample.signal_status,
                sample.pair,
            ),
        )
    )


def _metric_summary(values: Sequence[float]) -> RegimeDetectorShadowAuditMetricSummary:
    if not values:
        return RegimeDetectorShadowAuditMetricSummary()
    resolved_count = len(values)
    resolved_min = min(values)
    resolved_max = max(values)
    resolved_mean = sum(values) / resolved_count
    return RegimeDetectorShadowAuditMetricSummary(
        count=resolved_count,
        min_value=resolved_min,
        max_value=resolved_max,
        mean_value=resolved_mean,
        last_value=values[-1],
    )


def _status_counts(values: Sequence[str]) -> tuple[RegimeDetectorShadowAuditStatusCount, ...]:
    counter = Counter(values)
    return tuple(
        RegimeDetectorShadowAuditStatusCount(status=status, count=counter[status])
        for status in sorted(counter)
    )


def _reason_code_counts(
    samples: Sequence[RegimeDetectorShadowAuditSample],
) -> tuple[RegimeDetectorShadowAuditReasonCodeCount, ...]:
    counter = Counter(
        reason_code
        for sample in samples
        for reason_code in sample.reason_codes
    )
    return tuple(
        RegimeDetectorShadowAuditReasonCodeCount(reason_code=reason_code, count=counter[reason_code])
        for reason_code in sorted(counter)
    )


def _duration_counts(
    active_samples: Sequence[RegimeDetectorShadowAuditSample],
) -> RegimeDetectorShadowAuditDurationCounts:
    counter = Counter(sample.expected_duration_bucket.value for sample in active_samples)
    return RegimeDetectorShadowAuditDurationCounts(
        fragile=counter[RegimeDurationBucket.FRAGILE.value],
        short=counter[RegimeDurationBucket.SHORT.value],
        medium=counter[RegimeDurationBucket.MEDIUM.value],
        persistent=counter[RegimeDurationBucket.PERSISTENT.value],
        total=len(active_samples),
    )


def _resolved_hash(
    values: Sequence[str],
    *,
    blocking_reasons: list[str],
    mismatch_reason: str,
) -> str:
    unique_values = tuple(sorted({value for value in values if value}))
    if len(unique_values) > 1:
        blocking_reasons.append(mismatch_reason)
        return ""
    return unique_values[0] if unique_values else ""


def _schema_match_status(
    samples: Sequence[RegimeDetectorShadowAuditSample],
) -> RegimeDetectorShadowAuditSchemaMatchStatus:
    if any(sample.signal_status == "feature_schema_mismatch" for sample in samples):
        return RegimeDetectorShadowAuditSchemaMatchStatus.MISMATCHED
    if any("mismatch" in sample.artifact_status.lower() for sample in samples):
        return RegimeDetectorShadowAuditSchemaMatchStatus.MISMATCHED
    if any(sample.artifact_status.lower() == "loaded" for sample in samples):
        return RegimeDetectorShadowAuditSchemaMatchStatus.MATCHED
    return RegimeDetectorShadowAuditSchemaMatchStatus.INCONCLUSIVE


def build_regime_detector_shadow_audit_bundle(
    *,
    samples: Sequence[RegimeDetectorShadowAuditSample],
    feature_set_version: RegimeDetectorFeatureSetVersion,
    feature_profile: str,
    shadow_metrics: Mapping[str, float | int | str | bool] | None = None,
) -> RegimeDetectorShadowAuditBundle:
    """Aggregate bounded VPS shadow samples into a durable audit bundle."""

    ordered_samples = _ordered_samples(samples)
    blocking_reasons: list[str] = []
    if not ordered_samples:
        blocking_reasons.append("REGIME_DETECTOR_SHADOW_AUDIT_NO_SAMPLES")
        return RegimeDetectorShadowAuditBundle(
            feature_set_version=feature_set_version,
            feature_profile=feature_profile,
            blocking_reasons=tuple(blocking_reasons),
            shadow_metrics={} if shadow_metrics is None else dict(shadow_metrics),
        )

    pair_scope = tuple(sorted({sample.pair for sample in ordered_samples}))
    if len(pair_scope) != 1:
        blocking_reasons.append("REGIME_DETECTOR_SHADOW_AUDIT_PAIR_SCOPE_MISMATCH")
    active_samples = tuple(
        sample for sample in ordered_samples if sample.signal_status == "active"
    )
    coverage_values = tuple(
        sample.observation_coverage_ratio
        for sample in ordered_samples
        if sample.observation_coverage_ratio is not None
    )
    artifact_hash = _resolved_hash(
        [sample.artifact_hash for sample in ordered_samples],
        blocking_reasons=blocking_reasons,
        mismatch_reason="REGIME_DETECTOR_SHADOW_AUDIT_ARTIFACT_HASH_MISMATCH",
    )
    feature_hash = _resolved_hash(
        [sample.feature_hash for sample in ordered_samples],
        blocking_reasons=blocking_reasons,
        mismatch_reason="REGIME_DETECTOR_SHADOW_AUDIT_FEATURE_HASH_MISMATCH",
    )

    return RegimeDetectorShadowAuditBundle(
        artifact_hash=artifact_hash,
        feature_hash_at_runtime=feature_hash,
        feature_set_version=feature_set_version,
        feature_profile=feature_profile,
        pair=pair_scope[0] if len(pair_scope) == 1 else "",
        window_start_ns=ordered_samples[0].computed_at_ns,
        window_end_ns=ordered_samples[-1].computed_at_ns,
        sample_count=len(ordered_samples),
        prediction_count=len(active_samples),
        insufficient_data_count=sum(
            1 for sample in ordered_samples if sample.signal_status == "insufficient_data"
        ),
        runtime_stale_count=sum(
            1 for sample in ordered_samples if sample.artifact_status.lower() == "stale"
        ),
        schema_match_status=_schema_match_status(ordered_samples),
        transition_risk_summary=_metric_summary(
            [sample.regime_transition_risk for sample in active_samples]
        ),
        stability_score_summary=_metric_summary(
            [sample.regime_stability_score for sample in active_samples]
        ),
        toxicity_score_summary=_metric_summary(
            [sample.market_toxicity_score for sample in active_samples]
        ),
        observation_coverage_ratio_summary=_metric_summary(
            [float(value) for value in coverage_values]
        ),
        duration_bucket_counts=_duration_counts(active_samples),
        artifact_status_counts=_status_counts(
            [sample.artifact_status for sample in ordered_samples]
        ),
        signal_status_counts=_status_counts(
            [sample.signal_status for sample in ordered_samples]
        ),
        reason_code_counts=_reason_code_counts(ordered_samples),
        shadow_metrics={} if shadow_metrics is None else dict(shadow_metrics),
        blocking_reasons=tuple(blocking_reasons),
    )


__all__ = [
    "build_regime_detector_shadow_audit_sample",
    "build_regime_detector_shadow_audit_bundle",
]
