"""Runtime tests for the minimal real Build-13 Live-Light gate."""

from __future__ import annotations

import pytest

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
        observability_ready=True,
        halt_ready=True,
        execution_ready=True,
        broker_ready=True,
        exchange_ready=True,
        onboarding_accepted=True,
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
        observability_ready=True,
        halt_ready=True,
        execution_ready=True,
        broker_ready=True,
        exchange_ready=True,
        onboarding_accepted=True,
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
