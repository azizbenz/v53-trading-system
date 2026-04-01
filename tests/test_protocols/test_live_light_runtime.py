"""Runtime tests for the minimal real Build-13 Live-Light gate."""

from __future__ import annotations

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
    LiveLightInput,
    LiveLightInputError,
    LiveLightVerdict,
    MicroLiveDecision,
    MicroLiveExecutionPlan,
    MicroLiveRunState,
    MicroLiveRunSummary,
    MicroLiveVerdict,
    ShadowVerdict,
    build_live_light_input_from_micro_live,
    run_live_light_gate,
)
from interface_contracts import PromotionState


def _micro_live_payload(
    *,
    correlation_id: str = "corr-live",
    runtime_mode: RuntimeMode = RuntimeMode.MICRO_LIVE,
    profile: ProfileId = ProfileId.LIGHT,
    validation_status: str = "accepted",
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
            active_engines=("engine_a", "engine_b"),
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
            build14_enabler_count=4,
            shadow_validated_component_count=6,
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
            planned_engines=("engine_a", "engine_b"),
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
            lineage_version=replay_lineage_version or lineage_version,
            lifecycle_state="exported",
            validation_status=validation_status,
            review_state="pending" if validation_status == "accepted" else "needs_revision",
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
) -> MicroLiveRunSummary:
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
            planned_engines=("engine_a", "engine_b"),
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
        observability_ready=True,
        halt_ready=True,
        onboarding_ready=True,
    )


def test_build_live_light_input_from_micro_live_maps_governed_inputs():
    live_input = build_live_light_input_from_micro_live(
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

    assert live_input.runtime_mode == RuntimeMode.LIVE
    assert live_input.micro_live_run_id == "micro-run-1"
    assert live_input.micro_live_import_artifact_id == "artifact-1"
    assert live_input.import_validation_status == "accepted"


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
