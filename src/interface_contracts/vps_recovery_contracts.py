"""Typed recovery and warm-up proof contracts for governed VPS startup."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, model_validator

from .dashboard_command_contracts import (
    DashboardArtifactTransferManifest,
    DashboardCommandQueueSnapshot,
)
from .domain_types import DeploymentState, RuntimeMode
from .shadow_vps_service_contracts import ShadowVpsExecutionRuntimeBootstrapSummary


class VpsRecoveryCheckStatus(StrEnum):
    """Outcome vocabulary for one pre-trading recovery verification group."""

    PASSED = "passed"
    BLOCKED = "blocked"
    REVIEW_ONLY = "review_only"


class VpsWarmupState(StrEnum):
    """State machine vocabulary for VPS recovery and warm-up."""

    COLD_START = "cold_start"
    RECOVERY_RESTORE = "recovery_restore"
    BOOTSTRAP_RECONCILIATION = "bootstrap_reconciliation"
    PREFLIGHT_VALIDATION = "preflight_validation"
    WARMUP_SHADOW_ONLY = "warmup_shadow_only"
    ELIGIBLE_TO_TRADE = "eligible_to_trade"
    BLOCKED = "blocked"


class VpsRecoveryCheck(BaseModel, frozen=True):
    """One bounded recovery or warm-up verification check."""

    check_id: str = Field(..., min_length=1)
    status: VpsRecoveryCheckStatus
    reasons: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_status(self) -> "VpsRecoveryCheck":
        if self.status == VpsRecoveryCheckStatus.PASSED and self.reasons:
            raise ValueError("Passed VpsRecoveryCheck must not carry reasons")
        if self.status != VpsRecoveryCheckStatus.PASSED and not self.reasons:
            raise ValueError("Blocked or review_only VpsRecoveryCheck must carry reasons")
        return self


class VpsRecoveryReadinessReport(BaseModel, frozen=True):
    """Typed go/no-go report evaluated before any post-crash trading resumes."""

    report_id: str = Field(..., min_length=1)
    runtime_mode: RuntimeMode = RuntimeMode.LIVE
    deployment_state: DeploymentState = DeploymentState.LIVE_COMPLETE
    active_artifact: DashboardArtifactTransferManifest | None = None
    command_queue_snapshot: DashboardCommandQueueSnapshot | None = None
    bootstrap_summary: ShadowVpsExecutionRuntimeBootstrapSummary | None = None
    websocket_ready: bool = False
    regime_lite_ready: bool = False
    info_stress_ready: bool = False
    pending_ambiguous_command_count: int = Field(default=0, ge=0)
    checks: tuple[VpsRecoveryCheck, ...] = ()
    eligible_to_trade: bool = False
    blocking_reasons: tuple[str, ...] = ()
    caution_flags: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_consistency(self) -> "VpsRecoveryReadinessReport":
        has_blocker = any(
            check.status == VpsRecoveryCheckStatus.BLOCKED for check in self.checks
        )
        if self.eligible_to_trade and has_blocker:
            raise ValueError(
                "eligible_to_trade=True is invalid when a blocked recovery check exists"
            )
        return self


class VpsWarmupRunSummary(BaseModel, frozen=True):
    """Deterministic VPS warm-up run emitted before trading resumes."""

    run_id: str = Field(..., min_length=1)
    runtime_mode: RuntimeMode = RuntimeMode.LIVE
    final_state: VpsWarmupState = VpsWarmupState.COLD_START
    phase_sequence: tuple[VpsWarmupState, ...] = ()
    report: VpsRecoveryReadinessReport
    eligible_to_trade: bool = False
    blocking_reasons: tuple[str, ...] = ()
    caution_flags: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_warmup(self) -> "VpsWarmupRunSummary":
        if self.eligible_to_trade and self.final_state != VpsWarmupState.ELIGIBLE_TO_TRADE:
            raise ValueError(
                "eligible_to_trade=True requires final_state=eligible_to_trade"
            )
        return self


__all__ = [
    "VpsRecoveryCheckStatus",
    "VpsWarmupState",
    "VpsRecoveryCheck",
    "VpsRecoveryReadinessReport",
    "VpsWarmupRunSummary",
]
