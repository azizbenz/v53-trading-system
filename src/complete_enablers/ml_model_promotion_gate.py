"""Fail-closed promotion gate for bounded ML model artifacts."""

from __future__ import annotations

from pydantic import BaseModel, Field

from interface_contracts import MlModelArtifact, PromotionState


class MlModelPromotionGateVerdict(BaseModel, frozen=True):
    """Typed promotion verdict for the governed ML model layer."""

    passed: bool
    recommended_promotion_state: PromotionState
    gate_status: str = Field(..., min_length=1)
    blocking_reasons: tuple[str, ...] = ()
    oos_to_backtest_ratio: float | None = None


def evaluate_ml_model_promotion_gate(
    artifact: MlModelArtifact,
) -> MlModelPromotionGateVerdict:
    """Evaluate the bounded ML artifact with fail-closed semantics."""

    blocking_reasons: list[str] = []
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
