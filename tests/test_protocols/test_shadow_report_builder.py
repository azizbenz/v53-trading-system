"""Tests for protocols.shadow_report_builder."""

from __future__ import annotations

from interface_contracts import ProfileId, PromotionState, ReviewState, RuntimeMode
from monitoring import (
    AlertProjection,
    Build14Projection,
    Build14ReaderProjection,
    Build9MetaProjection,
    Build9XProjection,
    OperatorRuntimeProjection,
    PortfolioMetrics,
    ReplayImportProjection,
    SystemProjection,
    TechnicalDashboardPayload,
)
from protocols import (
    ShadowDecision,
    ShadowRunState,
    ShadowRunSummary,
    ShadowVerdict,
    build_shadow_daily_metrics_summary,
)


def _payload() -> TechnicalDashboardPayload:
    return TechnicalDashboardPayload(
        timestamp_ms=1_700_000_000_000,
        correlation_id="corr-shadow-builder",
        profile=ProfileId.LIGHT,
        runtime_mode=RuntimeMode.SHADOW,
        system=SystemProjection(
            headline_status="healthy",
            active_modules=("monitoring", "protocols"),
            active_engines=("engine_a", "engine_b", "engine_c", "engine_d"),
            shadow_status="healthy",
            build14_status="healthy",
            replay_import_status="healthy",
        ),
        portfolio=PortfolioMetrics(
            allocated_opportunities=2,
            gross_capacity_used_pct=20.0,
            loss_capacity_used_pct=5.0,
            beta_utilization=0.2,
            capital_deployed_usdt=1_000.0,
            ce_net=0.001,
            pnl_net_usdt=25.0,
            dominant_cluster="majors",
        ),
        build9_meta=Build9MetaProjection(
            dtr_coverage=0.84,
            dtr_status="healthy",
            cra_sterilization_rate=0.08,
            cra_alert_count=0,
            cra_status="healthy",
            break_even_state="stable",
            break_even_status="healthy",
            edge_credible_count=1,
            edge_degraded_count=0,
            edge_surveillance_count=0,
            edge_status="healthy",
        ),
        build9x=Build9XProjection(
            status="info",
            diagnostics_count=0,
            diagnostics_summary="No diagnostic report",
            open_hypotheses=0,
            total_hypotheses=0,
            near_miss_count=0,
            replay_candidate_count=0,
            memory_record_count=0,
            latest_memory_summary="No memory records",
            review_export_ready=True,
            review_export_ref="exports/review.md",
        ),
        replay_import=ReplayImportProjection(
            status="healthy",
            artifact_id="artifact-1",
            artifact_kind="review_packet",
            lineage_version="a.v1.0.r1",
            lifecycle_state="validated",
            validation_status="accepted",
            review_state="pending",
        ),
        alerts=AlertProjection(
            headline_status="healthy",
            active_alert_count=1,
            alert_ids=("alert-1",),
            queue_backlog=4,
            stale_pair_count=0,
            stale_pairs=(),
            backlog_stale_status="healthy",
            dtr_loss_count=0,
            log_loss_count=0,
            break_even_drift_scope_count=0,
            edge_degraded_count=0,
            loss_drift_status="healthy",
            operator_runtime=OperatorRuntimeProjection(event_count=1),
        ),
    )


def _summary() -> ShadowRunSummary:
    return ShadowRunSummary(
        run_id="shadow-run-1",
        correlation_id="corr-shadow-builder",
        run_state=ShadowRunState.COMPLETED,
        truth_set_ref="truth-1",
        validation_set_ref="validation-1",
        decision=ShadowDecision(
            accepted=True,
            verdict=ShadowVerdict.ACCEPTED,
            normalized_promotion_state=PromotionState.SHADOW_CANDIDATE,
            review_state=ReviewState.PENDING,
            manual_review_required=False,
        ),
        active_engines=("engine_a", "engine_b", "engine_c", "engine_d"),
        build14_status="healthy",
        shadow_days_completed=30,
        shadow_required_days=30,
        shadow_report_ready=True,
        inter_engine_comparison_ready=True,
        build14_contribution_ready=True,
    )


def test_build_shadow_daily_metrics_summary_prefers_replay_metrics_payload():
    metrics = build_shadow_daily_metrics_summary(
        _payload(),
        _summary(),
        capital_simulated_usdt=10_000.0,
        replay_metrics_payload={
            "dtr_coverage": 0.625,
            "total_opportunities": 8,
            "total_records": 5,
            "hard_blocked_count": 2,
            "phantom_count": 3,
        },
        hard_block_rate=0.0,
        phantom_trade_count=0,
    )

    assert metrics["dtr_coverage"] == 0.625
    assert metrics["hard_block_rate"] == 0.25
    assert metrics["phantom_trade_count"] == 3.0
    assert metrics["dtr_complete"] == 0.0


def test_build_shadow_daily_metrics_summary_projects_build14_reader_metrics():
    payload = _payload().model_copy(
        update={
            "build14": Build14Projection(
                status="warning",
                hard_state="shadow_enabled",
                influence_mode="shadow_enabled",
                action="shadow_apply",
                severity="elevated",
                summary="Build-14 readers remain shadow-only but visible",
                market_toxicity_value=0.46,
                market_toxicity_status="elevated",
                execution_fragility_value=0.42,
                execution_fragility_status="elevated",
                confidence_penalty_weight=0.0,
                recommended_budget_factor=1.0,
                requires_manual_review=False,
                candidate_effect="shadow_enabled",
                reader_projections=(
                    Build14ReaderProjection(
                        reader_name="market_toxicity_snapshot",
                        signal_family="microstructure",
                        observed_value=0.46,
                        status="elevated",
                        detail="backlog=4, stale_pairs=0, losses=0, cra=8.00%",
                        structured_log_key="build14.shadow_enabled.market_toxicity",
                    ),
                    Build14ReaderProjection(
                        reader_name="competition_monitor",
                        signal_family="risk",
                        observed_value=0.18,
                        status="nominal",
                        detail="competition_density=0.18 / stale_pair_count=0 / ce_net=0.0010",
                        structured_log_key="build14.shadow_enabled.competition_monitor",
                    ),
                ),
            )
        }
    )

    metrics = build_shadow_daily_metrics_summary(
        payload,
        _summary(),
        capital_simulated_usdt=10_000.0,
    )

    assert metrics["build14_reader.market_toxicity_snapshot.observed_value"] == 0.46
    assert metrics["build14_reader.market_toxicity_snapshot.severity_score"] == 0.5
    assert (
        metrics["build14_reader.market_toxicity_snapshot.structured_log_key"]
        == "build14.shadow_enabled.market_toxicity"
    )
    assert metrics["build14_reader.competition_monitor.signal_family"] == "risk"
