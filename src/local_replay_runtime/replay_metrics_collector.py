"""Derived metrics for governed LOCAL_REPLAY artifact exports."""

from __future__ import annotations

from pydantic import BaseModel, Field

from interface_contracts.capital_profile_contracts import CapitalBucketProfile
from meta import build_dtr_summary
from meta_minimal.dtr_core.decision_state_encoder import DecisionState
from meta_minimal.dtr_core.dtr_record_builder import DTRRecord


_ENGINE_ROLE_BY_ID: dict[str, str] = {
    "engine_c": "Breakout / continuation engine with fake-breakout protection and toxic-flow veto/context.",
    "engine_d": "Re-entry / second-chance engine with first-episode linkage, anti-revenge, reformation, and realized-vol context.",
}
_ENGINE_SHARED_PHYSICS_MAPPING_STATUS_BY_ID: dict[str, str] = {
    "engine_c": "PARTIAL_BY_DESIGN",
    "engine_d": "PARTIAL_BY_DESIGN",
}
_FEE_SOURCE_EXPLICIT_STATUSES = {
    "FEE_SOURCE_PROVEN",
    "FEE_SOURCE_CONFIGURED",
    "FEE_SOURCE_EXCHANGE_METADATA",
    "EXPLICIT",
}
_IMPACT_SOURCE_DEPTH20_STATUSES = {
    "IMPACT_SOURCE_PROVEN",
    "IMPACT_SOURCE_DEPTH20_MODEL",
    "EXPLICIT",
}
_FILL_REALISM_PROVEN_STATUSES = {
    "FILL_REALISM_PROVEN",
    "FILL_REALISM_SHADOW_MEASURED",
    "MEASURED",
    "PROVEN",
}
_REPLAY_LIVE_PARITY_PROVEN_STATUSES = {"REPLAY_LIVE_COST_PARITY_PROVEN"}
_ATTEMPTED_EXECUTION_STATES = {
    DecisionState.EXECUTED,
    DecisionState.REDUCED,
    DecisionState.PHANTOM,
}
_CAPITAL_PROFILE_READY_STATUSES = {"CAPITAL_BUCKET_READY"}


class ReplayFeeProvenance(BaseModel, frozen=True):
    """Explicit replay fee provenance carried alongside aggregate economics."""

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


class ReplayImpactProvenance(BaseModel, frozen=True):
    """Explicit replay impact provenance carried alongside aggregate economics."""

    impact_source_status: str = "IMPACT_SOURCE_NOT_PROVEN"
    impact_model_name: str | None = None
    impact_bps: float | None = Field(default=None, ge=0.0)
    impact_notional: float | None = Field(default=None, ge=0.0)
    impact_depth_ref: str | None = None
    impact_depth_level: int | None = Field(default=None, ge=0)
    impact_provenance_ref: str | None = None
    impact_input_hash: str | None = None
    impact_policy_version: str | None = None


class ReplayBookDepthAvailability(BaseModel, frozen=True):
    """Governed order-book depth availability metadata for replay/shadow economics."""

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


class ReplayFillRealismEvidence(BaseModel, frozen=True):
    """Governed fill-realism evidence for replay/shadow economics."""

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
    fill_ratio_source: str = "UNKNOWN"


class ReplayCostParityEvidence(BaseModel, frozen=True):
    """Governed replay/shadow/live cost parity evidence."""

    cost_parity_status: str = "REPLAY_LIVE_COST_PARITY_BLOCKED_BY_TELEMETRY"
    execution_label_source: str = "REPLAY_PROXY_EXECUTION"
    fee_model_source: str = "REPLAY_PROXY"
    spread_model_source: str = "REPLAY_PROXY"
    slippage_model_source: str = "REPLAY_PROXY"
    partial_fill_model_source: str = "REPLAY_PROXY"
    adverse_selection_source: str = "REPLAY_PROXY"
    order_type_selection_source: str = "REPLAY_PROXY"
    venue_constraints_source: str = "REPLAY_PROXY"
    execution_fidelity_gap_codes: tuple[str, ...] = ()
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
    parity_sample_count: int = Field(default=0, ge=0)
    parity_window_start: str | None = None
    parity_window_end: str | None = None
    parity_input_hash: str | None = None
    parity_policy_version: str | None = None
    realized_slippage_status: str = "NOT_PROVEN"


def _derive_capital_profile_readiness_statuses(
    capital_bucket_profiles: tuple[CapitalBucketProfile, ...],
) -> tuple[str, str, str, float | None]:
    if not capital_bucket_profiles:
        return (
            "BLOCKED_BY_BACKTEST",
            "BLOCKED_BY_BACKTEST",
            "NOT_PROVEN",
            None,
        )
    small_buckets = tuple(
        profile
        for profile in capital_bucket_profiles
        if profile.capital_bucket in {400, 500}
    )
    basis = small_buckets or capital_bucket_profiles
    small_capital_status = (
        "MEASURED"
        if any(profile.promotion_status in _CAPITAL_PROFILE_READY_STATUSES for profile in basis)
        else (
            "BLOCKED_BY_BACKTEST"
            if any(
                profile.promotion_status == "CAPITAL_BUCKET_BLOCKED_BY_BACKTEST"
                for profile in basis
            )
            else "NOT_PROVEN"
        )
    )
    min_notional_status = (
        "MEASURED"
        if all(profile.min_notional_block_rate is not None for profile in basis)
        else "MIN_NOTIONAL_NOT_PROVEN"
    )
    fragmentation_status = (
        "MEASURED"
        if all(
            profile.capital_fragmentation_rate is not None
            or profile.pair_universe_too_wide_status != "NOT_PROVEN"
            for profile in basis
        )
        else "NOT_PROVEN"
    )
    exclusion_rates = tuple(
        profile.min_notional_block_rate
        for profile in basis
        if profile.min_notional_block_rate is not None
    )
    exclusion_rate = round(_mean(exclusion_rates), 6) if exclusion_rates else None
    return (
        small_capital_status,
        min_notional_status,
        fragmentation_status,
        exclusion_rate,
    )


class ReplayPairAggregate(BaseModel, frozen=True):
    """Per-pair aggregates exported from a governed local replay session."""

    pair: str
    record_count: int = Field(default=0, ge=0)
    selected_count: int = Field(default=0, ge=0)
    ce_net: float = 0.0
    expected_cost_mean: float = 0.0
    replay_expected_cost_model_mean: float = 0.0
    expected_total_cost_mean: float | None = None
    realized_cost_mean: float = 0.0
    gross_return_mean: float = 0.0
    fee_source_status: str = "FEE_SOURCE_NOT_PROVEN"
    impact_source_status: str = "IMPACT_SOURCE_NOT_PROVEN"
    cost_model_completeness_status: str = "COST_MODEL_NOT_PROVEN"
    execution_label_source: str = "REPLAY_PROXY_EXECUTION"
    fee_model_source: str = "REPLAY_PROXY"
    spread_model_source: str = "REPLAY_PROXY"
    slippage_model_source: str = "REPLAY_PROXY"
    partial_fill_model_source: str = "REPLAY_PROXY"
    adverse_selection_source: str = "REPLAY_PROXY"
    order_type_selection_source: str = "REPLAY_PROXY"
    venue_constraints_source: str = "REPLAY_PROXY"
    execution_fidelity_gap_codes: tuple[str, ...] = ()


class ReplayEngineAggregate(BaseModel, frozen=True):
    """Per-engine aggregates exported from a governed local replay session."""

    engine_id: str
    engine_role: str = ""
    shared_physics_mapping_status: str = "NOT_APPLICABLE"
    record_count: int = Field(default=0, ge=0)
    selected_count: int = Field(default=0, ge=0)
    hard_blocked_count: int = Field(default=0, ge=0)
    executed_count: int = Field(default=0, ge=0)
    reduced_count: int = Field(default=0, ge=0)
    rejected_count: int = Field(default=0, ge=0)
    no_fill_count: int | None = Field(default=None, ge=0)
    missing_realized_cost_count: int = Field(default=0, ge=0)
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
    replay_live_cost_parity_status: str = "REPLAY_LIVE_COST_PARITY_BLOCKED_BY_TELEMETRY"
    cost_parity_status: str = "REPLAY_LIVE_COST_PARITY_BLOCKED_BY_TELEMETRY"
    cost_drift_bps: float | None = None
    cost_drift_status: str = "NOT_PROVEN"
    parity_sample_count: int = Field(default=0, ge=0)
    execution_label_source: str = "REPLAY_PROXY_EXECUTION"
    fee_model_source: str = "REPLAY_PROXY"
    spread_model_source: str = "REPLAY_PROXY"
    slippage_model_source: str = "REPLAY_PROXY"
    partial_fill_model_source: str = "REPLAY_PROXY"
    adverse_selection_source: str = "REPLAY_PROXY"
    order_type_selection_source: str = "REPLAY_PROXY"
    venue_constraints_source: str = "REPLAY_PROXY"
    execution_fidelity_gap_codes: tuple[str, ...] = ()
    sample_size_survival_status: str = "NOT_PROVEN"
    engine_executed_only_net_return: float | None = None
    executed_only_net_return_status: str = "EXECUTED_NET_RETURN_NOT_PROVEN"
    engine_true_net_equity_max_drawdown: float | None = None
    true_net_equity_drawdown_status: str = "TRUE_NET_EQUITY_DRAWDOWN_NOT_PROVEN"
    shadow_confirmation_status: str = "NOT_PROVEN"
    promotion_status: str = "NOT_SHADOW_READY"


class ReplayMetricsSummary(BaseModel, frozen=True):
    """Top-level replay metrics summary suitable for artifact export."""

    total_records: int = Field(default=0, ge=0)
    total_opportunities: int = Field(default=0, ge=0)
    dtr_coverage: float = Field(default=0.0, ge=0.0)
    selected_count: int = Field(default=0, ge=0)
    executed_count: int = Field(default=0, ge=0)
    # Patch P0 #3 (2026-05-30) — executed_count counts BUCKET RECORDS (a single
    # candidate × N capital_buckets emits N records). Operator dashboard
    # previously showed "8 executed" without clarifying it was 2 candidates ×
    # 4 buckets. `executed_distinct_candidate_count` exposes the underlying
    # count of distinct candidate_ids that produced an executed bucket record.
    executed_distinct_candidate_count: int = Field(default=0, ge=0)
    reduced_count: int = Field(default=0, ge=0)
    no_fill_count: int | None = Field(default=None, ge=0)
    hard_blocked_count: int = Field(default=0, ge=0)
    rejected_ranking_count: int = Field(default=0, ge=0)
    rejected_count: int = Field(default=0, ge=0)
    phantom_count: int = Field(default=0, ge=0)
    missing_realized_cost_count: int = Field(default=0, ge=0)
    ce_net: float = 0.0
    expected_cost_mean: float = 0.0
    replay_expected_cost_model_mean: float = 0.0
    expected_total_cost_mean: float | None = None
    realized_cost_mean: float = 0.0
    gross_return_mean: float = 0.0
    gross_return_total: float = 0.0
    executed_only_net_return: float | None = None
    executed_only_net_return_status: str = "EXECUTED_NET_RETURN_NOT_PROVEN"
    initial_capital: float | None = None
    true_net_equity_curve: tuple[float, ...] = ()
    true_net_equity_max_drawdown: float | None = None
    drawdown_proxy: float = 0.0
    selected_execution_rate: float | None = None
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
    execution_label_source: str = "REPLAY_PROXY_EXECUTION"
    fee_model_source: str = "REPLAY_PROXY"
    spread_model_source: str = "REPLAY_PROXY"
    slippage_model_source: str = "REPLAY_PROXY"
    partial_fill_model_source: str = "REPLAY_PROXY"
    adverse_selection_source: str = "REPLAY_PROXY"
    order_type_selection_source: str = "REPLAY_PROXY"
    venue_constraints_source: str = "REPLAY_PROXY"
    execution_fidelity_gap_codes: tuple[str, ...] = ()
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
    parity_sample_count: int = Field(default=0, ge=0)
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
    pair_aggregates: tuple[ReplayPairAggregate, ...] = ()
    engine_aggregates: tuple[ReplayEngineAggregate, ...] = ()


_EXECUTED_STATES = {
    DecisionState.EXECUTED,
    DecisionState.REDUCED,
}


def _drawdown_proxy(records: tuple[DTRRecord, ...]) -> float:
    running = 0.0
    peak = 0.0
    worst = 0.0
    for record in records:
        running += record.gross_return
        peak = max(peak, running)
        worst = min(worst, running - peak)
    return abs(worst)


def _mean(values: tuple[float, ...]) -> float:
    return sum(values) / len(values) if values else 0.0


def _normalize_fee_source_status(status: str | None) -> str:
    resolved = str(status or "FEE_SOURCE_NOT_PROVEN")
    if resolved == "NOT_PROVEN":
        return "FEE_SOURCE_NOT_PROVEN"
    if resolved == "MISSING":
        return "FEE_SOURCE_MISSING"
    if resolved == "EXPLICIT":
        return "FEE_SOURCE_PROVEN"
    return resolved


def _normalize_impact_source_status(
    status: str | None,
    *,
    depth_levels: int | None = None,
    book_depth_source_status: str | None = None,
) -> str:
    resolved = str(status or "IMPACT_SOURCE_NOT_PROVEN")
    if resolved == "NOT_PROVEN":
        resolved = "IMPACT_SOURCE_NOT_PROVEN"
    elif resolved == "MISSING":
        resolved = "IMPACT_SOURCE_MISSING"
    elif resolved == "EXPLICIT":
        resolved = "IMPACT_SOURCE_PROVEN"
    normalized_book_status = _normalize_book_depth_source_status(
        book_depth_source_status,
        levels=depth_levels,
    )
    if normalized_book_status == "BOOK_DEPTH20_AVAILABLE":
        return resolved if resolved == "IMPACT_SOURCE_PROVEN" else "IMPACT_SOURCE_DEPTH20_MODEL"
    if normalized_book_status == "BOOK_LIMITED_DEPTH_AVAILABLE":
        return "IMPACT_SOURCE_LIMITED_DEPTH_MODEL"
    if normalized_book_status == "BOOK_TOP_OF_BOOK_ONLY":
        return "IMPACT_SOURCE_TOP_OF_BOOK_PROXY"
    if normalized_book_status == "BOOK_DEPTH_MISSING":
        return "IMPACT_SOURCE_MISSING"
    return "IMPACT_SOURCE_NOT_PROVEN"


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
        "NOT_PROVEN": "REPLAY_LIVE_COST_PARITY_BLOCKED_BY_TELEMETRY",
        "MISSING": "REPLAY_LIVE_COST_PARITY_MISSING",
        "MEASURED": "REPLAY_LIVE_COST_PARITY_PARTIAL",
        "PROVEN": "REPLAY_LIVE_COST_PARITY_PARTIAL",
        "WITHIN_TOLERANCE": "REPLAY_LIVE_COST_PARITY_PARTIAL",
        "WITHIN_PRUDENT_TOLERANCE": "REPLAY_LIVE_COST_PARITY_PARTIAL",
    }
    return mapping.get(resolved, resolved)


def _normalize_book_depth_source_status(
    status: str | None,
    *,
    levels: int | None = None,
) -> str:
    resolved = str(status or "BOOK_DEPTH_NOT_PROVEN")
    if resolved == "BOOK_DEPTH_STALE":
        return "BOOK_DEPTH_STALE"
    if levels is None:
        return "BOOK_DEPTH_MISSING" if resolved == "BOOK_DEPTH_MISSING" else "BOOK_DEPTH_NOT_PROVEN"
    if levels <= 0:
        return "BOOK_DEPTH_MISSING"
    if levels == 1:
        return "BOOK_TOP_OF_BOOK_ONLY"
    if levels < 20:
        return "BOOK_LIMITED_DEPTH_AVAILABLE"
    return "BOOK_DEPTH20_AVAILABLE"


def _normalize_fill_source_status(status: str | None) -> str:
    resolved = str(status or "FILL_SOURCE_NOT_PROVEN")
    if resolved == "NOT_PROVEN":
        return "FILL_SOURCE_NOT_PROVEN"
    if resolved == "MISSING":
        return "FILL_SOURCE_MISSING"
    return resolved


def _is_explicit_fee_source(status: str) -> bool:
    return _normalize_fee_source_status(status) in _FEE_SOURCE_EXPLICIT_STATUSES


def _is_depth20_promotion_grade(
    *,
    impact_source_status: str,
    book_depth_source_status: str,
    impact_depth_readiness_status: str,
) -> bool:
    return (
        book_depth_source_status == "BOOK_DEPTH20_AVAILABLE"
        and impact_depth_readiness_status == "DEPTH20_AVAILABLE"
        and impact_source_status in _IMPACT_SOURCE_DEPTH20_STATUSES
    )


def _is_fill_realism_proven(status: str) -> bool:
    return _normalize_fill_realism_status(status) in _FILL_REALISM_PROVEN_STATUSES


def _is_replay_live_cost_parity_proven(status: str) -> bool:
    return _normalize_cost_parity_status(status) in _REPLAY_LIVE_PARITY_PROVEN_STATUSES


def _attempted_fill_ratio(record: DTRRecord) -> float | None:
    if record.decision_state not in _ATTEMPTED_EXECUTION_STATES:
        return None
    if record.candidate_size > 0.0:
        return max(0.0, min(1.0, record.final_size / record.candidate_size))
    if record.decision_state == DecisionState.EXECUTED:
        return 1.0
    if record.decision_state == DecisionState.PHANTOM:
        return 0.0
    return None


def _normalize_book_depth_availability(
    book_depth: ReplayBookDepthAvailability | None,
    impact_meta: ReplayImpactProvenance,
) -> tuple[ReplayBookDepthAvailability, str]:
    depth = book_depth or ReplayBookDepthAvailability(
        book_depth_levels=impact_meta.impact_depth_level,
        impact_depth_level_used=impact_meta.impact_depth_level,
    )
    levels = depth.book_depth_levels
    if levels is None:
        levels = impact_meta.impact_depth_level
    book_depth_source_status = _normalize_book_depth_source_status(
        depth.book_depth_source_status,
        levels=levels,
    )
    impact_depth_level_used = (
        depth.impact_depth_level_used
        if depth.impact_depth_level_used is not None
        else levels
    )
    if book_depth_source_status == "BOOK_DEPTH20_AVAILABLE":
        impact_depth_readiness_status = "DEPTH20_AVAILABLE"
        shadow_extension_status = "SHADOW_STANDARD_30D"
        shadow_extension_required = False
        shadow_extension_reason = "SHADOW_STANDARD_30D"
        minimum_shadow_days_required = 30
    elif book_depth_source_status == "BOOK_LIMITED_DEPTH_AVAILABLE":
        impact_depth_readiness_status = "LIMITED_DEPTH_PARTIAL"
        if levels is not None and levels <= 5:
            shadow_extension_status = "SHADOW_EXTENDED_60D"
            minimum_shadow_days_required = 60
        else:
            shadow_extension_status = "SHADOW_EXTENDED_45D"
            minimum_shadow_days_required = 45
        shadow_extension_required = True
        shadow_extension_reason = "SHADOW_EXTENDED_REQUIRED"
    elif book_depth_source_status == "BOOK_TOP_OF_BOOK_ONLY":
        impact_depth_readiness_status = "TOP_OF_BOOK_PROXY_ONLY"
        shadow_extension_status = "SHADOW_DIAGNOSTIC_ONLY"
        shadow_extension_required = True
        shadow_extension_reason = "MICRO_LIVE_BLOCKED_BY_DEPTH"
        minimum_shadow_days_required = 60
    elif book_depth_source_status == "BOOK_DEPTH_STALE":
        impact_depth_readiness_status = "BOOK_DEPTH_STALE"
        shadow_extension_status = "MICRO_LIVE_BLOCKED_BY_DEPTH"
        shadow_extension_required = True
        shadow_extension_reason = "BOOK_DEPTH_STALE"
        minimum_shadow_days_required = None
    else:
        impact_depth_readiness_status = book_depth_source_status
        shadow_extension_status = "MICRO_LIVE_BLOCKED_BY_DEPTH"
        shadow_extension_required = True
        shadow_extension_reason = "NO_PROMOTION_GRADE_REPLAY_IMPACT_PROOF"
        minimum_shadow_days_required = None
    normalized = depth.model_copy(
        update={
            "book_depth_available": book_depth_source_status
            in {
                "BOOK_DEPTH20_AVAILABLE",
                "BOOK_LIMITED_DEPTH_AVAILABLE",
                "BOOK_TOP_OF_BOOK_ONLY",
                "BOOK_DEPTH_STALE",
            },
            "book_depth_levels": levels,
            "book_depth_source_status": book_depth_source_status,
            "book_depth_snapshot_count": depth.book_depth_snapshot_count,
            "book_depth_event_count": depth.book_depth_event_count,
            "book_depth_missing_count": depth.book_depth_missing_count,
            "book_depth_staleness_status": (
                "BOOK_DEPTH_STALE"
                if book_depth_source_status == "BOOK_DEPTH_STALE"
                else (
                    depth.book_depth_staleness_status
                    if depth.book_depth_staleness_status != "BOOK_DEPTH_NOT_PROVEN"
                    else book_depth_source_status
                )
            ),
            "impact_depth_level_used": impact_depth_level_used,
            "impact_depth_readiness_status": impact_depth_readiness_status,
            "shadow_extension_required": shadow_extension_required,
            "shadow_extension_reason": shadow_extension_reason,
            "minimum_shadow_days_required": minimum_shadow_days_required,
            "shadow_extension_status": shadow_extension_status,
        }
    )
    normalized_impact_source_status = _normalize_impact_source_status(
        impact_meta.impact_source_status,
        depth_levels=normalized.book_depth_levels,
        book_depth_source_status=normalized.book_depth_source_status,
    )
    return normalized, normalized_impact_source_status


def _derive_fill_realism_from_records(
    records: tuple[DTRRecord, ...],
    *,
    fill_realism: ReplayFillRealismEvidence | None = None,
) -> ReplayFillRealismEvidence:
    attempted_records = tuple(
        record for record in records if record.decision_state in _ATTEMPTED_EXECUTION_STATES
    )
    ratios = tuple(
        ratio
        for ratio in (_attempted_fill_ratio(record) for record in attempted_records)
        if ratio is not None
    )
    attempted_count = len(attempted_records)
    reduced_count = sum(
        1 for record in attempted_records if record.decision_state == DecisionState.REDUCED
    )
    no_fill_count = sum(
        1 for record in attempted_records if record.decision_state == DecisionState.PHANTOM
    )
    default_status = (
        "FILL_REALISM_MODEL_ONLY" if attempted_count > 0 else "FILL_REALISM_NOT_PROVEN"
    )
    default_source_status = (
        "FILL_SOURCE_REPLAY_MODEL" if attempted_count > 0 else "FILL_SOURCE_NOT_PROVEN"
    )
    default_model_name = "shadow_execution_simulator_prudent_replay" if attempted_count > 0 else None
    default_model_version = "shadow_execution_simulator.v1" if attempted_count > 0 else None
    base = fill_realism or ReplayFillRealismEvidence()
    normalized_status = _normalize_fill_realism_status(
        base.fill_realism_status if fill_realism is not None else default_status
    )
    normalized_source_status = _normalize_fill_source_status(
        base.fill_source_status if fill_realism is not None else default_source_status
    )
    measured_fill_flag = bool(base.measured_fill_flag) and normalized_status in {
        "FILL_REALISM_PROVEN",
        "FILL_REALISM_SHADOW_MEASURED",
    }
    synthetic_fill_flag = bool(base.synthetic_fill_flag)
    if synthetic_fill_flag:
        measured_fill_flag = False
    return base.model_copy(
        update={
            "fill_realism_status": normalized_status,
            "fill_source_status": normalized_source_status,
            "fill_model_name": base.fill_model_name or default_model_name,
            "fill_model_version": base.fill_model_version or default_model_version,
            "fill_ratio_expected": (
                base.fill_ratio_expected
                if base.fill_ratio_expected is not None
                else (round(_mean(ratios), 6) if ratios else None)
            ),
            "fill_ratio_observed": base.fill_ratio_observed,
            "partial_fill_rate_expected": (
                base.partial_fill_rate_expected
                if base.partial_fill_rate_expected is not None
                else (round(reduced_count / attempted_count, 6) if attempted_count else None)
            ),
            "partial_fill_rate_observed": base.partial_fill_rate_observed,
            "no_fill_rate_expected": (
                base.no_fill_rate_expected
                if base.no_fill_rate_expected is not None
                else (round(no_fill_count / attempted_count, 6) if attempted_count else None)
            ),
            "no_fill_rate_observed": base.no_fill_rate_observed,
            "fill_latency_ms_expected": base.fill_latency_ms_expected,
            "fill_latency_ms_observed": base.fill_latency_ms_observed,
            "synthetic_fill_flag": synthetic_fill_flag,
            "measured_fill_flag": measured_fill_flag,
            "fill_ratio_source": (
                base.fill_ratio_source
                if base.fill_ratio_source != "UNKNOWN"
                else ("REPLAY_MODEL" if attempted_count > 0 else "UNKNOWN")
            ),
        }
    )


def _resolve_cost_parity_evidence(
    cost_parity: ReplayCostParityEvidence | None,
    *,
    fee_meta: ReplayFeeProvenance,
    impact_meta: ReplayImpactProvenance,
    fill_meta: ReplayFillRealismEvidence,
    records: tuple[DTRRecord, ...],
) -> ReplayCostParityEvidence:
    replay_cost_components: list[str] = ["expected_cost_total"]
    if fee_meta.fee_bps is not None:
        replay_cost_components.append("fee_bps")
    if impact_meta.impact_bps is not None:
        replay_cost_components.append("impact_bps")
    if any(record.expected_cost > 0.0 for record in records):
        replay_cost_components.append("expected_cost_component")
    if fill_meta.fill_ratio_expected is not None:
        replay_cost_components.append("fill_ratio_expected")
    base = cost_parity or ReplayCostParityEvidence()
    normalized_status = _normalize_cost_parity_status(base.cost_parity_status)
    has_shadow_telemetry = bool(base.shadow_cost_components) or any(
        value is not None
        for value in (
            base.shadow_fee_bps,
            base.shadow_impact_bps,
            base.shadow_slippage_bps,
            base.shadow_fill_ratio,
        )
    )
    has_live_telemetry = bool(base.live_cost_components) or any(
        value is not None
        for value in (
            base.live_fee_bps,
            base.live_impact_bps,
            base.live_slippage_bps,
            base.live_fill_ratio,
        )
    )
    if normalized_status == "REPLAY_LIVE_COST_PARITY_PROVEN" and not (
        has_live_telemetry and base.parity_sample_count > 0
    ):
        normalized_status = "REPLAY_LIVE_COST_PARITY_NOT_PROVEN"
    elif normalized_status == "REPLAY_SHADOW_COST_PARITY_PROVEN" and not (
        has_shadow_telemetry and base.parity_sample_count > 0
    ):
        normalized_status = "REPLAY_LIVE_COST_PARITY_NOT_PROVEN"
    elif normalized_status == "REPLAY_LIVE_COST_PARITY_PARTIAL" and not (
        has_shadow_telemetry or has_live_telemetry
    ):
        normalized_status = "REPLAY_LIVE_COST_PARITY_BLOCKED_BY_TELEMETRY"
    if normalized_status not in {
        "REPLAY_LIVE_COST_PARITY_PROVEN",
        "REPLAY_SHADOW_COST_PARITY_PROVEN",
        "REPLAY_LIVE_COST_PARITY_PARTIAL",
        "REPLAY_LIVE_COST_PARITY_BLOCKED_BY_TELEMETRY",
        "REPLAY_LIVE_COST_PARITY_NOT_PROVEN",
        "REPLAY_LIVE_COST_PARITY_MISSING",
    }:
        normalized_status = "REPLAY_LIVE_COST_PARITY_BLOCKED_BY_TELEMETRY"
    return base.model_copy(
        update={
            "cost_parity_status": normalized_status,
            "replay_cost_components": base.replay_cost_components or tuple(replay_cost_components),
            "replay_fee_bps": (
                base.replay_fee_bps if base.replay_fee_bps is not None else fee_meta.fee_bps
            ),
            "replay_impact_bps": (
                base.replay_impact_bps if base.replay_impact_bps is not None else impact_meta.impact_bps
            ),
            "replay_fill_ratio": (
                base.replay_fill_ratio
                if base.replay_fill_ratio is not None
                else fill_meta.fill_ratio_expected
            ),
            "cost_drift_status": (
                base.cost_drift_status
                if base.cost_drift_bps is not None or base.cost_drift_status != "NOT_PROVEN"
                else "NOT_PROVEN"
            ),
        }
    )


def _build_cost_readiness_reason_codes(
    *,
    fee_source_status: str,
    impact_source_status: str,
    book_depth_source_status: str,
    impact_depth_readiness_status: str,
    fill_realism_status: str,
    cost_parity_status: str,
    shadow_extension_required: bool,
    shadow_extension_status: str,
    realized_cost_source_present: bool,
) -> tuple[str, ...]:
    reason_codes: list[str] = []
    if not _is_explicit_fee_source(fee_source_status):
        reason_codes.append("FEE_SOURCE_NOT_PROVEN")
    if not _is_depth20_promotion_grade(
        impact_source_status=impact_source_status,
        book_depth_source_status=book_depth_source_status,
        impact_depth_readiness_status=impact_depth_readiness_status,
    ):
        reason_codes.append("IMPACT_SOURCE_NOT_PROVEN")
    if book_depth_source_status == "BOOK_LIMITED_DEPTH_AVAILABLE":
        reason_codes.append("LIMITED_DEPTH_PARTIAL")
    elif book_depth_source_status == "BOOK_TOP_OF_BOOK_ONLY":
        reason_codes.extend(("TOP_OF_BOOK_PROXY_ONLY", "MICRO_LIVE_BLOCKED_BY_DEPTH"))
    elif book_depth_source_status == "BOOK_DEPTH_MISSING":
        reason_codes.append("BOOK_DEPTH_MISSING")
    elif book_depth_source_status == "BOOK_DEPTH_STALE":
        reason_codes.append("BOOK_DEPTH_STALE")
    elif book_depth_source_status == "BOOK_DEPTH_NOT_PROVEN":
        reason_codes.append("BOOK_DEPTH_NOT_PROVEN")
    if shadow_extension_required and shadow_extension_status != "SHADOW_STANDARD_30D":
        reason_codes.append("SHADOW_EXTENDED_REQUIRED")
    if not _is_fill_realism_proven(fill_realism_status):
        reason_codes.append("FILL_REALISM_NOT_PROVEN")
    if not _is_replay_live_cost_parity_proven(cost_parity_status):
        reason_codes.append("REPLAY_LIVE_COST_PARITY_NOT_PROVEN")
    if not realized_cost_source_present:
        reason_codes.append("REALIZED_COST_SOURCE_NOT_PROVEN")
    return tuple(reason_codes)


def _derive_cost_model_completeness_status(
    *,
    fee_source_status: str,
    impact_source_status: str,
    book_depth_source_status: str,
    impact_depth_readiness_status: str,
    fill_realism_status: str,
    cost_parity_status: str,
    shadow_extension_required: bool,
    shadow_extension_status: str,
    realized_cost_source_present: bool,
) -> tuple[str, tuple[str, ...]]:
    reason_codes = _build_cost_readiness_reason_codes(
        fee_source_status=fee_source_status,
        impact_source_status=impact_source_status,
        book_depth_source_status=book_depth_source_status,
        impact_depth_readiness_status=impact_depth_readiness_status,
        fill_realism_status=fill_realism_status,
        cost_parity_status=cost_parity_status,
        shadow_extension_required=shadow_extension_required,
        shadow_extension_status=shadow_extension_status,
        realized_cost_source_present=realized_cost_source_present,
    )
    if not _is_explicit_fee_source(fee_source_status):
        return "COST_MODEL_PARTIAL_FEE_MISSING", reason_codes
    if not _is_depth20_promotion_grade(
        impact_source_status=impact_source_status,
        book_depth_source_status=book_depth_source_status,
        impact_depth_readiness_status=impact_depth_readiness_status,
    ):
        return "COST_MODEL_PARTIAL_IMPACT_MISSING", reason_codes
    if not _is_fill_realism_proven(fill_realism_status):
        return "COST_MODEL_PARTIAL_FILL_REALISM_MISSING", reason_codes
    if not _is_replay_live_cost_parity_proven(cost_parity_status):
        return "COST_MODEL_PARTIAL_REPLAY_LIVE_PARITY_MISSING", reason_codes
    if shadow_extension_required and shadow_extension_status != "SHADOW_STANDARD_30D":
        return "COST_MODEL_PARTIAL_IMPACT_MISSING", reason_codes
    if not realized_cost_source_present:
        return "COST_MODEL_NOT_PROVEN", reason_codes
    return "COST_MODEL_COMPLETE", reason_codes


def _executed_records(records: tuple[DTRRecord, ...]) -> tuple[DTRRecord, ...]:
    return tuple(record for record in records if record.decision_state in _EXECUTED_STATES)


def _has_proven_realized_total_cost(record: DTRRecord) -> bool:
    # Zero realized cost remains conservative on this rail: if provenance is not explicit,
    # it must not silently read as a measured zero.
    return record.realized_cost > 0.0


def _executed_only_net_return(
    records: tuple[DTRRecord, ...],
) -> tuple[float | None, str, int]:
    executed_records = _executed_records(records)
    if not executed_records:
        return None, "EXECUTED_NET_RETURN_INSUFFICIENT_EXECUTIONS", 0
    missing_realized_cost_count = sum(
        1 for record in executed_records if not _has_proven_realized_total_cost(record)
    )
    if missing_realized_cost_count > 0:
        return (
            None,
            "EXECUTED_NET_RETURN_MISSING_REALIZED_COST",
            missing_realized_cost_count,
        )
    return (
        round(
            sum(record.gross_return - record.realized_cost for record in executed_records),
            6,
        ),
        "EXECUTED_NET_RETURN_PROVEN",
        0,
    )


def _guard_executed_only_return_status(
    value: float | None,
    status: str,
    *,
    cost_model_completeness_status: str,
) -> tuple[float | None, str]:
    if (
        value is not None
        and status == "EXECUTED_NET_RETURN_PROVEN"
        and cost_model_completeness_status != "COST_MODEL_COMPLETE"
    ):
        return value, "EXECUTED_NET_RETURN_NOT_PROVEN"
    return value, status


def _true_net_equity_drawdown(
    records: tuple[DTRRecord, ...],
    *,
    initial_capital: float | None,
    executed_only_net_return_status: str,
) -> tuple[tuple[float, ...], float | None, str]:
    if initial_capital is None or initial_capital <= 0.0:
        return (), None, "TRUE_NET_EQUITY_DRAWDOWN_MISSING_CAPITAL"
    executed_records = _executed_records(records)
    if not executed_records:
        return (), None, "TRUE_NET_EQUITY_DRAWDOWN_INSUFFICIENT_EXECUTIONS"
    if executed_only_net_return_status != "EXECUTED_NET_RETURN_PROVEN":
        return (), None, "TRUE_NET_EQUITY_DRAWDOWN_MISSING_EXECUTED_PNL"
    ordered_records = tuple(
        sorted(executed_records, key=lambda record: (record.timestamp, record.dtr_id))
    )
    equity = float(initial_capital)
    running_peak = equity
    max_drawdown = 0.0
    curve: list[float] = []
    for record in ordered_records:
        equity += record.gross_return - record.realized_cost
        curve.append(round(equity, 6))
        running_peak = max(running_peak, equity)
        if running_peak > 0.0:
            drawdown = max(0.0, (running_peak - equity) / running_peak)
            max_drawdown = max(max_drawdown, drawdown)
    return tuple(curve), round(max_drawdown, 6), "TRUE_NET_EQUITY_DRAWDOWN_PROVEN"


def build_replay_metrics_summary(
    records: tuple[DTRRecord, ...],
    *,
    total_opportunities: int,
    initial_capital: float | None = None,
    fee_provenance: ReplayFeeProvenance | None = None,
    impact_provenance: ReplayImpactProvenance | None = None,
    book_depth_availability: ReplayBookDepthAvailability | None = None,
    fill_realism: ReplayFillRealismEvidence | None = None,
    cost_parity: ReplayCostParityEvidence | None = None,
    capital_bucket_profiles: tuple[CapitalBucketProfile, ...] = (),
) -> ReplayMetricsSummary:
    """Build replay metrics directly from governed DTR records."""

    dtr_summary = build_dtr_summary(records, total_opportunities=total_opportunities)
    selected_states = {
        DecisionState.SELECTED,
        DecisionState.REDUCED,
        DecisionState.PHANTOM,
        DecisionState.EXECUTED,
    }
    pair_groups: dict[str, list[DTRRecord]] = {}
    engine_groups: dict[str, list[DTRRecord]] = {}
    for record in records:
        pair_groups.setdefault(record.pair, []).append(record)
        engine_groups.setdefault(record.engine_id, []).append(record)

    total_records = len(records)
    selected_count = sum(1 for record in records if record.decision_state in selected_states)
    executed_count = sum(
        1 for record in records if record.decision_state == DecisionState.EXECUTED
    )
    # Patch P0 #3 (2026-05-30) — `executed_count` counts BUCKET RECORDS: one
    # candidate emits one record per capital_bucket. Distinct candidates are
    # keyed by (pair, engine_id, timestamp), which is stable across buckets
    # (only capital_bucket / dtr_id differ for the same candidate). This lets
    # the dashboard show e.g. "8 records = 2 distinct candidates × 4 buckets".
    executed_distinct_candidate_count = len(
        {
            (record.pair, record.engine_id, record.timestamp)
            for record in records
            if record.decision_state == DecisionState.EXECUTED
        }
    )
    reduced_count = sum(
        1 for record in records if record.decision_state == DecisionState.REDUCED
    )
    no_fill_count = sum(
        1 for record in records if record.decision_state == DecisionState.PHANTOM
    )
    normalized_capital_bucket_profiles = tuple(
        sorted(capital_bucket_profiles, key=lambda item: item.capital_bucket)
    )
    fee_meta = fee_provenance or ReplayFeeProvenance()
    impact_meta = impact_provenance or ReplayImpactProvenance()
    normalized_depth, normalized_impact_source_status = _normalize_book_depth_availability(
        book_depth_availability,
        impact_meta,
    )
    (
        small_capital_viability_status,
        min_notional_viability_status,
        capital_fragmentation_status,
        small_capital_exclusion_rate,
    ) = _derive_capital_profile_readiness_statuses(normalized_capital_bucket_profiles)
    fill_meta = _derive_fill_realism_from_records(records, fill_realism=fill_realism)
    cost_parity_meta = _resolve_cost_parity_evidence(
        cost_parity,
        fee_meta=fee_meta,
        impact_meta=impact_meta,
        fill_meta=fill_meta,
        records=records,
    )
    fee_source_status = _normalize_fee_source_status(fee_meta.fee_source_status)
    expected_cost_mean = round(_mean(tuple(record.expected_cost for record in records)), 6)
    executed_only_net_return, raw_executed_only_net_return_status, missing_realized_cost_count = (
        _executed_only_net_return(records)
    )
    realized_cost_source_present = (
        (executed_count + reduced_count) > 0 and missing_realized_cost_count == 0
    )
    cost_model_completeness_status, cost_readiness_reason_codes = (
        _derive_cost_model_completeness_status(
            fee_source_status=fee_source_status,
            impact_source_status=normalized_impact_source_status,
            book_depth_source_status=normalized_depth.book_depth_source_status,
            impact_depth_readiness_status=normalized_depth.impact_depth_readiness_status,
            fill_realism_status=fill_meta.fill_realism_status,
            cost_parity_status=cost_parity_meta.cost_parity_status,
            shadow_extension_required=normalized_depth.shadow_extension_required,
            shadow_extension_status=normalized_depth.shadow_extension_status,
            realized_cost_source_present=realized_cost_source_present,
        )
    )
    executed_only_net_return, executed_only_net_return_status = _guard_executed_only_return_status(
        executed_only_net_return,
        raw_executed_only_net_return_status,
        cost_model_completeness_status=cost_model_completeness_status,
    )
    (
        true_net_equity_curve,
        true_net_equity_max_drawdown,
        true_net_equity_drawdown_status,
    ) = _true_net_equity_drawdown(
        records,
        initial_capital=initial_capital,
        executed_only_net_return_status=executed_only_net_return_status,
    )

    pair_aggregates = tuple(
        ReplayPairAggregate(
            pair=pair,
            record_count=len(group),
            selected_count=sum(1 for record in group if record.decision_state in selected_states),
            ce_net=round(sum(record.ce_expected for record in group), 6),
            expected_cost_mean=round(_mean(tuple(record.expected_cost for record in group)), 6),
            replay_expected_cost_model_mean=round(
                _mean(tuple(record.expected_cost for record in group)),
                6,
            ),
            expected_total_cost_mean=None,
            realized_cost_mean=round(_mean(tuple(record.realized_cost for record in group)), 6),
            gross_return_mean=round(_mean(tuple(record.gross_return for record in group)), 6),
            fee_source_status=fee_source_status,
            impact_source_status=normalized_impact_source_status,
            cost_model_completeness_status=cost_model_completeness_status,
            execution_label_source=cost_parity_meta.execution_label_source,
            fee_model_source=cost_parity_meta.fee_model_source,
            spread_model_source=cost_parity_meta.spread_model_source,
            slippage_model_source=cost_parity_meta.slippage_model_source,
            partial_fill_model_source=cost_parity_meta.partial_fill_model_source,
            adverse_selection_source=cost_parity_meta.adverse_selection_source,
            order_type_selection_source=cost_parity_meta.order_type_selection_source,
            venue_constraints_source=cost_parity_meta.venue_constraints_source,
            execution_fidelity_gap_codes=cost_parity_meta.execution_fidelity_gap_codes,
        )
        for pair, group in sorted(pair_groups.items())
    )

    engine_rows: list[ReplayEngineAggregate] = []
    for engine_id, group in sorted(engine_groups.items()):
        group_records = tuple(group)
        (
            engine_executed_only_net_return,
            raw_engine_executed_only_net_return_status,
            engine_missing_realized_cost_count,
        ) = _executed_only_net_return(group_records)
        (
            engine_executed_only_net_return,
            engine_executed_only_net_return_status,
        ) = _guard_executed_only_return_status(
            engine_executed_only_net_return,
            raw_engine_executed_only_net_return_status,
            cost_model_completeness_status=cost_model_completeness_status,
        )
        (
            _engine_true_curve,
            engine_true_net_equity_max_drawdown,
            engine_true_net_equity_drawdown_status,
        ) = _true_net_equity_drawdown(
            group_records,
            initial_capital=initial_capital,
            executed_only_net_return_status=engine_executed_only_net_return_status,
        )
        engine_rows.append(
            ReplayEngineAggregate(
                engine_id=engine_id,
                engine_role=_ENGINE_ROLE_BY_ID.get(engine_id, ""),
                shared_physics_mapping_status=_ENGINE_SHARED_PHYSICS_MAPPING_STATUS_BY_ID.get(
                    engine_id,
                    "NOT_APPLICABLE",
                ),
                record_count=len(group_records),
                selected_count=sum(
                    1 for record in group_records if record.decision_state in selected_states
                ),
                hard_blocked_count=sum(
                    1
                    for record in group_records
                    if record.decision_state == DecisionState.HARD_BLOCKED
                ),
                executed_count=sum(
                    1
                    for record in group_records
                    if record.decision_state == DecisionState.EXECUTED
                ),
                reduced_count=sum(
                    1
                    for record in group_records
                    if record.decision_state == DecisionState.REDUCED
                ),
                rejected_count=sum(
                    1
                    for record in group_records
                    if record.decision_state == DecisionState.REJECTED_RANKING
                ),
                no_fill_count=sum(
                    1
                    for record in group_records
                    if record.decision_state == DecisionState.PHANTOM
                ),
                missing_realized_cost_count=engine_missing_realized_cost_count,
                execution_rate=(
                    round(
                        sum(
                            1
                            for record in group_records
                            if record.decision_state == DecisionState.EXECUTED
                        )
                        / len(group_records),
                        6,
                    )
                    if group_records
                    else None
                ),
                partial_fill_rate=(
                    round(
                        sum(
                            1
                            for record in group_records
                            if record.decision_state == DecisionState.REDUCED
                        )
                        / len(group_records),
                        6,
                    )
                    if group_records
                    else None
                ),
                no_fill_rate=(
                    round(
                        sum(
                            1
                            for record in group_records
                            if record.decision_state == DecisionState.PHANTOM
                        )
                        / len(group_records),
                        6,
                    )
                    if group_records
                    else None
                ),
                ce_net=round(sum(record.ce_expected for record in group_records), 6),
                expected_cost_mean=round(
                    _mean(tuple(record.expected_cost for record in group_records)),
                    6,
                ),
                replay_expected_cost_model_mean=round(
                    _mean(tuple(record.expected_cost for record in group_records)),
                    6,
                ),
                realized_cost_mean=round(
                    _mean(tuple(record.realized_cost for record in group_records)),
                    6,
                ),
                gross_return_mean=round(
                    _mean(tuple(record.gross_return for record in group_records)),
                    6,
                ),
                fee_source_status=fee_source_status,
                impact_source_status=normalized_impact_source_status,
                cost_model_completeness_status=cost_model_completeness_status,
                book_depth_source_status=normalized_depth.book_depth_source_status,
                book_depth_levels=normalized_depth.book_depth_levels,
                impact_depth_level_used=normalized_depth.impact_depth_level_used,
                impact_depth_readiness_status=normalized_depth.impact_depth_readiness_status,
                shadow_extension_required=normalized_depth.shadow_extension_required,
                shadow_extension_reason=normalized_depth.shadow_extension_reason,
                minimum_shadow_days_required=normalized_depth.minimum_shadow_days_required,
                shadow_extension_status=normalized_depth.shadow_extension_status,
                fill_source_status=fill_meta.fill_source_status,
                fill_model_name=fill_meta.fill_model_name,
                fill_realism_status=fill_meta.fill_realism_status,
                fill_ratio_expected=fill_meta.fill_ratio_expected,
                fill_ratio_observed=fill_meta.fill_ratio_observed,
                partial_fill_rate_expected=fill_meta.partial_fill_rate_expected,
                partial_fill_rate_observed=fill_meta.partial_fill_rate_observed,
                no_fill_rate_expected=fill_meta.no_fill_rate_expected,
                no_fill_rate_observed=fill_meta.no_fill_rate_observed,
                measured_fill_flag=fill_meta.measured_fill_flag,
                synthetic_fill_flag=fill_meta.synthetic_fill_flag,
                realized_slippage_status=cost_parity_meta.realized_slippage_status,
                replay_live_cost_parity_status=cost_parity_meta.cost_parity_status,
                cost_parity_status=cost_parity_meta.cost_parity_status,
                cost_drift_bps=cost_parity_meta.cost_drift_bps,
                cost_drift_status=cost_parity_meta.cost_drift_status,
                parity_sample_count=cost_parity_meta.parity_sample_count,
                execution_label_source=cost_parity_meta.execution_label_source,
                fee_model_source=cost_parity_meta.fee_model_source,
                spread_model_source=cost_parity_meta.spread_model_source,
                slippage_model_source=cost_parity_meta.slippage_model_source,
                partial_fill_model_source=cost_parity_meta.partial_fill_model_source,
                adverse_selection_source=cost_parity_meta.adverse_selection_source,
                order_type_selection_source=cost_parity_meta.order_type_selection_source,
                venue_constraints_source=cost_parity_meta.venue_constraints_source,
                execution_fidelity_gap_codes=cost_parity_meta.execution_fidelity_gap_codes,
                engine_executed_only_net_return=engine_executed_only_net_return,
                executed_only_net_return_status=engine_executed_only_net_return_status,
                engine_true_net_equity_max_drawdown=engine_true_net_equity_max_drawdown,
                true_net_equity_drawdown_status=engine_true_net_equity_drawdown_status,
            )
        )
    engine_aggregates = tuple(engine_rows)
    return ReplayMetricsSummary(
        total_records=total_records,
        total_opportunities=total_opportunities,
        dtr_coverage=round(dtr_summary.dtr_coverage, 6),
        selected_count=selected_count,
        executed_count=executed_count,
        executed_distinct_candidate_count=executed_distinct_candidate_count,
        reduced_count=reduced_count,
        no_fill_count=no_fill_count,
        hard_blocked_count=sum(
            1 for record in records if record.decision_state == DecisionState.HARD_BLOCKED
        ),
        rejected_ranking_count=sum(
            1 for record in records if record.decision_state == DecisionState.REJECTED_RANKING
        ),
        rejected_count=sum(
            1 for record in records if record.decision_state == DecisionState.REJECTED_RANKING
        ),
        phantom_count=sum(
            1 for record in records if record.decision_state == DecisionState.PHANTOM
        ),
        missing_realized_cost_count=missing_realized_cost_count,
        ce_net=round(sum(record.ce_expected for record in records), 6),
        expected_cost_mean=expected_cost_mean,
        replay_expected_cost_model_mean=expected_cost_mean,
        expected_total_cost_mean=None,
        realized_cost_mean=round(_mean(tuple(record.realized_cost for record in records)), 6),
        gross_return_mean=round(_mean(tuple(record.gross_return for record in records)), 6),
        gross_return_total=round(sum(record.gross_return for record in records), 6),
        executed_only_net_return=executed_only_net_return,
        executed_only_net_return_status=executed_only_net_return_status,
        initial_capital=initial_capital,
        true_net_equity_curve=true_net_equity_curve,
        true_net_equity_max_drawdown=true_net_equity_max_drawdown,
        drawdown_proxy=round(_drawdown_proxy(records), 6),
        selected_execution_rate=(
            round((executed_count + reduced_count) / selected_count, 6)
            if selected_count > 0
            else None
        ),
        non_execution_rate=(
            round(max(0.0, min(1.0, 1.0 - (executed_count / total_records))), 6)
            if total_records > 0
            else 1.0
        ),
        fee_source_status=fee_source_status,
        fee_model_name=fee_meta.fee_model_name,
        fee_rate_maker_bps=fee_meta.fee_rate_maker_bps,
        fee_rate_taker_bps=fee_meta.fee_rate_taker_bps,
        fee_currency=fee_meta.fee_currency,
        fee_amount=fee_meta.fee_amount,
        fee_bps=fee_meta.fee_bps,
        fee_provenance_ref=fee_meta.fee_provenance_ref,
        fee_input_hash=fee_meta.fee_input_hash,
        fee_policy_version=fee_meta.fee_policy_version,
        impact_source_status=normalized_impact_source_status,
        impact_model_name=impact_meta.impact_model_name,
        impact_bps=impact_meta.impact_bps,
        impact_notional=impact_meta.impact_notional,
        impact_depth_ref=impact_meta.impact_depth_ref,
        impact_depth_level=impact_meta.impact_depth_level,
        impact_provenance_ref=impact_meta.impact_provenance_ref,
        impact_input_hash=impact_meta.impact_input_hash,
        impact_policy_version=impact_meta.impact_policy_version,
        book_depth_available=normalized_depth.book_depth_available,
        book_depth_levels=normalized_depth.book_depth_levels,
        book_depth_source_status=normalized_depth.book_depth_source_status,
        book_depth_snapshot_count=normalized_depth.book_depth_snapshot_count,
        book_depth_event_count=normalized_depth.book_depth_event_count,
        book_depth_missing_count=normalized_depth.book_depth_missing_count,
        book_depth_staleness_status=normalized_depth.book_depth_staleness_status,
        impact_depth_level_used=normalized_depth.impact_depth_level_used,
        impact_depth_readiness_status=normalized_depth.impact_depth_readiness_status,
        shadow_extension_required=normalized_depth.shadow_extension_required,
        shadow_extension_reason=normalized_depth.shadow_extension_reason,
        minimum_shadow_days_required=normalized_depth.minimum_shadow_days_required,
        shadow_extension_status=normalized_depth.shadow_extension_status,
        cost_model_completeness_status=cost_model_completeness_status,
        cost_readiness_reason_codes=cost_readiness_reason_codes,
        fill_ratio_source=fill_meta.fill_ratio_source,
        fill_realism_status=fill_meta.fill_realism_status,
        fill_source_status=fill_meta.fill_source_status,
        fill_model_name=fill_meta.fill_model_name,
        fill_model_version=fill_meta.fill_model_version,
        fill_ratio_expected=fill_meta.fill_ratio_expected,
        fill_ratio_observed=fill_meta.fill_ratio_observed,
        partial_fill_rate_expected=fill_meta.partial_fill_rate_expected,
        partial_fill_rate_observed=fill_meta.partial_fill_rate_observed,
        no_fill_rate_expected=fill_meta.no_fill_rate_expected,
        no_fill_rate_observed=fill_meta.no_fill_rate_observed,
        fill_latency_ms_expected=fill_meta.fill_latency_ms_expected,
        fill_latency_ms_observed=fill_meta.fill_latency_ms_observed,
        synthetic_fill_flag=fill_meta.synthetic_fill_flag,
        measured_fill_flag=fill_meta.measured_fill_flag,
        fill_provenance_ref=fill_meta.fill_provenance_ref,
        fill_input_hash=fill_meta.fill_input_hash,
        fill_policy_version=fill_meta.fill_policy_version,
        realized_slippage_status=cost_parity_meta.realized_slippage_status,
        execution_label_source=cost_parity_meta.execution_label_source,
        fee_model_source=cost_parity_meta.fee_model_source,
        spread_model_source=cost_parity_meta.spread_model_source,
        slippage_model_source=cost_parity_meta.slippage_model_source,
        partial_fill_model_source=cost_parity_meta.partial_fill_model_source,
        adverse_selection_source=cost_parity_meta.adverse_selection_source,
        order_type_selection_source=cost_parity_meta.order_type_selection_source,
        venue_constraints_source=cost_parity_meta.venue_constraints_source,
        execution_fidelity_gap_codes=cost_parity_meta.execution_fidelity_gap_codes,
        cost_parity_status=cost_parity_meta.cost_parity_status,
        replay_live_cost_parity_status=cost_parity_meta.cost_parity_status,
        replay_cost_components=cost_parity_meta.replay_cost_components,
        shadow_cost_components=cost_parity_meta.shadow_cost_components,
        live_cost_components=cost_parity_meta.live_cost_components,
        replay_fee_bps=cost_parity_meta.replay_fee_bps,
        shadow_fee_bps=cost_parity_meta.shadow_fee_bps,
        live_fee_bps=cost_parity_meta.live_fee_bps,
        replay_impact_bps=cost_parity_meta.replay_impact_bps,
        shadow_impact_bps=cost_parity_meta.shadow_impact_bps,
        live_impact_bps=cost_parity_meta.live_impact_bps,
        replay_slippage_bps=cost_parity_meta.replay_slippage_bps,
        shadow_slippage_bps=cost_parity_meta.shadow_slippage_bps,
        live_slippage_bps=cost_parity_meta.live_slippage_bps,
        replay_fill_ratio=cost_parity_meta.replay_fill_ratio,
        shadow_fill_ratio=cost_parity_meta.shadow_fill_ratio,
        live_fill_ratio=cost_parity_meta.live_fill_ratio,
        cost_drift_bps=cost_parity_meta.cost_drift_bps,
        cost_drift_status=cost_parity_meta.cost_drift_status,
        parity_sample_count=cost_parity_meta.parity_sample_count,
        parity_window_start=cost_parity_meta.parity_window_start,
        parity_window_end=cost_parity_meta.parity_window_end,
        parity_input_hash=cost_parity_meta.parity_input_hash,
        parity_policy_version=cost_parity_meta.parity_policy_version,
        small_capital_exclusion_rate=small_capital_exclusion_rate,
        small_capital_exclusion_status=(
            "MEASURED" if small_capital_exclusion_rate is not None else "NOT_PROVEN"
        ),
        small_capital_viability_status=small_capital_viability_status,
        min_notional_viability_status=min_notional_viability_status,
        capital_fragmentation_status=capital_fragmentation_status,
        true_net_equity_drawdown_status=true_net_equity_drawdown_status,
        capital_bucket_profiles=normalized_capital_bucket_profiles,
        pair_aggregates=pair_aggregates,
        engine_aggregates=engine_aggregates,
    )


__all__ = [
    "ReplayBookDepthAvailability",
    "ReplayCostParityEvidence",
    "ReplayEngineAggregate",
    "ReplayFeeProvenance",
    "ReplayFillRealismEvidence",
    "ReplayImpactProvenance",
    "ReplayMetricsSummary",
    "ReplayPairAggregate",
    "build_replay_metrics_summary",
]
