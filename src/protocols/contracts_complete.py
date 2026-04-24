"""Governed Build-17 Complete control-surface contracts."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from interface_contracts import (
    DashboardArtifactTransferManifest,
    DashboardCommandQueueSnapshot,
    DeploymentState,
    OperatorSafingRequest,
    ProfileId,
    ReviewState,
    RuntimeMode,
    VpsRecoveryReadinessReport,
    VpsWarmupRunSummary,
)

from .contracts_promotion import LiveLightRunSummary
from .enums import LiveCompleteRunState, LiveCompleteVerdict, LiveLightRunState, LiveLightVerdict


class LiveCompleteGateGroupSummary(BaseModel, frozen=True):
    """Audit-friendly status projection for the canonical Build-17 gate groups."""

    gate_id: Literal[
        "governed_live_complete",
        "command_plane",
        "artifact_state",
        "recovery_warmup",
        "operator_surface",
    ]
    status: Literal["passed", "blocked", "review_only"] = "passed"
    reasons: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_status(self) -> "LiveCompleteGateGroupSummary":
        if self.status == "passed" and self.reasons:
            raise ValueError("Passed LiveComplete gate groups must not carry reasons")
        if self.status != "passed" and not self.reasons:
            raise ValueError(
                "Blocked or review_only LiveComplete gate groups must carry reasons"
            )
        return self


class LiveCompleteInput(BaseModel, frozen=True):
    """Single governed input entering the Build-17 Complete control gate."""

    correlation_id: str = Field(..., min_length=1)
    profile: ProfileId = ProfileId.COMPLETE
    runtime_mode: RuntimeMode = RuntimeMode.LIVE
    deployment_state: DeploymentState = DeploymentState.LIVE_COMPLETE
    live_light_run_id: str = Field(..., min_length=1)
    micro_live_run_id: str = ""
    shadow_run_id: str = ""
    live_light_verdict: LiveLightVerdict
    live_light_run_state: LiveLightRunState
    live_light_blocking_reasons: tuple[str, ...] = ()
    import_artifact_id: str = Field(..., min_length=1)
    import_lineage_version: str = Field(..., min_length=1)
    observability_ready: bool = False
    halt_ready: bool = False
    execution_ready: bool = False
    broker_ready: bool = False
    exchange_ready: bool = False
    complete_gates: tuple[str, ...] = ()
    selected_pairs: tuple[str, ...] = ()
    available_pairs: tuple[str, ...] = ()
    allowed_actions: tuple[str, ...] = ()
    forbidden_actions: tuple[str, ...] = ()
    command_queue_snapshot: DashboardCommandQueueSnapshot | None = None
    active_ml_artifact: DashboardArtifactTransferManifest | None = None
    active_regime_detector_artifact: DashboardArtifactTransferManifest | None = None
    recovery_readiness_report: VpsRecoveryReadinessReport | None = None
    warmup_run_summary: VpsWarmupRunSummary | None = None
    operator_safing_request: OperatorSafingRequest | None = None

    @model_validator(mode="after")
    def validate_governance(self) -> "LiveCompleteInput":
        if self.profile != ProfileId.COMPLETE:
            raise ValueError("Build-17 Complete requires profile=COMPLETE")
        if self.runtime_mode != RuntimeMode.LIVE:
            raise ValueError("Build-17 Complete requires runtime_mode=LIVE")
        if self.deployment_state != DeploymentState.LIVE_COMPLETE:
            raise ValueError("Build-17 Complete requires deployment_state=LIVE_COMPLETE")
        if len(set(self.allowed_actions)) != len(self.allowed_actions):
            raise ValueError("LiveCompleteInput allowed_actions must be unique")
        if len(set(self.forbidden_actions)) != len(self.forbidden_actions):
            raise ValueError("LiveCompleteInput forbidden_actions must be unique")
        if self.available_pairs and not set(self.selected_pairs).issubset(
            set(self.available_pairs)
        ):
            raise ValueError("selected_pairs must stay within available_pairs")
        if (
            self.operator_safing_request is not None
            and self.operator_safing_request.source_runtime_mode != RuntimeMode.LIVE
        ):
            raise ValueError(
                "Build-17 Complete operator_safing_request requires source_runtime_mode=LIVE"
            )
        return self


class LiveCompleteDecision(BaseModel, frozen=True):
    """Governed Build-17 verdict for the Complete control surface."""

    allowed_complete_supervision: bool
    verdict: LiveCompleteVerdict
    review_state: ReviewState
    blocking_reasons: tuple[str, ...] = ()
    manual_review_required: bool = True

    @model_validator(mode="after")
    def validate_decision(self) -> "LiveCompleteDecision":
        if (
            self.allowed_complete_supervision
            and self.verdict != LiveCompleteVerdict.ALLOWED_COMPLETE_SUPERVISION
        ):
            raise ValueError(
                "allowed_complete_supervision=True requires verdict=ALLOWED_COMPLETE_SUPERVISION"
            )
        if (
            not self.allowed_complete_supervision
            and self.verdict == LiveCompleteVerdict.ALLOWED_COMPLETE_SUPERVISION
        ):
            raise ValueError(
                "verdict=ALLOWED_COMPLETE_SUPERVISION requires allowed_complete_supervision=True"
            )
        return self


class LiveCompleteExecutionEnvelope(BaseModel, frozen=True):
    """Minimal Build-17 control envelope carried after the Complete gate passes."""

    envelope_id: str = Field(..., min_length=1)
    import_artifact_id: str = Field(..., min_length=1)
    import_lineage_version: str = Field(..., min_length=1)
    deployment_state: DeploymentState = DeploymentState.LIVE_COMPLETE
    selected_pairs: tuple[str, ...] = ()
    allowed_actions: tuple[str, ...] = ()
    forbidden_actions: tuple[str, ...] = ()
    command_queue_enabled: bool = False
    active_ml_artifact_hash: str = ""
    active_regime_detector_artifact_hash: str = ""
    recovery_state: str = "cold_start"
    halt_guard_required: bool = True
    autonomous_execution_enabled: bool = False


class LiveCompleteRunSummary(BaseModel, frozen=True):
    """Deterministic output of the Build-17 Complete control gate."""

    run_id: str = Field(..., min_length=1)
    correlation_id: str = Field(..., min_length=1)
    run_state: LiveCompleteRunState
    deployment_state: DeploymentState = DeploymentState.LIVE_COMPLETE
    live_light_run_id: str = Field(..., min_length=1)
    micro_live_run_id: str = ""
    shadow_run_id: str = ""
    live_light_verdict: LiveLightVerdict
    decision: LiveCompleteDecision
    execution_envelope: LiveCompleteExecutionEnvelope
    import_artifact_id: str = Field(..., min_length=1)
    import_lineage_version: str = Field(..., min_length=1)
    command_queue_snapshot: DashboardCommandQueueSnapshot | None = None
    active_ml_artifact: DashboardArtifactTransferManifest | None = None
    active_regime_detector_artifact: DashboardArtifactTransferManifest | None = None
    recovery_readiness_report: VpsRecoveryReadinessReport | None = None
    warmup_run_summary: VpsWarmupRunSummary | None = None
    gate_groups: tuple[LiveCompleteGateGroupSummary, ...] = ()

    @property
    def blocking_reason_count(self) -> int:
        return len(self.decision.blocking_reasons)

    @property
    def selected_pair_count(self) -> int:
        return len(self.execution_envelope.selected_pairs)


LiveInput = LiveCompleteInput
LiveDecision = LiveCompleteDecision
LiveExecutionIntent = LiveCompleteExecutionEnvelope
LiveRunSummary = LiveCompleteRunSummary


def build_live_complete_input_defaults(
    live_light_summary: LiveLightRunSummary,
) -> dict[str, object]:
    """Resolve shared Build-17 fields from the Build-13 Live-Light summary."""

    return {
        "correlation_id": live_light_summary.correlation_id,
        "live_light_run_id": live_light_summary.run_id,
        "micro_live_run_id": live_light_summary.micro_live_run_id,
        "shadow_run_id": live_light_summary.shadow_run_id,
        "live_light_verdict": live_light_summary.decision.verdict,
        "live_light_run_state": live_light_summary.run_state,
        "live_light_blocking_reasons": live_light_summary.decision.blocking_reasons,
        "import_artifact_id": live_light_summary.import_artifact_id,
        "import_lineage_version": live_light_summary.import_lineage_version,
        "observability_ready": live_light_summary.observability_ready,
        "halt_ready": live_light_summary.halt_ready,
        "execution_ready": live_light_summary.execution_ready,
        "broker_ready": live_light_summary.broker_ready,
        "exchange_ready": live_light_summary.exchange_ready,
        "operator_safing_request": live_light_summary.operator_safing_request,
    }


__all__ = [
    "LiveInput",
    "LiveDecision",
    "LiveExecutionIntent",
    "LiveRunSummary",
    "LiveCompleteGateGroupSummary",
    "LiveCompleteInput",
    "LiveCompleteDecision",
    "LiveCompleteExecutionEnvelope",
    "LiveCompleteRunSummary",
    "build_live_complete_input_defaults",
]
