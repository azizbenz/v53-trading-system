"""Runtime tests for the minimal real Build-11 Shadow flow."""

from __future__ import annotations

from interface_contracts import ProfileId, RuntimeMode
from monitoring import (
    AlertProjection,
    Build9MetaProjection,
    Build9XProjection,
    PortfolioMetrics,
    ReplayImportProjection,
    SystemProjection,
    TechnicalDashboardPayload,
)
from protocols import (
    ShadowVerdict,
    build_shadow_input_from_payloads,
    run_shadow_validation,
)


def _payload(
    *,
    correlation_id: str,
    ce_net: float,
    dtr_coverage: float,
    cra_sterilization_rate: float,
    break_even_scope_count: int,
    edge_degraded_count: int,
    active_alert_count: int,
    queue_backlog: int,
    diagnostics_count: int = 0,
    open_hypotheses: int = 0,
    replay_candidate_count: int = 0,
    review_export_ready: bool = False,
    validation_status: str = "accepted",
    artifact_id: str = "artifact-1",
    lineage_version: str = "a.v1.0.r1",
    rejection_reasons: tuple[str, ...] = (),
) -> TechnicalDashboardPayload:
    return TechnicalDashboardPayload(
        timestamp_ms=1_700_000_000_000,
        correlation_id=correlation_id,
        profile=ProfileId.LIGHT,
        runtime_mode=RuntimeMode.SHADOW,
        system=SystemProjection(
            headline_status="healthy",
            active_modules=("monitoring", "ui", "meta_learning", "backtest_artifact_import", "protocols"),
            active_engines=("engine_a", "engine_b"),
            stale_engines=(),
            build9x_status="warning" if diagnostics_count else "info",
            shadow_status="planned",
            replay_import_status="healthy" if validation_status == "accepted" else "warning",
            governed_extensions_detail="Build-9X, Shadow, and replay/import remain governed.",
        ),
        portfolio=PortfolioMetrics(
            allocated_opportunities=2,
            gross_capacity_used_pct=35.0,
            loss_capacity_used_pct=8.0,
            beta_utilization=0.3,
            capital_deployed_usdt=1200.0,
            ce_net=ce_net,
        ),
        build9_meta=Build9MetaProjection(
            dtr_coverage=dtr_coverage,
            dtr_status="healthy",
            cra_sterilization_rate=cra_sterilization_rate,
            cra_alert_count=1 if cra_sterilization_rate >= 0.2 else 0,
            cra_status="warning" if cra_sterilization_rate >= 0.2 else "healthy",
            break_even_state="stable" if break_even_scope_count == 0 else "drift_alert",
            break_even_status="healthy" if break_even_scope_count == 0 else "warning",
            break_even_drift_scopes=tuple(f"scope-{index}" for index in range(break_even_scope_count)),
            edge_credible_count=1,
            edge_degraded_count=edge_degraded_count,
            edge_surveillance_count=0,
            edge_status="warning" if edge_degraded_count else "healthy",
        ),
        build9x=Build9XProjection(
            status="warning" if diagnostics_count else "info",
            diagnostics_count=diagnostics_count,
            diagnostics_summary="Governed diagnostics ready" if diagnostics_count else "No diagnostic report",
            open_hypotheses=open_hypotheses,
            total_hypotheses=open_hypotheses,
            near_miss_count=0,
            replay_candidate_count=replay_candidate_count,
            memory_record_count=1 if diagnostics_count else 0,
            latest_memory_summary="Governed memory" if diagnostics_count else "No memory records",
            review_export_ready=review_export_ready,
            review_export_ref="exports/review.md" if review_export_ready else "",
        ),
        replay_import=ReplayImportProjection(
            status="healthy" if validation_status == "accepted" else "warning",
            artifact_id=artifact_id,
            artifact_kind="review_packet" if artifact_id != "none" else "No replay bundle exported",
            lineage_version=lineage_version,
            lifecycle_state="exported" if artifact_id != "none" else "Awaiting LOCAL_REPLAY artifact",
            validation_status=validation_status,
            review_state="pending" if validation_status == "accepted" else "needs_revision",
            rejection_reasons=rejection_reasons,
        ),
        alerts=AlertProjection(
            headline_status="healthy",
            active_alert_count=active_alert_count,
            alert_ids=tuple(f"alert-{index}" for index in range(active_alert_count)),
            queue_backlog=queue_backlog,
            stale_pair_count=0,
            stale_pairs=(),
            backlog_stale_status="warning" if queue_backlog > 0 else "healthy",
            dtr_loss_count=0,
            log_loss_count=0,
            break_even_drift_scope_count=break_even_scope_count,
            edge_degraded_count=edge_degraded_count,
            loss_drift_status="warning" if edge_degraded_count else "healthy",
        ),
    )


def test_build_shadow_input_from_payloads_maps_baseline_and_candidate_sets():
    baseline_payload = _payload(
        correlation_id="corr-shadow-baseline",
        ce_net=0.0012,
        dtr_coverage=0.84,
        cra_sterilization_rate=0.10,
        break_even_scope_count=1,
        edge_degraded_count=0,
        active_alert_count=2,
        queue_backlog=20,
    )
    candidate_payload = _payload(
        correlation_id="corr-shadow-candidate",
        ce_net=0.0010,
        dtr_coverage=0.81,
        cra_sterilization_rate=0.12,
        break_even_scope_count=1,
        edge_degraded_count=0,
        active_alert_count=3,
        queue_backlog=28,
        diagnostics_count=2,
        open_hypotheses=1,
        replay_candidate_count=1,
        review_export_ready=True,
    )

    shadow_input = build_shadow_input_from_payloads(
        baseline_payload,
        candidate_payload,
        truth_ref="truth-1",
        validation_ref="validation-1",
    )

    assert shadow_input.correlation_id == "corr-shadow-candidate"
    assert shadow_input.truth_set.truth_ref == "truth-1"
    assert shadow_input.validation_set.validation_ref == "validation-1"
    assert shadow_input.validation_set.accepted_import is True
    assert shadow_input.validation_set.build9x_diagnostics_count == 2
    assert shadow_input.validation_set.open_hypotheses == 1


def test_run_shadow_validation_accepts_candidate_within_thresholds():
    baseline_payload = _payload(
        correlation_id="corr-shadow-baseline",
        ce_net=0.0012,
        dtr_coverage=0.84,
        cra_sterilization_rate=0.10,
        break_even_scope_count=1,
        edge_degraded_count=0,
        active_alert_count=2,
        queue_backlog=20,
    )
    candidate_payload = _payload(
        correlation_id="corr-shadow-candidate",
        ce_net=0.0009,
        dtr_coverage=0.81,
        cra_sterilization_rate=0.15,
        break_even_scope_count=1,
        edge_degraded_count=0,
        active_alert_count=3,
        queue_backlog=35,
        diagnostics_count=2,
        open_hypotheses=1,
        replay_candidate_count=1,
        review_export_ready=True,
    )

    summary = run_shadow_validation(
        build_shadow_input_from_payloads(
            baseline_payload,
            candidate_payload,
            truth_ref="truth-1",
            validation_ref="validation-1",
        )
    )

    assert summary.decision.accepted is True
    assert summary.decision.verdict == ShadowVerdict.ACCEPTED
    assert summary.blocking_comparison_count == 0
    assert summary.divergent_comparison_count >= 1


def test_run_shadow_validation_requires_review_export_when_build9x_signals_exist():
    baseline_payload = _payload(
        correlation_id="corr-shadow-baseline",
        ce_net=0.0012,
        dtr_coverage=0.84,
        cra_sterilization_rate=0.10,
        break_even_scope_count=1,
        edge_degraded_count=0,
        active_alert_count=2,
        queue_backlog=20,
    )
    candidate_payload = _payload(
        correlation_id="corr-shadow-candidate",
        ce_net=0.0010,
        dtr_coverage=0.82,
        cra_sterilization_rate=0.12,
        break_even_scope_count=1,
        edge_degraded_count=0,
        active_alert_count=2,
        queue_backlog=21,
        diagnostics_count=1,
        open_hypotheses=1,
        replay_candidate_count=0,
        review_export_ready=False,
    )

    summary = run_shadow_validation(
        build_shadow_input_from_payloads(
            baseline_payload,
            candidate_payload,
            truth_ref="truth-1",
            validation_ref="validation-1",
        )
    )

    assert summary.decision.accepted is False
    assert summary.decision.verdict == ShadowVerdict.NEEDS_REVIEW
    assert summary.decision.blocking_reasons == (
        "Build-9X review export must be ready before accepting Shadow",
    )


def test_run_shadow_validation_blocks_missing_import_lineage():
    baseline_payload = _payload(
        correlation_id="corr-shadow-baseline",
        ce_net=0.0012,
        dtr_coverage=0.84,
        cra_sterilization_rate=0.10,
        break_even_scope_count=1,
        edge_degraded_count=0,
        active_alert_count=2,
        queue_backlog=20,
    )
    candidate_payload = _payload(
        correlation_id="corr-shadow-candidate",
        ce_net=0.0010,
        dtr_coverage=0.82,
        cra_sterilization_rate=0.12,
        break_even_scope_count=1,
        edge_degraded_count=0,
        active_alert_count=2,
        queue_backlog=22,
        diagnostics_count=0,
        open_hypotheses=0,
        replay_candidate_count=0,
        review_export_ready=False,
        validation_status="needs_revision",
        artifact_id="none",
        lineage_version="n/a",
        rejection_reasons=("artifact review incomplete",),
    )

    summary = run_shadow_validation(
        build_shadow_input_from_payloads(
            baseline_payload,
            candidate_payload,
            truth_ref="truth-1",
            validation_ref="validation-1",
        )
    )

    assert summary.decision.verdict == ShadowVerdict.BLOCKED
    assert "candidate import must be accepted before Shadow" in summary.decision.blocking_reasons
    assert "candidate lineage_version is required" in summary.decision.blocking_reasons


def test_run_shadow_validation_rejects_blocking_metric_divergence():
    baseline_payload = _payload(
        correlation_id="corr-shadow-baseline",
        ce_net=0.0012,
        dtr_coverage=0.84,
        cra_sterilization_rate=0.10,
        break_even_scope_count=1,
        edge_degraded_count=0,
        active_alert_count=2,
        queue_backlog=20,
    )
    candidate_payload = _payload(
        correlation_id="corr-shadow-candidate",
        ce_net=0.0001,
        dtr_coverage=0.70,
        cra_sterilization_rate=0.28,
        break_even_scope_count=1,
        edge_degraded_count=0,
        active_alert_count=2,
        queue_backlog=22,
        diagnostics_count=0,
        open_hypotheses=0,
        replay_candidate_count=0,
        review_export_ready=False,
    )

    summary = run_shadow_validation(
        build_shadow_input_from_payloads(
            baseline_payload,
            candidate_payload,
            truth_ref="truth-1",
            validation_ref="validation-1",
        )
    )

    assert summary.decision.verdict == ShadowVerdict.REJECTED
    assert summary.blocking_comparison_count >= 2
    assert any("dtr_coverage_drop" in reason for reason in summary.decision.blocking_reasons)

