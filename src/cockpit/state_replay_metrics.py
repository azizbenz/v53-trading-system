"""Phase 2 adapter - read ``auto_exports/<date>/replay_metrics.json``."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from interface_contracts.capital_profile_contracts import CapitalBucketProfile
from interface_contracts.promotion_artifact_contracts import (
    EnginePromotionArtifact,
    PairPromotionArtifact,
    SampleSizeSurvivalArtifact,
    StrategyPromotionArtifact,
)
from cockpit.state_freshness import source_stamp


_logger = logging.getLogger(__name__)
SourceStatus = Literal["ok", "missing", "stale", "parse_error", "not_yet_persisted"]
MIN_REPLAY_SAMPLE_RECORDS = 30
_FEE_SOURCE_EXPLICIT_STATUSES = {
    "FEE_SOURCE_PROVEN",
    "FEE_SOURCE_CONFIGURED",
    "FEE_SOURCE_EXCHANGE_METADATA",
    "EXPLICIT",
}
_IMPACT_SOURCE_EXPLICIT_STATUSES = {
    "IMPACT_SOURCE_PROVEN",
    "IMPACT_SOURCE_DEPTH20_MODEL",
    "EXPLICIT",
}
_BOOK_DEPTH_PROMOTION_READY_STATUSES = {"BOOK_DEPTH20_AVAILABLE"}
_FILL_REALISM_PROVEN_STATUSES = {
    "FILL_REALISM_PROVEN",
    "FILL_REALISM_SHADOW_MEASURED",
    "MEASURED",
    "PROVEN",
}
_REPLAY_LIVE_PARITY_PROVEN_STATUSES = {
    "REPLAY_LIVE_COST_PARITY_PROVEN",
    "REPLAY_SHADOW_COST_PARITY_PROVEN",
}


def _normalize_fee_source_status(status: str | None) -> str:
    resolved = str(status or "FEE_SOURCE_NOT_PROVEN")
    if resolved == "NOT_PROVEN":
        return "FEE_SOURCE_NOT_PROVEN"
    if resolved == "MISSING":
        return "FEE_SOURCE_MISSING"
    if resolved == "EXPLICIT":
        return "FEE_SOURCE_PROVEN"
    return resolved


def _normalize_impact_source_status(status: str | None) -> str:
    resolved = str(status or "IMPACT_SOURCE_NOT_PROVEN")
    if resolved == "NOT_PROVEN":
        return "IMPACT_SOURCE_NOT_PROVEN"
    if resolved == "MISSING":
        return "IMPACT_SOURCE_MISSING"
    if resolved == "EXPLICIT":
        return "IMPACT_SOURCE_PROVEN"
    return resolved


def _normalize_book_depth_source_status(status: str | None, levels: int | None) -> str:
    resolved = str(status or "BOOK_DEPTH_NOT_PROVEN")
    if resolved == "BOOK_DEPTH_STALE":
        return "BOOK_DEPTH_STALE"
    if levels is None:
        if resolved == "BOOK_DEPTH_MISSING":
            return "BOOK_DEPTH_MISSING"
        return resolved if resolved != "NOT_PROVEN" else "BOOK_DEPTH_NOT_PROVEN"
    if levels <= 0:
        return "BOOK_DEPTH_MISSING"
    if levels == 1:
        return "BOOK_TOP_OF_BOOK_ONLY"
    if levels < 20:
        return "BOOK_LIMITED_DEPTH_AVAILABLE"
    return "BOOK_DEPTH20_AVAILABLE"


def _normalize_fill_realism_status(status: str | None) -> str:
    resolved = str(status or "FILL_REALISM_NOT_PROVEN")
    mapping = {
        "PARTIAL": "FILL_REALISM_PARTIAL",
        "NOT_PROVEN": "FILL_REALISM_NOT_PROVEN",
        "MISSING": "FILL_REALISM_MISSING",
        "MEASURED": "FILL_REALISM_SHADOW_MEASURED",
        "PROVEN": "FILL_REALISM_PROVEN",
        "MODEL_ONLY": "FILL_REALISM_MODEL_ONLY",
        "SYNTHETIC_ONLY": "FILL_REALISM_SYNTHETIC_ONLY",
    }
    return mapping.get(resolved, resolved)


def _normalize_cost_parity_status(status: str | None) -> str:
    resolved = str(status or "REPLAY_LIVE_COST_PARITY_BLOCKED_BY_TELEMETRY")
    mapping = {
        "NOT_PROVEN": "REPLAY_LIVE_COST_PARITY_NOT_PROVEN",
        "MISSING": "REPLAY_LIVE_COST_PARITY_MISSING",
        "MEASURED": "REPLAY_LIVE_COST_PARITY_PARTIAL",
        "PROVEN": "REPLAY_LIVE_COST_PARITY_PARTIAL",
        "WITHIN_TOLERANCE": "REPLAY_LIVE_COST_PARITY_PARTIAL",
        "WITHIN_PRUDENT_TOLERANCE": "REPLAY_LIVE_COST_PARITY_PARTIAL",
    }
    return mapping.get(resolved, resolved)


def _normalize_cost_model_completeness_status(status: str | None) -> str:
    resolved = str(status or "COST_MODEL_NOT_PROVEN")
    if resolved == "COMPLETE":
        return "COST_MODEL_COMPLETE"
    if resolved in {"PARTIAL_NO_FEE_NO_IMPACT", "NOT_PROVEN", "UNKNOWN"}:
        return "COST_MODEL_NOT_PROVEN"
    return resolved


def _is_cost_model_complete(status: str) -> bool:
    return _normalize_cost_model_completeness_status(status) == "COST_MODEL_COMPLETE"


class PairAggregate(BaseModel, frozen=True):
    pair: str
    record_count: int = 0
    selected_count: int = 0
    ce_net: float = 0.0
    expected_cost_mean: float = 0.0
    replay_expected_cost_model_mean: float = 0.0
    expected_total_cost_mean: float | None = None
    realized_cost_mean: float = 0.0
    gross_return_mean: float = 0.0
    fee_source_status: str = "FEE_SOURCE_NOT_PROVEN"
    impact_source_status: str = "IMPACT_SOURCE_NOT_PROVEN"
    cost_model_completeness_status: str = "COST_MODEL_NOT_PROVEN"


class EngineAggregate(BaseModel, frozen=True):
    engine_id: str
    engine_role: str = ""
    shared_physics_mapping_status: str = "NOT_APPLICABLE"
    record_count: int = 0
    selected_count: int = 0
    hard_blocked_count: int = 0
    executed_count: int = 0
    reduced_count: int = 0
    rejected_count: int = 0
    no_fill_count: int | None = None
    execution_rate: float | None = None
    partial_fill_rate: float | None = None
    no_fill_rate: float | None = None
    ce_net: float = 0.0
    expected_cost_mean: float = 0.0
    replay_expected_cost_model_mean: float = 0.0
    expected_total_cost_mean: float | None = None
    realized_cost_mean: float = 0.0
    gross_return_mean: float = 0.0
    fee_source_status: str = "FEE_SOURCE_NOT_PROVEN"
    impact_source_status: str = "IMPACT_SOURCE_NOT_PROVEN"
    cost_model_completeness_status: str = "COST_MODEL_NOT_PROVEN"
    book_depth_source_status: str = "BOOK_DEPTH_NOT_PROVEN"
    book_depth_levels: int | None = Field(default=None, ge=0)
    impact_depth_level_used: int | None = Field(default=None, ge=0)
    impact_depth_readiness_status: str = "BOOK_DEPTH_NOT_PROVEN"
    shadow_extension_required: bool = True
    shadow_extension_reason: str | None = "NO_PROMOTION_GRADE_REPLAY_IMPACT_PROOF"
    minimum_shadow_days_required: int | None = Field(default=None, ge=0)
    shadow_extension_status: str = "MICRO_LIVE_BLOCKED_BY_DEPTH"
    fill_source_status: str = "FILL_SOURCE_NOT_PROVEN"
    fill_model_name: str | None = None
    fill_realism_status: str = "FILL_REALISM_NOT_PROVEN"
    fill_ratio_expected: float | None = Field(default=None, ge=0.0, le=1.0)
    fill_ratio_observed: float | None = Field(default=None, ge=0.0, le=1.0)
    partial_fill_rate_expected: float | None = Field(default=None, ge=0.0, le=1.0)
    partial_fill_rate_observed: float | None = Field(default=None, ge=0.0, le=1.0)
    no_fill_rate_expected: float | None = Field(default=None, ge=0.0, le=1.0)
    no_fill_rate_observed: float | None = Field(default=None, ge=0.0, le=1.0)
    measured_fill_flag: bool = False
    synthetic_fill_flag: bool = False
    realized_slippage_status: str = "NOT_PROVEN"
    cost_parity_status: str = "REPLAY_LIVE_COST_PARITY_BLOCKED_BY_TELEMETRY"
    replay_live_cost_parity_status: str = "REPLAY_LIVE_COST_PARITY_BLOCKED_BY_TELEMETRY"
    cost_drift_bps: float | None = None
    cost_drift_status: str = "NOT_PROVEN"
    parity_sample_count: int = 0
    sample_size_survival_status: str = "NOT_PROVEN"
    missing_realized_cost_count: int = 0
    engine_executed_only_net_return: float | None = None
    executed_only_net_return_status: str = "EXECUTED_NET_RETURN_NOT_PROVEN"
    engine_true_net_equity_max_drawdown: float | None = None
    true_net_equity_drawdown_status: str = "TRUE_NET_EQUITY_DRAWDOWN_NOT_PROVEN"
    shadow_confirmation_status: str = "NOT_PROVEN"
    promotion_status: str = "NOT_SHADOW_READY"


class ReplayMetricsSnapshot(BaseModel, frozen=True):
    """Typed view of the daily replay metrics export."""

    source_status: SourceStatus = "missing"
    source_path: str = ""
    total_records: int = 0
    total_opportunities: int = 0
    selected_count: int = 0
    executed_count: int = 0
    reduced_count: int = 0
    no_fill_count: int = 0
    hard_blocked_count: int = 0
    rejected_count: int = 0
    rejected_ranking_count: int = 0
    phantom_count: int = 0
    ce_net: float = 0.0
    expected_cost_mean: float = 0.0
    replay_expected_cost_model_mean: float = 0.0
    expected_total_cost_mean: float | None = None
    realized_cost_mean: float = 0.0
    gross_return_mean: float = 0.0
    gross_return_total: float = 0.0
    missing_realized_cost_count: int = 0
    executed_only_net_return: float | None = None
    executed_only_net_return_status: str = "EXECUTED_NET_RETURN_NOT_PROVEN"
    initial_capital: float | None = None
    true_net_equity_curve: tuple[float, ...] = ()
    true_net_equity_max_drawdown: float | None = None
    drawdown_proxy: float = 0.0
    non_execution_rate: float = 1.0
    fee_source_status: str = "FEE_SOURCE_NOT_PROVEN"
    fee_model_name: str | None = None
    fee_rate_maker_bps: float | None = Field(default=None, ge=0.0)
    fee_rate_taker_bps: float | None = Field(default=None, ge=0.0)
    fee_currency: str | None = None
    fee_amount: float | None = Field(default=None, ge=0.0)
    fee_bps: float | None = Field(default=None, ge=0.0)
    fee_provenance_ref: str | None = None
    fee_input_hash: str | None = None
    fee_policy_version: str | None = None
    impact_source_status: str = "IMPACT_SOURCE_NOT_PROVEN"
    impact_model_name: str | None = None
    impact_bps: float | None = Field(default=None, ge=0.0)
    impact_notional: float | None = Field(default=None, ge=0.0)
    impact_depth_ref: str | None = None
    impact_depth_level: int | None = Field(default=None, ge=0)
    impact_provenance_ref: str | None = None
    impact_input_hash: str | None = None
    impact_policy_version: str | None = None
    book_depth_available: bool | None = None
    book_depth_levels: int | None = Field(default=None, ge=0)
    book_depth_source_status: str = "BOOK_DEPTH_NOT_PROVEN"
    book_depth_snapshot_count: int | None = Field(default=None, ge=0)
    book_depth_event_count: int | None = Field(default=None, ge=0)
    book_depth_missing_count: int | None = Field(default=None, ge=0)
    book_depth_staleness_status: str = "BOOK_DEPTH_NOT_PROVEN"
    impact_depth_level_used: int | None = Field(default=None, ge=0)
    impact_depth_readiness_status: str = "BOOK_DEPTH_NOT_PROVEN"
    shadow_extension_required: bool = True
    shadow_extension_reason: str | None = "NO_PROMOTION_GRADE_REPLAY_IMPACT_PROOF"
    minimum_shadow_days_required: int | None = Field(default=None, ge=0)
    shadow_extension_status: str = "MICRO_LIVE_BLOCKED_BY_DEPTH"
    cost_model_completeness_status: str = "COST_MODEL_NOT_PROVEN"
    cost_readiness_reason_codes: tuple[str, ...] = ()
    fill_ratio_source: str = "UNKNOWN"
    fill_realism_status: str = "FILL_REALISM_NOT_PROVEN"
    fill_source_status: str = "FILL_SOURCE_NOT_PROVEN"
    fill_model_name: str | None = None
    fill_model_version: str | None = None
    fill_ratio_expected: float | None = Field(default=None, ge=0.0, le=1.0)
    fill_ratio_observed: float | None = Field(default=None, ge=0.0, le=1.0)
    partial_fill_rate_expected: float | None = Field(default=None, ge=0.0, le=1.0)
    partial_fill_rate_observed: float | None = Field(default=None, ge=0.0, le=1.0)
    no_fill_rate_expected: float | None = Field(default=None, ge=0.0, le=1.0)
    no_fill_rate_observed: float | None = Field(default=None, ge=0.0, le=1.0)
    fill_latency_ms_expected: float | None = Field(default=None, ge=0.0)
    fill_latency_ms_observed: float | None = Field(default=None, ge=0.0)
    synthetic_fill_flag: bool = False
    measured_fill_flag: bool = False
    fill_provenance_ref: str | None = None
    fill_input_hash: str | None = None
    fill_policy_version: str | None = None
    realized_slippage_status: str = "NOT_PROVEN"
    cost_parity_status: str = "REPLAY_LIVE_COST_PARITY_BLOCKED_BY_TELEMETRY"
    replay_live_cost_parity_status: str = "REPLAY_LIVE_COST_PARITY_BLOCKED_BY_TELEMETRY"
    replay_cost_components: tuple[str, ...] = ()
    shadow_cost_components: tuple[str, ...] = ()
    live_cost_components: tuple[str, ...] = ()
    replay_fee_bps: float | None = Field(default=None, ge=0.0)
    shadow_fee_bps: float | None = Field(default=None, ge=0.0)
    live_fee_bps: float | None = Field(default=None, ge=0.0)
    replay_impact_bps: float | None = Field(default=None, ge=0.0)
    shadow_impact_bps: float | None = Field(default=None, ge=0.0)
    live_impact_bps: float | None = Field(default=None, ge=0.0)
    replay_slippage_bps: float | None = Field(default=None, ge=0.0)
    shadow_slippage_bps: float | None = Field(default=None, ge=0.0)
    live_slippage_bps: float | None = Field(default=None, ge=0.0)
    replay_fill_ratio: float | None = Field(default=None, ge=0.0, le=1.0)
    shadow_fill_ratio: float | None = Field(default=None, ge=0.0, le=1.0)
    live_fill_ratio: float | None = Field(default=None, ge=0.0, le=1.0)
    cost_drift_bps: float | None = None
    cost_drift_status: str = "NOT_PROVEN"
    parity_sample_count: int = 0
    parity_window_start: str | None = None
    parity_window_end: str | None = None
    parity_input_hash: str | None = None
    parity_policy_version: str | None = None
    small_capital_exclusion_rate: float | None = None
    small_capital_exclusion_status: str = "NOT_PROVEN"
    small_capital_viability_status: str = "BLOCKED_BY_BACKTEST"
    min_notional_viability_status: str = "BLOCKED_BY_BACKTEST"
    capital_fragmentation_status: str = "NOT_PROVEN"
    sizing_doctrine: str = "FIXED_FRACTION_VOL_TARGET_CAPS"
    kelly_status: str = "NOT_IMPLEMENTED_BY_DESIGN_FOR_NOW"
    kelly_reason: str = (
        "crypto spot small-capital / high cost / high uncertainty / future research"
    )
    multi_asset_risk_control_status: str = "BASELINE_CAPS_ONLY"
    covariance_model_status: str = "NOT_IMPLEMENTED"
    true_net_equity_drawdown_status: str = "TRUE_NET_EQUITY_DRAWDOWN_NOT_PROVEN"
    drawdown_proxy_promotion_grade: bool = False
    capital_bucket_profiles: tuple[CapitalBucketProfile, ...] = ()
    engine_promotion_artifacts: tuple[EnginePromotionArtifact, ...] = ()
    pair_promotion_artifacts: tuple[PairPromotionArtifact, ...] = ()
    strategy_promotion_artifacts: tuple[StrategyPromotionArtifact, ...] = ()
    sample_size_survival_artifacts: tuple[SampleSizeSurvivalArtifact, ...] = ()
    pair_aggregates: tuple[PairAggregate, ...] = ()
    engine_aggregates: tuple[EngineAggregate, ...] = ()

    @property
    def exec_rate(self) -> float:
        if self.total_records == 0:
            return 0.0
        return self.executed_count / self.total_records

    @property
    def exec_rate_total(self) -> float:
        return self.exec_rate

    @property
    def selected_execution_rate(self) -> float | None:
        if self.selected_count <= 0:
            return None
        return self.executed_count / self.selected_count

    @property
    def expected_ce_label(self) -> str:
        return "Expected CE net"

    @property
    def expected_ce_caveat(self) -> str:
        return "Expected CE over replay DTR records; not realized profitability."

    @property
    def expected_ce_realization_status(self) -> str:
        return "EXPECTED_ONLY"

    @property
    def realized_profitability_status(self) -> str:
        return "NOT_REALIZED_PNL"

    @property
    def executed_only_net_return_label(self) -> str:
        return "Executed-only net return"

    @property
    def executed_only_net_return_caveat(self) -> str:
        if self.cost_model_is_complete:
            return (
                "Executed/reduced records only after realized cost. Blocked, rejected, "
                "phantom, and no-fill records do not count toward realized profitability."
            )
        return (
            "Executed/reduced records only after realized cost, but replay fee/impact/fill/parity "
            "provenance is incomplete, so the value stays diagnostic and non-promotion-grade."
        )

    @property
    def executed_return_display_status(self) -> str:
        if self.executed_only_net_return_status in {
            "EXECUTED_NET_RETURN_PROVEN",
            "EXECUTED_RETURN_PROVEN",
        }:
            return "PROVEN"
        return "EXECUTED_RETURN_NOT_PROVEN"

    @property
    def exec_rate_label(self) -> str:
        return "Exec rate (executed / total records)"

    @property
    def exec_rate_caveat(self) -> str:
        return "Current denominator is total replay records, not selected-only executions."

    @property
    def replay_expected_cost_model_label(self) -> str:
        return "Replay expected cost model"

    @property
    def replay_expected_cost_model_caveat(self) -> str:
        return (
            "Replay expected cost model is non-promotion-grade until fee and impact provenance are "
            "explicit, fill realism is proven, and replay/live cost parity is documented."
        )

    @property
    def normalized_fee_source_status(self) -> str:
        return _normalize_fee_source_status(self.fee_source_status)

    @property
    def normalized_impact_source_status(self) -> str:
        return _normalize_impact_source_status(self.impact_source_status)

    @property
    def normalized_book_depth_source_status(self) -> str:
        return _normalize_book_depth_source_status(
            self.book_depth_source_status,
            self.book_depth_levels,
        )

    @property
    def normalized_fill_realism_status(self) -> str:
        return _normalize_fill_realism_status(self.fill_realism_status)

    @property
    def normalized_cost_parity_status(self) -> str:
        return _normalize_cost_parity_status(self.cost_parity_status)

    @property
    def normalized_cost_model_completeness_status(self) -> str:
        return _normalize_cost_model_completeness_status(self.cost_model_completeness_status)

    @property
    def cost_model_is_complete(self) -> bool:
        return _is_cost_model_complete(self.cost_model_completeness_status)

    @property
    def cost_model_is_partial(self) -> bool:
        return not self.cost_model_is_complete

    @property
    def cost_model_caveat(self) -> str:
        reason_codes = ", ".join(self.cost_readiness_reason_codes) or "n/a"
        return (
            f"Fee source={self.normalized_fee_source_status} / model={self.fee_model_name or 'n/a'}; "
            f"impact source={self.normalized_impact_source_status} / model={self.impact_model_name or 'n/a'}; "
            f"book_depth={self.normalized_book_depth_source_status} / levels={self.book_depth_levels if self.book_depth_levels is not None else 'n/a'}; "
            f"fill_realism={self.normalized_fill_realism_status}; "
            f"parity={self.normalized_cost_parity_status}; completeness={self.normalized_cost_model_completeness_status}; "
            f"reasons={reason_codes}."
        )

    @property
    def fill_realism_caveat(self) -> str:
        return (
            f"Fill realism={self.normalized_fill_realism_status}; source={self.fill_source_status}; "
            f"fill_ratio source={self.fill_ratio_source}; measured_fill_flag={self.measured_fill_flag}; "
            f"synthetic_fill_flag={self.synthetic_fill_flag}. "
            "Execution factor remains non-promotion-grade unless measured fill provenance is proven."
        )

    @property
    def realized_slippage_caveat(self) -> str:
        if self.realized_slippage_status == "FOLDED_IN_TOTAL_COST":
            return "Realized slippage is folded into total realized cost, not exposed as a standalone metric."
        return "Standalone realized slippage is not proven on this replay rail."

    @property
    def book_depth_display_status(self) -> str:
        if self.normalized_book_depth_source_status == "BOOK_DEPTH20_AVAILABLE":
            return "DEPTH20_AVAILABLE"
        if self.normalized_book_depth_source_status == "BOOK_LIMITED_DEPTH_AVAILABLE":
            return "LIMITED_DEPTH_PARTIAL"
        if self.normalized_book_depth_source_status == "BOOK_TOP_OF_BOOK_ONLY":
            return "TOP_OF_BOOK_PROXY_ONLY"
        if self.normalized_book_depth_source_status == "BOOK_DEPTH_MISSING":
            return "BOOK_DEPTH_MISSING"
        if self.normalized_book_depth_source_status == "BOOK_DEPTH_STALE":
            return "BOOK_DEPTH_STALE"
        return "BOOK_DEPTH_NOT_PROVEN"

    @property
    def book_depth_caveat(self) -> str:
        return (
            f"Book depth={self.normalized_book_depth_source_status}; levels={self.book_depth_levels if self.book_depth_levels is not None else 'n/a'}; "
            f"impact readiness={self.impact_depth_readiness_status}; shadow extension={self.shadow_extension_status}; "
            "limited depth cannot masquerade as depth20 and missing depth cannot become zero impact."
        )

    @property
    def fill_realism_display_status(self) -> str:
        if self.normalized_fill_realism_status == "FILL_REALISM_SYNTHETIC_ONLY":
            return "FILL_REALISM_SYNTHETIC_ONLY"
        if self.normalized_fill_realism_status in _FILL_REALISM_PROVEN_STATUSES:
            return "FILL_REALISM_PROVEN"
        return "FILL_REALISM_NOT_PROVEN"

    @property
    def cost_parity_display_status(self) -> str:
        if self.normalized_cost_parity_status in _REPLAY_LIVE_PARITY_PROVEN_STATUSES:
            return "REPLAY_LIVE_COST_PARITY_PROVEN"
        return "REPLAY_LIVE_COST_PARITY_NOT_PROVEN"

    @property
    def shadow_extension_display_status(self) -> str:
        if self.shadow_extension_required:
            return "SHADOW_EXTENDED_REQUIRED"
        return self.shadow_extension_status

    @property
    def small_capital_caveat(self) -> str:
        return (
            "Small-capital readiness remains "
            f"{self.small_capital_viability_status}; fail-closed min_notional protection "
            "is safety only, not 400-500 EUR viability proof. "
            f"Capital profile artifact status={self.capital_profile_artifact_status}."
        )

    @property
    def capital_profile_artifact_status(self) -> str:
        if not self.capital_bucket_profiles:
            return "CAPITAL_BUCKET_NOT_PROVEN"
        if all(profile.promotion_status == "CAPITAL_BUCKET_READY" for profile in self.capital_bucket_profiles):
            return "CAPITAL_BUCKET_READY"
        priorities = (
            "CAPITAL_BUCKET_BLOCKED_BY_MIN_NOTIONAL",
            "CAPITAL_BUCKET_BLOCKED_BY_FRAGMENTATION",
            "CAPITAL_BUCKET_BLOCKED_BY_COST_COMPLETENESS",
            "CAPITAL_BUCKET_BLOCKED_BY_FILL_REALISM",
            "CAPITAL_BUCKET_BLOCKED_BY_DEPTH",
            "CAPITAL_BUCKET_BLOCKED_BY_DRAWDOWN",
            "CAPITAL_BUCKET_BLOCKED_BY_SAMPLE_SIZE",
            "CAPITAL_BUCKET_BLOCKED_BY_BACKTEST",
            "CAPITAL_BUCKET_NOT_PROVEN",
        )
        for priority in priorities:
            if any(profile.promotion_status == priority for profile in self.capital_bucket_profiles):
                return priority
        return "CAPITAL_BUCKET_NOT_PROVEN"

    @property
    def capital_profile_caveat(self) -> str:
        if not self.capital_bucket_profiles:
            return (
                "Capital profile artifacts are missing. Static config pair universes must not "
                "be treated as small-capital readiness proof."
            )
        return (
            f"Capital profile artifact status={self.capital_profile_artifact_status}; "
            "allowed_pairs and max_active_pairs remain non-green until measured per-bucket "
            "artifacts prove viability."
        )

    @property
    def capital_profiles_promotion_ready(self) -> bool:
        return bool(self.capital_bucket_profiles) and all(
            profile.promotion_status == "CAPITAL_BUCKET_READY"
            for profile in self.capital_bucket_profiles
        )

    @property
    def sizing_doctrine_caveat(self) -> str:
        return (
            f"Sizing doctrine={self.sizing_doctrine}; Kelly status={self.kelly_status}. "
            f"Kelly reason={self.kelly_reason}."
        )

    @property
    def portfolio_multi_asset_caveat(self) -> str:
        return (
            "Portfolio multi-asset control is "
            f"{self.multi_asset_risk_control_status}; covariance model={self.covariance_model_status}."
        )

    @property
    def true_drawdown_caveat(self) -> str:
        return (
            "True net-equity drawdown requires ordered executed/reduced realized net PnL "
            f"and capital base. status={self.true_net_equity_drawdown_status}; "
            f"drawdown_proxy_promotion_grade={self.drawdown_proxy_promotion_grade}."
        )

    @property
    def true_net_equity_drawdown_label(self) -> str:
        return "True net-equity max drawdown"

    @property
    def true_drawdown_display_status(self) -> str:
        if self.true_net_equity_drawdown_status in {
            "TRUE_NET_EQUITY_DRAWDOWN_PROVEN",
            "MEASURED",
            "PROVEN",
        }:
            return "PROVEN"
        return "TRUE_DRAWDOWN_NOT_PROVEN"

    @property
    def drawdown_proxy_label(self) -> str:
        return "Drawdown proxy"

    @property
    def drawdown_proxy_caveat(self) -> str:
        return "Gross-return proxy; not net-equity max drawdown and not promotion-grade."

    @property
    def drawdown_proxy_status(self) -> str:
        return "DRAWDOWN_PROXY_ONLY"

    @property
    def source_is_unavailable(self) -> bool:
        return self.source_status in {"missing", "parse_error", "not_yet_persisted"}

    @property
    def promotion_economics_status(self) -> str:
        if (
            not self.source_is_unavailable
            and self.source_status != "stale"
            and self.total_records >= MIN_REPLAY_SAMPLE_RECORDS
            and self.cost_model_is_complete
            and self.capital_profiles_promotion_ready
            and self.executed_only_net_return_status
            in {"EXECUTED_NET_RETURN_PROVEN", "EXECUTED_RETURN_PROVEN"}
            and self.true_net_equity_drawdown_status
            in {"TRUE_NET_EQUITY_DRAWDOWN_PROVEN", "MEASURED", "PROVEN"}
        ):
            return "PROMOTION_ECONOMICS_READY"
        return "PROMOTION_ECONOMICS_NOT_READY"

    @property
    def economics_display_state(self) -> str:
        if self.source_is_unavailable:
            return "placeholder"
        if self.source_status == "stale":
            return "stale"
        if self.total_records <= 0:
            return "placeholder"
        if self.total_records < MIN_REPLAY_SAMPLE_RECORDS:
            return "insufficient_sample"
        if (
            self.cost_model_is_partial
            or not self.capital_profiles_promotion_ready
            or self.executed_only_net_return_status
            not in {"EXECUTED_NET_RETURN_PROVEN", "EXECUTED_RETURN_PROVEN"}
            or self.true_net_equity_drawdown_status
            not in {"TRUE_NET_EQUITY_DRAWDOWN_PROVEN", "MEASURED", "PROVEN"}
        ):
            return "partial_replay"
        return "measured"

    @property
    def economics_reason_codes(self) -> tuple[str, ...]:
        reason_codes: list[str] = [
            "EXPECTED_CE_ONLY",
            "EXPECTED_ONLY",
            "NOT_REALIZED_PNL",
            "EXEC_RATE_DENOMINATOR_TOTAL_RECORDS",
            "DRAWDOWN_PROXY_DIAGNOSTIC_ONLY",
            "DRAWDOWN_PROXY_ONLY",
        ]
        if self.source_status == "stale":
            reason_codes.append("REPLAY_METRICS_STALE")
        elif self.source_is_unavailable:
            reason_codes.append("REPLAY_METRICS_NOT_AVAILABLE")
        if self.total_records <= 0:
            reason_codes.append("REPLAY_METRICS_NOT_MEASURED")
        if 0 < self.total_records < MIN_REPLAY_SAMPLE_RECORDS:
            reason_codes.append("SAMPLE_TOO_SMALL")
        if self.cost_model_is_partial:
            reason_codes.extend(("REPLAY_COST_MODEL_PARTIAL", "COST_MODEL_NOT_PROMOTION_READY"))
        if self.executed_only_net_return_status not in {
            "EXECUTED_NET_RETURN_PROVEN",
            "EXECUTED_RETURN_PROVEN",
        }:
            reason_codes.append("EXECUTED_RETURN_NOT_PROVEN")
        if self.normalized_fee_source_status in {"FEE_SOURCE_NOT_PROVEN", "FEE_SOURCE_MISSING"}:
            reason_codes.append("FEE_SOURCE_NOT_PROVEN")
        if self.normalized_impact_source_status in {
            "IMPACT_SOURCE_NOT_PROVEN",
            "IMPACT_SOURCE_MISSING",
        }:
            reason_codes.append("IMPACT_SOURCE_NOT_PROVEN")
        if self.normalized_impact_source_status in {
            "IMPACT_SOURCE_ESTIMATED",
            "IMPACT_SOURCE_SYNTHETIC",
        }:
            reason_codes.append(self.normalized_impact_source_status)
        if self.book_depth_display_status in {
            "LIMITED_DEPTH_PARTIAL",
            "TOP_OF_BOOK_PROXY_ONLY",
            "BOOK_DEPTH_MISSING",
            "BOOK_DEPTH_STALE",
            "BOOK_DEPTH_NOT_PROVEN",
        }:
            reason_codes.append(self.book_depth_display_status)
        if self.shadow_extension_required:
            reason_codes.append("SHADOW_EXTENDED_REQUIRED")
            if self.shadow_extension_status == "SHADOW_DIAGNOSTIC_ONLY":
                reason_codes.append("MICRO_LIVE_BLOCKED_BY_DEPTH")
        if self.normalized_fee_source_status == "FEE_SOURCE_ESTIMATED":
            reason_codes.append("FEE_SOURCE_ESTIMATED")
        if self.fill_ratio_source == "UNKNOWN":
            reason_codes.append("FILL_RATIO_SOURCE_UNKNOWN")
        if self.fill_realism_display_status == "FILL_REALISM_NOT_PROVEN":
            reason_codes.append("FILL_REALISM_NOT_PROVEN")
        elif self.fill_realism_display_status == "FILL_REALISM_SYNTHETIC_ONLY":
            reason_codes.append("FILL_REALISM_SYNTHETIC_ONLY")
        if self.realized_slippage_status == "NOT_PROVEN":
            reason_codes.append("REALIZED_SLIPPAGE_NOT_PROVEN")
        if self.cost_parity_display_status != "REPLAY_LIVE_COST_PARITY_PROVEN":
            reason_codes.append("REPLAY_LIVE_COST_PARITY_NOT_PROVEN")
        if self.small_capital_viability_status not in {"MEASURED", "PASS"}:
            reason_codes.append("SMALL_CAPITAL_VIABILITY_NOT_PROVEN")
        if self.min_notional_viability_status not in {"MEASURED", "PASS"}:
            reason_codes.append("MIN_NOTIONAL_VIABILITY_NOT_PROVEN")
        if self.capital_fragmentation_status not in {"MEASURED", "PASS"}:
            reason_codes.append("CAPITAL_FRAGMENTATION_NOT_PROVEN")
        if not self.capital_profiles_promotion_ready:
            reason_codes.append(self.capital_profile_artifact_status)
        if self.multi_asset_risk_control_status == "BASELINE_CAPS_ONLY":
            reason_codes.append("PORTFOLIO_BASELINE_CAPS_ONLY")
        if self.true_net_equity_drawdown_status not in {
            "TRUE_NET_EQUITY_DRAWDOWN_PROVEN",
            "MEASURED",
            "PROVEN",
        }:
            reason_codes.append("TRUE_DRAWDOWN_NOT_PROVEN")
        if self.promotion_economics_status == "PROMOTION_ECONOMICS_NOT_READY":
            reason_codes.append("PROMOTION_ECONOMICS_NOT_READY")
        reason_codes.extend(self.cost_readiness_reason_codes)
        return tuple(dict.fromkeys(reason_codes))

    @property
    def allow_positive_economics_tone(self) -> bool:
        return self.economics_display_state == "measured"

    @property
    def ce_net_value_class(self) -> str:
        if self.allow_positive_economics_tone:
            return "value-up" if self.ce_net >= 0 else "value-down"
        return "value-warn" if self.ce_net >= 0 else "value-down"

    @property
    def gross_return_mean_value_class(self) -> str:
        if self.allow_positive_economics_tone:
            return "value-up" if self.gross_return_mean >= 0 else "value-down"
        return "value-warn" if self.gross_return_mean >= 0 else "value-down"


def _latest_export_dir(auto_exports_root: Path) -> Path | None:
    if not auto_exports_root.is_dir():
        return None
    try:
        candidates = sorted(
            (d for d in auto_exports_root.iterdir() if d.is_dir()),
            key=lambda d: d.name,
            reverse=True,
        )
    except OSError:
        return None
    return candidates[0] if candidates else None


def read_replay_metrics(auto_exports_root: Path) -> ReplayMetricsSnapshot:
    latest = _latest_export_dir(auto_exports_root)
    if latest is None:
        return ReplayMetricsSnapshot(source_status="missing")
    path = latest / "replay_metrics.json"
    if not path.is_file():
        return ReplayMetricsSnapshot(source_status="missing", source_path=str(path))
    stamp = source_stamp(path=path, stale_after_seconds=300.0)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _logger.warning("Cannot parse replay metrics %s: %s", path, exc)
        return ReplayMetricsSnapshot(source_status="parse_error", source_path=str(path))
    if not isinstance(payload, dict):
        return ReplayMetricsSnapshot(source_status="parse_error", source_path=str(path))

    pairs = tuple(
        PairAggregate(
            pair=str(p.get("pair", "")),
            record_count=int(p.get("record_count", 0)),
            selected_count=int(p.get("selected_count", 0)),
            ce_net=float(p.get("ce_net", 0.0)),
            expected_cost_mean=float(p.get("expected_cost_mean", 0.0)),
            replay_expected_cost_model_mean=float(
                p.get("replay_expected_cost_model_mean", p.get("expected_cost_mean", 0.0))
            ),
            expected_total_cost_mean=_maybe_float(p.get("expected_total_cost_mean")),
            realized_cost_mean=float(p.get("realized_cost_mean", 0.0)),
            gross_return_mean=float(p.get("gross_return_mean", 0.0)),
            fee_source_status=_normalize_fee_source_status(p.get("fee_source_status")),
            impact_source_status=_normalize_impact_source_status(p.get("impact_source_status")),
            cost_model_completeness_status=_normalize_cost_model_completeness_status(
                p.get("cost_model_completeness_status")
            ),
        )
        for p in payload.get("pair_aggregates") or ()
        if isinstance(p, dict)
    )
    engines = tuple(
        EngineAggregate(
            engine_id=str(e.get("engine_id", "")),
            engine_role=str(e.get("engine_role", "")),
            shared_physics_mapping_status=str(
                e.get("shared_physics_mapping_status", "NOT_APPLICABLE")
            ),
            record_count=int(e.get("record_count", 0)),
            selected_count=int(e.get("selected_count", 0)),
            hard_blocked_count=int(e.get("hard_blocked_count", 0)),
            executed_count=int(e.get("executed_count", 0)),
            reduced_count=int(e.get("reduced_count", 0)),
            rejected_count=int(e.get("rejected_count", 0)),
            no_fill_count=(
                int(e.get("no_fill_count"))
                if e.get("no_fill_count") is not None
                else None
            ),
            execution_rate=_maybe_float(e.get("execution_rate")),
            partial_fill_rate=_maybe_float(e.get("partial_fill_rate")),
            no_fill_rate=_maybe_float(e.get("no_fill_rate")),
            ce_net=float(e.get("ce_net", 0.0)),
            expected_cost_mean=float(e.get("expected_cost_mean", 0.0)),
            replay_expected_cost_model_mean=float(
                e.get("replay_expected_cost_model_mean", e.get("expected_cost_mean", 0.0))
            ),
            expected_total_cost_mean=_maybe_float(e.get("expected_total_cost_mean")),
            realized_cost_mean=float(e.get("realized_cost_mean", 0.0)),
            gross_return_mean=float(e.get("gross_return_mean", 0.0)),
            fee_source_status=_normalize_fee_source_status(e.get("fee_source_status")),
            impact_source_status=_normalize_impact_source_status(e.get("impact_source_status")),
            cost_model_completeness_status=_normalize_cost_model_completeness_status(
                e.get("cost_model_completeness_status")
            ),
            book_depth_source_status=_normalize_book_depth_source_status(
                e.get("book_depth_source_status"),
                _maybe_int(e.get("book_depth_levels")),
            ),
            book_depth_levels=_maybe_int(e.get("book_depth_levels")),
            impact_depth_level_used=_maybe_int(e.get("impact_depth_level_used")),
            impact_depth_readiness_status=str(
                e.get("impact_depth_readiness_status", "BOOK_DEPTH_NOT_PROVEN")
            ),
            shadow_extension_required=bool(e.get("shadow_extension_required", True)),
            shadow_extension_reason=_maybe_str(e.get("shadow_extension_reason")),
            minimum_shadow_days_required=_maybe_int(
                e.get("minimum_shadow_days_required")
            ),
            shadow_extension_status=str(
                e.get("shadow_extension_status", "MICRO_LIVE_BLOCKED_BY_DEPTH")
            ),
            fill_source_status=str(e.get("fill_source_status", "FILL_SOURCE_NOT_PROVEN")),
            fill_model_name=_maybe_str(e.get("fill_model_name")),
            fill_realism_status=_normalize_fill_realism_status(
                e.get("fill_realism_status")
            ),
            fill_ratio_expected=_maybe_float(e.get("fill_ratio_expected")),
            fill_ratio_observed=_maybe_float(e.get("fill_ratio_observed")),
            partial_fill_rate_expected=_maybe_float(
                e.get("partial_fill_rate_expected")
            ),
            partial_fill_rate_observed=_maybe_float(
                e.get("partial_fill_rate_observed")
            ),
            no_fill_rate_expected=_maybe_float(e.get("no_fill_rate_expected")),
            no_fill_rate_observed=_maybe_float(e.get("no_fill_rate_observed")),
            measured_fill_flag=bool(e.get("measured_fill_flag", False)),
            synthetic_fill_flag=bool(e.get("synthetic_fill_flag", False)),
            realized_slippage_status=str(
                e.get("realized_slippage_status", "NOT_PROVEN")
            ),
            cost_parity_status=_normalize_cost_parity_status(
                e.get("cost_parity_status", e.get("replay_live_cost_parity_status"))
            ),
            replay_live_cost_parity_status=_normalize_cost_parity_status(
                e.get("replay_live_cost_parity_status")
            ),
            cost_drift_bps=_maybe_float(e.get("cost_drift_bps")),
            cost_drift_status=str(e.get("cost_drift_status", "NOT_PROVEN")),
            parity_sample_count=int(e.get("parity_sample_count", 0)),
            sample_size_survival_status=str(
                e.get("sample_size_survival_status", "NOT_PROVEN")
            ),
            missing_realized_cost_count=int(e.get("missing_realized_cost_count", 0)),
            engine_executed_only_net_return=_maybe_float(
                e.get("engine_executed_only_net_return")
            ),
            executed_only_net_return_status=str(
                e.get(
                    "executed_only_net_return_status",
                    "EXECUTED_NET_RETURN_NOT_PROVEN",
                )
            ),
            engine_true_net_equity_max_drawdown=_maybe_float(
                e.get("engine_true_net_equity_max_drawdown")
            ),
            true_net_equity_drawdown_status=str(
                e.get(
                    "true_net_equity_drawdown_status",
                    "TRUE_NET_EQUITY_DRAWDOWN_NOT_PROVEN",
                )
            ),
            shadow_confirmation_status=str(
                e.get("shadow_confirmation_status", "NOT_PROVEN")
            ),
            promotion_status=str(e.get("promotion_status", "NOT_SHADOW_READY")),
        )
        for e in payload.get("engine_aggregates") or ()
        if isinstance(e, dict)
    )
    capital_bucket_profiles = tuple(
        CapitalBucketProfile.model_validate(item)
        for item in payload.get("capital_bucket_profiles") or ()
        if isinstance(item, dict)
    )
    engine_promotion_artifacts = tuple(
        EnginePromotionArtifact.model_validate(item)
        for item in payload.get("engine_promotion_artifacts") or ()
        if isinstance(item, dict)
    )
    pair_promotion_artifacts = tuple(
        PairPromotionArtifact.model_validate(item)
        for item in payload.get("pair_promotion_artifacts") or ()
        if isinstance(item, dict)
    )
    strategy_promotion_artifacts = tuple(
        StrategyPromotionArtifact.model_validate(item)
        for item in payload.get("strategy_promotion_artifacts") or ()
        if isinstance(item, dict)
    )
    sample_size_survival_artifacts = tuple(
        SampleSizeSurvivalArtifact.model_validate(item)
        for item in payload.get("sample_size_survival_artifacts") or ()
        if isinstance(item, dict)
    )
    return ReplayMetricsSnapshot(
        source_status=str(stamp["source_status"]),
        source_path=str(path),
        total_records=int(payload.get("total_records", 0)),
        total_opportunities=int(payload.get("total_opportunities", 0)),
        selected_count=int(payload.get("selected_count", 0)),
        executed_count=int(payload.get("executed_count", 0)),
        reduced_count=int(payload.get("reduced_count", 0)),
        no_fill_count=int(payload.get("no_fill_count", 0) or 0),
        hard_blocked_count=int(payload.get("hard_blocked_count", 0)),
        rejected_count=int(
            payload.get("rejected_count", payload.get("rejected_ranking_count", 0))
        ),
        rejected_ranking_count=int(payload.get("rejected_ranking_count", 0)),
        phantom_count=int(payload.get("phantom_count", 0)),
        ce_net=float(payload.get("ce_net", 0.0)),
        expected_cost_mean=float(payload.get("expected_cost_mean", 0.0)),
        replay_expected_cost_model_mean=float(
            payload.get(
                "replay_expected_cost_model_mean", payload.get("expected_cost_mean", 0.0)
            )
        ),
        expected_total_cost_mean=_maybe_float(payload.get("expected_total_cost_mean")),
        realized_cost_mean=float(payload.get("realized_cost_mean", 0.0)),
        gross_return_mean=float(payload.get("gross_return_mean", 0.0)),
        gross_return_total=float(payload.get("gross_return_total", 0.0)),
        missing_realized_cost_count=int(payload.get("missing_realized_cost_count", 0)),
        executed_only_net_return=_maybe_float(payload.get("executed_only_net_return")),
        executed_only_net_return_status=str(
            payload.get(
                "executed_only_net_return_status",
                "EXECUTED_NET_RETURN_NOT_PROVEN",
            )
        ),
        initial_capital=_maybe_float(payload.get("initial_capital")),
        true_net_equity_curve=tuple(
            float(item) for item in (payload.get("true_net_equity_curve") or ())
        ),
        true_net_equity_max_drawdown=_maybe_float(
            payload.get("true_net_equity_max_drawdown")
        ),
        drawdown_proxy=float(payload.get("drawdown_proxy", 0.0)),
        non_execution_rate=float(
            payload.get(
                "non_execution_rate",
                1.0
                if int(payload.get("total_records", 0) or 0) <= 0
                else 1.0
                - (
                    float(payload.get("executed_count", 0) or 0)
                    / float(int(payload.get("total_records", 0) or 1))
                ),
            )
        ),
        fee_source_status=_normalize_fee_source_status(payload.get("fee_source_status")),
        fee_model_name=_maybe_str(payload.get("fee_model_name")),
        fee_rate_maker_bps=_maybe_float(payload.get("fee_rate_maker_bps")),
        fee_rate_taker_bps=_maybe_float(payload.get("fee_rate_taker_bps")),
        fee_currency=_maybe_str(payload.get("fee_currency")),
        fee_amount=_maybe_float(payload.get("fee_amount")),
        fee_bps=_maybe_float(payload.get("fee_bps")),
        fee_provenance_ref=_maybe_str(payload.get("fee_provenance_ref")),
        fee_input_hash=_maybe_str(payload.get("fee_input_hash")),
        fee_policy_version=_maybe_str(payload.get("fee_policy_version")),
        impact_source_status=_normalize_impact_source_status(
            payload.get("impact_source_status")
        ),
        impact_model_name=_maybe_str(payload.get("impact_model_name")),
        impact_bps=_maybe_float(payload.get("impact_bps")),
        impact_notional=_maybe_float(payload.get("impact_notional")),
        impact_depth_ref=_maybe_str(payload.get("impact_depth_ref")),
        impact_depth_level=_maybe_int(payload.get("impact_depth_level")),
        impact_provenance_ref=_maybe_str(payload.get("impact_provenance_ref")),
        impact_input_hash=_maybe_str(payload.get("impact_input_hash")),
        impact_policy_version=_maybe_str(payload.get("impact_policy_version")),
        book_depth_available=(
            bool(payload.get("book_depth_available"))
            if payload.get("book_depth_available") is not None
            else None
        ),
        book_depth_levels=_maybe_int(payload.get("book_depth_levels")),
        book_depth_source_status=_normalize_book_depth_source_status(
            payload.get("book_depth_source_status"),
            _maybe_int(payload.get("book_depth_levels")),
        ),
        book_depth_snapshot_count=_maybe_int(payload.get("book_depth_snapshot_count")),
        book_depth_event_count=_maybe_int(payload.get("book_depth_event_count")),
        book_depth_missing_count=_maybe_int(payload.get("book_depth_missing_count")),
        book_depth_staleness_status=str(
            payload.get("book_depth_staleness_status", "BOOK_DEPTH_NOT_PROVEN")
        ),
        impact_depth_level_used=_maybe_int(payload.get("impact_depth_level_used")),
        impact_depth_readiness_status=str(
            payload.get("impact_depth_readiness_status", "BOOK_DEPTH_NOT_PROVEN")
        ),
        shadow_extension_required=bool(payload.get("shadow_extension_required", True)),
        shadow_extension_reason=_maybe_str(payload.get("shadow_extension_reason")),
        minimum_shadow_days_required=_maybe_int(
            payload.get("minimum_shadow_days_required")
        ),
        shadow_extension_status=str(
            payload.get("shadow_extension_status", "MICRO_LIVE_BLOCKED_BY_DEPTH")
        ),
        cost_model_completeness_status=_normalize_cost_model_completeness_status(
            payload.get("cost_model_completeness_status")
        ),
        cost_readiness_reason_codes=tuple(
            str(item) for item in (payload.get("cost_readiness_reason_codes") or ())
        ),
        fill_ratio_source=str(payload.get("fill_ratio_source", "UNKNOWN")),
        fill_realism_status=_normalize_fill_realism_status(
            payload.get("fill_realism_status")
        ),
        fill_source_status=str(payload.get("fill_source_status", "FILL_SOURCE_NOT_PROVEN")),
        fill_model_name=_maybe_str(payload.get("fill_model_name")),
        fill_model_version=_maybe_str(payload.get("fill_model_version")),
        fill_ratio_expected=_maybe_float(payload.get("fill_ratio_expected")),
        fill_ratio_observed=_maybe_float(payload.get("fill_ratio_observed")),
        partial_fill_rate_expected=_maybe_float(
            payload.get("partial_fill_rate_expected")
        ),
        partial_fill_rate_observed=_maybe_float(
            payload.get("partial_fill_rate_observed")
        ),
        no_fill_rate_expected=_maybe_float(payload.get("no_fill_rate_expected")),
        no_fill_rate_observed=_maybe_float(payload.get("no_fill_rate_observed")),
        fill_latency_ms_expected=_maybe_float(payload.get("fill_latency_ms_expected")),
        fill_latency_ms_observed=_maybe_float(payload.get("fill_latency_ms_observed")),
        synthetic_fill_flag=bool(payload.get("synthetic_fill_flag", False)),
        measured_fill_flag=bool(payload.get("measured_fill_flag", False)),
        fill_provenance_ref=_maybe_str(payload.get("fill_provenance_ref")),
        fill_input_hash=_maybe_str(payload.get("fill_input_hash")),
        fill_policy_version=_maybe_str(payload.get("fill_policy_version")),
        realized_slippage_status=str(
            payload.get("realized_slippage_status", "NOT_PROVEN")
        ),
        cost_parity_status=_normalize_cost_parity_status(
            payload.get("cost_parity_status", payload.get("replay_live_cost_parity_status"))
        ),
        replay_live_cost_parity_status=_normalize_cost_parity_status(
            payload.get("replay_live_cost_parity_status")
        ),
        replay_cost_components=tuple(
            str(item) for item in (payload.get("replay_cost_components") or ())
        ),
        shadow_cost_components=tuple(
            str(item) for item in (payload.get("shadow_cost_components") or ())
        ),
        live_cost_components=tuple(
            str(item) for item in (payload.get("live_cost_components") or ())
        ),
        replay_fee_bps=_maybe_float(payload.get("replay_fee_bps")),
        shadow_fee_bps=_maybe_float(payload.get("shadow_fee_bps")),
        live_fee_bps=_maybe_float(payload.get("live_fee_bps")),
        replay_impact_bps=_maybe_float(payload.get("replay_impact_bps")),
        shadow_impact_bps=_maybe_float(payload.get("shadow_impact_bps")),
        live_impact_bps=_maybe_float(payload.get("live_impact_bps")),
        replay_slippage_bps=_maybe_float(payload.get("replay_slippage_bps")),
        shadow_slippage_bps=_maybe_float(payload.get("shadow_slippage_bps")),
        live_slippage_bps=_maybe_float(payload.get("live_slippage_bps")),
        replay_fill_ratio=_maybe_float(payload.get("replay_fill_ratio")),
        shadow_fill_ratio=_maybe_float(payload.get("shadow_fill_ratio")),
        live_fill_ratio=_maybe_float(payload.get("live_fill_ratio")),
        cost_drift_bps=_maybe_float(payload.get("cost_drift_bps")),
        cost_drift_status=str(payload.get("cost_drift_status", "NOT_PROVEN")),
        parity_sample_count=int(payload.get("parity_sample_count", 0)),
        parity_window_start=_maybe_str(payload.get("parity_window_start")),
        parity_window_end=_maybe_str(payload.get("parity_window_end")),
        parity_input_hash=_maybe_str(payload.get("parity_input_hash")),
        parity_policy_version=_maybe_str(payload.get("parity_policy_version")),
        small_capital_exclusion_rate=_maybe_float(
            payload.get("small_capital_exclusion_rate")
        ),
        small_capital_exclusion_status=str(
            payload.get("small_capital_exclusion_status", "NOT_PROVEN")
        ),
        small_capital_viability_status=str(
            payload.get("small_capital_viability_status", "BLOCKED_BY_BACKTEST")
        ),
        min_notional_viability_status=str(
            payload.get("min_notional_viability_status", "BLOCKED_BY_BACKTEST")
        ),
        capital_fragmentation_status=str(
            payload.get("capital_fragmentation_status", "NOT_PROVEN")
        ),
        sizing_doctrine=str(
            payload.get("sizing_doctrine", "FIXED_FRACTION_VOL_TARGET_CAPS")
        ),
        kelly_status=str(
            payload.get("kelly_status", "NOT_IMPLEMENTED_BY_DESIGN_FOR_NOW")
        ),
        kelly_reason=str(
            payload.get(
                "kelly_reason",
                "crypto spot small-capital / high cost / high uncertainty / future research",
            )
        ),
        multi_asset_risk_control_status=str(
            payload.get("multi_asset_risk_control_status", "BASELINE_CAPS_ONLY")
        ),
        covariance_model_status=str(
            payload.get("covariance_model_status", "NOT_IMPLEMENTED")
        ),
        true_net_equity_drawdown_status=str(
            payload.get(
                "true_net_equity_drawdown_status",
                "TRUE_NET_EQUITY_DRAWDOWN_NOT_PROVEN",
            )
        ),
        drawdown_proxy_promotion_grade=bool(
            payload.get("drawdown_proxy_promotion_grade", False)
        ),
        capital_bucket_profiles=capital_bucket_profiles,
        engine_promotion_artifacts=engine_promotion_artifacts,
        pair_promotion_artifacts=pair_promotion_artifacts,
        strategy_promotion_artifacts=strategy_promotion_artifacts,
        sample_size_survival_artifacts=sample_size_survival_artifacts,
        pair_aggregates=pairs,
        engine_aggregates=engines,
    )


def _maybe_float(value: object) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _maybe_int(value: object) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _maybe_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if text else None


__all__ = [
    "EngineAggregate",
    "PairAggregate",
    "ReplayMetricsSnapshot",
    "read_replay_metrics",
]
