"""Validation helpers for the governed Build-13 Live-Light runtime."""

from __future__ import annotations

from pydantic import ValidationError

from interface_contracts import (
    Build14InfluenceReport,
    Build14InfluenceSignal,
    ProfileId,
    RuntimeMode,
)
from monitoring import TechnicalDashboardPayload
from protocols.contracts import MicroLiveRunSummary
from protocols.errors import LiveLightInputError

Build14InfluenceContract = Build14InfluenceSignal | Build14InfluenceReport


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


def _validate_micro_live_summary_alignment(
    micro_live_summary: MicroLiveRunSummary,
    micro_live_payload: TechnicalDashboardPayload,
) -> None:
    replay_import = micro_live_payload.replay_import
    projection = micro_live_payload.micro_live
    if micro_live_summary.correlation_id != micro_live_payload.correlation_id:
        raise LiveLightInputError(
            "Build-13 Live-Light requires matching correlation_id between Micro-live summary and payload"
        )
    if (
        projection.run_state not in {"", "not_run"}
        and projection.run_state != micro_live_summary.run_state.value
    ):
        raise LiveLightInputError(
            "Build-13 Live-Light requires matching Micro-live run_state between summary and payload"
        )
    if (
        projection.verdict not in {"", "not_run"}
        and projection.verdict != micro_live_summary.decision.verdict.value
    ):
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
    if (
        projection.import_artifact_id not in {"", "none"}
        and projection.import_artifact_id != micro_live_summary.import_artifact_id
    ):
        raise LiveLightInputError(
            "Build-13 Live-Light requires matching Micro-live/import artifact_id"
        )
    if (
        projection.import_lineage_version not in {"", "n/a"}
        and projection.import_lineage_version != micro_live_summary.import_lineage_version
    ):
        raise LiveLightInputError(
            "Build-13 Live-Light requires matching Micro-live/import lineage_version"
        )
    if not replay_import.dataset_ref:
        raise LiveLightInputError(
            "Build-13 Live-Light requires replay import_dataset_ref"
        )
    if not replay_import.clock_ref:
        raise LiveLightInputError(
            "Build-13 Live-Light requires replay import_clock_ref"
        )


def _validate_micro_live_import_status(replay_import: object) -> None:
    normalized_status = replay_import.validation_status.strip().casefold()
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


def _validate_micro_live_feature_surface(replay_import: object) -> None:
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
        raise LiveLightInputError(
            "Build-13 Live-Light requires a non-rejected replay import_signature_check_status"
        )


def _validate_micro_live_import_conflicts(replay_import: object) -> None:
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


def _validate_micro_live_import_artifacts(
    micro_live_summary: MicroLiveRunSummary,
    replay_import: object,
) -> None:
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


def _validate_micro_live_consistency(
    micro_live_summary: MicroLiveRunSummary,
    micro_live_payload: TechnicalDashboardPayload,
) -> None:
    replay_import = micro_live_payload.replay_import
    _validate_micro_live_summary_alignment(micro_live_summary, micro_live_payload)
    _validate_micro_live_import_status(replay_import)
    _validate_micro_live_feature_surface(replay_import)
    _validate_micro_live_import_conflicts(replay_import)
    _validate_micro_live_import_artifacts(micro_live_summary, replay_import)


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


__all__ = [
    "_normalized_value",
    "_resolve_validated_build14_signal",
    "_build14_reason_codes",
    "_validate_micro_live_source_payload_scope",
    "_validate_micro_live_consistency",
    "_validate_live_light_surface",
    "_build14_guardrail_reasons",
]
