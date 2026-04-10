"""Prudent Shadow-compatible execution simulator for LOCAL_REPLAY."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from data_backbone.market_physics_math import round_float64
from local_replay_runtime.historical_data_gateway import (
    HistoricalReplayDataset,
    HistoricalReplayOpportunity,
)
from meta_minimal.dtr_core.decision_state_encoder import DecisionState
from meta_minimal.dtr_core.dtr_record_builder import DTRRecord, build_dtr


class ParityTolerancePolicy(BaseModel, frozen=True):
    """Explicit parity policy for governed replay/shadow comparisons."""

    parity_scope: str = "logical_decision_with_prudent_score_cost_tolerance"
    decision_parity_kind: str = "logical_decision_state"
    score_parity_kind: str = "bounded_float64_score_tolerance"
    cost_parity_kind: str = "prudent_expected_cost_tolerance"
    float_precision: str = "binary64"
    minimum_compared_records: int = Field(default=1, ge=1)
    decision_match_threshold: float = Field(default=0.95, ge=0.0, le=1.0)
    score_match_threshold: float = Field(default=0.95, ge=0.0, le=1.0)
    score_tolerance: float = Field(default=0.03, ge=0.0)
    cost_tolerance: float = Field(default=0.0005, ge=0.0)


class ShadowExecutionSimulatorConfig(BaseModel, frozen=True):
    """Minimal prudent execution assumptions for governed local replay."""

    slippage_multiplier: float = Field(default=1.15, ge=1.0)
    latency_penalty_multiplier: float = Field(default=1.0, ge=1.0)
    phantom_fill_threshold: float = Field(default=0.15, ge=0.0, le=1.0)
    reduced_fill_threshold: float = Field(default=0.95, ge=0.0, le=1.0)
    economic_absurdity_buffer_bps: float = Field(default=0.50, ge=0.0)
    parity_policy: ParityTolerancePolicy = Field(default_factory=ParityTolerancePolicy)


class ReplayParityDiagnosticsSummary(BaseModel, frozen=True):
    """Typed parity diagnostics payload exported by governed LOCAL_REPLAY."""

    parity_status: str = Field(..., min_length=1)
    dataset_id: str = "unknown_dataset"
    decision_match_rate: float = Field(..., ge=0.0, le=1.0)
    score_match_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    baseline_status: str = "unknown"
    score_alignment: str = "unknown"
    cost_alignment: str = "unknown"
    mean_cost_gap: float = Field(default=0.0, ge=0.0)
    compared_records: int = Field(default=0, ge=0)
    missing_baseline_records: int = Field(default=0, ge=0)
    divergence_count: int = Field(default=0, ge=0)
    shared_core_match: bool = False
    parity_policy: dict[str, Any] = Field(default_factory=dict)


def _base_state(row: HistoricalReplayOpportunity) -> DecisionState:
    if row.target_decision_state is not None:
        return row.target_decision_state
    if row.hard_block_reasons:
        return DecisionState.HARD_BLOCKED
    if row.final_size > 0.0 and row.fill_ratio >= 1.0:
        return DecisionState.EXECUTED
    if row.final_size > 0.0 and row.fill_ratio > 0.0:
        return DecisionState.REDUCED
    if row.ranking_position > 0:
        return DecisionState.REJECTED_RANKING
    return DecisionState.EVALUATED


def _expected_cost(
    row: HistoricalReplayOpportunity,
    config: ShadowExecutionSimulatorConfig,
) -> float:
    return (
        row.spread_bps
        + row.slippage_bps * config.slippage_multiplier
        + row.latency_penalty_bps * config.latency_penalty_multiplier
    ) / 10_000.0


def _state_and_reason(
    row: HistoricalReplayOpportunity,
    *,
    config: ShadowExecutionSimulatorConfig,
    expected_cost: float,
) -> tuple[DecisionState, str]:
    base_state = _base_state(row)
    expected_edge = row.expected_edge_bps / 10_000.0
    selected_states = {
        DecisionState.SELECTED,
        DecisionState.REDUCED,
        DecisionState.EXECUTED,
    }
    if base_state in selected_states and expected_edge <= (
        expected_cost + config.economic_absurdity_buffer_bps / 10_000.0
    ):
        return DecisionState.PHANTOM, "economically_absurd"
    if base_state in selected_states and row.fill_ratio <= config.phantom_fill_threshold:
        return DecisionState.PHANTOM, row.primary_reason or "no_fill"
    if base_state in selected_states and row.fill_ratio < config.reduced_fill_threshold:
        return DecisionState.REDUCED, row.primary_reason or "partial_fill"
    if base_state == DecisionState.SELECTED:
        return DecisionState.EXECUTED, row.primary_reason or "shadow_compatible_execution"
    if base_state == DecisionState.HARD_BLOCKED:
        return DecisionState.HARD_BLOCKED, row.primary_reason or "hard_blocked"
    if base_state == DecisionState.REJECTED_RANKING:
        return DecisionState.REJECTED_RANKING, row.primary_reason or "rank_cutoff"
    return base_state, row.primary_reason


def _execution_factor(state: DecisionState, row: HistoricalReplayOpportunity) -> float:
    if state in {
        DecisionState.HARD_BLOCKED,
        DecisionState.REJECTED_RANKING,
        DecisionState.EVALUATED,
        DecisionState.NOT_EVALUATED,
    }:
        return 0.0
    if state == DecisionState.PHANTOM:
        return 0.0
    if state == DecisionState.REDUCED:
        return row.fill_ratio
    return 1.0


def simulate_shadow_compatible_dtrs(
    dataset: HistoricalReplayDataset,
    *,
    config: ShadowExecutionSimulatorConfig | None = None,
) -> tuple[DTRRecord, ...]:
    """Replay historical opportunities through a prudent Shadow-style simulator."""

    effective_config = config or ShadowExecutionSimulatorConfig()
    records: list[DTRRecord] = []
    for row in dataset.rows:
        expected_cost = _expected_cost(row, effective_config)
        state, primary_reason = _state_and_reason(
            row,
            config=effective_config,
            expected_cost=expected_cost,
        )
        execution_factor = _execution_factor(state, row)
        gross_return = round((row.gross_return_bps / 10_000.0) * execution_factor, 6)
        records.append(
            build_dtr(
                dtr_id=f"{dataset.dataset_id}:{row.opportunity_id}",
                pair=row.pair,
                engine_id=row.engine_id,
                decision_state=state,
                raw_score=row.raw_score,
                penalized_score=row.penalized_score or row.raw_score,
                final_score=row.final_score or row.raw_score,
                hard_blocked=bool(row.hard_block_reasons),
                hard_block_reasons=row.hard_block_reasons,
                ranking_position=row.ranking_position,
                candidate_size=row.candidate_size,
                final_size=(
                    row.final_size
                    if execution_factor >= 1.0
                    else round(row.final_size * execution_factor, 6)
                ),
                tier=row.tier,
                expected_cost=round(expected_cost, 6),
                realized_cost=round(expected_cost * execution_factor, 6),
                gross_return=gross_return,
                ce_expected=round((row.expected_edge_bps / 10_000.0) - expected_cost, 6),
                regime=row.regime,
                runtime_mode="local_replay",
                input_source="historical_data_gateway",
                path_complete=bool(row.feature_values) and row.shared_core_match,
                path_warnings=tuple(
                    warning
                    for warning in (
                        "" if row.feature_values else "missing_feature_values",
                        "" if row.shared_core_match else "shared_core_mismatch",
                    )
                    if warning
                ),
                primary_reason=primary_reason,
                cause_chain=(
                    row.hard_block_reasons
                    if row.hard_block_reasons
                    else ((primary_reason,) if primary_reason else ())
                ),
                timestamp=row.timestamp_ms / 1000.0,
            )
        )
    return tuple(records)


def build_parity_diagnostics_payload(
    dataset: HistoricalReplayDataset,
    dtr_records: tuple[DTRRecord, ...],
    *,
    config: ShadowExecutionSimulatorConfig | None = None,
) -> dict[str, Any]:
    """Compare simulated replay outputs against optional production baselines."""

    effective_config = config or ShadowExecutionSimulatorConfig()
    parity_policy = effective_config.parity_policy
    decision_compared = 0
    decision_matches = 0
    score_compared = 0
    score_matches = 0
    cost_compared = 0
    cost_diffs: list[float] = []

    for row, record in zip(dataset.rows, dtr_records, strict=False):
        baseline_state = row.production_decision_state or row.target_decision_state
        if baseline_state is not None:
            decision_compared += 1
            if baseline_state == record.decision_state:
                decision_matches += 1

        baseline_score = (
            row.production_final_score
            if row.production_final_score is not None
            else row.final_score
        )
        if baseline_score is not None:
            score_compared += 1
            if (
                abs(float(baseline_score) - record.final_score)
                <= parity_policy.score_tolerance
            ):
                score_matches += 1

        if row.production_expected_cost is not None:
            cost_compared += 1
            cost_diffs.append(abs(row.production_expected_cost - record.expected_cost))

    decision_match_rate = (
        round_float64(decision_matches / decision_compared, 6)
        if decision_compared
        else 0.0
    )
    score_match_rate = (
        round_float64(score_matches / score_compared, 6) if score_compared else 0.0
    )
    mean_cost_gap = (
        round_float64(sum(cost_diffs) / len(cost_diffs), 6) if cost_diffs else 0.0
    )
    baseline_status = (
        "sufficient"
        if decision_compared >= parity_policy.minimum_compared_records
        else "insufficient"
    )
    score_alignment = (
        "within_prudent_tolerance"
        if score_compared and score_match_rate >= parity_policy.score_match_threshold
        else ("missing_baseline" if score_compared == 0 else "diverged")
    )
    cost_alignment = (
        "within_prudent_tolerance"
        if cost_compared and mean_cost_gap <= parity_policy.cost_tolerance
        else ("missing_baseline" if cost_compared == 0 else "diverged")
    )
    parity_status = (
        "ok"
        if dataset.shared_core_match
        and dataset.missing_feature_rows == 0
        and baseline_status == "sufficient"
        and decision_match_rate >= parity_policy.decision_match_threshold
        and score_alignment == "within_prudent_tolerance"
        and cost_alignment == "within_prudent_tolerance"
        else "warning"
    )
    return ReplayParityDiagnosticsSummary(
        parity_status=parity_status,
        dataset_id=dataset.dataset_id,
        decision_match_rate=decision_match_rate,
        score_match_rate=score_match_rate,
        baseline_status=baseline_status,
        score_alignment=score_alignment,
        cost_alignment=cost_alignment,
        mean_cost_gap=mean_cost_gap,
        compared_records=decision_compared,
        missing_baseline_records=max(dataset.record_count - decision_compared, 0),
        divergence_count=max(decision_compared - decision_matches, 0),
        shared_core_match=dataset.shared_core_match,
        parity_policy=parity_policy.model_dump(mode="json"),
    ).model_dump(mode="json")


__all__ = [
    "ParityTolerancePolicy",
    "ReplayParityDiagnosticsSummary",
    "ShadowExecutionSimulatorConfig",
    "simulate_shadow_compatible_dtrs",
    "build_parity_diagnostics_payload",
]
