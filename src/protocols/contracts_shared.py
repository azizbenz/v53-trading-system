"""Shared governed protocol contracts for Shadow, Micro-live, and Live-Light."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from interface_contracts import (
    OperatorSafingAction,
    OperatorSafingRequest,
    ProfileId,
    PromotionState,
    ReviewState,
    RuntimeMode,
)
from protocols.enums import (
    LiveLightRunState,
    LiveLightVerdict,
    MicroLiveRunState,
    MicroLiveVerdict,
    ShadowComponentHardState,
    ShadowComponentKind,
    ShadowComponentVerdict,
    ShadowComparisonStatus,
    ShadowDivergenceSeverity,
    ShadowRunState,
    ShadowVerdict,
)


_ACCEPTED_IMPORT_STATUSES = frozenset({"accepted"})
_ACCEPTED_IMPORT_REVIEW_STATES = frozenset({"pending", "approved"})
_EXPECTED_IMPORT_SOURCE_PROFILE = ProfileId.COMPLETE.value
_ACCEPTED_ONBOARDING_REVIEW_STATES = frozenset(
    {ReviewState.PENDING, ReviewState.APPROVED}
)
_REJECTED_IMPORT_COMPATIBILITY_STATUSES = frozenset({"rejected"})
_REJECTED_IMPORT_SIGNATURE_STATUSES = frozenset(
    {
        "signature_invalid",
        "trust_store_unavailable",
        "key_id_unknown",
        "key_revoked",
        "payload_hash_mismatch",
    }
)
_EXPECTED_IMPORT_CONFLICT_RESOLUTION_MODE = "no_trade_then_strictest"
_EXPECTED_IMPORT_CONFLICT_HARD_VETO_ACTION = "no_trade"
_EXPECTED_IMPORT_CONFLICT_SCORE_AGGREGATION_MODE = "bounded_sum_with_global_cap"
_EXPECTED_IMPORT_CONFLICT_SIZE_REDUCE_MODE = "min_factor_wins"
_EXPECTED_IMPORT_CONFLICT_RANK_ADJUST_MODE = "bounded_sum"
_EXPECTED_IMPORT_REGISTRY_ATOMICITY_MODE = "atomic_snapshot_swap"
_EXPECTED_IMPORT_REGISTRY_CONCURRENCY_MODEL = "single_writer_multi_reader"
_REQUIRED_SHADOW_ENGINE_IDS = frozenset(
    {"engine_a", "engine_b", "engine_c", "engine_d"}
)
_REQUIRED_SHADOW_BUILD14_COMPONENT_IDS = frozenset(
    {
        "build14_microstructure",
        "build14_regime",
        "build14_covariance",
        "build14_risk_contribution",
        "build14_edge_diversity",
    }
)
_KNOWN_SHADOW_BUILD14_READER_IDS = frozenset(
    {
        "market_toxicity_snapshot",
        "execution_fragility_score",
        "lob_deep_filter_vwa",
        "order_book_imbalance",
        "false_breakout_model",
        "hurst_regime_classifier",
        "competition_monitor",
    }
)
_MICRO_LIVE_ALLOWED_ENGINES = _REQUIRED_SHADOW_ENGINE_IDS
_LIVE_LIGHT_ALLOWED_ENGINES = _REQUIRED_SHADOW_ENGINE_IDS

ShadowEngineJudgmentVerdict = Literal[
    "promotable",
    "shadow-only",
    "rewrite-required",
    "dormant",
]
ShadowPortfolioJudgmentVerdict = Literal[
    "promotable",
    "shadow-only",
    "rewrite-required",
]
ShadowPressureLevel = Literal["nominal", "elevated", "critical"]


class RegimeLiteGovernanceSummary(BaseModel, frozen=True):
    """Protocol-local summary of explicit regime_lite governance truth."""

    status: Literal[
        "not_configured",
        "assessment_only",
        "recommendation_only",
        "ready",
    ] = "not_configured"
    state: str = "not_configured"
    candidate_state: str = "not_configured"
    state_changed: bool = False
    entries_blocked: bool = False
    sudden_event: bool = False
    safing_severity: str = "not_configured"
    should_block_new_entries: bool = False
    should_exit_all: bool = False
    recommended_operator_action: str = ""
    operator_safing_request_action: str = ""
    operator_safing_request_source_runtime_mode: str = ""
    reason_codes: tuple[str, ...] = ()
    detail: str = ""


class InfoStressGovernanceSummary(BaseModel, frozen=True):
    """Protocol-local summary of explicit info_stress governance truth."""

    status: Literal[
        "not_configured",
        "assessment_only",
    ] = "not_configured"
    level: str = "not_configured"
    alert_count: int = Field(default=0, ge=0)
    entries_blocked: bool = False
    entries_blocked_until_ts: int = Field(default=0, ge=0)
    reason_codes: tuple[str, ...] = ()
    detail: str = ""


class DailyPnlBreakerGovernanceSummary(BaseModel, frozen=True):
    """Protocol-local summary of explicit daily PnL breaker governance truth."""

    status: Literal[
        "not_configured",
        "assessment_only",
    ] = "not_configured"
    verdict: str = "not_configured"
    should_force_shadow: bool = False
    circuit_breaker_tripped: bool = False
    circuit_breaker_reason: str = ""
    drawdown_pct: float = Field(default=0.0, ge=0.0)
    threshold_pct: float = Field(default=0.0, ge=0.0)
    shadow_locked_session_date: str = ""
    state_corrupted: bool = False
    state_last_reason: str = ""
    detail: str = ""
    reason_codes: tuple[str, ...] = ()


class ShadowEngineJudgment(BaseModel, frozen=True):
    """Engine-by-engine supervised judgment derived from the Build-11 shadow report."""

    engine_id: str = Field(..., min_length=1)
    component_verdict: str = Field(..., min_length=1)
    judgment_verdict: ShadowEngineJudgmentVerdict
    useful_frequency: float = Field(default=0.0, ge=0.0)
    ce_expected: float | None = None
    estimated_cost_bps: float = Field(default=0.0, ge=0.0)
    edge_net: float = 0.0
    economic_pass_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    conflict_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    marginal_edge: float = 0.0
    redundancy_score: float = Field(default=0.0, ge=0.0, le=1.0)
    portfolio_contribution: float = 0.0
    final_size_multiplier: float | None = None
    selection_outcome_code: str = ""
    portfolio_verdict_code: str = ""
    phantom_trade: bool = False
    hard_blocked: bool = False
    risk_decision_severity: str = ""
    physics_pressure_state: ShadowPressureLevel = "nominal"
    fragility_score: float | None = Field(default=None, ge=0.0, le=1.0)
    toxicity_score: float | None = Field(default=None, ge=0.0, le=1.0)
    execution_survivability_score: float | None = Field(default=None, ge=0.0, le=1.0)
    micro_friction_score: float | None = Field(default=None, ge=0.0, le=1.0)
    observations: int = Field(default=0, ge=0)
    rationale: str = ""
    evidence_summary: str = ""


class ShadowPortfolioJudgment(BaseModel, frozen=True):
    """Portfolio-level supervised judgment derived from the governed Shadow payload."""

    judgment_verdict: ShadowPortfolioJudgmentVerdict = "shadow-only"
    physics_pressure: ShadowPressureLevel = "nominal"
    redundancy_pressure: ShadowPressureLevel = "nominal"
    cluster_pressure: ShadowPressureLevel = "nominal"
    beta_pressure: ShadowPressureLevel = "nominal"
    gross_capacity_pressure: ShadowPressureLevel = "nominal"
    loss_capacity_pressure: ShadowPressureLevel = "nominal"
    dominant_cluster: str = ""
    beta_utilization: float | None = Field(default=None, ge=0.0)
    gross_capacity_used_pct: float | None = Field(default=None, ge=0.0, le=100.0)
    loss_capacity_used_pct: float | None = Field(default=None, ge=0.0, le=100.0)
    hard_block_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    phantom_trade_count: int | None = Field(default=None, ge=0)
    promotable_engine_count: int = Field(default=0, ge=0)
    shadow_only_engine_count: int = Field(default=0, ge=0)
    rewrite_required_engine_count: int = Field(default=0, ge=0)
    dormant_engine_count: int = Field(default=0, ge=0)
    elevated_physics_engine_count: int = Field(default=0, ge=0)
    critical_physics_engine_count: int = Field(default=0, ge=0)
    portfolio_rejected_engine_count: int = Field(default=0, ge=0)
    ranking_rejected_engine_count: int = Field(default=0, ge=0)
    cluster_rejected_engine_count: int = Field(default=0, ge=0)
    beta_rejected_engine_count: int = Field(default=0, ge=0)
    exposure_rejected_engine_count: int = Field(default=0, ge=0)
    loss_budget_rejected_engine_count: int = Field(default=0, ge=0)
    rationale: str = ""


class ShadowEngineJudgmentSummary(BaseModel, frozen=True):
    """Normalized judgment bundle used to decide engine promotion readiness after Shadow."""

    source_report_id: str = ""
    source_shadow_run_id: str = ""
    source_shadow_days_completed: int = Field(default=0, ge=0)
    source_shadow_required_days: int = Field(default=30, ge=1)
    portfolio_judgment: ShadowPortfolioJudgment = ShadowPortfolioJudgment()
    judgments: tuple[ShadowEngineJudgment, ...] = ()


__all__ = [
    "DailyPnlBreakerGovernanceSummary",
    "InfoStressGovernanceSummary",
    "OperatorSafingAction",
    "OperatorSafingRequest",
    "RegimeLiteGovernanceSummary",
    "ShadowEngineJudgment",
    "ShadowEngineJudgmentSummary",
    "ShadowEngineJudgmentVerdict",
    "ShadowPortfolioJudgment",
    "ShadowPortfolioJudgmentVerdict",
    "ShadowPressureLevel",
]
