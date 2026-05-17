"""Typed contracts for governed promotion and sample-size artifact exports."""

from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json

from pydantic import BaseModel, Field


REQUIRED_PROMOTION_ENGINE_IDS: tuple[str, ...] = (
    "engine_a",
    "engine_b",
    "engine_c",
    "engine_d",
)
REQUIRED_SAMPLE_SIZE_SCOPES: tuple[str, ...] = (
    "global",
    "engine",
    "pair",
    "strategy",
    "capital_bucket",
    "engine_pair",
    "strategy_pair",
)


class EngineCPromotionLocalStatus(BaseModel, frozen=True):
    """Local explainability/status carriage for Engine C promotion evidence."""

    breakout_confirmation_score_status: str = "NOT_PROVEN"
    continuation_score_status: str = "NOT_PROVEN"
    false_breakout_risk_status: str = "NOT_PROVEN"
    microstructure_confirmation_status: str = "NOT_PROVEN"
    vpin_context_status: str = "NOT_PROVEN"
    ofi_context_status: str = "NOT_PROVEN"
    kyle_lambda_context_status: str = "NOT_PROVEN"
    queue_pressure_context_status: str = "NOT_PROVEN"


class EngineDPromotionLocalStatus(BaseModel, frozen=True):
    """Local explainability/status carriage for Engine D promotion evidence."""

    first_episode_ref_status: str = "NOT_PROVEN"
    reentry_age_status: str = "NOT_PROVEN"
    timing_window_status: str = "NOT_PROVEN"
    reformation_score_status: str = "NOT_PROVEN"
    history_score_status: str = "NOT_PROVEN"
    marginal_value_score_status: str = "NOT_PROVEN"
    anti_revenge_state_status: str = "NOT_PROVEN"
    realized_vol_context_status: str = "NOT_PROVEN"


class EnginePromotionArtifact(BaseModel, frozen=True):
    """Canonical engine-level promotion artifact."""

    schema_version: str = Field(default="v1", min_length=1)
    run_id: str | None = None
    engine_id: str = Field(..., min_length=1)
    engine_role: str | None = None
    strategy_id: str | None = None
    capital_bucket: int | None = Field(default=None, ge=1)
    pair_universe: tuple[str, ...] = ()
    shared_physics_mapping_status: str | None = None
    record_count: int | None = Field(default=None, ge=0)
    candidate_count: int | None = Field(default=None, ge=0)
    unique_candidate_count: int | None = Field(default=None, ge=0)
    engine_evaluation_count: int | None = Field(default=None, ge=0)
    evaluation_record_count: int | None = Field(default=None, ge=0)
    promotion_record_count: int | None = Field(default=None, ge=0)
    capital_bucket_record_count: int | None = Field(default=None, ge=0)
    replay_expansion_factor: float | None = Field(default=None, ge=0.0)
    replay_expansion_axis: str = ""
    selected_count: int | None = Field(default=None, ge=0)
    executed_count: int | None = Field(default=None, ge=0)
    reduced_count: int | None = Field(default=None, ge=0)
    no_fill_count: int | None = Field(default=None, ge=0)
    hard_blocked_count: int | None = Field(default=None, ge=0)
    rejected_count: int | None = Field(default=None, ge=0)
    execution_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    partial_fill_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    no_fill_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    expected_ce_net: float | None = None
    executed_only_net_return: float | None = None
    executed_only_net_return_status: str = "EXECUTED_NET_RETURN_NOT_PROVEN"
    true_net_equity_max_drawdown: float | None = Field(default=None, ge=0.0, le=1.0)
    true_net_equity_drawdown_status: str = "TRUE_NET_EQUITY_DRAWDOWN_NOT_PROVEN"
    drawdown_proxy: float | None = None
    drawdown_proxy_status: str = "DIAGNOSTIC_ONLY"
    fee_source_status: str = "FEE_SOURCE_NOT_PROVEN"
    impact_source_status: str = "IMPACT_SOURCE_NOT_PROVEN"
    fill_realism_status: str = "FILL_REALISM_NOT_PROVEN"
    cost_parity_status: str = "REPLAY_LIVE_COST_PARITY_NOT_PROVEN"
    execution_label_source: str = "REPLAY_PROXY_EXECUTION"
    fee_model_source: str = "REPLAY_PROXY"
    spread_model_source: str = "REPLAY_PROXY"
    slippage_model_source: str = "REPLAY_PROXY"
    partial_fill_model_source: str = "REPLAY_PROXY"
    adverse_selection_source: str = "REPLAY_PROXY"
    order_type_selection_source: str = "REPLAY_PROXY"
    venue_constraints_source: str = "REPLAY_PROXY"
    execution_fidelity_gap_codes: tuple[str, ...] = ()
    cost_model_completeness_status: str = "COST_MODEL_NOT_PROVEN"
    book_depth_source_status: str = "BOOK_DEPTH_NOT_PROVEN"
    impact_depth_readiness_status: str = "BOOK_DEPTH_NOT_PROVEN"
    sample_size_survival_status: str = "SAMPLE_SIZE_NOT_PROVEN"
    sample_size_survival_ratio: float | None = Field(default=None, ge=0.0, le=1.0)
    sample_size_min_required: int | None = Field(default=None, ge=0)
    sample_size_actual: int | None = Field(default=None, ge=0)
    promotion_status: str = "ENGINE_PROMOTION_NOT_READY"
    promotion_blockers: tuple[str, ...] = ()
    engine_c: EngineCPromotionLocalStatus | None = None
    engine_d: EngineDPromotionLocalStatus | None = None
    artifact_hash: str | None = None
    input_data_hash: str | None = None
    method_version_hash: str | None = None
    created_at: datetime | None = None
    expires_at: datetime | None = None


class PairPromotionArtifact(BaseModel, frozen=True):
    """Canonical pair-level promotion artifact."""

    schema_version: str = Field(default="v1", min_length=1)
    run_id: str | None = None
    pair: str = Field(..., min_length=1)
    capital_bucket: int | None = Field(default=None, ge=1)
    engines_seen: tuple[str, ...] = ()
    strategies_seen: tuple[str, ...] = ()
    record_count: int | None = Field(default=None, ge=0)
    candidate_count: int | None = Field(default=None, ge=0)
    unique_candidate_count: int | None = Field(default=None, ge=0)
    evaluation_record_count: int | None = Field(default=None, ge=0)
    promotion_record_count: int | None = Field(default=None, ge=0)
    capital_bucket_record_count: int | None = Field(default=None, ge=0)
    replay_expansion_factor: float | None = Field(default=None, ge=0.0)
    replay_expansion_axis: str = ""
    selected_count: int | None = Field(default=None, ge=0)
    executed_count: int | None = Field(default=None, ge=0)
    reduced_count: int | None = Field(default=None, ge=0)
    no_fill_count: int | None = Field(default=None, ge=0)
    hard_blocked_count: int | None = Field(default=None, ge=0)
    rejected_count: int | None = Field(default=None, ge=0)
    execution_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    partial_fill_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    no_fill_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    expected_ce_net: float | None = None
    executed_only_net_return: float | None = None
    executed_only_net_return_status: str = "EXECUTED_NET_RETURN_NOT_PROVEN"
    true_net_equity_max_drawdown: float | None = Field(default=None, ge=0.0, le=1.0)
    true_net_equity_drawdown_status: str = "TRUE_NET_EQUITY_DRAWDOWN_NOT_PROVEN"
    min_notional_block_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    capital_fragmentation_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    fee_source_status: str = "FEE_SOURCE_NOT_PROVEN"
    impact_source_status: str = "IMPACT_SOURCE_NOT_PROVEN"
    fill_realism_status: str = "FILL_REALISM_NOT_PROVEN"
    cost_parity_status: str = "REPLAY_LIVE_COST_PARITY_NOT_PROVEN"
    execution_label_source: str = "REPLAY_PROXY_EXECUTION"
    fee_model_source: str = "REPLAY_PROXY"
    spread_model_source: str = "REPLAY_PROXY"
    slippage_model_source: str = "REPLAY_PROXY"
    partial_fill_model_source: str = "REPLAY_PROXY"
    adverse_selection_source: str = "REPLAY_PROXY"
    order_type_selection_source: str = "REPLAY_PROXY"
    venue_constraints_source: str = "REPLAY_PROXY"
    execution_fidelity_gap_codes: tuple[str, ...] = ()
    book_depth_source_status: str = "BOOK_DEPTH_NOT_PROVEN"
    sample_size_survival_status: str = "SAMPLE_SIZE_NOT_PROVEN"
    promotion_status: str = "PAIR_NOT_PROVEN"
    promotion_blockers: tuple[str, ...] = ()
    artifact_hash: str | None = None
    input_data_hash: str | None = None
    method_version_hash: str | None = None
    created_at: datetime | None = None
    expires_at: datetime | None = None


class StrategyPromotionArtifact(BaseModel, frozen=True):
    """Canonical strategy-level promotion artifact."""

    schema_version: str = Field(default="v1", min_length=1)
    run_id: str | None = None
    strategy_id: str | None = None
    strategy_role: str | None = None
    engine_ids: tuple[str, ...] = ()
    capital_bucket: int | None = Field(default=None, ge=1)
    pair_universe: tuple[str, ...] = ()
    record_count: int | None = Field(default=None, ge=0)
    candidate_count: int | None = Field(default=None, ge=0)
    unique_candidate_count: int | None = Field(default=None, ge=0)
    evaluation_record_count: int | None = Field(default=None, ge=0)
    promotion_record_count: int | None = Field(default=None, ge=0)
    capital_bucket_record_count: int | None = Field(default=None, ge=0)
    replay_expansion_factor: float | None = Field(default=None, ge=0.0)
    replay_expansion_axis: str = ""
    selected_count: int | None = Field(default=None, ge=0)
    executed_count: int | None = Field(default=None, ge=0)
    reduced_count: int | None = Field(default=None, ge=0)
    no_fill_count: int | None = Field(default=None, ge=0)
    hard_blocked_count: int | None = Field(default=None, ge=0)
    rejected_count: int | None = Field(default=None, ge=0)
    execution_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    partial_fill_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    no_fill_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    expected_ce_net: float | None = None
    executed_only_net_return: float | None = None
    executed_only_net_return_status: str = "EXECUTED_NET_RETURN_NOT_PROVEN"
    true_net_equity_max_drawdown: float | None = Field(default=None, ge=0.0, le=1.0)
    true_net_equity_drawdown_status: str = "TRUE_NET_EQUITY_DRAWDOWN_NOT_PROVEN"
    cost_model_completeness_status: str = "COST_MODEL_NOT_PROVEN"
    fill_realism_status: str = "FILL_REALISM_NOT_PROVEN"
    cost_parity_status: str = "REPLAY_LIVE_COST_PARITY_NOT_PROVEN"
    execution_label_source: str = "REPLAY_PROXY_EXECUTION"
    fee_model_source: str = "REPLAY_PROXY"
    spread_model_source: str = "REPLAY_PROXY"
    slippage_model_source: str = "REPLAY_PROXY"
    partial_fill_model_source: str = "REPLAY_PROXY"
    adverse_selection_source: str = "REPLAY_PROXY"
    order_type_selection_source: str = "REPLAY_PROXY"
    venue_constraints_source: str = "REPLAY_PROXY"
    execution_fidelity_gap_codes: tuple[str, ...] = ()
    book_depth_source_status: str = "BOOK_DEPTH_NOT_PROVEN"
    sample_size_survival_status: str = "SAMPLE_SIZE_NOT_PROVEN"
    promotion_status: str = "STRATEGY_PROMOTION_NOT_READY"
    promotion_blockers: tuple[str, ...] = ()
    artifact_hash: str | None = None
    input_data_hash: str | None = None
    method_version_hash: str | None = None
    created_at: datetime | None = None
    expires_at: datetime | None = None


class SampleSizeSurvivalArtifact(BaseModel, frozen=True):
    """Canonical sample-size survival artifact."""

    schema_version: str = Field(default="v1", min_length=1)
    run_id: str | None = None
    scope: str = Field(..., min_length=1)
    id: str = Field(..., min_length=1)
    raw_candidate_count: int | None = Field(default=None, ge=0)
    after_hard_filters_count: int | None = Field(default=None, ge=0)
    after_cost_filters_count: int | None = Field(default=None, ge=0)
    after_risk_filters_count: int | None = Field(default=None, ge=0)
    selected_count: int | None = Field(default=None, ge=0)
    executed_count: int | None = Field(default=None, ge=0)
    reduced_count: int | None = Field(default=None, ge=0)
    no_fill_count: int | None = Field(default=None, ge=0)
    survival_ratio_raw_to_selected: float | None = Field(default=None, ge=0.0, le=1.0)
    survival_ratio_selected_to_executed: float | None = Field(default=None, ge=0.0, le=1.0)
    survival_ratio_raw_to_executed: float | None = Field(default=None, ge=0.0, le=1.0)
    min_required_candidates: int | None = Field(default=None, ge=0)
    min_required_executions: int | None = Field(default=None, ge=0)
    min_required_days: int | None = Field(default=None, ge=0)
    sample_period_start: str | None = None
    sample_period_end: str | None = None
    sample_days: int | None = Field(default=None, ge=0)
    sample_size_survival_status: str = "SAMPLE_SIZE_NOT_PROVEN"
    sample_size_blockers: tuple[str, ...] = ()
    artifact_hash: str | None = None
    input_data_hash: str | None = None
    method_version_hash: str | None = None
    created_at: datetime | None = None
    expires_at: datetime | None = None


def _normalize_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _artifact_hash(model: BaseModel) -> str:
    payload = model.model_copy(
        update={
            "artifact_hash": None,
            "created_at": _normalize_datetime(getattr(model, "created_at", None)),
            "expires_at": _normalize_datetime(getattr(model, "expires_at", None)),
        }
    ).model_dump(mode="json")
    encoded = json.dumps(
        payload,
        sort_keys=True,
        ensure_ascii=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def engine_promotion_artifact_hash(artifact: EnginePromotionArtifact) -> str:
    return _artifact_hash(artifact)


def pair_promotion_artifact_hash(artifact: PairPromotionArtifact) -> str:
    return _artifact_hash(artifact)


def strategy_promotion_artifact_hash(artifact: StrategyPromotionArtifact) -> str:
    return _artifact_hash(artifact)


def sample_size_survival_artifact_hash(artifact: SampleSizeSurvivalArtifact) -> str:
    return _artifact_hash(artifact)


__all__ = [
    "REQUIRED_PROMOTION_ENGINE_IDS",
    "REQUIRED_SAMPLE_SIZE_SCOPES",
    "EngineCPromotionLocalStatus",
    "EngineDPromotionLocalStatus",
    "EnginePromotionArtifact",
    "PairPromotionArtifact",
    "StrategyPromotionArtifact",
    "SampleSizeSurvivalArtifact",
    "engine_promotion_artifact_hash",
    "pair_promotion_artifact_hash",
    "strategy_promotion_artifact_hash",
    "sample_size_survival_artifact_hash",
]
