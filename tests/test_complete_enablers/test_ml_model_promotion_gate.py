from __future__ import annotations

import base64
from datetime import UTC, datetime

from complete_enablers import evaluate_ml_model_promotion_gate
from interface_contracts import MlModelArtifact, MlModelWindow, PromotionState


def _artifact(
    *,
    oos_sharpe: float = 1.0,
    backtest_sharpe: float = 1.2,
    ks_test_features_pvalue: float | None = 0.4,
    shadow_diff_pct: float | None = 0.02,
) -> MlModelArtifact:
    return MlModelArtifact.create(
        feature_names=("feature_a", "feature_b"),
        feature_hash="5" * 64,
        pair_universe=("BTCUSDT",),
        train_window=MlModelWindow(
            start_at=datetime(2025, 9, 24, tzinfo=UTC),
            end_at=datetime(2026, 3, 22, tzinfo=UTC),
        ),
        validation_window=MlModelWindow(
            start_at=datetime(2026, 3, 23, tzinfo=UTC),
            end_at=datetime(2026, 4, 21, tzinfo=UTC),
        ),
        oos_sharpe=oos_sharpe,
        backtest_sharpe=backtest_sharpe,
        ks_test_features_pvalue=ks_test_features_pvalue,
        shadow_diff_pct=shadow_diff_pct,
        promotion_state=PromotionState.REPLAY_ONLY,
        training_seed=9,
        created_at=datetime(2026, 4, 22, 12, 0, tzinfo=UTC),
        calibration_version="cal.v1",
        dataset_hash="6" * 64,
        model_bytes_b64=base64.b64encode(b'{"prediction":0.7}').decode("ascii"),
    )


def test_ml_model_promotion_gate_passes_when_all_rules_green() -> None:
    verdict = evaluate_ml_model_promotion_gate(_artifact())

    assert verdict.passed is True
    assert verdict.recommended_promotion_state == PromotionState.SHADOW_CANDIDATE


def test_ml_model_promotion_gate_fails_closed_on_missing_metrics() -> None:
    verdict = evaluate_ml_model_promotion_gate(
        _artifact(ks_test_features_pvalue=None, shadow_diff_pct=None)
    )

    assert verdict.passed is False
    assert "KS_TEST_FEATURES_PVALUE_REQUIRED" in verdict.blocking_reasons
    assert "SHADOW_DIFF_PCT_REQUIRED" in verdict.blocking_reasons


def test_ml_model_promotion_gate_fails_on_oos_sharpe_ratio() -> None:
    verdict = evaluate_ml_model_promotion_gate(_artifact(oos_sharpe=0.7, backtest_sharpe=1.0))

    assert verdict.passed is False
    assert "OOS_SHARPE_BELOW_80PCT_OF_BACKTEST" in verdict.blocking_reasons


def test_ml_model_promotion_gate_fails_on_ks_floor() -> None:
    verdict = evaluate_ml_model_promotion_gate(_artifact(ks_test_features_pvalue=0.05))

    assert verdict.passed is False
    assert "KS_TEST_FEATURES_PVALUE_TOO_LOW" in verdict.blocking_reasons


def test_ml_model_promotion_gate_fails_on_shadow_diff_cap() -> None:
    verdict = evaluate_ml_model_promotion_gate(_artifact(shadow_diff_pct=0.1))

    assert verdict.passed is False
    assert "SHADOW_DIFF_PCT_TOO_HIGH" in verdict.blocking_reasons
