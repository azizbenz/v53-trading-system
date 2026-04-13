#!/usr/bin/env python3
"""Monitoring and payload helpers for the governed LOCAL_REPLAY -> SHADOW runner."""

from __future__ import annotations

import json
from pathlib import Path
import sys

from backtest_artifact_import import (
    ArtifactImportSummary,
    ArtifactPayloadRefBundle,
    build_replay_import_projection,
)
from complete_enablers import Build14InfluenceReport, evaluate_build14_shadow_activation
from interface_contracts import PairHealthLevel, ProfileId, RuntimeMode
from local_replay_shadow_models import ShadowEngineRuntimeEvidence
from manifest_registry.profile_registry import get_modules_for_profile
from meta import build_break_even_report, build_cra_report, build_dtr_summary, build_edge_report
from meta_minimal.break_even_dashboard.motor_pair_break_even_view import BreakEvenView
from meta_minimal.cra_monitor.cra_alert_builder import CRAAlert, CRAAlertLevel
from meta_minimal.cra_monitor.sterilization_classifier import (
    SterilizationClass,
    SterilizationResult,
)
from meta_minimal.dtr_core.decision_state_encoder import DecisionState
from meta_minimal.dtr_core.dtr_record_builder import build_dtr
from meta_minimal.edge_tracker_prudent_minimal.edge_status_classifier import (
    EdgeClassification,
    EdgeStatus,
)
from monitoring import (
    Build14Projection,
    Build14ReaderProjection,
    Build9XProjection,
    EngineMetrics,
    MetaMetrics,
    MonitoringSnapshot,
    PairMetrics,
    ReplayImportProjection,
    build_technical_dashboard_payload,
    collect_engine_metrics,
    collect_infra_metrics,
    collect_meta_metrics,
    collect_monitoring_snapshot,
    collect_pair_metrics,
    collect_portfolio_metrics,
    derive_build14_observation_from_snapshot,
)
from protocols import (
    ShadowComponentAssessment,
    ShadowComponentKind,
    ShadowComponentVerdict,
    build_execution_runtime_projection_bridge_projection,
    build_runtime_hook_bridge_projections,
)

def _meta_metrics() -> MetaMetrics:
    dtr_summary = build_dtr_summary(
        (
            build_dtr(
                dtr_id="dtr-local-replay-shadow-1",
                pair="BTCUSDT",
                engine_id="engine_a",
                decision_state=DecisionState.SELECTED,
                timestamp=1_700_000_000.0,
            ),
            build_dtr(
                dtr_id="dtr-local-replay-shadow-2",
                pair="ETHUSDT",
                engine_id="engine_b",
                decision_state=DecisionState.REJECTED_RANKING,
                timestamp=1_700_000_060.0,
            ),
        ),
        total_opportunities=4,
    )
    cra_report = build_cra_report(
        (
            SterilizationResult(
                pair="BTCUSDT",
                engine_id="engine_a",
                classification=SterilizationClass.HEALTHY,
                multiplier=1.0,
                phantom_risk_score=0.10,
            ),
            SterilizationResult(
                pair="ETHUSDT",
                engine_id="engine_b",
                classification=SterilizationClass.PHANTOM_PROBABLE,
                multiplier=0.55,
                phantom_risk_score=0.78,
            ),
        ),
        alerts=(
            CRAAlert(
                scope="engine_b",
                sterilization_rate=0.50,
                total_trades=2,
                sterilized_count=1,
                alert_level=CRAAlertLevel.WARNING,
                dominant_cause="spread_drift",
            ),
        ),
    )
    break_even_report = build_break_even_report(
        (
            BreakEvenView(
                scope="engine_b",
                sample_size=12,
                mean_realized_cost=0.0015,
                mean_expected_cost=0.0010,
                mean_cost_drift=0.0005,
                profitable_rate=0.41,
            ),
        )
    )
    edge_report = build_edge_report(
        (
            EdgeClassification(
                scope="engine_a",
                status=EdgeStatus.CREDIBLE,
                mean_net_return=0.0021,
                standard_error=0.0003,
                sample_size=18,
                sharpe_per_trade=0.31,
                mean_cost_p90=0.0010,
                ce_observed=0.0005,
                cluster_utilization=0.22,
            ),
            EdgeClassification(
                scope="engine_b",
                status=EdgeStatus.DEGRADED,
                mean_net_return=-0.0008,
                standard_error=0.0005,
                sample_size=16,
                sharpe_per_trade=-0.07,
                mean_cost_p90=0.0021,
                ce_observed=-0.0001,
                cluster_utilization=0.35,
            ),
        )
    )
    return collect_meta_metrics(
        dtr_summary,
        cra_report,
        break_even_report,
        edge_report,
        future_learning_diagnostics=0,
        future_learning_hypotheses=0,
    )


def _build14_reader_projections(
    report: Build14InfluenceReport,
) -> tuple[Build14ReaderProjection, ...]:
    return tuple(
        Build14ReaderProjection(
            reader_name=snapshot.reader_name,
            signal_family=snapshot.signal_family.value,
            observed_value=snapshot.observed_value,
            status=snapshot.status.value,
            detail=snapshot.detail,
            evidence_refs=snapshot.evidence_refs,
            structured_log_key=snapshot.structured_log_key,
        )
        for snapshot in report.snapshots
    )


def _build14_projection(snapshot: MonitoringSnapshot) -> Build14Projection:
    report = evaluate_build14_shadow_activation(
        derive_build14_observation_from_snapshot(snapshot)
    )
    snapshots_by_reader = {entry.reader_name: entry for entry in report.snapshots}
    market_toxicity = snapshots_by_reader.get("market_toxicity_snapshot")
    execution_fragility = snapshots_by_reader.get("execution_fragility_score")
    status = (
        "critical"
        if report.signal.severity.value == "critical"
        else "warning"
        if report.signal.severity.value == "elevated"
        else "healthy"
    )
    return Build14Projection(
        status=status,
        hard_state=report.hard_state.value,
        live_promotion_eligible=report.live_promotion_eligible,
        influence_mode=report.signal.influence_mode.value,
        action=report.signal.action.value,
        severity=report.signal.severity.value,
        summary=report.signal.summary,
        market_toxicity_value=market_toxicity.observed_value if market_toxicity is not None else 0.0,
        market_toxicity_status=market_toxicity.status.value if market_toxicity is not None else "nominal",
        execution_fragility_value=(
            execution_fragility.observed_value if execution_fragility is not None else 0.0
        ),
        execution_fragility_status=(
            execution_fragility.status.value if execution_fragility is not None else "nominal"
        ),
        confidence_penalty_weight=0.0,
        recommended_budget_factor=1.0,
        requires_manual_review=report.signal.requires_manual_review,
        candidate_effect=report.signal.candidate_effect,
        reason_codes=report.signal.reason_codes,
        reader_projections=_build14_reader_projections(report),
    )


def _build_component_assessments(
    engine_runtime_evidence: tuple[ShadowEngineRuntimeEvidence, ...],
) -> tuple[ShadowComponentAssessment, ...]:
    engine_ids = ("engine_a", "engine_b", "engine_c", "engine_d")
    build14_ids = (
        "build14_microstructure",
        "build14_regime",
        "build14_covariance",
        "build14_risk_contribution",
        "build14_edge_diversity",
    )
    runtime_evidence_by_component = {
        evidence.component_id: evidence for evidence in engine_runtime_evidence
    }
    assessments: list[ShadowComponentAssessment] = []
    for component_id in engine_ids:
        evidence = runtime_evidence_by_component.get(component_id)
        assessments.append(
            ShadowComponentAssessment(
                component_id=component_id,
                component_kind=ShadowComponentKind.ENGINE,
                verdict=(
                    evidence.verdict
                    if evidence is not None
                    else ShadowComponentVerdict.SHADOW_VALIDATED
                ),
                evidence_summary=(
                    evidence.evidence_summary
                    if evidence is not None
                    else f"{component_id} stayed reproducible in the governed demo run."
                ),
            )
        )
    for component_id in build14_ids:
        assessments.append(
            ShadowComponentAssessment(
                component_id=component_id,
                component_kind=ShadowComponentKind.BUILD14_ENABLER,
                verdict=ShadowComponentVerdict.SHADOW_VALIDATED,
                evidence_summary=f"{component_id} remained available for governed Shadow review.",
            )
        )
    return tuple(assessments)


def _demo_payload_refs(correlation_id: str) -> ArtifactPayloadRefBundle:
    review_export_ref = "exports/local_replay_shadow_review.md"
    feature_bridge_ref = f"feature_bridge:{correlation_id}"
    parity_diagnostics_ref = f"parity_diagnostics:{correlation_id}"
    replay_metrics_ref = f"replay_metrics:{correlation_id}"
    replay_dtr_ref = f"replay_dtr:{correlation_id}"
    return ArtifactPayloadRefBundle(
        review_export_ref=review_export_ref,
        feature_bridge_ref=feature_bridge_ref,
        parity_diagnostics_ref=parity_diagnostics_ref,
        replay_metrics_ref=replay_metrics_ref,
        replay_dtr_ref=replay_dtr_ref,
    )


def _load_json_payload_from_ref(ref: str) -> dict | None:
    candidate = Path(ref)
    if not candidate.is_file():
        return None
    if candidate.suffix.lower() not in {".json", ".jsonl"}:
        return None
    try:
        return json.loads(candidate.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _build_replay_projection(
    import_summary: ArtifactImportSummary,
) -> ReplayImportProjection:
    return build_replay_import_projection(import_summary)


def _write_cli_output(lines: tuple[str, ...]) -> None:
    sys.stdout.write("\n".join(lines))
    sys.stdout.write("\n")


def _resolve_execution_runtime_projection_path(
    *,
    output_dir: Path,
    explicit_path: Path | None,
) -> Path | None:
    if explicit_path is not None:
        return explicit_path
    candidate = output_dir / "local_lab_execution_runtime_projection.json"
    if candidate.is_file():
        return candidate
    return None


def _resolve_regime_lite_assessment_path(
    *,
    output_dir: Path,
    explicit_path: Path | None,
) -> Path | None:
    if explicit_path is not None:
        return explicit_path
    candidate = output_dir / "regime_lite_assessment.json"
    if candidate.is_file():
        return candidate
    return None


def _resolve_regime_lite_safing_recommendation_path(
    *,
    output_dir: Path,
    explicit_path: Path | None,
) -> Path | None:
    if explicit_path is not None:
        return explicit_path
    candidate = output_dir / "regime_lite_safing_recommendation.json"
    if candidate.is_file():
        return candidate
    return None


def _resolve_info_stress_assessment_path(
    *,
    output_dir: Path,
    explicit_path: Path | None,
) -> Path | None:
    if explicit_path is not None:
        return explicit_path
    candidate = output_dir / "info_stress_assessment.json"
    if candidate.is_file():
        return candidate
    return None


def _resolve_daily_pnl_breaker_assessment_path(
    *,
    output_dir: Path,
    explicit_path: Path | None,
) -> Path | None:
    if explicit_path is not None:
        return explicit_path
    candidate = output_dir / "daily_pnl_breaker_assessment.json"
    if candidate.is_file():
        return candidate
    return None


_DEMO_ENGINE_SPECS: tuple[tuple[str, int, float, float, float], ...] = (
    ("engine_a", 3, 8.0, 2.0, 0.0006),
    ("engine_b", 2, 4.0, 2.4, 0.0002),
    ("engine_c", 0, 6.5, 2.3, 0.00035),
    ("engine_d", 0, 5.2, 2.1, 0.00028),
)


def _build_demo_engine_metric(
    *,
    engine_id: str,
    default_emitted_signals: int,
    default_net_edge_bps: float,
    default_expected_cost_bps: float,
    default_ce_expected: float,
    evidence: ShadowEngineRuntimeEvidence | None,
) -> EngineMetrics:
    emitted_signals = 1 if evidence is not None and evidence.emitted_signal else default_emitted_signals
    return collect_engine_metrics(
        engine_id=engine_id,
        emitted_signals=emitted_signals,
        net_edge_bps=evidence.expected_edge_bps if evidence is not None else default_net_edge_bps,
        expected_cost_bps=(
            evidence.expected_cost_bps if evidence is not None else default_expected_cost_bps
        ),
        ce_expected=evidence.ce_expected if evidence is not None else default_ce_expected,
        scoring_summary=evidence.scoring_summary if evidence is not None else "",
        risk_summary=evidence.risk_summary if evidence is not None else "",
        scoring_reason_codes=evidence.scoring_reason_codes if evidence is not None else (),
        risk_reason_codes=evidence.risk_reason_codes if evidence is not None else (),
    )


def _build_demo_engine_metrics(
    engine_runtime_evidence: tuple[ShadowEngineRuntimeEvidence, ...],
) -> tuple[EngineMetrics, ...]:
    runtime_evidence_by_component = {
        evidence.component_id: evidence for evidence in engine_runtime_evidence
    }
    return tuple(
        _build_demo_engine_metric(
            engine_id=engine_id,
            default_emitted_signals=default_emitted_signals,
            default_net_edge_bps=default_net_edge_bps,
            default_expected_cost_bps=default_expected_cost_bps,
            default_ce_expected=default_ce_expected,
            evidence=runtime_evidence_by_component.get(engine_id),
        )
        for (
            engine_id,
            default_emitted_signals,
            default_net_edge_bps,
            default_expected_cost_bps,
            default_ce_expected,
        ) in _DEMO_ENGINE_SPECS
    )


def _build_demo_pair_metrics(
    *,
    active_alert_count: int,
    queue_backlog: int,
) -> tuple[PairMetrics, ...]:
    eth_pair_health = (
        PairHealthLevel.STALE if active_alert_count else PairHealthLevel.HEALTHY
    )
    eth_pair_freshness_ms = 9_000 if active_alert_count else 1_100
    return (
        collect_pair_metrics(
            pair="BTCUSDT",
            health=PairHealthLevel.HEALTHY,
            freshness_ms=900,
            backlog_depth=queue_backlog,
        ),
        collect_pair_metrics(
            pair="ETHUSDT",
            health=eth_pair_health,
            freshness_ms=eth_pair_freshness_ms,
            backlog_depth=queue_backlog,
        ),
    )


def _build_demo_snapshot(
    *,
    correlation_id: str,
    ce_net: float,
    dtr_coverage: float,
    cra_sterilization_rate: float,
    active_alert_count: int,
    queue_backlog: int,
    engine_runtime_evidence: tuple[ShadowEngineRuntimeEvidence, ...],
) -> MonitoringSnapshot:
    return collect_monitoring_snapshot(
        correlation_id=correlation_id,
        profile=ProfileId.COMPLETE,
        runtime_mode=RuntimeMode.SHADOW,
        timestamp_ms=1_700_000_000_000,
        portfolio=collect_portfolio_metrics(
            allocated_opportunities=2,
            gross_capacity_used_pct=35.0,
            loss_capacity_used_pct=8.0,
            beta_utilization=0.30,
            capital_deployed_usdt=1200.0,
            ce_net=ce_net,
        ),
        infra=collect_infra_metrics(
            queue_backlog=queue_backlog,
            stale_pairs=("ETHUSDT",) if active_alert_count else (),
            stale_spike_count=1 if active_alert_count else 0,
        ),
        meta=_meta_metrics().model_copy(
            update={
                "dtr_coverage": dtr_coverage,
                "cra_sterilization_rate": cra_sterilization_rate,
            }
        ),
        engines=_build_demo_engine_metrics(engine_runtime_evidence),
        pairs=_build_demo_pair_metrics(
            active_alert_count=active_alert_count,
            queue_backlog=queue_backlog,
        ),
    )


def _build_demo_payload(
    *,
    correlation_id: str,
    ce_net: float,
    dtr_coverage: float,
    cra_sterilization_rate: float,
    active_alert_count: int,
    queue_backlog: int,
    output_dir: Path,
    replay_projection: ReplayImportProjection,
    execution_runtime_projection_path: Path | None = None,
    engine_runtime_evidence: tuple[ShadowEngineRuntimeEvidence, ...] = (),
) -> object:
    snapshot = _build_demo_snapshot(
        correlation_id=correlation_id,
        ce_net=ce_net,
        dtr_coverage=dtr_coverage,
        cra_sterilization_rate=cra_sterilization_rate,
        active_alert_count=active_alert_count,
        queue_backlog=queue_backlog,
        engine_runtime_evidence=engine_runtime_evidence,
    )
    active_modules = tuple(
        module.module_name for module in get_modules_for_profile(ProfileId.COMPLETE)
    )
    build14_projection = _build14_projection(snapshot)
    execution_runtime_projection_bridge_projection = (
        build_execution_runtime_projection_bridge_projection(
            execution_runtime_projection_path=execution_runtime_projection_path,
        )
    )
    return build_technical_dashboard_payload(
        snapshot,
        active_modules=active_modules,
        active_engines=("engine_a", "engine_b", "engine_c", "engine_d"),
        build9x_projection=Build9XProjection(
            status="info",
            diagnostics_count=0,
            diagnostics_summary="No diagnostic report",
            open_hypotheses=0,
            total_hypotheses=0,
            near_miss_count=0,
            replay_candidate_count=0,
            memory_record_count=1,
            latest_memory_summary="Governed replay candidate prepared for Shadow.",
            review_export_ready=True,
            review_export_ref="exports/local_replay_shadow_review.md",
        ),
        runtime_hook_bridge_projections=build_runtime_hook_bridge_projections(
            compiled_registry_state_dir=output_dir
        ),
        execution_runtime_projection_bridge_projection=(
            execution_runtime_projection_bridge_projection
        ),
        replay_projection=replay_projection,
        build14_projection=build14_projection,
    )
