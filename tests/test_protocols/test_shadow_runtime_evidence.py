"""Stateful runtime evidence tests for the governed Build-11 Shadow path."""

from __future__ import annotations

import shutil
from pathlib import Path

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
    ShadowRuntimeEvidenceRecorder,
    ShadowRuntimeEvidenceRecorderConfig,
    build_shadow_input_from_payloads,
    run_shadow_validation,
)


def _scratch_dir(name: str) -> Path:
    from tests.support_paths import make_repo_scratch_dir

    return make_repo_scratch_dir("shadow_runtime_evidence_tests", name)


def _component_assessments() -> tuple[ShadowComponentAssessment, ...]:
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
                verdict=ShadowComponentVerdict.SHADOW_VALIDATED,
                evidence_summary=f"{component_id} shadow evidence rendered",
            )
        )
    for component_id in build14_ids:
        assessments.append(
            ShadowComponentAssessment(
                component_id=component_id,
                component_kind=ShadowComponentKind.BUILD14_ENABLER,
                hard_state=ShadowComponentHardState.SHADOW_ENABLED,
                verdict=ShadowComponentVerdict.SHADOW_VALIDATED,
                evidence_summary=f"{component_id} shadow evidence rendered",
            )
        )
    return tuple(assessments)


def _payload(correlation_id: str, *, ce_net: float = 0.0010) -> TechnicalDashboardPayload:
    return TechnicalDashboardPayload(
        timestamp_ms=1_700_000_000_000,
        correlation_id=correlation_id,
        profile=ProfileId.COMPLETE,
        runtime_mode=RuntimeMode.SHADOW,
        system=SystemProjection(
            headline_status="healthy",
            active_modules=("monitoring", "ui", "meta_learning", "backtest_artifact_import", "protocols"),
            active_engines=("engine_a", "engine_b", "engine_c", "engine_d"),
            stale_engines=(),
            build9x_status="info",
            shadow_status="healthy",
            build14_status="healthy",
            replay_import_status="healthy",
            governed_extensions_detail="Build-11 Shadow remains governed.",
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
            dtr_coverage=0.84,
            dtr_status="healthy",
            cra_sterilization_rate=0.10,
            cra_alert_count=0,
            cra_status="healthy",
            break_even_state="stable",
            break_even_status="healthy",
            break_even_drift_scopes=(),
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
            exported_from="local",
            source_profile="complete",
            lineage_version="a.v1.0.r1",
            dataset_ref="dataset-1",
            clock_ref="clock-1",
            activation_stage="shadow_ready",
            health_state="active",
            lifecycle_state="exported",
            validation_status="accepted",
            review_state="pending",
            compatibility_status="supported",
            feature_lineage_required=True,
            feature_lineage_present=True,
            feature_lineage_status="ok",
            transform_whitelist_required=True,
            transform_whitelist_present=True,
            transform_whitelist_status="ok",
            signature_check_status="trust_eligible",
            conflict_resolution_mode="no_trade_then_strictest",
            conflict_hard_veto_action="no_trade",
            conflict_score_aggregation_mode="bounded_sum_with_global_cap",
            conflict_size_reduce_mode="min_factor_wins",
            conflict_rank_adjust_mode="bounded_sum",
            conflict_additive_soft_boosts_allowed=True,
            conflict_additive_soft_reduces_allowed=True,
            registry_atomicity_mode="atomic_snapshot_swap",
            registry_concurrency_model="single_writer_multi_reader",
            registry_publish_requires_atomic_replace=True,
            registry_publish_requires_fsync=True,
            registry_rollback_to_last_known_good=True,
            payload_ref_count=5,
            payload_bundle_present=True,
            review_export_ref="exports/review.md",
            feature_bridge_ref="exports/feature_bridge.json",
            parity_diagnostics_ref="exports/parity.json",
            replay_metrics_ref="exports/replay_metrics.json",
            replay_dtr_ref="exports/replay_dtr.json",
            rejection_reasons=(),
        ),
        alerts=AlertProjection(
            headline_status="healthy",
            active_alert_count=1,
            alert_ids=("alert-1",),
            queue_backlog=10,
            stale_pair_count=0,
            stale_pairs=(),
            backlog_stale_status="healthy",
            dtr_loss_count=0,
            log_loss_count=0,
            break_even_drift_scope_count=0,
            edge_degraded_count=0,
            loss_drift_status="healthy",
        ),
    )


def test_shadow_runtime_evidence_recorder_produces_acceptance_ready_evidence():
    recorder = ShadowRuntimeEvidenceRecorder(
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
        )
    )
    recorder.mark_runtime_source("recorded_replay")
    recorder.mark_config_loaded("config/shadow.runtime.yaml")
    recorder.record_event_loop_tick(1_700_000_000_000)
    recorder.record_event_loop_tick(1_700_086_400_000)
    recorder.mark_shadow_dtr_persisted("shadow/dtr/day01.jsonl")

    evidence = recorder.build_evidence()
    baseline_payload = _payload("corr-shadow-baseline", ce_net=0.0012)
    candidate_payload = _payload("corr-shadow-candidate", ce_net=0.0010)
    shadow_input = build_shadow_input_from_payloads(
        baseline_payload,
        candidate_payload,
        truth_ref="truth-1",
        validation_ref="validation-1",
        component_assessments=_component_assessments(),
        shadow_days_completed=30,
        shadow_report_ready=True,
        inter_engine_comparison_ready=True,
        build14_contribution_ready=True,
        runtime_evidence=evidence,
    )
    summary = run_shadow_validation(shadow_input)

    assert evidence.continuous_hours == 24.0
    assert summary.runtime_evidence_ready is True
    assert summary.decision.accepted is True


def test_shadow_runtime_evidence_recorder_persists_state_across_restart():
    state_dir = _scratch_dir("persist")
    shutil.rmtree(state_dir, ignore_errors=True)
    try:
        config = ShadowRuntimeEvidenceRecorderConfig(state_dir=state_dir, persist_state=True)
        recorder = ShadowRuntimeEvidenceRecorder(
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
            config=config,
        )
        recorder.mark_runtime_source("recorded_replay")
        recorder.mark_config_loaded("config/shadow.runtime.yaml")
        recorder.record_event_loop_tick(1_700_000_000_000)
        recorder.record_event_loop_tick(1_700_086_400_000)
        recorder.mark_shadow_dtr_persisted("shadow/dtr/day01.jsonl")

        reloaded = ShadowRuntimeEvidenceRecorder(
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
            config=config,
        )
        evidence = reloaded.build_evidence()

        assert evidence.continuous_hours == 24.0
        assert evidence.shadow_dtr_persisted is True
        assert evidence.config_loaded is True
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)
