from __future__ import annotations

from datetime import UTC, datetime

import pytest

from complete_enablers import MlConfidenceEnabler, apply_ml_score_fusion
from interface_contracts import MlModelArtifact, MlModelWindow, PromotionState, Side


def _artifact() -> MlModelArtifact:
    created_at = datetime(2026, 4, 22, 12, 0, tzinfo=UTC)
    return MlModelArtifact.create(
        feature_names=("feature_a", "feature_b"),
        feature_hash="1" * 64,
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
        training_seed=4,
        created_at=created_at,
        calibration_version="cal.v1",
        dataset_hash="2" * 64,
        model_bytes_b64="eyJwcmVkaWN0aW9uIjowLjl9",
    )


def test_ml_fusion_alpha_zero_keeps_base_score() -> None:
    result = apply_ml_score_fusion(base_score=12.0, ml_confidence=0.95, alpha=0.0)

    assert result.fused_score == pytest.approx(12.0)


def test_ml_fusion_neutral_confidence_keeps_base_score() -> None:
    result = apply_ml_score_fusion(base_score=12.0, ml_confidence=0.5, alpha=0.3)

    assert result.fused_score == pytest.approx(12.0)


def test_ml_fusion_high_confidence_does_not_uplift_score() -> None:
    result = apply_ml_score_fusion(base_score=10.0, ml_confidence=0.9, alpha=0.3)

    assert result.multiplier_delta == pytest.approx(0.0)
    assert result.fused_score == pytest.approx(10.0)


def test_ml_fusion_low_confidence_penalizes_score() -> None:
    result = apply_ml_score_fusion(base_score=10.0, ml_confidence=0.1, alpha=0.3)

    assert result.multiplier_delta == pytest.approx(-0.12)
    assert result.fused_score < 10.0


def test_ml_fusion_rejects_alpha_above_cap() -> None:
    with pytest.raises(ValueError, match="alpha must be <= 0.5"):
        apply_ml_score_fusion(base_score=10.0, ml_confidence=0.9, alpha=0.51)


def test_ml_fusion_no_artifact_keeps_base_score() -> None:
    result = apply_ml_score_fusion(
        base_score=7.0,
        ml_confidence=None,
        alpha=0.3,
        artifact_ready=False,
    )

    assert result.fused_score == pytest.approx(7.0)
    assert result.applied is False


def test_ml_fusion_never_changes_engine_side() -> None:
    artifact = _artifact()
    enabler = MlConfidenceEnabler(default_alpha=0.3)

    result = enabler.apply_to_engine_score(
        base_score=9.0,
        engine_side=Side.SELL,
        artifact=artifact,
        ml_confidence=0.9,
        allow_direct_ml_confidence_override=True,
    )

    assert result.engine_side == Side.SELL
    assert result.signal.ml_direction.value == "long"
