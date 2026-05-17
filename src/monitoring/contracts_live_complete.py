"""Build-17 Complete monitoring projection contracts."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from .contracts_artifacts import (
    ArtifactComparisonProjection,
    ArtifactRuntimeVisibilityProjection,
    ArtifactThresholdConsumerProjection,
    ArtifactVerdictBundleProjection,
)
from .contracts_core import ProjectionStatus


class LiveCompleteGateGroupProjection(BaseModel, frozen=True):
    """Normalized gate-group projection for the Build-17 Complete control surface."""

    gate_id: Literal[
        "governed_live_complete",
        "command_plane",
        "artifact_state",
        "recovery_warmup",
        "operator_surface",
    ]
    status: Literal["passed", "blocked", "review_only"] = "passed"
    reasons: tuple[str, ...] = ()


class LiveCompleteProjection(BaseModel, frozen=True):
    """Normalized Build-17 Complete supervision summary for dashboard/operator use."""

    status: ProjectionStatus = "planned"
    run_state: str = "not_run"
    verdict: str = "not_run"
    deployment_state: str = "live_complete"
    live_light_run_id: str = ""
    micro_live_run_id: str = ""
    shadow_run_id: str = ""
    import_artifact_id: str = "none"
    import_lineage_version: str = "n/a"
    selected_pairs: tuple[str, ...] = ()
    allowed_actions: tuple[str, ...] = ()
    forbidden_actions: tuple[str, ...] = ()
    active_ml_artifact_id: str = ""
    active_ml_artifact_hash: str = ""
    active_regime_detector_artifact_id: str = ""
    active_regime_detector_artifact_hash: str = ""
    shadow_ml_challenger_artifact_id: str = ""
    shadow_ml_challenger_artifact_hash: str = ""
    shadow_regime_detector_challenger_artifact_id: str = ""
    shadow_regime_detector_challenger_artifact_hash: str = ""
    artifact_runtime_visibility: tuple[ArtifactRuntimeVisibilityProjection, ...] = ()
    artifact_threshold_consumers: tuple[ArtifactThresholdConsumerProjection, ...] = ()
    artifact_comparisons: tuple[ArtifactComparisonProjection, ...] = ()
    artifact_verdict_bundle: ArtifactVerdictBundleProjection | None = None
    command_queue_status: str = "not_configured"
    command_queue_pending_request_count: int = Field(default=0, ge=0)
    command_queue_ambiguous_pending_count: int = Field(default=0, ge=0)
    recovery_state: str = "cold_start"
    recovery_eligible_to_trade: bool = False
    warmup_final_state: str = "cold_start"
    warmup_eligible_to_trade: bool = False
    blocking_reasons: tuple[str, ...] = ()
    gate_groups: tuple[LiveCompleteGateGroupProjection, ...] = ()


__all__ = [
    "LiveCompleteGateGroupProjection",
    "LiveCompleteProjection",
]
