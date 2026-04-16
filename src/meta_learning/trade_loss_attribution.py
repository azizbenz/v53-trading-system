"""Governed per-trade loss attribution for Local IA Lab post-trade review."""

from __future__ import annotations

from collections import Counter

from meta_learning.contracts import (
    DiagnosticResult,
    TradeLossAttribution,
    TradeLossAttributionReport,
    TradeLossEvidence,
    TradeLossFailureModeSummary,
)
from meta_minimal.break_even_dashboard.break_even_reporter import BreakEvenReport
from meta_minimal.cra_monitor.cra_reporter import CRAReport
from meta_minimal.dtr_core.decision_state_encoder import DecisionState
from meta_minimal.dtr_core.dtr_record_builder import DTRRecord
from meta_minimal.dtr_core.dtr_reporter import DTRSummary
from meta_minimal.edge_tracker_prudent_minimal.edge_reporter import EdgeReport

_EDGE_THRESHOLD_IDS = ("THR-E01", "THR-E02")


def _net_return_after_cost(record: DTRRecord) -> float:
    return float(record.gross_return - record.realized_cost)


def _linked_diagnostic_categories(diagnostics: tuple[DiagnosticResult, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(diagnostic.category for diagnostic in diagnostics))


def _build_not_executed_attribution(
    record: DTRRecord,
    linked_categories: tuple[str, ...],
) -> TradeLossAttribution:
    return TradeLossAttribution(
        dtr_id=record.dtr_id,
        pair=record.pair,
        engine_id=record.engine_id,
        decision_state=record.decision_state.value,
        attribution_status="not_executed",
        gross_return=record.gross_return,
        realized_cost=record.realized_cost,
        net_return_after_cost=_net_return_after_cost(record),
        primary_failure_mode="not_executed",
        why_losing=("trade_not_executed_no_loss_to_attribute",),
        preventive_action="Review the cause chain before changing thresholds; this DTR did not become a live loss.",
        action_scope=f"{record.engine_id}:{record.pair}",
        confidence=1.0,
        linked_diagnostic_categories=linked_categories,
        evidence=(
            TradeLossEvidence(
                source="dtr_record",
                reference=record.dtr_id,
                observation=f"decision_state={record.decision_state.value}",
            ),
        ),
    )


def _build_not_loss_attribution(
    record: DTRRecord,
    linked_categories: tuple[str, ...],
) -> TradeLossAttribution:
    net_return = _net_return_after_cost(record)
    return TradeLossAttribution(
        dtr_id=record.dtr_id,
        pair=record.pair,
        engine_id=record.engine_id,
        decision_state=record.decision_state.value,
        attribution_status="not_loss",
        gross_return=record.gross_return,
        realized_cost=record.realized_cost,
        net_return_after_cost=net_return,
        primary_failure_mode="not_loss",
        why_losing=("profitable_after_realized_costs",),
        preventive_action="No preventive action required; keep collecting governed evidence on this scope.",
        action_scope=f"{record.engine_id}:{record.pair}",
        confidence=1.0,
        linked_diagnostic_categories=linked_categories,
        evidence=(
            TradeLossEvidence(
                source="dtr_record",
                reference=record.dtr_id,
                observation=f"net_return_after_cost={net_return:.6f}",
            ),
        ),
    )


def _cost_drift_applies(record: DTRRecord, break_even_report: BreakEvenReport) -> bool:
    if record.expected_cost <= 0.0:
        return break_even_report.has_cost_drift_alert
    return record.realized_cost > record.expected_cost * 1.10 or break_even_report.has_cost_drift_alert


def _sterilization_applies(record: DTRRecord, cra_report: CRAReport) -> bool:
    return (
        record.final_size < record.candidate_size
        or cra_report.sterilization_rate >= 0.20
        or any(step.startswith("allocation:") for step in record.cause_chain)
    )


def _edge_degraded_applies(record: DTRRecord, edge_report: EdgeReport) -> bool:
    return record.ce_expected <= 0.0 or record.final_score <= 0.0 or edge_report.degraded_count > 0


def _trace_coverage_applies(record: DTRRecord, dtr_summary: DTRSummary) -> bool:
    return not record.path_complete or dtr_summary.dtr_coverage < 0.80


def _build_loss_base_kwargs(
    record: DTRRecord,
    *,
    linked_categories: tuple[str, ...],
    net_return: float,
) -> dict[str, object]:
    return {
        "dtr_id": record.dtr_id,
        "pair": record.pair,
        "engine_id": record.engine_id,
        "decision_state": record.decision_state.value,
        "attribution_status": "loss",
        "gross_return": record.gross_return,
        "realized_cost": record.realized_cost,
        "net_return_after_cost": net_return,
        "action_scope": f"{record.engine_id}:{record.pair}",
        "linked_diagnostic_categories": linked_categories,
    }


def _build_cost_drift_loss_attribution(
    record: DTRRecord,
    *,
    linked_categories: tuple[str, ...],
    net_return: float,
    break_even_report: BreakEvenReport,
) -> TradeLossAttribution:
    return TradeLossAttribution(
        **_build_loss_base_kwargs(
            record,
            linked_categories=linked_categories,
            net_return=net_return,
        ),
        primary_failure_mode="cost_drift",
        why_losing=(
            "realized_cost_exceeded_expected_cost",
            "net_return_after_cost_turned_negative",
        ),
        preventive_action="Raise the fee-aware edge gate and recalibrate realized execution costs before replay promotion.",
        confidence=0.90,
        recommended_threshold_ids=_EDGE_THRESHOLD_IDS,
        evidence=(
            TradeLossEvidence(
                source="dtr_record",
                reference=record.dtr_id,
                observation=(
                    f"expected_cost={record.expected_cost:.6f}, "
                    f"realized_cost={record.realized_cost:.6f}, "
                    f"net_return_after_cost={net_return:.6f}"
                ),
            ),
            TradeLossEvidence(
                source="break_even_report",
                reference="cost_drift_alert",
                observation=f"has_cost_drift_alert={break_even_report.has_cost_drift_alert}",
            ),
        ),
    )


def _build_trace_coverage_loss_attribution(
    record: DTRRecord,
    *,
    linked_categories: tuple[str, ...],
    net_return: float,
    dtr_summary: DTRSummary,
) -> TradeLossAttribution:
    return TradeLossAttribution(
        **_build_loss_base_kwargs(
            record,
            linked_categories=linked_categories,
            net_return=net_return,
        ),
        primary_failure_mode="trace_coverage",
        why_losing=("diagnostic_trace_is_incomplete_for_high_confidence_loss_attribution",),
        preventive_action="Do not mutate production gates yet; improve trace capture and rerun the governed replay first.",
        confidence=0.82,
        evidence=(
            TradeLossEvidence(
                source="dtr_record",
                reference=record.dtr_id,
                observation=f"path_complete={record.path_complete}",
            ),
            TradeLossEvidence(
                source="dtr_summary",
                reference="dtr_coverage",
                observation=f"dtr_coverage={dtr_summary.dtr_coverage:.6f}",
            ),
        ),
    )


def _build_sterilization_loss_attribution(
    record: DTRRecord,
    *,
    linked_categories: tuple[str, ...],
    net_return: float,
    cra_report: CRAReport,
) -> TradeLossAttribution:
    return TradeLossAttribution(
        **_build_loss_base_kwargs(
            record,
            linked_categories=linked_categories,
            net_return=net_return,
        ),
        primary_failure_mode="sterilization",
        why_losing=(
            "trade_was_reduced_or_crowded_before_execution",
            "realized_value_was_destroyed_by_execution_pressure",
        ),
        preventive_action="Reduce size earlier or suspend this pair/engine scope when sterilization remains elevated.",
        confidence=0.78,
        evidence=(
            TradeLossEvidence(
                source="dtr_record",
                reference=record.dtr_id,
                observation=(
                    f"candidate_size={record.candidate_size:.6f}, "
                    f"final_size={record.final_size:.6f}, "
                    f"cause_chain={','.join(record.cause_chain) or 'none'}"
                ),
            ),
            TradeLossEvidence(
                source="cra_report",
                reference="sterilization_rate",
                observation=f"sterilization_rate={cra_report.sterilization_rate:.6f}",
            ),
        ),
    )


def _build_edge_degraded_loss_attribution(
    record: DTRRecord,
    *,
    linked_categories: tuple[str, ...],
    net_return: float,
    edge_report: EdgeReport,
) -> TradeLossAttribution:
    return TradeLossAttribution(
        **_build_loss_base_kwargs(
            record,
            linked_categories=linked_categories,
            net_return=net_return,
        ),
        primary_failure_mode="edge_degraded",
        why_losing=(
            "expected_edge_was_too_weak_for_realized_market_conditions",
            "scope_requires_tighter_minimum_edge_before_execution",
        ),
        preventive_action="Tighten the minimum edge gate and keep this scope under surveillance until replay evidence improves.",
        confidence=0.74,
        recommended_threshold_ids=_EDGE_THRESHOLD_IDS,
        evidence=(
            TradeLossEvidence(
                source="dtr_record",
                reference=record.dtr_id,
                observation=(
                    f"ce_expected={record.ce_expected:.6f}, "
                    f"final_score={record.final_score:.6f}, "
                    f"net_return_after_cost={net_return:.6f}"
                ),
            ),
            TradeLossEvidence(
                source="edge_report",
                reference="degraded_count",
                observation=f"degraded_count={edge_report.degraded_count}",
            ),
        ),
    )


def _build_unclassified_loss_attribution(
    record: DTRRecord,
    *,
    linked_categories: tuple[str, ...],
    net_return: float,
) -> TradeLossAttribution:
    return TradeLossAttribution(
        **_build_loss_base_kwargs(
            record,
            linked_categories=linked_categories,
            net_return=net_return,
        ),
        primary_failure_mode="unclassified_loss",
        why_losing=("manual_review_required_for_unclassified_loss",),
        preventive_action="Review the governed DTR manually before changing runtime behavior.",
        confidence=0.40,
        evidence=(
            TradeLossEvidence(
                source="dtr_record",
                reference=record.dtr_id,
                observation=(
                    f"primary_reason={record.primary_reason or 'none'}, "
                    f"cause_chain={','.join(record.cause_chain) or 'none'}"
                ),
            ),
        ),
    )


def _build_loss_attribution(
    record: DTRRecord,
    *,
    linked_categories: tuple[str, ...],
    dtr_summary: DTRSummary,
    cra_report: CRAReport,
    break_even_report: BreakEvenReport,
    edge_report: EdgeReport,
) -> TradeLossAttribution:
    net_return = _net_return_after_cost(record)

    if _cost_drift_applies(record, break_even_report):
        return _build_cost_drift_loss_attribution(
            record,
            linked_categories=linked_categories,
            net_return=net_return,
            break_even_report=break_even_report,
        )

    if _trace_coverage_applies(record, dtr_summary):
        return _build_trace_coverage_loss_attribution(
            record,
            linked_categories=linked_categories,
            net_return=net_return,
            dtr_summary=dtr_summary,
        )

    if _sterilization_applies(record, cra_report):
        return _build_sterilization_loss_attribution(
            record,
            linked_categories=linked_categories,
            net_return=net_return,
            cra_report=cra_report,
        )

    if _edge_degraded_applies(record, edge_report):
        return _build_edge_degraded_loss_attribution(
            record,
            linked_categories=linked_categories,
            net_return=net_return,
            edge_report=edge_report,
        )

    return _build_unclassified_loss_attribution(
        record,
        linked_categories=linked_categories,
        net_return=net_return,
    )


def build_trade_loss_attribution_report(
    correlation_id: str,
    *,
    dtr_records: tuple[DTRRecord, ...],
    diagnostics: tuple[DiagnosticResult, ...],
    dtr_summary: DTRSummary,
    cra_report: CRAReport,
    break_even_report: BreakEvenReport,
    edge_report: EdgeReport,
) -> TradeLossAttributionReport:
    """Build a governed per-trade loss attribution sidecar."""

    linked_categories = _linked_diagnostic_categories(diagnostics)
    attributions: list[TradeLossAttribution] = []
    failure_modes: Counter[str] = Counter()
    executed_records = 0
    losing_trade_count = 0

    for record in dtr_records:
        if record.decision_state != DecisionState.EXECUTED:
            attribution = _build_not_executed_attribution(record, linked_categories)
        else:
            executed_records += 1
            if _net_return_after_cost(record) > 0.0:
                attribution = _build_not_loss_attribution(record, linked_categories)
            else:
                attribution = _build_loss_attribution(
                    record,
                    linked_categories=linked_categories,
                    dtr_summary=dtr_summary,
                    cra_report=cra_report,
                    break_even_report=break_even_report,
                    edge_report=edge_report,
                )
                losing_trade_count += 1
                failure_modes[attribution.primary_failure_mode] += 1
        attributions.append(attribution)

    ordered_failure_modes = tuple(
        TradeLossFailureModeSummary(failure_mode=failure_mode, count=count)
        for failure_mode, count in sorted(
            failure_modes.items(),
            key=lambda item: (-item[1], item[0]),
        )
    )
    return TradeLossAttributionReport(
        correlation_id=correlation_id,
        total_records=len(dtr_records),
        executed_records=executed_records,
        losing_trade_count=losing_trade_count,
        attribution_ready=bool(attributions),
        failure_modes=ordered_failure_modes,
        attributions=tuple(attributions),
    )


__all__ = [
    "build_trade_loss_attribution_report",
]
