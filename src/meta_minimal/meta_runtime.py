"""
Build-9 / meta_runtime
Real Build-9 runtime path across DTR, CRA, break-even and prudent edge reports.

This closes the canonical Build-9 path without inventing a parallel architecture:
- every significant decision becomes a DTR
- DTRs feed CRA
- executed trades feed break-even and prudent edge tracking
- synthetic or incomplete paths are signaled explicitly
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel

from meta_minimal.break_even_dashboard.break_even_reporter import (
    BreakEvenReport,
    build_break_even_report,
)
from meta_minimal.break_even_dashboard.cost_distribution_aggregator import (
    CostDistribution,
    aggregate_costs,
)
from meta_minimal.break_even_dashboard.motor_pair_break_even_view import build_views_by_engine_and_pair
from meta_minimal.break_even_dashboard.realized_break_even_calculator import (
    RealizedBreakEven,
    compute_realized_break_even,
)
from meta_minimal.cra_monitor.cra_alert_builder import build_alerts
from meta_minimal.cra_monitor.cra_reporter import CRAReport, build_cra_report
from meta_minimal.cra_monitor.phantom_risk_estimator import estimate_phantom_risk
from meta_minimal.cra_monitor.reduction_trace_reader import read_reduction
from meta_minimal.cra_monitor.sterilization_classifier import (
    SterilizationResult,
    classify_sterilization,
)
from meta_minimal.dtr_core.cause_chain_assembler import assemble_cause_chain
from meta_minimal.dtr_core.decision_state_encoder import DecisionState, encode_state
from meta_minimal.dtr_core.dtr_record_builder import DTRRecord, build_dtr
from meta_minimal.dtr_core.dtr_reporter import DTRSummary, build_dtr_summary
from meta_minimal.dtr_core.trace_persistence_layer import DTRStore, PersistenceStats
from meta_minimal.edge_tracker_prudent_minimal.edge_reporter import EdgeReport, build_edge_report
from meta_minimal.edge_tracker_prudent_minimal.edge_status_classifier import (
    EdgeClassification,
    EdgeStatus,
    PortfolioContext,
    classify_edge,
)
from meta_minimal.edge_tracker_prudent_minimal.return_aggregator import aggregate_returns
from meta_minimal.edge_tracker_prudent_minimal.sample_size_tracker import assess_sample_size
from meta_minimal.edge_tracker_prudent_minimal.uncertainty_estimator import estimate_uncertainty


class MetaInputSource(StrEnum):
    REAL_MARKET = "real_market"
    SHADOW_REAL = "shadow_real"
    LOCAL_REPLAY = "local_replay"
    SYNTHETIC = "synthetic"


class MetaRuntimeStatus(StrEnum):
    EMPTY = "empty"
    READY = "ready"
    HAS_PATH_WARNINGS = "has_path_warnings"
    HAS_SYNTHETIC_INPUTS = "has_synthetic_inputs"


class MetaRuntimeInput(BaseModel, frozen=True):
    """One significant decision entering the Build-9 runtime path."""

    dtr_id: str
    pair: str
    engine_id: str
    runtime_mode: str = ""
    input_source: MetaInputSource = MetaInputSource.REAL_MARKET
    path_complete: bool = True
    path_warnings: tuple[str, ...] = ()
    regime: str = ""
    raw_score: float = 0.0
    penalized_score: float = 0.0
    final_score: float = 0.0
    hard_block_reasons: tuple[str, ...] = ()
    ranking_position: int = 0
    candidate_size: float = 0.0
    final_size: float = 0.0
    tier: str = ""
    expected_cost: float = 0.0
    realized_cost: float = 0.0
    gross_return: float = 0.0
    ce_expected: float = 0.0
    score_step: str = ""
    penalty_steps: tuple[str, ...] = ()
    penalty_total: float = 0.0
    blocker_steps: tuple[str, ...] = ()
    ranking_step: str = ""
    allocation_step: str = ""
    execution_step: str = ""
    reduction_causes: tuple[str, ...] = ()
    holding_hours: float = 0.0
    cluster_utilization: float = 0.0
    is_cluster_crowded: bool = False
    hard_blocked: bool = False
    ranking_rejected: bool = False
    selected: bool = False
    was_reduced: bool = False
    is_phantom: bool = False
    was_executed: bool = False
    timestamp: float | None = None


class MetaRuntimeConfig(BaseModel, frozen=True):
    """Build-9 runtime configuration."""

    flush_dir: Path | None = None
    flush_to_disk: bool = False


class MetaRuntimeResult(BaseModel, frozen=True):
    """Audit-ready Build-9 runtime result."""

    status: MetaRuntimeStatus
    records: tuple[DTRRecord, ...] = ()
    dtr_summary: DTRSummary = DTRSummary()
    cra_report: CRAReport = CRAReport()
    break_even_report: BreakEvenReport = BreakEvenReport()
    edge_report: EdgeReport = EdgeReport()
    persistence_stats: PersistenceStats = PersistenceStats()
    flushed_count: int = 0
    warnings: tuple[str, ...] = ()


class MetaRuntime:
    """Real Build-9 runtime chaining DTR -> CRA -> break-even -> edge."""

    def __init__(self, *, config: MetaRuntimeConfig | None = None) -> None:
        self._config = config or MetaRuntimeConfig()
        self._store = DTRStore(flush_dir=self._config.flush_dir)

    def evaluate(self, runtime_inputs: tuple[MetaRuntimeInput, ...]) -> MetaRuntimeResult:
        """Evaluate the full Build-9 path on significant decisions."""
        if not runtime_inputs:
            return MetaRuntimeResult(status=MetaRuntimeStatus.EMPTY)

        warnings: list[str] = []
        synthetic_seen = False
        local_replay_seen = False
        incomplete_path_seen = False

        for item in runtime_inputs:
            record = _build_runtime_dtr(item)
            self._store.persist(record)
            if item.input_source == MetaInputSource.SYNTHETIC:
                synthetic_seen = True
            if item.input_source == MetaInputSource.LOCAL_REPLAY:
                local_replay_seen = True
            if not item.path_complete:
                incomplete_path_seen = True

        records = self._store.get_all()
        dtr_summary = build_dtr_summary(records, total_opportunities=len(runtime_inputs))

        cra_results, cra_alerts = _build_cra_results(records)
        cra_report = build_cra_report(cra_results, cra_alerts)

        break_even_records = _build_break_even_records(records)
        break_even_views = build_views_by_engine_and_pair(break_even_records)
        cost_distributions = _build_cost_distributions(break_even_records)
        break_even_report = build_break_even_report(
            break_even_views,
            cost_distributions=cost_distributions,
        )

        edge_classifications = _build_edge_classifications(records)
        edge_report = build_edge_report(edge_classifications)

        flushed_count = 0
        if self._config.flush_to_disk:
            flushed_count = self._store.flush_to_disk()

        if synthetic_seen:
            warnings.append("synthetic inputs detected: edge tracking excluded for those records")
        if local_replay_seen:
            warnings.append("local replay inputs detected: edge readings are indicative only")
        if incomplete_path_seen:
            warnings.append("incomplete decision path detected: DTR carries explicit path warnings")

        status = MetaRuntimeStatus.READY
        if synthetic_seen:
            status = MetaRuntimeStatus.HAS_SYNTHETIC_INPUTS
        elif local_replay_seen or incomplete_path_seen:
            status = MetaRuntimeStatus.HAS_PATH_WARNINGS

        return MetaRuntimeResult(
            status=status,
            records=records,
            dtr_summary=dtr_summary,
            cra_report=cra_report,
            break_even_report=break_even_report,
            edge_report=edge_report,
            persistence_stats=self._store.get_stats(),
            flushed_count=flushed_count,
            warnings=tuple(warnings),
        )


def build_meta_runtime_result_from_records(
    records: tuple[DTRRecord, ...],
    *,
    total_opportunities: int | None = None,
) -> MetaRuntimeResult:
    """Rebuild the canonical Build-9 report set from governed DTR records."""

    if not records:
        return MetaRuntimeResult(status=MetaRuntimeStatus.EMPTY)

    synthetic_seen = any(record.input_source == MetaInputSource.SYNTHETIC for record in records)
    local_replay_seen = any(record.input_source == MetaInputSource.LOCAL_REPLAY for record in records)
    incomplete_path_seen = any(not record.path_complete for record in records)

    dtr_summary = build_dtr_summary(
        records,
        total_opportunities=len(records) if total_opportunities is None else total_opportunities,
    )
    cra_results, cra_alerts = _build_cra_results(records)
    cra_report = build_cra_report(cra_results, cra_alerts)

    break_even_records = _build_break_even_records(records)
    break_even_views = build_views_by_engine_and_pair(break_even_records)
    cost_distributions = _build_cost_distributions(break_even_records)
    break_even_report = build_break_even_report(
        break_even_views,
        cost_distributions=cost_distributions,
    )

    edge_classifications = _build_edge_classifications(records)
    edge_report = build_edge_report(edge_classifications)

    warnings: list[str] = []
    if synthetic_seen:
        warnings.append("synthetic inputs detected: edge tracking excluded for those records")
    if local_replay_seen:
        warnings.append("local replay inputs detected: edge readings are indicative only")
    if incomplete_path_seen:
        warnings.append("incomplete decision path detected: DTR carries explicit path warnings")

    status = MetaRuntimeStatus.READY
    if synthetic_seen:
        status = MetaRuntimeStatus.HAS_SYNTHETIC_INPUTS
    elif local_replay_seen or incomplete_path_seen:
        status = MetaRuntimeStatus.HAS_PATH_WARNINGS

    return MetaRuntimeResult(
        status=status,
        records=records,
        dtr_summary=dtr_summary,
        cra_report=cra_report,
        break_even_report=break_even_report,
        edge_report=edge_report,
        warnings=tuple(warnings),
    )


def _build_runtime_dtr(runtime_input: MetaRuntimeInput) -> DTRRecord:
    path_warnings = list(runtime_input.path_warnings)
    if not runtime_input.path_complete and not path_warnings:
        path_warnings.append("incomplete decision path")
    if runtime_input.input_source == MetaInputSource.LOCAL_REPLAY:
        path_warnings.append("local_replay input is indicative only")
    if runtime_input.input_source == MetaInputSource.SYNTHETIC:
        path_warnings.append("synthetic input is excluded from edge validation")

    cause_chain = assemble_cause_chain(
        score_step=runtime_input.score_step,
        penalty_steps=runtime_input.penalty_steps,
        penalty_total=runtime_input.penalty_total,
        blocker_steps=runtime_input.blocker_steps,
        ranking_step=runtime_input.ranking_step,
        allocation_step=runtime_input.allocation_step,
        execution_step=runtime_input.execution_step,
        reduction_reason=", ".join(runtime_input.reduction_causes),
    )
    decision_state = encode_state(
        hard_blocked=runtime_input.hard_blocked,
        ranking_rejected=runtime_input.ranking_rejected,
        selected=runtime_input.selected,
        was_reduced=runtime_input.was_reduced,
        is_phantom=runtime_input.is_phantom,
        was_executed=runtime_input.was_executed,
    )
    return build_dtr(
        dtr_id=runtime_input.dtr_id,
        pair=runtime_input.pair,
        engine_id=runtime_input.engine_id,
        decision_state=decision_state,
        raw_score=runtime_input.raw_score,
        penalized_score=runtime_input.penalized_score,
        final_score=runtime_input.final_score,
        hard_blocked=runtime_input.hard_blocked,
        hard_block_reasons=runtime_input.hard_block_reasons,
        ranking_position=runtime_input.ranking_position,
        candidate_size=runtime_input.candidate_size,
        final_size=runtime_input.final_size,
        tier=runtime_input.tier,
        expected_cost=runtime_input.expected_cost,
        realized_cost=runtime_input.realized_cost,
        gross_return=runtime_input.gross_return,
        ce_expected=runtime_input.ce_expected,
        regime=runtime_input.regime,
        runtime_mode=runtime_input.runtime_mode,
        input_source=runtime_input.input_source,
        path_complete=runtime_input.path_complete,
        path_warnings=tuple(path_warnings),
        primary_reason=cause_chain.primary_reason,
        cause_chain=cause_chain.steps,
        timestamp=runtime_input.timestamp,
    )


def _build_cra_results(records: tuple[DTRRecord, ...]) -> tuple[tuple[SterilizationResult, ...], tuple[CRAAlert, ...]]:
    cra_inputs = []
    for record in records:
        if record.decision_state not in {
            DecisionState.SELECTED,
            DecisionState.REDUCED,
            DecisionState.PHANTOM,
            DecisionState.EXECUTED,
        }:
            continue

        original_size = record.candidate_size
        final_size = record.final_size if record.final_size > 0.0 else record.candidate_size
        trace = read_reduction(
            pair=record.pair,
            engine_id=record.engine_id,
            original_size=original_size,
            final_size=final_size,
            reduction_causes=tuple(step for step in record.cause_chain if step.startswith("allocation:")),
            expected_cost=record.expected_cost,
            ce_expected=record.ce_expected,
            holding_hours=0.0,
        )
        risk = estimate_phantom_risk(trace)
        cra_inputs.append(classify_sterilization(trace, risk))

    results = tuple(cra_inputs)
    alerts = build_alerts(results)
    return results, alerts


def _build_break_even_records(records: tuple[DTRRecord, ...]) -> tuple[RealizedBreakEven, ...]:
    be_records: list[RealizedBreakEven] = []
    for record in records:
        if record.decision_state != DecisionState.EXECUTED:
            continue
        be_records.append(
            compute_realized_break_even(
                pair=record.pair,
                engine_id=record.engine_id,
                realized_cost=record.realized_cost,
                expected_cost=record.expected_cost,
                gross_return=record.gross_return,
            )
        )
    return tuple(be_records)


def _build_cost_distributions(records: tuple[RealizedBreakEven, ...]) -> tuple[CostDistribution, ...]:
    by_engine: dict[str, list[float]] = {}
    by_pair: dict[str, list[float]] = {}
    for record in records:
        by_engine.setdefault(record.engine_id, []).append(record.realized_cost)
        by_pair.setdefault(record.pair, []).append(record.realized_cost)

    distributions: list[CostDistribution] = []
    for scope, values in by_engine.items():
        distributions.append(aggregate_costs(scope, tuple(values)))
    for scope, values in by_pair.items():
        distributions.append(aggregate_costs(scope, tuple(values)))
    return tuple(distributions)


def _build_edge_classifications(records: tuple[DTRRecord, ...]) -> tuple[EdgeClassification, ...]:
    grouped: dict[str, list[DTRRecord]] = {}
    for record in records:
        if record.decision_state != DecisionState.EXECUTED:
            continue
        grouped.setdefault(record.engine_id, []).append(record)
        grouped.setdefault(record.pair, []).append(record)
        grouped.setdefault(f"{record.engine_id}:{record.pair}", []).append(record)

    classifications: list[EdgeClassification] = []
    for scope, group in grouped.items():
        sources = {record.input_source for record in group}
        if MetaInputSource.SYNTHETIC in sources:
            continue

        gross_returns = tuple(
            record.gross_return
            for record in group
        )
        costs = tuple(record.realized_cost for record in group)
        aggregate = aggregate_returns(scope, gross_returns, costs)
        uncertainty = estimate_uncertainty(scope, aggregate.net_returns)
        sample = assess_sample_size(scope, aggregate.sample_size)
        cost_distribution = aggregate_costs(scope, costs)
        cluster_utilization = max((record.path_warnings.count("crowded") for record in group), default=0)
        classification = classify_edge(
            uncertainty,
            sample,
            mean_cost_p90=cost_distribution.p90_cost,
            ce_observed=0.0,
            portfolio_context=PortfolioContext(
                cluster_utilization=float(cluster_utilization),
                is_crowded=any("crowded" in warning for record in group for warning in record.path_warnings),
            ),
        )
        if MetaInputSource.LOCAL_REPLAY in sources and classification.status == EdgeStatus.CREDIBLE:
            classification = classification.model_copy(
                update={
                    "status": EdgeStatus.UNDER_SURVEILLANCE,
                    "reason": "local replay inputs are indicative only",
                }
            )
        classifications.append(classification)
    return tuple(classifications)
