"""Minimal real Build-11 Shadow orchestration.

HARD STATEMENT §0.6: 30 consecutive shadow days required before promotion.
"""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

from interface_contracts import ProfileId, PromotionState, ReviewState, RuntimeMode
from local_replay_runtime import LocalReplayRuntimeEvidence
from monitoring import TechnicalDashboardPayload
from protocols.contracts import (
    ShadowComparison,
    ShadowComponentAssessment,
    ShadowEngineJudgment,
    ShadowEngineJudgmentSummary,
    ShadowPortfolioJudgment,
    ShadowDecision,
    ShadowInput,
    ShadowRuntimeEvidence,
    ShadowRunSummary,
    ShadowTruthSet,
    ShadowValidationSet,
)
from protocols.enums import (
    ShadowComponentKind,
    ShadowComponentVerdict,
    ShadowComparisonStatus,
    ShadowDivergenceSeverity,
    ShadowRunState,
    ShadowVerdict,
)
from protocols.errors import ShadowInputError


_REQUIRED_SHADOW_ENGINES = frozenset(
    {"engine_a", "engine_b", "engine_c", "engine_d"}
)
_REQUIRED_BUILD14_COMPONENTS = frozenset(
    {
        "build14_microstructure",
        "build14_regime",
        "build14_covariance",
        "build14_risk_contribution",
        "build14_edge_diversity",
    }
)
_RUNTIME_EVIDENCE_ACCEPTED_SOURCES = frozenset({"live_websocket", "recorded_replay"})


def _runtime_evidence_summary(
    *,
    runtime_data_source: str,
    runtime_feature_bridge_ready: bool,
    runtime_parity_diagnostics_ready: bool,
    runtime_replay_metrics_ready: bool,
    runtime_replay_dtr_ready: bool,
    runtime_event_loop_ready: bool,
    runtime_config_loaded: bool,
    runtime_shadow_dtr_persisted: bool,
    runtime_continuous_hours: float,
) -> str:
    return (
        f"source={runtime_data_source or 'unknown'} / "
        f"feature_bridge={'yes' if runtime_feature_bridge_ready else 'no'} / "
        f"parity={'yes' if runtime_parity_diagnostics_ready else 'no'} / "
        f"metrics={'yes' if runtime_replay_metrics_ready else 'no'} / "
        f"replay_dtr={'yes' if runtime_replay_dtr_ready else 'no'} / "
        f"event_loop={'yes' if runtime_event_loop_ready else 'no'} / "
        f"config={'yes' if runtime_config_loaded else 'no'} / "
        f"shadow_dtr={'yes' if runtime_shadow_dtr_persisted else 'no'} / "
        f"hours={runtime_continuous_hours:.1f}"
    )


def build_shadow_runtime_evidence(
    *,
    local_replay_evidence: LocalReplayRuntimeEvidence | None = None,
    runtime_data_source: str = "unknown",
    runtime_feature_bridge_ready: bool = False,
    runtime_parity_diagnostics_ready: bool = False,
    runtime_replay_metrics_ready: bool = False,
    runtime_replay_dtr_ready: bool = False,
    runtime_event_loop_ready: bool = False,
    runtime_config_loaded: bool = False,
    runtime_shadow_dtr_persisted: bool = False,
    runtime_continuous_hours: float = 0.0,
) -> ShadowRuntimeEvidence:
    """Combine replay-usefulness proof with Shadow runtime proof into one evidence object."""

    resolved_data_source = runtime_data_source
    if (
        resolved_data_source == "unknown"
        and local_replay_evidence is not None
        and local_replay_evidence.data_source != "unknown"
    ):
        resolved_data_source = local_replay_evidence.data_source

    feature_bridge_ready = (
        local_replay_evidence.feature_bridge_ready
        if local_replay_evidence is not None
        else runtime_feature_bridge_ready
    )
    parity_diagnostics_ready = (
        local_replay_evidence.parity_diagnostics_ready
        if local_replay_evidence is not None
        else runtime_parity_diagnostics_ready
    )
    replay_metrics_ready = (
        local_replay_evidence.replay_metrics_ready
        if local_replay_evidence is not None
        else runtime_replay_metrics_ready
    )
    replay_dtr_ready = (
        local_replay_evidence.replay_dtr_ready
        if local_replay_evidence is not None
        else runtime_replay_dtr_ready
    )

    return ShadowRuntimeEvidence(
        data_source=resolved_data_source,  # type: ignore[arg-type]
        feature_bridge_ready=feature_bridge_ready,
        parity_diagnostics_ready=parity_diagnostics_ready,
        replay_metrics_ready=replay_metrics_ready,
        replay_dtr_ready=replay_dtr_ready,
        event_loop_ready=runtime_event_loop_ready,
        config_loaded=runtime_config_loaded,
        shadow_dtr_persisted=runtime_shadow_dtr_persisted,
        continuous_hours=runtime_continuous_hours,
        evidence_summary=_runtime_evidence_summary(
            runtime_data_source=resolved_data_source,
            runtime_feature_bridge_ready=feature_bridge_ready,
            runtime_parity_diagnostics_ready=parity_diagnostics_ready,
            runtime_replay_metrics_ready=replay_metrics_ready,
            runtime_replay_dtr_ready=replay_dtr_ready,
            runtime_event_loop_ready=runtime_event_loop_ready,
            runtime_config_loaded=runtime_config_loaded,
            runtime_shadow_dtr_persisted=runtime_shadow_dtr_persisted,
            runtime_continuous_hours=runtime_continuous_hours,
        ),
    )


def _validate_shadow_payload_scope(
    payload: TechnicalDashboardPayload,
    *,
    role: str,
) -> None:
    if payload.profile != ProfileId.COMPLETE:
        raise ShadowInputError(
            f"Build-11 Shadow {role} payload must stay on profile=COMPLETE"
        )
    if payload.runtime_mode != RuntimeMode.SHADOW:
        raise ShadowInputError(
            f"Build-11 Shadow {role} payload must stay on runtime_mode=SHADOW"
        )


def _pressure_level(
    value: float | None,
    *,
    elevated_at: float,
    critical_at: float,
) -> str:
    if value is None:
        return "nominal"
    if value >= critical_at:
        return "critical"
    if value >= elevated_at:
        return "elevated"
    return "nominal"


def _engine_physics_pressure(payload_engine) -> str:
    if payload_engine is None:
        return "nominal"
    state = payload_engine.physics.physics_pressure_state.strip().lower()
    if state == "critical":
        return "critical"
    if state == "elevated":
        return "elevated"

    fragility_score = payload_engine.physics.fragility_score
    toxicity_score = payload_engine.physics.toxicity_score
    execution_survivability_score = payload_engine.physics.execution_survivability_score
    micro_friction_score = payload_engine.physics.micro_friction_score

    if (
        (fragility_score is not None and fragility_score >= 0.75)
        or (toxicity_score is not None and toxicity_score >= 0.75)
        or (
            execution_survivability_score is not None
            and execution_survivability_score <= 0.25
        )
        or (micro_friction_score is not None and micro_friction_score >= 0.75)
    ):
        return "critical"
    if (
        (fragility_score is not None and fragility_score >= 0.50)
        or (toxicity_score is not None and toxicity_score >= 0.50)
        or (
            execution_survivability_score is not None
            and execution_survivability_score <= 0.50
        )
        or (micro_friction_score is not None and micro_friction_score >= 0.50)
    ):
        return "elevated"
    return "nominal"


def _fallback_shadow_engine_verdicts(
    shadow_payload: TechnicalDashboardPayload | None,
) -> dict[str, str]:
    if shadow_payload is None:
        return {}

    verdicts: dict[str, str] = {}
    for engine in shadow_payload.engines:
        engine_id = engine.engine_id
        if engine_id not in _REQUIRED_SHADOW_ENGINES:
            continue
        if (
            engine.hard_blocked
            or engine.phantom_trade
            or engine.portfolio_verdict_code.startswith("rejected_")
            or engine.selection_outcome_code == "rejected_portfolio"
        ):
            verdicts[engine_id] = "rewrite-required"
        elif (
            engine.selection_outcome_code == "rejected_ranking"
            or engine.risk_decision_severity == "critical"
            or engine.scoring_final_size_multiplier <= 0.1
        ):
            verdicts[engine_id] = "shadow-only"
        else:
            verdicts[engine_id] = "promotable"
    return verdicts


def derive_shadow_portfolio_judgment(
    shadow_payload: TechnicalDashboardPayload | None = None,
    *,
    shadow_report: ShadowReportArtifact | None = None,
    judgments: tuple[ShadowEngineJudgment, ...] = (),
) -> ShadowPortfolioJudgment:
    """Derive a portfolio-level promotion judgment from governed Shadow surfaces."""

    payload_engines = (
        {
            engine.engine_id: engine
            for engine in shadow_payload.engines
            if engine.engine_id in _REQUIRED_SHADOW_ENGINES
        }
        if shadow_payload is not None
        else {}
    )
    judgment_verdicts = {
        judgment.engine_id: judgment.judgment_verdict
        for judgment in judgments
        if judgment.engine_id in _REQUIRED_SHADOW_ENGINES
    }
    if not judgment_verdicts and shadow_payload is not None:
        judgment_verdicts = {
            card.engine_id: card.judgment_verdict
            for card in shadow_payload.engine_judgment.cards
            if card.engine_id in _REQUIRED_SHADOW_ENGINES
        }
    if not judgment_verdicts:
        judgment_verdicts = _fallback_shadow_engine_verdicts(shadow_payload)
    if not judgment_verdicts and not payload_engines:
        return ShadowPortfolioJudgment(
            judgment_verdict="shadow-only",
            rationale="governed Shadow portfolio evidence is incomplete",
        )

    promotable_engine_count = sum(
        1 for verdict in judgment_verdicts.values() if verdict == "promotable"
    )
    shadow_only_engine_count = sum(
        1 for verdict in judgment_verdicts.values() if verdict == "shadow-only"
    )
    rewrite_required_engine_count = sum(
        1 for verdict in judgment_verdicts.values() if verdict == "rewrite-required"
    )
    dormant_engine_count = sum(
        1 for verdict in judgment_verdicts.values() if verdict == "dormant"
    )
    critical_physics_engine_count = sum(
        1
        for judgment in judgments
        if judgment.engine_id in _REQUIRED_SHADOW_ENGINES
        and judgment.physics_pressure_state == "critical"
    )
    elevated_physics_engine_count = sum(
        1
        for judgment in judgments
        if judgment.engine_id in _REQUIRED_SHADOW_ENGINES
        and judgment.physics_pressure_state == "elevated"
    )
    if not judgments and shadow_payload is not None:
        payload_physics_pressures = {
            engine_id: _engine_physics_pressure(engine)
            for engine_id, engine in payload_engines.items()
        }
        critical_physics_engine_count = sum(
            1 for pressure in payload_physics_pressures.values() if pressure == "critical"
        )
        elevated_physics_engine_count = sum(
            1 for pressure in payload_physics_pressures.values() if pressure == "elevated"
        )
    high_redundancy_engine_count = sum(
        1
        for judgment in judgments
        if judgment.engine_id in _REQUIRED_SHADOW_ENGINES
        and (
            judgment.conflict_rate >= 0.35
            or judgment.redundancy_score >= 0.35
        )
    )
    if not judgments and shadow_payload is not None:
        high_redundancy_engine_count = sum(
            1
            for card in shadow_payload.engine_judgment.cards
            if card.engine_id in _REQUIRED_SHADOW_ENGINES
            and (
                card.conflict_rate >= 0.35
                or card.redundancy_score >= 0.35
            )
        )
    portfolio_rejected_engine_count = sum(
        1
        for engine in payload_engines.values()
        if engine.portfolio_verdict_code.startswith("rejected_")
        or engine.selection_outcome_code == "rejected_portfolio"
    )
    cluster_rejected_engine_count = sum(
        1
        for engine in payload_engines.values()
        if engine.portfolio_verdict_code == "rejected_cluster"
    )
    beta_rejected_engine_count = sum(
        1
        for engine in payload_engines.values()
        if engine.portfolio_verdict_code == "rejected_beta"
    )
    exposure_rejected_engine_count = sum(
        1
        for engine in payload_engines.values()
        if engine.portfolio_verdict_code == "rejected_exposure"
    )
    loss_budget_rejected_engine_count = sum(
        1
        for engine in payload_engines.values()
        if engine.portfolio_verdict_code == "rejected_loss_budget"
    )
    ranking_rejected_engine_count = sum(
        1
        for engine in payload_engines.values()
        if engine.selection_outcome_code == "rejected_ranking"
    )
    dominant_cluster = (
        shadow_payload.portfolio.dominant_cluster
        if shadow_payload is not None and shadow_payload.portfolio.dominant_cluster
        else (shadow_report.dominant_cluster if shadow_report is not None else "")
    )
    beta_utilization = (
        shadow_payload.portfolio.beta_utilization
        if shadow_payload is not None
        else None
    )
    gross_capacity_used_pct = (
        shadow_payload.portfolio.gross_capacity_used_pct
        if shadow_payload is not None
        else None
    )
    loss_capacity_used_pct = (
        shadow_payload.portfolio.loss_capacity_used_pct
        if shadow_payload is not None
        else None
    )
    hard_block_rate = shadow_report.hard_block_rate if shadow_report is not None else None
    payload_phantom_trade_count = sum(
        1 for engine in payload_engines.values() if engine.phantom_trade
    )
    if shadow_report is not None and shadow_report.phantom_trade_count is not None:
        phantom_trade_count = max(
            shadow_report.phantom_trade_count,
            payload_phantom_trade_count,
        )
    else:
        phantom_trade_count = payload_phantom_trade_count

    redundancy_pressure = (
        "critical"
        if high_redundancy_engine_count >= 2
        else "elevated"
        if high_redundancy_engine_count >= 1
        else "nominal"
    )
    cluster_pressure = (
        "critical"
        if cluster_rejected_engine_count >= 2
        else "elevated"
        if cluster_rejected_engine_count >= 1
        or (dominant_cluster and high_redundancy_engine_count >= 1)
        else "nominal"
    )
    beta_pressure = (
        "critical"
        if beta_rejected_engine_count >= 2
        else "elevated"
        if beta_rejected_engine_count >= 1
        else _pressure_level(
            beta_utilization,
            elevated_at=0.75,
            critical_at=1.0,
        )
    )
    gross_capacity_pressure = (
        "critical"
        if exposure_rejected_engine_count >= 2
        else "elevated"
        if exposure_rejected_engine_count >= 1
        else _pressure_level(
            gross_capacity_used_pct,
            elevated_at=85.0,
            critical_at=100.0,
        )
    )
    loss_capacity_pressure = (
        "critical"
        if loss_budget_rejected_engine_count >= 2
        else "elevated"
        if loss_budget_rejected_engine_count >= 1
        else _pressure_level(
            loss_capacity_used_pct,
            elevated_at=85.0,
            critical_at=100.0,
        )
    )
    physics_pressure = (
        "critical"
        if critical_physics_engine_count >= 2
        else "elevated"
        if critical_physics_engine_count >= 1 or elevated_physics_engine_count >= 2
        else "nominal"
    )

    if hard_block_rate is not None and hard_block_rate >= 0.25:
        judgment_verdict = "rewrite-required"
        rationale = "Shadow portfolio hard-block rate stayed above the governed rewrite threshold"
    elif (
        rewrite_required_engine_count >= 2
        or portfolio_rejected_engine_count >= 2
        or phantom_trade_count >= 2
        or "critical" in {
            physics_pressure,
            redundancy_pressure,
            cluster_pressure,
            beta_pressure,
            gross_capacity_pressure,
            loss_capacity_pressure,
        }
    ):
        judgment_verdict = "rewrite-required"
        rationale = (
            "portfolio concentration, rejection load, or capital pressure remained too high for governed promotion"
        )
    elif (
        shadow_only_engine_count >= 1
        or portfolio_rejected_engine_count >= 1
        or ranking_rejected_engine_count >= 1
        or phantom_trade_count >= 1
        or "elevated" in {
            physics_pressure,
            redundancy_pressure,
            cluster_pressure,
            beta_pressure,
            gross_capacity_pressure,
            loss_capacity_pressure,
        }
    ):
        judgment_verdict = "shadow-only"
        rationale = (
            "portfolio-level pressure is still elevated, so Shadow must continue before governed promotion"
        )
    else:
        judgment_verdict = "promotable"
        rationale = "engine mix and portfolio pressure stayed within governed promotion bounds"

    return ShadowPortfolioJudgment(
        judgment_verdict=judgment_verdict,
        physics_pressure=physics_pressure,  # type: ignore[arg-type]
        redundancy_pressure=redundancy_pressure,  # type: ignore[arg-type]
        cluster_pressure=cluster_pressure,  # type: ignore[arg-type]
        beta_pressure=beta_pressure,  # type: ignore[arg-type]
        gross_capacity_pressure=gross_capacity_pressure,  # type: ignore[arg-type]
        loss_capacity_pressure=loss_capacity_pressure,  # type: ignore[arg-type]
        dominant_cluster=dominant_cluster,
        beta_utilization=beta_utilization,
        gross_capacity_used_pct=gross_capacity_used_pct,
        loss_capacity_used_pct=loss_capacity_used_pct,
        hard_block_rate=hard_block_rate,
        phantom_trade_count=phantom_trade_count,
        promotable_engine_count=promotable_engine_count,
        shadow_only_engine_count=shadow_only_engine_count,
        rewrite_required_engine_count=rewrite_required_engine_count,
        dormant_engine_count=dormant_engine_count,
        elevated_physics_engine_count=elevated_physics_engine_count,
        critical_physics_engine_count=critical_physics_engine_count,
        portfolio_rejected_engine_count=portfolio_rejected_engine_count,
        ranking_rejected_engine_count=ranking_rejected_engine_count,
        cluster_rejected_engine_count=cluster_rejected_engine_count,
        beta_rejected_engine_count=beta_rejected_engine_count,
        exposure_rejected_engine_count=exposure_rejected_engine_count,
        loss_budget_rejected_engine_count=loss_budget_rejected_engine_count,
        rationale=rationale,
    )


def build_shadow_input_from_payloads(
    baseline_payload: TechnicalDashboardPayload,
    candidate_payload: TechnicalDashboardPayload,
    *,
    truth_ref: str,
    validation_ref: str,
    component_assessments: tuple[ShadowComponentAssessment, ...],
    shadow_days_completed: int,
    shadow_report_ready: bool,
    inter_engine_comparison_ready: bool,
    build14_contribution_ready: bool,
    runtime_evidence: ShadowRuntimeEvidence | None = None,
    runtime_data_source: str = "unknown",
    runtime_feature_bridge_ready: bool = False,
    runtime_parity_diagnostics_ready: bool = False,
    runtime_replay_metrics_ready: bool = False,
    runtime_replay_dtr_ready: bool = False,
    runtime_event_loop_ready: bool = False,
    runtime_config_loaded: bool = False,
    runtime_shadow_dtr_persisted: bool = False,
    runtime_continuous_hours: float = 0.0,
    max_allowed_dtr_coverage_drop: float = 0.05,
    max_allowed_cra_increase: float = 0.10,
    max_allowed_break_even_drift_scope_increase: int = 0,
    max_allowed_edge_degraded_delta: int = 0,
    max_allowed_ce_net_drop: float = 0.0005,
    max_allowed_alert_count_increase: int = 1,
    max_allowed_queue_backlog_increase: int = 25,
) -> ShadowInput:
    """Build governed Shadow input from normalized Build-10 payloads."""

    _validate_shadow_payload_scope(baseline_payload, role="baseline")
    _validate_shadow_payload_scope(candidate_payload, role="candidate")

    truth_set = ShadowTruthSet(
        truth_ref=truth_ref,
        dtr_coverage=baseline_payload.build9_meta.dtr_coverage,
        cra_sterilization_rate=baseline_payload.build9_meta.cra_sterilization_rate,
        break_even_drift_scope_count=len(baseline_payload.build9_meta.break_even_drift_scopes),
        edge_degraded_count=baseline_payload.build9_meta.edge_degraded_count,
        ce_net=baseline_payload.portfolio.ce_net,
        active_alert_count=baseline_payload.alerts.active_alert_count,
        queue_backlog=baseline_payload.alerts.queue_backlog,
    )
    resolved_runtime_evidence = runtime_evidence or build_shadow_runtime_evidence(
        runtime_data_source=runtime_data_source,
        runtime_feature_bridge_ready=runtime_feature_bridge_ready,
        runtime_parity_diagnostics_ready=runtime_parity_diagnostics_ready,
        runtime_replay_metrics_ready=runtime_replay_metrics_ready,
        runtime_replay_dtr_ready=runtime_replay_dtr_ready,
        runtime_event_loop_ready=runtime_event_loop_ready,
        runtime_config_loaded=runtime_config_loaded,
        runtime_shadow_dtr_persisted=runtime_shadow_dtr_persisted,
        runtime_continuous_hours=runtime_continuous_hours,
    )
    validation_set = ShadowValidationSet(
        validation_ref=validation_ref,
        dtr_coverage=candidate_payload.build9_meta.dtr_coverage,
        cra_sterilization_rate=candidate_payload.build9_meta.cra_sterilization_rate,
        break_even_drift_scope_count=len(candidate_payload.build9_meta.break_even_drift_scopes),
        edge_degraded_count=candidate_payload.build9_meta.edge_degraded_count,
        ce_net=candidate_payload.portfolio.ce_net,
        active_alert_count=candidate_payload.alerts.active_alert_count,
        queue_backlog=candidate_payload.alerts.queue_backlog,
        accepted_import=candidate_payload.replay_import.validation_status == "accepted",
        import_validation_status=candidate_payload.replay_import.validation_status,
        import_artifact_id=candidate_payload.replay_import.artifact_id,
        import_exported_from=candidate_payload.replay_import.exported_from,
        import_lineage_version=candidate_payload.replay_import.lineage_version,
        import_source_profile=candidate_payload.replay_import.source_profile,
        import_review_state=candidate_payload.replay_import.review_state,
        import_rejection_reasons=candidate_payload.replay_import.rejection_reasons,
        import_dataset_ref=candidate_payload.replay_import.dataset_ref,
        import_clock_ref=candidate_payload.replay_import.clock_ref,
        import_activation_stage=candidate_payload.replay_import.activation_stage,
        import_health_state=candidate_payload.replay_import.health_state,
        import_compatibility_status=candidate_payload.replay_import.compatibility_status,
        import_compatibility_reasons=candidate_payload.replay_import.compatibility_reasons,
        import_feature_lineage_required=(
            candidate_payload.replay_import.feature_lineage_required
        ),
        import_feature_lineage_present=(
            candidate_payload.replay_import.feature_lineage_present
        ),
        import_feature_lineage_status=(
            candidate_payload.replay_import.feature_lineage_status
        ),
        import_feature_lineage_reasons=(
            candidate_payload.replay_import.feature_lineage_reasons
        ),
        import_transform_whitelist_required=(
            candidate_payload.replay_import.transform_whitelist_required
        ),
        import_transform_whitelist_present=(
            candidate_payload.replay_import.transform_whitelist_present
        ),
        import_transform_whitelist_status=(
            candidate_payload.replay_import.transform_whitelist_status
        ),
        import_transform_whitelist_reasons=(
            candidate_payload.replay_import.transform_whitelist_reasons
        ),
        import_signature_check_status=candidate_payload.replay_import.signature_check_status,
        import_signature_check_reasons=candidate_payload.replay_import.signature_check_reasons,
        import_conflict_resolution_mode=candidate_payload.replay_import.conflict_resolution_mode,
        import_conflict_hard_veto_action=candidate_payload.replay_import.conflict_hard_veto_action,
        import_conflict_score_aggregation_mode=(
            candidate_payload.replay_import.conflict_score_aggregation_mode
        ),
        import_conflict_size_reduce_mode=(
            candidate_payload.replay_import.conflict_size_reduce_mode
        ),
        import_conflict_rank_adjust_mode=(
            candidate_payload.replay_import.conflict_rank_adjust_mode
        ),
        import_conflict_additive_soft_boosts_allowed=(
            candidate_payload.replay_import.conflict_additive_soft_boosts_allowed
        ),
        import_conflict_additive_soft_reduces_allowed=(
            candidate_payload.replay_import.conflict_additive_soft_reduces_allowed
        ),
        import_registry_atomicity_mode=candidate_payload.replay_import.registry_atomicity_mode,
        import_registry_concurrency_model=(
            candidate_payload.replay_import.registry_concurrency_model
        ),
        import_registry_publish_requires_atomic_replace=(
            candidate_payload.replay_import.registry_publish_requires_atomic_replace
        ),
        import_registry_publish_requires_fsync=(
            candidate_payload.replay_import.registry_publish_requires_fsync
        ),
        import_registry_rollback_to_last_known_good=(
            candidate_payload.replay_import.registry_rollback_to_last_known_good
        ),
        import_payload_ref_count=candidate_payload.replay_import.payload_ref_count,
        import_payload_bundle_present=(
            candidate_payload.replay_import.payload_bundle_present
        ),
        import_review_export_ref=candidate_payload.replay_import.review_export_ref,
        import_feature_bridge_ref=candidate_payload.replay_import.feature_bridge_ref,
        import_parity_diagnostics_ref=(
            candidate_payload.replay_import.parity_diagnostics_ref
        ),
        import_replay_metrics_ref=candidate_payload.replay_import.replay_metrics_ref,
        import_replay_dtr_ref=candidate_payload.replay_import.replay_dtr_ref,
        runtime_data_source=resolved_runtime_evidence.data_source,
        runtime_feature_bridge_ready=resolved_runtime_evidence.feature_bridge_ready,
        runtime_parity_diagnostics_ready=resolved_runtime_evidence.parity_diagnostics_ready,
        runtime_replay_metrics_ready=resolved_runtime_evidence.replay_metrics_ready,
        runtime_replay_dtr_ready=resolved_runtime_evidence.replay_dtr_ready,
        runtime_event_loop_ready=resolved_runtime_evidence.event_loop_ready,
        runtime_config_loaded=resolved_runtime_evidence.config_loaded,
        runtime_shadow_dtr_persisted=resolved_runtime_evidence.shadow_dtr_persisted,
        runtime_continuous_hours=resolved_runtime_evidence.continuous_hours,
        runtime_evidence_summary=resolved_runtime_evidence.evidence_summary,
        build9x_diagnostics_count=candidate_payload.build9x.diagnostics_count,
        open_hypotheses=candidate_payload.build9x.open_hypotheses,
        replay_candidate_count=candidate_payload.build9x.replay_candidate_count,
        review_export_ready=candidate_payload.build9x.review_export_ready,
        active_engines=candidate_payload.system.active_engines,
        build14_status=candidate_payload.system.build14_status,
        shadow_days_completed=shadow_days_completed,
        shadow_required_days=30,
        shadow_report_ready=shadow_report_ready,
        inter_engine_comparison_ready=inter_engine_comparison_ready,
        build14_contribution_ready=build14_contribution_ready,
        component_assessments=component_assessments,
    )
    return ShadowInput(
        correlation_id=candidate_payload.correlation_id,
        profile=candidate_payload.profile,
        runtime_mode=candidate_payload.runtime_mode,
        truth_set=truth_set,
        validation_set=validation_set,
        max_allowed_dtr_coverage_drop=max_allowed_dtr_coverage_drop,
        max_allowed_cra_increase=max_allowed_cra_increase,
        max_allowed_break_even_drift_scope_increase=max_allowed_break_even_drift_scope_increase,
        max_allowed_edge_degraded_delta=max_allowed_edge_degraded_delta,
        max_allowed_ce_net_drop=max_allowed_ce_net_drop,
        max_allowed_alert_count_increase=max_allowed_alert_count_increase,
        max_allowed_queue_backlog_increase=max_allowed_queue_backlog_increase,
    )


def _missing_shadow_components(
    assessments: tuple[ShadowComponentAssessment, ...],
) -> tuple[str, ...]:
    seen_engines = {
        assessment.component_id
        for assessment in assessments
        if assessment.component_kind == ShadowComponentKind.ENGINE
    }
    seen_build14 = {
        assessment.component_id
        for assessment in assessments
        if assessment.component_kind == ShadowComponentKind.BUILD14_ENABLER
    }
    missing = sorted(
        (_REQUIRED_SHADOW_ENGINES - seen_engines)
        | (_REQUIRED_BUILD14_COMPONENTS - seen_build14)
    )
    return tuple(missing)


def derive_shadow_engine_judgment_summary(
    shadow_summary: ShadowRunSummary,
    shadow_report: ShadowReportArtifact | None,
    *,
    ce_by_engine: Mapping[str, float] | None = None,
    shadow_payload: TechnicalDashboardPayload | None = None,
) -> ShadowEngineJudgmentSummary:
    """Derive per-engine promotion judgments from the governed Shadow artifacts."""

    if shadow_report is None:
        return ShadowEngineJudgmentSummary(
            source_shadow_run_id=shadow_summary.run_id,
            source_shadow_days_completed=shadow_summary.shadow_days_completed,
            source_shadow_required_days=shadow_summary.shadow_required_days,
            judgments=(),
        )

    assessments = {
        assessment.component_id: assessment
        for assessment in shadow_summary.component_assessments
        if assessment.component_kind == ShadowComponentKind.ENGINE
    }
    reports = {
        report.engine_id: report
        for report in shadow_report.inter_engine_comparison
    }
    payload_engines = (
        {engine.engine_id: engine for engine in shadow_payload.engines}
        if shadow_payload is not None
        else {}
    )
    ce_expected_by_engine = dict(ce_by_engine or {})
    judgments: list[ShadowEngineJudgment] = []
    for engine_id in sorted(_REQUIRED_SHADOW_ENGINES):
        assessment = assessments.get(engine_id)
        report = reports.get(engine_id)
        payload_engine = payload_engines.get(engine_id)
        component_verdict = assessment.verdict.value if assessment is not None else "missing"
        ce_expected = ce_expected_by_engine.get(engine_id)
        if ce_expected is None and payload_engine is not None:
            ce_expected = payload_engine.ce_expected
        physics_pressure_state = _engine_physics_pressure(payload_engine)
        fragility_score = (
            payload_engine.physics.fragility_score if payload_engine is not None else None
        )
        toxicity_score = (
            payload_engine.physics.toxicity_score if payload_engine is not None else None
        )
        execution_survivability_score = (
            payload_engine.physics.execution_survivability_score
            if payload_engine is not None
            else None
        )
        micro_friction_score = (
            payload_engine.physics.micro_friction_score if payload_engine is not None else None
        )

        if assessment is not None and assessment.verdict == ShadowComponentVerdict.DORMANT:
            judgment_verdict = "dormant"
            rationale = "component marked dormant by the Shadow component verdicts"
        elif report is None or assessment is None:
            judgment_verdict = "shadow-only"
            rationale = "Shadow evidence is incomplete for this engine"
        elif (
            shadow_summary.shadow_days_completed < shadow_summary.shadow_required_days
            or not shadow_summary.shadow_report_ready
            or not shadow_report.is_complete
        ):
            judgment_verdict = "shadow-only"
            rationale = (
                f"Shadow gate incomplete: {shadow_summary.shadow_days_completed}/"
                f"{shadow_summary.shadow_required_days} day(s), report_complete={shadow_report.is_complete}"
            )
        elif payload_engine is not None and (
            payload_engine.hard_blocked
            or payload_engine.phantom_trade
            or payload_engine.portfolio_verdict_code.startswith("rejected_")
            or payload_engine.selection_outcome_code == "rejected_portfolio"
        ):
            judgment_verdict = "rewrite-required"
            rationale = (
                "risk, phantom-trade, or portfolio compatibility rejected this engine in the governed payload"
            )
        elif physics_pressure_state == "critical":
            judgment_verdict = "rewrite-required"
            rationale = (
                "execution fragility, toxicity, survivability, or micro-friction stayed above the governed rewrite threshold"
            )
        elif physics_pressure_state == "elevated":
            judgment_verdict = "shadow-only"
            rationale = (
                "execution physics pressure remained elevated, so Shadow must continue before governed promotion"
            )
        elif payload_engine is not None and (
            payload_engine.selection_outcome_code == "rejected_ranking"
            or payload_engine.risk_decision_severity == "critical"
            or payload_engine.scoring_final_size_multiplier <= 0.1
        ):
            judgment_verdict = "shadow-only"
            rationale = (
                "engine remained selection-limited or size-capped in the governed payload"
            )
        elif (
            report.economic_pass_rate <= 0.5
            or report.marginal_edge <= 0.0
            or report.conflict_rate >= 0.5
            or (ce_expected is not None and ce_expected <= 0.0)
        ):
            judgment_verdict = "rewrite-required"
            rationale = (
                "economic pass-rate, CE, marginal edge, or conflict-rate stayed below the supervised threshold"
            )
        else:
            judgment_verdict = "promotable"
            rationale = "Shadow gate complete with positive supervised engine metrics"

        judgments.append(
            ShadowEngineJudgment(
                engine_id=engine_id,
                component_verdict=component_verdict,
                judgment_verdict=judgment_verdict,
                useful_frequency=report.useful_frequency if report is not None else 0.0,
                ce_expected=ce_expected,
                estimated_cost_bps=report.estimated_cost_bps if report is not None else 0.0,
                edge_net=report.edge_net if report is not None else 0.0,
                economic_pass_rate=report.economic_pass_rate if report is not None else 0.0,
                conflict_rate=report.conflict_rate if report is not None else 0.0,
                marginal_edge=report.marginal_edge if report is not None else 0.0,
                redundancy_score=report.conflict_rate if report is not None else 0.0,
                portfolio_contribution=report.marginal_edge if report is not None else 0.0,
                final_size_multiplier=(
                    payload_engine.scoring_final_size_multiplier
                    if payload_engine is not None
                    else None
                ),
                selection_outcome_code=(
                    payload_engine.selection_outcome_code if payload_engine is not None else ""
                ),
                portfolio_verdict_code=(
                    payload_engine.portfolio_verdict_code if payload_engine is not None else ""
                ),
                phantom_trade=payload_engine.phantom_trade if payload_engine is not None else False,
                hard_blocked=payload_engine.hard_blocked if payload_engine is not None else False,
                risk_decision_severity=(
                    payload_engine.risk_decision_severity if payload_engine is not None else ""
                ),
                physics_pressure_state=physics_pressure_state,  # type: ignore[arg-type]
                fragility_score=fragility_score,
                toxicity_score=toxicity_score,
                execution_survivability_score=execution_survivability_score,
                micro_friction_score=micro_friction_score,
                observations=report.observations if report is not None else 0,
                rationale=rationale,
                evidence_summary=assessment.evidence_summary if assessment is not None else "",
            )
        )

    return ShadowEngineJudgmentSummary(
        source_report_id=shadow_report.report_id,
        source_shadow_run_id=shadow_summary.run_id,
        source_shadow_days_completed=shadow_summary.shadow_days_completed,
        source_shadow_required_days=shadow_summary.shadow_required_days,
        portfolio_judgment=derive_shadow_portfolio_judgment(
            shadow_payload,
            shadow_report=shadow_report,
            judgments=tuple(judgments),
        ),
        judgments=tuple(judgments),
    )


def _comparison(
    shadow_input: ShadowInput,
    *,
    metric_name: str,
    baseline_value: float,
    candidate_value: float,
    threshold: float,
    higher_is_better: bool,
) -> ShadowComparison:
    if higher_is_better:
        delta = max(0.0, baseline_value - candidate_value)
    else:
        delta = max(0.0, candidate_value - baseline_value)

    if delta == 0.0:
        status = ShadowComparisonStatus.MATCHING
        severity = ShadowDivergenceSeverity.INFO
        blocking = False
        summary = f"{metric_name} matched or improved the baseline"
    elif delta <= threshold:
        status = ShadowComparisonStatus.DIVERGENT
        severity = ShadowDivergenceSeverity.WARNING
        blocking = False
        summary = f"{metric_name} diverged within the allowed Shadow threshold"
    else:
        status = ShadowComparisonStatus.BLOCKING
        severity = ShadowDivergenceSeverity.CRITICAL
        blocking = True
        summary = f"{metric_name} exceeded the allowed Shadow threshold"

    return ShadowComparison(
        comparison_id=f"{shadow_input.correlation_id}:{metric_name}",
        metric_name=metric_name,
        baseline_value=baseline_value,
        candidate_value=candidate_value,
        delta=round(delta, 6),
        threshold=threshold,
        status=status,
        severity=severity,
        blocking=blocking,
        summary=summary,
    )


def compare_shadow_candidate(shadow_input: ShadowInput) -> tuple[ShadowComparison, ...]:
    """Compare candidate Shadow measurements against the baseline truth set."""

    truth = shadow_input.truth_set
    validation = shadow_input.validation_set
    return (
        _comparison(
            shadow_input,
            metric_name="dtr_coverage_drop",
            baseline_value=truth.dtr_coverage,
            candidate_value=validation.dtr_coverage,
            threshold=shadow_input.max_allowed_dtr_coverage_drop,
            higher_is_better=True,
        ),
        _comparison(
            shadow_input,
            metric_name="cra_sterilization_increase",
            baseline_value=truth.cra_sterilization_rate,
            candidate_value=validation.cra_sterilization_rate,
            threshold=shadow_input.max_allowed_cra_increase,
            higher_is_better=False,
        ),
        _comparison(
            shadow_input,
            metric_name="break_even_drift_scope_increase",
            baseline_value=float(truth.break_even_drift_scope_count),
            candidate_value=float(validation.break_even_drift_scope_count),
            threshold=float(shadow_input.max_allowed_break_even_drift_scope_increase),
            higher_is_better=False,
        ),
        _comparison(
            shadow_input,
            metric_name="edge_degraded_delta",
            baseline_value=float(truth.edge_degraded_count),
            candidate_value=float(validation.edge_degraded_count),
            threshold=float(shadow_input.max_allowed_edge_degraded_delta),
            higher_is_better=False,
        ),
        _comparison(
            shadow_input,
            metric_name="ce_net_drop",
            baseline_value=truth.ce_net,
            candidate_value=validation.ce_net,
            threshold=shadow_input.max_allowed_ce_net_drop,
            higher_is_better=True,
        ),
        _comparison(
            shadow_input,
            metric_name="active_alert_count_increase",
            baseline_value=float(truth.active_alert_count),
            candidate_value=float(validation.active_alert_count),
            threshold=float(shadow_input.max_allowed_alert_count_increase),
            higher_is_better=False,
        ),
        _comparison(
            shadow_input,
            metric_name="queue_backlog_increase",
            baseline_value=float(truth.queue_backlog),
            candidate_value=float(validation.queue_backlog),
            threshold=float(shadow_input.max_allowed_queue_backlog_increase),
            higher_is_better=False,
        ),
    )


def run_shadow_validation(
    shadow_input: ShadowInput,
    *,
    run_id: str | None = None,
) -> ShadowRunSummary:
    """Run the minimal real Build-11 Shadow gating logic."""

    comparisons = compare_shadow_candidate(shadow_input)
    validation = shadow_input.validation_set
    blocking_reasons: list[str] = []
    structurally_blocked = False
    normalized_validation_status = validation.import_validation_status.strip().casefold()
    missing_engines = tuple(
        sorted(_REQUIRED_SHADOW_ENGINES - set(validation.active_engines))
    )
    missing_components = _missing_shadow_components(validation.component_assessments)
    normalized_build14_status = validation.build14_status.strip().casefold()
    runtime_evidence_ready = (
        validation.runtime_data_source in _RUNTIME_EVIDENCE_ACCEPTED_SOURCES
        and validation.runtime_feature_bridge_ready
        and validation.runtime_parity_diagnostics_ready
        and validation.runtime_replay_metrics_ready
        and validation.runtime_replay_dtr_ready
        and validation.runtime_event_loop_ready
        and validation.runtime_config_loaded
        and validation.runtime_shadow_dtr_persisted
        and validation.runtime_continuous_hours >= 24.0
    )

    if not validation.accepted_import:
        structurally_blocked = True
        blocking_reasons.append("candidate import must be accepted before Shadow")
    if normalized_validation_status != "accepted":
        structurally_blocked = True
        blocking_reasons.append(
            "candidate import_validation_status must be an accepted status before Shadow"
        )
    if not validation.import_artifact_id or validation.import_artifact_id == "none":
        structurally_blocked = True
        blocking_reasons.append("candidate import artifact_id is required")
    if validation.import_exported_from != "local":
        structurally_blocked = True
        blocking_reasons.append(
            "candidate import exported_from must be local before Shadow"
        )
    if not validation.import_lineage_version or validation.import_lineage_version == "n/a":
        structurally_blocked = True
        blocking_reasons.append("candidate lineage_version is required")
    if validation.import_source_profile != "complete":
        structurally_blocked = True
        blocking_reasons.append(
            "candidate import source_profile must be complete before Shadow"
        )
    if validation.import_review_state not in {"pending", "approved"}:
        structurally_blocked = True
        blocking_reasons.append(
            "candidate import review_state must stay pending or approved before Shadow"
        )
    if not validation.import_dataset_ref:
        structurally_blocked = True
        blocking_reasons.append("candidate import dataset_ref is required before Shadow")
    if not validation.import_clock_ref:
        structurally_blocked = True
        blocking_reasons.append("candidate import clock_ref is required before Shadow")
    if validation.import_activation_stage != "shadow_ready":
        structurally_blocked = True
        blocking_reasons.append(
            "candidate import activation_stage must be shadow_ready before Shadow"
        )
    if validation.import_health_state != "active":
        structurally_blocked = True
        blocking_reasons.append(
            "candidate import health_state must be active before Shadow"
        )
    if validation.import_rejection_reasons:
        structurally_blocked = True
    blocking_reasons.extend(
        f"import gate: {reason}" for reason in validation.import_rejection_reasons
    )
    if validation.import_compatibility_status == "rejected":
        structurally_blocked = True
        blocking_reasons.append(
            "candidate import compatibility policy rejected the artifact before Shadow"
        )
    blocking_reasons.extend(
        f"import compatibility gate: {reason}"
        for reason in validation.import_compatibility_reasons
    )
    if not validation.import_feature_lineage_required:
        structurally_blocked = True
        blocking_reasons.append(
            "candidate import must require feature_lineage_lock before Shadow"
        )
    if not validation.import_feature_lineage_present:
        structurally_blocked = True
        blocking_reasons.append(
            "candidate import must keep feature_lineage_lock present before Shadow"
        )
    if validation.import_feature_lineage_status != "ok":
        structurally_blocked = True
        blocking_reasons.append(
            "candidate import feature_lineage_lock must be valid before Shadow"
        )
    blocking_reasons.extend(
        f"import feature lineage gate: {reason}"
        for reason in validation.import_feature_lineage_reasons
    )
    if not validation.import_transform_whitelist_required:
        structurally_blocked = True
        blocking_reasons.append(
            "candidate import must require transform_whitelist_lock before Shadow"
        )
    if not validation.import_transform_whitelist_present:
        structurally_blocked = True
        blocking_reasons.append(
            "candidate import must keep transform_whitelist_lock present before Shadow"
        )
    if validation.import_transform_whitelist_status != "ok":
        structurally_blocked = True
        blocking_reasons.append(
            "candidate import transform_whitelist_lock must be valid before Shadow"
        )
    blocking_reasons.extend(
        f"import transform whitelist gate: {reason}"
        for reason in validation.import_transform_whitelist_reasons
    )
    if validation.import_signature_check_status in {
        "trust_store_unavailable",
        "key_id_unknown",
        "key_revoked",
        "payload_hash_mismatch",
    }:
        structurally_blocked = True
        blocking_reasons.append(
            "candidate import signature policy rejected the artifact before Shadow"
        )
    blocking_reasons.extend(
        f"import signature gate: {reason}"
        for reason in validation.import_signature_check_reasons
    )
    if validation.import_conflict_resolution_mode != "no_trade_then_strictest":
        structurally_blocked = True
        blocking_reasons.append(
            "candidate import conflict policy must keep resolution_mode=no_trade_then_strictest before Shadow"
        )
    if validation.import_conflict_hard_veto_action != "no_trade":
        structurally_blocked = True
        blocking_reasons.append(
            "candidate import conflict policy must keep hard_veto_action=no_trade before Shadow"
        )
    if validation.import_conflict_score_aggregation_mode != "bounded_sum_with_global_cap":
        structurally_blocked = True
        blocking_reasons.append(
            "candidate import conflict policy must keep score_aggregation_mode=bounded_sum_with_global_cap before Shadow"
        )
    if validation.import_conflict_size_reduce_mode != "min_factor_wins":
        structurally_blocked = True
        blocking_reasons.append(
            "candidate import conflict policy must keep size_reduce_mode=min_factor_wins before Shadow"
        )
    if validation.import_conflict_rank_adjust_mode != "bounded_sum":
        structurally_blocked = True
        blocking_reasons.append(
            "candidate import conflict policy must keep rank_adjust_mode=bounded_sum before Shadow"
        )
    if not validation.import_conflict_additive_soft_boosts_allowed:
        structurally_blocked = True
        blocking_reasons.append(
            "candidate import conflict policy must keep additive_soft_boosts_allowed=True before Shadow"
        )
    if not validation.import_conflict_additive_soft_reduces_allowed:
        structurally_blocked = True
        blocking_reasons.append(
            "candidate import conflict policy must keep additive_soft_reduces_allowed=True before Shadow"
        )
    if validation.import_registry_atomicity_mode != "atomic_snapshot_swap":
        structurally_blocked = True
        blocking_reasons.append(
            "candidate import registry policy must keep atomicity_mode=atomic_snapshot_swap before Shadow"
        )
    if validation.import_registry_concurrency_model != "single_writer_multi_reader":
        structurally_blocked = True
        blocking_reasons.append(
            "candidate import registry policy must keep concurrency_model=single_writer_multi_reader before Shadow"
        )
    if not validation.import_registry_publish_requires_atomic_replace:
        structurally_blocked = True
        blocking_reasons.append(
            "candidate import registry policy must require atomic replace before Shadow"
        )
    if not validation.import_registry_publish_requires_fsync:
        structurally_blocked = True
        blocking_reasons.append(
            "candidate import registry policy must require fsync before Shadow"
        )
    if not validation.import_registry_rollback_to_last_known_good:
        structurally_blocked = True
        blocking_reasons.append(
            "candidate import registry policy must keep rollback_to_last_known_good=True before Shadow"
        )
    if validation.import_payload_ref_count < 5:
        structurally_blocked = True
        blocking_reasons.append(
            "candidate import must keep payload_ref_count>=5 before Shadow"
        )
    if not validation.import_payload_bundle_present:
        structurally_blocked = True
        blocking_reasons.append(
            "candidate import must keep payload_bundle_present=True before Shadow"
        )
    if not validation.import_review_export_ref:
        structurally_blocked = True
        blocking_reasons.append(
            "candidate import must keep review_export_ref before Shadow"
        )
    if not validation.import_feature_bridge_ref:
        structurally_blocked = True
        blocking_reasons.append(
            "candidate import must keep feature_bridge_ref before Shadow"
        )
    if not validation.import_parity_diagnostics_ref:
        structurally_blocked = True
        blocking_reasons.append(
            "candidate import must keep parity_diagnostics_ref before Shadow"
        )
    if not validation.import_replay_metrics_ref:
        structurally_blocked = True
        blocking_reasons.append(
            "candidate import must keep replay_metrics_ref before Shadow"
        )
    if not validation.import_replay_dtr_ref:
        structurally_blocked = True
        blocking_reasons.append(
            "candidate import must keep replay_dtr_ref before Shadow"
        )
    if validation.runtime_data_source not in _RUNTIME_EVIDENCE_ACCEPTED_SOURCES:
        structurally_blocked = True
        blocking_reasons.append(
            "Build-11 Shadow requires runtime evidence from live_websocket or recorded_replay"
        )
    if not validation.runtime_feature_bridge_ready:
        structurally_blocked = True
        blocking_reasons.append(
            "Build-11 Shadow requires feature bridge evidence (prices -> features -> engines)"
        )
    if not validation.runtime_parity_diagnostics_ready:
        structurally_blocked = True
        blocking_reasons.append(
            "Build-11 Shadow requires parity diagnostics evidence"
        )
    if not validation.runtime_replay_metrics_ready:
        structurally_blocked = True
        blocking_reasons.append(
            "Build-11 Shadow requires replay metrics evidence"
        )
    if not validation.runtime_replay_dtr_ready:
        structurally_blocked = True
        blocking_reasons.append(
            "Build-11 Shadow requires replay DTR evidence"
        )
    if not validation.runtime_event_loop_ready:
        structurally_blocked = True
        blocking_reasons.append(
            "Build-11 Shadow requires event loop evidence"
        )
    if not validation.runtime_config_loaded:
        structurally_blocked = True
        blocking_reasons.append(
            "Build-11 Shadow requires official config loading evidence"
        )
    if not validation.runtime_shadow_dtr_persisted:
        structurally_blocked = True
        blocking_reasons.append(
            "Build-11 Shadow requires persisted shadow DTR evidence"
        )
    if validation.runtime_continuous_hours < 24.0:
        structurally_blocked = True
        blocking_reasons.append(
            "Build-11 Shadow requires at least 24h of real runtime evidence before the verdict gate"
        )
    if validation.shadow_days_completed < validation.shadow_required_days:
        structurally_blocked = True
        blocking_reasons.append(
            "Build-11 Shadow requires 30 consecutive days before the verdict gate"
        )
    if not validation.shadow_report_ready:
        structurally_blocked = True
        blocking_reasons.append(
            "Build-11 Shadow requires a complete shadow report before the verdict gate"
        )
    if not validation.inter_engine_comparison_ready:
        structurally_blocked = True
        blocking_reasons.append(
            "Build-11 Shadow requires an inter-engine A/B/C/D comparison in the report"
        )
    if not validation.build14_contribution_ready:
        structurally_blocked = True
        blocking_reasons.append(
            "Build-11 Shadow requires Build-14 contribution evidence in the report"
        )
    if missing_engines:
        structurally_blocked = True
        blocking_reasons.append(
            "Build-11 Shadow requires A/B/C/D active in Shadow: "
            + ", ".join(missing_engines)
        )
    if normalized_build14_status == "planned":
        structurally_blocked = True
        blocking_reasons.append(
            "Build-11 Shadow requires Build-14 to be active, not planned"
        )
    if missing_components:
        structurally_blocked = True
        blocking_reasons.append(
            "Build-11 Shadow requires component verdicts for A/B/C/D and all Build-14 enablers: "
            + ", ".join(missing_components)
        )

    blocking_reasons.extend(
        comparison.summary for comparison in comparisons if comparison.blocking
    )

    manual_review_required = (
        validation.build9x_diagnostics_count > 0
        or validation.open_hypotheses > 0
        or validation.replay_candidate_count > 0
    )

    if structurally_blocked:
        decision = ShadowDecision(
            accepted=False,
            verdict=ShadowVerdict.BLOCKED,
            normalized_promotion_state=PromotionState.REPLAY_ONLY,
            review_state=ReviewState.NEEDS_REVISION,
            blocking_reasons=tuple(blocking_reasons),
            manual_review_required=True,
        )
        run_state = ShadowRunState.BLOCKED
    elif any(comparison.blocking for comparison in comparisons):
        decision = ShadowDecision(
            accepted=False,
            verdict=ShadowVerdict.REJECTED,
            normalized_promotion_state=PromotionState.REPLAY_ONLY,
            review_state=ReviewState.NEEDS_REVISION,
            blocking_reasons=tuple(blocking_reasons),
            manual_review_required=True,
        )
        run_state = ShadowRunState.COMPLETED
    elif manual_review_required and not validation.review_export_ready:
        decision = ShadowDecision(
            accepted=False,
            verdict=ShadowVerdict.NEEDS_REVIEW,
            normalized_promotion_state=PromotionState.REPLAY_ONLY,
            review_state=ReviewState.NEEDS_REVISION,
            blocking_reasons=("Build-9X review export must be ready before accepting Shadow",),
            manual_review_required=True,
        )
        run_state = ShadowRunState.COMPLETED
    else:
        decision = ShadowDecision(
            accepted=True,
            verdict=ShadowVerdict.ACCEPTED,
            normalized_promotion_state=PromotionState.SHADOW_CANDIDATE,
            review_state=ReviewState.PENDING,
            blocking_reasons=(),
            manual_review_required=manual_review_required,
        )
        run_state = ShadowRunState.COMPLETED

    return ShadowRunSummary(
        run_id=run_id or f"{shadow_input.correlation_id}:shadow_run",
        correlation_id=shadow_input.correlation_id,
        run_state=run_state,
        truth_set_ref=shadow_input.truth_set.truth_ref,
        validation_set_ref=shadow_input.validation_set.validation_ref,
        comparisons=comparisons,
        decision=decision,
        import_artifact_id=validation.import_artifact_id,
        import_lineage_version=validation.import_lineage_version,
        runtime_data_source=validation.runtime_data_source,
        runtime_feature_bridge_ready=validation.runtime_feature_bridge_ready,
        runtime_parity_diagnostics_ready=validation.runtime_parity_diagnostics_ready,
        runtime_replay_metrics_ready=validation.runtime_replay_metrics_ready,
        runtime_replay_dtr_ready=validation.runtime_replay_dtr_ready,
        runtime_event_loop_ready=validation.runtime_event_loop_ready,
        runtime_config_loaded=validation.runtime_config_loaded,
        runtime_shadow_dtr_persisted=validation.runtime_shadow_dtr_persisted,
        runtime_continuous_hours=validation.runtime_continuous_hours,
        runtime_evidence_ready=runtime_evidence_ready,
        runtime_evidence_summary=validation.runtime_evidence_summary,
        build9x_diagnostics_count=validation.build9x_diagnostics_count,
        open_hypotheses=validation.open_hypotheses,
        replay_candidate_count=validation.replay_candidate_count,
        review_export_ready=validation.review_export_ready,
        active_engines=validation.active_engines,
        build14_status=validation.build14_status,
        shadow_days_completed=validation.shadow_days_completed,
        shadow_required_days=validation.shadow_required_days,
        shadow_report_ready=validation.shadow_report_ready,
        inter_engine_comparison_ready=validation.inter_engine_comparison_ready,
        build14_contribution_ready=validation.build14_contribution_ready,
        component_assessments=validation.component_assessments,
    )


def check_shadow_30j_gate(
    state_dir: Path,
    profile: str,
) -> tuple[bool, dict]:
    """HARD STATEMENT §0.6: check if 30 consecutive shadow days are met.

    Args:
        state_dir: Directory containing persisted shadow counter state.
        profile: "light" or "complete".

    Returns:
        (gate_passed, report_dict)
    """
    from protocols.shadow_day_counter import ShadowDayCounter, ShadowProfile

    shadow_profile = ShadowProfile(profile)
    counter = ShadowDayCounter(state_dir=state_dir, profile=shadow_profile)
    report = counter.generate_report()
    gate_passed = counter.is_promotion_ready() and bool(
        report.get("shadow_report_ready", False)
    )
    return gate_passed, report


__all__ = [
    "build_shadow_runtime_evidence",
    "build_shadow_input_from_payloads",
    "derive_shadow_portfolio_judgment",
    "derive_shadow_engine_judgment_summary",
    "compare_shadow_candidate",
    "run_shadow_validation",
    "check_shadow_30j_gate",
]
