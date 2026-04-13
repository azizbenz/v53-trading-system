"""Minimal governed Build-13 Live-Light gate and execution-intent builder.

HARD STATEMENT §0.6: 30j shadow prerequisite enforced before Live-Light.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import ValidationError

from interface_contracts import (
    ALL_PAIRS,
    Build14InfluenceReport,
    Build14InfluenceSignal,
    PromotionState,
    ProfileId,
    ReviewState,
    RuntimeMode,
)
from monitoring import TechnicalDashboardPayload
from protocols.contracts import (
    LiveLightDecision,
    LiveLightExecutionIntent,
    LiveLightInput,
    LiveLightRunSummary,
    MicroLiveRunSummary,
)
from protocols.enums import (
    LiveLightRunState,
    LiveLightVerdict,
    MicroLiveRunState,
    MicroLiveVerdict,
)
from protocols.errors import LiveLightInputError

Build14InfluenceContract = Build14InfluenceSignal | Build14InfluenceReport
_SHADOW_ENGINE_IDS = frozenset({"engine_a", "engine_b", "engine_c", "engine_d"})


def _format_operator_safing_reason(request) -> str:
    target_mode = (
        f" -> {request.target_runtime_mode.value}"
        if request.target_runtime_mode is not None
        else ""
    )
    return (
        "operator safing request: "
        f"{request.action.value} ({request.source_runtime_mode.value}{target_mode}) "
        f"reason={request.reason}"
    )


def _normalized_value(value: object, default: str) -> str:
    if value is None:
        return default
    enum_value = getattr(value, "value", value)
    return str(enum_value)


def _revalidate_typed_build14_contract(
    value: Build14InfluenceContract,
) -> Build14InfluenceContract:
    return value.__class__.model_validate(value.model_dump())


def _resolve_validated_build14_signal(
    build14_influence: object | None,
    *,
    expected_correlation_id: str,
) -> tuple[Build14InfluenceSignal | None, tuple[str, ...]]:
    if build14_influence is None:
        return None, ()

    typed_contract: Build14InfluenceContract
    if isinstance(build14_influence, Build14InfluenceSignal):
        contract_kind = "signal"
        typed_contract = build14_influence
    elif isinstance(build14_influence, Build14InfluenceReport):
        contract_kind = "report"
        typed_contract = build14_influence
    else:
        return None, (
            "Build-14 influence must be a typed Build14InfluenceSignal or Build14InfluenceReport",
        )

    try:
        validated_contract = _revalidate_typed_build14_contract(typed_contract)
    except ValidationError as exc:
        first_error = exc.errors()[0] if exc.errors() else {}
        detail = str(first_error.get("msg", "")).strip()
        if not detail:
            detail = "Build-14 influence failed typed contract validation"
        return None, (f"Build-14 influence failed typed contract validation: {detail}",)
    except (TypeError, ValueError) as exc:
        detail = str(exc).strip() or "Build-14 influence failed typed contract validation"
        return None, (f"Build-14 influence failed typed contract validation: {detail}",)

    if contract_kind == "report":
        report_correlation_id = validated_contract.correlation_id.strip()
        if not report_correlation_id:
            return None, ("Build-14 influence report must expose a concrete correlation_id",)
        if report_correlation_id != expected_correlation_id:
            return None, (
                "Build-14 influence correlation_id must match the current Live-Light run",
            )
        signal = validated_contract.signal
    else:
        signal = validated_contract

    signal_correlation_id = signal.correlation_id.strip()
    if not signal_correlation_id:
        return None, ("Build-14 influence must expose a concrete correlation_id",)
    if signal_correlation_id != expected_correlation_id:
        return None, (
            "Build-14 influence correlation_id must match the current Live-Light run",
        )

    return signal, ()


def _build14_reason_codes(signal: object | None) -> tuple[str, ...]:
    if signal is None:
        return ()
    raw_value = getattr(signal, "reason_codes", ())
    if raw_value is None:
        return ()
    return tuple(str(item) for item in raw_value)


def _validate_micro_live_source_payload_scope(payload: TechnicalDashboardPayload) -> None:
    if payload.profile != ProfileId.COMPLETE:
        raise LiveLightInputError(
            "Build-13 Live-Light source payload must stay on profile=COMPLETE"
        )
    if payload.runtime_mode != RuntimeMode.MICRO_LIVE:
        raise LiveLightInputError(
            "Build-13 Live-Light source payload must originate from runtime_mode=MICRO_LIVE"
        )


def _validate_micro_live_consistency(
    micro_live_summary: MicroLiveRunSummary,
    micro_live_payload: TechnicalDashboardPayload,
) -> None:
    replay_import = micro_live_payload.replay_import
    projection = micro_live_payload.micro_live
    normalized_status = replay_import.validation_status.strip().casefold()

    if micro_live_summary.correlation_id != micro_live_payload.correlation_id:
        raise LiveLightInputError(
            "Build-13 Live-Light requires matching correlation_id between Micro-live summary and payload"
        )
    if projection.run_state not in {"", "not_run"} and projection.run_state != micro_live_summary.run_state.value:
        raise LiveLightInputError(
            "Build-13 Live-Light requires matching Micro-live run_state between summary and payload"
        )
    if projection.verdict not in {"", "not_run"} and projection.verdict != micro_live_summary.decision.verdict.value:
        raise LiveLightInputError(
            "Build-13 Live-Light requires matching Micro-live verdict between summary and payload"
        )
    if projection.allowed_to_probe != micro_live_summary.decision.allowed_to_probe:
        raise LiveLightInputError(
            "Build-13 Live-Light requires matching Micro-live allowed_to_probe between summary and payload"
        )
    if projection.shadow_run_id and projection.shadow_run_id != micro_live_summary.shadow_run_id:
        raise LiveLightInputError(
            "Build-13 Live-Light requires matching shadow_run_id between Micro-live summary and payload"
        )
    if projection.import_artifact_id not in {"", "none"} and projection.import_artifact_id != micro_live_summary.import_artifact_id:
        raise LiveLightInputError(
            "Build-13 Live-Light requires matching Micro-live/import artifact_id"
        )
    if projection.import_lineage_version not in {"", "n/a"} and projection.import_lineage_version != micro_live_summary.import_lineage_version:
        raise LiveLightInputError(
            "Build-13 Live-Light requires matching Micro-live/import lineage_version"
        )
    if normalized_status != "accepted":
        raise LiveLightInputError(
            "Build-13 Live-Light requires an accepted replay import_validation_status"
        )
    if replay_import.exported_from != "local":
        raise LiveLightInputError(
            "Build-13 Live-Light requires replay import_exported_from=local"
        )
    if replay_import.source_profile != "complete":
        raise LiveLightInputError(
            "Build-13 Live-Light requires replay import_source_profile=complete"
        )
    if replay_import.rejection_reasons:
        raise LiveLightInputError(
            "Build-13 Live-Light requires empty replay import_rejection_reasons"
        )
    if replay_import.review_state not in {"pending", "approved"}:
        raise LiveLightInputError(
            "Build-13 Live-Light requires replay import_review_state to stay pending or approved"
        )
    if not replay_import.dataset_ref:
        raise LiveLightInputError(
            "Build-13 Live-Light requires replay import_dataset_ref"
        )
    if not replay_import.clock_ref:
        raise LiveLightInputError(
            "Build-13 Live-Light requires replay import_clock_ref"
        )
    if replay_import.activation_stage != "shadow_ready":
        raise LiveLightInputError(
            "Build-13 Live-Light requires replay import_activation_stage=shadow_ready"
        )
    if replay_import.health_state != "active":
        raise LiveLightInputError(
            "Build-13 Live-Light requires replay import_health_state=active"
        )
    if replay_import.compatibility_status == "rejected":
        raise LiveLightInputError(
            "Build-13 Live-Light requires a non-rejected replay import_compatibility_status"
        )
    if not replay_import.feature_lineage_required:
        raise LiveLightInputError(
            "Build-13 Live-Light requires replay import_feature_lineage_required=True"
        )
    if not replay_import.feature_lineage_present:
        raise LiveLightInputError(
            "Build-13 Live-Light requires replay import_feature_lineage_present=True"
        )
    if replay_import.feature_lineage_status != "ok":
        raise LiveLightInputError(
            "Build-13 Live-Light requires replay import_feature_lineage_status=ok"
        )
    if not replay_import.transform_whitelist_required:
        raise LiveLightInputError(
            "Build-13 Live-Light requires replay import_transform_whitelist_required=True"
        )
    if not replay_import.transform_whitelist_present:
        raise LiveLightInputError(
            "Build-13 Live-Light requires replay import_transform_whitelist_present=True"
        )
    if replay_import.transform_whitelist_status != "ok":
        raise LiveLightInputError(
            "Build-13 Live-Light requires replay import_transform_whitelist_status=ok"
        )
    if replay_import.signature_check_status != "verified":
        # BS-40: allowlist — only "verified" passes
        raise LiveLightInputError(
            "Build-13 Live-Light requires a non-rejected replay import_signature_check_status"
        )
    if replay_import.conflict_resolution_mode != "no_trade_then_strictest":
        raise LiveLightInputError(
            "Build-13 Live-Light requires replay import_conflict_resolution_mode=no_trade_then_strictest"
        )
    if replay_import.conflict_hard_veto_action != "no_trade":
        raise LiveLightInputError(
            "Build-13 Live-Light requires replay import_conflict_hard_veto_action=no_trade"
        )
    if replay_import.conflict_score_aggregation_mode != "bounded_sum_with_global_cap":
        raise LiveLightInputError(
            "Build-13 Live-Light requires replay import_conflict_score_aggregation_mode=bounded_sum_with_global_cap"
        )
    if replay_import.conflict_size_reduce_mode != "min_factor_wins":
        raise LiveLightInputError(
            "Build-13 Live-Light requires replay import_conflict_size_reduce_mode=min_factor_wins"
        )
    if replay_import.conflict_rank_adjust_mode != "bounded_sum":
        raise LiveLightInputError(
            "Build-13 Live-Light requires replay import_conflict_rank_adjust_mode=bounded_sum"
        )
    if not replay_import.conflict_additive_soft_boosts_allowed:
        raise LiveLightInputError(
            "Build-13 Live-Light requires replay import_conflict_additive_soft_boosts_allowed=True"
        )
    if not replay_import.conflict_additive_soft_reduces_allowed:
        raise LiveLightInputError(
            "Build-13 Live-Light requires replay import_conflict_additive_soft_reduces_allowed=True"
        )
    if replay_import.registry_atomicity_mode != "atomic_snapshot_swap":
        raise LiveLightInputError(
            "Build-13 Live-Light requires replay import_registry_atomicity_mode=atomic_snapshot_swap"
        )
    if replay_import.registry_concurrency_model != "single_writer_multi_reader":
        raise LiveLightInputError(
            "Build-13 Live-Light requires replay import_registry_concurrency_model=single_writer_multi_reader"
        )
    if not replay_import.registry_publish_requires_atomic_replace:
        raise LiveLightInputError(
            "Build-13 Live-Light requires replay import_registry_publish_requires_atomic_replace=True"
        )
    if not replay_import.registry_publish_requires_fsync:
        raise LiveLightInputError(
            "Build-13 Live-Light requires replay import_registry_publish_requires_fsync=True"
        )
    if not replay_import.registry_rollback_to_last_known_good:
        raise LiveLightInputError(
            "Build-13 Live-Light requires replay import_registry_rollback_to_last_known_good=True"
        )
    if replay_import.payload_ref_count < 5:
        raise LiveLightInputError(
            "Build-13 Live-Light requires replay import_payload_ref_count>=5"
        )
    if not replay_import.payload_bundle_present:
        raise LiveLightInputError(
            "Build-13 Live-Light requires replay import_payload_bundle_present=True"
        )
    if not replay_import.review_export_ref:
        raise LiveLightInputError(
            "Build-13 Live-Light requires replay import_review_export_ref"
        )
    if not replay_import.feature_bridge_ref:
        raise LiveLightInputError(
            "Build-13 Live-Light requires replay import_feature_bridge_ref"
        )
    if not replay_import.parity_diagnostics_ref:
        raise LiveLightInputError(
            "Build-13 Live-Light requires replay import_parity_diagnostics_ref"
        )
    if not replay_import.replay_metrics_ref:
        raise LiveLightInputError(
            "Build-13 Live-Light requires replay import_replay_metrics_ref"
        )
    if not replay_import.replay_dtr_ref:
        raise LiveLightInputError(
            "Build-13 Live-Light requires replay import_replay_dtr_ref"
        )
    if not replay_import.artifact_id or replay_import.artifact_id == "none":
        raise LiveLightInputError(
            "Build-13 Live-Light requires a concrete replay import_artifact_id"
        )
    if not replay_import.lineage_version or replay_import.lineage_version == "n/a":
        raise LiveLightInputError(
            "Build-13 Live-Light requires a concrete replay lineage_version"
        )
    if micro_live_summary.import_artifact_id != replay_import.artifact_id:
        raise LiveLightInputError(
            "Build-13 Live-Light requires matching Micro-live/import artifact_id"
        )
    if micro_live_summary.import_lineage_version != replay_import.lineage_version:
        raise LiveLightInputError(
            "Build-13 Live-Light requires matching Micro-live/import lineage_version"
        )


def _validate_live_light_surface(
    micro_live_summary: MicroLiveRunSummary,
    *,
    live_pairs: tuple[str, ...],
    active_engines: tuple[str, ...],
) -> None:
    planned_pairs = set(micro_live_summary.execution_plan.planned_pairs)
    planned_engines = set(micro_live_summary.execution_plan.planned_engines)

    if not set(live_pairs).issubset(planned_pairs):
        raise LiveLightInputError(
            "Build-13 Live-Light live_pairs must stay within the governed Micro-live planned_pairs"
        )
    if not set(active_engines).issubset(planned_engines):
        raise LiveLightInputError(
            "Build-13 Live-Light active_engines must stay within the governed Micro-live planned_engines"
        )


def _build14_guardrail_reasons(
    signal: object,
) -> tuple[str, ...]:
    reasons: list[str] = []
    influence_mode = _normalized_value(getattr(signal, "influence_mode", None), "read_only")
    action = _normalized_value(getattr(signal, "action", None), "observe")
    reason_codes = _build14_reason_codes(signal)
    confidence_penalty_weight = float(getattr(signal, "confidence_penalty_weight", 0.0))
    recommended_budget_factor = float(getattr(signal, "recommended_budget_factor", 1.0))
    requires_manual_review = bool(getattr(signal, "requires_manual_review", False))
    stability_confirmed = bool(getattr(signal, "stability_confirmed", True))
    non_regression_required = bool(getattr(signal, "non_regression_required", True))
    families = tuple(getattr(signal, "families", ()) or ())

    if (
        bool(getattr(signal, "can_override_engines", False))
        or bool(getattr(signal, "can_bypass_risk", False))
        or bool(getattr(signal, "can_bypass_portfolio", False))
    ):
        reasons.append(
            "Build-14 influence must never bypass engines, risk, or portfolio"
        )
    if bool(getattr(signal, "can_trade_autonomously", False)):
        reasons.append("Build-14 influence must never trade autonomously")
    if not non_regression_required:
        reasons.append("Build-14 influence must keep non_regression_required=True")

    if influence_mode == "shadow_enabled":
        reasons.append(
            "Shadow-enabled Build-14 outputs require explicit post-Shadow live translation before Live-Light"
        )
        return tuple(reasons)

    if influence_mode == "read_only":
        if action != "observe":
            reasons.append("read-only Build-14 influence must keep action=observe")
        if confidence_penalty_weight != 0.0:
            reasons.append("read-only Build-14 influence must keep zero confidence penalty")
        if recommended_budget_factor != 1.0:
            reasons.append("read-only Build-14 influence must keep budget factor at 1.0")
        if requires_manual_review:
            reasons.append("read-only Build-14 influence must not require manual review")
        return tuple(reasons)

    if not stability_confirmed:
        reasons.append("limited Build-14 influence requires stability_confirmed=True")
    if not families:
        reasons.append("limited Build-14 influence must reference at least one signal family")
    if action == "observe":
        reasons.append("limited Build-14 influence must not keep action=observe")
    if action == "downgrade_confidence":
        if confidence_penalty_weight <= 0.0:
            reasons.append("Build-14 confidence downgrade requires a positive penalty")
        if not 0.0 < recommended_budget_factor < 1.0:
            reasons.append("Build-14 confidence downgrade requires a bounded budget factor")
        if requires_manual_review:
            reasons.append("Build-14 confidence downgrade must stay automated and bounded")
    if action in {"review_only", "soft_veto"}:
        if not requires_manual_review:
            reasons.append("Build-14 review_only and soft_veto must require manual review")
        if recommended_budget_factor != 0.0:
            reasons.append("Build-14 review_only and soft_veto must zero the budget factor")
    if action != "observe" and not reason_codes:
        reasons.append("limited Build-14 influence must expose reason_codes")

    return tuple(reasons)


def _shadow_portfolio_blocking_reasons(judgment) -> tuple[str, ...]:
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


def _shadow_engine_scope_blocking_reasons(live_light_input: LiveLightInput) -> tuple[str, ...]:
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


def _micro_live_surface_blocking_reasons(live_light_input: LiveLightInput) -> tuple[str, ...]:
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


def _live_surface_budget_blocking_reasons(live_light_input: LiveLightInput) -> tuple[str, ...]:
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


def _rollout_temporal_blocking_reasons(live_light_input: LiveLightInput) -> tuple[str, ...]:
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


def _governance_envelope_blocking_reasons(live_light_input: LiveLightInput) -> tuple[str, ...]:
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


def build_live_light_input_from_micro_live(
    micro_live_summary: MicroLiveRunSummary,
    micro_live_payload: TechnicalDashboardPayload,
    *,
    live_pairs: tuple[str, ...],
    requested_total_notional_usdt: float,
    requested_pair_notional_usdt: float,
    max_total_notional_usdt: float,
    max_pair_notional_usdt: float,
    execution_order_limit: int = 3,
    active_engines: tuple[str, ...] | None = None,
    shadow_days_completed: int | None = None,
    shadow_required_days: int | None = None,
    component_verdicts_rendered: bool | None = None,
    shadow_report_ready: bool | None = None,
    micro_live_stable_days: int,
    micro_live_required_days: int = 7,
    build14_live_eligible: bool = False,
    observability_ready: bool = False,
    halt_ready: bool = False,
    operator_safing_request=None,
    execution_ready: bool = False,
    broker_ready: bool = False,
    exchange_ready: bool = False,
    onboarding_accepted: bool = False,
    onboarding_review_state: ReviewState = ReviewState.PENDING,
    onboarding_reasons: tuple[str, ...] = (),
) -> LiveLightInput:
    """Build a governed Build-13 input from Build-12 Micro-live outputs."""

    _validate_micro_live_source_payload_scope(micro_live_payload)
    _validate_micro_live_consistency(micro_live_summary, micro_live_payload)
    resolved_active_engines = active_engines or micro_live_summary.execution_plan.planned_engines
    shadow_projection = micro_live_payload.shadow
    resolved_shadow_days_completed = (
        shadow_projection.shadow_days_completed
        if shadow_days_completed is None
        else shadow_days_completed
    )
    resolved_shadow_required_days = (
        shadow_projection.shadow_required_days
        if shadow_required_days is None
        else shadow_required_days
    )
    resolved_shadow_report_ready = (
        shadow_projection.shadow_report_ready
        if shadow_report_ready is None
        else shadow_report_ready
    )
    resolved_component_verdicts_rendered = (
        (
            shadow_projection.shadow_validated_component_count
            + shadow_projection.dormant_component_count
        )
        > 0
        if component_verdicts_rendered is None
        else component_verdicts_rendered
    )
    _validate_live_light_surface(
        micro_live_summary,
        live_pairs=live_pairs,
        active_engines=resolved_active_engines,
    )
    return LiveLightInput(
        correlation_id=micro_live_summary.correlation_id,
        profile=micro_live_payload.profile,
        runtime_mode=RuntimeMode.LIVE,
        micro_live_run_id=micro_live_summary.run_id,
        shadow_run_id=micro_live_summary.shadow_run_id,
        micro_live_verdict=micro_live_summary.decision.verdict,
        micro_live_run_state=micro_live_summary.run_state,
        micro_live_blocking_reasons=micro_live_summary.decision.blocking_reasons,
        shadow_days_completed=resolved_shadow_days_completed,
        shadow_required_days=resolved_shadow_required_days,
        component_verdicts_rendered=resolved_component_verdicts_rendered,
        shadow_report_ready=resolved_shadow_report_ready,
        shadow_promotable_engines=micro_live_summary.shadow_promotable_engines,
        shadow_shadow_only_engines=micro_live_summary.shadow_shadow_only_engines,
        shadow_rewrite_required_engines=micro_live_summary.shadow_rewrite_required_engines,
        shadow_portfolio_judgment=micro_live_summary.shadow_portfolio_judgment,
        micro_live_planned_engines=micro_live_summary.execution_plan.planned_engines,
        micro_live_planned_pairs=micro_live_summary.execution_plan.planned_pairs,
        micro_live_stable_days=micro_live_stable_days,
        micro_live_required_days=micro_live_required_days,
        build14_live_eligible=build14_live_eligible,
        micro_live_import_artifact_id=micro_live_summary.import_artifact_id,
        micro_live_import_lineage_version=micro_live_summary.import_lineage_version,
        import_artifact_id=micro_live_payload.replay_import.artifact_id,
        import_exported_from=micro_live_payload.replay_import.exported_from,
        import_lineage_version=micro_live_payload.replay_import.lineage_version,
        import_validation_status=micro_live_payload.replay_import.validation_status,
        import_source_profile=micro_live_payload.replay_import.source_profile,
        import_review_state=micro_live_payload.replay_import.review_state,
        import_rejection_reasons=micro_live_payload.replay_import.rejection_reasons,
        import_dataset_ref=micro_live_payload.replay_import.dataset_ref,
        import_clock_ref=micro_live_payload.replay_import.clock_ref,
        import_activation_stage=micro_live_payload.replay_import.activation_stage,
        import_health_state=micro_live_payload.replay_import.health_state,
        import_compatibility_status=micro_live_payload.replay_import.compatibility_status,
        import_compatibility_reasons=micro_live_payload.replay_import.compatibility_reasons,
        import_feature_lineage_required=(
            micro_live_payload.replay_import.feature_lineage_required
        ),
        import_feature_lineage_present=(
            micro_live_payload.replay_import.feature_lineage_present
        ),
        import_feature_lineage_status=(
            micro_live_payload.replay_import.feature_lineage_status
        ),
        import_feature_lineage_reasons=(
            micro_live_payload.replay_import.feature_lineage_reasons
        ),
        import_transform_whitelist_required=(
            micro_live_payload.replay_import.transform_whitelist_required
        ),
        import_transform_whitelist_present=(
            micro_live_payload.replay_import.transform_whitelist_present
        ),
        import_transform_whitelist_status=(
            micro_live_payload.replay_import.transform_whitelist_status
        ),
        import_transform_whitelist_reasons=(
            micro_live_payload.replay_import.transform_whitelist_reasons
        ),
        import_signature_check_status=micro_live_payload.replay_import.signature_check_status,
        import_signature_check_reasons=micro_live_payload.replay_import.signature_check_reasons,
        import_conflict_resolution_mode=micro_live_payload.replay_import.conflict_resolution_mode,
        import_conflict_hard_veto_action=micro_live_payload.replay_import.conflict_hard_veto_action,
        import_conflict_score_aggregation_mode=(
            micro_live_payload.replay_import.conflict_score_aggregation_mode
        ),
        import_conflict_size_reduce_mode=micro_live_payload.replay_import.conflict_size_reduce_mode,
        import_conflict_rank_adjust_mode=micro_live_payload.replay_import.conflict_rank_adjust_mode,
        import_conflict_additive_soft_boosts_allowed=(
            micro_live_payload.replay_import.conflict_additive_soft_boosts_allowed
        ),
        import_conflict_additive_soft_reduces_allowed=(
            micro_live_payload.replay_import.conflict_additive_soft_reduces_allowed
        ),
        import_registry_atomicity_mode=micro_live_payload.replay_import.registry_atomicity_mode,
        import_registry_concurrency_model=micro_live_payload.replay_import.registry_concurrency_model,
        import_registry_publish_requires_atomic_replace=(
            micro_live_payload.replay_import.registry_publish_requires_atomic_replace
        ),
        import_registry_publish_requires_fsync=(
            micro_live_payload.replay_import.registry_publish_requires_fsync
        ),
        import_registry_rollback_to_last_known_good=(
            micro_live_payload.replay_import.registry_rollback_to_last_known_good
        ),
        import_payload_ref_count=micro_live_payload.replay_import.payload_ref_count,
        import_payload_bundle_present=micro_live_payload.replay_import.payload_bundle_present,
        import_review_export_ref=micro_live_payload.replay_import.review_export_ref,
        import_feature_bridge_ref=micro_live_payload.replay_import.feature_bridge_ref,
        import_parity_diagnostics_ref=micro_live_payload.replay_import.parity_diagnostics_ref,
        import_replay_metrics_ref=micro_live_payload.replay_import.replay_metrics_ref,
        import_replay_dtr_ref=micro_live_payload.replay_import.replay_dtr_ref,
        onboarding_accepted=onboarding_accepted,
        onboarding_review_state=onboarding_review_state,
        onboarding_reasons=onboarding_reasons,
        review_export_ready=micro_live_payload.shadow.review_export_ready,
        execution_runtime_projection_ref=(
            micro_live_summary.execution_runtime_projection_ref
        ),
        execution_runtime_projection_status=(
            micro_live_summary.execution_runtime_projection_status
        ),
        execution_runtime_projection_ready=(
            micro_live_summary.execution_runtime_projection_ready
        ),
        execution_runtime_projection_consumer_count=(
            micro_live_summary.execution_runtime_projection_consumer_count
        ),
        execution_runtime_projection_ready_consumer_count=(
            micro_live_summary.execution_runtime_projection_ready_consumer_count
        ),
        execution_runtime_projection_partial_consumer_count=(
            micro_live_summary.execution_runtime_projection_partial_consumer_count
        ),
        execution_runtime_projection_blocked_consumer_count=(
            micro_live_summary.execution_runtime_projection_blocked_consumer_count
        ),
        regime_lite_governance=micro_live_summary.regime_lite_governance,
        info_stress_governance=micro_live_summary.info_stress_governance,
        observability_ready=observability_ready,
        halt_ready=halt_ready,
        operator_safing_request=operator_safing_request,
        execution_ready=execution_ready,
        broker_ready=broker_ready,
        exchange_ready=exchange_ready,
        active_engines=resolved_active_engines,
        live_pairs=live_pairs,
        requested_total_notional_usdt=requested_total_notional_usdt,
        requested_pair_notional_usdt=requested_pair_notional_usdt,
        max_total_notional_usdt=max_total_notional_usdt,
        max_pair_notional_usdt=max_pair_notional_usdt,
        execution_order_limit=execution_order_limit,
    )


def run_live_light_gate(
    live_light_input: LiveLightInput,
    *,
    run_id: str | None = None,
    build14_influence: object | None = None,
    shadow_state_dir: Path | None = None,
) -> LiveLightRunSummary:
    """Run the minimal Build-13 gate without opening Complete or full live execution.

    HARD STATEMENT §0.6: if shadow_state_dir is provided, verifies 30 consecutive
    shadow days before allowing Live-Light promotion.
    """

    hard_blocking_reasons: list[str] = []
    hard_blocking_reasons.extend(_governance_envelope_blocking_reasons(live_light_input))

    # HARD STATEMENT §0.6: 30j shadow prerequisite
    if shadow_state_dir is not None:
        from protocols.shadow_runtime import check_shadow_30j_gate
        gate_passed, report = check_shadow_30j_gate(
            shadow_state_dir,
            profile=live_light_input.profile.value,
        )
        if not gate_passed:
            days = report.get("consecutive_days", 0)
            hard_blocking_reasons.append(
                f"HARD STATEMENT: {live_light_input.profile.value} shadow requires 30 consecutive days, "
                f"currently at {days}/30"
            )
    micro_live_needs_review = False
    build14_requires_review = False
    normalized_import_status = live_light_input.import_validation_status.strip().casefold()
    build14_signal, build14_validation_reasons = _resolve_validated_build14_signal(
        build14_influence,
        expected_correlation_id=live_light_input.correlation_id,
    )
    build14_influence_mode = _normalized_value(
        getattr(build14_signal, "influence_mode", None),
        "read_only",
    )
    build14_action = _normalized_value(
        getattr(build14_signal, "action", None),
        "observe",
    )
    build14_severity = _normalized_value(
        getattr(build14_signal, "severity", None),
        "nominal",
    )
    build14_summary = str(getattr(build14_signal, "summary", "")) if build14_signal is not None else ""
    build14_reason_codes = _build14_reason_codes(build14_signal)
    confidence_penalty_weight = 0.0
    recommended_budget_factor = 1.0
    build14_reason_lines: tuple[str, ...] = ()

    hard_blocking_reasons.extend(build14_validation_reasons)

    if build14_signal is not None and not live_light_input.build14_live_eligible:
        hard_blocking_reasons.append(
            "Build-14 live influence requires explicit post-Shadow live eligibility"
        )

    if live_light_input.micro_live_run_state != MicroLiveRunState.READY_TO_PROBE:
        hard_blocking_reasons.append(
            "Build-12 Micro-live run must be ready_to_probe before Live-Light"
        )
    if live_light_input.micro_live_verdict == MicroLiveVerdict.BLOCKED:
        hard_blocking_reasons.append(
            "Build-12 Micro-live is blocked and cannot open Live-Light"
        )
    elif live_light_input.micro_live_verdict == MicroLiveVerdict.DRY_RUN_ONLY:
        micro_live_needs_review = True

    if live_light_input.micro_live_blocking_reasons:
        hard_blocking_reasons.extend(
            f"micro-live gate: {reason}"
            for reason in live_light_input.micro_live_blocking_reasons
        )
    hard_blocking_reasons.extend(_rollout_temporal_blocking_reasons(live_light_input))
    hard_blocking_reasons.extend(_micro_live_surface_blocking_reasons(live_light_input))
    hard_blocking_reasons.extend(_live_surface_budget_blocking_reasons(live_light_input))
    hard_blocking_reasons.extend(_shadow_engine_scope_blocking_reasons(live_light_input))
    hard_blocking_reasons.extend(
        _shadow_portfolio_blocking_reasons(
            live_light_input.shadow_portfolio_judgment
        )
    )

    if normalized_import_status != "accepted":
        hard_blocking_reasons.append(
            "Build-13 Live-Light requires an accepted import_validation_status"
        )
    if live_light_input.import_exported_from != "local":
        hard_blocking_reasons.append(
            "Build-13 Live-Light requires import_exported_from=local"
        )
    if live_light_input.import_source_profile != "complete":
        hard_blocking_reasons.append(
            "Build-13 Live-Light requires import_source_profile=complete"
        )
    if live_light_input.import_rejection_reasons:
        hard_blocking_reasons.append(
            "Build-13 Live-Light requires empty import_rejection_reasons"
        )
    if live_light_input.import_review_state not in {"pending", "approved"}:
        hard_blocking_reasons.append(
            "Build-13 Live-Light requires import_review_state to stay pending or approved"
        )
    if not live_light_input.import_dataset_ref:
        hard_blocking_reasons.append(
            "Build-13 Live-Light requires import_dataset_ref"
        )
    if not live_light_input.import_clock_ref:
        hard_blocking_reasons.append(
            "Build-13 Live-Light requires import_clock_ref"
        )
    if live_light_input.import_activation_stage != "shadow_ready":
        hard_blocking_reasons.append(
            "Build-13 Live-Light requires import_activation_stage=shadow_ready"
        )
    if live_light_input.import_health_state != "active":
        hard_blocking_reasons.append(
            "Build-13 Live-Light requires import_health_state=active"
        )
    if live_light_input.import_compatibility_status == "rejected":
        hard_blocking_reasons.append(
            "Build-13 Live-Light requires a non-rejected import_compatibility_status"
        )
    hard_blocking_reasons.extend(
        f"import compatibility gate: {reason}"
        for reason in live_light_input.import_compatibility_reasons
    )
    if not live_light_input.import_feature_lineage_required:
        hard_blocking_reasons.append(
            "Build-13 Live-Light requires import_feature_lineage_required=True"
        )
    if not live_light_input.import_feature_lineage_present:
        hard_blocking_reasons.append(
            "Build-13 Live-Light requires import_feature_lineage_present=True"
        )
    if live_light_input.import_feature_lineage_status != "ok":
        hard_blocking_reasons.append(
            "Build-13 Live-Light requires import_feature_lineage_status=ok"
        )
    hard_blocking_reasons.extend(
        f"import feature lineage gate: {reason}"
        for reason in live_light_input.import_feature_lineage_reasons
    )
    if not live_light_input.import_transform_whitelist_required:
        hard_blocking_reasons.append(
            "Build-13 Live-Light requires import_transform_whitelist_required=True"
        )
    if not live_light_input.import_transform_whitelist_present:
        hard_blocking_reasons.append(
            "Build-13 Live-Light requires import_transform_whitelist_present=True"
        )
    if live_light_input.import_transform_whitelist_status != "ok":
        hard_blocking_reasons.append(
            "Build-13 Live-Light requires import_transform_whitelist_status=ok"
        )
    hard_blocking_reasons.extend(
        f"import transform whitelist gate: {reason}"
        for reason in live_light_input.import_transform_whitelist_reasons
    )
    if live_light_input.import_signature_check_status != "verified":
        # BS-40: allowlist — only "verified" passes
        hard_blocking_reasons.append(
            "Build-13 Live-Light requires a non-rejected import_signature_check_status"
        )
    hard_blocking_reasons.extend(
        f"import signature gate: {reason}"
        for reason in live_light_input.import_signature_check_reasons
    )
    if live_light_input.import_conflict_resolution_mode != "no_trade_then_strictest":
        hard_blocking_reasons.append(
            "Build-13 Live-Light requires canonical import_conflict_resolution_mode"
        )
    if live_light_input.import_conflict_hard_veto_action != "no_trade":
        hard_blocking_reasons.append(
            "Build-13 Live-Light requires canonical import_conflict_hard_veto_action"
        )
    if (
        live_light_input.import_conflict_score_aggregation_mode
        != "bounded_sum_with_global_cap"
    ):
        hard_blocking_reasons.append(
            "Build-13 Live-Light requires canonical import_conflict_score_aggregation_mode"
        )
    if live_light_input.import_conflict_size_reduce_mode != "min_factor_wins":
        hard_blocking_reasons.append(
            "Build-13 Live-Light requires canonical import_conflict_size_reduce_mode"
        )
    if live_light_input.import_conflict_rank_adjust_mode != "bounded_sum":
        hard_blocking_reasons.append(
            "Build-13 Live-Light requires canonical import_conflict_rank_adjust_mode"
        )
    if not live_light_input.import_conflict_additive_soft_boosts_allowed:
        hard_blocking_reasons.append(
            "Build-13 Live-Light requires import_conflict_additive_soft_boosts_allowed=True"
        )
    if not live_light_input.import_conflict_additive_soft_reduces_allowed:
        hard_blocking_reasons.append(
            "Build-13 Live-Light requires import_conflict_additive_soft_reduces_allowed=True"
        )
    if live_light_input.import_registry_atomicity_mode != "atomic_snapshot_swap":
        hard_blocking_reasons.append(
            "Build-13 Live-Light requires canonical import_registry_atomicity_mode"
        )
    if live_light_input.import_registry_concurrency_model != "single_writer_multi_reader":
        hard_blocking_reasons.append(
            "Build-13 Live-Light requires canonical import_registry_concurrency_model"
        )
    if not live_light_input.import_registry_publish_requires_atomic_replace:
        hard_blocking_reasons.append(
            "Build-13 Live-Light requires import_registry_publish_requires_atomic_replace=True"
        )
    if not live_light_input.import_registry_publish_requires_fsync:
        hard_blocking_reasons.append(
            "Build-13 Live-Light requires import_registry_publish_requires_fsync=True"
        )
    if not live_light_input.import_registry_rollback_to_last_known_good:
        hard_blocking_reasons.append(
            "Build-13 Live-Light requires import_registry_rollback_to_last_known_good=True"
        )
    if live_light_input.import_payload_ref_count < 5:
        hard_blocking_reasons.append(
            "Build-13 Live-Light requires import_payload_ref_count>=5"
        )
    if not live_light_input.import_payload_bundle_present:
        hard_blocking_reasons.append(
            "Build-13 Live-Light requires import_payload_bundle_present=True"
        )
    if not live_light_input.import_review_export_ref:
        hard_blocking_reasons.append(
            "Build-13 Live-Light requires import_review_export_ref"
        )
    if not live_light_input.import_feature_bridge_ref:
        hard_blocking_reasons.append(
            "Build-13 Live-Light requires import_feature_bridge_ref"
        )
    if not live_light_input.import_parity_diagnostics_ref:
        hard_blocking_reasons.append(
            "Build-13 Live-Light requires import_parity_diagnostics_ref"
        )
    if not live_light_input.import_replay_metrics_ref:
        hard_blocking_reasons.append(
            "Build-13 Live-Light requires import_replay_metrics_ref"
        )
    if not live_light_input.import_replay_dtr_ref:
        hard_blocking_reasons.append(
            "Build-13 Live-Light requires import_replay_dtr_ref"
        )
    if (
        live_light_input.micro_live_import_artifact_id
        != live_light_input.import_artifact_id
    ):
        hard_blocking_reasons.append(
            "Build-13 Live-Light requires matching Micro-live/import artifact_id"
        )
    if (
        live_light_input.micro_live_import_lineage_version
        != live_light_input.import_lineage_version
    ):
        hard_blocking_reasons.append(
            "Build-13 Live-Light requires matching Micro-live/import lineage_version"
        )

    if not live_light_input.onboarding_accepted:
        hard_blocking_reasons.append(
            "strategy onboarding must be accepted before Live-Light"
        )
    elif live_light_input.onboarding_review_state not in {
        ReviewState.PENDING,
        ReviewState.APPROVED,
    }:
        hard_blocking_reasons.append(
            "accepted onboarding must keep a pending or approved review_state"
        )
    if live_light_input.onboarding_reasons and live_light_input.onboarding_accepted:
        hard_blocking_reasons.append(
            "accepted onboarding must not carry rejection reasons"
        )
    if live_light_input.onboarding_review_state in {
        ReviewState.NEEDS_REVISION,
        ReviewState.REJECTED,
    }:
        hard_blocking_reasons.append(
            f"onboarding review_state={live_light_input.onboarding_review_state.value} is not eligible for Live-Light"
        )
    hard_blocking_reasons.extend(
        f"onboarding gate: {reason}" for reason in live_light_input.onboarding_reasons
    )

    if not live_light_input.review_export_ready:
        hard_blocking_reasons.append(
            "Build-11/9X review export must be ready before Live-Light execution"
        )
    if not live_light_input.observability_ready:
        hard_blocking_reasons.append(
            "Build-10 observability must be ready before Live-Light execution"
        )
    if not live_light_input.halt_ready:
        hard_blocking_reasons.append(
            "operator halt guard must be ready before Live-Light execution"
        )
    if live_light_input.operator_safing_request is not None:
        hard_blocking_reasons.append(
            _format_operator_safing_reason(live_light_input.operator_safing_request)
        )
    if not live_light_input.execution_ready:
        hard_blocking_reasons.append(
            "execution readiness must be confirmed before Live-Light execution"
        )
    if not live_light_input.broker_ready:
        hard_blocking_reasons.append(
            "broker readiness must be confirmed before Live-Light execution"
        )
    if not live_light_input.exchange_ready:
        hard_blocking_reasons.append(
            "exchange readiness must be confirmed before Live-Light execution"
        )

    if build14_signal is not None:
        hard_blocking_reasons.extend(_build14_guardrail_reasons(build14_signal))
        build14_reason_lines = tuple(
            f"build14 gate: {reason}" for reason in build14_reason_codes
        )
        if build14_action == "downgrade_confidence":
            confidence_penalty_weight = float(
                getattr(build14_signal, "confidence_penalty_weight", 0.0)
            )
            recommended_budget_factor = float(
                getattr(build14_signal, "recommended_budget_factor", 1.0)
            )
        elif build14_action in {"review_only", "soft_veto"}:
            build14_requires_review = True
            confidence_penalty_weight = float(
                getattr(build14_signal, "confidence_penalty_weight", 0.0)
            )
            recommended_budget_factor = float(
                getattr(build14_signal, "recommended_budget_factor", 1.0)
            )

    if hard_blocking_reasons:
        combined_reasons = tuple(hard_blocking_reasons) + build14_reason_lines
        decision = LiveLightDecision(
            allowed_to_execute_small=False,
            verdict=LiveLightVerdict.BLOCKED,
            normalized_promotion_state=PromotionState.MICRO_LIVE_CANDIDATE,
            review_state=ReviewState.NEEDS_REVISION,
            approved_total_notional_usdt=0.0,
            approved_pair_notional_usdt=0.0,
            blocking_reasons=combined_reasons,
            manual_review_required=True,
        )
        execution_intent = LiveLightExecutionIntent(
            intent_id=run_id or f"{live_light_input.correlation_id}:live_light_intent",
            import_artifact_id=live_light_input.import_artifact_id,
            import_lineage_version=live_light_input.import_lineage_version,
            planned_engines=(),
            planned_pairs=(),
            requested_total_notional_usdt=live_light_input.requested_total_notional_usdt,
            approved_total_notional_usdt=0.0,
            approved_pair_notional_usdt=0.0,
            execution_order_limit=0,
            dry_run_only=False,
            halt_guard_required=True,
            broker_ready_required=True,
            exchange_ready_required=True,
        )
        run_state = LiveLightRunState.BLOCKED
    elif micro_live_needs_review or build14_requires_review:
        review_reasons = []
        if micro_live_needs_review:
            review_reasons.append(
                "Build-12 Micro-live verdict must be allowed_to_probe before Live-Light can execute small size"
            )
        if build14_signal is not None and build14_requires_review:
            review_reasons.append(build14_summary)
            review_reasons.extend(build14_reason_lines)
        decision = LiveLightDecision(
            allowed_to_execute_small=False,
            verdict=LiveLightVerdict.DRY_RUN_ONLY,
            normalized_promotion_state=PromotionState.MICRO_LIVE_CANDIDATE,
            review_state=ReviewState.NEEDS_REVISION,
            approved_total_notional_usdt=0.0,
            approved_pair_notional_usdt=0.0,
            blocking_reasons=tuple(review_reasons),
            manual_review_required=True,
        )
        execution_intent = LiveLightExecutionIntent(
            intent_id=run_id or f"{live_light_input.correlation_id}:live_light_intent",
            import_artifact_id=live_light_input.import_artifact_id,
            import_lineage_version=live_light_input.import_lineage_version,
            planned_engines=live_light_input.active_engines,
            planned_pairs=live_light_input.live_pairs,
            requested_total_notional_usdt=live_light_input.requested_total_notional_usdt,
            approved_total_notional_usdt=0.0,
            approved_pair_notional_usdt=0.0,
            execution_order_limit=live_light_input.execution_order_limit,
            dry_run_only=True,
            halt_guard_required=True,
            broker_ready_required=True,
            exchange_ready_required=True,
        )
        run_state = LiveLightRunState.PREPARED
    else:
        approved_total = round(
            live_light_input.requested_total_notional_usdt * recommended_budget_factor,
            8,
        )
        approved_pair = round(
            live_light_input.requested_pair_notional_usdt * recommended_budget_factor,
            8,
        )
        decision = LiveLightDecision(
            allowed_to_execute_small=True,
            verdict=LiveLightVerdict.ALLOWED_TO_EXECUTE_SMALL,
            normalized_promotion_state=PromotionState.LIVE_CANDIDATE,
            review_state=ReviewState.PENDING,
            approved_total_notional_usdt=approved_total,
            approved_pair_notional_usdt=approved_pair,
            blocking_reasons=(),
            manual_review_required=False,
        )
        execution_intent = LiveLightExecutionIntent(
            intent_id=run_id or f"{live_light_input.correlation_id}:live_light_intent",
            import_artifact_id=live_light_input.import_artifact_id,
            import_lineage_version=live_light_input.import_lineage_version,
            planned_engines=live_light_input.active_engines,
            planned_pairs=live_light_input.live_pairs,
            requested_total_notional_usdt=live_light_input.requested_total_notional_usdt,
            approved_total_notional_usdt=approved_total,
            approved_pair_notional_usdt=approved_pair,
            execution_order_limit=live_light_input.execution_order_limit,
            dry_run_only=False,
            halt_guard_required=True,
            broker_ready_required=True,
            exchange_ready_required=True,
        )
        run_state = LiveLightRunState.READY_TO_EXECUTE_SMALL

    return LiveLightRunSummary(
        run_id=run_id or f"{live_light_input.correlation_id}:live_light_run",
        correlation_id=live_light_input.correlation_id,
        run_state=run_state,
        micro_live_run_id=live_light_input.micro_live_run_id,
        shadow_run_id=live_light_input.shadow_run_id,
        micro_live_verdict=live_light_input.micro_live_verdict,
        decision=decision,
        execution_intent=execution_intent,
        import_artifact_id=live_light_input.import_artifact_id,
        import_lineage_version=live_light_input.import_lineage_version,
        execution_runtime_projection_ref=(
            live_light_input.execution_runtime_projection_ref
        ),
        execution_runtime_projection_status=(
            live_light_input.execution_runtime_projection_status
        ),
        execution_runtime_projection_ready=(
            live_light_input.execution_runtime_projection_ready
        ),
        execution_runtime_projection_consumer_count=(
            live_light_input.execution_runtime_projection_consumer_count
        ),
        execution_runtime_projection_ready_consumer_count=(
            live_light_input.execution_runtime_projection_ready_consumer_count
        ),
        execution_runtime_projection_partial_consumer_count=(
            live_light_input.execution_runtime_projection_partial_consumer_count
        ),
        execution_runtime_projection_blocked_consumer_count=(
            live_light_input.execution_runtime_projection_blocked_consumer_count
        ),
        regime_lite_governance=live_light_input.regime_lite_governance,
        info_stress_governance=live_light_input.info_stress_governance,
        observability_ready=live_light_input.observability_ready,
        halt_ready=live_light_input.halt_ready,
        operator_safing_request=live_light_input.operator_safing_request,
        execution_ready=live_light_input.execution_ready,
        broker_ready=live_light_input.broker_ready,
        exchange_ready=live_light_input.exchange_ready,
        onboarding_ready=live_light_input.onboarding_accepted,
        build14_influence_mode=build14_influence_mode,
        build14_action=build14_action,
        build14_severity=build14_severity,
        build14_summary=build14_summary,
        build14_reason_codes=build14_reason_codes,
        build14_confidence_penalty_weight=confidence_penalty_weight,
        build14_recommended_budget_factor=recommended_budget_factor,
        build14_live_eligible=live_light_input.build14_live_eligible,
        shadow_portfolio_judgment=live_light_input.shadow_portfolio_judgment,
    )


__all__ = [
    "build_live_input_from_micro_live",
    "run_live_gate",
    "build_live_light_input_from_micro_live",
    "run_live_light_gate",
]


build_live_input_from_micro_live = build_live_light_input_from_micro_live
run_live_gate = run_live_light_gate
