"""Bounded Build-5 scoring hook backed by governed non-positive ML modulation."""

from __future__ import annotations

from pydantic import BaseModel, Field

from complete_enablers.ml_confidence_enabler import MlArtifactStatus, MlConfidenceEnabler
from complete_enablers.ml_fusion import confidence_to_multiplier_delta, validate_alpha
from scoring_backbone import ScoringSoftPenaltyLayerInput, ScoringSoftPenaltyLayerOutcome


class MlScoringSoftPenaltyHookConfig(BaseModel, frozen=True):
    """Bounded configuration for the additive ML scoring hook."""

    alpha: float = Field(default=0.2, ge=0.0, le=0.5)


class MlScoringSoftPenaltyHook:
    """Apply bounded non-positive ML score modulation on the canonical Build-5 hook rail."""

    def __init__(
        self,
        *,
        enabler: MlConfidenceEnabler | None = None,
        config: MlScoringSoftPenaltyHookConfig | None = None,
    ) -> None:
        self._enabler = enabler or MlConfidenceEnabler()
        self._config = config or MlScoringSoftPenaltyHookConfig()

    def __call__(
        self,
        hook_input: ScoringSoftPenaltyLayerInput,
    ) -> ScoringSoftPenaltyLayerOutcome:
        signal = self._enabler.score_candidate_from_supplementary_refs(
            feature_values=hook_input.feature_values,
            supplementary_refs=hook_input.supplementary_refs,
        )
        if signal.artifact_status != MlArtifactStatus.ACTIVE:
            return ScoringSoftPenaltyLayerOutcome(
                reason_codes=signal.reason_codes,
                detail=(
                    "ml scoring modulation skipped for "
                    f"{hook_input.pair}/{hook_input.engine_id}: {signal.artifact_status.value}"
                ),
            )
        multiplier_delta = confidence_to_multiplier_delta(
            ml_confidence=signal.ml_confidence,
            alpha=validate_alpha(self._config.alpha),
        )
        return ScoringSoftPenaltyLayerOutcome(
            raw_score_multiplier_delta=multiplier_delta,
            reason_codes=(*signal.reason_codes, "ML_SCORE_MODULATION_ACTIVE"),
            detail=(
                "ml non-positive scoring modulation applied for "
                f"{hook_input.pair}/{hook_input.engine_id}"
            ),
        )


__all__ = [
    "MlScoringSoftPenaltyHookConfig",
    "MlScoringSoftPenaltyHook",
]
