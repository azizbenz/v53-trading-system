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
    collect_engine_metrics,
)
from protocols import (
    ShadowBuild14Contribution,
    ShadowComponentAssessment,
    ShadowComponentHardState,
    ShadowComponentKind,
    ShadowComponentVerdict,
    ShadowEngineReport,
    ShadowInput,
    ShadowInputError,
    ShadowReportArtifact,
    ShadowReportSection,
    ShadowRuntimeEvidence,
    ShadowTruthSet,
    ShadowValidationSet,
    ShadowVerdict,
    build_shadow_runtime_evidence,
    build_shadow_input_from_payloads,
    derive_shadow_engine_judgment_summary,
    run_shadow_validation,
)


def _component_assessments(
    *,
    dormant_component_ids: tuple[str, ...] = (),
) -> tuple[ShadowComponentAssessment, ...]:
    dormant = set(dormant_component_ids)
    engine_ids = ("engine_a", "engine_b", "engine_c", "engine_d")
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
    exported_from: str = "local",
    source_profile: str = "complete",
    dataset_ref: str = "dataset-1",
    clock_ref: str = "clock-1",
    review_state: str | None = None,
    activation_stage: str = "shadow_ready",
    health_state: str = "active",
    compatibility_status: str = "not_evaluated",
    compatibility_reasons: tuple[str, ...] = (),
    feature_lineage_required: bool = True,
    feature_lineage_present: bool = True,
    feature_lineage_status: str = "ok",
    feature_lineage_reasons: tuple[str, ...] = (),
    transform_whitelist_required: bool = True,
    transform_whitelist_present: bool = True,
    transform_whitelist_status: str = "ok",
    transform_whitelist_reasons: tuple[str, ...] = (),
    signature_check_status: str = "verified",
    signature_check_reasons: tuple[str, ...] = (),
    conflict_resolution_mode: str = "no_trade_then_strictest",
    conflict_hard_veto_action: str = "no_trade",
    conflict_score_aggregation_mode: str = "bounded_sum_with_global_cap",
    conflict_size_reduce_mode: str = "min_factor_wins",
    conflict_rank_adjust_mode: str = "bounded_sum",
    conflict_additive_soft_boosts_allowed: bool = True,
    conflict_additive_soft_reduces_allowed: bool = True,
    registry_atomicity_mode: str = "atomic_snapshot_swap",
    registry_concurrency_model: str = "single_writer_multi_reader",
    registry_publish_requires_atomic_replace: bool = True,
    registry_publish_requires_fsync: bool = True,
    registry_rollback_to_last_known_good: bool = True,
    artifact_id: str = "artifact-1",
    lineage_version: str = "a.v1.0.r1",
    rejection_reasons: tuple[str, ...] = (),
    active_engines: tuple[str, ...] = ("engine_a", "engine_b", "engine_c", "engine_d"),
    build14_status: str = "healthy",
    engines: tuple = (),
) -> TechnicalDashboardPayload:
    return TechnicalDashboardPayload(
        timestamp_ms=1_700_000_000_000,
        correlation_id=correlation_id,
        profile=ProfileId.COMPLETE,
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
        engines=engines,
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
            exported_from=exported_from,
            source_profile=source_profile,
            lineage_version=lineage_version,
            dataset_ref=dataset_ref,
            clock_ref=clock_ref,
            activation_stage=activation_stage,
            health_state=health_state,
            lifecycle_state="exported" if artifact_id != "none" else "Awaiting LOCAL_REPLAY artifact",
            validation_status=validation_status,
            review_state=review_state or ("pending" if validation_status == "accepted" else "needs_revision"),
            compatibility_status=compatibility_status,
            compatibility_reasons=compatibility_reasons,
            feature_lineage_required=feature_lineage_required,
            feature_lineage_present=feature_lineage_present,
            feature_lineage_status=feature_lineage_status,
            feature_lineage_reasons=feature_lineage_reasons,
            transform_whitelist_required=transform_whitelist_required,
            transform_whitelist_present=transform_whitelist_present,
            transform_whitelist_status=transform_whitelist_status,
            transform_whitelist_reasons=transform_whitelist_reasons,
            signature_check_status=signature_check_status,
            signature_check_reasons=signature_check_reasons,
            conflict_resolution_mode=conflict_resolution_mode,
            conflict_hard_veto_action=conflict_hard_veto_action,
            conflict_score_aggregation_mode=conflict_score_aggregation_mode,
            conflict_size_reduce_mode=conflict_size_reduce_mode,
            conflict_rank_adjust_mode=conflict_rank_adjust_mode,
            conflict_additive_soft_boosts_allowed=conflict_additive_soft_boosts_allowed,
            conflict_additive_soft_reduces_allowed=conflict_additive_soft_reduces_allowed,
            registry_atomicity_mode=registry_atomicity_mode,
            registry_concurrency_model=registry_concurrency_model,
            registry_publish_requires_atomic_replace=registry_publish_requires_atomic_replace,
            registry_publish_requires_fsync=registry_publish_requires_fsync,
            registry_rollback_to_last_known_good=registry_rollback_to_last_known_good,
            payload_ref_count=5,
            payload_bundle_present=True,
            review_export_ref="exports/review.md",
            feature_bridge_ref="exports/feature_bridge.json",
            parity_diagnostics_ref="exports/parity.json",
            replay_metrics_ref="exports/replay_metrics.json",
            replay_dtr_ref="exports/replay_dtr.json",
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


def _shadow_report(
    *,
    consecutive_days: int = 30,
    is_complete: bool = True,
    engine_overrides: dict[str, dict[str, float | int]] | None = None,
) -> ShadowReportArtifact:
    defaults = {
        "engine_a": dict(
            gross_frequency=0.24,
            useful_frequency=0.18,
            estimated_cost_bps=4.0,
            edge_net=8.8,
            economic_pass_rate=0.86,
            conflict_rate=0.18,
            marginal_edge=0.0040,
            observations=18,
        ),
        "engine_b": dict(
            gross_frequency=0.17,
            useful_frequency=0.11,
            estimated_cost_bps=3.2,
            edge_net=3.6,
            economic_pass_rate=0.69,
            conflict_rate=0.22,
            marginal_edge=0.0017,
            observations=12,
        ),
        "engine_c": dict(
            gross_frequency=0.08,
            useful_frequency=0.02,
            estimated_cost_bps=2.1,
            edge_net=0.8,
            economic_pass_rate=0.61,
            conflict_rate=0.14,
            marginal_edge=0.0006,
            observations=5,
        ),
        "engine_d": dict(
            gross_frequency=0.07,
            useful_frequency=0.01,
            estimated_cost_bps=2.4,
            edge_net=0.5,
            economic_pass_rate=0.58,
            conflict_rate=0.16,
            marginal_edge=0.0005,
            observations=4,
        ),
    }
    if engine_overrides:
        for engine_id, values in engine_overrides.items():
            defaults[engine_id].update(values)
    inter_engine_comparison = tuple(
        ShadowEngineReport(engine_id=engine_id, **values)
        for engine_id, values in defaults.items()
    )
    return ShadowReportArtifact(
        report_id="shadow-report-1",
        profile="complete",
        report_generated_at=1_700_000_000.0,
        consecutive_days=consecutive_days,
        required_days=30,
        remaining_days=max(0, 30 - consecutive_days),
        is_complete=is_complete,
        started_at=1_697_408_000.0,
        last_shadow_timestamp=1_700_000_000.0,
        total_resets=0,
        daily_records_count=max(1, consecutive_days),
        dtr_coverage=1.0,
        dtr_complete=True,
        ce_net=0.0012,
        estimated_cost_bps=3.6,
        edge_net=6.2,
        drawdown_pct=1.8,
        stale_rate=0.0,
        economic_pass_rate=0.78,
        pair_health_ratio=1.0,
        backlog_avg=18.0,
        capital_simulated_usdt=1200.0,
        gross_exposure_shadow_pct=35.0,
        loss_budget_shadow_pct=8.0,
        capital_free_usdt=8800.0,
        beta_btc_shadow=0.22,
        dominant_cluster="trend_flow",
        pnl_shadow=92.0,
        dtr_loss_rate=0.0,
        log_loss_rate=0.0,
        event_latency_ms=42.0,
        hard_block_rate=0.0,
        phantom_trade_count=0,
        decisions_reproducible=True,
        infra_stable=True,
        costs_plausible=True,
        break_even_visible=True,
        critical_alerts_visible=True,
        operator_actions_logged=True,
        ui_locked=True,
        shadow_report_ready=is_complete,
        data_infra_report_ready=True,
        decisions_dtr_report_ready=True,
        costs_break_even_report_ready=True,
        inter_engine_comparison_ready=True,
        build14_contribution_ready=True,
        portfolio_report_ready=True,
        ui_alerting_report_ready=True,
        go_no_go_report_ready=True,
        inter_engine_comparison=inter_engine_comparison,
        build14_contribution=(
            ShadowBuild14Contribution(
                component_id="build14_microstructure",
                contribution_score=0.58,
                interaction_score=0.17,
                observations=14,
            ),
            ShadowBuild14Contribution(
                component_id="build14_regime",
                contribution_score=0.42,
                interaction_score=0.12,
                observations=14,
            ),
            ShadowBuild14Contribution(
                component_id="build14_covariance",
                contribution_score=0.33,
                interaction_score=0.09,
                observations=14,
            ),
            ShadowBuild14Contribution(
                component_id="build14_risk_contribution",
                contribution_score=0.31,
                interaction_score=0.10,
                observations=14,
            ),
            ShadowBuild14Contribution(
                component_id="build14_edge_diversity",
                contribution_score=0.29,
                interaction_score=0.08,
                observations=14,
            ),
        ),
        rendered_sections=(
            ShadowReportSection(section_id="data_infra_report", title="infra", ready=True, summary="ok"),
            ShadowReportSection(section_id="decisions_dtr_report", title="dtr", ready=True, summary="ok"),
            ShadowReportSection(section_id="costs_break_even_report", title="costs", ready=True, summary="ok"),
            ShadowReportSection(section_id="engine_comparison_report", title="engines", ready=True, summary="ok"),
            ShadowReportSection(section_id="portfolio_report", title="portfolio", ready=True, summary="ok"),
            ShadowReportSection(section_id="ui_alerting_report", title="alerts", ready=True, summary="ok"),
            ShadowReportSection(section_id="go_no_go_report", title="go-no-go", ready=True, summary="ok"),
        ),
        missing_sections=(),
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
    assert shadow_input.validation_set.import_activation_stage == "shadow_ready"
    assert shadow_input.validation_set.import_health_state == "active"
    assert shadow_input.validation_set.import_exported_from == "local"
    assert shadow_input.validation_set.import_source_profile == "complete"
    assert shadow_input.validation_set.import_dataset_ref == "dataset-1"
    assert shadow_input.validation_set.import_clock_ref == "clock-1"
    assert shadow_input.validation_set.import_review_state == "pending"
    assert shadow_input.validation_set.import_compatibility_status == "not_evaluated"
    assert shadow_input.validation_set.import_feature_lineage_required is True
    assert shadow_input.validation_set.import_feature_lineage_present is True
    assert shadow_input.validation_set.import_feature_lineage_status == "ok"
    assert shadow_input.validation_set.import_transform_whitelist_required is True
    assert shadow_input.validation_set.import_transform_whitelist_present is True
    assert shadow_input.validation_set.import_transform_whitelist_status == "ok"
    assert shadow_input.validation_set.import_signature_check_status == "verified"
    assert shadow_input.validation_set.import_conflict_resolution_mode == "no_trade_then_strictest"
    assert shadow_input.validation_set.import_registry_atomicity_mode == "atomic_snapshot_swap"
    assert shadow_input.validation_set.import_registry_publish_requires_atomic_replace is True
    assert shadow_input.validation_set.active_engines == (
        "engine_a",
        "engine_b",
        "engine_c",
        "engine_d",
    )
    assert len(shadow_input.validation_set.component_assessments) == 9


def test_build_shadow_input_from_payloads_rejects_light_baseline():
    baseline_payload = _payload(
        correlation_id="corr-shadow-baseline",
        ce_net=0.0012,
        dtr_coverage=0.84,
        cra_sterilization_rate=0.10,
        break_even_scope_count=1,
        edge_degraded_count=0,
        active_alert_count=2,
        queue_backlog=20,
    ).model_copy(update={"profile": ProfileId.LIGHT})
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

    with pytest.raises(ShadowInputError, match="baseline payload must stay on profile=COMPLETE"):
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
    assert summary.shadow_validated_component_count == 9
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
    assert summary.shadow_validated_component_count == 7
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
    assert "Build-11 Shadow requires an inter-engine A/B/C/D comparison in the report" in summary.decision.blocking_reasons
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
    assert (
        "Build-11 Shadow requires A/B/C/D active in Shadow: engine_b, engine_c, engine_d"
        in summary.decision.blocking_reasons
    )


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
            "Build-11 Shadow requires component verdicts for A/B/C/D and all Build-14 enablers"
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
        profile=ProfileId.COMPLETE,
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


def test_run_shadow_validation_blocks_rejected_import_policy_even_if_validation_status_is_accepted():
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

    shadow_input = _build_shadow_input(baseline_payload, candidate_payload)
    shadow_input = shadow_input.model_copy(
        update={
            "validation_set": shadow_input.validation_set.model_copy(
                update={
                    "accepted_import": True,
                    "import_validation_status": "accepted",
                    "import_rejection_reasons": (),
                    "import_compatibility_status": "rejected",
                    "import_compatibility_reasons": ("ARTIFACT_SCHEMA_MINOR_UNSUPPORTED",),
                    "import_signature_check_status": "key_id_unknown",
                    "import_signature_check_reasons": ("KEY_ID_UNKNOWN",),
                }
            )
        }
    )

    summary = run_shadow_validation(shadow_input)

    assert summary.decision.accepted is False
    assert summary.decision.verdict == ShadowVerdict.BLOCKED
    assert (
        "candidate import compatibility policy rejected the artifact before Shadow"
        in summary.decision.blocking_reasons
    )
    assert "import compatibility gate: ARTIFACT_SCHEMA_MINOR_UNSUPPORTED" in summary.decision.blocking_reasons
    assert (
        "candidate import signature policy rejected the artifact before Shadow"
        in summary.decision.blocking_reasons
    )
    assert "import signature gate: KEY_ID_UNKNOWN" in summary.decision.blocking_reasons


def test_run_shadow_validation_accepts_trust_eligible_signature_status():
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
        signature_check_status="trust_eligible",
    )

    summary = run_shadow_validation(_build_shadow_input(baseline_payload, candidate_payload))

    assert summary.decision.accepted is True


def test_run_shadow_validation_blocks_signature_invalid_status():
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

    shadow_input = _build_shadow_input(baseline_payload, candidate_payload)
    shadow_input = shadow_input.model_copy(
        update={
            "validation_set": shadow_input.validation_set.model_copy(
                update={
                    "accepted_import": True,
                    "import_validation_status": "accepted",
                    "import_rejection_reasons": (),
                    "import_signature_check_status": "signature_invalid",
                    "import_signature_check_reasons": ("SIGNATURE_INVALID",),
                }
            )
        }
    )

    summary = run_shadow_validation(shadow_input)

    assert summary.decision.accepted is False
    assert summary.decision.verdict == ShadowVerdict.BLOCKED
    assert (
        "candidate import signature policy rejected the artifact before Shadow"
        in summary.decision.blocking_reasons
    )
    assert "import signature gate: SIGNATURE_INVALID" in summary.decision.blocking_reasons


def test_run_shadow_validation_blocks_non_shadow_ready_or_non_active_import_state():
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

    shadow_input = _build_shadow_input(baseline_payload, candidate_payload)
    shadow_input = shadow_input.model_copy(
        update={
            "validation_set": shadow_input.validation_set.model_copy(
                update={
                    "accepted_import": True,
                    "import_validation_status": "accepted",
                    "import_rejection_reasons": (),
                    "import_activation_stage": "replay_only",
                    "import_health_state": "review_required",
                }
            )
        }
    )

    summary = run_shadow_validation(shadow_input)

    assert summary.decision.accepted is False
    assert summary.decision.verdict == ShadowVerdict.BLOCKED
    assert (
        "candidate import activation_stage must be shadow_ready before Shadow"
        in summary.decision.blocking_reasons
    )
    assert (
        "candidate import health_state must be active before Shadow"
        in summary.decision.blocking_reasons
    )


def test_run_shadow_validation_blocks_import_review_state_needs_revision():
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

    shadow_input = _build_shadow_input(baseline_payload, candidate_payload)
    shadow_input = shadow_input.model_copy(
        update={
            "validation_set": shadow_input.validation_set.model_copy(
                update={
                    "accepted_import": True,
                    "import_validation_status": "accepted",
                    "import_review_state": "needs_revision",
                    "import_rejection_reasons": (),
                }
            )
        }
    )

    summary = run_shadow_validation(shadow_input)

    assert summary.decision.accepted is False
    assert summary.decision.verdict == ShadowVerdict.BLOCKED
    assert (
        "candidate import review_state must stay pending or approved before Shadow"
        in summary.decision.blocking_reasons
    )


def test_run_shadow_validation_blocks_non_complete_import_source_profile():
    baseline_payload = _payload(
        correlation_id="corr-shadow-baseline",
        ce_net=0.0012,
        dtr_coverage=0.84,
        cra_sterilization_rate=0.10,
        break_even_scope_count=0,
        edge_degraded_count=0,
        active_alert_count=1,
        queue_backlog=8,
    )
    candidate_payload = _payload(
        correlation_id="corr-shadow-candidate",
        ce_net=0.0010,
        dtr_coverage=0.81,
        cra_sterilization_rate=0.11,
        break_even_scope_count=0,
        edge_degraded_count=0,
        active_alert_count=2,
        queue_backlog=20,
    )

    shadow_input = _build_shadow_input(baseline_payload, candidate_payload)
    shadow_input = shadow_input.model_copy(
        update={
            "validation_set": shadow_input.validation_set.model_copy(
                update={
                    "accepted_import": True,
                    "import_validation_status": "accepted",
                    "import_source_profile": "light",
                    "import_rejection_reasons": (),
                }
            )
        }
    )

    summary = run_shadow_validation(shadow_input, run_id="shadow-run-1")

    assert summary.decision.verdict == ShadowVerdict.BLOCKED
    assert (
        "candidate import source_profile must be complete before Shadow"
        in summary.decision.blocking_reasons
    )


def test_run_shadow_validation_blocks_non_local_import_origin():
    baseline_payload = _payload(
        correlation_id="corr-shadow-baseline",
        ce_net=0.0012,
        dtr_coverage=0.84,
        cra_sterilization_rate=0.10,
        break_even_scope_count=0,
        edge_degraded_count=0,
        active_alert_count=1,
        queue_backlog=8,
    )
    candidate_payload = _payload(
        correlation_id="corr-shadow-candidate",
        ce_net=0.0010,
        dtr_coverage=0.81,
        cra_sterilization_rate=0.11,
        break_even_scope_count=0,
        edge_degraded_count=0,
        active_alert_count=2,
        queue_backlog=20,
    )

    shadow_input = _build_shadow_input(baseline_payload, candidate_payload)
    shadow_input = shadow_input.model_copy(
        update={
            "validation_set": shadow_input.validation_set.model_copy(
                update={
                    "accepted_import": True,
                    "import_validation_status": "accepted",
                    "import_exported_from": "vps",
                    "import_rejection_reasons": (),
                }
            )
        }
    )

    summary = run_shadow_validation(shadow_input, run_id="shadow-run-1")

    assert summary.decision.verdict == ShadowVerdict.BLOCKED
    assert (
        "candidate import exported_from must be local before Shadow"
        in summary.decision.blocking_reasons
    )


def test_run_shadow_validation_blocks_missing_payload_bundle_and_refs():
    baseline_payload = _payload(
        correlation_id="corr-shadow-baseline",
        ce_net=0.0012,
        dtr_coverage=0.84,
        cra_sterilization_rate=0.10,
        break_even_scope_count=0,
        edge_degraded_count=0,
        active_alert_count=1,
        queue_backlog=8,
    )
    candidate_payload = _payload(
        correlation_id="corr-shadow-candidate",
        ce_net=0.0010,
        dtr_coverage=0.81,
        cra_sterilization_rate=0.11,
        break_even_scope_count=0,
        edge_degraded_count=0,
        active_alert_count=2,
        queue_backlog=20,
    )

    shadow_input = _build_shadow_input(baseline_payload, candidate_payload)
    shadow_input = shadow_input.model_copy(
        update={
            "validation_set": shadow_input.validation_set.model_copy(
                update={
                    "accepted_import": True,
                    "import_validation_status": "accepted",
                    "import_payload_ref_count": 0,
                    "import_payload_bundle_present": False,
                    "import_review_export_ref": "",
                    "import_feature_bridge_ref": "",
                    "import_parity_diagnostics_ref": "",
                    "import_replay_metrics_ref": "",
                    "import_replay_dtr_ref": "",
                    "import_rejection_reasons": (),
                }
            )
        }
    )

    summary = run_shadow_validation(shadow_input, run_id="shadow-run-1")

    assert summary.decision.verdict == ShadowVerdict.BLOCKED
    assert (
        "candidate import must keep payload_ref_count>=5 before Shadow"
        in summary.decision.blocking_reasons
    )
    assert (
        "candidate import must keep payload_bundle_present=True before Shadow"
        in summary.decision.blocking_reasons
    )
    assert (
        "candidate import must keep review_export_ref before Shadow"
        in summary.decision.blocking_reasons
    )


def test_run_shadow_validation_blocks_non_canonical_conflict_and_registry_policy():
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

    shadow_input = _build_shadow_input(baseline_payload, candidate_payload)
    shadow_input = shadow_input.model_copy(
        update={
            "validation_set": shadow_input.validation_set.model_copy(
                update={
                    "accepted_import": True,
                    "import_validation_status": "accepted",
                    "import_rejection_reasons": (),
                    "import_conflict_resolution_mode": "first_artifact_wins",
                    "import_conflict_hard_veto_action": "soft_reduce",
                    "import_conflict_score_aggregation_mode": "max_abs_wins",
                    "import_conflict_size_reduce_mode": "max_factor_wins",
                    "import_conflict_rank_adjust_mode": "max_abs_wins",
                    "import_conflict_additive_soft_boosts_allowed": False,
                    "import_conflict_additive_soft_reduces_allowed": False,
                    "import_registry_atomicity_mode": "in_place_mutation",
                    "import_registry_concurrency_model": "multi_writer",
                    "import_registry_publish_requires_atomic_replace": False,
                    "import_registry_publish_requires_fsync": False,
                    "import_registry_rollback_to_last_known_good": False,
                }
            )
        }
    )

    summary = run_shadow_validation(shadow_input)

    assert summary.decision.accepted is False
    assert summary.decision.verdict == ShadowVerdict.BLOCKED
    assert (
        "candidate import conflict policy must keep resolution_mode=no_trade_then_strictest before Shadow"
        in summary.decision.blocking_reasons
    )
    assert (
        "candidate import registry policy must keep atomicity_mode=atomic_snapshot_swap before Shadow"
        in summary.decision.blocking_reasons
    )
    assert (
        "candidate import registry policy must require atomic replace before Shadow"
        in summary.decision.blocking_reasons
    )


def test_run_shadow_validation_blocks_invalid_lineage_and_transform_whitelist_policy():
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

    shadow_input = _build_shadow_input(baseline_payload, candidate_payload)
    shadow_input = shadow_input.model_copy(
        update={
            "validation_set": shadow_input.validation_set.model_copy(
                update={
                    "accepted_import": True,
                    "import_validation_status": "accepted",
                    "import_rejection_reasons": (),
                    "import_feature_lineage_required": False,
                    "import_feature_lineage_present": False,
                    "import_feature_lineage_status": "invalid",
                    "import_feature_lineage_reasons": ("FEATURE_LINEAGE_LOCK_REQUIRED",),
                    "import_transform_whitelist_required": False,
                    "import_transform_whitelist_present": False,
                    "import_transform_whitelist_status": "invalid",
                    "import_transform_whitelist_reasons": ("TRANSFORM_WHITELIST_LOCK_REQUIRED",),
                }
            )
        }
    )

    summary = run_shadow_validation(shadow_input)

    assert summary.decision.verdict == ShadowVerdict.BLOCKED
    assert (
        "candidate import must require feature_lineage_lock before Shadow"
        in summary.decision.blocking_reasons
    )
    assert (
        "candidate import feature_lineage_lock must be valid before Shadow"
        in summary.decision.blocking_reasons
    )
    assert (
        "import feature lineage gate: FEATURE_LINEAGE_LOCK_REQUIRED"
        in summary.decision.blocking_reasons
    )
    assert (
        "candidate import must require transform_whitelist_lock before Shadow"
        in summary.decision.blocking_reasons
    )
    assert (
        "candidate import transform_whitelist_lock must be valid before Shadow"
        in summary.decision.blocking_reasons
    )
    assert (
        "import transform whitelist gate: TRANSFORM_WHITELIST_LOCK_REQUIRED"
        in summary.decision.blocking_reasons
    )


def test_derive_shadow_engine_judgment_summary_marks_promotable_on_complete_positive_shadow():
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

    summary = run_shadow_validation(_build_shadow_input(baseline_payload, candidate_payload))
    judgment = derive_shadow_engine_judgment_summary(
        summary,
        _shadow_report(),
        ce_by_engine={"engine_a": 0.0007, "engine_b": 0.0002, "engine_c": 0.0001, "engine_d": 0.0001},
    )

    assert judgment.source_shadow_days_completed == 30
    assert judgment.portfolio_judgment.judgment_verdict == "promotable"
    assert all(entry.judgment_verdict == "promotable" for entry in judgment.judgments)


def test_derive_shadow_engine_judgment_summary_marks_shadow_only_when_shadow_gate_incomplete():
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
            shadow_days_completed=1,
            shadow_report_ready=False,
        )
    )
    judgment = derive_shadow_engine_judgment_summary(
        summary,
        _shadow_report(consecutive_days=1, is_complete=False),
        ce_by_engine={"engine_a": 0.0007},
    )

    assert judgment.portfolio_judgment.judgment_verdict == "shadow-only"
    assert all(entry.judgment_verdict == "shadow-only" for entry in judgment.judgments)


def test_derive_shadow_engine_judgment_summary_marks_rewrite_required_on_negative_economics():
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

    summary = run_shadow_validation(_build_shadow_input(baseline_payload, candidate_payload))
    judgment = derive_shadow_engine_judgment_summary(
        summary,
        _shadow_report(
            engine_overrides={
                "engine_b": {
                    "economic_pass_rate": 0.40,
                    "conflict_rate": 0.52,
                    "marginal_edge": -0.0001,
                }
            }
        ),
        ce_by_engine={"engine_a": 0.0007, "engine_b": 0.0},
    )

    engine_b = next(entry for entry in judgment.judgments if entry.engine_id == "engine_b")
    assert engine_b.judgment_verdict == "rewrite-required"
    assert "economic pass-rate" in engine_b.rationale


def test_derive_shadow_engine_judgment_summary_preserves_dormant_verdict():
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
            component_assessments=_component_assessments(dormant_component_ids=("engine_c",)),
        )
    )
    judgment = derive_shadow_engine_judgment_summary(summary, _shadow_report())

    engine_c = next(entry for entry in judgment.judgments if entry.engine_id == "engine_c")
    assert engine_c.judgment_verdict == "dormant"
    assert engine_c.component_verdict == "dormant"


def test_derive_shadow_engine_judgment_summary_uses_payload_portfolio_and_selection_signals():
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
        engines=(
            collect_engine_metrics(
                engine_id="engine_a",
                emitted_signals=2,
                net_edge_bps=12.0,
                expected_cost_bps=4.0,
                ce_expected=0.0007,
                scoring_final_size_multiplier=1.0,
                selection_outcome_code="selected",
                portfolio_verdict_code="compatible",
                risk_decision_severity="nominal",
            ),
            collect_engine_metrics(
                engine_id="engine_b",
                emitted_signals=1,
                net_edge_bps=4.0,
                expected_cost_bps=3.0,
                ce_expected=0.0002,
                scoring_final_size_multiplier=1.0,
                selection_outcome_code="rejected_portfolio",
                portfolio_verdict_code="rejected_cluster",
                risk_decision_severity="warning",
            ),
            collect_engine_metrics(
                engine_id="engine_c",
                emitted_signals=1,
                net_edge_bps=3.0,
                expected_cost_bps=2.5,
                ce_expected=0.0001,
                scoring_final_size_multiplier=0.05,
                selection_outcome_code="rejected_ranking",
                portfolio_verdict_code="compatible",
                risk_decision_severity="critical",
            ),
            collect_engine_metrics(
                engine_id="engine_d",
                emitted_signals=1,
                net_edge_bps=2.0,
                expected_cost_bps=2.0,
                ce_expected=0.0001,
                scoring_final_size_multiplier=1.0,
                selection_outcome_code="selected",
                portfolio_verdict_code="compatible",
                phantom_trade=True,
                risk_decision_severity="nominal",
            ),
        ),
    )

    summary = run_shadow_validation(_build_shadow_input(baseline_payload, candidate_payload))
    judgment = derive_shadow_engine_judgment_summary(
        summary,
        _shadow_report(),
        shadow_payload=candidate_payload,
    )

    engine_a = next(entry for entry in judgment.judgments if entry.engine_id == "engine_a")
    engine_b = next(entry for entry in judgment.judgments if entry.engine_id == "engine_b")
    engine_c = next(entry for entry in judgment.judgments if entry.engine_id == "engine_c")
    engine_d = next(entry for entry in judgment.judgments if entry.engine_id == "engine_d")

    assert engine_a.judgment_verdict == "promotable"
    assert engine_b.judgment_verdict == "rewrite-required"
    assert engine_c.judgment_verdict == "shadow-only"
    assert engine_d.judgment_verdict == "rewrite-required"
    assert judgment.portfolio_judgment.judgment_verdict == "rewrite-required"
    assert judgment.portfolio_judgment.portfolio_rejected_engine_count == 1
    assert judgment.portfolio_judgment.cluster_rejected_engine_count == 1
    assert judgment.portfolio_judgment.ranking_rejected_engine_count == 1
    assert judgment.portfolio_judgment.cluster_pressure == "elevated"


def test_derive_shadow_engine_judgment_summary_uses_physics_pressure_for_engine_verdicts():
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
        engines=(
            collect_engine_metrics(
                engine_id="engine_a",
                emitted_signals=2,
                net_edge_bps=12.0,
                expected_cost_bps=4.0,
                ce_expected=0.0007,
                scoring_final_size_multiplier=1.0,
                selection_outcome_code="selected",
                portfolio_verdict_code="compatible",
                risk_decision_severity="nominal",
            ),
            collect_engine_metrics(
                engine_id="engine_b",
                emitted_signals=1,
                net_edge_bps=4.0,
                expected_cost_bps=3.0,
                ce_expected=0.0002,
                scoring_final_size_multiplier=1.0,
                selection_outcome_code="selected",
                portfolio_verdict_code="compatible",
                risk_decision_severity="nominal",
                physics_pressure_state="elevated",
                fragility_score=0.56,
                toxicity_score=0.58,
                execution_survivability_score=0.44,
                micro_friction_score=0.57,
            ),
            collect_engine_metrics(
                engine_id="engine_c",
                emitted_signals=1,
                net_edge_bps=3.0,
                expected_cost_bps=2.5,
                ce_expected=0.0001,
                scoring_final_size_multiplier=1.0,
                selection_outcome_code="selected",
                portfolio_verdict_code="compatible",
                risk_decision_severity="warning",
                physics_pressure_state="critical",
                fragility_score=0.81,
                toxicity_score=0.79,
                execution_survivability_score=0.18,
                micro_friction_score=0.82,
            ),
            collect_engine_metrics(
                engine_id="engine_d",
                emitted_signals=1,
                net_edge_bps=2.0,
                expected_cost_bps=2.0,
                ce_expected=0.0001,
                scoring_final_size_multiplier=1.0,
                selection_outcome_code="selected",
                portfolio_verdict_code="compatible",
                risk_decision_severity="nominal",
            ),
        ),
    )

    summary = run_shadow_validation(_build_shadow_input(baseline_payload, candidate_payload))
    judgment = derive_shadow_engine_judgment_summary(
        summary,
        _shadow_report(),
        shadow_payload=candidate_payload,
    )

    engine_a = next(entry for entry in judgment.judgments if entry.engine_id == "engine_a")
    engine_b = next(entry for entry in judgment.judgments if entry.engine_id == "engine_b")
    engine_c = next(entry for entry in judgment.judgments if entry.engine_id == "engine_c")
    engine_d = next(entry for entry in judgment.judgments if entry.engine_id == "engine_d")

    assert engine_a.judgment_verdict == "promotable"
    assert engine_b.judgment_verdict == "shadow-only"
    assert engine_b.physics_pressure_state == "elevated"
    assert engine_b.fragility_score == pytest.approx(0.56)
    assert engine_b.execution_survivability_score == pytest.approx(0.44)
    assert engine_c.judgment_verdict == "rewrite-required"
    assert engine_c.physics_pressure_state == "critical"
    assert engine_c.toxicity_score == pytest.approx(0.79)
    assert engine_c.micro_friction_score == pytest.approx(0.82)
    assert engine_d.judgment_verdict == "promotable"
    assert judgment.portfolio_judgment.judgment_verdict == "shadow-only"
    assert judgment.portfolio_judgment.physics_pressure == "elevated"
    assert judgment.portfolio_judgment.elevated_physics_engine_count == 1
    assert judgment.portfolio_judgment.critical_physics_engine_count == 1
