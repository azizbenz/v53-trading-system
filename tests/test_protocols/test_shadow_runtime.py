"""Runtime tests for the governed Build-11 Shadow gate."""

from __future__ import annotations

import pytest

from interface_contracts import ProfileId, RuntimeMode
from local_replay_runtime import LocalReplayRuntimeEvidence
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
    ShadowComponentAssessment,
    ShadowComponentHardState,
    ShadowComponentKind,
    ShadowComponentVerdict,
    ShadowInput,
    ShadowInputError,
    ShadowRuntimeEvidence,
    ShadowTruthSet,
    ShadowValidationSet,
    ShadowVerdict,
    build_shadow_runtime_evidence,
    build_shadow_input_from_payloads,
    run_shadow_validation,
)


def _component_assessments(
    *,
    dormant_component_ids: tuple[str, ...] = (),
) -> tuple[ShadowComponentAssessment, ...]:
    dormant = set(dormant_component_ids)
    engine_ids = ("engine_a", "engine_b")
    build14_ids = (
        "build14_microstructure",
        "build14_regime",
        "build14_covariance",
        "build14_risk_contribution",
        "build14_edge_diversity",
    )
    assessments: list[ShadowComponentAssessment] = []
    for component_id in engine_ids:
        assessments.append(
            ShadowComponentAssessment(
                component_id=component_id,
                component_kind=ShadowComponentKind.ENGINE,
                hard_state=ShadowComponentHardState.SHADOW_ENABLED,
                verdict=(
                    ShadowComponentVerdict.DORMANT
                    if component_id in dormant
                    else ShadowComponentVerdict.SHADOW_VALIDATED
                ),
                evidence_summary=f"{component_id} shadow evidence rendered",
            )
        )
    for component_id in build14_ids:
        assessments.append(
            ShadowComponentAssessment(
                component_id=component_id,
                component_kind=ShadowComponentKind.BUILD14_ENABLER,
                hard_state=ShadowComponentHardState.SHADOW_ENABLED,
                verdict=(
                    ShadowComponentVerdict.DORMANT
                    if component_id in dormant
                    else ShadowComponentVerdict.SHADOW_VALIDATED
                ),
                evidence_summary=f"{component_id} shadow evidence rendered",
            )
        )
    return tuple(assessments)


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
    active_engines: tuple[str, ...] = ("engine_a", "engine_b"),
    build14_status: str = "healthy",
) -> TechnicalDashboardPayload:
    return TechnicalDashboardPayload(
        timestamp_ms=1_700_000_000_000,
        correlation_id=correlation_id,
        profile=ProfileId.LIGHT,
        runtime_mode=RuntimeMode.SHADOW,
        system=SystemProjection(
            headline_status="healthy",
            active_modules=("monitoring", "ui", "meta_learning", "backtest_artifact_import", "protocols"),
            active_engines=active_engines,
            stale_engines=(),
            build9x_status="warning" if diagnostics_count else "info",
            shadow_status="healthy",
            build14_status=build14_status,
            replay_import_status="healthy" if validation_status == "accepted" else "warning",
            governed_extensions_detail="Build-11 Shadow remains the governed full-system truth phase.",
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


def _build_shadow_input(
    baseline_payload: TechnicalDashboardPayload,
    candidate_payload: TechnicalDashboardPayload,
    *,
    component_assessments: tuple[ShadowComponentAssessment, ...] | None = None,
    shadow_days_completed: int = 30,
    shadow_report_ready: bool = True,
    inter_engine_comparison_ready: bool = True,
    build14_contribution_ready: bool = True,
    runtime_evidence: ShadowRuntimeEvidence | None = None,
) -> ShadowInput:
    return build_shadow_input_from_payloads(
        baseline_payload,
        candidate_payload,
        truth_ref="truth-1",
        validation_ref="validation-1",
        component_assessments=component_assessments or _component_assessments(),
        shadow_days_completed=shadow_days_completed,
        shadow_report_ready=shadow_report_ready,
        inter_engine_comparison_ready=inter_engine_comparison_ready,
        build14_contribution_ready=build14_contribution_ready,
        runtime_evidence=runtime_evidence
        or build_shadow_runtime_evidence(
            local_replay_evidence=LocalReplayRuntimeEvidence(
                artifact_id="artifact-1",
                lineage_version="a.v1.0.r1",
                data_source="recorded_replay",
                feature_bridge_ready=True,
                parity_diagnostics_ready=True,
                replay_metrics_ready=True,
                replay_dtr_ready=True,
                replay_useful_ready=True,
                evidence_summary="local replay evidence ready",
            ),
            runtime_event_loop_ready=True,
            runtime_config_loaded=True,
            runtime_shadow_dtr_persisted=True,
            runtime_continuous_hours=24.0,
        ),
    )


def test_build_shadow_input_from_payloads_maps_full_system_shadow_state():
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

    shadow_input = _build_shadow_input(baseline_payload, candidate_payload)

    assert shadow_input.correlation_id == "corr-shadow-candidate"
    assert shadow_input.validation_set.shadow_days_completed == 30
    assert shadow_input.validation_set.shadow_report_ready is True
    assert shadow_input.validation_set.runtime_data_source == "recorded_replay"
    assert shadow_input.validation_set.runtime_parity_diagnostics_ready is True
    assert shadow_input.validation_set.runtime_replay_metrics_ready is True
    assert shadow_input.validation_set.runtime_replay_dtr_ready is True
    assert shadow_input.validation_set.runtime_event_loop_ready is True
    assert shadow_input.validation_set.runtime_continuous_hours == 24.0
    assert shadow_input.validation_set.active_engines == (
        "engine_a",
        "engine_b",
    )
    assert len(shadow_input.validation_set.component_assessments) == 7


def test_build_shadow_input_from_payloads_rejects_complete_baseline():
    baseline_payload = _payload(
        correlation_id="corr-shadow-baseline",
        ce_net=0.0012,
        dtr_coverage=0.84,
        cra_sterilization_rate=0.10,
        break_even_scope_count=1,
        edge_degraded_count=0,
        active_alert_count=2,
        queue_backlog=20,
    ).model_copy(update={"profile": ProfileId.COMPLETE})
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

    with pytest.raises(ShadowInputError, match="baseline payload must stay on profile=LIGHT"):
        _build_shadow_input(baseline_payload, candidate_payload)


def test_build_shadow_input_from_payloads_rejects_non_shadow_baseline_mode():
    baseline_payload = _payload(
        correlation_id="corr-shadow-baseline",
        ce_net=0.0012,
        dtr_coverage=0.84,
        cra_sterilization_rate=0.10,
        break_even_scope_count=1,
        edge_degraded_count=0,
        active_alert_count=2,
        queue_backlog=20,
    ).model_copy(update={"runtime_mode": RuntimeMode.LOCAL_REPLAY})
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

    with pytest.raises(ShadowInputError, match="baseline payload must stay on runtime_mode=SHADOW"):
        _build_shadow_input(baseline_payload, candidate_payload)


def test_run_shadow_validation_accepts_candidate_with_full_system_shadow_evidence():
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

    summary = run_shadow_validation(_build_shadow_input(baseline_payload, candidate_payload))

    assert summary.decision.accepted is True
    assert summary.decision.verdict == ShadowVerdict.ACCEPTED
    assert summary.shadow_days_completed == 30
    assert summary.runtime_evidence_ready is True
    assert summary.shadow_validated_component_count == 7
    assert summary.dormant_component_count == 0
    assert summary.blocking_comparison_count == 0
    assert summary.divergent_comparison_count >= 1


def test_run_shadow_validation_accepts_dormant_components_once_verdicts_are_rendered():
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
        ce_net=0.0011,
        dtr_coverage=0.83,
        cra_sterilization_rate=0.12,
        break_even_scope_count=1,
        edge_degraded_count=0,
        active_alert_count=2,
        queue_backlog=21,
        review_export_ready=True,
    )

    summary = run_shadow_validation(
        _build_shadow_input(
            baseline_payload,
            candidate_payload,
            component_assessments=_component_assessments(
        dormant_component_ids=("engine_b", "build14_edge_diversity")
            ),
        )
    )

    assert summary.decision.verdict == ShadowVerdict.ACCEPTED
    assert summary.shadow_validated_component_count == 5
    assert summary.dormant_component_count == 2


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

    summary = run_shadow_validation(_build_shadow_input(baseline_payload, candidate_payload))

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

    summary = run_shadow_validation(_build_shadow_input(baseline_payload, candidate_payload))

    assert summary.decision.verdict == ShadowVerdict.BLOCKED
    assert "candidate import must be accepted before Shadow" in summary.decision.blocking_reasons
    assert "candidate lineage_version is required" in summary.decision.blocking_reasons


def test_run_shadow_validation_blocks_without_real_runtime_evidence():
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
        review_export_ready=True,
    )

    summary = run_shadow_validation(
        _build_shadow_input(
            baseline_payload,
            candidate_payload,
            runtime_evidence=build_shadow_runtime_evidence(
                local_replay_evidence=LocalReplayRuntimeEvidence(
                    artifact_id="artifact-1",
                    lineage_version="a.v1.0.r1",
                    data_source="unknown",
                    feature_bridge_ready=False,
                    parity_diagnostics_ready=False,
                    replay_metrics_ready=False,
                    replay_dtr_ready=False,
                    replay_useful_ready=False,
                    evidence_summary="local replay evidence missing",
                ),
                runtime_data_source="unknown",
                runtime_event_loop_ready=False,
                runtime_config_loaded=False,
                runtime_shadow_dtr_persisted=False,
                runtime_continuous_hours=0.0,
            ),
        )
    )

    assert summary.decision.verdict == ShadowVerdict.BLOCKED
    assert summary.runtime_evidence_ready is False
    assert "Build-11 Shadow requires runtime evidence from live_websocket or recorded_replay" in summary.decision.blocking_reasons
    assert "Build-11 Shadow requires feature bridge evidence (prices -> features -> engines)" in summary.decision.blocking_reasons
    assert "Build-11 Shadow requires parity diagnostics evidence" in summary.decision.blocking_reasons
    assert "Build-11 Shadow requires replay metrics evidence" in summary.decision.blocking_reasons
    assert "Build-11 Shadow requires replay DTR evidence" in summary.decision.blocking_reasons
    assert "Build-11 Shadow requires event loop evidence" in summary.decision.blocking_reasons
    assert "Build-11 Shadow requires official config loading evidence" in summary.decision.blocking_reasons
    assert "Build-11 Shadow requires persisted shadow DTR evidence" in summary.decision.blocking_reasons
    assert "Build-11 Shadow requires at least 24h of real runtime evidence before the verdict gate" in summary.decision.blocking_reasons


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

    summary = run_shadow_validation(_build_shadow_input(baseline_payload, candidate_payload))

    assert summary.decision.verdict == ShadowVerdict.REJECTED
    assert summary.blocking_comparison_count >= 2
    assert any("dtr_coverage_drop" in reason for reason in summary.decision.blocking_reasons)


def test_run_shadow_validation_blocks_if_30_day_gate_is_not_complete():
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
        review_export_ready=True,
    )

    summary = run_shadow_validation(
        _build_shadow_input(
            baseline_payload,
            candidate_payload,
            shadow_days_completed=29,
        )
    )

    assert summary.decision.verdict == ShadowVerdict.BLOCKED
    assert "Build-11 Shadow requires 30 consecutive days before the verdict gate" in summary.decision.blocking_reasons


def test_run_shadow_validation_blocks_if_report_is_missing_inter_engine_or_build14_sections():
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
        review_export_ready=True,
    )

    summary = run_shadow_validation(
        _build_shadow_input(
            baseline_payload,
            candidate_payload,
            shadow_report_ready=False,
            inter_engine_comparison_ready=False,
            build14_contribution_ready=False,
        )
    )

    assert summary.decision.verdict == ShadowVerdict.BLOCKED
    assert "Build-11 Shadow requires a complete shadow report before the verdict gate" in summary.decision.blocking_reasons
    assert "Build-11 Shadow requires an inter-engine A/B comparison in the report" in summary.decision.blocking_reasons
    assert "Build-11 Shadow requires Build-14 contribution evidence in the report" in summary.decision.blocking_reasons


def test_run_shadow_validation_blocks_missing_engine_activation():
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
        review_export_ready=True,
        active_engines=("engine_a",),
    )

    summary = run_shadow_validation(_build_shadow_input(baseline_payload, candidate_payload))

    assert summary.decision.verdict == ShadowVerdict.BLOCKED
    assert "Build-11 Shadow requires A/B active in Shadow: engine_b" in summary.decision.blocking_reasons


def test_run_shadow_validation_blocks_missing_component_verdicts():
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
        review_export_ready=True,
    )

    summary = run_shadow_validation(
        _build_shadow_input(
            baseline_payload,
            candidate_payload,
            component_assessments=_component_assessments()[:-1],
        )
    )

    assert summary.decision.verdict == ShadowVerdict.BLOCKED
    assert any(
        reason.startswith(
            "Build-11 Shadow requires component verdicts for A/B and all Build-14 enablers"
        )
        for reason in summary.decision.blocking_reasons
    )


def test_run_shadow_validation_blocks_contradictory_import_state_even_if_contracts_are_bypassed():
    truth = ShadowTruthSet(
        truth_ref="truth-1",
        dtr_coverage=0.84,
        cra_sterilization_rate=0.10,
        break_even_drift_scope_count=1,
        edge_degraded_count=0,
        ce_net=0.0012,
        active_alert_count=2,
        queue_backlog=20,
    )
    invalid_validation = ShadowValidationSet.model_construct(
        validation_ref="validation-1",
        dtr_coverage=0.81,
        cra_sterilization_rate=0.12,
        break_even_drift_scope_count=1,
        edge_degraded_count=0,
        ce_net=0.0010,
        active_alert_count=2,
        queue_backlog=21,
        accepted_import=True,
        import_validation_status="needs_revision",
        import_artifact_id="artifact-1",
        import_lineage_version="a.v1.0.r1",
        import_rejection_reasons=("artifact review incomplete",),
        build9x_diagnostics_count=0,
        open_hypotheses=0,
        replay_candidate_count=0,
        review_export_ready=False,
        active_engines=("engine_a", "engine_b"),
        build14_status="healthy",
        shadow_days_completed=30,
        shadow_required_days=30,
        shadow_report_ready=True,
        inter_engine_comparison_ready=True,
        build14_contribution_ready=True,
        component_assessments=_component_assessments(),
    )
    shadow_input = ShadowInput.model_construct(
        correlation_id="corr-shadow",
        profile=ProfileId.LIGHT,
        runtime_mode=RuntimeMode.SHADOW,
        truth_set=truth,
        validation_set=invalid_validation,
        max_allowed_dtr_coverage_drop=0.05,
        max_allowed_cra_increase=0.10,
        max_allowed_break_even_drift_scope_increase=0,
        max_allowed_edge_degraded_delta=0,
        max_allowed_ce_net_drop=0.0005,
        max_allowed_alert_count_increase=1,
        max_allowed_queue_backlog_increase=25,
        backtest_profile=None,
        creates_profile_fork=False,
        automatic_promotion_requested=False,
    )

    summary = run_shadow_validation(shadow_input)

    assert summary.decision.accepted is False
    assert summary.decision.verdict == ShadowVerdict.BLOCKED
    assert (
        "candidate import_validation_status must be an accepted status before Shadow"
        in summary.decision.blocking_reasons
    )
