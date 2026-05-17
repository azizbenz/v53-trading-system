from __future__ import annotations

import base64
from datetime import UTC, datetime

from complete_enablers import evaluate_ml_model_promotion_gate
from interface_contracts import (
    MlAntiLeakageProofArtifact,
    MlLiveDriftSnapshot,
    MlModelArtifact,
    MlModelWindow,
    PromotionState,
)


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


def _anti_leakage_proof(artifact: MlModelArtifact) -> MlAntiLeakageProofArtifact:
    return MlAntiLeakageProofArtifact.create(
        artifact_id="anti-leakage-proof-1",
        target_artifact_hash=artifact.artifact_hash,
        dataset_hash=artifact.dataset_hash,
        feature_hash=artifact.feature_hash,
        label_policy="ml_backtest_realized_target_policy.v1",
        train_window=artifact.train_window,
        validation_window=artifact.validation_window,
        test_window=MlModelWindow(
            start_at=datetime(2026, 4, 22, tzinfo=UTC),
            end_at=datetime(2026, 4, 29, tzinfo=UTC),
        ),
        purge_size=48,
        embargo_size=24,
        label_horizon="30m",
        max_feature_timestamp=datetime(2026, 4, 21, 23, 30, tzinfo=UTC),
        min_label_timestamp=datetime(2026, 4, 21, 23, 30, tzinfo=UTC),
        feature_timestamp_alignment_status="FEATURE_TIMESTAMP_ALIGNED",
        no_future_data_leak_status="NO_FUTURE_DATA_LEAK_PROVEN",
        reviewer_signature="quant-reviewer",
        method_version_hash="anti_leakage.v1",
        created_at=datetime(2026, 4, 22, 12, 0, tzinfo=UTC),
    )


def _live_drift_snapshot(artifact: MlModelArtifact) -> MlLiveDriftSnapshot:
    return MlLiveDriftSnapshot.create(
        artifact_id="live-drift-1",
        target_artifact_hash=artifact.artifact_hash,
        feature_hash=artifact.feature_hash,
        stage="LIVE",
        feature_ks_pvalue=0.42,
        shadow_diff_pct=0.02,
        live_diff_pct=0.03,
        win_rate_delta=-0.01,
        ce_delta=-0.002,
        source_status="LIVE_DRIFT_SOURCE_GOVERNED",
        input_data_hash="c" * 64,
        method_version_hash="live_drift.v1",
        created_at=datetime(2026, 4, 22, 12, 0, tzinfo=UTC),
        expires_at=datetime(2026, 4, 29, 12, 0, tzinfo=UTC),
    )


def test_ml_model_promotion_gate_blocks_on_unresolved_formalism_even_when_metrics_are_green() -> None:
    verdict = evaluate_ml_model_promotion_gate(_artifact())

    assert verdict.passed is False
    assert verdict.recommended_promotion_state == PromotionState.REPLAY_ONLY
    assert "ml.formalism.unresolved" in verdict.blocking_reasons
    assert "ML_ANTI_LEAKAGE_PROOF_MISSING" in verdict.blocking_reasons
    assert "ML_LIVE_DRIFT_SNAPSHOT_MISSING" in verdict.blocking_reasons


def test_ml_model_promotion_gate_accepts_proof_contracts_but_keeps_formalism_blocker() -> None:
    artifact = _artifact()

    verdict = evaluate_ml_model_promotion_gate(
        artifact,
        anti_leakage_proof=_anti_leakage_proof(artifact),
        live_drift_snapshot=_live_drift_snapshot(artifact),
    )

    assert verdict.passed is False
    assert "ml.formalism.unresolved" in verdict.blocking_reasons
    assert "ML_ANTI_LEAKAGE_PROOF_MISSING" not in verdict.blocking_reasons
    assert "ML_LIVE_DRIFT_SNAPSHOT_MISSING" not in verdict.blocking_reasons


def test_ml_model_promotion_gate_fails_closed_on_missing_metrics() -> None:
    verdict = evaluate_ml_model_promotion_gate(
        _artifact(ks_test_features_pvalue=None, shadow_diff_pct=None)
    )

    assert verdict.passed is False
    assert "ml.formalism.unresolved" in verdict.blocking_reasons
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
