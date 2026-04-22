"""Runtime tests for the minimal real Build-13 Live-Light gate."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from complete_enablers import (
    Build14InfluenceAction,
    Build14InfluenceMode,
    Build14InfluenceReport,
    Build14InfluenceSignal,
    Build14ObservationInput,
    Build14Severity,
    Build14SignalFamily,
    evaluate_build14_limited_influence,
    evaluate_build14_shadow_activation,
)
from interface_contracts import PairHealthLevel, ProfileId, ReviewState, RuntimeMode
from monitoring import (
    AlertProjection,
    Build9MetaProjection,
    Build9XProjection,
    LiveLightProjection,
    MicroLiveProjection,
    PortfolioMetrics,
    ReplayImportProjection,
    ShadowProjection,
    SystemProjection,
    TechnicalDashboardPayload,
)
from protocols import (
    InfoStressGovernanceSummary,
    LiveLightGateGroupSummary,
    LiveLightInput,
    LiveLightInputError,
    LiveLightRunSummary,
    LiveLightVerdict,
    MicroLiveDecision,
    MicroLiveExecutionPlan,
    MicroLiveRunState,
    MicroLiveRunSummary,
    MicroLiveVerdict,
    OperatorSafingAction,
    OperatorSafingRequest,
    RegimeLiteGovernanceSummary,
    ShadowPortfolioJudgment,
    ShadowVerdict,
    build_live_light_input_from_micro_live,
    run_live_light_gate,
)
from interface_contracts import PromotionState


def _gate_group(
    summary: LiveLightRunSummary,
    gate_id: str,
) -> LiveLightGateGroupSummary:
    return next(group for group in summary.gate_groups if group.gate_id == gate_id)


def _micro_live_payload(
    *,
    correlation_id: str = "corr-live",
    runtime_mode: RuntimeMode = RuntimeMode.MICRO_LIVE,
    profile: ProfileId = ProfileId.COMPLETE,
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
    replay_artifact_id: str | None = None,
    replay_lineage_version: str | None = None,
    replay_rejection_reasons: tuple[str, ...] = (),
    micro_live_run_state: str = "ready_to_probe",
    micro_live_verdict: str = "allowed_to_probe",
    micro_live_allowed_to_probe: bool = True,
) -> TechnicalDashboardPayload:
    return TechnicalDashboardPayload(
        timestamp_ms=1_700_000_000_000,
        correlation_id=correlation_id,
        profile=profile,
        runtime_mode=runtime_mode,
        system=SystemProjection(
            headline_status="healthy",
            active_modules=("protocols", "monitoring", "ui"),
            active_engines=("engine_a", "engine_b", "engine_c", "engine_d"),
            stale_engines=(),
            build9x_status="info",
            shadow_status="healthy",
            micro_live_status="healthy",
            live_light_status="planned",
            replay_import_status="healthy",
            governed_extensions_detail="Build-9X, Shadow, Micro-live, Live-Light, and replay/import remain governed.",
        ),
        portfolio=PortfolioMetrics(
            allocated_opportunities=2,
            gross_capacity_used_pct=18.0,
            loss_capacity_used_pct=5.0,
            beta_utilization=0.3,
            capital_deployed_usdt=400.0,
            ce_net=0.0013,
        ),
        build9_meta=Build9MetaProjection(
            dtr_coverage=0.9,
            dtr_status="healthy",
            cra_sterilization_rate=0.1,
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
        shadow=ShadowProjection(
            status="healthy",
            run_state="completed",
            verdict="accepted",
            truth_set_ref="truth-1",
            validation_set_ref="validation-1",
            divergent_comparison_count=0,
            blocking_comparison_count=0,
            total_comparison_count=7,
            build9x_diagnostics_count=0,
            open_hypotheses=0,
            replay_candidate_count=0,
            review_export_ready=True,
            import_artifact_id=artifact_id,
            import_lineage_version=lineage_version,
            blocking_reasons=(),
            manual_review_required=False,
            shadow_days_completed=30,
            shadow_required_days=30,
            shadow_report_ready=True,
            active_engine_count=4,
            build14_enabler_count=5,
            shadow_validated_component_count=8,
            dormant_component_count=1,
        ),
        micro_live=MicroLiveProjection(
            status="healthy",
            run_state=micro_live_run_state,
            verdict=micro_live_verdict,
            shadow_run_id="shadow-run-1",
            shadow_verdict="accepted",
            allowed_to_probe=micro_live_allowed_to_probe,
            requested_total_notional_usdt=40.0,
            approved_total_notional_usdt=40.0 if micro_live_allowed_to_probe else 0.0,
            approved_pair_notional_usdt=20.0 if micro_live_allowed_to_probe else 0.0,
            order_probe_limit=2,
            planned_pairs=("BTCUSDT", "ETHUSDT"),
            planned_engines=("engine_a", "engine_b", "engine_c", "engine_d"),
            import_artifact_id=artifact_id,
            import_lineage_version=lineage_version,
            observability_ready=True,
            halt_ready=True,
            onboarding_ready=True,
            blocking_reasons=(),
        ),
        live_light=LiveLightProjection(),
        replay_import=ReplayImportProjection(
            status="healthy" if validation_status == "accepted" else "warning",
            artifact_id=replay_artifact_id or artifact_id,
            artifact_kind="review_packet",
            exported_from=exported_from,
            source_profile=source_profile,
            lineage_version=replay_lineage_version or lineage_version,
            dataset_ref=dataset_ref,
            clock_ref=clock_ref,
            activation_stage=activation_stage,
            health_state=health_state,
            lifecycle_state="exported",
            validation_status=validation_status,
            review_state=review_state
            or ("pending" if validation_status == "accepted" else "needs_revision"),
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
            rejection_reasons=replay_rejection_reasons,
        ),
        alerts=AlertProjection(
            headline_status="healthy",
            active_alert_count=0,
            alert_ids=(),
            queue_backlog=0,
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


def _micro_live_summary(
    *,
    verdict: MicroLiveVerdict = MicroLiveVerdict.ALLOWED_TO_PROBE,
    run_state: MicroLiveRunState = MicroLiveRunState.READY_TO_PROBE,
    promotable_engines: tuple[str, ...] = ("engine_a", "engine_b", "engine_c", "engine_d"),
    shadow_only_engines: tuple[str, ...] = (),
    rewrite_required_engines: tuple[str, ...] = (),
    shadow_portfolio_judgment: ShadowPortfolioJudgment | None = None,
    planned_engines: tuple[str, ...] | None = None,
    execution_runtime_projection_ref: str = "",
    execution_runtime_projection_status: str = "not_configured",
    execution_runtime_projection_ready: bool = False,
    execution_runtime_projection_consumer_count: int = 0,
    execution_runtime_projection_ready_consumer_count: int = 0,
    execution_runtime_projection_partial_consumer_count: int = 0,
    execution_runtime_projection_blocked_consumer_count: int = 0,
    regime_lite_governance: RegimeLiteGovernanceSummary | None = None,
    info_stress_governance: InfoStressGovernanceSummary | None = None,
) -> MicroLiveRunSummary:
    resolved_planned_engines = planned_engines or promotable_engines
    return MicroLiveRunSummary(
        run_id="micro-run-1",
        correlation_id="corr-live",
        run_state=run_state,
        shadow_run_id="shadow-run-1",
        shadow_verdict=ShadowVerdict.ACCEPTED,
        decision=MicroLiveDecision(
            allowed_to_probe=verdict == MicroLiveVerdict.ALLOWED_TO_PROBE,
            verdict=verdict,
            normalized_promotion_state=(
                PromotionState.MICRO_LIVE_CANDIDATE
                if verdict == MicroLiveVerdict.ALLOWED_TO_PROBE
                else PromotionState.SHADOW_CANDIDATE
            ),
            review_state=ReviewState.PENDING if verdict == MicroLiveVerdict.ALLOWED_TO_PROBE else ReviewState.NEEDS_REVISION,
            approved_total_notional_usdt=40.0 if verdict == MicroLiveVerdict.ALLOWED_TO_PROBE else 0.0,
            approved_pair_notional_usdt=20.0 if verdict == MicroLiveVerdict.ALLOWED_TO_PROBE else 0.0,
            blocking_reasons=(),
            manual_review_required=verdict != MicroLiveVerdict.ALLOWED_TO_PROBE,
        ),
        execution_plan=MicroLiveExecutionPlan(
            plan_id="micro-plan-1",
            import_artifact_id="artifact-1",
            import_lineage_version="a.v1.0.r1",
            planned_engines=resolved_planned_engines,
            planned_pairs=("BTCUSDT", "ETHUSDT"),
            requested_total_notional_usdt=40.0,
            approved_total_notional_usdt=40.0 if verdict == MicroLiveVerdict.ALLOWED_TO_PROBE else 0.0,
            approved_pair_notional_usdt=20.0 if verdict == MicroLiveVerdict.ALLOWED_TO_PROBE else 0.0,
            order_probe_limit=2,
            dry_run_only=verdict != MicroLiveVerdict.ALLOWED_TO_PROBE,
            halt_guard_required=True,
        ),
        import_artifact_id="artifact-1",
        import_lineage_version="a.v1.0.r1",
        execution_runtime_projection_ref=execution_runtime_projection_ref,
        execution_runtime_projection_status=execution_runtime_projection_status,
        execution_runtime_projection_ready=execution_runtime_projection_ready,
        execution_runtime_projection_consumer_count=(
            execution_runtime_projection_consumer_count
        ),
        execution_runtime_projection_ready_consumer_count=(
            execution_runtime_projection_ready_consumer_count
        ),
        execution_runtime_projection_partial_consumer_count=(
            execution_runtime_projection_partial_consumer_count
        ),
        execution_runtime_projection_blocked_consumer_count=(
            execution_runtime_projection_blocked_consumer_count
        ),
        regime_lite_governance=regime_lite_governance or RegimeLiteGovernanceSummary(),
        info_stress_governance=info_stress_governance or InfoStressGovernanceSummary(),
        observability_ready=True,
        halt_ready=True,
        onboarding_ready=True,
        shadow_validated_engines=("engine_a", "engine_b", "engine_c", "engine_d"),
        shadow_promotable_engines=promotable_engines,
        shadow_shadow_only_engines=shadow_only_engines,
        shadow_rewrite_required_engines=rewrite_required_engines,
        shadow_portfolio_judgment=shadow_portfolio_judgment
        or ShadowPortfolioJudgment(judgment_verdict="promotable", rationale="test helper default"),
    )


def test_build_live_light_input_from_micro_live_maps_governed_inputs():
    live_input = build_live_light_input_from_micro_live(
        _micro_live_summary(
            execution_runtime_projection_ref="build/local_lab_execution_runtime_projection.json",
            execution_runtime_projection_status="ready",
            execution_runtime_projection_ready=True,
            execution_runtime_projection_consumer_count=3,
            execution_runtime_projection_ready_consumer_count=3,
        ),
        _micro_live_payload(),
        live_pairs=("BTCUSDT", "ETHUSDT"),
        requested_total_notional_usdt=80.0,
        requested_pair_notional_usdt=40.0,
        max_total_notional_usdt=100.0,
        max_pair_notional_usdt=50.0,
        micro_live_stable_days=7,
        observability_ready=True,
        halt_ready=True,
        execution_ready=True,
        broker_ready=True,
        exchange_ready=True,
        onboarding_accepted=True,
    )

    assert live_input.runtime_mode == RuntimeMode.LIVE
    assert live_input.micro_live_run_id == "micro-run-1"
    assert live_input.micro_live_import_artifact_id == "artifact-1"
    assert live_input.import_validation_status == "accepted"
    assert live_input.import_exported_from == "local"
    assert live_input.import_source_profile == "complete"
    assert live_input.import_dataset_ref == "dataset-1"
    assert live_input.import_clock_ref == "clock-1"
    assert live_input.import_feature_lineage_required is True
    assert live_input.import_feature_lineage_present is True
    assert live_input.import_feature_lineage_status == "ok"
    assert live_input.import_transform_whitelist_required is True
    assert live_input.import_transform_whitelist_present is True
    assert live_input.import_transform_whitelist_status == "ok"
    assert live_input.shadow_promotable_engines == (
        "engine_a",
        "engine_b",
        "engine_c",
        "engine_d",
    )
    assert live_input.execution_runtime_projection_ref.endswith(
        "local_lab_execution_runtime_projection.json"
    )
    assert live_input.execution_runtime_projection_status == "ready"
    assert live_input.execution_runtime_projection_ready is True
    assert live_input.execution_runtime_projection_ready_consumer_count == 3


def test_run_live_light_gate_blocks_when_shadow_portfolio_judgment_is_not_promotable():
    live_input = build_live_light_input_from_micro_live(
        _micro_live_summary(
            shadow_portfolio_judgment=ShadowPortfolioJudgment(
                judgment_verdict="shadow-only",
                physics_pressure="elevated",
                cluster_pressure="elevated",
                elevated_physics_engine_count=1,
                critical_physics_engine_count=1,
                rationale="portfolio concentration remained elevated in Shadow",
            )
        ),
        _micro_live_payload(),
        live_pairs=("BTCUSDT", "ETHUSDT"),
        requested_total_notional_usdt=80.0,
        requested_pair_notional_usdt=40.0,
        max_total_notional_usdt=100.0,
        max_pair_notional_usdt=50.0,
        micro_live_stable_days=7,
        observability_ready=True,
        halt_ready=True,
        execution_ready=True,
        broker_ready=True,
        exchange_ready=True,
        onboarding_accepted=True,
    )

    summary = run_live_light_gate(live_input)

    assert summary.decision.allowed_to_execute_small is False
    assert summary.decision.verdict == LiveLightVerdict.BLOCKED
    assert any(
        "shadow portfolio judgment=shadow-only" in reason
        for reason in summary.decision.blocking_reasons
    )


def test_run_live_light_gate_preserves_execution_runtime_projection_seam():
    live_input = build_live_light_input_from_micro_live(
        _micro_live_summary(
            execution_runtime_projection_ref="build/local_lab_execution_runtime_projection.json",
            execution_runtime_projection_status="partial",
            execution_runtime_projection_ready=False,
            execution_runtime_projection_consumer_count=3,
            execution_runtime_projection_ready_consumer_count=1,
            execution_runtime_projection_partial_consumer_count=2,
            execution_runtime_projection_blocked_consumer_count=0,
        ),
        _micro_live_payload(),
        live_pairs=("BTCUSDT", "ETHUSDT"),
        requested_total_notional_usdt=80.0,
        requested_pair_notional_usdt=40.0,
        max_total_notional_usdt=100.0,
        max_pair_notional_usdt=50.0,
        micro_live_stable_days=7,
        observability_ready=True,
        halt_ready=True,
        execution_ready=True,
        broker_ready=True,
        exchange_ready=True,
        onboarding_accepted=True,
    )

    summary = run_live_light_gate(live_input)

    assert summary.execution_runtime_projection_ref.endswith(
        "local_lab_execution_runtime_projection.json"
    )
    assert summary.execution_runtime_projection_status == "partial"
    assert summary.execution_runtime_projection_ready is False
    assert summary.execution_runtime_projection_consumer_count == 3
    assert summary.execution_runtime_projection_ready_consumer_count == 1
    assert summary.execution_runtime_projection_partial_consumer_count == 2
    assert summary.execution_runtime_projection_blocked_consumer_count == 0


def test_build_live_light_input_from_micro_live_preserves_regime_lite_governance():
    governance = RegimeLiteGovernanceSummary(
        status="ready",
        state="extreme",
        candidate_state="extreme",
        state_changed=True,
        entries_blocked=True,
        sudden_event=True,
        safing_severity="halt_recommended",
        should_block_new_entries=True,
        should_exit_all=True,
        recommended_operator_action="set_halted",
        operator_safing_request_action="set_halted",
        operator_safing_request_source_runtime_mode="shadow",
        reason_codes=("RG_EXTREME_BTC_DROP_1H", "RISK_REGIME_EXTREME_EXIT_ALL"),
        detail="explicit regime_lite governance summary",
    )
    live_input = build_live_light_input_from_micro_live(
        _micro_live_summary(regime_lite_governance=governance),
        _micro_live_payload(),
        live_pairs=("BTCUSDT", "ETHUSDT"),
        requested_total_notional_usdt=80.0,
        requested_pair_notional_usdt=40.0,
        max_total_notional_usdt=100.0,
        max_pair_notional_usdt=50.0,
        micro_live_stable_days=7,
        observability_ready=True,
        halt_ready=True,
        execution_ready=True,
        broker_ready=True,
        exchange_ready=True,
        onboarding_accepted=True,
    )

    assert live_input.regime_lite_governance == governance


def test_run_live_light_gate_preserves_regime_lite_governance_summary():
    governance = RegimeLiteGovernanceSummary(
        status="recommendation_only",
        state="not_configured",
        candidate_state="not_configured",
        safing_severity="entry_block_only",
        should_block_new_entries=True,
        reason_codes=("RISK_REGIME_EXTREME_COOLDOWN",),
        detail="recommendation supplied without explicit assessment",
    )
    live_input = build_live_light_input_from_micro_live(
        _micro_live_summary(regime_lite_governance=governance),
        _micro_live_payload(),
        live_pairs=("BTCUSDT", "ETHUSDT"),
        requested_total_notional_usdt=80.0,
        requested_pair_notional_usdt=40.0,
        max_total_notional_usdt=100.0,
        max_pair_notional_usdt=50.0,
        micro_live_stable_days=7,
        observability_ready=True,
        halt_ready=True,
        execution_ready=True,
        broker_ready=True,
        exchange_ready=True,
        onboarding_accepted=True,
    )

    summary = run_live_light_gate(live_input)

    assert summary.regime_lite_governance == governance


def test_build_live_light_input_from_micro_live_preserves_info_stress_governance():
    governance = InfoStressGovernanceSummary(
        status="assessment_only",
        level="extreme",
        alert_count=4,
        entries_blocked=True,
        entries_blocked_until_ts=1_700_000_600,
        reason_codes=("INFO_STRESS_SPREAD_EXPLOSION",),
        detail="explicit info_stress governance summary",
    )
    live_input = build_live_light_input_from_micro_live(
        _micro_live_summary(info_stress_governance=governance),
        _micro_live_payload(),
        live_pairs=("BTCUSDT", "ETHUSDT"),
        requested_total_notional_usdt=80.0,
        requested_pair_notional_usdt=40.0,
        max_total_notional_usdt=100.0,
        max_pair_notional_usdt=50.0,
        micro_live_stable_days=7,
        observability_ready=True,
        halt_ready=True,
        execution_ready=True,
        broker_ready=True,
        exchange_ready=True,
        onboarding_accepted=True,
    )

    assert live_input.info_stress_governance == governance


def test_run_live_light_gate_preserves_info_stress_governance_summary():
    governance = InfoStressGovernanceSummary(
        status="assessment_only",
        level="elevated",
        alert_count=1,
        entries_blocked=False,
        reason_codes=("INFO_STRESS_DEPTH_RATIO_COLLAPSE",),
        detail="assessment supplied without late-stage mutation",
    )
    live_input = build_live_light_input_from_micro_live(
        _micro_live_summary(info_stress_governance=governance),
        _micro_live_payload(),
        live_pairs=("BTCUSDT", "ETHUSDT"),
        requested_total_notional_usdt=80.0,
        requested_pair_notional_usdt=40.0,
        max_total_notional_usdt=100.0,
        max_pair_notional_usdt=50.0,
        micro_live_stable_days=7,
        observability_ready=True,
        halt_ready=True,
        execution_ready=True,
        broker_ready=True,
        exchange_ready=True,
        onboarding_accepted=True,
    )

    summary = run_live_light_gate(live_input)

    assert summary.info_stress_governance == governance


def test_build_live_light_input_from_micro_live_rejects_non_micro_live_source_payload():
    with pytest.raises(
        LiveLightInputError,
        match="source payload must originate from runtime_mode=MICRO_LIVE",
    ):
        build_live_light_input_from_micro_live(
            _micro_live_summary(),
            _micro_live_payload(runtime_mode=RuntimeMode.LIVE),
            live_pairs=("BTCUSDT",),
            requested_total_notional_usdt=80.0,
            requested_pair_notional_usdt=40.0,
            max_total_notional_usdt=100.0,
            max_pair_notional_usdt=50.0,
            micro_live_stable_days=7,
            observability_ready=True,
            halt_ready=True,
            execution_ready=True,
            broker_ready=True,
            exchange_ready=True,
            onboarding_accepted=True,
        )


def test_build_live_light_input_from_micro_live_rejects_import_artifact_mismatch():
    with pytest.raises(
        LiveLightInputError,
        match="matching Micro-live/import artifact_id",
    ):
        build_live_light_input_from_micro_live(
            _micro_live_summary(),
            _micro_live_payload(replay_artifact_id="artifact-2"),
            live_pairs=("BTCUSDT",),
            requested_total_notional_usdt=80.0,
            requested_pair_notional_usdt=40.0,
            max_total_notional_usdt=100.0,
            max_pair_notional_usdt=50.0,
            micro_live_stable_days=7,
            observability_ready=True,
            halt_ready=True,
            execution_ready=True,
            broker_ready=True,
            exchange_ready=True,
            onboarding_accepted=True,
        )


def test_build_live_light_input_from_micro_live_rejects_import_lineage_mismatch():
    with pytest.raises(
        LiveLightInputError,
        match="matching Micro-live/import lineage_version",
    ):
        build_live_light_input_from_micro_live(
            _micro_live_summary(),
            _micro_live_payload(replay_lineage_version="a.v1.0.r2"),
            live_pairs=("BTCUSDT",),
            requested_total_notional_usdt=80.0,
            requested_pair_notional_usdt=40.0,
            max_total_notional_usdt=100.0,
            max_pair_notional_usdt=50.0,
            micro_live_stable_days=7,
            observability_ready=True,
            halt_ready=True,
            execution_ready=True,
            broker_ready=True,
            exchange_ready=True,
            onboarding_accepted=True,
        )


def test_build_live_light_input_from_micro_live_rejects_non_empty_import_rejection_reasons():
    with pytest.raises(
        LiveLightInputError,
        match="empty replay import_rejection_reasons",
    ):
        build_live_light_input_from_micro_live(
            _micro_live_summary(),
            _micro_live_payload(replay_rejection_reasons=("lineage mismatch",)),
            live_pairs=("BTCUSDT",),
            requested_total_notional_usdt=80.0,
            requested_pair_notional_usdt=40.0,
            max_total_notional_usdt=100.0,
            max_pair_notional_usdt=50.0,
            micro_live_stable_days=7,
            observability_ready=True,
            halt_ready=True,
            execution_ready=True,
            broker_ready=True,
            exchange_ready=True,
            onboarding_accepted=True,
        )


def test_build_live_light_input_from_micro_live_rejects_non_governed_import_review_state():
    with pytest.raises(
        LiveLightInputError,
        match="replay import_review_state to stay pending or approved",
    ):
        build_live_light_input_from_micro_live(
            _micro_live_summary(),
            _micro_live_payload(review_state="needs_revision"),
            live_pairs=("BTCUSDT",),
            requested_total_notional_usdt=80.0,
            requested_pair_notional_usdt=40.0,
            max_total_notional_usdt=100.0,
            max_pair_notional_usdt=50.0,
            micro_live_stable_days=7,
            observability_ready=True,
            halt_ready=True,
            execution_ready=True,
            broker_ready=True,
            exchange_ready=True,
            onboarding_accepted=True,
        )


def test_build_live_light_input_from_micro_live_rejects_non_complete_import_source_profile():
    with pytest.raises(
        LiveLightInputError,
        match="replay import_source_profile=complete",
    ):
        build_live_light_input_from_micro_live(
            _micro_live_summary(),
            _micro_live_payload(source_profile="light"),
            live_pairs=("BTCUSDT",),
            requested_total_notional_usdt=80.0,
            requested_pair_notional_usdt=40.0,
            max_total_notional_usdt=100.0,
            max_pair_notional_usdt=50.0,
            micro_live_stable_days=7,
            observability_ready=True,
            halt_ready=True,
            execution_ready=True,
            broker_ready=True,
            exchange_ready=True,
            onboarding_accepted=True,
        )


def test_build_live_light_input_from_micro_live_rejects_non_local_import_origin():
    with pytest.raises(
        LiveLightInputError,
        match="replay import_exported_from=local",
    ):
        build_live_light_input_from_micro_live(
            _micro_live_summary(),
            _micro_live_payload(exported_from="vps"),
            live_pairs=("BTCUSDT",),
            requested_total_notional_usdt=80.0,
            requested_pair_notional_usdt=40.0,
            max_total_notional_usdt=100.0,
            max_pair_notional_usdt=50.0,
            micro_live_stable_days=7,
            observability_ready=True,
            halt_ready=True,
            execution_ready=True,
            broker_ready=True,
            exchange_ready=True,
            onboarding_accepted=True,
        )


def test_build_live_light_input_from_micro_live_rejects_non_shadow_ready_import_state():
    with pytest.raises(
        LiveLightInputError,
        match="replay import_activation_stage=shadow_ready",
    ):
        build_live_light_input_from_micro_live(
            _micro_live_summary(),
            _micro_live_payload(activation_stage="replay_only"),
            live_pairs=("BTCUSDT",),
            requested_total_notional_usdt=80.0,
            requested_pair_notional_usdt=40.0,
            max_total_notional_usdt=100.0,
            max_pair_notional_usdt=50.0,
            micro_live_stable_days=7,
            observability_ready=True,
            halt_ready=True,
            execution_ready=True,
            broker_ready=True,
            exchange_ready=True,
            onboarding_accepted=True,
        )

    with pytest.raises(
        LiveLightInputError,
        match="replay import_health_state=active",
    ):
        build_live_light_input_from_micro_live(
            _micro_live_summary(),
            _micro_live_payload(health_state="review_required"),
            live_pairs=("BTCUSDT",),
            requested_total_notional_usdt=80.0,
            requested_pair_notional_usdt=40.0,
            max_total_notional_usdt=100.0,
            max_pair_notional_usdt=50.0,
            micro_live_stable_days=7,
            observability_ready=True,
            halt_ready=True,
            execution_ready=True,
            broker_ready=True,
            exchange_ready=True,
            onboarding_accepted=True,
        )

    with pytest.raises(
        LiveLightInputError,
        match="replay import_feature_lineage_status=ok",
    ):
        build_live_light_input_from_micro_live(
            _micro_live_summary(),
            _micro_live_payload(
                feature_lineage_status="invalid",
                feature_lineage_reasons=("feature lineage missing",),
            ),
            live_pairs=("BTCUSDT",),
            requested_total_notional_usdt=80.0,
            requested_pair_notional_usdt=40.0,
            max_total_notional_usdt=100.0,
            max_pair_notional_usdt=50.0,
            micro_live_stable_days=7,
            observability_ready=True,
            halt_ready=True,
            execution_ready=True,
            broker_ready=True,
            exchange_ready=True,
            onboarding_accepted=True,
        )

    with pytest.raises(
        LiveLightInputError,
        match="replay import_transform_whitelist_status=ok",
    ):
        build_live_light_input_from_micro_live(
            _micro_live_summary(),
            _micro_live_payload(
                transform_whitelist_status="invalid",
                transform_whitelist_reasons=("transform whitelist missing",),
            ),
            live_pairs=("BTCUSDT",),
            requested_total_notional_usdt=80.0,
            requested_pair_notional_usdt=40.0,
            max_total_notional_usdt=100.0,
            max_pair_notional_usdt=50.0,
            micro_live_stable_days=7,
            observability_ready=True,
            halt_ready=True,
            execution_ready=True,
            broker_ready=True,
            exchange_ready=True,
            onboarding_accepted=True,
        )


def test_build_live_light_input_from_micro_live_rejects_live_pairs_outside_micro_live_surface():
    with pytest.raises(
        LiveLightInputError,
        match="live_pairs must stay within the governed Micro-live planned_pairs",
    ):
        build_live_light_input_from_micro_live(
            _micro_live_summary(),
            _micro_live_payload(),
            live_pairs=("SOLUSDT",),
            requested_total_notional_usdt=80.0,
            requested_pair_notional_usdt=40.0,
            max_total_notional_usdt=100.0,
            max_pair_notional_usdt=50.0,
            micro_live_stable_days=7,
            observability_ready=True,
            halt_ready=True,
            execution_ready=True,
            broker_ready=True,
            exchange_ready=True,
            onboarding_accepted=True,
        )


def test_build_live_light_input_from_micro_live_rejects_incomplete_shadow_from_payload():
    payload = _micro_live_payload().model_copy(
        update={
            "shadow": _micro_live_payload().shadow.model_copy(
                update={
                    "shadow_days_completed": 29,
                    "shadow_report_ready": False,
                    "shadow_validated_component_count": 0,
                    "dormant_component_count": 0,
                }
            )
        }
    )

    with pytest.raises(ValidationError, match="completed 30-day Shadow"):
        build_live_light_input_from_micro_live(
            _micro_live_summary(),
            payload,
            live_pairs=("BTCUSDT",),
            requested_total_notional_usdt=80.0,
            requested_pair_notional_usdt=40.0,
            max_total_notional_usdt=100.0,
            max_pair_notional_usdt=50.0,
            micro_live_stable_days=7,
            observability_ready=True,
            halt_ready=True,
            execution_ready=True,
            broker_ready=True,
            exchange_ready=True,
            onboarding_accepted=True,
        )


def test_build_live_light_input_from_micro_live_rejects_non_promotable_engine_from_shadow_judgment():
    with pytest.raises(
        ValidationError,
        match="active_engines must be PROMOTABLE in Shadow judgment",
    ):
        build_live_light_input_from_micro_live(
            _micro_live_summary(
                promotable_engines=("engine_a",),
                shadow_only_engines=("engine_b",),
                rewrite_required_engines=("engine_c",),
                planned_engines=("engine_a", "engine_b"),
            ),
            _micro_live_payload(),
            live_pairs=("BTCUSDT",),
            requested_total_notional_usdt=80.0,
            requested_pair_notional_usdt=40.0,
            max_total_notional_usdt=100.0,
            max_pair_notional_usdt=50.0,
            micro_live_stable_days=7,
            observability_ready=True,
            halt_ready=True,
            execution_ready=True,
            broker_ready=True,
            exchange_ready=True,
            onboarding_accepted=True,
            active_engines=("engine_b",),
        )


def test_build_live_light_input_from_micro_live_rejects_insufficient_stable_days():
    with pytest.raises(ValidationError, match="requires 7 stable Micro-live days"):
        build_live_light_input_from_micro_live(
            _micro_live_summary(),
            _micro_live_payload(),
            live_pairs=("BTCUSDT",),
            requested_total_notional_usdt=80.0,
            requested_pair_notional_usdt=40.0,
            max_total_notional_usdt=100.0,
            max_pair_notional_usdt=50.0,
            micro_live_stable_days=6,
            observability_ready=True,
            halt_ready=True,
            execution_ready=True,
            broker_ready=True,
            exchange_ready=True,
            onboarding_accepted=True,
        )


def test_run_live_light_gate_allows_small_execution_when_micro_live_and_guards_are_ready():
    summary = run_live_light_gate(
        build_live_light_input_from_micro_live(
            _micro_live_summary(),
            _micro_live_payload(),
            live_pairs=("BTCUSDT", "ETHUSDT"),
            requested_total_notional_usdt=80.0,
            requested_pair_notional_usdt=40.0,
            max_total_notional_usdt=100.0,
            max_pair_notional_usdt=50.0,
            micro_live_stable_days=7,
            observability_ready=True,
            halt_ready=True,
            execution_ready=True,
            broker_ready=True,
            exchange_ready=True,
            onboarding_accepted=True,
        )
    )

    assert summary.run_state.value == "ready_to_execute_small"
    assert summary.decision.verdict == LiveLightVerdict.ALLOWED_TO_EXECUTE_SMALL
    assert summary.decision.allowed_to_execute_small is True
    assert summary.execution_intent.approved_total_notional_usdt == 80.0
    assert {group.gate_id for group in summary.gate_groups} == {
        "governance_envelope",
        "promotion_history",
        "import_replay_integrity",
        "operational_readiness",
        "build14_influence",
    }
    assert all(group.status == "passed" for group in summary.gate_groups)


def test_run_live_light_gate_applies_build14_budget_downgrade_without_bypass():
    summary = run_live_light_gate(
        build_live_light_input_from_micro_live(
            _micro_live_summary(),
            _micro_live_payload(),
            live_pairs=("BTCUSDT", "ETHUSDT"),
            requested_total_notional_usdt=80.0,
            requested_pair_notional_usdt=40.0,
            max_total_notional_usdt=100.0,
            max_pair_notional_usdt=50.0,
            micro_live_stable_days=7,
            observability_ready=True,
            halt_ready=True,
            execution_ready=True,
            broker_ready=True,
            exchange_ready=True,
            onboarding_accepted=True,
            build14_live_eligible=True,
        ),
        build14_influence=Build14InfluenceSignal(
            correlation_id="corr-live",
            influence_mode=Build14InfluenceMode.LIMITED_INFLUENCE,
            action=Build14InfluenceAction.DOWNGRADE_CONFIDENCE,
            severity=Build14Severity.ELEVATED,
            families=(Build14SignalFamily.MICROSTRUCTURE,),
            summary="Elevated toxicity requires a bounded confidence downgrade",
            reason_codes=("market_toxicity_snapshot_elevated",),
            confidence_penalty_weight=0.10,
            recommended_budget_factor=0.85,
            requires_manual_review=False,
            candidate_effect="confidence_downgrade",
        ),
    )

    assert summary.decision.verdict == LiveLightVerdict.ALLOWED_TO_EXECUTE_SMALL
    assert summary.execution_intent.approved_total_notional_usdt == 68.0
    assert summary.decision.blocking_reasons == ()
    assert summary.build14_action == "downgrade_confidence"
    assert summary.build14_recommended_budget_factor == 0.85


def test_run_live_light_gate_keeps_build14_review_only_governed():
    summary = run_live_light_gate(
        build_live_light_input_from_micro_live(
            _micro_live_summary(),
            _micro_live_payload(),
            live_pairs=("BTCUSDT",),
            requested_total_notional_usdt=80.0,
            requested_pair_notional_usdt=40.0,
            max_total_notional_usdt=100.0,
            max_pair_notional_usdt=50.0,
            micro_live_stable_days=7,
            observability_ready=True,
            halt_ready=True,
            execution_ready=True,
            broker_ready=True,
            exchange_ready=True,
            onboarding_accepted=True,
            build14_live_eligible=True,
        ),
        build14_influence=Build14InfluenceSignal(
            correlation_id="corr-live",
            influence_mode=Build14InfluenceMode.LIMITED_INFLUENCE,
            action=Build14InfluenceAction.REVIEW_ONLY,
            severity=Build14Severity.CRITICAL,
            families=(Build14SignalFamily.AI_EDGE,),
            summary="Critical execution fragility requires manual review",
            reason_codes=("execution_fragility_score_critical",),
            confidence_penalty_weight=0.15,
            recommended_budget_factor=0.0,
            requires_manual_review=True,
            candidate_effect="review_only",
        ),
    )

    assert summary.decision.verdict == LiveLightVerdict.DRY_RUN_ONLY
    assert summary.execution_intent.dry_run_only is True
    assert "Critical execution fragility requires manual review" in summary.decision.blocking_reasons
    assert "build14 gate: execution_fragility_score_critical" in summary.decision.blocking_reasons
    build14_group = _gate_group(summary, "build14_influence")
    assert build14_group.status == "review_only"
    assert "Critical execution fragility requires manual review" in build14_group.reasons
    assert "build14 gate: execution_fragility_score_critical" in build14_group.reasons


def test_run_live_light_gate_accepts_typed_build14_report_with_matching_correlation():
    report = evaluate_build14_limited_influence(
        Build14ObservationInput(
            correlation_id="corr-live",
            dtr_coverage=0.75,
            cra_sterilization_rate=0.45,
            cra_alert_count=2,
            break_even_drift_alert=True,
            edge_degraded_count=1,
            queue_backlog=55,
            stale_pair_count=0,
            dtr_loss_count=0,
            log_loss_count=0,
            ce_net=0.0012,
        )
    )
    summary = run_live_light_gate(
        build_live_light_input_from_micro_live(
            _micro_live_summary(),
            _micro_live_payload(),
            live_pairs=("BTCUSDT",),
            requested_total_notional_usdt=80.0,
            requested_pair_notional_usdt=40.0,
            max_total_notional_usdt=100.0,
            max_pair_notional_usdt=50.0,
            micro_live_stable_days=7,
            observability_ready=True,
            halt_ready=True,
            execution_ready=True,
            broker_ready=True,
            exchange_ready=True,
            onboarding_accepted=True,
            build14_live_eligible=True,
        ),
        build14_influence=report,
    )

    assert summary.decision.verdict == LiveLightVerdict.ALLOWED_TO_EXECUTE_SMALL
    assert summary.execution_intent.approved_total_notional_usdt == 68.0
    assert summary.build14_action == "downgrade_confidence"


def test_run_live_light_gate_blocks_build14_influence_without_explicit_live_eligibility():
    summary = run_live_light_gate(
        build_live_light_input_from_micro_live(
            _micro_live_summary(),
            _micro_live_payload(),
            live_pairs=("BTCUSDT",),
            requested_total_notional_usdt=80.0,
            requested_pair_notional_usdt=40.0,
            max_total_notional_usdt=100.0,
            max_pair_notional_usdt=50.0,
            micro_live_stable_days=7,
            observability_ready=True,
            halt_ready=True,
            execution_ready=True,
            broker_ready=True,
            exchange_ready=True,
            onboarding_accepted=True,
        ),
        build14_influence=Build14InfluenceSignal(
            correlation_id="corr-live",
            influence_mode=Build14InfluenceMode.LIMITED_INFLUENCE,
            action=Build14InfluenceAction.DOWNGRADE_CONFIDENCE,
            severity=Build14Severity.ELEVATED,
            families=(Build14SignalFamily.MICROSTRUCTURE,),
            summary="Build-14 live influence must stay gated post-Shadow",
            reason_codes=("market_toxicity_snapshot_elevated",),
            confidence_penalty_weight=0.10,
            recommended_budget_factor=0.85,
            requires_manual_review=False,
            candidate_effect="confidence_downgrade",
        ),
    )

    assert summary.decision.verdict == LiveLightVerdict.BLOCKED
    assert summary.decision.allowed_to_execute_small is False
    assert (
        "Build-14 live influence requires explicit post-Shadow live eligibility"
        in summary.decision.blocking_reasons
    )


def test_run_live_light_gate_blocks_shadow_enabled_build14_report_in_live_light():
    report = evaluate_build14_shadow_activation(
        Build14ObservationInput(
            correlation_id="corr-live",
            dtr_coverage=0.75,
            cra_sterilization_rate=0.45,
            cra_alert_count=2,
            break_even_drift_alert=True,
            edge_degraded_count=1,
            queue_backlog=55,
            stale_pair_count=0,
            dtr_loss_count=0,
            log_loss_count=0,
            ce_net=0.0012,
        )
    )

    summary = run_live_light_gate(
        build_live_light_input_from_micro_live(
            _micro_live_summary(),
            _micro_live_payload(),
            live_pairs=("BTCUSDT",),
            requested_total_notional_usdt=80.0,
            requested_pair_notional_usdt=40.0,
            max_total_notional_usdt=100.0,
            max_pair_notional_usdt=50.0,
            micro_live_stable_days=7,
            observability_ready=True,
            halt_ready=True,
            execution_ready=True,
            broker_ready=True,
            exchange_ready=True,
            onboarding_accepted=True,
            build14_live_eligible=True,
        ),
        build14_influence=report,
    )

    assert summary.decision.verdict == LiveLightVerdict.BLOCKED
    assert summary.decision.allowed_to_execute_small is False
    assert (
        "Shadow-enabled Build-14 outputs require explicit post-Shadow live translation before Live-Light"
        in summary.decision.blocking_reasons
    )


def test_run_live_light_gate_blocks_when_execution_or_onboarding_is_missing():
    summary = run_live_light_gate(
        build_live_light_input_from_micro_live(
            _micro_live_summary(),
            _micro_live_payload(),
            live_pairs=("BTCUSDT",),
            requested_total_notional_usdt=80.0,
            requested_pair_notional_usdt=40.0,
            max_total_notional_usdt=100.0,
            max_pair_notional_usdt=50.0,
            micro_live_stable_days=7,
            observability_ready=True,
            halt_ready=True,
            execution_ready=False,
            broker_ready=True,
            exchange_ready=True,
            onboarding_accepted=False,
            onboarding_reasons=("manual sign-off missing",),
        )
    )

    assert summary.decision.verdict == LiveLightVerdict.BLOCKED
    assert "execution readiness must be confirmed before Live-Light execution" in summary.decision.blocking_reasons
    assert "strategy onboarding must be accepted before Live-Light" in summary.decision.blocking_reasons
    operational_group = _gate_group(summary, "operational_readiness")
    assert operational_group.status == "blocked"
    assert "execution readiness must be confirmed before Live-Light execution" in operational_group.reasons
    assert "strategy onboarding must be accepted before Live-Light" in operational_group.reasons


def test_run_live_light_gate_blocks_when_operator_requests_downgrade_to_micro_live():
    summary = run_live_light_gate(
        build_live_light_input_from_micro_live(
            _micro_live_summary(),
            _micro_live_payload(),
            live_pairs=("BTCUSDT",),
            requested_total_notional_usdt=80.0,
            requested_pair_notional_usdt=40.0,
            max_total_notional_usdt=100.0,
            max_pair_notional_usdt=50.0,
            micro_live_stable_days=7,
            observability_ready=True,
            halt_ready=True,
            operator_safing_request=OperatorSafingRequest(
                timestamp_ms=1_700_000_000_000,
                request_id="safing-live-1",
                action=OperatorSafingAction.DOWNGRADE_TO_MICRO_LIVE,
                source_runtime_mode=RuntimeMode.LIVE,
                target_runtime_mode=RuntimeMode.MICRO_LIVE,
                reason="execution drift requires step-down",
            ),
            execution_ready=True,
            broker_ready=True,
            exchange_ready=True,
            onboarding_accepted=True,
        )
    )

    assert summary.run_state == summary.run_state.__class__.BLOCKED
    assert summary.operator_safing_request is not None
    assert any(
        "operator safing request: downgrade_to_micro_live (live -> micro_live)" in reason
        for reason in summary.decision.blocking_reasons
    )


def test_run_live_light_gate_stays_dry_run_only_when_micro_live_needs_review():
    summary = run_live_light_gate(
        build_live_light_input_from_micro_live(
            _micro_live_summary(verdict=MicroLiveVerdict.DRY_RUN_ONLY),
            _micro_live_payload(
                micro_live_verdict="dry_run_only",
                micro_live_allowed_to_probe=False,
            ),
            live_pairs=("BTCUSDT",),
            requested_total_notional_usdt=80.0,
            requested_pair_notional_usdt=40.0,
            max_total_notional_usdt=100.0,
            max_pair_notional_usdt=50.0,
            micro_live_stable_days=7,
            observability_ready=True,
            halt_ready=True,
            execution_ready=True,
            broker_ready=True,
            exchange_ready=True,
            onboarding_accepted=True,
        )
    )

    assert summary.decision.verdict == LiveLightVerdict.DRY_RUN_ONLY
    assert summary.decision.allowed_to_execute_small is False
    assert summary.execution_intent.dry_run_only is True
    promotion_group = _gate_group(summary, "promotion_history")
    assert promotion_group.status == "review_only"
    assert promotion_group.reasons == (
        "Build-12 Micro-live verdict must be allowed_to_probe before Live-Light can execute small size",
    )


def test_run_live_light_gate_keeps_hard_blockers_stronger_than_dry_run():
    summary = run_live_light_gate(
        build_live_light_input_from_micro_live(
            _micro_live_summary(verdict=MicroLiveVerdict.DRY_RUN_ONLY),
            _micro_live_payload(
                micro_live_verdict="dry_run_only",
                micro_live_allowed_to_probe=False,
            ),
            live_pairs=("BTCUSDT",),
            requested_total_notional_usdt=80.0,
            requested_pair_notional_usdt=40.0,
            max_total_notional_usdt=100.0,
            max_pair_notional_usdt=50.0,
            micro_live_stable_days=7,
            observability_ready=True,
            halt_ready=False,
            execution_ready=True,
            broker_ready=True,
            exchange_ready=True,
            onboarding_accepted=True,
        )
    )

    assert summary.decision.verdict == LiveLightVerdict.BLOCKED
    assert "operator halt guard must be ready before Live-Light execution" in summary.decision.blocking_reasons


def test_run_live_light_gate_uses_complete_profile_for_shadow_counter_check(
    monkeypatch: pytest.MonkeyPatch,
):
    captured: dict[str, str] = {}

    def _fake_check_shadow_30j_gate(state_dir, profile):
        captured["profile"] = profile
        return True, {"consecutive_days": 30, "shadow_report_ready": True}

    monkeypatch.setattr(
        "protocols.shadow_runtime.check_shadow_30j_gate",
        _fake_check_shadow_30j_gate,
    )

    summary = run_live_light_gate(
        build_live_light_input_from_micro_live(
            _micro_live_summary(),
            _micro_live_payload(),
            live_pairs=("BTCUSDT",),
            requested_total_notional_usdt=80.0,
            requested_pair_notional_usdt=40.0,
            max_total_notional_usdt=100.0,
            max_pair_notional_usdt=50.0,
            micro_live_stable_days=7,
            observability_ready=True,
            halt_ready=True,
            execution_ready=True,
            broker_ready=True,
            exchange_ready=True,
            onboarding_accepted=True,
            build14_live_eligible=True,
        ),
        shadow_state_dir=Path("build"),
    )

    assert summary.decision.verdict == LiveLightVerdict.ALLOWED_TO_EXECUTE_SMALL
    assert captured["profile"] == "complete"


def test_run_live_light_gate_blocks_model_constructed_import_provenance_mismatch():
    live_input = build_live_light_input_from_micro_live(
        _micro_live_summary(),
        _micro_live_payload(),
        live_pairs=("BTCUSDT",),
        requested_total_notional_usdt=80.0,
        requested_pair_notional_usdt=40.0,
        max_total_notional_usdt=100.0,
        max_pair_notional_usdt=50.0,
        micro_live_stable_days=7,
        observability_ready=True,
        halt_ready=True,
        execution_ready=True,
        broker_ready=True,
        exchange_ready=True,
        onboarding_accepted=True,
        build14_live_eligible=True,
    )

    contradictory_input = LiveLightInput.model_construct(
        **{
            **live_input.model_dump(),
            "micro_live_import_artifact_id": "artifact-shadow",
        }
    )
    summary = run_live_light_gate(contradictory_input)

    assert summary.decision.verdict == LiveLightVerdict.BLOCKED
    assert summary.decision.allowed_to_execute_small is False
    assert "Build-13 Live-Light requires matching Micro-live/import artifact_id" in summary.decision.blocking_reasons


def test_run_live_light_gate_blocks_model_constructed_onboarding_contradiction():
    live_input = build_live_light_input_from_micro_live(
        _micro_live_summary(),
        _micro_live_payload(),
        live_pairs=("BTCUSDT",),
        requested_total_notional_usdt=80.0,
        requested_pair_notional_usdt=40.0,
        max_total_notional_usdt=100.0,
        max_pair_notional_usdt=50.0,
        micro_live_stable_days=7,
        observability_ready=True,
        halt_ready=True,
        execution_ready=True,
        broker_ready=True,
        exchange_ready=True,
        onboarding_accepted=True,
        build14_live_eligible=True,
    )

    contradictory_input = LiveLightInput.model_construct(
        **{
            **live_input.model_dump(),
            "onboarding_review_state": ReviewState.NEEDS_REVISION,
        }
    )
    summary = run_live_light_gate(contradictory_input)

    assert summary.decision.verdict == LiveLightVerdict.BLOCKED
    assert summary.decision.allowed_to_execute_small is False
    assert "accepted onboarding must keep a pending or approved review_state" in summary.decision.blocking_reasons


def test_run_live_light_gate_blocks_model_constructed_rejected_import_policy():
    live_input = build_live_light_input_from_micro_live(
        _micro_live_summary(),
        _micro_live_payload(),
        live_pairs=("BTCUSDT",),
        requested_total_notional_usdt=80.0,
        requested_pair_notional_usdt=40.0,
        max_total_notional_usdt=100.0,
        max_pair_notional_usdt=50.0,
        micro_live_stable_days=7,
        observability_ready=True,
        halt_ready=True,
        execution_ready=True,
        broker_ready=True,
        exchange_ready=True,
        onboarding_accepted=True,
        build14_live_eligible=True,
    )

    contradictory_input = LiveLightInput.model_construct(
        **{
            **live_input.model_dump(),
            "import_compatibility_status": "rejected",
            "import_compatibility_reasons": ("schema mismatch",),
            "import_feature_lineage_required": False,
            "import_feature_lineage_present": False,
            "import_feature_lineage_status": "invalid",
            "import_feature_lineage_reasons": ("feature lineage missing",),
            "import_transform_whitelist_required": False,
            "import_transform_whitelist_present": False,
            "import_transform_whitelist_status": "invalid",
            "import_transform_whitelist_reasons": ("transform whitelist missing",),
            "import_signature_check_status": "key_revoked",
            "import_signature_check_reasons": ("revoked signing key",),
            "import_conflict_resolution_mode": "first_artifact_wins",
            "import_registry_atomicity_mode": "in_place_mutation",
            "import_registry_publish_requires_atomic_replace": False,
            "import_payload_ref_count": 0,
            "import_payload_bundle_present": False,
            "import_review_export_ref": "",
        }
    )
    summary = run_live_light_gate(contradictory_input)

    assert summary.decision.verdict == LiveLightVerdict.BLOCKED
    assert summary.decision.allowed_to_execute_small is False
    assert (
        "Build-13 Live-Light requires a non-rejected import_compatibility_status"
        in summary.decision.blocking_reasons
    )
    assert "import compatibility gate: schema mismatch" in summary.decision.blocking_reasons
    assert (
        "Build-13 Live-Light requires a non-rejected import_signature_check_status"
        in summary.decision.blocking_reasons
    )
    assert "import signature gate: revoked signing key" in summary.decision.blocking_reasons
    assert (
        "Build-13 Live-Light requires import_feature_lineage_required=True"
        in summary.decision.blocking_reasons
    )
    assert (
        "Build-13 Live-Light requires import_feature_lineage_status=ok"
        in summary.decision.blocking_reasons
    )
    assert (
        "import feature lineage gate: feature lineage missing"
        in summary.decision.blocking_reasons
    )
    assert (
        "Build-13 Live-Light requires import_transform_whitelist_required=True"
        in summary.decision.blocking_reasons
    )
    assert (
        "Build-13 Live-Light requires import_transform_whitelist_status=ok"
        in summary.decision.blocking_reasons
    )
    assert (
        "import transform whitelist gate: transform whitelist missing"
        in summary.decision.blocking_reasons
    )
    assert (
        "Build-13 Live-Light requires canonical import_conflict_resolution_mode"
        in summary.decision.blocking_reasons
    )
    assert (
        "Build-13 Live-Light requires canonical import_registry_atomicity_mode"
        in summary.decision.blocking_reasons
    )
    assert (
        "Build-13 Live-Light requires import_registry_publish_requires_atomic_replace=True"
        in summary.decision.blocking_reasons
    )
    assert (
        "Build-13 Live-Light requires import_payload_ref_count>=5"
        in summary.decision.blocking_reasons
    )
    assert (
        "Build-13 Live-Light requires import_payload_bundle_present=True"
        in summary.decision.blocking_reasons
    )
    assert (
        "Build-13 Live-Light requires import_review_export_ref"
        in summary.decision.blocking_reasons
    )
    import_group = _gate_group(summary, "import_replay_integrity")
    assert import_group.status == "blocked"
    assert (
        "Build-13 Live-Light requires a non-rejected import_compatibility_status"
        in import_group.reasons
    )
    assert "import compatibility gate: schema mismatch" in import_group.reasons


def test_run_live_light_gate_blocks_model_constructed_non_complete_import_source_profile():
    live_input = build_live_light_input_from_micro_live(
        _micro_live_summary(),
        _micro_live_payload(),
        live_pairs=("BTCUSDT",),
        requested_total_notional_usdt=80.0,
        requested_pair_notional_usdt=40.0,
        max_total_notional_usdt=100.0,
        max_pair_notional_usdt=50.0,
        micro_live_stable_days=7,
        observability_ready=True,
        halt_ready=True,
        execution_ready=True,
        broker_ready=True,
        exchange_ready=True,
        onboarding_accepted=True,
        build14_live_eligible=True,
    )

    contradictory_input = LiveLightInput.model_construct(
        **{
            **live_input.model_dump(),
            "import_source_profile": "light",
        }
    )
    summary = run_live_light_gate(contradictory_input)

    assert summary.decision.verdict == LiveLightVerdict.BLOCKED
    assert summary.decision.allowed_to_execute_small is False
    assert (
        "Build-13 Live-Light requires import_source_profile=complete"
        in summary.decision.blocking_reasons
    )


def test_run_live_light_gate_blocks_model_constructed_non_local_import_origin():
    live_input = build_live_light_input_from_micro_live(
        _micro_live_summary(),
        _micro_live_payload(),
        live_pairs=("BTCUSDT",),
        requested_total_notional_usdt=80.0,
        requested_pair_notional_usdt=40.0,
        max_total_notional_usdt=100.0,
        max_pair_notional_usdt=50.0,
        micro_live_stable_days=7,
        observability_ready=True,
        halt_ready=True,
        execution_ready=True,
        broker_ready=True,
        exchange_ready=True,
        onboarding_accepted=True,
        build14_live_eligible=True,
    )

    contradictory_input = LiveLightInput.model_construct(
        **{
            **live_input.model_dump(),
            "import_exported_from": "vps",
        }
    )
    summary = run_live_light_gate(contradictory_input)

    assert summary.decision.verdict == LiveLightVerdict.BLOCKED
    assert summary.decision.allowed_to_execute_small is False
    assert (
        "Build-13 Live-Light requires import_exported_from=local"
        in summary.decision.blocking_reasons
    )


def test_run_live_light_gate_blocks_model_constructed_micro_live_surface_mismatch():
    live_input = build_live_light_input_from_micro_live(
        _micro_live_summary(),
        _micro_live_payload(),
        live_pairs=("BTCUSDT",),
        requested_total_notional_usdt=80.0,
        requested_pair_notional_usdt=40.0,
        max_total_notional_usdt=100.0,
        max_pair_notional_usdt=50.0,
        micro_live_stable_days=7,
        observability_ready=True,
        halt_ready=True,
        execution_ready=True,
        broker_ready=True,
        exchange_ready=True,
        onboarding_accepted=True,
        build14_live_eligible=True,
    )

    contradictory_input = LiveLightInput.model_construct(
        **{
            **live_input.model_dump(),
            "micro_live_planned_engines": ("engine_a",),
            "micro_live_planned_pairs": ("ETHUSDT",),
        }
    )
    summary = run_live_light_gate(contradictory_input)

    assert summary.decision.verdict == LiveLightVerdict.BLOCKED
    assert summary.decision.allowed_to_execute_small is False
    assert (
        "Build-13 Live-Light active_engines must stay within the governed Micro-live planned_engines"
        in summary.decision.blocking_reasons
    )
    assert (
        "Build-13 Live-Light live_pairs must stay within the governed Micro-live planned_pairs"
        in summary.decision.blocking_reasons
    )


def test_run_live_light_gate_blocks_model_constructed_live_surface_budget_mismatch():
    live_input = build_live_light_input_from_micro_live(
        _micro_live_summary(),
        _micro_live_payload(),
        live_pairs=("BTCUSDT",),
        requested_total_notional_usdt=80.0,
        requested_pair_notional_usdt=40.0,
        max_total_notional_usdt=100.0,
        max_pair_notional_usdt=50.0,
        micro_live_stable_days=7,
        observability_ready=True,
        halt_ready=True,
        execution_ready=True,
        broker_ready=True,
        exchange_ready=True,
        onboarding_accepted=True,
        build14_live_eligible=True,
    )

    contradictory_input = LiveLightInput.model_construct(
        **{
            **live_input.model_dump(),
            "live_pairs": ("DOGEUSDT",),
            "requested_total_notional_usdt": 140.0,
            "requested_pair_notional_usdt": 60.0,
            "max_total_notional_usdt": 100.0,
            "max_pair_notional_usdt": 50.0,
            "execution_order_limit": 0,
        }
    )
    summary = run_live_light_gate(contradictory_input)

    assert summary.decision.verdict == LiveLightVerdict.BLOCKED
    assert summary.decision.allowed_to_execute_small is False
    assert (
        "Build-13 Live-Light live_pairs must stay within the Complete pair scope"
        in summary.decision.blocking_reasons
    )
    assert (
        "Live-Light requested_total_notional_usdt exceeds max cap"
        in summary.decision.blocking_reasons
    )
    assert (
        "Live-Light requested_pair_notional_usdt exceeds max pair cap"
        in summary.decision.blocking_reasons
    )
    assert (
        "Build-13 Live-Light requires execution_order_limit within [1, 20]"
        in summary.decision.blocking_reasons
    )


def test_run_live_light_gate_blocks_model_constructed_rollout_temporal_mismatch():
    live_input = build_live_light_input_from_micro_live(
        _micro_live_summary(),
        _micro_live_payload(),
        live_pairs=("BTCUSDT",),
        requested_total_notional_usdt=80.0,
        requested_pair_notional_usdt=40.0,
        max_total_notional_usdt=100.0,
        max_pair_notional_usdt=50.0,
        micro_live_stable_days=7,
        observability_ready=True,
        halt_ready=True,
        execution_ready=True,
        broker_ready=True,
        exchange_ready=True,
        onboarding_accepted=True,
        build14_live_eligible=True,
    )

    contradictory_input = LiveLightInput.model_construct(
        **{
            **live_input.model_dump(),
            "shadow_days_completed": 29,
            "component_verdicts_rendered": False,
            "shadow_report_ready": False,
            "micro_live_stable_days": 6,
        }
    )
    summary = run_live_light_gate(contradictory_input)

    assert summary.decision.verdict == LiveLightVerdict.BLOCKED
    assert summary.decision.allowed_to_execute_small is False
    assert (
        "Build-13 Live-Light requires a completed 30-day Shadow"
        in summary.decision.blocking_reasons
    )
    assert (
        "Build-13 Live-Light requires rendered component verdicts from Shadow"
        in summary.decision.blocking_reasons
    )
    assert (
        "Build-13 Live-Light requires shadow_report_ready=True"
        in summary.decision.blocking_reasons
    )
    assert (
        "Build-13 Live-Light requires 7 stable Micro-live days"
        in summary.decision.blocking_reasons
    )


def test_run_live_light_gate_blocks_model_constructed_governance_envelope_mismatch():
    live_input = build_live_light_input_from_micro_live(
        _micro_live_summary(),
        _micro_live_payload(),
        live_pairs=("BTCUSDT",),
        requested_total_notional_usdt=80.0,
        requested_pair_notional_usdt=40.0,
        max_total_notional_usdt=100.0,
        max_pair_notional_usdt=50.0,
        micro_live_stable_days=7,
        observability_ready=True,
        halt_ready=True,
        execution_ready=True,
        broker_ready=True,
        exchange_ready=True,
        onboarding_accepted=True,
        build14_live_eligible=True,
    )

    contradictory_input = LiveLightInput.model_construct(
        **{
            **live_input.model_dump(),
            "correlation_id": " ",
            "profile": ProfileId.LIGHT,
            "runtime_mode": RuntimeMode.MICRO_LIVE,
            "micro_live_run_id": " ",
            "shadow_run_id": " ",
            "backtest_profile": "legacy",
            "creates_profile_fork": True,
            "automatic_complete_promotion_requested": True,
            "shadow_required_days": 29,
            "micro_live_required_days": 6,
            "micro_live_import_artifact_id": "none",
            "micro_live_import_lineage_version": "n/a",
            "import_artifact_id": "none",
            "import_lineage_version": "n/a",
            "operator_safing_request": OperatorSafingRequest(
                timestamp_ms=1_700_000_000_000,
                request_id="safing-bad-live",
                action=OperatorSafingAction.DOWNGRADE_TO_SHADOW,
                source_runtime_mode=RuntimeMode.LIVE,
                target_runtime_mode=RuntimeMode.SHADOW,
                reason="mismatched source",
            ),
        }
    )
    summary = run_live_light_gate(contradictory_input)

    assert summary.decision.verdict == LiveLightVerdict.BLOCKED
    assert summary.decision.allowed_to_execute_small is False
    assert "Build-13 Live-Light requires a concrete correlation_id" in summary.decision.blocking_reasons
    assert "Build-13 Live-Light opens in COMPLETE profile only" in summary.decision.blocking_reasons
    assert "Build-13 Live-Light requires runtime_mode=LIVE" in summary.decision.blocking_reasons
    assert "Build-13 Live-Light requires a concrete micro_live_run_id" in summary.decision.blocking_reasons
    assert "Build-13 Live-Light requires a concrete shadow_run_id" in summary.decision.blocking_reasons
    assert "BACKTEST_PROFILE is forbidden in the unified V5.3" in summary.decision.blocking_reasons
    assert "Local/VPS profile forks are forbidden" in summary.decision.blocking_reasons
    assert (
        "Build-13 Live-Light must not request automatic promotion to Complete"
        in summary.decision.blocking_reasons
    )
    assert "Build-13 Live-Light requires shadow_required_days=30" in summary.decision.blocking_reasons
    assert "Build-13 Live-Light requires micro_live_required_days=7" in summary.decision.blocking_reasons
    assert (
        "Build-13 Live-Light requires a concrete micro_live_import_artifact_id"
        in summary.decision.blocking_reasons
    )
    assert (
        "Build-13 Live-Light requires a concrete micro_live_import_lineage_version"
        in summary.decision.blocking_reasons
    )
    assert "Build-13 Live-Light requires a concrete import_artifact_id" in summary.decision.blocking_reasons
    assert "Build-13 Live-Light requires a concrete lineage_version" in summary.decision.blocking_reasons
    assert (
        "Build-13 Live-Light operator_safing_request must match source_runtime_mode=LIVE"
        in summary.decision.blocking_reasons
    )
    governance_group = _gate_group(summary, "governance_envelope")
    assert governance_group.status == "blocked"
    assert "Build-13 Live-Light opens in COMPLETE profile only" in governance_group.reasons
    assert "Build-13 Live-Light requires runtime_mode=LIVE" in governance_group.reasons


def test_run_live_light_gate_blocks_model_constructed_shadow_only_engine_scope():
    live_input = build_live_light_input_from_micro_live(
        _micro_live_summary(),
        _micro_live_payload(),
        live_pairs=("BTCUSDT",),
        requested_total_notional_usdt=80.0,
        requested_pair_notional_usdt=40.0,
        max_total_notional_usdt=100.0,
        max_pair_notional_usdt=50.0,
        micro_live_stable_days=7,
        observability_ready=True,
        halt_ready=True,
        execution_ready=True,
        broker_ready=True,
        exchange_ready=True,
        onboarding_accepted=True,
        build14_live_eligible=True,
    )

    contradictory_input = LiveLightInput.model_construct(
        **{
            **live_input.model_dump(),
            "active_engines": ("engine_b",),
            "shadow_promotable_engines": ("engine_a",),
            "shadow_shadow_only_engines": ("engine_b",),
            "shadow_rewrite_required_engines": ("engine_c",),
        }
    )
    summary = run_live_light_gate(contradictory_input)

    assert summary.decision.verdict == LiveLightVerdict.BLOCKED
    assert summary.decision.allowed_to_execute_small is False
    assert (
        "Build-13 Live-Light active_engines must be PROMOTABLE in Shadow judgment"
        in summary.decision.blocking_reasons
    )
    assert (
        "Build-13 Live-Light must not activate engines marked SHADOW_ONLY in Shadow judgment"
        in summary.decision.blocking_reasons
    )


def test_run_live_light_gate_blocks_typed_build14_signal_with_foreign_correlation_id():
    live_input = build_live_light_input_from_micro_live(
        _micro_live_summary(),
        _micro_live_payload(),
        live_pairs=("BTCUSDT",),
        requested_total_notional_usdt=80.0,
        requested_pair_notional_usdt=40.0,
        max_total_notional_usdt=100.0,
        max_pair_notional_usdt=50.0,
        micro_live_stable_days=7,
        observability_ready=True,
        halt_ready=True,
        execution_ready=True,
        broker_ready=True,
        exchange_ready=True,
        onboarding_accepted=True,
        build14_live_eligible=True,
    )

    summary = run_live_light_gate(
        live_input,
        build14_influence=Build14InfluenceSignal(
            correlation_id="corr-other",
            influence_mode=Build14InfluenceMode.LIMITED_INFLUENCE,
            action=Build14InfluenceAction.REVIEW_ONLY,
            severity=Build14Severity.CRITICAL,
            families=(Build14SignalFamily.AI_EDGE,),
            summary="Foreign Build-14 signal must be rejected",
            reason_codes=("execution_fragility_score_critical",),
            confidence_penalty_weight=0.15,
            recommended_budget_factor=0.0,
            requires_manual_review=True,
            candidate_effect="review_only",
        ),
    )

    assert summary.decision.verdict == LiveLightVerdict.BLOCKED
    assert summary.decision.allowed_to_execute_small is False
    assert (
        "Build-14 influence correlation_id must match the current Live-Light run"
        in summary.decision.blocking_reasons
    )


def test_run_live_light_gate_blocks_untyped_build14_object():
    live_input = build_live_light_input_from_micro_live(
        _micro_live_summary(),
        _micro_live_payload(),
        live_pairs=("BTCUSDT",),
        requested_total_notional_usdt=80.0,
        requested_pair_notional_usdt=40.0,
        max_total_notional_usdt=100.0,
        max_pair_notional_usdt=50.0,
        micro_live_stable_days=7,
        observability_ready=True,
        halt_ready=True,
        execution_ready=True,
        broker_ready=True,
        exchange_ready=True,
        onboarding_accepted=True,
        build14_live_eligible=True,
    )
    rogue_object = SimpleNamespace(
        correlation_id="corr-live",
        influence_mode="limited_influence",
        action="review_only",
        severity="critical",
        families=("ai_edge",),
        summary="Untyped object must be rejected",
        reason_codes=("execution_fragility_score_critical",),
        confidence_penalty_weight=0.15,
        recommended_budget_factor=0.0,
        requires_manual_review=True,
        candidate_effect="review_only",
        stability_confirmed=True,
        non_regression_required=True,
        can_override_engines=False,
        can_bypass_risk=False,
        can_bypass_portfolio=False,
        can_trade_autonomously=False,
    )

    summary = run_live_light_gate(live_input, build14_influence=rogue_object)

    assert summary.decision.verdict == LiveLightVerdict.BLOCKED
    assert summary.decision.allowed_to_execute_small is False
    assert (
        "Build-14 influence must be a typed Build14InfluenceSignal or Build14InfluenceReport"
        in summary.decision.blocking_reasons
    )


def test_run_live_light_gate_blocks_build14_duck_typed_impostor():
    live_input = build_live_light_input_from_micro_live(
        _micro_live_summary(),
        _micro_live_payload(),
        live_pairs=("BTCUSDT",),
        requested_total_notional_usdt=80.0,
        requested_pair_notional_usdt=40.0,
        max_total_notional_usdt=100.0,
        max_pair_notional_usdt=50.0,
        micro_live_stable_days=7,
        observability_ready=True,
        halt_ready=True,
        execution_ready=True,
        broker_ready=True,
        exchange_ready=True,
        onboarding_accepted=True,
        build14_live_eligible=True,
    )

    class Build14InfluenceSignal:
        __module__ = "complete_enablers.contracts"

        def __init__(self, **data):
            defaults = {
                "correlation_id": "corr-live",
                "influence_mode": "limited_influence",
                "action": "downgrade_confidence",
                "severity": "elevated",
                "families": ("microstructure",),
                "summary": "Duck-typed impostor must be rejected",
                "reason_codes": ("market_toxicity_snapshot_elevated",),
                "confidence_penalty_weight": 0.10,
                "recommended_budget_factor": 0.85,
                "requires_manual_review": False,
                "candidate_effect": "confidence_downgrade",
                "stability_confirmed": True,
                "non_regression_required": True,
                "can_override_engines": False,
                "can_bypass_risk": False,
                "can_bypass_portfolio": False,
                "can_trade_autonomously": False,
            }
            defaults.update(data)
            for key, value in defaults.items():
                setattr(self, key, value)

        def model_dump(self):
            return self.__dict__.copy()

        @classmethod
        def model_validate(cls, data):
            if isinstance(data, cls):
                return data
            return cls(**data)

    spoofed_signal = Build14InfluenceSignal()

    summary = run_live_light_gate(live_input, build14_influence=spoofed_signal)

    assert summary.decision.verdict == LiveLightVerdict.BLOCKED
    assert summary.decision.allowed_to_execute_small is False
    assert (
        "Build-14 influence must be a typed Build14InfluenceSignal or Build14InfluenceReport"
        in summary.decision.blocking_reasons
    )


def test_run_live_light_gate_blocks_model_constructed_partial_build14_report():
    live_input = build_live_light_input_from_micro_live(
        _micro_live_summary(),
        _micro_live_payload(),
        live_pairs=("BTCUSDT",),
        requested_total_notional_usdt=80.0,
        requested_pair_notional_usdt=40.0,
        max_total_notional_usdt=100.0,
        max_pair_notional_usdt=50.0,
        micro_live_stable_days=7,
        observability_ready=True,
        halt_ready=True,
        execution_ready=True,
        broker_ready=True,
        exchange_ready=True,
        onboarding_accepted=True,
        build14_live_eligible=True,
    )
    contradictory_report = Build14InfluenceReport.model_construct(
        correlation_id="corr-live",
        snapshots=(),
        signal=None,
    )

    summary = run_live_light_gate(live_input, build14_influence=contradictory_report)

    assert summary.decision.verdict == LiveLightVerdict.BLOCKED
    assert summary.decision.allowed_to_execute_small is False
    assert any(
        "Build-14 influence failed typed contract validation" in reason
        for reason in summary.decision.blocking_reasons
    )


def test_run_live_light_gate_blocks_model_constructed_build14_foreign_correlation():
    live_input = build_live_light_input_from_micro_live(
        _micro_live_summary(),
        _micro_live_payload(),
        live_pairs=("BTCUSDT",),
        requested_total_notional_usdt=80.0,
        requested_pair_notional_usdt=40.0,
        max_total_notional_usdt=100.0,
        max_pair_notional_usdt=50.0,
        micro_live_stable_days=7,
        observability_ready=True,
        halt_ready=True,
        execution_ready=True,
        broker_ready=True,
        exchange_ready=True,
        onboarding_accepted=True,
        build14_live_eligible=True,
    )
    contradictory_signal = Build14InfluenceSignal.model_construct(
        correlation_id="corr-other",
        influence_mode=Build14InfluenceMode.LIMITED_INFLUENCE,
        action=Build14InfluenceAction.REVIEW_ONLY,
        severity=Build14Severity.CRITICAL,
        families=(Build14SignalFamily.AI_EDGE,),
        summary="Foreign model-constructed signal must be rejected",
        reason_codes=("execution_fragility_score_critical",),
        confidence_penalty_weight=0.15,
        recommended_budget_factor=0.0,
        requires_manual_review=True,
        candidate_effect="review_only",
        stability_confirmed=True,
        non_regression_required=True,
        can_override_engines=False,
        can_bypass_risk=False,
        can_bypass_portfolio=False,
        can_trade_autonomously=False,
        classification="build14_enabler",
    )

    summary = run_live_light_gate(live_input, build14_influence=contradictory_signal)

    assert summary.decision.verdict == LiveLightVerdict.BLOCKED
    assert summary.decision.allowed_to_execute_small is False
    assert (
        "Build-14 influence correlation_id must match the current Live-Light run"
        in summary.decision.blocking_reasons
    )


def test_run_live_light_gate_blocks_model_constructed_build14_guardrail_bypass():
    live_input = build_live_light_input_from_micro_live(
        _micro_live_summary(),
        _micro_live_payload(),
        live_pairs=("BTCUSDT",),
        requested_total_notional_usdt=80.0,
        requested_pair_notional_usdt=40.0,
        max_total_notional_usdt=100.0,
        max_pair_notional_usdt=50.0,
        micro_live_stable_days=7,
        observability_ready=True,
        halt_ready=True,
        execution_ready=True,
        broker_ready=True,
        exchange_ready=True,
        onboarding_accepted=True,
        build14_live_eligible=True,
    )
    contradictory_signal = Build14InfluenceSignal.model_construct(
        correlation_id="corr-live",
        influence_mode=Build14InfluenceMode.LIMITED_INFLUENCE,
        action=Build14InfluenceAction.DOWNGRADE_CONFIDENCE,
        severity=Build14Severity.ELEVATED,
        families=(Build14SignalFamily.MICROSTRUCTURE,),
        summary="Forbidden autonomous bypass",
        reason_codes=("market_toxicity_snapshot_elevated",),
        confidence_penalty_weight=0.10,
        recommended_budget_factor=0.85,
        requires_manual_review=False,
        candidate_effect="confidence_downgrade",
        stability_confirmed=True,
        non_regression_required=True,
        can_override_engines=True,
        can_bypass_risk=False,
        can_bypass_portfolio=False,
        can_trade_autonomously=False,
        classification="build14_enabler",
    )

    summary = run_live_light_gate(live_input, build14_influence=contradictory_signal)

    assert summary.decision.verdict == LiveLightVerdict.BLOCKED
    assert summary.decision.allowed_to_execute_small is False
    assert any(
        "Build-14 influence must never bypass engines, risk, or portfolio" in reason
        for reason in summary.decision.blocking_reasons
    )
