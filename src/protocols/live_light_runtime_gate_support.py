"""Gate-surface helpers for the governed Build-13 Live-Light runtime."""

from __future__ import annotations

from dataclasses import dataclass

from interface_contracts import ALL_PAIRS, ProfileId, RuntimeMode
from monitoring import TechnicalDashboardPayload
from protocols.contracts import LiveLightInput, MicroLiveRunSummary, ShadowPortfolioJudgment
from protocols.errors import LiveLightInputError

_SHADOW_ENGINE_IDS = frozenset({"engine_a", "engine_b", "engine_c", "engine_d"})


@dataclass(frozen=True)
class _ResolvedShadowSurface:
    active_engines: tuple[str, ...]
    shadow_days_completed: int
    shadow_required_days: int
    component_verdicts_rendered: bool
    shadow_report_ready: bool


def _format_operator_safing_reason(request: object) -> str:
    target_runtime_mode = getattr(request, "target_runtime_mode", None)
    target_mode = (
        f" -> {target_runtime_mode.value}"
        if target_runtime_mode is not None
        else ""
    )
    return (
        "operator safing request: "
        f"{request.action.value} ({request.source_runtime_mode.value}{target_mode}) "
        f"reason={request.reason}"
    )


def _shadow_portfolio_blocking_reasons(
    judgment: ShadowPortfolioJudgment | dict[str, object],
) -> tuple[str, ...]:
    if isinstance(judgment, dict):
        judgment = type("_JudgmentProxy", (), judgment)()

    if judgment.judgment_verdict == "promotable":
        return ()

    reasons = [
        f"shadow portfolio judgment={judgment.judgment_verdict}: {judgment.rationale}"
    ]
    for label, pressure in (
        ("physics", judgment.physics_pressure),
        ("redundancy", judgment.redundancy_pressure),
        ("cluster", judgment.cluster_pressure),
        ("beta", judgment.beta_pressure),
        ("gross_capacity", judgment.gross_capacity_pressure),
        ("loss_capacity", judgment.loss_capacity_pressure),
    ):
        if pressure in {"elevated", "critical"}:
            reasons.append(f"shadow portfolio {label}_pressure={pressure}")
    if judgment.portfolio_rejected_engine_count > 0:
        reasons.append(
            f"shadow portfolio rejected_engines={judgment.portfolio_rejected_engine_count}"
        )
    for label, count in (
        ("cluster_rejected_engines", judgment.cluster_rejected_engine_count),
        ("beta_rejected_engines", judgment.beta_rejected_engine_count),
        ("exposure_rejected_engines", judgment.exposure_rejected_engine_count),
        ("loss_budget_rejected_engines", judgment.loss_budget_rejected_engine_count),
    ):
        if count > 0:
            reasons.append(f"shadow portfolio {label}={count}")
    if judgment.ranking_rejected_engine_count > 0:
        reasons.append(
            f"shadow ranking_rejected_engines={judgment.ranking_rejected_engine_count}"
        )
    for label, count in (
        ("elevated_physics_engines", judgment.elevated_physics_engine_count),
        ("critical_physics_engines", judgment.critical_physics_engine_count),
    ):
        if count > 0:
            reasons.append(f"shadow portfolio {label}={count}")
    if judgment.phantom_trade_count:
        reasons.append(f"shadow phantom_trade_count={judgment.phantom_trade_count}")
    return tuple(reasons)


def _shadow_engine_scope_blocking_reasons(
    live_light_input: LiveLightInput,
) -> tuple[str, ...]:
    reasons: list[str] = []
    active_engines = set(live_light_input.active_engines)
    shadow_promotable_engines = set(live_light_input.shadow_promotable_engines)
    shadow_shadow_only_engines = set(live_light_input.shadow_shadow_only_engines)
    shadow_rewrite_required_engines = set(live_light_input.shadow_rewrite_required_engines)

    if not active_engines:
        reasons.append("Build-13 Live-Light requires at least one governed engine")
        return tuple(reasons)

    unknown_active_engines = active_engines - _SHADOW_ENGINE_IDS
    if unknown_active_engines:
        reasons.append(
            "Build-13 Live-Light allows only governed engines from the Full Shadow perimeter"
        )

    if shadow_promotable_engines:
        unknown_shadow_promotable = shadow_promotable_engines - _SHADOW_ENGINE_IDS
        if unknown_shadow_promotable:
            reasons.append(
                "Build-13 Live-Light shadow_promotable_engines must stay within the governed engine perimeter"
            )
        if not active_engines.issubset(shadow_promotable_engines):
            reasons.append(
                "Build-13 Live-Light active_engines must be PROMOTABLE in Shadow judgment"
            )
    elif shadow_shadow_only_engines or shadow_rewrite_required_engines:
        reasons.append(
            "Build-13 Live-Light requires at least one PROMOTABLE engine in Shadow judgment"
        )

    if active_engines & shadow_shadow_only_engines:
        reasons.append(
            "Build-13 Live-Light must not activate engines marked SHADOW_ONLY in Shadow judgment"
        )
    if active_engines & shadow_rewrite_required_engines:
        reasons.append(
            "Build-13 Live-Light must not activate engines marked REWRITE_REQUIRED in Shadow judgment"
        )

    return tuple(reasons)


def _micro_live_surface_blocking_reasons(
    live_light_input: LiveLightInput,
) -> tuple[str, ...]:
    reasons: list[str] = []
    active_engines = set(live_light_input.active_engines)
    live_pairs = set(live_light_input.live_pairs)
    micro_live_planned_engines = set(live_light_input.micro_live_planned_engines)
    micro_live_planned_pairs = set(live_light_input.micro_live_planned_pairs)

    if not micro_live_planned_engines:
        reasons.append("Build-13 Live-Light requires governed micro_live_planned_engines")
    else:
        unknown_planned_engines = micro_live_planned_engines - _SHADOW_ENGINE_IDS
        if unknown_planned_engines:
            reasons.append(
                "Build-13 Live-Light micro_live_planned_engines must stay within the governed engine perimeter"
            )
        if not active_engines.issubset(micro_live_planned_engines):
            reasons.append(
                "Build-13 Live-Light active_engines must stay within the governed Micro-live planned_engines"
            )

    if not micro_live_planned_pairs:
        reasons.append("Build-13 Live-Light requires governed micro_live_planned_pairs")
    else:
        invalid_planned_pairs = tuple(
            pair for pair in micro_live_planned_pairs if pair not in ALL_PAIRS
        )
        if invalid_planned_pairs:
            reasons.append(
                "Build-13 Live-Light micro_live_planned_pairs must stay within the Complete pair scope"
            )
        if not live_pairs.issubset(micro_live_planned_pairs):
            reasons.append(
                "Build-13 Live-Light live_pairs must stay within the governed Micro-live planned_pairs"
            )

    return tuple(reasons)


def _live_surface_budget_blocking_reasons(
    live_light_input: LiveLightInput,
) -> tuple[str, ...]:
    reasons: list[str] = []

    if not live_light_input.live_pairs:
        reasons.append("Build-13 Live-Light requires at least one live pair")
    elif len(live_light_input.live_pairs) > len(ALL_PAIRS):
        reasons.append("Build-13 Live-Light must stay within the Complete pair scope")
    else:
        invalid_pairs = tuple(
            pair for pair in live_light_input.live_pairs if pair not in ALL_PAIRS
        )
        if invalid_pairs:
            reasons.append(
                "Build-13 Live-Light live_pairs must stay within the Complete pair scope"
            )

    if live_light_input.max_pair_notional_usdt > live_light_input.max_total_notional_usdt:
        reasons.append("Live-Light max_pair_notional_usdt must stay within total cap")
    if (
        live_light_input.requested_pair_notional_usdt
        > live_light_input.requested_total_notional_usdt
    ):
        reasons.append(
            "Live-Light requested_pair_notional_usdt must stay within total request"
        )
    if (
        live_light_input.requested_total_notional_usdt
        > live_light_input.max_total_notional_usdt
    ):
        reasons.append("Live-Light requested_total_notional_usdt exceeds max cap")
    if (
        live_light_input.requested_pair_notional_usdt
        > live_light_input.max_pair_notional_usdt
    ):
        reasons.append("Live-Light requested_pair_notional_usdt exceeds max pair cap")
    if (
        live_light_input.execution_order_limit < 1
        or live_light_input.execution_order_limit > 20
    ):
        reasons.append("Build-13 Live-Light requires execution_order_limit within [1, 20]")

    return tuple(reasons)


def _rollout_temporal_blocking_reasons(
    live_light_input: LiveLightInput,
) -> tuple[str, ...]:
    reasons: list[str] = []

    if live_light_input.shadow_days_completed < live_light_input.shadow_required_days:
        reasons.append("Build-13 Live-Light requires a completed 30-day Shadow")
    if not live_light_input.component_verdicts_rendered:
        reasons.append("Build-13 Live-Light requires rendered component verdicts from Shadow")
    if not live_light_input.shadow_report_ready:
        reasons.append("Build-13 Live-Light requires shadow_report_ready=True")
    if live_light_input.micro_live_stable_days < live_light_input.micro_live_required_days:
        reasons.append("Build-13 Live-Light requires 7 stable Micro-live days")

    return tuple(reasons)


def _governance_envelope_blocking_reasons(
    live_light_input: LiveLightInput,
) -> tuple[str, ...]:
    reasons: list[str] = []

    if not live_light_input.correlation_id.strip():
        reasons.append("Build-13 Live-Light requires a concrete correlation_id")
    if live_light_input.profile != ProfileId.COMPLETE:
        reasons.append("Build-13 Live-Light opens in COMPLETE profile only")
    if live_light_input.runtime_mode != RuntimeMode.LIVE:
        reasons.append("Build-13 Live-Light requires runtime_mode=LIVE")
    if not live_light_input.micro_live_run_id.strip():
        reasons.append("Build-13 Live-Light requires a concrete micro_live_run_id")
    if not live_light_input.shadow_run_id.strip():
        reasons.append("Build-13 Live-Light requires a concrete shadow_run_id")
    if live_light_input.backtest_profile is not None:
        reasons.append("BACKTEST_PROFILE is forbidden in the unified V5.3")
    if live_light_input.creates_profile_fork:
        reasons.append("Local/VPS profile forks are forbidden")
    if live_light_input.automatic_complete_promotion_requested:
        reasons.append(
            "Build-13 Live-Light must not request automatic promotion to Complete"
        )
    if (
        live_light_input.operator_safing_request is not None
        and live_light_input.operator_safing_request.source_runtime_mode
        != live_light_input.runtime_mode
    ):
        reasons.append(
            "Build-13 Live-Light operator_safing_request must match source_runtime_mode=LIVE"
        )
    if live_light_input.shadow_required_days != 30:
        reasons.append("Build-13 Live-Light requires shadow_required_days=30")
    if live_light_input.micro_live_required_days != 7:
        reasons.append("Build-13 Live-Light requires micro_live_required_days=7")
    if (
        not live_light_input.micro_live_import_artifact_id
        or live_light_input.micro_live_import_artifact_id == "none"
    ):
        reasons.append(
            "Build-13 Live-Light requires a concrete micro_live_import_artifact_id"
        )
    if (
        not live_light_input.micro_live_import_lineage_version
        or live_light_input.micro_live_import_lineage_version == "n/a"
    ):
        reasons.append(
            "Build-13 Live-Light requires a concrete micro_live_import_lineage_version"
        )
    if not live_light_input.import_artifact_id or live_light_input.import_artifact_id == "none":
        reasons.append("Build-13 Live-Light requires a concrete import_artifact_id")
    if (
        not live_light_input.import_lineage_version
        or live_light_input.import_lineage_version == "n/a"
    ):
        reasons.append("Build-13 Live-Light requires a concrete lineage_version")

    return tuple(reasons)


def _resolve_shadow_surface(
    micro_live_summary: MicroLiveRunSummary,
    micro_live_payload: TechnicalDashboardPayload,
    *,
    active_engines: tuple[str, ...] | None,
    shadow_days_completed: int | None,
    shadow_required_days: int | None,
    component_verdicts_rendered: bool | None,
    shadow_report_ready: bool | None,
) -> _ResolvedShadowSurface:
    shadow_projection = micro_live_payload.shadow
    resolved_component_verdicts_rendered = (
        (
            shadow_projection.shadow_validated_component_count
            + shadow_projection.dormant_component_count
        )
        > 0
        if component_verdicts_rendered is None
        else component_verdicts_rendered
    )
    return _ResolvedShadowSurface(
        active_engines=active_engines or micro_live_summary.execution_plan.planned_engines,
        shadow_days_completed=(
            shadow_projection.shadow_days_completed
            if shadow_days_completed is None
            else shadow_days_completed
        ),
        shadow_required_days=(
            shadow_projection.shadow_required_days
            if shadow_required_days is None
            else shadow_required_days
        ),
        component_verdicts_rendered=resolved_component_verdicts_rendered,
        shadow_report_ready=(
            shadow_projection.shadow_report_ready
            if shadow_report_ready is None
            else shadow_report_ready
        ),
    )


def _build_live_light_import_fields(
    micro_live_payload: TechnicalDashboardPayload,
) -> dict[str, object]:
    replay_import = micro_live_payload.replay_import
    return {
        "import_artifact_id": replay_import.artifact_id,
        "import_exported_from": replay_import.exported_from,
        "import_lineage_version": replay_import.lineage_version,
        "import_validation_status": replay_import.validation_status,
        "import_source_profile": replay_import.source_profile,
        "import_review_state": replay_import.review_state,
        "import_rejection_reasons": replay_import.rejection_reasons,
        "import_dataset_ref": replay_import.dataset_ref,
        "import_clock_ref": replay_import.clock_ref,
        "import_activation_stage": replay_import.activation_stage,
        "import_health_state": replay_import.health_state,
        "import_compatibility_status": replay_import.compatibility_status,
        "import_compatibility_reasons": replay_import.compatibility_reasons,
        "import_feature_lineage_required": replay_import.feature_lineage_required,
        "import_feature_lineage_present": replay_import.feature_lineage_present,
        "import_feature_lineage_status": replay_import.feature_lineage_status,
        "import_feature_lineage_reasons": replay_import.feature_lineage_reasons,
        "import_transform_whitelist_required": replay_import.transform_whitelist_required,
        "import_transform_whitelist_present": replay_import.transform_whitelist_present,
        "import_transform_whitelist_status": replay_import.transform_whitelist_status,
        "import_transform_whitelist_reasons": replay_import.transform_whitelist_reasons,
        "import_signature_check_status": replay_import.signature_check_status,
        "import_signature_check_reasons": replay_import.signature_check_reasons,
        "import_conflict_resolution_mode": replay_import.conflict_resolution_mode,
        "import_conflict_hard_veto_action": replay_import.conflict_hard_veto_action,
        "import_conflict_score_aggregation_mode": replay_import.conflict_score_aggregation_mode,
        "import_conflict_size_reduce_mode": replay_import.conflict_size_reduce_mode,
        "import_conflict_rank_adjust_mode": replay_import.conflict_rank_adjust_mode,
        "import_conflict_additive_soft_boosts_allowed": replay_import.conflict_additive_soft_boosts_allowed,
        "import_conflict_additive_soft_reduces_allowed": replay_import.conflict_additive_soft_reduces_allowed,
        "import_registry_atomicity_mode": replay_import.registry_atomicity_mode,
        "import_registry_concurrency_model": replay_import.registry_concurrency_model,
        "import_registry_publish_requires_atomic_replace": replay_import.registry_publish_requires_atomic_replace,
        "import_registry_publish_requires_fsync": replay_import.registry_publish_requires_fsync,
        "import_registry_rollback_to_last_known_good": replay_import.registry_rollback_to_last_known_good,
        "import_payload_ref_count": replay_import.payload_ref_count,
        "import_payload_bundle_present": replay_import.payload_bundle_present,
        "import_review_export_ref": replay_import.review_export_ref,
        "import_feature_bridge_ref": replay_import.feature_bridge_ref,
        "import_parity_diagnostics_ref": replay_import.parity_diagnostics_ref,
        "import_replay_metrics_ref": replay_import.replay_metrics_ref,
        "import_replay_dtr_ref": replay_import.replay_dtr_ref,
    }


def _build_live_light_runtime_fields(
    micro_live_summary: MicroLiveRunSummary,
) -> dict[str, object]:
    return {
        "execution_runtime_projection_ref": micro_live_summary.execution_runtime_projection_ref,
        "execution_runtime_projection_status": micro_live_summary.execution_runtime_projection_status,
        "execution_runtime_projection_ready": micro_live_summary.execution_runtime_projection_ready,
        "execution_runtime_projection_consumer_count": micro_live_summary.execution_runtime_projection_consumer_count,
        "execution_runtime_projection_ready_consumer_count": micro_live_summary.execution_runtime_projection_ready_consumer_count,
        "execution_runtime_projection_partial_consumer_count": micro_live_summary.execution_runtime_projection_partial_consumer_count,
        "execution_runtime_projection_blocked_consumer_count": micro_live_summary.execution_runtime_projection_blocked_consumer_count,
        "regime_lite_governance": micro_live_summary.regime_lite_governance,
        "info_stress_governance": micro_live_summary.info_stress_governance,
    }


__all__ = [
    "_format_operator_safing_reason",
    "_shadow_portfolio_blocking_reasons",
    "_shadow_engine_scope_blocking_reasons",
    "_micro_live_surface_blocking_reasons",
    "_live_surface_budget_blocking_reasons",
    "_rollout_temporal_blocking_reasons",
    "_governance_envelope_blocking_reasons",
    "_resolve_shadow_surface",
    "_build_live_light_import_fields",
    "_build_live_light_runtime_fields",
]
