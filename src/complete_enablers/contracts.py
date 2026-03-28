"""Minimal guarded contracts for Build-14 enablers."""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from complete_enablers.enums import Build14InfluenceMode, Build14SignalFamily
from interface_contracts import StrategyClassification


class Build14EnablerContract(BaseModel, frozen=True):
    """Read-only first, limited influence later, never autonomous."""

    correlation_id: str = Field(..., min_length=1)
    signal_family: Build14SignalFamily
    summary: str = Field(..., min_length=1)
    classification: StrategyClassification = StrategyClassification.BUILD14_ENABLER
    influence_mode: Build14InfluenceMode = Build14InfluenceMode.READ_ONLY
    max_influence_weight: float = Field(default=0.0, ge=0.0, le=0.25)
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
        if self.influence_mode == Build14InfluenceMode.READ_ONLY and self.max_influence_weight != 0.0:
            raise ValueError("Read-only Build-14 contracts must have zero influence weight")
        if self.influence_mode == Build14InfluenceMode.LIMITED_INFLUENCE and self.max_influence_weight <= 0.0:
            raise ValueError("Limited influence mode requires a positive bounded weight")
        return self


class Build14ObservationInput(BaseModel, frozen=True):
    """Read-only facts collected from existing Build-9 / Build-10 surfaces."""

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
    """Traceable read-only analytical snapshot emitted by a concrete Build-14 reader."""

    reader_name: str = Field(..., min_length=1)
    observed_value: float = Field(..., ge=0.0)
    status: str = Field(..., min_length=1)
    detail: str = Field(..., min_length=1)
    evidence_refs: tuple[str, ...] = ()
    structured_log_key: str = Field(..., min_length=1)


__all__ = [
    "Build14EnablerContract",
    "Build14ObservationInput",
    "Build14EnablerSnapshot",
]
