from __future__ import annotations

import base64
from datetime import UTC, datetime, timedelta
from typing import cast

import pytest

from interface_contracts import (
    PromotionState,
    RegimeDetectorArtifact,
    RegimeDetectorFeatureSetVersion,
    RegimeDetectorLabelConfig,
    RegimeDetectorWindow,
)
from local_replay_runtime import (
    LocalLabRegimeDetectorArtifactTrainingReport,
    build_local_lab_regime_detector_profile_comparison_report,
)
from local_replay_runtime.historical_snapshot_loader import HistoricalSnapshotBatch


def _artifact(
    *,
    feature_names: tuple[str, ...],
    accuracy: float,
    brier: float,
    ks_pvalue: float,
    shadow_diff_pct: float = 0.02,
) -> RegimeDetectorArtifact:
    created_at = datetime(2026, 4, 23, 12, 0, tzinfo=UTC)
    return RegimeDetectorArtifact.create(
        feature_set_version=RegimeDetectorFeatureSetVersion.LOB_REGIME_FEATURE_SET_V2,
        feature_names=feature_names,
        feature_hash="a" * 64,
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
        dataset_hash="b" * 64,
        model_bytes_b64=base64.b64encode(b'{"prediction":[0.8,0.2,0.7,0.0]}').decode("ascii"),
        stale_after=created_at + timedelta(days=30),
    )


def _report(
    *,
    feature_profile: str,
    ready: bool,
    status: str,
    feature_count: int,
    accuracy: float | None = None,
    brier: float | None = None,
    ks_pvalue: float | None = None,
) -> LocalLabRegimeDetectorArtifactTrainingReport:
    feature_names = tuple(f"f{index}" for index in range(feature_count))
    artifact = None
    artifact_hash = None
    if ready:
        assert accuracy is not None
        assert brier is not None
        assert ks_pvalue is not None
        artifact = _artifact(
            feature_names=feature_names,
            accuracy=accuracy,
            brier=brier,
            ks_pvalue=ks_pvalue,
        )
        artifact_hash = artifact.artifact_hash
    return LocalLabRegimeDetectorArtifactTrainingReport(
        dataset_id="dataset-regime-1",
        status=status,
        ready=ready,
        feature_set_version=RegimeDetectorFeatureSetVersion.LOB_REGIME_FEATURE_SET_V2,
        feature_profile=feature_profile,
        sample_count=240,
        training_row_count=210,
        selected_feature_count=feature_count,
        selected_feature_names=feature_names,
        pair_scope=("BTCUSDT",),
        artifact=artifact,
        artifact_hash=artifact_hash,
        blocking_reasons=() if ready else ("TRAINING_FAILED",),
    )


def _dummy_batch() -> HistoricalSnapshotBatch:
    return cast(
        HistoricalSnapshotBatch,
        object(),
    )


def _label_config() -> RegimeDetectorLabelConfig:
    return RegimeDetectorLabelConfig()


def test_profile_comparison_runs_all_three_profiles_and_keeps_extended_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    reports = {
        "core_v1": _report(
            feature_profile="core_v1",
            ready=True,
            status="trained",
            feature_count=10,
            accuracy=0.72,
            brier=0.20,
            ks_pvalue=0.11,
        ),
        "extended_v2": _report(
            feature_profile="extended_v2",
            ready=True,
            status="trained",
            feature_count=13,
            accuracy=0.75,
            brier=0.18,
            ks_pvalue=0.12,
        ),
        "full_v2": _report(
            feature_profile="full_v2",
            ready=True,
            status="trained",
            feature_count=27,
            accuracy=0.74,
            brier=0.19,
            ks_pvalue=0.10,
        ),
    }

    def _fake_builder(**kwargs: object) -> LocalLabRegimeDetectorArtifactTrainingReport:
        feature_profile = cast(str, kwargs["feature_profile"])
        calls.append(feature_profile)
        return reports[feature_profile]

    monkeypatch.setattr(
        "local_replay_runtime.regime_detector_profile_comparison.build_local_lab_regime_detector_artifact_training_report",
        _fake_builder,
    )

    report = build_local_lab_regime_detector_profile_comparison_report(
        correlation_id="corr-regime-profiles-1",
        batch=_dummy_batch(),
        artifact_id_prefix="regime-profile-compare",
        calibration_version="lob-regime.v2",
        training_seed=17,
        label_config=_label_config(),
    )

    assert calls == ["core_v1", "extended_v2", "full_v2"]
    assert report.status == "ready"
    assert report.comparison_ready is True
    assert report.ready_profile_count == 3
    assert report.winner_profile == "extended_v2"
    assert report.recommended_default_profile == "extended_v2"
    assert report.recommendation == "keep_extended_v2_default"
    assert report.full_v2_disposition == "research_only"


def test_profile_comparison_falls_back_to_core_when_extended_is_not_ready(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reports = {
        "core_v1": _report(
            feature_profile="core_v1",
            ready=True,
            status="trained",
            feature_count=10,
            accuracy=0.74,
            brier=0.19,
            ks_pvalue=0.12,
        ),
        "extended_v2": _report(
            feature_profile="extended_v2",
            ready=False,
            status="training_failed",
            feature_count=13,
        ),
        "full_v2": _report(
            feature_profile="full_v2",
            ready=True,
            status="trained",
            feature_count=27,
            accuracy=0.70,
            brier=0.22,
            ks_pvalue=0.09,
        ),
    }

    monkeypatch.setattr(
        "local_replay_runtime.regime_detector_profile_comparison.build_local_lab_regime_detector_artifact_training_report",
        lambda **kwargs: reports[cast(str, kwargs["feature_profile"])],
    )

    report = build_local_lab_regime_detector_profile_comparison_report(
        correlation_id="corr-regime-profiles-2",
        batch=_dummy_batch(),
        artifact_id_prefix="regime-profile-compare",
        calibration_version="lob-regime.v2",
        training_seed=17,
    )

    assert report.status == "partial"
    assert report.comparison_ready is True
    assert report.recommended_default_profile == "core_v1"
    assert report.recommendation == "fallback_to_core_v1"
    assert "REGIME_DETECTOR_PROFILE_COMPARISON_PARTIAL" in report.caution_flags


def test_profile_comparison_marks_full_as_candidate_without_making_it_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reports = {
        "core_v1": _report(
            feature_profile="core_v1",
            ready=True,
            status="trained",
            feature_count=10,
            accuracy=0.72,
            brier=0.21,
            ks_pvalue=0.10,
        ),
        "extended_v2": _report(
            feature_profile="extended_v2",
            ready=True,
            status="trained",
            feature_count=13,
            accuracy=0.75,
            brier=0.19,
            ks_pvalue=0.11,
        ),
        "full_v2": _report(
            feature_profile="full_v2",
            ready=True,
            status="trained",
            feature_count=27,
            accuracy=0.79,
            brier=0.18,
            ks_pvalue=0.12,
        ),
    }

    monkeypatch.setattr(
        "local_replay_runtime.regime_detector_profile_comparison.build_local_lab_regime_detector_artifact_training_report",
        lambda **kwargs: reports[cast(str, kwargs["feature_profile"])],
    )

    report = build_local_lab_regime_detector_profile_comparison_report(
        correlation_id="corr-regime-profiles-3",
        batch=_dummy_batch(),
        artifact_id_prefix="regime-profile-compare",
        calibration_version="lob-regime.v2",
        training_seed=17,
    )

    assert report.winner_profile == "full_v2"
    assert report.recommended_default_profile == "extended_v2"
    assert report.recommendation == "promote_full_v2_candidate"
    assert report.full_v2_disposition == "candidate_real"
