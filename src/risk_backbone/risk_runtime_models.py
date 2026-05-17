"""Public models and hook contracts for the Build-4 risk runtime."""

from __future__ import annotations

from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel, Field

from .btc_factor_guard.beta_cap_guard import BetaCapResult
from .btc_factor_guard.projected_beta_checker import ProjectedBeta
from .correlation_cluster_guard.cluster_cap_guard import ClusterCapResult
from .exposure_budgeter.gross_cap_guard import GrossCapResult
from .exposure_budgeter.gross_exposure_calculator import Position
from .loss_budgeter.drawdown_guard import DrawdownGuardResult, DrawdownVerdict
from .loss_budgeter.loss_cap_guard import LossCapResult


class RiskRuntimeAction(StrEnum):
    ACCEPT = "accept"
    REJECT = "reject"
    REDUCE_EXPOSURE = "reduce_exposure"
    OBSERVE_ONLY = "observe_only"


class RiskLimits(BaseModel, frozen=True):
    gross_cap: float
    position_cap: float
    loss_cap: float
    beta_cap: float
    cluster_cap: float
    beta_mapping_max_age_s: float = 86_400.0
    drawdown_warning_threshold_pct: float = 0.02
    drawdown_observe_threshold_pct: float = 0.04


class RiskCandidate(BaseModel, frozen=True):
    pair: str
    engine_id: str
    size: float
    planned_loss: float | None
    pair_beta: float | None = None
    side: str = "buy"
    carriage_statuses: tuple[str, ...] = ()
    carriage_reason_codes: tuple[str, ...] = ()
    shared_physics_mapping_status: str = "NOT_PROVEN"
    engine_role: str = ""
    execution_fragility: float = 0.0
    execution_fragility_status: str = "UNKNOWN"
    market_toxicity: float = 0.0
    market_toxicity_status: str = "UNKNOWN"
    spread_regime_penalty: float = 0.0
    spread_regime_penalty_status: str = "UNKNOWN"
    participation_penalty: float = 0.0
    participation_penalty_status: str = "NOT_PROVEN"
    micro_friction_source_status: str = "UNKNOWN"
    risk_input_completeness_status: str = "UNKNOWN"
    cost_model_completeness_status: str = "UNKNOWN"
    fee_source_status: str = "UNKNOWN"
    impact_source_status: str = "UNKNOWN"
    fill_realism_status: str = "UNKNOWN"
    realized_slippage_status: str = "UNKNOWN"
    spread_bps: float | None = Field(default=None, ge=0.0)
    reference_spread_bps: float | None = Field(default=None, gt=0.0)
    depth_ratio: float | None = Field(default=None, ge=0.0, le=1.0)
    order_cancellation_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    taker_imbalance: float | None = Field(default=None, ge=-1.0, le=1.0)
    micro_vol_divergence: float | None = Field(default=None, ge=0.0)


class RiskReasonDetail(BaseModel, frozen=True):
    """Stable, audit-ready reason emitted by the Build-4 risk runtime."""

    code: str
    category: str
    verdict: str
    message: str


class RiskExplainability(BaseModel, frozen=True):
    """Structured Build-4 explainability summary for downstream monitoring/UI."""

    blocked_guard_codes: tuple[str, ...] = ()
    blocked_guard_categories: tuple[str, ...] = ()
    blocked_guard_count: int = 0
    carriage_statuses: tuple[str, ...] = ()
    carriage_reason_codes: tuple[str, ...] = ()
    shared_physics_mapping_status: str = "NOT_PROVEN"
    engine_role: str = ""
    execution_fragility_status: str = "UNKNOWN"
    market_toxicity_status: str = "UNKNOWN"
    spread_regime_penalty_status: str = "UNKNOWN"
    participation_penalty_status: str = "NOT_PROVEN"
    micro_friction_source_status: str = "UNKNOWN"
    risk_input_completeness_status: str = "UNKNOWN"
    cost_model_completeness_status: str = "UNKNOWN"
    fee_source_status: str = "UNKNOWN"
    impact_source_status: str = "UNKNOWN"
    fill_realism_status: str = "UNKNOWN"
    realized_slippage_status: str = "UNKNOWN"
    risk_readiness_status: str = "UNKNOWN"
    input_reason_codes: tuple[str, ...] = ()
    execution_ready: bool = False
    promotion_ready: bool = False
    drawdown_state_code: str = DrawdownVerdict.ACCEPTED.value
    decision_severity: str = "nominal"
    physics_pressure_state: str = "nominal"
    fragility_score: float = 0.0
    toxicity_score: float = 0.0
    execution_survivability_score: float = 1.0
    micro_friction_score: float = 0.0
    summary: str = "risk=accept / no blocker triggered"


class PortfolioRiskSnapshot(BaseModel, frozen=True):
    positions: tuple[Position, ...] = ()
    current_loss_budget: float = 0.0
    current_equity: float = 0.0
    session_peak_equity: float = 0.0


class RiskPhysicsScores(BaseModel, frozen=True):
    fragility_score: float = 0.0
    toxicity_score: float = 0.0
    execution_survivability_score: float = 1.0
    micro_friction_score: float = 0.0
    pressure_state: str = "nominal"


class RiskMicroFrictionPrecheckInput(BaseModel, frozen=True):
    """Bounded typed input for the runtime-open micro-friction precheck hook."""

    context_id: str = Field(..., min_length=1)
    pair: str = Field(..., min_length=1)
    engine_id: str = Field(..., min_length=1)
    size: float = 0.0
    planned_loss: float | None = None
    fragility_score: float = 0.0
    toxicity_score: float = 0.0
    execution_survivability_score: float = 1.0
    micro_friction_score: float = 0.0
    pressure_state: str = "nominal"


class RiskMicroFrictionPrecheckOutcome(BaseModel, frozen=True):
    """Deterministic outcome of the bounded risk micro-friction precheck hook."""

    accepted: bool = True
    reason_codes: tuple[str, ...] = ()
    detail: str = ""


class RiskMicroFrictionPrecheckHook(Protocol):
    """Bounded hook surface injected into the real Build-4 risk runtime rail."""

    def __call__(
        self,
        hook_input: RiskMicroFrictionPrecheckInput,
    ) -> RiskMicroFrictionPrecheckOutcome:
        ...


class RiskDailyPnlPrecheckInput(BaseModel, frozen=True):
    """Bounded typed input for the runtime-open daily PnL breaker precheck hook."""

    context_id: str = Field(..., min_length=1)
    pair: str = Field(..., min_length=1)
    engine_id: str = Field(..., min_length=1)
    size: float = 0.0
    planned_loss: float | None = None
    session_date: str = Field(..., min_length=1)
    current_equity: float = Field(..., ge=0.0)
    session_peak_equity: float = Field(..., gt=0.0)


class RiskDailyPnlPrecheckOutcome(BaseModel, frozen=True):
    """Deterministic outcome of the bounded daily PnL breaker precheck hook."""

    accepted: bool = True
    verdict: str = "accepted"
    should_force_shadow: bool = False
    reason_codes: tuple[str, ...] = ()
    detail: str = ""


class RiskDailyPnlPrecheckHook(Protocol):
    """Bounded hook surface injected into the real Build-4 risk runtime rail."""

    def __call__(
        self,
        hook_input: RiskDailyPnlPrecheckInput,
    ) -> RiskDailyPnlPrecheckOutcome:
        ...


class RiskRegimePrecheckInput(BaseModel, frozen=True):
    """Bounded typed input for the runtime-open regime precheck hook."""

    context_id: str = Field(..., min_length=1)
    pair: str = Field(..., min_length=1)
    engine_id: str = Field(..., min_length=1)
    size: float = 0.0
    planned_loss: float | None = None
    regime_state: str = Field(default="unknown", min_length=1)
    entries_blocked: bool = False
    entries_blocked_until_ts: int = Field(default=0, ge=0)
    reason_codes: tuple[str, ...] = ()


class RiskRegimePrecheckOutcome(BaseModel, frozen=True):
    """Deterministic outcome of the bounded risk regime precheck hook."""

    accepted: bool = True
    reason_codes: tuple[str, ...] = ()
    detail: str = ""


class RiskRegimePrecheckHook(Protocol):
    """Bounded hook surface injected into the real Build-4 risk runtime rail."""

    def __call__(
        self,
        hook_input: RiskRegimePrecheckInput,
    ) -> RiskRegimePrecheckOutcome:
        ...


class RiskInfoStressPrecheckInput(BaseModel, frozen=True):
    """Bounded typed input for the runtime-open information-stress precheck hook."""

    context_id: str = Field(..., min_length=1)
    pair: str = Field(..., min_length=1)
    engine_id: str = Field(..., min_length=1)
    size: float = 0.0
    planned_loss: float | None = None
    now_ts: float = Field(..., gt=0.0)
    spread_bps: float | None = Field(default=None, ge=0.0)
    reference_spread_bps: float | None = Field(default=None, gt=0.0)
    depth_ratio: float | None = Field(default=None, ge=0.0, le=1.0)
    order_cancellation_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    taker_imbalance: float | None = Field(default=None, ge=-1.0, le=1.0)
    micro_vol_divergence: float | None = Field(default=None, ge=0.0)


class RiskInfoStressPrecheckOutcome(BaseModel, frozen=True):
    """Deterministic outcome of the bounded information-stress precheck hook."""

    accepted: bool = True
    stress_level: str = "normal"
    alert_count: int = Field(default=0, ge=0)
    entries_blocked: bool = False
    entries_blocked_until_ts: int = Field(default=0, ge=0)
    reason_codes: tuple[str, ...] = ()
    detail: str = ""


class RiskInfoStressPrecheckHook(Protocol):
    """Bounded hook surface injected into the real Build-4 risk runtime rail."""

    def __call__(
        self,
        hook_input: RiskInfoStressPrecheckInput,
    ) -> RiskInfoStressPrecheckOutcome:
        ...


class RiskEvaluation(BaseModel, frozen=True):
    action: RiskRuntimeAction
    accepted: bool
    reasons: tuple[str, ...] = ()
    reason_details: tuple[RiskReasonDetail, ...] = ()
    dominant_reason_code: str = ""
    explain_summary: str = "risk=accepted"
    explainability: RiskExplainability = Field(default_factory=RiskExplainability)
    gross_result: GrossCapResult
    loss_result: LossCapResult
    beta_projection: ProjectedBeta
    beta_result: BetaCapResult
    cluster_results: tuple[ClusterCapResult, ...] = ()
    drawdown_result: DrawdownGuardResult


__all__ = [
    "PortfolioRiskSnapshot",
    "RiskCandidate",
    "RiskDailyPnlPrecheckHook",
    "RiskDailyPnlPrecheckInput",
    "RiskDailyPnlPrecheckOutcome",
    "RiskEvaluation",
    "RiskExplainability",
    "RiskInfoStressPrecheckHook",
    "RiskInfoStressPrecheckInput",
    "RiskInfoStressPrecheckOutcome",
    "RiskLimits",
    "RiskMicroFrictionPrecheckHook",
    "RiskMicroFrictionPrecheckInput",
    "RiskMicroFrictionPrecheckOutcome",
    "RiskPhysicsScores",
    "RiskReasonDetail",
    "RiskRegimePrecheckHook",
    "RiskRegimePrecheckInput",
    "RiskRegimePrecheckOutcome",
    "RiskRuntimeAction",
]
