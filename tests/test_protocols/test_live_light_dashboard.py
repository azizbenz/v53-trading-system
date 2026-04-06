"""Dashboard projection tests for Build-13 governed Live."""

from __future__ import annotations

from interface_contracts import PromotionState, ReviewState
from protocols import (
    LiveLightDecision,
    LiveLightExecutionIntent,
    OperatorSafingAction,
    OperatorSafingRequest,
    LiveLightRunState,
    LiveLightRunSummary,
    LiveLightVerdict,
    MicroLiveVerdict,
    build_live_light_dashboard_section,
    build_live_light_projection,
)


def _summary() -> LiveLightRunSummary:
    return LiveLightRunSummary(
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
            approved_total_notional_usdt=80.0,
            approved_pair_notional_usdt=40.0,
            blocking_reasons=(),
            manual_review_required=False,
        ),
        execution_intent=LiveLightExecutionIntent(
            intent_id="live-intent-1",
            import_artifact_id="artifact-1",
            import_lineage_version="a.v1.0.r1",
            planned_engines=("engine_a", "engine_b"),
            planned_pairs=("BTCUSDT", "ETHUSDT"),
            requested_total_notional_usdt=80.0,
            approved_total_notional_usdt=80.0,
            approved_pair_notional_usdt=40.0,
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
        build14_influence_mode="limited_influence",
        build14_action="downgrade_confidence",
        build14_severity="elevated",
        build14_summary="Elevated toxicity requires a bounded confidence downgrade",
        build14_reason_codes=("market_toxicity_snapshot_elevated",),
        build14_confidence_penalty_weight=0.10,
        build14_recommended_budget_factor=0.85,
    )


def test_build_live_light_projection_returns_normalized_monitoring_summary():
    projection = build_live_light_projection(_summary())

    assert projection.status == "healthy"
    assert projection.run_state == "ready_to_execute_small"
    assert projection.verdict == "allowed_to_execute_small"
    assert projection.approved_total_notional_usdt == 80.0
    assert projection.planned_pairs == ("BTCUSDT", "ETHUSDT")
    assert projection.build14_action == "downgrade_confidence"
    assert projection.build14_recommended_budget_factor == 0.85
    assert projection.operator_safing_action == ""


def test_build_live_light_dashboard_section_renders_expected_cards():
    section = build_live_light_dashboard_section(_summary())

    assert section.title == "Build-13 Live"
    keys = {card.key for card in section.cards}
    assert keys == {
        "live_light_run_state",
        "live_light_verdict",
        "live_light_budget",
        "live_light_surface",
        "live_light_readiness",
        "live_light_safing_request",
        "live_light_blocking_reasons",
    }
    verdict = next(card for card in section.cards if card.key == "live_light_verdict")
    budget = next(card for card in section.cards if card.key == "live_light_budget")
    assert verdict.value == "allowed_to_execute_small"
    assert verdict.status == "healthy"
    assert "build14=downgrade_confidence@0.85" in budget.detail


def test_build_live_light_dashboard_section_surfaces_manual_safing_request():
    summary = _summary().model_copy(
        update={
            "operator_safing_request": OperatorSafingRequest(
                timestamp_ms=1_700_000_000_000,
                request_id="live-safing-1",
                action=OperatorSafingAction.DOWNGRADE_TO_MICRO_LIVE,
                source_runtime_mode="live",
                target_runtime_mode="micro_live",
                reason="execution drift requires step-down",
            )
        }
    )

    projection = build_live_light_projection(summary)
    section = build_live_light_dashboard_section(summary)

    assert projection.operator_safing_action == "downgrade_to_micro_live"
    assert projection.operator_safing_target_runtime_mode == "micro_live"
    card = next(card for card in section.cards if card.key == "live_light_safing_request")
    assert card.value == "downgrade_to_micro_live -> micro_live"
    assert card.status == "warning"
    assert card.detail == "execution drift requires step-down"
