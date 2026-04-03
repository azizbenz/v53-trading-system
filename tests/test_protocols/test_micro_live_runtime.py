"""Runtime tests for the minimal real Build-12 Micro-live gate."""

from __future__ import annotations

import pytest

from interface_contracts import PairHealthLevel, ProfileId, ReviewState, RuntimeMode
from monitoring import (
    AlertProjection,
    Build9MetaProjection,
    Build9XProjection,
    MicroLiveProjection,
    PortfolioMetrics,
    ReplayImportProjection,
    ShadowProjection,
    SystemProjection,
    TechnicalDashboardPayload,
)
from protocols import (
    MicroLiveInput,
    MicroLiveInputError,
    MicroLiveVerdict,
    OperatorSafingAction,
    OperatorSafingRequest,
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
    build_micro_live_input_from_shadow,
    run_micro_live_gate,
)
from interface_contracts import PromotionState


def _shadow_component_assessments(
    *,
    dormant_component_ids: tuple[str, ...] = (
        "build14_microstructure",
        "build14_regime",
        "build14_covariance",
        "build14_risk_contribution",
        "build14_edge_diversity",
    ),
) -> tuple[ShadowComponentAssessment, ...]:
    dormant = set(dormant_component_ids)
    assessments: list[ShadowComponentAssessment] = []
    for component_id in ("engine_a", "engine_b", "engine_c", "engine_d"):
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
                evidence_summary=f"{component_id} shadow verdict rendered",
            )
        )
    for component_id in (
        "build14_microstructure",
        "build14_regime",
        "build14_covariance",
        "build14_risk_contribution",
        "build14_edge_diversity",
    ):
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
                evidence_summary=f"{component_id} shadow verdict rendered",
            )
        )
    return tuple(assessments)


def _shadow_payload(
    *,
    correlation_id: str = "corr-micro",
    runtime_mode: RuntimeMode = RuntimeMode.SHADOW,
    profile: ProfileId = ProfileId.LIGHT,
    validation_status: str = "accepted",
    artifact_id: str = "artifact-1",
    lineage_version: str = "a.v1.0.r1",
    replay_artifact_id: str | None = None,
    replay_lineage_version: str | None = None,
    replay_rejection_reasons: tuple[str, ...] = (),
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
            micro_live_status="planned",
            replay_import_status="healthy",
            governed_extensions_detail="Build-9X, Shadow, Micro-live, and replay/import remain governed.",
        ),
        portfolio=PortfolioMetrics(
            allocated_opportunities=2,
            gross_capacity_used_pct=12.0,
            loss_capacity_used_pct=4.0,
            beta_utilization=0.2,
            capital_deployed_usdt=200.0,
            ce_net=0.0011,
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
        micro_live=MicroLiveProjection(),
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


def _shadow_summary(
    *,
    verdict: ShadowVerdict = ShadowVerdict.ACCEPTED,
    run_state: ShadowRunState = ShadowRunState.COMPLETED,
    shadow_days_completed: int = 30,
    shadow_report_ready: bool = True,
    inter_engine_comparison_ready: bool = True,
    build14_contribution_ready: bool = True,
    component_assessments: tuple[ShadowComponentAssessment, ...] | None = None,
) -> ShadowRunSummary:
    return ShadowRunSummary(
        run_id="shadow-run-1",
        correlation_id="corr-micro",
        run_state=run_state,
        truth_set_ref="truth-1",
        validation_set_ref="validation-1",
        comparisons=(
            ShadowComparison(
                comparison_id="cmp-1",
                metric_name="dtr_coverage_drop",
                baseline_value=0.9,
                candidate_value=0.9,
                delta=0.0,
                threshold=0.05,
                status=ShadowComparisonStatus.MATCHING,
                severity=ShadowDivergenceSeverity.INFO,
                blocking=False,
                summary="matched",
            ),
        ),
        decision=ShadowDecision(
            accepted=verdict == ShadowVerdict.ACCEPTED,
            verdict=verdict,
            normalized_promotion_state=(
                PromotionState.SHADOW_CANDIDATE
                if verdict == ShadowVerdict.ACCEPTED
                else PromotionState.REPLAY_ONLY
            ),
            review_state=ReviewState.PENDING if verdict == ShadowVerdict.ACCEPTED else ReviewState.NEEDS_REVISION,
            blocking_reasons=(),
            manual_review_required=False,
        ),
        import_artifact_id="artifact-1",
        import_lineage_version="a.v1.0.r1",
        build9x_diagnostics_count=0,
        open_hypotheses=0,
        replay_candidate_count=0,
        review_export_ready=True,
        active_engines=("engine_a", "engine_b", "engine_c", "engine_d"),
        build14_status="warning",
        shadow_days_completed=shadow_days_completed,
        shadow_required_days=30,
        shadow_report_ready=shadow_report_ready,
        inter_engine_comparison_ready=inter_engine_comparison_ready,
        build14_contribution_ready=build14_contribution_ready,
        component_assessments=component_assessments or _shadow_component_assessments(),
    )


def test_build_micro_live_input_from_shadow_maps_governed_inputs():
    micro_input = build_micro_live_input_from_shadow(
        _shadow_summary(),
        _shadow_payload(),
        probe_pairs=("BTCUSDT", "ETHUSDT"),
        requested_total_notional_usdt=20.0,
        requested_pair_notional_usdt=10.0,
        max_total_notional_usdt=25.0,
        max_pair_notional_usdt=12.5,
        observability_ready=True,
        halt_ready=True,
        onboarding_accepted=True,
    )

    assert micro_input.runtime_mode == RuntimeMode.MICRO_LIVE
    assert micro_input.shadow_run_id == "shadow-run-1"
    assert micro_input.shadow_import_artifact_id == "artifact-1"
    assert micro_input.shadow_import_lineage_version == "a.v1.0.r1"
    assert micro_input.import_validation_status == "accepted"
    assert micro_input.active_engines == (
        "engine_a",
        "engine_b",
        "engine_c",
        "engine_d",
    )
    assert micro_input.shadow_validated_engines == (
        "engine_a",
        "engine_b",
        "engine_c",
        "engine_d",
    )


def test_build_micro_live_input_from_shadow_filters_to_shadow_validated_light_engines():
    micro_input = build_micro_live_input_from_shadow(
        _shadow_summary(
            component_assessments=_shadow_component_assessments(
                dormant_component_ids=(
                    "engine_b",
                    "engine_c",
                    "engine_d",
                    "build14_microstructure",
                    "build14_regime",
                    "build14_covariance",
                    "build14_risk_contribution",
                    "build14_edge_diversity",
                )
            )
        ),
        _shadow_payload(),
        probe_pairs=("BTCUSDT",),
        requested_total_notional_usdt=20.0,
        requested_pair_notional_usdt=10.0,
        max_total_notional_usdt=25.0,
        max_pair_notional_usdt=12.5,
        observability_ready=True,
        halt_ready=True,
        onboarding_accepted=True,
    )

    assert micro_input.active_engines == ("engine_a",)
    assert "engine_b" in micro_input.shadow_dormant_components
    assert "engine_c" in micro_input.shadow_dormant_components
    assert "engine_d" in micro_input.shadow_dormant_components


def test_build_micro_live_input_from_shadow_rejects_non_shadow_source_payload():
    with pytest.raises(
        MicroLiveInputError,
        match="source payload must originate from runtime_mode=SHADOW",
    ):
        build_micro_live_input_from_shadow(
            _shadow_summary(),
            _shadow_payload(runtime_mode=RuntimeMode.MICRO_LIVE),
            probe_pairs=("BTCUSDT",),
            requested_total_notional_usdt=20.0,
            requested_pair_notional_usdt=10.0,
            max_total_notional_usdt=25.0,
            max_pair_notional_usdt=12.5,
            observability_ready=True,
            halt_ready=True,
            onboarding_accepted=True,
        )


def test_build_micro_live_input_from_shadow_rejects_shadow_import_artifact_mismatch():
    with pytest.raises(
        MicroLiveInputError,
        match="matching Shadow/import artifact_id",
    ):
        build_micro_live_input_from_shadow(
            _shadow_summary(),
            _shadow_payload(replay_artifact_id="artifact-2"),
            probe_pairs=("BTCUSDT",),
            requested_total_notional_usdt=20.0,
            requested_pair_notional_usdt=10.0,
            max_total_notional_usdt=25.0,
            max_pair_notional_usdt=12.5,
            observability_ready=True,
            halt_ready=True,
            onboarding_accepted=True,
        )


def test_build_micro_live_input_from_shadow_rejects_shadow_import_lineage_mismatch():
    with pytest.raises(
        MicroLiveInputError,
        match="matching Shadow/import lineage_version",
    ):
        build_micro_live_input_from_shadow(
            _shadow_summary(),
            _shadow_payload(replay_lineage_version="a.v1.0.r2"),
            probe_pairs=("BTCUSDT",),
            requested_total_notional_usdt=20.0,
            requested_pair_notional_usdt=10.0,
            max_total_notional_usdt=25.0,
            max_pair_notional_usdt=12.5,
            observability_ready=True,
            halt_ready=True,
            onboarding_accepted=True,
        )


def test_build_micro_live_input_from_shadow_rejects_requesting_dormant_or_unvalidated_engine():
    with pytest.raises(
        MicroLiveInputError,
        match="active_engines must be SHADOW_VALIDATED",
    ):
        build_micro_live_input_from_shadow(
            _shadow_summary(
                component_assessments=_shadow_component_assessments(
                    dormant_component_ids=(
                    "engine_b",
                    "engine_c",
                    "engine_d",
                    "build14_microstructure",
                    "build14_regime",
                    "build14_covariance",
                        "build14_risk_contribution",
                        "build14_edge_diversity",
                    )
                )
            ),
            _shadow_payload(),
            probe_pairs=("BTCUSDT",),
            requested_total_notional_usdt=20.0,
            requested_pair_notional_usdt=10.0,
            max_total_notional_usdt=25.0,
            max_pair_notional_usdt=12.5,
            observability_ready=True,
            halt_ready=True,
            onboarding_accepted=True,
            active_engines=("engine_b",),
        )


def test_build_micro_live_input_from_shadow_rejects_non_empty_import_rejection_reasons():
    with pytest.raises(
        MicroLiveInputError,
        match="empty replay import_rejection_reasons",
    ):
        build_micro_live_input_from_shadow(
            _shadow_summary(),
            _shadow_payload(replay_rejection_reasons=("lineage mismatch",)),
            probe_pairs=("BTCUSDT",),
            requested_total_notional_usdt=20.0,
            requested_pair_notional_usdt=10.0,
            max_total_notional_usdt=25.0,
            max_pair_notional_usdt=12.5,
            observability_ready=True,
            halt_ready=True,
            onboarding_accepted=True,
        )


def test_build_micro_live_input_from_shadow_rejects_incomplete_shadow_gate():
    with pytest.raises(
        MicroLiveInputError,
        match="completed 30-day Shadow",
    ):
        build_micro_live_input_from_shadow(
            _shadow_summary(shadow_days_completed=29),
            _shadow_payload(),
            probe_pairs=("BTCUSDT",),
            requested_total_notional_usdt=20.0,
            requested_pair_notional_usdt=10.0,
            max_total_notional_usdt=25.0,
            max_pair_notional_usdt=12.5,
            observability_ready=True,
            halt_ready=True,
            onboarding_accepted=True,
        )

    with pytest.raises(
        MicroLiveInputError,
        match="shadow_report_ready=True",
    ):
        build_micro_live_input_from_shadow(
            _shadow_summary(shadow_report_ready=False),
            _shadow_payload(),
            probe_pairs=("BTCUSDT",),
            requested_total_notional_usdt=20.0,
            requested_pair_notional_usdt=10.0,
            max_total_notional_usdt=25.0,
            max_pair_notional_usdt=12.5,
            observability_ready=True,
            halt_ready=True,
            onboarding_accepted=True,
        )


def test_build_micro_live_input_from_shadow_rejects_non_accepted_import_status():
    with pytest.raises(
        MicroLiveInputError,
        match="accepted replay import_validation_status",
    ):
        build_micro_live_input_from_shadow(
            _shadow_summary(),
            _shadow_payload(validation_status="needs_revision"),
            probe_pairs=("BTCUSDT",),
            requested_total_notional_usdt=20.0,
            requested_pair_notional_usdt=10.0,
            max_total_notional_usdt=25.0,
            max_pair_notional_usdt=12.5,
            observability_ready=True,
            halt_ready=True,
            onboarding_accepted=True,
        )


def test_run_micro_live_gate_allows_probe_when_shadow_and_governance_are_ready():
    summary = run_micro_live_gate(
        build_micro_live_input_from_shadow(
            _shadow_summary(),
            _shadow_payload(),
            probe_pairs=("BTCUSDT", "ETHUSDT"),
            requested_total_notional_usdt=20.0,
            requested_pair_notional_usdt=10.0,
            max_total_notional_usdt=25.0,
            max_pair_notional_usdt=12.5,
            observability_ready=True,
            halt_ready=True,
            onboarding_accepted=True,
        )
    )

    assert summary.run_state.value == "ready_to_probe"
    assert summary.decision.verdict == MicroLiveVerdict.ALLOWED_TO_PROBE
    assert summary.decision.allowed_to_probe is True
    assert summary.execution_plan.approved_total_notional_usdt == 20.0
    assert summary.shadow_validated_engines == (
        "engine_a",
        "engine_b",
        "engine_c",
        "engine_d",
    )


def test_run_micro_live_gate_blocks_when_observability_or_onboarding_is_missing():
    summary = run_micro_live_gate(
        build_micro_live_input_from_shadow(
            _shadow_summary(),
            _shadow_payload(),
            probe_pairs=("BTCUSDT",),
            requested_total_notional_usdt=20.0,
            requested_pair_notional_usdt=10.0,
            max_total_notional_usdt=25.0,
            max_pair_notional_usdt=12.5,
            observability_ready=False,
            halt_ready=True,
            onboarding_accepted=False,
            onboarding_reasons=("manual sign-off missing",),
        )
    )

    assert summary.decision.verdict == MicroLiveVerdict.BLOCKED
    assert "Build-10 observability must be ready before Micro-live capital exposure" in summary.decision.blocking_reasons
    assert "strategy onboarding must be accepted before Micro-live" in summary.decision.blocking_reasons


def test_run_micro_live_gate_blocks_when_operator_requests_downgrade_to_shadow():
    summary = run_micro_live_gate(
        build_micro_live_input_from_shadow(
            _shadow_summary(),
            _shadow_payload(),
            probe_pairs=("BTCUSDT",),
            requested_total_notional_usdt=20.0,
            requested_pair_notional_usdt=10.0,
            max_total_notional_usdt=25.0,
            max_pair_notional_usdt=12.5,
            observability_ready=True,
            halt_ready=True,
            operator_safing_request=OperatorSafingRequest(
                timestamp_ms=1_700_000_000_000,
                request_id="safing-micro-1",
                action=OperatorSafingAction.DOWNGRADE_TO_SHADOW,
                source_runtime_mode=RuntimeMode.MICRO_LIVE,
                target_runtime_mode=RuntimeMode.SHADOW,
                reason="manual requalification requested",
            ),
            onboarding_accepted=True,
        )
    )

    assert summary.run_state == summary.run_state.__class__.BLOCKED
    assert summary.operator_safing_request is not None
    assert any(
        "operator safing request: downgrade_to_shadow (micro_live -> shadow)" in reason
        for reason in summary.decision.blocking_reasons
    )


def test_run_micro_live_gate_stays_dry_run_only_when_shadow_needs_review():
    summary = run_micro_live_gate(
        build_micro_live_input_from_shadow(
            _shadow_summary(verdict=ShadowVerdict.NEEDS_REVIEW),
            _shadow_payload(),
            probe_pairs=("BTCUSDT",),
            requested_total_notional_usdt=20.0,
            requested_pair_notional_usdt=10.0,
            max_total_notional_usdt=25.0,
            max_pair_notional_usdt=12.5,
            observability_ready=True,
            halt_ready=True,
            onboarding_accepted=True,
        )
    )

    assert summary.decision.verdict == MicroLiveVerdict.DRY_RUN_ONLY
    assert summary.decision.allowed_to_probe is False
    assert summary.execution_plan.dry_run_only is True


def test_run_micro_live_gate_keeps_hard_blockers_stronger_than_needs_review():
    summary = run_micro_live_gate(
        build_micro_live_input_from_shadow(
            _shadow_summary(verdict=ShadowVerdict.NEEDS_REVIEW),
            _shadow_payload(),
            probe_pairs=("BTCUSDT",),
            requested_total_notional_usdt=20.0,
            requested_pair_notional_usdt=10.0,
            max_total_notional_usdt=25.0,
            max_pair_notional_usdt=12.5,
            observability_ready=False,
            halt_ready=True,
            onboarding_accepted=True,
        )
    )

    assert summary.decision.verdict == MicroLiveVerdict.BLOCKED
    assert summary.run_state == summary.run_state.__class__.BLOCKED
    assert (
        "Build-10 observability must be ready before Micro-live capital exposure"
        in summary.decision.blocking_reasons
    )


def test_run_micro_live_gate_blocks_model_constructed_import_provenance_mismatch():
    micro_input = build_micro_live_input_from_shadow(
        _shadow_summary(),
        _shadow_payload(),
        probe_pairs=("BTCUSDT",),
        requested_total_notional_usdt=20.0,
        requested_pair_notional_usdt=10.0,
        max_total_notional_usdt=25.0,
        max_pair_notional_usdt=12.5,
        observability_ready=True,
        halt_ready=True,
        onboarding_accepted=True,
    )

    contradictory_input = MicroLiveInput.model_construct(
        **{
            **micro_input.model_dump(),
            "shadow_import_artifact_id": "artifact-shadow",
        }
    )
    summary = run_micro_live_gate(contradictory_input)

    assert summary.decision.verdict == MicroLiveVerdict.BLOCKED
    assert summary.decision.allowed_to_probe is False
    assert "Build-12 Micro-live requires matching Shadow/import artifact_id" in (
        summary.decision.blocking_reasons
    )


def test_run_micro_live_gate_blocks_model_constructed_onboarding_contradiction():
    micro_input = build_micro_live_input_from_shadow(
        _shadow_summary(),
        _shadow_payload(),
        probe_pairs=("BTCUSDT",),
        requested_total_notional_usdt=20.0,
        requested_pair_notional_usdt=10.0,
        max_total_notional_usdt=25.0,
        max_pair_notional_usdt=12.5,
        observability_ready=True,
        halt_ready=True,
        onboarding_accepted=True,
    )

    contradictory_input = MicroLiveInput.model_construct(
        **{
            **micro_input.model_dump(),
            "onboarding_review_state": ReviewState.NEEDS_REVISION,
        }
    )
    summary = run_micro_live_gate(contradictory_input)

    assert summary.decision.verdict == MicroLiveVerdict.BLOCKED
    assert summary.decision.allowed_to_probe is False
    assert "accepted onboarding must keep a pending or approved review_state" in (
        summary.decision.blocking_reasons
    )


def test_run_micro_live_gate_blocks_model_constructed_non_accepted_import_status():
    micro_input = build_micro_live_input_from_shadow(
        _shadow_summary(),
        _shadow_payload(),
        probe_pairs=("BTCUSDT",),
        requested_total_notional_usdt=20.0,
        requested_pair_notional_usdt=10.0,
        max_total_notional_usdt=25.0,
        max_pair_notional_usdt=12.5,
        observability_ready=True,
        halt_ready=True,
        onboarding_accepted=True,
    )

    contradictory_input = MicroLiveInput.model_construct(
        **{
            **micro_input.model_dump(),
            "import_validation_status": "needs_revision",
        }
    )
    summary = run_micro_live_gate(contradictory_input)

    assert summary.decision.verdict == MicroLiveVerdict.BLOCKED
    assert summary.decision.allowed_to_probe is False
    assert "Build-12 Micro-live requires an accepted import_validation_status" in (
        summary.decision.blocking_reasons
    )
