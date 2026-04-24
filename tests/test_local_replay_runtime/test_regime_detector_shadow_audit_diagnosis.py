from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from interface_contracts import (
    PromotionState,
    RegimeDetectorArtifact,
    RegimeDetectorFeatureSetVersion,
    RegimeDetectorShadowAuditDiagnosisStatus,
    RegimeDetectorShadowAuditFindingCode,
    RegimeDetectorWindow,
)
from local_replay_runtime import (
    build_local_lab_regime_detector_shadow_audit_diagnosis,
    load_regime_detector_shadow_audit_bundle,
)
from monitoring import (
    build_regime_detector_shadow_audit_bundle,
    build_regime_detector_shadow_audit_sample,
)


def _artifact() -> RegimeDetectorArtifact:
    created_at = datetime(2026, 4, 23, 12, 0, tzinfo=UTC)
    return RegimeDetectorArtifact.create(
        feature_set_version=RegimeDetectorFeatureSetVersion.LOB_REGIME_FEATURE_SET_V2,
        feature_names=("spread_bps", "order_book_imbalance"),
        feature_hash="b" * 64,
        pair_universe=("BTCUSDT",),
        train_window=RegimeDetectorWindow(
            start_at=datetime(2026, 1, 1, tzinfo=UTC),
            end_at=datetime(2026, 3, 31, tzinfo=UTC),
        ),
        validation_window=RegimeDetectorWindow(
            start_at=datetime(2026, 4, 1, tzinfo=UTC),
            end_at=datetime(2026, 4, 22, tzinfo=UTC),
        ),
        regime_labels=("calm", "transition", "toxic"),
        oos_metrics={"transition_auc": 0.71},
        shadow_metrics={"shadow_diff_pct": 0.02},
        promotion_state=PromotionState.REPLAY_ONLY,
        training_seed=17,
        created_at=created_at,
        calibration_version="lob-regime.v1",
        dataset_hash="c" * 64,
        model_bytes_b64="eyJwcmVkaWN0aW9uIjpbMC44LDAuMiwwLjddfQ==",
        stale_after=created_at + timedelta(days=30),
    )


def _sample(
    *,
    computed_at_ns: int,
    artifact_status: str,
    signal_status: str,
    transition: float = 0.0,
    stability: float = 1.0,
    toxicity: float = 0.0,
    coverage: float | None = None,
    artifact_hash: str | None = None,
    feature_hash: str = "b" * 64,
    pair: str = "BTCUSDT",
) -> object:
    return build_regime_detector_shadow_audit_sample(
        artifact_status=artifact_status,
        observation_coverage_ratio=coverage,
        signal_payload={
            "status": signal_status,
            "pair": pair,
            "computed_at_ns": computed_at_ns,
            "artifact_hash": artifact_hash or _artifact().artifact_hash,
            "feature_hash": feature_hash,
            "regime_transition_risk": transition,
            "regime_stability_score": stability,
            "market_toxicity_score": toxicity,
            "expected_duration_bucket": "short",
            "reason_codes": ("RC",),
        },
    )


def test_regime_detector_shadow_audit_diagnosis_is_healthy_for_matching_bundle() -> None:
    artifact = _artifact()
    bundle = build_regime_detector_shadow_audit_bundle(
        samples=(
            _sample(
                computed_at_ns=1_000_000_000,
                artifact_status="loaded",
                signal_status="active",
                transition=0.8,
                stability=0.3,
                toxicity=0.7,
                coverage=0.9,
                artifact_hash=artifact.artifact_hash,
            ),
            _sample(
                computed_at_ns=2_000_000_000,
                artifact_status="loaded",
                signal_status="active",
                transition=0.6,
                stability=0.5,
                toxicity=0.4,
                coverage=0.8,
                artifact_hash=artifact.artifact_hash,
            ),
        ),
        feature_set_version=artifact.feature_set_version,
        feature_profile="extended_v2",
        shadow_metrics={"shadow_diff_pct": 0.02},
    )

    diagnosis = build_local_lab_regime_detector_shadow_audit_diagnosis(
        bundle,
        expected_artifact=artifact,
        expected_feature_profile="extended_v2",
    )

    assert diagnosis.status == RegimeDetectorShadowAuditDiagnosisStatus.HEALTHY
    assert diagnosis.diagnosis_ready is True
    assert diagnosis.finding_count == 0
    assert diagnosis.blocking_reasons == ()
    assert diagnosis.caution_flags == ()


def test_regime_detector_shadow_audit_diagnosis_blocks_on_schema_hash_and_drift() -> None:
    artifact = _artifact()
    bundle = build_regime_detector_shadow_audit_bundle(
        samples=(
            _sample(
                computed_at_ns=1_000_000_000,
                artifact_status="feature_set_version_mismatch",
                signal_status="feature_schema_mismatch",
                artifact_hash="a" * 64,
                pair="ETHUSDT",
            ),
        ),
        feature_set_version=RegimeDetectorFeatureSetVersion.LOB_REGIME_FEATURE_SET_V1,
        feature_profile="core_v1",
        shadow_metrics={"shadow_diff_pct": 0.1},
    )

    diagnosis = build_local_lab_regime_detector_shadow_audit_diagnosis(
        bundle,
        expected_artifact=artifact,
        expected_feature_profile="extended_v2",
    )

    finding_codes = tuple(finding.code for finding in diagnosis.findings)
    assert diagnosis.status == RegimeDetectorShadowAuditDiagnosisStatus.BLOCKED
    assert RegimeDetectorShadowAuditFindingCode.ARTIFACT_SCHEMA_MISMATCH in finding_codes
    assert RegimeDetectorShadowAuditFindingCode.SHADOW_DRIFT_HIGH in finding_codes
    assert RegimeDetectorShadowAuditFindingCode.FEATURE_PROFILE_MISMATCH in finding_codes
    assert RegimeDetectorShadowAuditFindingCode.PAIR_NOT_IN_UNIVERSE in finding_codes


def test_regime_detector_shadow_audit_diagnosis_marks_low_coverage_and_no_predictions_as_caution() -> None:
    artifact = _artifact()
    bundle = build_regime_detector_shadow_audit_bundle(
        samples=(
            _sample(
                computed_at_ns=1_000_000_000,
                artifact_status="loaded",
                signal_status="neutral",
                coverage=0.4,
                artifact_hash=artifact.artifact_hash,
            ),
            _sample(
                computed_at_ns=2_000_000_000,
                artifact_status="stale",
                signal_status="neutral",
                coverage=0.5,
                artifact_hash=artifact.artifact_hash,
            ),
        ),
        feature_set_version=artifact.feature_set_version,
        feature_profile="extended_v2",
        shadow_metrics={"shadow_diff_pct": 0.02},
    )

    diagnosis = build_local_lab_regime_detector_shadow_audit_diagnosis(
        bundle,
        expected_artifact=artifact,
        expected_feature_profile="extended_v2",
    )

    finding_codes = tuple(finding.code for finding in diagnosis.findings)
    assert diagnosis.status == RegimeDetectorShadowAuditDiagnosisStatus.CAUTION
    assert RegimeDetectorShadowAuditFindingCode.COVERAGE_TOO_LOW in finding_codes
    assert RegimeDetectorShadowAuditFindingCode.NO_ACTIVE_PREDICTIONS in finding_codes
    assert RegimeDetectorShadowAuditFindingCode.RUNTIME_STALE_PRESENT in finding_codes


def test_load_regime_detector_shadow_audit_bundle_round_trips_from_disk(tmp_path: Path) -> None:
    artifact = _artifact()
    bundle = build_regime_detector_shadow_audit_bundle(
        samples=(
            _sample(
                computed_at_ns=1_000_000_000,
                artifact_status="loaded",
                signal_status="active",
                transition=0.8,
                coverage=0.9,
                artifact_hash=artifact.artifact_hash,
            ),
        ),
        feature_set_version=artifact.feature_set_version,
        feature_profile="extended_v2",
        shadow_metrics={"shadow_diff_pct": 0.02},
    )
    bundle_path = tmp_path / "regime_detector_shadow_audit_bundle.json"
    bundle_path.write_text(bundle.model_dump_json(indent=2), encoding="utf-8")

    restored = load_regime_detector_shadow_audit_bundle(str(bundle_path))

    assert restored == bundle
