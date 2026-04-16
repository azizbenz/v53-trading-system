"""Validation helpers for governed protocol contracts."""

from __future__ import annotations

from typing import TYPE_CHECKING

from interface_contracts import ALL_PAIRS

if TYPE_CHECKING:
    from interface_contracts import ReviewState
    from protocols.contracts import LiveLightInput, MicroLiveInput, ShadowValidationSet

def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)

def _validate_onboarding_acceptance(
    accepted: bool,
    review_state: "ReviewState",
    reasons: tuple[str, ...],
    *,
    accepted_onboarding_review_states: frozenset["ReviewState"],
) -> None:
    if not accepted:
        return
    _require(review_state in accepted_onboarding_review_states, "onboarding_accepted=True requires a pending or approved onboarding_review_state")
    _require(not reasons, "onboarding_accepted=True requires empty onboarding_reasons")

def _validate_common_import_requirements(
    value: "MicroLiveInput | LiveLightInput",
    *,
    label: str,
    accepted_import_statuses: frozenset[str],
    expected_import_source_profile: str,
    accepted_import_review_states: frozenset[str],
    rejected_import_compatibility_statuses: frozenset[str],
    rejected_import_signature_statuses: frozenset[str],
    expected_import_conflict_resolution_mode: str,
    expected_import_conflict_hard_veto_action: str,
    expected_import_conflict_score_aggregation_mode: str,
    expected_import_conflict_size_reduce_mode: str,
    expected_import_conflict_rank_adjust_mode: str,
) -> None:
    normalized_status = value.import_validation_status.strip().casefold()
    _require(normalized_status in accepted_import_statuses, f"{label} requires an accepted import_validation_status")
    _require(value.import_exported_from == "local", f"{label} requires import_exported_from=local")
    _require(value.import_source_profile == expected_import_source_profile, f"{label} requires import_source_profile=complete")
    _require(not value.import_rejection_reasons, f"{label} requires empty import_rejection_reasons")
    _require(
        value.import_review_state in accepted_import_review_states,
        f"{label} requires import_review_state to stay pending or approved",
    )
    _require(bool(value.import_dataset_ref), f"{label} requires import_dataset_ref")
    _require(bool(value.import_clock_ref), f"{label} requires import_clock_ref")
    _require(value.import_activation_stage == "shadow_ready", f"{label} requires import_activation_stage=shadow_ready")
    _require(value.import_health_state == "active", f"{label} requires import_health_state=active")
    _require(
        value.import_compatibility_status not in rejected_import_compatibility_statuses,
        f"{label} requires a non-rejected import_compatibility_status",
    )
    _require(value.import_feature_lineage_required, f"{label} requires import_feature_lineage_required=True")
    _require(value.import_feature_lineage_present, f"{label} requires import_feature_lineage_present=True")
    _require(value.import_feature_lineage_status == "ok", f"{label} requires import_feature_lineage_status=ok")
    _require(
        value.import_transform_whitelist_required,
        f"{label} requires import_transform_whitelist_required=True",
    )
    _require(
        value.import_transform_whitelist_present,
        f"{label} requires import_transform_whitelist_present=True",
    )
    _require(
        value.import_transform_whitelist_status == "ok",
        f"{label} requires import_transform_whitelist_status=ok",
    )
    _require(
        value.import_signature_check_status not in rejected_import_signature_statuses,
        f"{label} requires a non-rejected import_signature_check_status",
    )
    _require(
        value.import_conflict_resolution_mode
        == expected_import_conflict_resolution_mode,
        f"{label} requires canonical import_conflict_resolution_mode",
    )
    _require(
        value.import_conflict_hard_veto_action
        == expected_import_conflict_hard_veto_action,
        f"{label} requires canonical import_conflict_hard_veto_action",
    )
    _require(
        value.import_conflict_score_aggregation_mode
        == expected_import_conflict_score_aggregation_mode,
        f"{label} requires canonical import_conflict_score_aggregation_mode",
    )
    _require(
        value.import_conflict_size_reduce_mode
        == expected_import_conflict_size_reduce_mode,
        f"{label} requires canonical import_conflict_size_reduce_mode",
    )
    _require(
        value.import_conflict_rank_adjust_mode
        == expected_import_conflict_rank_adjust_mode,
        f"{label} requires canonical import_conflict_rank_adjust_mode",
    )


def _validate_common_import_envelope(
    value: "MicroLiveInput | LiveLightInput",
    *,
    label: str,
    expected_import_registry_atomicity_mode: str,
    expected_import_registry_concurrency_model: str,
) -> None:
    _require(
        value.import_conflict_additive_soft_boosts_allowed,
        f"{label} requires import_conflict_additive_soft_boosts_allowed=True",
    )
    _require(
        value.import_conflict_additive_soft_reduces_allowed,
        f"{label} requires import_conflict_additive_soft_reduces_allowed=True",
    )
    _require(
        value.import_registry_atomicity_mode
        == expected_import_registry_atomicity_mode,
        f"{label} requires canonical import_registry_atomicity_mode",
    )
    _require(
        value.import_registry_concurrency_model
        == expected_import_registry_concurrency_model,
        f"{label} requires canonical import_registry_concurrency_model",
    )
    _require(
        value.import_registry_publish_requires_atomic_replace,
        f"{label} requires import_registry_publish_requires_atomic_replace=True",
    )
    _require(
        value.import_registry_publish_requires_fsync,
        f"{label} requires import_registry_publish_requires_fsync=True",
    )
    _require(
        value.import_registry_rollback_to_last_known_good,
        f"{label} requires import_registry_rollback_to_last_known_good=True",
    )
    _require(
        value.import_payload_ref_count >= 5,
        f"{label} requires import_payload_ref_count>=5",
    )
    _require(
        value.import_payload_bundle_present,
        f"{label} requires import_payload_bundle_present=True",
    )
    _require(bool(value.import_review_export_ref), f"{label} requires import_review_export_ref")
    _require(bool(value.import_feature_bridge_ref), f"{label} requires import_feature_bridge_ref")
    _require(bool(value.import_parity_diagnostics_ref), f"{label} requires import_parity_diagnostics_ref")
    _require(bool(value.import_replay_metrics_ref), f"{label} requires import_replay_metrics_ref")
    _require(bool(value.import_replay_dtr_ref), f"{label} requires import_replay_dtr_ref")


def validate_shadow_validation_import_consistency(
    value: "ShadowValidationSet",
    *,
    accepted_import_statuses: frozenset[str],
    expected_import_source_profile: str,
    accepted_import_review_states: frozenset[str],
    rejected_import_compatibility_statuses: frozenset[str],
    rejected_import_signature_statuses: frozenset[str],
    expected_import_conflict_resolution_mode: str,
    expected_import_conflict_hard_veto_action: str,
    expected_import_conflict_score_aggregation_mode: str,
    expected_import_conflict_size_reduce_mode: str,
    expected_import_conflict_rank_adjust_mode: str,
    expected_import_registry_atomicity_mode: str,
    expected_import_registry_concurrency_model: str,
) -> None:
    normalized_status = value.import_validation_status.strip().casefold()
    if value.accepted_import:
        _require(
            normalized_status in accepted_import_statuses,
            "accepted_import=True requires an acceptance import_validation_status",
        )
        _require(
            not value.import_rejection_reasons,
            "accepted_import=True requires empty import_rejection_reasons",
        )
    _require(
        normalized_status not in accepted_import_statuses or value.accepted_import,
        "accepted import_validation_status requires accepted_import=True",
    )
    if value.accepted_import:
        _validate_shadow_accepted_import_contract(
            value,
            expected_import_source_profile=expected_import_source_profile,
            accepted_import_review_states=accepted_import_review_states,
            rejected_import_compatibility_statuses=rejected_import_compatibility_statuses,
            rejected_import_signature_statuses=rejected_import_signature_statuses,
            expected_import_conflict_resolution_mode=expected_import_conflict_resolution_mode,
            expected_import_conflict_hard_veto_action=expected_import_conflict_hard_veto_action,
            expected_import_conflict_score_aggregation_mode=expected_import_conflict_score_aggregation_mode,
            expected_import_conflict_size_reduce_mode=expected_import_conflict_size_reduce_mode,
            expected_import_conflict_rank_adjust_mode=expected_import_conflict_rank_adjust_mode,
            expected_import_registry_atomicity_mode=expected_import_registry_atomicity_mode,
            expected_import_registry_concurrency_model=expected_import_registry_concurrency_model,
        )
    _validate_shadow_runtime_constraints(value)


def _validate_shadow_accepted_import_contract(
    value: "ShadowValidationSet",
    *,
    expected_import_source_profile: str,
    accepted_import_review_states: frozenset[str],
    rejected_import_compatibility_statuses: frozenset[str],
    rejected_import_signature_statuses: frozenset[str],
    expected_import_conflict_resolution_mode: str,
    expected_import_conflict_hard_veto_action: str,
    expected_import_conflict_score_aggregation_mode: str,
    expected_import_conflict_size_reduce_mode: str,
    expected_import_conflict_rank_adjust_mode: str,
    expected_import_registry_atomicity_mode: str,
    expected_import_registry_concurrency_model: str,
) -> None:
    if value.accepted_import:
        _require(
            value.import_exported_from == "local",
            "accepted_import=True requires import_exported_from=local",
        )
        _require(
            value.import_source_profile == expected_import_source_profile,
            "accepted_import=True requires import_source_profile=complete",
        )
        _require(
            value.import_review_state in accepted_import_review_states,
            "accepted_import=True requires import_review_state to stay pending or approved",
        )
        _require(bool(value.import_dataset_ref), "accepted_import=True requires import_dataset_ref")
        _require(bool(value.import_clock_ref), "accepted_import=True requires import_clock_ref")
        _require(
            value.import_compatibility_status not in rejected_import_compatibility_statuses,
            "accepted_import=True requires a non-rejected import_compatibility_status",
        )
        _require(
            value.import_feature_lineage_required,
            "accepted_import=True requires import_feature_lineage_required=True",
        )
        _require(
            value.import_feature_lineage_present,
            "accepted_import=True requires import_feature_lineage_present=True",
        )
        _require(
            value.import_feature_lineage_status == "ok",
            "accepted_import=True requires import_feature_lineage_status=ok",
        )
        _require(
            value.import_transform_whitelist_required,
            "accepted_import=True requires import_transform_whitelist_required=True",
        )
        _require(
            value.import_transform_whitelist_present,
            "accepted_import=True requires import_transform_whitelist_present=True",
        )
        _require(
            value.import_transform_whitelist_status == "ok",
            "accepted_import=True requires import_transform_whitelist_status=ok",
        )
        _require(
            value.import_signature_check_status not in rejected_import_signature_statuses,
            "accepted_import=True requires a non-rejected import_signature_check_status",
        )
        _require(
            value.import_activation_stage == "shadow_ready",
            "accepted_import=True requires import_activation_stage=shadow_ready",
        )
        _require(
            value.import_health_state == "active",
            "accepted_import=True requires import_health_state=active",
        )
        _require(
            value.import_conflict_resolution_mode == expected_import_conflict_resolution_mode,
            "accepted_import=True requires canonical import_conflict_resolution_mode",
        )
        _require(
            value.import_conflict_hard_veto_action == expected_import_conflict_hard_veto_action,
            "accepted_import=True requires canonical import_conflict_hard_veto_action",
        )
        _require(
            value.import_conflict_score_aggregation_mode
            == expected_import_conflict_score_aggregation_mode,
            "accepted_import=True requires canonical import_conflict_score_aggregation_mode",
        )
        _require(
            value.import_conflict_size_reduce_mode == expected_import_conflict_size_reduce_mode,
            "accepted_import=True requires canonical import_conflict_size_reduce_mode",
        )
        _require(
            value.import_conflict_rank_adjust_mode == expected_import_conflict_rank_adjust_mode,
            "accepted_import=True requires canonical import_conflict_rank_adjust_mode",
        )
        _require(value.import_conflict_additive_soft_boosts_allowed, "accepted_import=True requires import_conflict_additive_soft_boosts_allowed=True")
        _require(value.import_conflict_additive_soft_reduces_allowed, "accepted_import=True requires import_conflict_additive_soft_reduces_allowed=True")
        _require(value.import_registry_atomicity_mode == expected_import_registry_atomicity_mode, "accepted_import=True requires canonical import_registry_atomicity_mode")
        _require(value.import_registry_concurrency_model == expected_import_registry_concurrency_model, "accepted_import=True requires canonical import_registry_concurrency_model")
        _require(value.import_registry_publish_requires_atomic_replace, "accepted_import=True requires import_registry_publish_requires_atomic_replace=True")
        _require(value.import_registry_publish_requires_fsync, "accepted_import=True requires import_registry_publish_requires_fsync=True")
        _require(value.import_registry_rollback_to_last_known_good, "accepted_import=True requires import_registry_rollback_to_last_known_good=True")
        _require(value.import_payload_ref_count >= 5, "accepted_import=True requires import_payload_ref_count>=5")
        _require(value.import_payload_bundle_present, "accepted_import=True requires import_payload_bundle_present=True")
        _require(bool(value.import_review_export_ref), "accepted_import=True requires import_review_export_ref")
        _require(bool(value.import_feature_bridge_ref), "accepted_import=True requires import_feature_bridge_ref")
        _require(bool(value.import_parity_diagnostics_ref), "accepted_import=True requires import_parity_diagnostics_ref")
        _require(bool(value.import_replay_metrics_ref), "accepted_import=True requires import_replay_metrics_ref")
        _require(bool(value.import_replay_dtr_ref), "accepted_import=True requires import_replay_dtr_ref")


def _validate_shadow_runtime_constraints(value: "ShadowValidationSet") -> None:
    _require(value.shadow_required_days == 30, "Build-11 Shadow requires shadow_required_days=30")
    _require(
        len(value.active_engines) == len(set(value.active_engines)),
        "Build-11 Shadow active_engines must be unique",
    )
    component_ids = tuple(assessment.component_id for assessment in value.component_assessments)
    _require(
        len(component_ids) == len(set(component_ids)),
        "Build-11 Shadow component assessments must be unique per component",
    )


def _validate_micro_live_stage(value: "MicroLiveInput") -> None:
    _require(value.profile.name == "COMPLETE", "Build-12 Micro-live opens in COMPLETE profile only")
    _require(value.runtime_mode.name == "MICRO_LIVE", "Build-12 Micro-live requires runtime_mode=MICRO_LIVE")
    _require(value.backtest_profile is None, "BACKTEST_PROFILE is forbidden in the unified V5.3")
    _require(not value.creates_profile_fork, "Local/VPS profile forks are forbidden")
    _require(
        not value.automatic_live_promotion_requested,
        "Micro-live must not request automatic promotion to LIVE",
    )
    _require(
        value.operator_safing_request is None
        or value.operator_safing_request.source_runtime_mode == value.runtime_mode,
        "Build-12 Micro-live operator_safing_request must match source_runtime_mode=MICRO_LIVE",
    )
    _require(value.shadow_required_days == 30, "Build-12 Micro-live requires shadow_required_days=30")
    _require(
        value.shadow_days_completed >= value.shadow_required_days,
        "Build-12 Micro-live requires a completed 30-day Shadow",
    )
    _require(value.shadow_report_ready, "Build-12 Micro-live requires shadow_report_ready=True")
    _require(
        value.inter_engine_comparison_ready,
        "Build-12 Micro-live requires inter_engine_comparison_ready=True",
    )
    _require(
        value.build14_contribution_ready,
        "Build-12 Micro-live requires build14_contribution_ready=True",
    )


def _validate_micro_live_engines(
    value: "MicroLiveInput",
    *,
    micro_live_allowed_engines: frozenset[str],
    accepted_onboarding_review_states: frozenset["ReviewState"],
) -> None:
    _require(value.shadow_import_artifact_id != "none", "Build-12 Micro-live requires a concrete shadow_import_artifact_id")
    _require(value.shadow_import_lineage_version != "n/a", "Build-12 Micro-live requires a concrete shadow_import_lineage_version")
    _require(value.import_artifact_id != "none", "Build-12 Micro-live requires a concrete import_artifact_id")
    _require(value.import_lineage_version != "n/a", "Build-12 Micro-live requires a concrete lineage_version")
    _require(
        value.shadow_import_artifact_id == value.import_artifact_id,
        "Build-12 Micro-live requires matching Shadow/import artifact_id",
    )
    _require(
        value.shadow_import_lineage_version == value.import_lineage_version,
        "Build-12 Micro-live requires matching Shadow/import lineage_version",
    )
    _validate_onboarding_acceptance(
        value.onboarding_accepted,
        value.onboarding_review_state,
        value.onboarding_reasons,
        accepted_onboarding_review_states=accepted_onboarding_review_states,
    )
    _require(bool(value.active_engines), "Build-12 Micro-live requires at least one governed engine")
    _require(
        not (set(value.active_engines) - micro_live_allowed_engines),
        "Build-12 Micro-live allows only governed engines from the Full Shadow perimeter",
    )
    _require(
        bool(value.shadow_validated_engines),
        "Build-12 Micro-live requires at least one SHADOW_VALIDATED engine",
    )
    _require(
        not (set(value.shadow_validated_engines) - micro_live_allowed_engines),
        "Build-12 Micro-live shadow_validated_engines must stay within the governed engine perimeter",
    )
    _require(
        set(value.active_engines).issubset(set(value.shadow_validated_engines)),
        "Build-12 Micro-live active_engines must be SHADOW_VALIDATED in Shadow",
    )
    if value.shadow_promotable_engines:
        _require(
            not (set(value.shadow_promotable_engines) - micro_live_allowed_engines),
            "Build-12 Micro-live shadow_promotable_engines must stay within the governed engine perimeter",
        )
        _require(
            set(value.active_engines).issubset(set(value.shadow_promotable_engines)),
            "Build-12 Micro-live active_engines must be PROMOTABLE in Shadow judgment",
        )
    else:
        _require(
            not (value.shadow_shadow_only_engines or value.shadow_rewrite_required_engines),
            "Build-12 Micro-live requires at least one PROMOTABLE engine in Shadow judgment",
        )
    _require(
        not (set(value.active_engines) & set(value.shadow_shadow_only_engines)),
        "Build-12 Micro-live must not activate engines marked SHADOW_ONLY in Shadow judgment",
    )
    _require(
        not (set(value.active_engines) & set(value.shadow_rewrite_required_engines)),
        "Build-12 Micro-live must not activate engines marked REWRITE_REQUIRED in Shadow judgment",
    )
    _require(
        not (set(value.active_engines) & set(value.shadow_dormant_components)),
        "Build-12 Micro-live must not activate components marked DORMANT in Shadow",
    )


def validate_micro_live_governance(
    value: "MicroLiveInput",
    *,
    accepted_import_statuses: frozenset[str],
    expected_import_source_profile: str,
    accepted_import_review_states: frozenset[str],
    accepted_onboarding_review_states: frozenset["ReviewState"],
    rejected_import_compatibility_statuses: frozenset[str],
    rejected_import_signature_statuses: frozenset[str],
    expected_import_conflict_resolution_mode: str,
    expected_import_conflict_hard_veto_action: str,
    expected_import_conflict_score_aggregation_mode: str,
    expected_import_conflict_size_reduce_mode: str,
    expected_import_conflict_rank_adjust_mode: str,
    expected_import_registry_atomicity_mode: str,
    expected_import_registry_concurrency_model: str,
    micro_live_allowed_engines: frozenset[str],
) -> None:
    _validate_micro_live_stage(value)
    _validate_common_import_requirements(
        value,
        label="Build-12 Micro-live",
        accepted_import_statuses=accepted_import_statuses,
        expected_import_source_profile=expected_import_source_profile,
        accepted_import_review_states=accepted_import_review_states,
        rejected_import_compatibility_statuses=rejected_import_compatibility_statuses,
        rejected_import_signature_statuses=rejected_import_signature_statuses,
        expected_import_conflict_resolution_mode=expected_import_conflict_resolution_mode,
        expected_import_conflict_hard_veto_action=expected_import_conflict_hard_veto_action,
        expected_import_conflict_score_aggregation_mode=expected_import_conflict_score_aggregation_mode,
        expected_import_conflict_size_reduce_mode=expected_import_conflict_size_reduce_mode,
        expected_import_conflict_rank_adjust_mode=expected_import_conflict_rank_adjust_mode,
    )
    _validate_common_import_envelope(
        value,
        label="Build-12 Micro-live",
        expected_import_registry_atomicity_mode=expected_import_registry_atomicity_mode,
        expected_import_registry_concurrency_model=expected_import_registry_concurrency_model,
    )
    _validate_micro_live_engines(
        value,
        micro_live_allowed_engines=micro_live_allowed_engines,
        accepted_onboarding_review_states=accepted_onboarding_review_states,
    )
    _require(bool(value.probe_pairs), "Build-12 Micro-live requires at least one probe pair")
    _require(
        len(value.probe_pairs) <= len(ALL_PAIRS),
        "Build-12 Micro-live must stay within the Complete pair scope",
    )
    _require(
        not tuple(pair for pair in value.probe_pairs if pair not in ALL_PAIRS),
        "Build-12 Micro-live probe_pairs must stay within the Complete pair scope",
    )
    _require(
        value.max_pair_notional_usdt <= value.max_total_notional_usdt,
        "Micro-live max_pair_notional_usdt must stay within total budget",
    )
    _require(
        value.requested_pair_notional_usdt <= value.requested_total_notional_usdt,
        "Micro-live requested_pair_notional_usdt must stay within total request",
    )
    _require(
        value.requested_total_notional_usdt <= value.max_total_notional_usdt,
        "Micro-live requested_total_notional_usdt exceeds max budget",
    )
    _require(
        value.requested_pair_notional_usdt <= value.max_pair_notional_usdt,
        "Micro-live requested_pair_notional_usdt exceeds max pair budget",
    )


def _validate_live_light_stage(value: "LiveLightInput") -> None:
    _require(value.profile.name == "COMPLETE", "Build-13 Live-Light opens in COMPLETE profile only")
    _require(value.runtime_mode.name == "LIVE", "Build-13 Live-Light requires runtime_mode=LIVE")
    _require(value.backtest_profile is None, "BACKTEST_PROFILE is forbidden in the unified V5.3")
    _require(not value.creates_profile_fork, "Local/VPS profile forks are forbidden")
    _require(
        not value.automatic_complete_promotion_requested,
        "Build-13 Live-Light must not request automatic promotion to Complete",
    )
    _require(
        value.operator_safing_request is None
        or value.operator_safing_request.source_runtime_mode == value.runtime_mode,
        "Build-13 Live-Light operator_safing_request must match source_runtime_mode=LIVE",
    )
    _require(value.shadow_required_days == 30, "Build-13 Live-Light requires shadow_required_days=30")
    _require(
        value.shadow_days_completed >= value.shadow_required_days,
        "Build-13 Live-Light requires a completed 30-day Shadow",
    )
    _require(
        value.component_verdicts_rendered,
        "Build-13 Live-Light requires rendered post-Shadow component verdicts",
    )
    _require(value.shadow_report_ready, "Build-13 Live-Light requires shadow_report_ready=True")
    _require(
        value.micro_live_required_days == 7,
        "Build-13 Live-Light requires micro_live_required_days=7",
    )
    _require(
        value.micro_live_stable_days >= value.micro_live_required_days,
        "Build-13 Live-Light requires 7 stable Micro-live days",
    )


def _validate_live_light_engines(
    value: "LiveLightInput",
    *,
    live_light_allowed_engines: frozenset[str],
    accepted_onboarding_review_states: frozenset["ReviewState"],
) -> None:
    _require(
        value.micro_live_import_artifact_id != "none",
        "Build-13 Live-Light requires a concrete micro_live_import_artifact_id",
    )
    _require(
        value.micro_live_import_lineage_version != "n/a",
        "Build-13 Live-Light requires a concrete micro_live_import_lineage_version",
    )
    _require(
        value.import_artifact_id != "none",
        "Build-13 Live-Light requires a concrete import_artifact_id",
    )
    _require(
        value.import_lineage_version != "n/a",
        "Build-13 Live-Light requires a concrete lineage_version",
    )
    _require(
        value.micro_live_import_artifact_id == value.import_artifact_id,
        "Build-13 Live-Light requires matching Micro-live/import artifact_id",
    )
    _require(
        value.micro_live_import_lineage_version == value.import_lineage_version,
        "Build-13 Live-Light requires matching Micro-live/import lineage_version",
    )
    _validate_onboarding_acceptance(
        value.onboarding_accepted,
        value.onboarding_review_state,
        value.onboarding_reasons,
        accepted_onboarding_review_states=accepted_onboarding_review_states,
    )
    _require(bool(value.active_engines), "Build-13 Live-Light requires at least one governed engine")
    _require(
        not (set(value.active_engines) - live_light_allowed_engines),
        "Build-13 Live-Light allows only governed engines from the Full Shadow perimeter",
    )
    if value.shadow_promotable_engines:
        _require(
            not (set(value.shadow_promotable_engines) - live_light_allowed_engines),
            "Build-13 Live-Light shadow_promotable_engines must stay within the governed engine perimeter",
        )
        _require(
            set(value.active_engines).issubset(set(value.shadow_promotable_engines)),
            "Build-13 Live-Light active_engines must be PROMOTABLE in Shadow judgment",
        )
    else:
        _require(
            not (value.shadow_shadow_only_engines or value.shadow_rewrite_required_engines),
            "Build-13 Live-Light requires at least one PROMOTABLE engine in Shadow judgment",
        )
    _require(
        not (set(value.active_engines) & set(value.shadow_shadow_only_engines)),
        "Build-13 Live-Light must not activate engines marked SHADOW_ONLY in Shadow judgment",
    )
    _require(
        not (set(value.active_engines) & set(value.shadow_rewrite_required_engines)),
        "Build-13 Live-Light must not activate engines marked REWRITE_REQUIRED in Shadow judgment",
    )
    _require(
        bool(value.micro_live_planned_engines),
        "Build-13 Live-Light requires governed micro_live_planned_engines",
    )
    _require(
        not (set(value.micro_live_planned_engines) - live_light_allowed_engines),
        "Build-13 Live-Light micro_live_planned_engines must stay within the governed engine perimeter",
    )
    _require(
        set(value.active_engines).issubset(set(value.micro_live_planned_engines)),
        "Build-13 Live-Light active_engines must stay within the governed Micro-live planned_engines",
    )


def validate_live_light_governance(
    value: "LiveLightInput",
    *,
    accepted_import_statuses: frozenset[str],
    expected_import_source_profile: str,
    accepted_import_review_states: frozenset[str],
    accepted_onboarding_review_states: frozenset["ReviewState"],
    rejected_import_compatibility_statuses: frozenset[str],
    rejected_import_signature_statuses: frozenset[str],
    expected_import_conflict_resolution_mode: str,
    expected_import_conflict_hard_veto_action: str,
    expected_import_conflict_score_aggregation_mode: str,
    expected_import_conflict_size_reduce_mode: str,
    expected_import_conflict_rank_adjust_mode: str,
    expected_import_registry_atomicity_mode: str,
    expected_import_registry_concurrency_model: str,
    live_light_allowed_engines: frozenset[str],
) -> None:
    _validate_live_light_stage(value)
    _validate_common_import_requirements(
        value,
        label="Build-13 Live-Light",
        accepted_import_statuses=accepted_import_statuses,
        expected_import_source_profile=expected_import_source_profile,
        accepted_import_review_states=accepted_import_review_states,
        rejected_import_compatibility_statuses=rejected_import_compatibility_statuses,
        rejected_import_signature_statuses=rejected_import_signature_statuses,
        expected_import_conflict_resolution_mode=expected_import_conflict_resolution_mode,
        expected_import_conflict_hard_veto_action=expected_import_conflict_hard_veto_action,
        expected_import_conflict_score_aggregation_mode=expected_import_conflict_score_aggregation_mode,
        expected_import_conflict_size_reduce_mode=expected_import_conflict_size_reduce_mode,
        expected_import_conflict_rank_adjust_mode=expected_import_conflict_rank_adjust_mode,
    )
    _validate_common_import_envelope(
        value,
        label="Build-13 Live-Light",
        expected_import_registry_atomicity_mode=expected_import_registry_atomicity_mode,
        expected_import_registry_concurrency_model=expected_import_registry_concurrency_model,
    )
    _validate_live_light_engines(
        value,
        live_light_allowed_engines=live_light_allowed_engines,
        accepted_onboarding_review_states=accepted_onboarding_review_states,
    )
    _require(bool(value.live_pairs), "Build-13 Live-Light requires at least one live pair")
    _require(
        len(value.live_pairs) <= len(ALL_PAIRS),
        "Build-13 Live-Light must stay within the Complete pair scope",
    )
    _require(
        not tuple(pair for pair in value.live_pairs if pair not in ALL_PAIRS),
        "Build-13 Live-Light live_pairs must stay within the Complete pair scope",
    )
    _require(
        bool(value.micro_live_planned_pairs),
        "Build-13 Live-Light requires governed micro_live_planned_pairs",
    )
    _require(
        not tuple(pair for pair in value.micro_live_planned_pairs if pair not in ALL_PAIRS),
        "Build-13 Live-Light micro_live_planned_pairs must stay within the Complete pair scope",
    )
    _require(
        set(value.live_pairs).issubset(set(value.micro_live_planned_pairs)),
        "Build-13 Live-Light live_pairs must stay within the governed Micro-live planned_pairs",
    )
    _require(
        value.max_pair_notional_usdt <= value.max_total_notional_usdt,
        "Live-Light max_pair_notional_usdt must stay within total cap",
    )
    _require(
        value.requested_pair_notional_usdt <= value.requested_total_notional_usdt,
        "Live-Light requested_pair_notional_usdt must stay within total request",
    )
    _require(
        value.requested_total_notional_usdt <= value.max_total_notional_usdt,
        "Live-Light requested_total_notional_usdt exceeds max cap",
    )
    _require(
        value.requested_pair_notional_usdt <= value.max_pair_notional_usdt,
        "Live-Light requested_pair_notional_usdt exceeds max pair cap",
    )
