"""Minimal guarded contracts for Build-14 enablers."""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from complete_enablers.enums import (
    Build14InfluenceAction,
    Build14HardState,
    Build14InfluenceMode,
    Build14Severity,
    Build14SignalFamily,
)
from interface_contracts import StrategyClassification


class Build14EnablerContract(BaseModel, frozen=True):
    """Canonical Build-14 enabler contract: SHADOW_ENABLED in Shadow, never autonomous."""

    correlation_id: str = Field(..., min_length=1)
    signal_family: Build14SignalFamily
    summary: str = Field(..., min_length=1)
    classification: StrategyClassification = StrategyClassification.BUILD14_ENABLER
    hard_state: Build14HardState = Build14HardState.SHADOW_ENABLED
    live_promotion_eligible: bool = False
    influence_mode: Build14InfluenceMode = Build14InfluenceMode.SHADOW_ENABLED
    max_influence_weight: float = Field(default=1.0, ge=0.0, le=1.0)
    can_override_engines: bool = False
    can_bypass_risk: bool = False
    can_bypass_portfolio: bool = False
    can_trade_autonomously: bool = False

    @model_validator(mode="after")
    def validate_guardrails(self) -> "Build14EnablerContract":
        if self.classification != StrategyClassification.BUILD14_ENABLER:
            raise ValueError("Build-14 contracts must stay classified as build14_enabler")
        if self.can_override_engines or self.can_bypass_risk or self.can_bypass_portfolio:
            raise ValueError("Build-14 must never bypass engines, risk, or portfolio")
        if self.can_trade_autonomously:
            raise ValueError("Build-14 must never become an autonomous engine")
        if self.live_promotion_eligible and self.hard_state != Build14HardState.SHADOW_VALIDATED:
            raise ValueError(
                "Build-14 live promotion eligibility requires hard_state=shadow_validated"
            )
        if self.influence_mode == Build14InfluenceMode.SHADOW_ENABLED:
            if self.hard_state == Build14HardState.DORMANT:
                raise ValueError("Dormant Build-14 contracts cannot stay shadow_enabled")
            if self.max_influence_weight != 1.0:
                raise ValueError(
                    "Shadow-enabled Build-14 contracts must keep max_influence_weight=1.0"
                )
        elif self.influence_mode == Build14InfluenceMode.READ_ONLY and self.max_influence_weight != 0.0:
            raise ValueError("Read-only Build-14 contracts must have zero influence weight")
        if self.influence_mode == Build14InfluenceMode.LIMITED_INFLUENCE and self.max_influence_weight <= 0.0:
            raise ValueError("Limited influence mode requires a positive bounded weight")
        return self


class Build14ObservationInput(BaseModel, frozen=True):
    """Observed facts collected from existing Build-9 / Build-10 surfaces."""

    correlation_id: str = Field(..., min_length=1)
    dtr_coverage: float = Field(..., ge=0.0, le=1.0)
    cra_sterilization_rate: float = Field(..., ge=0.0, le=1.0)
    cra_alert_count: int = Field(default=0, ge=0)
    break_even_drift_alert: bool = False
    edge_degraded_count: int = Field(default=0, ge=0)
    queue_backlog: int = Field(default=0, ge=0)
    stale_pair_count: int = Field(default=0, ge=0)
    dtr_loss_count: int = Field(default=0, ge=0)
    log_loss_count: int = Field(default=0, ge=0)
    ce_net: float = 0.0


class Build14EnablerSnapshot(Build14EnablerContract):
    """Traceable SHADOW_ENABLED analytical snapshot emitted by a concrete Build-14 reader."""

    reader_name: str = Field(..., min_length=1)
    observed_value: float = Field(..., ge=0.0)
    status: Build14Severity
    detail: str = Field(..., min_length=1)
    evidence_refs: tuple[str, ...] = ()
    structured_log_key: str = Field(..., min_length=1)


class Build14InfluenceSignal(BaseModel, frozen=True):
    """Governed Build-14 signal: SHADOW_ENABLED in Shadow, bounded after post-Shadow verdict."""

    correlation_id: str = Field(..., min_length=1)
    classification: StrategyClassification = StrategyClassification.BUILD14_ENABLER
    hard_state: Build14HardState = Build14HardState.SHADOW_ENABLED
    live_promotion_eligible: bool = False
    influence_mode: Build14InfluenceMode = Build14InfluenceMode.READ_ONLY
    action: Build14InfluenceAction = Build14InfluenceAction.OBSERVE
    severity: Build14Severity = Build14Severity.NOMINAL
    families: tuple[Build14SignalFamily, ...] = ()
    summary: str = Field(..., min_length=1)
    reason_codes: tuple[str, ...] = ()
    confidence_penalty_weight: float = Field(default=0.0, ge=0.0, le=0.25)
    recommended_budget_factor: float = Field(default=1.0, ge=0.0, le=1.0)
    stability_confirmed: bool = True
    non_regression_required: bool = True
    requires_manual_review: bool = False
    candidate_effect: str = Field(default="observe_only", min_length=1)
    can_override_engines: bool = False
    can_bypass_risk: bool = False
    can_bypass_portfolio: bool = False
    can_trade_autonomously: bool = False

    @model_validator(mode="after")
    def validate_signal(self) -> "Build14InfluenceSignal":
        if self.classification != StrategyClassification.BUILD14_ENABLER:
            raise ValueError("Build-14 influence must stay classified as build14_enabler")
        if self.can_override_engines or self.can_bypass_risk or self.can_bypass_portfolio:
            raise ValueError("Build-14 influence must never bypass engines, risk, or portfolio")
        if self.can_trade_autonomously:
            raise ValueError("Build-14 influence must never become an autonomous engine")
        if self.live_promotion_eligible and self.hard_state != Build14HardState.SHADOW_VALIDATED:
            raise ValueError(
                "Build-14 live promotion eligibility requires hard_state=shadow_validated"
            )
        if not self.non_regression_required:
            raise ValueError("Build-14 influence must keep non_regression_required=True")
        if self.influence_mode == Build14InfluenceMode.SHADOW_ENABLED:
            if self.hard_state == Build14HardState.DORMANT:
                raise ValueError("Dormant Build-14 signals cannot stay shadow_enabled")
            if not self.families:
                raise ValueError("Shadow-enabled Build-14 signals must reference at least one signal family")
            if self.action != Build14InfluenceAction.SHADOW_APPLY:
                raise ValueError("Shadow-enabled Build-14 signals must keep action=shadow_apply")
            if self.requires_manual_review:
                raise ValueError("Shadow-enabled Build-14 signals must stay automated inside Shadow")
            if self.candidate_effect != "shadow_enabled":
                raise ValueError("Shadow-enabled Build-14 signals must expose candidate_effect=shadow_enabled")
        elif self.influence_mode == Build14InfluenceMode.READ_ONLY:
            if self.action != Build14InfluenceAction.OBSERVE:
                raise ValueError("Read-only Build-14 influence must keep action=observe")
            if self.confidence_penalty_weight != 0.0:
                raise ValueError("Read-only Build-14 influence must have zero confidence penalty")
            if self.recommended_budget_factor != 1.0:
                raise ValueError("Read-only Build-14 influence must keep budget factor at 1.0")
            if self.requires_manual_review:
                raise ValueError("Read-only Build-14 influence must not require manual review")
        else:
            if not self.stability_confirmed:
                raise ValueError("Limited Build-14 influence requires stability_confirmed=True")
            if not self.families:
                raise ValueError("Limited Build-14 influence must reference at least one signal family")
            if self.action == Build14InfluenceAction.OBSERVE:
                raise ValueError("Limited Build-14 influence must change the candidate effect")
            if self.action == Build14InfluenceAction.DOWNGRADE_CONFIDENCE:
                if self.confidence_penalty_weight <= 0.0:
                    raise ValueError("Confidence downgrade requires a positive bounded penalty")
                if not 0.0 < self.recommended_budget_factor < 1.0:
                    raise ValueError("Confidence downgrade requires a budget factor strictly between 0 and 1")
                if self.requires_manual_review:
                    raise ValueError("Confidence downgrade must stay governed without manual review by default")
            if self.action in {
                Build14InfluenceAction.REVIEW_ONLY,
                Build14InfluenceAction.SOFT_VETO,
            }:
                if not self.requires_manual_review:
                    raise ValueError("Review-only and soft-veto Build-14 actions must require manual review")
                if self.recommended_budget_factor != 0.0:
                    raise ValueError("Review-only and soft-veto Build-14 actions must zero the budget factor")
            if self.action != Build14InfluenceAction.OBSERVE and not self.reason_codes:
                raise ValueError("Limited Build-14 influence must explain itself with reason_codes")
        return self


class Build14InfluenceReport(BaseModel, frozen=True):
    """Traceable Build-14 report: SHADOW activation evidence plus optional post-Shadow live recommendation."""

    correlation_id: str = Field(..., min_length=1)
    hard_state: Build14HardState = Build14HardState.SHADOW_ENABLED
    live_promotion_eligible: bool = False
    snapshots: tuple[Build14EnablerSnapshot, ...] = ()
    signal: Build14InfluenceSignal

    @model_validator(mode="after")
    def validate_report(self) -> "Build14InfluenceReport":
        if any(snapshot.correlation_id != self.correlation_id for snapshot in self.snapshots):
            raise ValueError("Build-14 report requires matching correlation_id across all snapshots")
        if self.signal.correlation_id != self.correlation_id:
            raise ValueError("Build-14 report requires matching correlation_id across signal and report")
        if self.signal.hard_state != self.hard_state:
            raise ValueError("Build-14 report requires matching hard_state across signal and report")
        if self.signal.live_promotion_eligible != self.live_promotion_eligible:
            raise ValueError(
                "Build-14 report requires matching live_promotion_eligible across signal and report"
            )
        return self


__all__ = [
    "Build14EnablerContract",
    "Build14ObservationInput",
    "Build14EnablerSnapshot",
    "Build14InfluenceSignal",
    "Build14InfluenceReport",
]
