from __future__ import annotations

import base64
from datetime import UTC, datetime, timedelta
from typing import cast

import pytest

from interface_contracts import (
    DashboardGovernedCommandKind,
    DashboardGovernedCommandResult,
    DashboardGovernedCommandStatus,
    PromotionState,
    RegimeDetectorArtifact,
    RegimeDetectorFeatureSetVersion,
    RegimeDetectorWindow,
)
from local_replay_runtime import (
    LocalLabRegimeDetectorArtifactTrainingReport,
    build_local_lab_regime_detector_final_audit_report,
    build_local_lab_regime_detector_final_audit_report_from_vps_command_result,
)
from local_replay_runtime.historical_snapshot_loader import HistoricalSnapshotBatch
from monitoring import (
    build_regime_detector_shadow_audit_bundle,
    build_regime_detector_shadow_audit_sample,
)
from tests.support_paths import make_repo_scratch_dir


def _artifact(
    *,
    feature_names: tuple[str, ...],
    accuracy: float,
    brier: float,
    ks_pvalue: float,
    feature_hash: str = "b" * 64,
    shadow_diff_pct: float = 0.02,
) -> RegimeDetectorArtifact:
    created_at = datetime(2026, 4, 23, 12, 0, tzinfo=UTC)
    return RegimeDetectorArtifact.create(
        feature_set_version=RegimeDetectorFeatureSetVersion.LOB_REGIME_FEATURE_SET_V2,
        feature_names=feature_names,
        feature_hash=feature_hash,
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
        oos_metrics={
            "transition_accuracy": accuracy,
            "transition_brier_score": brier,
            "feature_ks_min_pvalue": ks_pvalue,
        },
        shadow_metrics={"shadow_diff_pct": shadow_diff_pct},
        promotion_state=PromotionState.REPLAY_ONLY,
        training_seed=17,
        created_at=created_at,
        calibration_version="lob-regime.v2",
        dataset_hash="c" * 64,
        model_bytes_b64=base64.b64encode(b'{"prediction":[0.8,0.2,0.7,0.0]}').decode("ascii"),
        stale_after=created_at + timedelta(days=30),
    )


def _report(
    *,
    feature_profile: str,
    accuracy: float,
    brier: float,
    ks_pvalue: float,
    feature_count: int,
) -> LocalLabRegimeDetectorArtifactTrainingReport:
    feature_names = tuple(f"{feature_profile}_f{index}" for index in range(feature_count))
    artifact = _artifact(
        feature_names=feature_names,
        accuracy=accuracy,
        brier=brier,
        ks_pvalue=ks_pvalue,
        feature_hash=(feature_profile[0] * 64),
    )
    return LocalLabRegimeDetectorArtifactTrainingReport(
        dataset_id="dataset-regime-1",
        status="trained",
        ready=True,
        feature_set_version=RegimeDetectorFeatureSetVersion.LOB_REGIME_FEATURE_SET_V2,
        feature_profile=feature_profile,
        sample_count=240,
        training_row_count=210,
        selected_feature_count=feature_count,
        selected_feature_names=feature_names,
        pair_scope=("BTCUSDT",),
        artifact=artifact,
        artifact_hash=artifact.artifact_hash,
        blocking_reasons=(),
    )


def _dummy_batch() -> HistoricalSnapshotBatch:
    return cast(HistoricalSnapshotBatch, object())


def _healthy_bundle(report: LocalLabRegimeDetectorArtifactTrainingReport) -> object:
    artifact = report.artifact
    assert artifact is not None
    return build_regime_detector_shadow_audit_bundle(
        samples=(
            build_regime_detector_shadow_audit_sample(
                artifact_status="loaded",
                observation_coverage_ratio=0.9,
                signal_payload={
                    "status": "active",
                    "pair": "BTCUSDT",
                    "computed_at_ns": 1_000_000_000,
                    "artifact_hash": artifact.artifact_hash,
                    "feature_hash": artifact.feature_hash,
                    "regime_transition_risk": 0.8,
                    "regime_stability_score": 0.3,
                    "market_toxicity_score": 0.7,
                    "expected_duration_bucket": "short",
                    "reason_codes": ("RC",),
                },
            ),
        ),
        feature_set_version=artifact.feature_set_version,
        feature_profile=report.feature_profile,
        shadow_metrics={"shadow_diff_pct": 0.02},
    )


def test_final_audit_report_requires_vps_shadow_bundle_for_full_readiness(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reports = {
        "core_v1": _report(feature_profile="core_v1", accuracy=0.72, brier=0.20, ks_pvalue=0.11, feature_count=10),
        "extended_v2": _report(feature_profile="extended_v2", accuracy=0.75, brier=0.18, ks_pvalue=0.12, feature_count=13),
        "full_v2": _report(feature_profile="full_v2", accuracy=0.74, brier=0.19, ks_pvalue=0.10, feature_count=27),
    }
    monkeypatch.setattr(
        "local_replay_runtime.regime_detector_final_audit_report.build_local_lab_regime_detector_artifact_training_report",
        lambda **kwargs: reports[cast(str, kwargs["feature_profile"])],
    )

    report = build_local_lab_regime_detector_final_audit_report(
        correlation_id="corr-regime-final-1",
        batch=_dummy_batch(),
        artifact_id_prefix="regime-final",
        calibration_version="lob-regime.v2",
        training_seed=17,
    )

    assert report.status == "partial"
    assert report.audit_ready is False
    assert report.shadow_audit_present is False
    assert report.recommended_default_profile == "extended_v2"
    assert report.final_recommendation == "collect_vps_shadow_audit_bundle"


def test_final_audit_report_blocks_when_uploaded_artifact_diagnosis_is_blocked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reports = {
        "core_v1": _report(feature_profile="core_v1", accuracy=0.72, brier=0.20, ks_pvalue=0.11, feature_count=10),
        "extended_v2": _report(feature_profile="extended_v2", accuracy=0.75, brier=0.18, ks_pvalue=0.12, feature_count=13),
        "full_v2": _report(feature_profile="full_v2", accuracy=0.74, brier=0.19, ks_pvalue=0.10, feature_count=27),
    }
    monkeypatch.setattr(
        "local_replay_runtime.regime_detector_final_audit_report.build_local_lab_regime_detector_artifact_training_report",
        lambda **kwargs: reports[cast(str, kwargs["feature_profile"])],
    )
    extended = reports["extended_v2"]
    assert extended.artifact is not None
    bundle = build_regime_detector_shadow_audit_bundle(
        samples=(
            build_regime_detector_shadow_audit_sample(
                artifact_status="feature_set_version_mismatch",
                observation_coverage_ratio=0.9,
                signal_payload={
                    "status": "feature_schema_mismatch",
                    "pair": "ETHUSDT",
                    "computed_at_ns": 1_000_000_000,
                    "artifact_hash": extended.artifact.artifact_hash,
                    "feature_hash": extended.artifact.feature_hash,
                    "regime_transition_risk": 0.0,
                    "regime_stability_score": 1.0,
                    "market_toxicity_score": 0.0,
                    "expected_duration_bucket": "short",
                    "reason_codes": ("RC",),
                },
            ),
        ),
        feature_set_version=RegimeDetectorFeatureSetVersion.LOB_REGIME_FEATURE_SET_V1,
        feature_profile="extended_v2",
        shadow_metrics={"shadow_diff_pct": 0.1},
    )

    report = build_local_lab_regime_detector_final_audit_report(
        correlation_id="corr-regime-final-2",
        batch=_dummy_batch(),
        artifact_id_prefix="regime-final",
        calibration_version="lob-regime.v2",
        training_seed=17,
        shadow_audit_bundle=bundle,
    )

    assert report.status == "blocked"
    assert report.audit_ready is False
    assert report.shadow_audit_diagnosis is not None
    assert report.final_recommendation == "investigate_uploaded_artifact_root_cause"
    assert "REGIME_DETECTOR_SCHEMA_MISMATCH" in report.blocking_reasons


def test_final_audit_report_flags_uploaded_profile_different_from_lab_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reports = {
        "core_v1": _report(feature_profile="core_v1", accuracy=0.72, brier=0.20, ks_pvalue=0.11, feature_count=10),
        "extended_v2": _report(feature_profile="extended_v2", accuracy=0.75, brier=0.18, ks_pvalue=0.12, feature_count=13),
        "full_v2": _report(feature_profile="full_v2", accuracy=0.74, brier=0.19, ks_pvalue=0.10, feature_count=27),
    }
    monkeypatch.setattr(
        "local_replay_runtime.regime_detector_final_audit_report.build_local_lab_regime_detector_artifact_training_report",
        lambda **kwargs: reports[cast(str, kwargs["feature_profile"])],
    )
    full_bundle = _healthy_bundle(reports["full_v2"])

    report = build_local_lab_regime_detector_final_audit_report(
        correlation_id="corr-regime-final-3",
        batch=_dummy_batch(),
        artifact_id_prefix="regime-final",
        calibration_version="lob-regime.v2",
        training_seed=17,
        shadow_audit_bundle=full_bundle,
    )

    assert report.status == "partial"
    assert report.audit_ready is False
    assert report.uploaded_profile == "full_v2"
    assert report.uploaded_profile_matches_lab_default is False
    assert report.final_recommendation == "uploaded_profile_differs_from_lab_default"


def test_final_audit_report_is_ready_when_uploaded_profile_matches_lab_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reports = {
        "core_v1": _report(feature_profile="core_v1", accuracy=0.72, brier=0.20, ks_pvalue=0.11, feature_count=10),
        "extended_v2": _report(feature_profile="extended_v2", accuracy=0.75, brier=0.18, ks_pvalue=0.12, feature_count=13),
        "full_v2": _report(feature_profile="full_v2", accuracy=0.74, brier=0.19, ks_pvalue=0.10, feature_count=27),
    }
    monkeypatch.setattr(
        "local_replay_runtime.regime_detector_final_audit_report.build_local_lab_regime_detector_artifact_training_report",
        lambda **kwargs: reports[cast(str, kwargs["feature_profile"])],
    )
    extended_bundle = _healthy_bundle(reports["extended_v2"])
    scratch_dir = make_repo_scratch_dir("regime_detector_final_audit", "ready")
    bundle_path = scratch_dir / "regime_detector_shadow_audit_bundle.json"
    bundle_path.write_text(extended_bundle.model_dump_json(indent=2), encoding="utf-8")

    report = build_local_lab_regime_detector_final_audit_report(
        correlation_id="corr-regime-final-4",
        batch=_dummy_batch(),
        artifact_id_prefix="regime-final",
        calibration_version="lob-regime.v2",
        training_seed=17,
        shadow_audit_bundle_ref=str(bundle_path),
    )

    assert report.status == "ready"
    assert report.audit_ready is True
    assert report.uploaded_profile == "extended_v2"
    assert report.uploaded_profile_matches_lab_default is True
    assert report.final_recommendation == "uploaded_profile_matches_lab_recommendation"


def test_final_audit_report_can_be_built_from_vps_command_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reports = {
        "core_v1": _report(feature_profile="core_v1", accuracy=0.72, brier=0.20, ks_pvalue=0.11, feature_count=10),
        "extended_v2": _report(feature_profile="extended_v2", accuracy=0.75, brier=0.18, ks_pvalue=0.12, feature_count=13),
        "full_v2": _report(feature_profile="full_v2", accuracy=0.74, brier=0.19, ks_pvalue=0.10, feature_count=27),
    }
    monkeypatch.setattr(
        "local_replay_runtime.regime_detector_final_audit_report.build_local_lab_regime_detector_artifact_training_report",
        lambda **kwargs: reports[cast(str, kwargs["feature_profile"])],
    )
    extended_bundle = _healthy_bundle(reports["extended_v2"])
    scratch_dir = make_repo_scratch_dir("regime_detector_final_audit", "from_vps")
    bundle_path = scratch_dir / "regime_detector_shadow_audit_bundle.json"
    bundle_path.write_text(extended_bundle.model_dump_json(indent=2), encoding="utf-8")
    command_result = DashboardGovernedCommandResult(
        timestamp_ms=1_700_000_000_000,
        correlation_id="corr-regime-final-5",
        result_id="req-5.result",
        request_id="req-5",
        command_kind=DashboardGovernedCommandKind.REQUEST_EXPORT_REGIME_DETECTOR_SHADOW_AUDIT_BUNDLE,
        status=DashboardGovernedCommandStatus.COMPLETED,
        idempotency_key="req-5:no_artifact:request_export_regime_detector_shadow_audit_bundle",
        reason_codes=("dashboard.command.request_export_regime_detector_shadow_audit_bundle.completed",),
        detail="request_export_regime_detector_shadow_audit_bundle completed",
        export_ref=str(bundle_path),
    )

    report = build_local_lab_regime_detector_final_audit_report_from_vps_command_result(
        correlation_id="corr-regime-final-5",
        batch=_dummy_batch(),
        artifact_id_prefix="regime-final",
        calibration_version="lob-regime.v2",
        training_seed=17,
        command_result=command_result,
    )

    assert report.status == "ready"
    assert report.audit_ready is True
    assert report.uploaded_profile == "extended_v2"
