"""Dashboard projection tests for Build-12 Micro-live."""

from __future__ import annotations

from interface_contracts import PromotionState, ReviewState
from protocols import (
    MicroLiveDecision,
    MicroLiveExecutionPlan,
    MicroLiveRunState,
    MicroLiveRunSummary,
    MicroLiveVerdict,
    ShadowVerdict,
    build_micro_live_dashboard_section,
    build_micro_live_projection,
)


def _summary() -> MicroLiveRunSummary:
    return MicroLiveRunSummary(
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


def test_build_micro_live_projection_returns_normalized_monitoring_summary():
    projection = build_micro_live_projection(_summary())

    assert projection.status == "healthy"
    assert projection.run_state == "ready_to_probe"
    assert projection.verdict == "allowed_to_probe"
    assert projection.approved_total_notional_usdt == 20.0
    assert projection.planned_pairs == ("BTCUSDT", "ETHUSDT")


def test_build_micro_live_dashboard_section_renders_expected_cards():
    section = build_micro_live_dashboard_section(_summary())

    assert section.title == "Build-12 Micro-live"
    keys = {card.key for card in section.cards}
    assert keys == {
        "micro_live_run_state",
        "micro_live_verdict",
        "micro_live_budget",
        "micro_live_surface",
        "micro_live_guardrails",
        "micro_live_blocking_reasons",
    }
    verdict = next(card for card in section.cards if card.key == "micro_live_verdict")
    assert verdict.value == "allowed_to_probe"
    assert verdict.status == "healthy"
