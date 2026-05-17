"""Fail-closed promotion gate for bounded ML model artifacts."""

from __future__ import annotations

from pydantic import BaseModel, Field

from interface_contracts import (
    MlAntiLeakageProofArtifact,
    MlLiveDriftSnapshot,
    MlModelArtifact,
    PromotionState,
)


class MlModelPromotionGateVerdict(BaseModel, frozen=True):
    """Typed promotion verdict for the governed ML model layer."""

    passed: bool
    recommended_promotion_state: PromotionState
    gate_status: str = Field(..., min_length=1)
    blocking_reasons: tuple[str, ...] = ()
    oos_to_backtest_ratio: float | None = None


def evaluate_ml_model_promotion_gate(
    artifact: MlModelArtifact,
    *,
    anti_leakage_proof: MlAntiLeakageProofArtifact | None = None,
    live_drift_snapshot: MlLiveDriftSnapshot | None = None,
) -> MlModelPromotionGateVerdict:
    """Evaluate the bounded ML artifact with fail-closed semantics."""

    blocking_reasons: list[str] = ["ml.formalism.unresolved"]
    if anti_leakage_proof is None:
        blocking_reasons.append("ML_ANTI_LEAKAGE_PROOF_MISSING")
    else:
        if anti_leakage_proof.target_artifact_hash != artifact.artifact_hash:
            blocking_reasons.append("ML_ANTI_LEAKAGE_TARGET_HASH_MISMATCH")
        if anti_leakage_proof.dataset_hash != artifact.dataset_hash:
            blocking_reasons.append("ML_ANTI_LEAKAGE_DATASET_HASH_MISMATCH")
        if anti_leakage_proof.feature_hash != artifact.feature_hash:
            blocking_reasons.append("ML_ANTI_LEAKAGE_FEATURE_HASH_MISMATCH")
        if not anti_leakage_proof.promotion_ready_proof:
            blocking_reasons.append("ML_ANTI_LEAKAGE_PROOF_NOT_READY")
    if live_drift_snapshot is None:
        blocking_reasons.append("ML_LIVE_DRIFT_SNAPSHOT_MISSING")
    else:
        if live_drift_snapshot.target_artifact_hash != artifact.artifact_hash:
            blocking_reasons.append("ML_LIVE_DRIFT_TARGET_HASH_MISMATCH")
        if live_drift_snapshot.feature_hash != artifact.feature_hash:
            blocking_reasons.append("ML_LIVE_DRIFT_FEATURE_HASH_MISMATCH")
        if not live_drift_snapshot.promotion_ready_snapshot:
            blocking_reasons.append("ML_LIVE_DRIFT_SOURCE_NOT_READY")
    if artifact.model_family.value != "lightgbm":
        blocking_reasons.append("MODEL_FAMILY_NOT_LIGHTGBM")
    if artifact.backtest_sharpe <= 0.0:
        blocking_reasons.append("BACKTEST_SHARPE_REQUIRED_POSITIVE")
    if artifact.ks_test_features_pvalue is None:
        blocking_reasons.append("KS_TEST_FEATURES_PVALUE_REQUIRED")
    elif artifact.ks_test_features_pvalue <= 0.05:
        blocking_reasons.append("KS_TEST_FEATURES_PVALUE_TOO_LOW")
    if artifact.shadow_diff_pct is None:
        blocking_reasons.append("SHADOW_DIFF_PCT_REQUIRED")
    elif artifact.shadow_diff_pct >= 0.1:
        blocking_reasons.append("SHADOW_DIFF_PCT_TOO_HIGH")
    ratio = None
    if artifact.backtest_sharpe > 0.0:
        ratio = artifact.oos_sharpe / artifact.backtest_sharpe
        if ratio < 0.80:
            blocking_reasons.append("OOS_SHARPE_BELOW_80PCT_OF_BACKTEST")
    if artifact.artifact_hash != artifact.artifact_hash_sha256():
        blocking_reasons.append("ARTIFACT_HASH_INVALID")

    passed = not blocking_reasons
    return MlModelPromotionGateVerdict(
        passed=passed,
        recommended_promotion_state=(
            PromotionState.SHADOW_CANDIDATE if passed else PromotionState.REPLAY_ONLY
        ),
        gate_status="passed" if passed else "blocked",
        blocking_reasons=tuple(dict.fromkeys(blocking_reasons)),
        oos_to_backtest_ratio=ratio,
    )


__all__ = [
    "MlModelPromotionGateVerdict",
    "evaluate_ml_model_promotion_gate",
]
