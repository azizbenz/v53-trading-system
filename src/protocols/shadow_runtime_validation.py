"""Validation and governance helpers for the governed Shadow runtime."""

from __future__ import annotations

from interface_contracts import PromotionState, ReviewState
from protocols.contracts import (
    DailyPnlBreakerGovernanceSummary,
    InfoStressGovernanceSummary,
    RegimeLiteGovernanceSummary,
    ShadowComparison,
    ShadowComponentAssessment,
    ShadowDecision,
    ShadowInput,
    ShadowRunSummary,
    ShadowValidationSet,
)
from protocols.enums import ShadowComponentKind, ShadowRunState, ShadowVerdict
from protocols.shadow_runtime_judgments import compare_shadow_candidate
from protocols.shadow_runtime_shared import (
    _REQUIRED_BUILD14_COMPONENTS,
    _REQUIRED_SHADOW_ENGINES,
    _RUNTIME_EVIDENCE_ACCEPTED_SOURCES,
)
from regime_classifier import RegimeLiteAssessment
from risk_backbone import InfoStressAssessment, RegimeLiteSafingRecommendation
from risk_backbone.loss_budgeter import DailyPnlBreakerAssessment


def _build_regime_lite_governance_summary(
    *,
    regime_lite_assessment: RegimeLiteAssessment | None,
    regime_lite_safing_recommendation: RegimeLiteSafingRecommendation | None,
) -> RegimeLiteGovernanceSummary:
    if regime_lite_assessment is None and regime_lite_safing_recommendation is None:
        return RegimeLiteGovernanceSummary()

    if regime_lite_assessment is not None and regime_lite_safing_recommendation is not None:
        status = "ready"
    elif regime_lite_assessment is not None:
        status = "assessment_only"
    else:
        status = "recommendation_only"

    assessment_reason_codes = (
        regime_lite_assessment.reason_codes if regime_lite_assessment is not None else ()
    )
    safing_reason_codes = (
        regime_lite_safing_recommendation.reason_codes
        if regime_lite_safing_recommendation is not None
        else ()
    )
    operator_safing_request = (
        regime_lite_safing_recommendation.operator_safing_request
        if regime_lite_safing_recommendation is not None
        else None
    )
    return RegimeLiteGovernanceSummary(
        status=status,
        state=(
            regime_lite_assessment.state.value
            if regime_lite_assessment is not None
            else "not_configured"
        ),
        candidate_state=(
            regime_lite_assessment.candidate_state.value
            if regime_lite_assessment is not None
            else "not_configured"
        ),
        state_changed=(
            regime_lite_assessment.state_changed
            if regime_lite_assessment is not None
            else False
        ),
        entries_blocked=(
            regime_lite_assessment.entries_blocked
            if regime_lite_assessment is not None
            else False
        ),
        sudden_event=(
            regime_lite_assessment.sudden_event
            if regime_lite_assessment is not None
            else False
        ),
        safing_severity=(
            regime_lite_safing_recommendation.severity.value
            if regime_lite_safing_recommendation is not None
            else "not_configured"
        ),
        should_block_new_entries=(
            regime_lite_safing_recommendation.should_block_new_entries
            if regime_lite_safing_recommendation is not None
            else (
                regime_lite_assessment.entries_blocked
                if regime_lite_assessment is not None
                else False
            )
        ),
        should_exit_all=(
            regime_lite_safing_recommendation.should_exit_all
            if regime_lite_safing_recommendation is not None
            else False
        ),
        recommended_operator_action=(
            regime_lite_safing_recommendation.recommended_operator_action.value
            if (
                regime_lite_safing_recommendation is not None
                and regime_lite_safing_recommendation.recommended_operator_action is not None
            )
            else ""
        ),
        operator_safing_request_action=(
            operator_safing_request.action.value
            if operator_safing_request is not None
            else ""
        ),
        operator_safing_request_source_runtime_mode=(
            operator_safing_request.source_runtime_mode.value
            if operator_safing_request is not None
            else ""
        ),
        reason_codes=tuple(
            dict.fromkeys(assessment_reason_codes + safing_reason_codes)
        ),
        detail=(
            regime_lite_safing_recommendation.detail
            if regime_lite_safing_recommendation is not None
            else (
                "regime_lite assessment supplied without explicit safing recommendation"
                if regime_lite_assessment is not None
                else "regime_lite safing recommendation supplied without explicit assessment"
            )
        ),
    )


def _runtime_evidence_ready(validation: ShadowValidationSet) -> bool:
    return (
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


def _shadow_import_identity_failures(
    validation: ShadowValidationSet,
    *,
    normalized_validation_status: str,
) -> tuple[str, ...]:
    reasons: list[str] = []
    if not validation.accepted_import:
        reasons.append("candidate import must be accepted before Shadow")
    if normalized_validation_status != "accepted":
        reasons.append(
            "candidate import_validation_status must be an accepted status before Shadow"
        )
    if not validation.import_artifact_id or validation.import_artifact_id == "none":
        reasons.append("candidate import artifact_id is required")
    if validation.import_exported_from != "local":
        reasons.append("candidate import exported_from must be local before Shadow")
    if not validation.import_lineage_version or validation.import_lineage_version == "n/a":
        reasons.append("candidate lineage_version is required")
    if validation.import_source_profile != "complete":
        reasons.append("candidate import source_profile must be complete before Shadow")
    if validation.import_review_state not in {"pending", "approved"}:
        reasons.append(
            "candidate import review_state must stay pending or approved before Shadow"
        )
    if not validation.import_dataset_ref:
        reasons.append("candidate import dataset_ref is required before Shadow")
    if not validation.import_clock_ref:
        reasons.append("candidate import clock_ref is required before Shadow")
    if validation.import_activation_stage != "shadow_ready":
        reasons.append("candidate import activation_stage must be shadow_ready before Shadow")
    if validation.import_health_state != "active":
        reasons.append("candidate import health_state must be active before Shadow")
    reasons.extend(
        f"import gate: {reason}" for reason in validation.import_rejection_reasons
    )
    if validation.import_compatibility_status == "rejected":
        reasons.append(
            "candidate import compatibility policy rejected the artifact before Shadow"
        )
    reasons.extend(
        f"import compatibility gate: {reason}"
        for reason in validation.import_compatibility_reasons
    )
    return tuple(reasons)


def _shadow_lineage_failures(validation: ShadowValidationSet) -> tuple[str, ...]:
    reasons: list[str] = []
    if not validation.import_feature_lineage_required:
        reasons.append(
            "candidate import must require feature_lineage_lock before Shadow"
        )
    if not validation.import_feature_lineage_present:
        reasons.append(
            "candidate import must keep feature_lineage_lock present before Shadow"
        )
    if validation.import_feature_lineage_status != "ok":
        reasons.append(
            "candidate import feature_lineage_lock must be valid before Shadow"
        )
    reasons.extend(
        f"import feature lineage gate: {reason}"
        for reason in validation.import_feature_lineage_reasons
    )
    if not validation.import_transform_whitelist_required:
        reasons.append(
            "candidate import must require transform_whitelist_lock before Shadow"
        )
    if not validation.import_transform_whitelist_present:
        reasons.append(
            "candidate import must keep transform_whitelist_lock present before Shadow"
        )
    if validation.import_transform_whitelist_status != "ok":
        reasons.append(
            "candidate import transform_whitelist_lock must be valid before Shadow"
        )
    reasons.extend(
        f"import transform whitelist gate: {reason}"
        for reason in validation.import_transform_whitelist_reasons
    )
    return tuple(reasons)


def _shadow_policy_failures(validation: ShadowValidationSet) -> tuple[str, ...]:
    reasons: list[str] = []
    if validation.import_signature_check_status in {
        "signature_invalid",
        "trust_store_unavailable",
        "key_id_unknown",
        "key_revoked",
        "payload_hash_mismatch",
    }:
        reasons.append(
            "candidate import signature policy rejected the artifact before Shadow"
        )
    reasons.extend(
        f"import signature gate: {reason}"
        for reason in validation.import_signature_check_reasons
    )
    if validation.import_conflict_resolution_mode != "no_trade_then_strictest":
        reasons.append(
            "candidate import conflict policy must keep resolution_mode=no_trade_then_strictest before Shadow"
        )
    if validation.import_conflict_hard_veto_action != "no_trade":
        reasons.append(
            "candidate import conflict policy must keep hard_veto_action=no_trade before Shadow"
        )
    if validation.import_conflict_score_aggregation_mode != "bounded_sum_with_global_cap":
        reasons.append(
            "candidate import conflict policy must keep score_aggregation_mode=bounded_sum_with_global_cap before Shadow"
        )
    if validation.import_conflict_size_reduce_mode != "min_factor_wins":
        reasons.append(
            "candidate import conflict policy must keep size_reduce_mode=min_factor_wins before Shadow"
        )
    if validation.import_conflict_rank_adjust_mode != "bounded_sum":
        reasons.append(
            "candidate import conflict policy must keep rank_adjust_mode=bounded_sum before Shadow"
        )
    if not validation.import_conflict_additive_soft_boosts_allowed:
        reasons.append(
            "candidate import conflict policy must keep additive_soft_boosts_allowed=True before Shadow"
        )
    if not validation.import_conflict_additive_soft_reduces_allowed:
        reasons.append(
            "candidate import conflict policy must keep additive_soft_reduces_allowed=True before Shadow"
        )
    if validation.import_registry_atomicity_mode != "atomic_snapshot_swap":
        reasons.append(
            "candidate import registry policy must keep atomicity_mode=atomic_snapshot_swap before Shadow"
        )
    if validation.import_registry_concurrency_model != "single_writer_multi_reader":
        reasons.append(
            "candidate import registry policy must keep concurrency_model=single_writer_multi_reader before Shadow"
        )
    if not validation.import_registry_publish_requires_atomic_replace:
        reasons.append(
            "candidate import registry policy must require atomic replace before Shadow"
        )
    if not validation.import_registry_publish_requires_fsync:
        reasons.append(
            "candidate import registry policy must require fsync before Shadow"
        )
    if not validation.import_registry_rollback_to_last_known_good:
        reasons.append(
            "candidate import registry policy must keep rollback_to_last_known_good=True before Shadow"
        )
    if validation.import_payload_ref_count < 5:
        reasons.append("candidate import must keep payload_ref_count>=5 before Shadow")
    if not validation.import_payload_bundle_present:
        reasons.append("candidate import must keep payload_bundle_present=True before Shadow")
    if not validation.import_review_export_ref:
        reasons.append("candidate import must keep review_export_ref before Shadow")
    if not validation.import_feature_bridge_ref:
        reasons.append("candidate import must keep feature_bridge_ref before Shadow")
    if not validation.import_parity_diagnostics_ref:
        reasons.append("candidate import must keep parity_diagnostics_ref before Shadow")
    if not validation.import_replay_metrics_ref:
        reasons.append("candidate import must keep replay_metrics_ref before Shadow")
    if not validation.import_replay_dtr_ref:
        reasons.append("candidate import must keep replay_dtr_ref before Shadow")
    return tuple(reasons)


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


def _shadow_runtime_gate_failures(
    validation: ShadowValidationSet,
    *,
    missing_engines: tuple[str, ...],
    missing_components: tuple[str, ...],
    normalized_build14_status: str,
) -> tuple[str, ...]:
    reasons: list[str] = []
    if validation.runtime_data_source not in _RUNTIME_EVIDENCE_ACCEPTED_SOURCES:
        reasons.append(
            "Build-11 Shadow requires runtime evidence from live_websocket or recorded_replay"
        )
    if not validation.runtime_feature_bridge_ready:
        reasons.append(
            "Build-11 Shadow requires feature bridge evidence (prices -> features -> engines)"
        )
    if not validation.runtime_parity_diagnostics_ready:
        reasons.append("Build-11 Shadow requires parity diagnostics evidence")
    if not validation.runtime_replay_metrics_ready:
        reasons.append("Build-11 Shadow requires replay metrics evidence")
    if not validation.runtime_replay_dtr_ready:
        reasons.append("Build-11 Shadow requires replay DTR evidence")
    if not validation.runtime_event_loop_ready:
        reasons.append("Build-11 Shadow requires event loop evidence")
    if not validation.runtime_config_loaded:
        reasons.append("Build-11 Shadow requires official config loading evidence")
    if not validation.runtime_shadow_dtr_persisted:
        reasons.append("Build-11 Shadow requires persisted shadow DTR evidence")
    if validation.runtime_continuous_hours < 24.0:
        reasons.append(
            "Build-11 Shadow requires at least 24h of real runtime evidence before the verdict gate"
        )
    if validation.shadow_days_completed < validation.shadow_required_days:
        reasons.append(
            "Build-11 Shadow requires 30 consecutive days before the verdict gate"
        )
    if not validation.shadow_report_ready:
        reasons.append(
            "Build-11 Shadow requires a complete shadow report before the verdict gate"
        )
    if not validation.inter_engine_comparison_ready:
        reasons.append(
            "Build-11 Shadow requires an inter-engine A/B/C/D comparison in the report"
        )
    if not validation.build14_contribution_ready:
        reasons.append(
            "Build-11 Shadow requires Build-14 contribution evidence in the report"
        )
    if missing_engines:
        reasons.append(
            "Build-11 Shadow requires A/B/C/D active in Shadow: "
            + ", ".join(missing_engines)
        )
    if normalized_build14_status == "planned":
        reasons.append("Build-11 Shadow requires Build-14 to be active, not planned")
    if missing_components:
        reasons.append(
            "Build-11 Shadow requires component verdicts for A/B/C/D and all Build-14 enablers: "
            + ", ".join(missing_components)
        )
    return tuple(reasons)


def _shadow_validation_decision(
    *,
    structurally_blocked: bool,
    comparisons: tuple[ShadowComparison, ...],
    blocking_reasons: tuple[str, ...],
    manual_review_required: bool,
    review_export_ready: bool,
) -> tuple[ShadowDecision, ShadowRunState]:
    if structurally_blocked:
        return (
            ShadowDecision(
                accepted=False,
                verdict=ShadowVerdict.BLOCKED,
                normalized_promotion_state=PromotionState.REPLAY_ONLY,
                review_state=ReviewState.NEEDS_REVISION,
                blocking_reasons=blocking_reasons,
                manual_review_required=True,
            ),
            ShadowRunState.BLOCKED,
        )
    if any(comparison.blocking for comparison in comparisons):
        return (
            ShadowDecision(
                accepted=False,
                verdict=ShadowVerdict.REJECTED,
                normalized_promotion_state=PromotionState.REPLAY_ONLY,
                review_state=ReviewState.NEEDS_REVISION,
                blocking_reasons=blocking_reasons,
                manual_review_required=True,
            ),
            ShadowRunState.COMPLETED,
        )
    if manual_review_required and not review_export_ready:
        return (
            ShadowDecision(
                accepted=False,
                verdict=ShadowVerdict.NEEDS_REVIEW,
                normalized_promotion_state=PromotionState.REPLAY_ONLY,
                review_state=ReviewState.NEEDS_REVISION,
                blocking_reasons=("Build-9X review export must be ready before accepting Shadow",),
                manual_review_required=True,
            ),
            ShadowRunState.COMPLETED,
        )
    return (
        ShadowDecision(
            accepted=True,
            verdict=ShadowVerdict.ACCEPTED,
            normalized_promotion_state=PromotionState.SHADOW_CANDIDATE,
            review_state=ReviewState.PENDING,
            blocking_reasons=(),
            manual_review_required=manual_review_required,
        ),
        ShadowRunState.COMPLETED,
    )


def _build_info_stress_governance_summary(
    *,
    info_stress_assessment: InfoStressAssessment | None,
) -> InfoStressGovernanceSummary:
    if info_stress_assessment is None:
        return InfoStressGovernanceSummary()

    return InfoStressGovernanceSummary(
        status="assessment_only",
        level=info_stress_assessment.level.value,
        alert_count=info_stress_assessment.alert_count,
        entries_blocked=info_stress_assessment.entries_blocked,
        entries_blocked_until_ts=info_stress_assessment.entries_blocked_until_ts,
        reason_codes=info_stress_assessment.reason_codes,
        detail=info_stress_assessment.detail,
    )


def _build_daily_pnl_breaker_governance_summary(
    *,
    daily_pnl_breaker_assessment: DailyPnlBreakerAssessment | None,
) -> DailyPnlBreakerGovernanceSummary:
    if daily_pnl_breaker_assessment is None:
        return DailyPnlBreakerGovernanceSummary()

    return DailyPnlBreakerGovernanceSummary(
        status="assessment_only",
        verdict=daily_pnl_breaker_assessment.verdict.value,
        should_force_shadow=daily_pnl_breaker_assessment.should_force_shadow,
        circuit_breaker_tripped=daily_pnl_breaker_assessment.circuit_breaker_tripped,
        circuit_breaker_reason=daily_pnl_breaker_assessment.circuit_breaker_reason,
        drawdown_pct=daily_pnl_breaker_assessment.drawdown_pct,
        threshold_pct=daily_pnl_breaker_assessment.threshold_pct,
        shadow_locked_session_date=(
            daily_pnl_breaker_assessment.state.shadow_locked_session_date
        ),
        state_corrupted=daily_pnl_breaker_assessment.state.state_corrupted,
        state_last_reason=daily_pnl_breaker_assessment.state.last_reason,
        detail=daily_pnl_breaker_assessment.detail,
        reason_codes=daily_pnl_breaker_assessment.reason_codes,
    )


def run_shadow_validation(
    shadow_input: ShadowInput,
    *,
    run_id: str | None = None,
    regime_lite_assessment: RegimeLiteAssessment | None = None,
    regime_lite_safing_recommendation: RegimeLiteSafingRecommendation | None = None,
    info_stress_assessment: InfoStressAssessment | None = None,
    daily_pnl_breaker_assessment: DailyPnlBreakerAssessment | None = None,
) -> ShadowRunSummary:
    """Run the minimal real Build-11 Shadow gating logic."""

    comparisons = compare_shadow_candidate(shadow_input)
    validation = shadow_input.validation_set
    normalized_validation_status = validation.import_validation_status.strip().casefold()
    missing_engines = tuple(sorted(_REQUIRED_SHADOW_ENGINES - set(validation.active_engines)))
    missing_components = _missing_shadow_components(validation.component_assessments)
    normalized_build14_status = validation.build14_status.strip().casefold()
    runtime_evidence_ready = _runtime_evidence_ready(validation)
    regime_lite_governance = _build_regime_lite_governance_summary(
        regime_lite_assessment=regime_lite_assessment,
        regime_lite_safing_recommendation=regime_lite_safing_recommendation,
    )
    info_stress_governance = _build_info_stress_governance_summary(
        info_stress_assessment=info_stress_assessment,
    )
    daily_pnl_breaker_governance = _build_daily_pnl_breaker_governance_summary(
        daily_pnl_breaker_assessment=daily_pnl_breaker_assessment,
    )
    blocking_reasons = list(
        _shadow_import_identity_failures(
            validation,
            normalized_validation_status=normalized_validation_status,
        )
    )
    blocking_reasons.extend(_shadow_lineage_failures(validation))
    blocking_reasons.extend(_shadow_policy_failures(validation))
    blocking_reasons.extend(
        _shadow_runtime_gate_failures(
            validation,
            missing_engines=missing_engines,
            missing_components=missing_components,
            normalized_build14_status=normalized_build14_status,
        )
    )
    structurally_blocked = bool(blocking_reasons)
    blocking_reasons.extend(
        comparison.summary for comparison in comparisons if comparison.blocking
    )
    manual_review_required = (
        validation.build9x_diagnostics_count > 0
        or validation.open_hypotheses > 0
        or validation.replay_candidate_count > 0
    )
    decision, run_state = _shadow_validation_decision(
        structurally_blocked=structurally_blocked,
        comparisons=comparisons,
        blocking_reasons=tuple(blocking_reasons),
        manual_review_required=manual_review_required,
        review_export_ready=validation.review_export_ready,
    )
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
        regime_lite_governance=regime_lite_governance,
        info_stress_governance=info_stress_governance,
        daily_pnl_breaker_governance=daily_pnl_breaker_governance,
    )


__all__ = ["run_shadow_validation"]
