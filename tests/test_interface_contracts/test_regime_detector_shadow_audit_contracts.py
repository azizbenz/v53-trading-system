from __future__ import annotations

import pytest
from pydantic import ValidationError

from interface_contracts import (
    RegimeDetectorFeatureSetVersion,
    RegimeDetectorShadowAuditBundle,
    RegimeDetectorShadowAuditDiagnosis,
    RegimeDetectorShadowAuditDiagnosisStatus,
    RegimeDetectorShadowAuditDurationCounts,
    RegimeDetectorShadowAuditFinding,
    RegimeDetectorShadowAuditFindingCode,
    RegimeDetectorShadowAuditFindingSeverity,
    RegimeDetectorShadowAuditMetricSummary,
    RegimeDetectorShadowAuditSample,
)


def test_regime_detector_shadow_audit_sample_rejects_invalid_optional_hash() -> None:
    with pytest.raises(ValidationError):
        RegimeDetectorShadowAuditSample(
            artifact_status="loaded",
            signal_status="active",
            pair="BTCUSDT",
            computed_at_ns=1_000_000_000,
            artifact_hash="not-a-hash",
        )


def test_regime_detector_shadow_audit_bundle_round_trip_is_stable() -> None:
    bundle = RegimeDetectorShadowAuditBundle(
        artifact_hash="a" * 64,
        feature_hash_at_runtime="b" * 64,
        feature_set_version=RegimeDetectorFeatureSetVersion.LOB_REGIME_FEATURE_SET_V2,
        feature_profile="extended_v2",
        pair="BTCUSDT",
        window_start_ns=1_000_000_000,
        window_end_ns=2_000_000_000,
        sample_count=2,
        prediction_count=1,
        transition_risk_summary=RegimeDetectorShadowAuditMetricSummary(
            count=1,
            min_value=0.8,
            max_value=0.8,
            mean_value=0.8,
            last_value=0.8,
        ),
        duration_bucket_counts=RegimeDetectorShadowAuditDurationCounts(
            short=1,
            total=1,
        ),
        shadow_metrics={"shadow_diff_pct": 0.02},
    )

    restored = RegimeDetectorShadowAuditBundle.model_validate_json(
        bundle.model_dump_json()
    )

    assert restored == bundle
    assert restored.feature_set_version == RegimeDetectorFeatureSetVersion.LOB_REGIME_FEATURE_SET_V2


def test_regime_detector_shadow_audit_diagnosis_round_trip_is_stable() -> None:
    diagnosis = RegimeDetectorShadowAuditDiagnosis(
        status=RegimeDetectorShadowAuditDiagnosisStatus.CAUTION,
        diagnosis_ready=True,
        feature_set_version=RegimeDetectorFeatureSetVersion.LOB_REGIME_FEATURE_SET_V2,
        feature_profile="extended_v2",
        pair="BTCUSDT",
        sample_count=2,
        prediction_count=1,
        insufficient_data_rate=0.5,
        runtime_stale_rate=0.0,
        observation_coverage_mean=0.55,
        shadow_diff_pct=0.02,
        finding_count=1,
        caution_flags=("REGIME_DETECTOR_OBSERVATION_COVERAGE_LOW",),
        findings=(
            RegimeDetectorShadowAuditFinding(
                code=RegimeDetectorShadowAuditFindingCode.COVERAGE_TOO_LOW,
                severity=RegimeDetectorShadowAuditFindingSeverity.CAUTION,
                detail="Mean observation coverage 0.550 is below 0.600.",
            ),
        ),
    )

    restored = RegimeDetectorShadowAuditDiagnosis.model_validate_json(
        diagnosis.model_dump_json()
    )

    assert restored == diagnosis
