from __future__ import annotations

import base64
from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from interface_contracts import MlModelArtifact, MlModelDriftBaseline, MlModelWindow, PromotionState


def _build_artifact() -> MlModelArtifact:
    created_at = datetime(2026, 4, 22, 12, 0, tzinfo=UTC)
    return MlModelArtifact.create(
        feature_names=("feature_a", "feature_b"),
        feature_hash="a" * 64,
        pair_universe=("BTCUSDT", "ETHUSDT"),
        train_window=MlModelWindow(
            start_at=datetime(2025, 9, 24, 0, 0, tzinfo=UTC),
            end_at=datetime(2026, 3, 22, 0, 0, tzinfo=UTC),
        ),
        validation_window=MlModelWindow(
            start_at=datetime(2026, 3, 23, 0, 0, tzinfo=UTC),
            end_at=datetime(2026, 4, 21, 0, 0, tzinfo=UTC),
        ),
        oos_sharpe=1.1,
        backtest_sharpe=1.3,
        ks_test_features_pvalue=0.41,
        shadow_diff_pct=0.02,
        promotion_state=PromotionState.REPLAY_ONLY,
        training_seed=7,
        created_at=created_at,
        calibration_version="cal.v1",
        dataset_hash="b" * 64,
        model_bytes_b64=base64.b64encode(b'{"prediction":0.7}').decode("ascii"),
        drift_baseline=MlModelDriftBaseline(
            forecast_mean=0.12,
            win_rate=0.56,
            ce_mean=0.08,
            feature_ks_reference_pvalue=0.44,
            sample_count=180,
        ),
        stale_after=created_at + timedelta(days=30),
    )


def test_ml_model_artifact_is_frozen_and_typed() -> None:
    artifact = _build_artifact()

    assert artifact.model_family.value == "lightgbm"
    with pytest.raises(ValidationError):
        artifact.feature_hash = "c" * 64  # type: ignore[misc]


def test_ml_model_artifact_rejects_invalid_hash() -> None:
    artifact = _build_artifact()
    payload = artifact.model_dump(mode="python")
    payload["artifact_hash"] = "0" * 64

    with pytest.raises(ValidationError):
        MlModelArtifact.model_validate(payload)


def test_ml_model_artifact_rejects_missing_mandatory_fields() -> None:
    artifact = _build_artifact()
    payload = artifact.model_dump(mode="python")
    payload.pop("feature_hash")

    with pytest.raises(ValidationError):
        MlModelArtifact.model_validate(payload)


def test_ml_model_artifact_round_trip_serialization_is_stable() -> None:
    artifact = _build_artifact()

    restored = MlModelArtifact.model_validate_json(artifact.model_dump_json())

    assert restored == artifact
    assert restored.artifact_hash == artifact.artifact_hash
