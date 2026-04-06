"""Canonical manifest for LOCAL_REPLAY artifacts."""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from interface_contracts import (
    ActionUnit,
    ArtifactActivationStage,
    ArtifactActionKind,
    ArtifactSignatureEnvelope,
    ArtifactHealthState,
    ArtifactLogicFormat,
    CANONICAL_FEATURE_SET_VERSION,
    CANONICAL_TRANSFORM_SET_VERSION,
    HookId,
    ProfileId,
    RuntimeMode,
    StrategyClassification,
)


SHARED_CORE_ID = "v5_3_shared_core"


class ArtifactManifest(BaseModel, frozen=True):
    """Minimal manifest carried by replay bundles and imports."""

    artifact_id: str = Field(..., min_length=1)
    correlation_id: str = Field(..., min_length=1)
    source_profile: ProfileId
    runtime_mode: RuntimeMode = RuntimeMode.LOCAL_REPLAY
    strategy_classification: StrategyClassification
    strategy_version: str = Field(..., min_length=1)
    lineage_version: str = Field(..., min_length=1)
    artifact_schema_version: str = Field(default="1.0.0", min_length=1)
    feature_set_version: str = Field(default=CANONICAL_FEATURE_SET_VERSION, min_length=1)
    transform_set_version: str = Field(default=CANONICAL_TRANSFORM_SET_VERSION, min_length=1)
    shared_core_id: str = Field(default=SHARED_CORE_ID, min_length=1)
    exported_from: str = Field(default="local", min_length=1)
    activation_stage: ArtifactActivationStage = ArtifactActivationStage.REPLAY_ONLY
    health_state: ArtifactHealthState = ArtifactHealthState.ACTIVE
    distilled_logic_format: ArtifactLogicFormat = ArtifactLogicFormat.RULE_AST_JSON
    allowed_hook_ids: tuple[HookId, ...] = ()
    allowed_action_kinds: tuple[ArtifactActionKind, ...] = ()
    allowed_action_units: tuple[ActionUnit, ...] = ()
    signature_envelope: ArtifactSignatureEnvelope | None = None
    dataset_ref: str = ""
    clock_ref: str = ""
    feature_bridge_ref: str = ""
    parity_diagnostics_ref: str = ""
    replay_metrics_ref: str = ""
    replay_dtr_ref: str = ""
    diagnostic_ids: tuple[str, ...] = ()
    hypothesis_ids: tuple[str, ...] = ()
    candidate_ids: tuple[str, ...] = ()
    target_components: tuple[str, ...] = ()
    expected_shadow_evidence: tuple[str, ...] = ()
    review_export_ref: str = ""
    backtest_profile: str | None = None
    creates_profile_fork: bool = False
    implicit_promotion_requested: bool = False

    @model_validator(mode="after")
    def validate_unified_plan(self) -> "ArtifactManifest":
        if self.runtime_mode != RuntimeMode.LOCAL_REPLAY:
            raise ValueError("Artifacts must originate from runtime_mode=LOCAL_REPLAY")
        if self.shared_core_id != SHARED_CORE_ID:
            raise ValueError("Artifacts must reference the shared V5.3 core")
        if self.backtest_profile is not None:
            raise ValueError("BACKTEST_PROFILE is forbidden in the unified V5.3")
        if self.creates_profile_fork:
            raise ValueError("Local/VPS profile forks are forbidden")
        if self.implicit_promotion_requested:
            raise ValueError("Artifacts must not request implicit promotion")
        if not self.lineage_version.startswith(self.strategy_version):
            raise ValueError("lineage_version must extend strategy_version")
        if bool(self.dataset_ref) != bool(self.clock_ref):
            raise ValueError("Artifact manifests must declare dataset and clock refs together")
        if len(set(self.diagnostic_ids)) != len(self.diagnostic_ids):
            raise ValueError("Artifact diagnostic refs must be unique")
        if len(set(self.hypothesis_ids)) != len(self.hypothesis_ids):
            raise ValueError("Artifact hypothesis refs must be unique")
        if len(set(self.candidate_ids)) != len(self.candidate_ids):
            raise ValueError("Artifact candidate refs must be unique")
        if len(set(self.target_components)) != len(self.target_components):
            raise ValueError("Artifact target components must be unique")
        if len(set(self.allowed_hook_ids)) != len(self.allowed_hook_ids):
            raise ValueError("Artifact hook ids must be unique")
        if len(set(self.allowed_action_kinds)) != len(self.allowed_action_kinds):
            raise ValueError("Artifact action kinds must be unique")
        if len(set(self.allowed_action_units)) != len(self.allowed_action_units):
            raise ValueError("Artifact action units must be unique")
        return self


__all__ = [
    "ArtifactManifest",
    "SHARED_CORE_ID",
]
