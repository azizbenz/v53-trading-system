"""Dashboard projection tests for Build-11 Shadow."""

from __future__ import annotations

from interface_contracts import PromotionState, ReviewState
from protocols import (
    ShadowComparison,
    ShadowComponentAssessment,
    ShadowComponentHardState,
    ShadowComponentKind,
    ShadowComponentVerdict,
    ShadowComparisonStatus,
    ShadowDecision,
    ShadowDivergenceSeverity,
    ShadowRunState,
    ShadowRunSummary,
    ShadowVerdict,
    build_shadow_dashboard_section,
    build_shadow_projection,
)


def _summary() -> ShadowRunSummary:
    return ShadowRunSummary(
        run_id="shadow-run-1",
        correlation_id="corr-shadow",
        run_state=ShadowRunState.COMPLETED,
        truth_set_ref="truth-1",
        validation_set_ref="validation-1",
        comparisons=(
            ShadowComparison(
                comparison_id="cmp-1",
                metric_name="dtr_coverage_drop",
                baseline_value=0.84,
                candidate_value=0.81,
                delta=0.03,
                threshold=0.05,
                status=ShadowComparisonStatus.DIVERGENT,
                severity=ShadowDivergenceSeverity.WARNING,
                blocking=False,
                summary="within threshold",
            ),
        ),
        decision=ShadowDecision(
            accepted=False,
            verdict=ShadowVerdict.NEEDS_REVIEW,
            normalized_promotion_state=PromotionState.REPLAY_ONLY,
            review_state=ReviewState.NEEDS_REVISION,
            blocking_reasons=("Build-9X review export must be ready before accepting Shadow",),
            manual_review_required=True,
        ),
        import_artifact_id="artifact-1",
        import_lineage_version="a.v1.0.r1",
        build9x_diagnostics_count=2,
        open_hypotheses=1,
        replay_candidate_count=1,
        review_export_ready=False,
        active_engines=("engine_a", "engine_b", "engine_c", "engine_d"),
        build14_status="warning",
        shadow_days_completed=30,
        shadow_required_days=30,
        shadow_report_ready=True,
        inter_engine_comparison_ready=True,
        build14_contribution_ready=True,
        component_assessments=(
            ShadowComponentAssessment(
                component_id="engine_a",
                component_kind=ShadowComponentKind.ENGINE,
                hard_state=ShadowComponentHardState.SHADOW_ENABLED,
                verdict=ShadowComponentVerdict.SHADOW_VALIDATED,
                evidence_summary="engine_a contributed distinct shadow edge",
            ),
            ShadowComponentAssessment(
                component_id="build14_microstructure",
                component_kind=ShadowComponentKind.BUILD14_ENABLER,
                hard_state=ShadowComponentHardState.SHADOW_ENABLED,
                verdict=ShadowComponentVerdict.DORMANT,
                evidence_summary="microstructure stayed active but did not validate",
            ),
        ),
    )


def test_build_shadow_projection_returns_normalized_monitoring_summary():
    projection = build_shadow_projection(_summary())

    assert projection.status == "warning"
    assert projection.run_state == "completed"
    assert projection.verdict == "needs_review"
    assert projection.divergent_comparison_count == 1
    assert projection.blocking_comparison_count == 0
    assert projection.import_lineage_version == "a.v1.0.r1"
    assert projection.shadow_days_completed == 30
    assert projection.shadow_validated_component_count == 1
    assert projection.dormant_component_count == 1


def test_build_shadow_dashboard_section_renders_expected_cards():
    section = build_shadow_dashboard_section(_summary())

    assert section.title == "Build-11 Shadow"
    keys = {card.key for card in section.cards}
    assert keys == {
        "shadow_run_state",
        "shadow_verdict",
        "shadow_day_counter",
        "shadow_divergences",
        "shadow_candidate_state",
        "shadow_import_lineage",
        "shadow_component_verdicts",
        "shadow_blocking_reasons",
    }
    verdict = next(card for card in section.cards if card.key == "shadow_verdict")
    assert verdict.value == "needs_review"
    assert verdict.status == "warning"
    day_counter = next(card for card in section.cards if card.key == "shadow_day_counter")
    assert day_counter.value == "30/30"
