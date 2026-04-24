from __future__ import annotations

import base64
from datetime import UTC, datetime

from interface_contracts import MlModelArtifact, MlModelWindow, PromotionState
from meta_learning import (
    MlModelDriftSnapshot,
    MlModelRiskRegistry,
    MlModelRiskState,
    MlModelRuntimeStage,
    evaluate_model_risk_signal,
)


def _artifact() -> MlModelArtifact:
    return MlModelArtifact.create(
        feature_names=("feature_a", "feature_b"),
        feature_hash="7" * 64,
        pair_universe=("BTCUSDT",),
        train_window=MlModelWindow(
            start_at=datetime(2025, 9, 24, tzinfo=UTC),
            end_at=datetime(2026, 3, 22, tzinfo=UTC),
        ),
        validation_window=MlModelWindow(
            start_at=datetime(2026, 3, 23, tzinfo=UTC),
            end_at=datetime(2026, 4, 21, tzinfo=UTC),
        ),
        oos_sharpe=1.0,
        backtest_sharpe=1.2,
        ks_test_features_pvalue=0.4,
        shadow_diff_pct=0.02,
        promotion_state=PromotionState.REPLAY_ONLY,
        training_seed=12,
        created_at=datetime(2026, 4, 22, 12, 0, tzinfo=UTC),
        calibration_version="cal.v1",
        dataset_hash="8" * 64,
        model_bytes_b64=base64.b64encode(b'{"prediction":0.7}').decode("ascii"),
    )


def test_model_risk_registry_stores_identity_and_drift_metadata() -> None:
    artifact = _artifact()
    registry = MlModelRiskRegistry().register_artifact(artifact)
    snapshot = MlModelDriftSnapshot(
        stage=MlModelRuntimeStage.SHADOW,
        created_at=datetime(2026, 4, 23, 12, 0, tzinfo=UTC),
        feature_ks_pvalue=0.41,
        shadow_diff_pct=0.02,
    )

    updated = registry.append_drift_snapshot(artifact_id=artifact.artifact_hash, snapshot=snapshot)
    latest = updated.latest(artifact.artifact_hash)

    assert latest.artifact_id == artifact.artifact_hash
    assert latest.feature_hash == artifact.feature_hash
    assert latest.drift_snapshots == (snapshot,)


def test_model_risk_registry_flags_synthetic_drift() -> None:
    artifact = _artifact()
    registry = MlModelRiskRegistry().register_artifact(artifact)
    blocked_registry = registry.append_drift_snapshot(
        artifact_id=artifact.artifact_hash,
        snapshot=MlModelDriftSnapshot(
            stage=MlModelRuntimeStage.SHADOW,
            created_at=datetime(2026, 4, 23, 12, 0, tzinfo=UTC),
            feature_ks_pvalue=0.03,
        ),
    )
    paused_registry = registry.append_drift_snapshot(
        artifact_id=artifact.artifact_hash,
        snapshot=MlModelDriftSnapshot(
            stage=MlModelRuntimeStage.LIVE,
            created_at=datetime(2026, 4, 23, 12, 0, tzinfo=UTC),
            live_diff_pct=0.12,
        ),
    )

    blocked_signal = evaluate_model_risk_signal(blocked_registry.latest(artifact.artifact_hash))
    paused_signal = evaluate_model_risk_signal(paused_registry.latest(artifact.artifact_hash))

    assert blocked_signal.state == MlModelRiskState.PROMOTION_BLOCK
    assert blocked_signal.promotion_block is True
    assert paused_signal.state == MlModelRiskState.PAUSE
    assert paused_signal.pause_signal is True


def test_model_risk_registry_fails_closed_on_missing_data() -> None:
    artifact = _artifact()
    registry = MlModelRiskRegistry().register_artifact(artifact)

    signal = evaluate_model_risk_signal(registry.latest(artifact.artifact_hash))

    assert signal.state == MlModelRiskState.INSUFFICIENT_DATA
    assert signal.promotion_block is True
