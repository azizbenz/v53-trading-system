"""Runtime tests for the minimal real Build-12 Micro-live gate."""

from __future__ import annotations

import pytest

from interface_contracts import PairHealthLevel, ProfileId, ReviewState, RuntimeMode
from monitoring import (
    AlertProjection,
    Build9MetaProjection,
    Build9XProjection,
    EngineJudgmentCard,
    EngineJudgmentProjection,
    MicroLiveProjection,
    PortfolioMetrics,
    ReplayImportProjection,
    ShadowProjection,
    SystemProjection,
    TechnicalDashboardPayload,
    collect_engine_metrics,
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
    signature_check_status: str = "not_provided",
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
    engine_judgment_cards: tuple[EngineJudgmentCard, ...] | None = None,
) -> TechnicalDashboardPayload:
    resolved_engine_judgment_cards = engine_judgment_cards
    if resolved_engine_judgment_cards is None:
        resolved_engine_judgment_cards = (
            EngineJudgmentCard(
                engine_id="engine_a",
                component_verdict="shadow_validated",
                judgment_verdict="promotable",
                status="healthy",
            ),
            EngineJudgmentCard(
                engine_id="engine_b",
                component_verdict="shadow_validated",
                judgment_verdict="promotable",
                status="healthy",
            ),
            EngineJudgmentCard(
                engine_id="engine_c",
                component_verdict="shadow_validated",
                judgment_verdict="promotable",
                status="healthy",
            ),
            EngineJudgmentCard(
                engine_id="engine_d",
                component_verdict="shadow_validated",
                judgment_verdict="promotable",
                status="healthy",
            ),
        )
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
        engine_judgment=EngineJudgmentProjection(
            status="healthy" if resolved_engine_judgment_cards else "planned",
            source_report_id="shadow-report-1" if resolved_engine_judgment_cards else "",
            source_shadow_run_id="shadow-run-1" if resolved_engine_judgment_cards else "",
            source_shadow_days_completed=30 if resolved_engine_judgment_cards else 0,
            source_shadow_required_days=30,
            cards=resolved_engine_judgment_cards,
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
    assert micro_input.import_exported_from == "local"
    assert micro_input.import_source_profile == "complete"
    assert micro_input.import_dataset_ref == "dataset-1"
    assert micro_input.import_clock_ref == "clock-1"
    assert micro_input.import_feature_lineage_required is True
    assert micro_input.import_feature_lineage_present is True
    assert micro_input.import_feature_lineage_status == "ok"
    assert micro_input.import_transform_whitelist_required is True
    assert micro_input.import_transform_whitelist_present is True
    assert micro_input.import_transform_whitelist_status == "ok"
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
        match="active_engines must be PROMOTABLE in Shadow judgment",
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


def test_build_micro_live_input_from_shadow_prefers_promotable_engine_judgments():
    micro_input = build_micro_live_input_from_shadow(
        _shadow_summary(
            component_assessments=_shadow_component_assessments(dormant_component_ids=("engine_d",))
        ),
        _shadow_payload(
            engine_judgment_cards=(
                EngineJudgmentCard(
                    engine_id="engine_a",
                    component_verdict="shadow_validated",
                    judgment_verdict="promotable",
                    status="healthy",
                ),
                EngineJudgmentCard(
                    engine_id="engine_b",
                    component_verdict="shadow_validated",
                    judgment_verdict="shadow-only",
                    status="warning",
                ),
                EngineJudgmentCard(
                    engine_id="engine_c",
                    component_verdict="shadow_validated",
                    judgment_verdict="rewrite-required",
                    status="critical",
                ),
                EngineJudgmentCard(
                    engine_id="engine_d",
                    component_verdict="dormant",
                    judgment_verdict="dormant",
                    status="planned",
                ),
            )
        ),
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
    assert micro_input.shadow_promotable_engines == ("engine_a",)
    assert micro_input.shadow_shadow_only_engines == ("engine_b",)
    assert micro_input.shadow_rewrite_required_engines == ("engine_c",)
    assert micro_input.shadow_portfolio_judgment.judgment_verdict == "shadow-only"


def test_build_micro_live_input_from_shadow_rejects_requesting_non_promotable_engine_judgment():
    with pytest.raises(
        MicroLiveInputError,
        match="active_engines must be PROMOTABLE in Shadow judgment",
    ):
        build_micro_live_input_from_shadow(
            _shadow_summary(),
            _shadow_payload(
                engine_judgment_cards=(
                    EngineJudgmentCard(
                        engine_id="engine_a",
                        component_verdict="shadow_validated",
                        judgment_verdict="promotable",
                        status="healthy",
                    ),
                    EngineJudgmentCard(
                        engine_id="engine_b",
                        component_verdict="shadow_validated",
                        judgment_verdict="shadow-only",
                        status="warning",
                    ),
                    EngineJudgmentCard(
                        engine_id="engine_c",
                        component_verdict="shadow_validated",
                        judgment_verdict="rewrite-required",
                        status="critical",
                    ),
                    EngineJudgmentCard(
                        engine_id="engine_d",
                        component_verdict="shadow_validated",
                        judgment_verdict="promotable",
                        status="healthy",
                    ),
                )
            ),
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


def test_build_micro_live_input_from_shadow_falls_back_to_payload_engine_scope_when_judgment_bundle_missing():
    micro_input = build_micro_live_input_from_shadow(
        _shadow_summary(),
        _shadow_payload(engine_judgment_cards=()).model_copy(
            update={
                "engines": (
                    collect_engine_metrics(
                        engine_id="engine_a",
                        emitted_signals=2,
                        net_edge_bps=12.0,
                        expected_cost_bps=4.0,
                        ce_expected=0.0007,
                        scoring_final_size_multiplier=1.0,
                        selection_outcome_code="selected",
                        portfolio_verdict_code="compatible",
                        risk_decision_severity="nominal",
                    ),
                    collect_engine_metrics(
                        engine_id="engine_b",
                        emitted_signals=1,
                        net_edge_bps=4.0,
                        expected_cost_bps=3.0,
                        ce_expected=0.0002,
                        scoring_final_size_multiplier=1.0,
                        selection_outcome_code="rejected_portfolio",
                        portfolio_verdict_code="rejected_cluster",
                        risk_decision_severity="warning",
                    ),
                    collect_engine_metrics(
                        engine_id="engine_c",
                        emitted_signals=1,
                        net_edge_bps=3.0,
                        expected_cost_bps=2.5,
                        ce_expected=0.0001,
                        scoring_final_size_multiplier=0.05,
                        selection_outcome_code="rejected_ranking",
                        portfolio_verdict_code="compatible",
                        risk_decision_severity="critical",
                    ),
                    collect_engine_metrics(
                        engine_id="engine_d",
                        emitted_signals=1,
                        net_edge_bps=2.0,
                        expected_cost_bps=2.0,
                        ce_expected=0.0001,
                        scoring_final_size_multiplier=1.0,
                        selection_outcome_code="selected",
                        portfolio_verdict_code="compatible",
                        phantom_trade=True,
                        risk_decision_severity="nominal",
                    ),
                )
            }
        ),
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
    assert micro_input.shadow_promotable_engines == ("engine_a",)
    assert micro_input.shadow_shadow_only_engines == ("engine_c",)
    assert set(micro_input.shadow_rewrite_required_engines) == {"engine_b", "engine_d"}
    assert micro_input.shadow_portfolio_judgment.judgment_verdict == "rewrite-required"


def test_run_micro_live_gate_blocks_when_shadow_portfolio_judgment_is_not_promotable():
    micro_input = build_micro_live_input_from_shadow(
        _shadow_summary(),
        _shadow_payload(engine_judgment_cards=()).model_copy(
            update={
                "engines": (
                    collect_engine_metrics(
                        engine_id="engine_a",
                        emitted_signals=2,
                        net_edge_bps=12.0,
                        expected_cost_bps=4.0,
                        ce_expected=0.0007,
                        scoring_final_size_multiplier=1.0,
                        selection_outcome_code="selected",
                        portfolio_verdict_code="compatible",
                        risk_decision_severity="nominal",
                    ),
                    collect_engine_metrics(
                        engine_id="engine_b",
                        emitted_signals=1,
                        net_edge_bps=4.0,
                        expected_cost_bps=3.0,
                        ce_expected=0.0002,
                        scoring_final_size_multiplier=1.0,
                        selection_outcome_code="rejected_portfolio",
                        portfolio_verdict_code="rejected_cluster",
                        risk_decision_severity="warning",
                    ),
                    collect_engine_metrics(
                        engine_id="engine_c",
                        emitted_signals=1,
                        net_edge_bps=3.0,
                        expected_cost_bps=2.5,
                        ce_expected=0.0001,
                        scoring_final_size_multiplier=0.05,
                        selection_outcome_code="rejected_ranking",
                        portfolio_verdict_code="compatible",
                        risk_decision_severity="critical",
                    ),
                    collect_engine_metrics(
                        engine_id="engine_d",
                        emitted_signals=1,
                        net_edge_bps=2.0,
                        expected_cost_bps=2.0,
                        ce_expected=0.0001,
                        scoring_final_size_multiplier=1.0,
                        selection_outcome_code="selected",
                        portfolio_verdict_code="compatible",
                        phantom_trade=True,
                        risk_decision_severity="nominal",
                    ),
                )
            }
        ),
        probe_pairs=("BTCUSDT",),
        requested_total_notional_usdt=20.0,
        requested_pair_notional_usdt=10.0,
        max_total_notional_usdt=25.0,
        max_pair_notional_usdt=12.5,
        observability_ready=True,
        halt_ready=True,
        onboarding_accepted=True,
    )

    summary = run_micro_live_gate(micro_input)

    assert summary.decision.allowed_to_probe is False
    assert summary.decision.verdict == MicroLiveVerdict.BLOCKED
    assert any(
        "shadow portfolio judgment=rewrite-required" in reason
        for reason in summary.decision.blocking_reasons
    )


def test_run_micro_live_gate_surfaces_shadow_portfolio_physics_pressure_reasons():
    micro_input = build_micro_live_input_from_shadow(
        _shadow_summary(),
        _shadow_payload(engine_judgment_cards=()).model_copy(
            update={
                "engines": (
                    collect_engine_metrics(
                        engine_id="engine_a",
                        emitted_signals=2,
                        net_edge_bps=12.0,
                        expected_cost_bps=4.0,
                        ce_expected=0.0007,
                        scoring_final_size_multiplier=1.0,
                        selection_outcome_code="selected",
                        portfolio_verdict_code="compatible",
                        risk_decision_severity="nominal",
                    ),
                    collect_engine_metrics(
                        engine_id="engine_b",
                        emitted_signals=1,
                        net_edge_bps=4.0,
                        expected_cost_bps=3.0,
                        ce_expected=0.0002,
                        scoring_final_size_multiplier=1.0,
                        selection_outcome_code="selected",
                        portfolio_verdict_code="compatible",
                        risk_decision_severity="nominal",
                        physics_pressure_state="elevated",
                        fragility_score=0.56,
                        toxicity_score=0.58,
                        execution_survivability_score=0.44,
                        micro_friction_score=0.57,
                    ),
                    collect_engine_metrics(
                        engine_id="engine_c",
                        emitted_signals=1,
                        net_edge_bps=3.0,
                        expected_cost_bps=2.5,
                        ce_expected=0.0001,
                        scoring_final_size_multiplier=1.0,
                        selection_outcome_code="selected",
                        portfolio_verdict_code="compatible",
                        risk_decision_severity="warning",
                        physics_pressure_state="critical",
                        fragility_score=0.81,
                        toxicity_score=0.79,
                        execution_survivability_score=0.18,
                        micro_friction_score=0.82,
                    ),
                    collect_engine_metrics(
                        engine_id="engine_d",
                        emitted_signals=1,
                        net_edge_bps=2.0,
                        expected_cost_bps=2.0,
                        ce_expected=0.0001,
                        scoring_final_size_multiplier=1.0,
                        selection_outcome_code="selected",
                        portfolio_verdict_code="compatible",
                        risk_decision_severity="nominal",
                    ),
                )
            }
        ),
        probe_pairs=("BTCUSDT",),
        requested_total_notional_usdt=20.0,
        requested_pair_notional_usdt=10.0,
        max_total_notional_usdt=25.0,
        max_pair_notional_usdt=12.5,
        observability_ready=True,
        halt_ready=True,
        onboarding_accepted=True,
    )

    summary = run_micro_live_gate(micro_input)

    assert summary.decision.allowed_to_probe is False
    assert summary.decision.verdict == MicroLiveVerdict.BLOCKED
    assert "shadow portfolio physics_pressure=elevated" in summary.decision.blocking_reasons
    assert "shadow portfolio elevated_physics_engines=1" in summary.decision.blocking_reasons
    assert "shadow portfolio critical_physics_engines=1" in summary.decision.blocking_reasons


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


def test_build_micro_live_input_from_shadow_rejects_non_complete_import_source_profile():
    with pytest.raises(
        MicroLiveInputError,
        match="replay import_source_profile=complete",
    ):
        build_micro_live_input_from_shadow(
            _shadow_summary(),
            _shadow_payload(source_profile="light"),
            probe_pairs=("BTCUSDT",),
            requested_total_notional_usdt=20.0,
            requested_pair_notional_usdt=10.0,
            max_total_notional_usdt=25.0,
            max_pair_notional_usdt=12.5,
            observability_ready=True,
            halt_ready=True,
            onboarding_accepted=True,
        )


def test_build_micro_live_input_from_shadow_rejects_non_local_import_origin():
    with pytest.raises(
        MicroLiveInputError,
        match="replay import_exported_from=local",
    ):
        build_micro_live_input_from_shadow(
            _shadow_summary(),
            _shadow_payload(exported_from="vps"),
            probe_pairs=("BTCUSDT",),
            requested_total_notional_usdt=20.0,
            requested_pair_notional_usdt=10.0,
            max_total_notional_usdt=25.0,
            max_pair_notional_usdt=12.5,
            observability_ready=True,
            halt_ready=True,
            onboarding_accepted=True,
        )


def test_build_micro_live_input_from_shadow_rejects_non_governed_import_review_state():
    with pytest.raises(
        MicroLiveInputError,
        match="replay import_review_state to stay pending or approved",
    ):
        build_micro_live_input_from_shadow(
            _shadow_summary(),
            _shadow_payload(review_state="needs_revision"),
            probe_pairs=("BTCUSDT",),
            requested_total_notional_usdt=20.0,
            requested_pair_notional_usdt=10.0,
            max_total_notional_usdt=25.0,
            max_pair_notional_usdt=12.5,
            observability_ready=True,
            halt_ready=True,
            onboarding_accepted=True,
        )


def test_build_micro_live_input_from_shadow_rejects_non_shadow_ready_import_state():
    with pytest.raises(
        MicroLiveInputError,
        match="replay import_activation_stage=shadow_ready",
    ):
        build_micro_live_input_from_shadow(
            _shadow_summary(),
            _shadow_payload(activation_stage="replay_only"),
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
        match="replay import_health_state=active",
    ):
        build_micro_live_input_from_shadow(
            _shadow_summary(),
            _shadow_payload(health_state="review_required"),
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
        match="replay import_feature_lineage_status=ok",
    ):
        build_micro_live_input_from_shadow(
            _shadow_summary(),
            _shadow_payload(
                feature_lineage_status="invalid",
                feature_lineage_reasons=("feature lineage missing",),
            ),
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
        match="replay import_transform_whitelist_status=ok",
    ):
        build_micro_live_input_from_shadow(
            _shadow_summary(),
            _shadow_payload(
                transform_whitelist_status="invalid",
                transform_whitelist_reasons=("transform whitelist missing",),
            ),
            probe_pairs=("BTCUSDT",),
            requested_total_notional_usdt=20.0,
            requested_pair_notional_usdt=10.0,
            max_total_notional_usdt=25.0,
            max_pair_notional_usdt=12.5,
            observability_ready=True,
            halt_ready=True,
            onboarding_accepted=True,
        )


def test_run_micro_live_gate_blocks_model_constructed_rejected_import_policy():
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
    summary = run_micro_live_gate(contradictory_input)

    assert summary.decision.verdict == MicroLiveVerdict.BLOCKED
    assert summary.decision.allowed_to_probe is False
    assert (
        "Build-12 Micro-live requires a non-rejected import_compatibility_status"
        in summary.decision.blocking_reasons
    )
    assert "import compatibility gate: schema mismatch" in summary.decision.blocking_reasons
    assert (
        "Build-12 Micro-live requires a non-rejected import_signature_check_status"
        in summary.decision.blocking_reasons
    )
    assert "import signature gate: revoked signing key" in summary.decision.blocking_reasons
    assert (
        "Build-12 Micro-live requires import_feature_lineage_required=True"
        in summary.decision.blocking_reasons
    )
    assert (
        "Build-12 Micro-live requires import_feature_lineage_status=ok"
        in summary.decision.blocking_reasons
    )
    assert (
        "import feature lineage gate: feature lineage missing"
        in summary.decision.blocking_reasons
    )
    assert (
        "Build-12 Micro-live requires import_transform_whitelist_required=True"
        in summary.decision.blocking_reasons
    )
    assert (
        "Build-12 Micro-live requires import_transform_whitelist_status=ok"
        in summary.decision.blocking_reasons
    )
    assert (
        "import transform whitelist gate: transform whitelist missing"
        in summary.decision.blocking_reasons
    )
    assert (
        "Build-12 Micro-live requires canonical import_conflict_resolution_mode"
        in summary.decision.blocking_reasons
    )
    assert (
        "Build-12 Micro-live requires canonical import_registry_atomicity_mode"
        in summary.decision.blocking_reasons
    )
    assert (
        "Build-12 Micro-live requires import_registry_publish_requires_atomic_replace=True"
        in summary.decision.blocking_reasons
    )
    assert (
        "Build-12 Micro-live requires import_payload_ref_count>=5"
        in summary.decision.blocking_reasons
    )
    assert (
        "Build-12 Micro-live requires import_payload_bundle_present=True"
        in summary.decision.blocking_reasons
    )
    assert (
        "Build-12 Micro-live requires import_review_export_ref"
        in summary.decision.blocking_reasons
    )


def test_run_micro_live_gate_blocks_model_constructed_non_complete_import_source_profile():
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
            "import_source_profile": "light",
        }
    )
    summary = run_micro_live_gate(contradictory_input)

    assert summary.decision.verdict == MicroLiveVerdict.BLOCKED
    assert summary.decision.allowed_to_probe is False
    assert (
        "Build-12 Micro-live requires import_source_profile=complete"
        in summary.decision.blocking_reasons
    )


def test_run_micro_live_gate_blocks_model_constructed_non_local_import_origin():
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
            "import_exported_from": "vps",
        }
    )
    summary = run_micro_live_gate(contradictory_input)

    assert summary.decision.verdict == MicroLiveVerdict.BLOCKED
    assert summary.decision.allowed_to_probe is False
    assert (
        "Build-12 Micro-live requires import_exported_from=local"
        in summary.decision.blocking_reasons
    )


def test_run_micro_live_gate_blocks_model_constructed_shadow_only_engine_scope():
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
            "active_engines": ("engine_b",),
            "shadow_promotable_engines": ("engine_a",),
            "shadow_shadow_only_engines": ("engine_b",),
            "shadow_rewrite_required_engines": ("engine_c",),
        }
    )
    summary = run_micro_live_gate(contradictory_input)

    assert summary.decision.verdict == MicroLiveVerdict.BLOCKED
    assert summary.decision.allowed_to_probe is False
    assert (
        "Build-12 Micro-live active_engines must be PROMOTABLE in Shadow judgment"
        in summary.decision.blocking_reasons
    )
    assert (
        "Build-12 Micro-live must not activate engines marked SHADOW_ONLY in Shadow judgment"
        in summary.decision.blocking_reasons
    )


def test_run_micro_live_gate_blocks_model_constructed_probe_surface_mismatch():
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
            "probe_pairs": ("DOGEUSDT",),
            "requested_total_notional_usdt": 40.0,
            "requested_pair_notional_usdt": 30.0,
            "max_total_notional_usdt": 25.0,
            "max_pair_notional_usdt": 12.5,
            "order_probe_limit": 0,
        }
    )
    summary = run_micro_live_gate(contradictory_input)

    assert summary.decision.verdict == MicroLiveVerdict.BLOCKED
    assert summary.decision.allowed_to_probe is False
    assert (
        "Build-12 Micro-live probe_pairs must stay within the Complete pair scope"
        in summary.decision.blocking_reasons
    )
    assert (
        "Micro-live requested_total_notional_usdt exceeds max budget"
        in summary.decision.blocking_reasons
    )
    assert (
        "Micro-live requested_pair_notional_usdt exceeds max pair budget"
        in summary.decision.blocking_reasons
    )
    assert (
        "Build-12 Micro-live requires order_probe_limit within [1, 10]"
        in summary.decision.blocking_reasons
    )


def test_run_micro_live_gate_blocks_model_constructed_shadow_temporal_mismatch():
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
            "shadow_days_completed": 29,
            "shadow_report_ready": False,
            "inter_engine_comparison_ready": False,
            "build14_contribution_ready": False,
        }
    )
    summary = run_micro_live_gate(contradictory_input)

    assert summary.decision.verdict == MicroLiveVerdict.BLOCKED
    assert summary.decision.allowed_to_probe is False
    assert (
        "Build-12 Micro-live requires a completed 30-day Shadow"
        in summary.decision.blocking_reasons
    )
    assert (
        "Build-12 Micro-live requires shadow_report_ready=True"
        in summary.decision.blocking_reasons
    )
    assert (
        "Build-12 Micro-live requires inter-engine A/B/C/D comparison evidence from Build-11"
        in summary.decision.blocking_reasons
    )
    assert (
        "Build-12 Micro-live requires Build-14 contribution evidence from Build-11"
        in summary.decision.blocking_reasons
    )


def test_run_micro_live_gate_blocks_model_constructed_governance_envelope_mismatch():
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
            "correlation_id": " ",
            "profile": ProfileId.LIGHT,
            "runtime_mode": RuntimeMode.SHADOW,
            "shadow_run_id": " ",
            "shadow_truth_set_ref": " ",
            "shadow_validation_set_ref": " ",
            "backtest_profile": "legacy",
            "creates_profile_fork": True,
            "automatic_live_promotion_requested": True,
            "shadow_required_days": 29,
            "shadow_import_artifact_id": "none",
            "shadow_import_lineage_version": "n/a",
            "import_artifact_id": "none",
            "import_lineage_version": "n/a",
            "operator_safing_request": OperatorSafingRequest(
                timestamp_ms=1_700_000_000_000,
                request_id="safing-bad-micro",
                action=OperatorSafingAction.DOWNGRADE_TO_SHADOW,
                source_runtime_mode=RuntimeMode.LIVE,
                target_runtime_mode=RuntimeMode.SHADOW,
                reason="mismatched source",
            ),
        }
    )
    summary = run_micro_live_gate(contradictory_input)

    assert summary.decision.verdict == MicroLiveVerdict.BLOCKED
    assert summary.decision.allowed_to_probe is False
    assert "Build-12 Micro-live requires a concrete correlation_id" in summary.decision.blocking_reasons
    assert "Build-12 Micro-live opens in COMPLETE profile only" in summary.decision.blocking_reasons
    assert "Build-12 Micro-live requires runtime_mode=MICRO_LIVE" in summary.decision.blocking_reasons
    assert "Build-12 Micro-live requires a concrete shadow_run_id" in summary.decision.blocking_reasons
    assert "Build-12 Micro-live requires a concrete shadow_truth_set_ref" in summary.decision.blocking_reasons
    assert (
        "Build-12 Micro-live requires a concrete shadow_validation_set_ref"
        in summary.decision.blocking_reasons
    )
    assert "BACKTEST_PROFILE is forbidden in the unified V5.3" in summary.decision.blocking_reasons
    assert "Local/VPS profile forks are forbidden" in summary.decision.blocking_reasons
    assert "Micro-live must not request automatic promotion to LIVE" in summary.decision.blocking_reasons
    assert "Build-12 Micro-live requires shadow_required_days=30" in summary.decision.blocking_reasons
    assert (
        "Build-12 Micro-live requires a concrete shadow_import_artifact_id"
        in summary.decision.blocking_reasons
    )
    assert (
        "Build-12 Micro-live requires a concrete shadow_import_lineage_version"
        in summary.decision.blocking_reasons
    )
    assert "Build-12 Micro-live requires a concrete import_artifact_id" in summary.decision.blocking_reasons
    assert "Build-12 Micro-live requires a concrete lineage_version" in summary.decision.blocking_reasons
    assert (
        "Build-12 Micro-live operator_safing_request must match source_runtime_mode=MICRO_LIVE"
        in summary.decision.blocking_reasons
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
