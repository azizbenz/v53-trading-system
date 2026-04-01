"""Derived metrics for governed LOCAL_REPLAY artifact exports."""

from __future__ import annotations

from pydantic import BaseModel, Field

from meta import build_dtr_summary
from meta_minimal.dtr_core.decision_state_encoder import DecisionState
from meta_minimal.dtr_core.dtr_record_builder import DTRRecord


class ReplayPairAggregate(BaseModel, frozen=True):
    """Per-pair aggregates exported from a governed local replay session."""

    pair: str
    record_count: int = Field(default=0, ge=0)
    selected_count: int = Field(default=0, ge=0)
    ce_net: float = 0.0
    expected_cost_mean: float = 0.0
    realized_cost_mean: float = 0.0
    gross_return_mean: float = 0.0


class ReplayEngineAggregate(BaseModel, frozen=True):
    """Per-engine aggregates exported from a governed local replay session."""

    engine_id: str
    record_count: int = Field(default=0, ge=0)
    selected_count: int = Field(default=0, ge=0)
    hard_blocked_count: int = Field(default=0, ge=0)
    ce_net: float = 0.0
    expected_cost_mean: float = 0.0
    realized_cost_mean: float = 0.0
    gross_return_mean: float = 0.0


class ReplayMetricsSummary(BaseModel, frozen=True):
    """Top-level replay metrics summary suitable for artifact export."""

    total_records: int = Field(default=0, ge=0)
    total_opportunities: int = Field(default=0, ge=0)
    dtr_coverage: float = Field(default=0.0, ge=0.0)
    selected_count: int = Field(default=0, ge=0)
    executed_count: int = Field(default=0, ge=0)
    hard_blocked_count: int = Field(default=0, ge=0)
    rejected_ranking_count: int = Field(default=0, ge=0)
    phantom_count: int = Field(default=0, ge=0)
    ce_net: float = 0.0
    expected_cost_mean: float = 0.0
    realized_cost_mean: float = 0.0
    gross_return_mean: float = 0.0
    gross_return_total: float = 0.0
    drawdown_proxy: float = 0.0
    pair_aggregates: tuple[ReplayPairAggregate, ...] = ()
    engine_aggregates: tuple[ReplayEngineAggregate, ...] = ()


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


def build_replay_metrics_summary(
    records: tuple[DTRRecord, ...],
    *,
    total_opportunities: int,
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

    pair_aggregates = tuple(
        ReplayPairAggregate(
            pair=pair,
            record_count=len(group),
            selected_count=sum(1 for record in group if record.decision_state in selected_states),
            ce_net=round(sum(record.ce_expected for record in group), 6),
            expected_cost_mean=round(_mean(tuple(record.expected_cost for record in group)), 6),
            realized_cost_mean=round(_mean(tuple(record.realized_cost for record in group)), 6),
            gross_return_mean=round(_mean(tuple(record.gross_return for record in group)), 6),
        )
        for pair, group in sorted(pair_groups.items())
    )
    engine_aggregates = tuple(
        ReplayEngineAggregate(
            engine_id=engine_id,
            record_count=len(group),
            selected_count=sum(1 for record in group if record.decision_state in selected_states),
            hard_blocked_count=sum(
                1 for record in group if record.decision_state == DecisionState.HARD_BLOCKED
            ),
            ce_net=round(sum(record.ce_expected for record in group), 6),
            expected_cost_mean=round(_mean(tuple(record.expected_cost for record in group)), 6),
            realized_cost_mean=round(_mean(tuple(record.realized_cost for record in group)), 6),
            gross_return_mean=round(_mean(tuple(record.gross_return for record in group)), 6),
        )
        for engine_id, group in sorted(engine_groups.items())
    )
    return ReplayMetricsSummary(
        total_records=len(records),
        total_opportunities=total_opportunities,
        dtr_coverage=round(dtr_summary.dtr_coverage, 6),
        selected_count=sum(
            1 for record in records if record.decision_state in selected_states
        ),
        executed_count=sum(
            1 for record in records if record.decision_state == DecisionState.EXECUTED
        ),
        hard_blocked_count=sum(
            1 for record in records if record.decision_state == DecisionState.HARD_BLOCKED
        ),
        rejected_ranking_count=sum(
            1 for record in records if record.decision_state == DecisionState.REJECTED_RANKING
        ),
        phantom_count=sum(
            1 for record in records if record.decision_state == DecisionState.PHANTOM
        ),
        ce_net=round(sum(record.ce_expected for record in records), 6),
        expected_cost_mean=round(_mean(tuple(record.expected_cost for record in records)), 6),
        realized_cost_mean=round(_mean(tuple(record.realized_cost for record in records)), 6),
        gross_return_mean=round(_mean(tuple(record.gross_return for record in records)), 6),
        gross_return_total=round(sum(record.gross_return for record in records), 6),
        drawdown_proxy=round(_drawdown_proxy(records), 6),
        pair_aggregates=pair_aggregates,
        engine_aggregates=engine_aggregates,
    )


__all__ = [
    "ReplayPairAggregate",
    "ReplayEngineAggregate",
    "ReplayMetricsSummary",
    "build_replay_metrics_summary",
]
