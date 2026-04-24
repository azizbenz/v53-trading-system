from __future__ import annotations

from interface_contracts import (
    RegimeDetectorFeatureSetVersion,
    RegimeDetectorShadowAuditSchemaMatchStatus,
    RegimeDurationBucket,
)
from monitoring import (
    build_regime_detector_shadow_audit_bundle,
    build_regime_detector_shadow_audit_sample,
)


def _sample(
    *,
    computed_at_ns: int,
    artifact_status: str,
    signal_status: str,
    transition: float = 0.0,
    stability: float = 1.0,
    toxicity: float = 0.0,
    duration: RegimeDurationBucket = RegimeDurationBucket.PERSISTENT,
    coverage: float | None = None,
    artifact_hash: str = "a" * 64,
    feature_hash: str = "b" * 64,
    pair: str = "BTCUSDT",
    reason_codes: tuple[str, ...] = (),
) -> object:
    return build_regime_detector_shadow_audit_sample(
        artifact_status=artifact_status,
        observation_coverage_ratio=coverage,
        signal_payload={
            "status": signal_status,
            "pair": pair,
            "computed_at_ns": computed_at_ns,
            "artifact_hash": artifact_hash,
            "feature_hash": feature_hash,
            "regime_transition_risk": transition,
            "regime_stability_score": stability,
            "market_toxicity_score": toxicity,
            "expected_duration_bucket": duration,
            "reason_codes": reason_codes,
        },
    )


def test_regime_detector_shadow_audit_bundle_is_deterministic_and_aggregates_counts() -> None:
    first = _sample(
        computed_at_ns=3_000_000_000,
        artifact_status="loaded",
        signal_status="active",
        transition=0.9,
        stability=0.2,
        toxicity=0.8,
        duration=RegimeDurationBucket.SHORT,
        coverage=0.8,
        reason_codes=("RC_B", "RC_A"),
    )
    second = _sample(
        computed_at_ns=1_000_000_000,
        artifact_status="loaded",
        signal_status="insufficient_data",
        coverage=0.4,
        reason_codes=("INSUFF",),
    )
    third = _sample(
        computed_at_ns=2_000_000_000,
        artifact_status="stale",
        signal_status="active",
        transition=0.4,
        stability=0.7,
        toxicity=0.3,
        duration=RegimeDurationBucket.PERSISTENT,
        coverage=0.6,
        reason_codes=("RC_A",),
    )

    bundle_a = build_regime_detector_shadow_audit_bundle(
        samples=(first, second, third),
        feature_set_version=RegimeDetectorFeatureSetVersion.LOB_REGIME_FEATURE_SET_V2,
        feature_profile="extended_v2",
        shadow_metrics={"shadow_diff_pct": 0.02},
    )
    bundle_b = build_regime_detector_shadow_audit_bundle(
        samples=(third, first, second),
        feature_set_version=RegimeDetectorFeatureSetVersion.LOB_REGIME_FEATURE_SET_V2,
        feature_profile="extended_v2",
        shadow_metrics={"shadow_diff_pct": 0.02},
    )

    assert bundle_a == bundle_b
    assert bundle_a.sample_count == 3
    assert bundle_a.prediction_count == 2
    assert bundle_a.insufficient_data_count == 1
    assert bundle_a.runtime_stale_count == 1
    assert bundle_a.window_start_ns == 1_000_000_000
    assert bundle_a.window_end_ns == 3_000_000_000
    assert bundle_a.schema_match_status == RegimeDetectorShadowAuditSchemaMatchStatus.MATCHED
    assert bundle_a.transition_risk_summary.mean_value == 0.65
    assert bundle_a.transition_risk_summary.last_value == 0.9
    assert bundle_a.observation_coverage_ratio_summary.count == 3
    assert bundle_a.observation_coverage_ratio_summary.mean_value == 0.6
    assert bundle_a.duration_bucket_counts.short == 1
    assert bundle_a.duration_bucket_counts.persistent == 1
    assert bundle_a.reason_code_counts[0].reason_code == "INSUFF"
    assert bundle_a.reason_code_counts[1].reason_code == "RC_A"
    assert bundle_a.reason_code_counts[1].count == 2


def test_regime_detector_shadow_audit_bundle_flags_schema_mismatch_and_hash_drift() -> None:
    first = _sample(
        computed_at_ns=1_000_000_000,
        artifact_status="loaded",
        signal_status="feature_schema_mismatch",
    )
    second = _sample(
        computed_at_ns=2_000_000_000,
        artifact_status="feature_set_version_mismatch",
        signal_status="neutral",
        artifact_hash="c" * 64,
    )

    bundle = build_regime_detector_shadow_audit_bundle(
        samples=(first, second),
        feature_set_version=RegimeDetectorFeatureSetVersion.LOB_REGIME_FEATURE_SET_V2,
        feature_profile="extended_v2",
    )

    assert bundle.schema_match_status == RegimeDetectorShadowAuditSchemaMatchStatus.MISMATCHED
    assert "REGIME_DETECTOR_SHADOW_AUDIT_ARTIFACT_HASH_MISMATCH" in bundle.blocking_reasons
    assert bundle.artifact_hash == ""


def test_regime_detector_shadow_audit_bundle_fails_closed_without_samples() -> None:
    bundle = build_regime_detector_shadow_audit_bundle(
        samples=(),
        feature_set_version=RegimeDetectorFeatureSetVersion.LOB_REGIME_FEATURE_SET_V2,
        feature_profile="extended_v2",
    )

    assert bundle.sample_count == 0
    assert bundle.prediction_count == 0
    assert bundle.schema_match_status == RegimeDetectorShadowAuditSchemaMatchStatus.INCONCLUSIVE
    assert bundle.blocking_reasons == ("REGIME_DETECTOR_SHADOW_AUDIT_NO_SAMPLES",)
