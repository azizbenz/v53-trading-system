"""Contract tests for the minimal real Build-11 Shadow runtime."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

import protocols
from interface_contracts import ProfileId, PromotionState, ReviewState, RuntimeMode
from protocols import (
    ShadowComparison,
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
        "ShadowTruthSet",
        "ShadowValidationSet",
        "ShadowInput",
        "ShadowComparison",
        "ShadowDecision",
        "ShadowRunSummary",
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
