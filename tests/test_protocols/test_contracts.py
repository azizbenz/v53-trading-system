"""Contract tests for the minimal real Build-11 Shadow runtime."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

import protocols
from interface_contracts import ProfileId, PromotionState, ReviewState, RuntimeMode
from protocols import (
    LiveLightDecision,
    LiveLightExecutionIntent,
    LiveLightInput,
    LiveLightRunState,
    LiveLightRunSummary,
    LiveLightVerdict,
    MicroLiveDecision,
    MicroLiveExecutionPlan,
    MicroLiveInput,
    MicroLiveRunState,
    MicroLiveRunSummary,
    MicroLiveVerdict,
    ShadowComparison,
    ShadowComponentAssessment,
    ShadowComponentHardState,
    ShadowComponentKind,
    ShadowComponentVerdict,
    ShadowComparisonStatus,
    ShadowDecision,
    ShadowDivergenceSeverity,
    ShadowInput,
    ShadowRunState,
    ShadowRunSummary,
    ShadowTruthSet,
    ShadowValidationSet,
    ShadowVerdict,
)


def test_protocols_exports_expected_symbols():
    assert {
        "MicroLiveInput",
        "MicroLiveDecision",
        "MicroLiveExecutionPlan",
        "MicroLiveRunSummary",
        "LiveLightInput",
        "LiveLightDecision",
        "LiveLightExecutionIntent",
        "LiveLightRunSummary",
        "build_live_light_input_from_micro_live",
        "run_live_light_gate",
        "build_live_light_projection",
        "build_live_light_dashboard_section",
        "build_micro_live_input_from_shadow",
        "run_micro_live_gate",
        "build_micro_live_projection",
        "build_micro_live_dashboard_section",
        "ShadowTruthSet",
        "ShadowValidationSet",
        "ShadowInput",
        "ShadowComparison",
        "ShadowComponentAssessment",
        "ShadowDecision",
        "ShadowRunSummary",
        "ShadowComponentKind",
        "ShadowComponentHardState",
        "ShadowComponentVerdict",
        "build_shadow_input_from_payloads",
        "compare_shadow_candidate",
        "run_shadow_validation",
        "build_shadow_projection",
        "build_shadow_dashboard_section",
    }.issubset(set(protocols.__all__))


def test_shadow_input_rejects_wrong_runtime_mode():
    with pytest.raises(ValidationError):
        ShadowInput(
            correlation_id="corr-shadow",
            profile=ProfileId.LIGHT,
            runtime_mode=RuntimeMode.LOCAL_REPLAY,
            truth_set=ShadowTruthSet(
                truth_ref="truth-1",
                dtr_coverage=0.82,
                cra_sterilization_rate=0.11,
                break_even_drift_scope_count=0,
                edge_degraded_count=0,
                ce_net=0.0010,
                active_alert_count=1,
                queue_backlog=12,
            ),
            validation_set=ShadowValidationSet(
                validation_ref="validation-1",
                dtr_coverage=0.81,
                cra_sterilization_rate=0.12,
                break_even_drift_scope_count=0,
                edge_degraded_count=0,
                ce_net=0.0009,
                active_alert_count=1,
                queue_backlog=14,
                accepted_import=True,
                import_validation_status="accepted",
                import_artifact_id="artifact-1",
                import_lineage_version="a.v1.0.r1",
            ),
        )


def test_shadow_input_rejects_backtest_profile_and_implicit_promotion():
    truth = ShadowTruthSet(
        truth_ref="truth-1",
        dtr_coverage=0.82,
        cra_sterilization_rate=0.11,
        break_even_drift_scope_count=0,
        edge_degraded_count=0,
        ce_net=0.0010,
        active_alert_count=1,
        queue_backlog=12,
    )
    validation = ShadowValidationSet(
        validation_ref="validation-1",
        dtr_coverage=0.81,
        cra_sterilization_rate=0.12,
        break_even_drift_scope_count=0,
        edge_degraded_count=0,
        ce_net=0.0009,
        active_alert_count=1,
        queue_backlog=14,
        accepted_import=True,
        import_validation_status="accepted",
        import_artifact_id="artifact-1",
        import_lineage_version="a.v1.0.r1",
    )

    with pytest.raises(ValidationError):
        ShadowInput(
            correlation_id="corr-shadow",
            profile=ProfileId.LIGHT,
            runtime_mode=RuntimeMode.SHADOW,
            truth_set=truth,
            validation_set=validation,
            backtest_profile="paper_shadow",
        )

    with pytest.raises(ValidationError):
        ShadowInput(
            correlation_id="corr-shadow",
            profile=ProfileId.LIGHT,
            runtime_mode=RuntimeMode.SHADOW,
            truth_set=truth,
            validation_set=validation,
            automatic_promotion_requested=True,
        )


def test_shadow_run_summary_counts_divergent_and_blocking_comparisons():
    summary = ShadowRunSummary(
        run_id="shadow-run-1",
        correlation_id="corr-shadow",
        run_state=ShadowRunState.COMPLETED,
        truth_set_ref="truth-1",
        validation_set_ref="validation-1",
        comparisons=(
            ShadowComparison(
                comparison_id="cmp-1",
                metric_name="dtr_coverage_drop",
                baseline_value=0.82,
                candidate_value=0.80,
                delta=0.02,
                threshold=0.05,
                status=ShadowComparisonStatus.DIVERGENT,
                severity=ShadowDivergenceSeverity.WARNING,
                blocking=False,
                summary="within threshold",
            ),
            ShadowComparison(
                comparison_id="cmp-2",
                metric_name="queue_backlog_increase",
                baseline_value=12.0,
                candidate_value=54.0,
                delta=42.0,
                threshold=25.0,
                status=ShadowComparisonStatus.BLOCKING,
                severity=ShadowDivergenceSeverity.CRITICAL,
                blocking=True,
                summary="exceeded threshold",
            ),
        ),
        decision=ShadowDecision(
            accepted=False,
            verdict=ShadowVerdict.REJECTED,
            normalized_promotion_state=PromotionState.REPLAY_ONLY,
            review_state=ReviewState.NEEDS_REVISION,
            blocking_reasons=("queue backlog too high",),
            manual_review_required=True,
        ),
        import_artifact_id="artifact-1",
        import_lineage_version="a.v1.0.r1",
        build9x_diagnostics_count=2,
        open_hypotheses=1,
        replay_candidate_count=1,
        review_export_ready=True,
    )

    assert summary.divergent_comparison_count == 1
    assert summary.blocking_comparison_count == 1


def test_shadow_validation_set_rejects_accepted_import_with_incoherent_status():
    with pytest.raises(ValidationError):
        ShadowValidationSet(
            validation_ref="validation-1",
            dtr_coverage=0.81,
            cra_sterilization_rate=0.12,
            break_even_drift_scope_count=0,
            edge_degraded_count=0,
            ce_net=0.0009,
            active_alert_count=1,
            queue_backlog=14,
            accepted_import=True,
            import_validation_status="needs_revision",
            import_artifact_id="artifact-1",
            import_lineage_version="a.v1.0.r1",
        )


def test_shadow_validation_set_rejects_accepted_import_with_rejection_reasons():
    with pytest.raises(ValidationError):
        ShadowValidationSet(
            validation_ref="validation-1",
            dtr_coverage=0.81,
            cra_sterilization_rate=0.12,
            break_even_drift_scope_count=0,
            edge_degraded_count=0,
            ce_net=0.0009,
            active_alert_count=1,
            queue_backlog=14,
            accepted_import=True,
            import_validation_status="accepted",
            import_artifact_id="artifact-1",
            import_lineage_version="a.v1.0.r1",
            import_rejection_reasons=("lineage mismatch",),
        )


def test_shadow_validation_set_rejects_accepted_status_when_accept_flag_is_false():
    with pytest.raises(ValidationError):
        ShadowValidationSet(
            validation_ref="validation-1",
            dtr_coverage=0.81,
            cra_sterilization_rate=0.12,
            break_even_drift_scope_count=0,
            edge_degraded_count=0,
            ce_net=0.0009,
            active_alert_count=1,
            queue_backlog=14,
            accepted_import=False,
            import_validation_status="accepted",
            import_artifact_id="artifact-1",
            import_lineage_version="a.v1.0.r1",
        )


def test_shadow_validation_set_rejects_non_30_day_required_gate():
    with pytest.raises(ValidationError, match="shadow_required_days=30"):
        ShadowValidationSet(
            validation_ref="validation-1",
            dtr_coverage=0.81,
            cra_sterilization_rate=0.12,
            break_even_drift_scope_count=0,
            edge_degraded_count=0,
            ce_net=0.0009,
            active_alert_count=1,
            queue_backlog=14,
            accepted_import=True,
            import_validation_status="accepted",
            import_artifact_id="artifact-1",
            import_lineage_version="a.v1.0.r1",
            shadow_required_days=29,
        )


def test_shadow_validation_set_rejects_duplicate_component_assessments():
    assessment = ShadowComponentAssessment(
        component_id="engine_a",
        component_kind=ShadowComponentKind.ENGINE,
        hard_state=ShadowComponentHardState.SHADOW_ENABLED,
        verdict=ShadowComponentVerdict.SHADOW_VALIDATED,
        evidence_summary="engine_a remained useful throughout Shadow",
    )

    with pytest.raises(ValidationError, match="component assessments must be unique"):
        ShadowValidationSet(
            validation_ref="validation-1",
            dtr_coverage=0.81,
            cra_sterilization_rate=0.12,
            break_even_drift_scope_count=0,
            edge_degraded_count=0,
            ce_net=0.0009,
            active_alert_count=1,
            queue_backlog=14,
            accepted_import=True,
            import_validation_status="accepted",
            import_artifact_id="artifact-1",
            import_lineage_version="a.v1.0.r1",
            component_assessments=(assessment, assessment),
        )


def test_shadow_validation_set_accepts_coherent_import_state():
    validation = ShadowValidationSet(
        validation_ref="validation-1",
        dtr_coverage=0.81,
        cra_sterilization_rate=0.12,
        break_even_drift_scope_count=0,
        edge_degraded_count=0,
        ce_net=0.0009,
        active_alert_count=1,
        queue_backlog=14,
        accepted_import=True,
        import_validation_status="accepted",
        import_artifact_id="artifact-1",
        import_lineage_version="a.v1.0.r1",
        import_rejection_reasons=(),
    )

    assert validation.accepted_import is True
    assert validation.import_validation_status == "accepted"


def test_micro_live_input_rejects_wrong_runtime_mode_and_budget_overflow():
    with pytest.raises(ValidationError):
        MicroLiveInput(
            correlation_id="corr-micro",
            profile=ProfileId.LIGHT,
            runtime_mode=RuntimeMode.SHADOW,
            shadow_run_id="shadow-run-1",
            shadow_truth_set_ref="truth-1",
            shadow_validation_set_ref="validation-1",
            shadow_verdict=ShadowVerdict.ACCEPTED,
            shadow_run_state=ShadowRunState.COMPLETED,
            shadow_import_artifact_id="artifact-1",
            shadow_import_lineage_version="a.v1.0.r1",
            import_artifact_id="artifact-1",
            import_lineage_version="a.v1.0.r1",
            import_validation_status="accepted",
            onboarding_accepted=True,
            review_export_ready=True,
            observability_ready=True,
            halt_ready=True,
            active_engines=("engine_a",),
            probe_pairs=("BTCUSDT",),
            requested_total_notional_usdt=20.0,
            requested_pair_notional_usdt=10.0,
            max_total_notional_usdt=15.0,
            max_pair_notional_usdt=10.0,
        )


def test_micro_live_input_rejects_shadow_import_provenance_mismatch():
    with pytest.raises(ValidationError):
        MicroLiveInput(
            correlation_id="corr-micro",
            profile=ProfileId.LIGHT,
            runtime_mode=RuntimeMode.MICRO_LIVE,
            shadow_run_id="shadow-run-1",
            shadow_truth_set_ref="truth-1",
            shadow_validation_set_ref="validation-1",
            shadow_verdict=ShadowVerdict.ACCEPTED,
            shadow_run_state=ShadowRunState.COMPLETED,
            shadow_import_artifact_id="artifact-shadow",
            shadow_import_lineage_version="a.v1.0.r1",
            import_artifact_id="artifact-replay",
            import_lineage_version="a.v1.0.r1",
            import_validation_status="accepted",
            onboarding_accepted=True,
            onboarding_review_state=ReviewState.PENDING,
            review_export_ready=True,
            observability_ready=True,
            halt_ready=True,
            active_engines=("engine_a",),
            probe_pairs=("BTCUSDT",),
            requested_total_notional_usdt=20.0,
            requested_pair_notional_usdt=10.0,
            max_total_notional_usdt=25.0,
            max_pair_notional_usdt=12.5,
        )


def test_micro_live_input_rejects_accepted_import_with_rejection_reasons():
    with pytest.raises(ValidationError):
        MicroLiveInput(
            correlation_id="corr-micro",
            profile=ProfileId.LIGHT,
            runtime_mode=RuntimeMode.MICRO_LIVE,
            shadow_run_id="shadow-run-1",
            shadow_truth_set_ref="truth-1",
            shadow_validation_set_ref="validation-1",
            shadow_verdict=ShadowVerdict.ACCEPTED,
            shadow_run_state=ShadowRunState.COMPLETED,
            shadow_import_artifact_id="artifact-1",
            shadow_import_lineage_version="a.v1.0.r1",
            import_artifact_id="artifact-1",
            import_lineage_version="a.v1.0.r1",
            import_validation_status="accepted",
            import_rejection_reasons=("lineage mismatch",),
            onboarding_accepted=True,
            onboarding_review_state=ReviewState.PENDING,
            review_export_ready=True,
            observability_ready=True,
            halt_ready=True,
            active_engines=("engine_a",),
            probe_pairs=("BTCUSDT",),
            requested_total_notional_usdt=20.0,
            requested_pair_notional_usdt=10.0,
            max_total_notional_usdt=25.0,
            max_pair_notional_usdt=12.5,
        )


def test_micro_live_input_rejects_accepted_onboarding_with_incoherent_review_state():
    with pytest.raises(ValidationError):
        MicroLiveInput(
            correlation_id="corr-micro",
            profile=ProfileId.LIGHT,
            runtime_mode=RuntimeMode.MICRO_LIVE,
            shadow_run_id="shadow-run-1",
            shadow_truth_set_ref="truth-1",
            shadow_validation_set_ref="validation-1",
            shadow_verdict=ShadowVerdict.ACCEPTED,
            shadow_run_state=ShadowRunState.COMPLETED,
            shadow_import_artifact_id="artifact-1",
            shadow_import_lineage_version="a.v1.0.r1",
            import_artifact_id="artifact-1",
            import_lineage_version="a.v1.0.r1",
            import_validation_status="accepted",
            onboarding_accepted=True,
            onboarding_review_state=ReviewState.NEEDS_REVISION,
            review_export_ready=True,
            observability_ready=True,
            halt_ready=True,
            active_engines=("engine_a",),
            probe_pairs=("BTCUSDT",),
            requested_total_notional_usdt=20.0,
            requested_pair_notional_usdt=10.0,
            max_total_notional_usdt=25.0,
            max_pair_notional_usdt=12.5,
        )


def test_micro_live_input_rejects_accepted_onboarding_with_rejection_reasons():
    with pytest.raises(ValidationError):
        MicroLiveInput(
            correlation_id="corr-micro",
            profile=ProfileId.LIGHT,
            runtime_mode=RuntimeMode.MICRO_LIVE,
            shadow_run_id="shadow-run-1",
            shadow_truth_set_ref="truth-1",
            shadow_validation_set_ref="validation-1",
            shadow_verdict=ShadowVerdict.ACCEPTED,
            shadow_run_state=ShadowRunState.COMPLETED,
            shadow_import_artifact_id="artifact-1",
            shadow_import_lineage_version="a.v1.0.r1",
            import_artifact_id="artifact-1",
            import_lineage_version="a.v1.0.r1",
            import_validation_status="accepted",
            onboarding_accepted=True,
            onboarding_review_state=ReviewState.PENDING,
            onboarding_reasons=("manual sign-off missing",),
            review_export_ready=True,
            observability_ready=True,
            halt_ready=True,
            active_engines=("engine_a",),
            probe_pairs=("BTCUSDT",),
            requested_total_notional_usdt=20.0,
            requested_pair_notional_usdt=10.0,
            max_total_notional_usdt=25.0,
            max_pair_notional_usdt=12.5,
        )


def test_micro_live_decision_requires_allowed_flag_to_match_verdict():
    with pytest.raises(ValidationError):
        MicroLiveDecision(
            allowed_to_probe=False,
            verdict=MicroLiveVerdict.ALLOWED_TO_PROBE,
            normalized_promotion_state=PromotionState.MICRO_LIVE_CANDIDATE,
            review_state=ReviewState.PENDING,
        )


def test_micro_live_run_summary_counts_planned_surface():
    summary = MicroLiveRunSummary(
        run_id="micro-run-1",
        correlation_id="corr-micro",
        run_state=MicroLiveRunState.READY_TO_PROBE,
        shadow_run_id="shadow-run-1",
        shadow_verdict=ShadowVerdict.ACCEPTED,
        decision=MicroLiveDecision(
            allowed_to_probe=True,
            verdict=MicroLiveVerdict.ALLOWED_TO_PROBE,
            normalized_promotion_state=PromotionState.MICRO_LIVE_CANDIDATE,
            review_state=ReviewState.PENDING,
            approved_total_notional_usdt=20.0,
            approved_pair_notional_usdt=10.0,
            blocking_reasons=(),
            manual_review_required=False,
        ),
        execution_plan=MicroLiveExecutionPlan(
            plan_id="micro-plan-1",
            import_artifact_id="artifact-1",
            import_lineage_version="a.v1.0.r1",
            planned_engines=("engine_a", "engine_b"),
            planned_pairs=("BTCUSDT", "ETHUSDT"),
            requested_total_notional_usdt=20.0,
            approved_total_notional_usdt=20.0,
            approved_pair_notional_usdt=10.0,
            order_probe_limit=2,
            dry_run_only=False,
            halt_guard_required=True,
        ),
        import_artifact_id="artifact-1",
        import_lineage_version="a.v1.0.r1",
        observability_ready=True,
        halt_ready=True,
        onboarding_ready=True,
    )

    assert summary.planned_pair_count == 2
    assert summary.planned_engine_count == 2
    assert summary.blocking_reason_count == 0


def test_live_light_input_rejects_wrong_runtime_mode_and_budget_overflow():
    with pytest.raises(ValidationError):
        LiveLightInput(
            correlation_id="corr-live",
            profile=ProfileId.LIGHT,
            runtime_mode=RuntimeMode.MICRO_LIVE,
            micro_live_run_id="micro-run-1",
            shadow_run_id="shadow-run-1",
            micro_live_verdict=MicroLiveVerdict.ALLOWED_TO_PROBE,
            micro_live_run_state=MicroLiveRunState.READY_TO_PROBE,
            micro_live_import_artifact_id="artifact-1",
            micro_live_import_lineage_version="a.v1.0.r1",
            import_artifact_id="artifact-1",
            import_lineage_version="a.v1.0.r1",
            import_validation_status="accepted",
            onboarding_accepted=True,
            onboarding_review_state=ReviewState.PENDING,
            review_export_ready=True,
            observability_ready=True,
            halt_ready=True,
            execution_ready=True,
            broker_ready=True,
            exchange_ready=True,
            active_engines=("engine_a",),
            live_pairs=("BTCUSDT",),
            requested_total_notional_usdt=60.0,
            requested_pair_notional_usdt=30.0,
            max_total_notional_usdt=50.0,
            max_pair_notional_usdt=25.0,
        )


def test_live_light_input_rejects_micro_live_import_provenance_mismatch():
    with pytest.raises(ValidationError):
        LiveLightInput(
            correlation_id="corr-live",
            profile=ProfileId.LIGHT,
            runtime_mode=RuntimeMode.LIVE,
            micro_live_run_id="micro-run-1",
            shadow_run_id="shadow-run-1",
            micro_live_verdict=MicroLiveVerdict.ALLOWED_TO_PROBE,
            micro_live_run_state=MicroLiveRunState.READY_TO_PROBE,
            micro_live_import_artifact_id="artifact-micro",
            micro_live_import_lineage_version="a.v1.0.r1",
            import_artifact_id="artifact-live",
            import_lineage_version="a.v1.0.r1",
            import_validation_status="accepted",
            onboarding_accepted=True,
            onboarding_review_state=ReviewState.PENDING,
            review_export_ready=True,
            observability_ready=True,
            halt_ready=True,
            execution_ready=True,
            broker_ready=True,
            exchange_ready=True,
            active_engines=("engine_a",),
            live_pairs=("BTCUSDT",),
            requested_total_notional_usdt=40.0,
            requested_pair_notional_usdt=20.0,
            max_total_notional_usdt=60.0,
            max_pair_notional_usdt=30.0,
        )


def test_live_light_input_rejects_accepted_onboarding_with_incoherent_review_state():
    with pytest.raises(ValidationError):
        LiveLightInput(
            correlation_id="corr-live",
            profile=ProfileId.LIGHT,
            runtime_mode=RuntimeMode.LIVE,
            micro_live_run_id="micro-run-1",
            shadow_run_id="shadow-run-1",
            micro_live_verdict=MicroLiveVerdict.ALLOWED_TO_PROBE,
            micro_live_run_state=MicroLiveRunState.READY_TO_PROBE,
            micro_live_import_artifact_id="artifact-1",
            micro_live_import_lineage_version="a.v1.0.r1",
            import_artifact_id="artifact-1",
            import_lineage_version="a.v1.0.r1",
            import_validation_status="accepted",
            onboarding_accepted=True,
            onboarding_review_state=ReviewState.NEEDS_REVISION,
            review_export_ready=True,
            observability_ready=True,
            halt_ready=True,
            execution_ready=True,
            broker_ready=True,
            exchange_ready=True,
            active_engines=("engine_a",),
            live_pairs=("BTCUSDT",),
            requested_total_notional_usdt=40.0,
            requested_pair_notional_usdt=20.0,
            max_total_notional_usdt=60.0,
            max_pair_notional_usdt=30.0,
        )


def test_live_light_decision_requires_allowed_flag_to_match_verdict():
    with pytest.raises(ValidationError):
        LiveLightDecision(
            allowed_to_execute_small=False,
            verdict=LiveLightVerdict.ALLOWED_TO_EXECUTE_SMALL,
            normalized_promotion_state=PromotionState.LIVE_CANDIDATE,
            review_state=ReviewState.PENDING,
        )


def test_live_light_run_summary_counts_planned_surface():
    summary = LiveLightRunSummary(
        run_id="live-run-1",
        correlation_id="corr-live",
        run_state=LiveLightRunState.READY_TO_EXECUTE_SMALL,
        micro_live_run_id="micro-run-1",
        shadow_run_id="shadow-run-1",
        micro_live_verdict=MicroLiveVerdict.ALLOWED_TO_PROBE,
        decision=LiveLightDecision(
            allowed_to_execute_small=True,
            verdict=LiveLightVerdict.ALLOWED_TO_EXECUTE_SMALL,
            normalized_promotion_state=PromotionState.LIVE_CANDIDATE,
            review_state=ReviewState.PENDING,
            approved_total_notional_usdt=60.0,
            approved_pair_notional_usdt=30.0,
            blocking_reasons=(),
            manual_review_required=False,
        ),
        execution_intent=LiveLightExecutionIntent(
            intent_id="live-intent-1",
            import_artifact_id="artifact-1",
            import_lineage_version="a.v1.0.r1",
            planned_engines=("engine_a", "engine_b"),
            planned_pairs=("BTCUSDT", "ETHUSDT"),
            requested_total_notional_usdt=60.0,
            approved_total_notional_usdt=60.0,
            approved_pair_notional_usdt=30.0,
            execution_order_limit=3,
            dry_run_only=False,
            halt_guard_required=True,
            broker_ready_required=True,
            exchange_ready_required=True,
        ),
        import_artifact_id="artifact-1",
        import_lineage_version="a.v1.0.r1",
        observability_ready=True,
        halt_ready=True,
        execution_ready=True,
        broker_ready=True,
        exchange_ready=True,
        onboarding_ready=True,
    )

    assert summary.planned_pair_count == 2
    assert summary.planned_engine_count == 2
    assert summary.blocking_reason_count == 0
