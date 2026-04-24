from __future__ import annotations

import base64
from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from interface_contracts import (
    PromotionState,
    RegimeDetectorArtifact,
    RegimeDetectorFeatureSetVersion,
    RegimeDetectorWindow,
)


def _artifact() -> RegimeDetectorArtifact:
    created_at = datetime(2026, 4, 23, 12, 0, tzinfo=UTC)
    return RegimeDetectorArtifact.create(
        feature_set_version=RegimeDetectorFeatureSetVersion.LOB_REGIME_FEATURE_SET_V2,
        feature_names=("spread_bps", "order_book_imbalance", "spoof_like_suspicion_bid"),
        feature_hash="a" * 64,
        pair_universe=("BTCUSDT", "ETHUSDT"),
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
        dataset_hash="b" * 64,
        model_bytes_b64=base64.b64encode(b'{"prediction":[0.8,0.2,0.7,0.0]}').decode("ascii"),
        stale_after=created_at + timedelta(days=30),
    )


def test_regime_detector_artifact_is_frozen_and_hash_validated() -> None:
    artifact = _artifact()

    assert artifact.output_semantics.value == "lob_regime_detector.v1"
    assert artifact.feature_set_version == RegimeDetectorFeatureSetVersion.LOB_REGIME_FEATURE_SET_V2
    assert len(artifact.artifact_hash) == 64
    with pytest.raises(ValidationError):
        artifact.feature_hash = "c" * 64  # type: ignore[misc]


def test_regime_detector_artifact_rejects_invalid_hash() -> None:
    artifact = _artifact()
    payload = artifact.model_dump(mode="python")
    payload["artifact_hash"] = "0" * 64

    with pytest.raises(ValidationError):
        RegimeDetectorArtifact.model_validate(payload)


def test_regime_detector_artifact_rejects_invalid_duration_bucket() -> None:
    artifact = _artifact()
    payload = artifact.model_dump(mode="python")
    payload["duration_bucket_scheme"] = ("fragile", "forever")

    with pytest.raises(ValidationError):
        RegimeDetectorArtifact.model_validate(payload)


def test_regime_detector_artifact_round_trip_serialization_is_stable() -> None:
    artifact = _artifact()

    restored = RegimeDetectorArtifact.model_validate_json(artifact.model_dump_json())

    assert restored == artifact
    assert restored.artifact_hash == artifact.artifact_hash
