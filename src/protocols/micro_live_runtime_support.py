"""Validation helpers for the governed Build-12 Micro-live runtime."""

from __future__ import annotations

from dataclasses import dataclass

from interface_contracts import ALL_PAIRS, ProfileId, RuntimeMode
from monitoring import TechnicalDashboardPayload
from protocols.contracts import MicroLiveInput, ShadowPortfolioJudgment, ShadowRunSummary
from protocols.enums import ShadowComponentKind, ShadowComponentVerdict
from protocols.errors import MicroLiveInputError
from protocols.shadow_runtime import derive_shadow_portfolio_judgment

_SHADOW_ENGINE_IDS = frozenset({"engine_a", "engine_b", "engine_c", "engine_d"})


@dataclass(frozen=True)
class _ResolvedShadowScope:
    validated_engines: tuple[str, ...]
    dormant_components: tuple[str, ...]
    promotable_engines: tuple[str, ...]
    shadow_only_engines: tuple[str, ...]
    rewrite_required_engines: tuple[str, ...]
    portfolio_judgment: ShadowPortfolioJudgment
    active_engines: tuple[str, ...]


def _validate_shadow_source_payload_scope(payload: TechnicalDashboardPayload) -> None:
    if payload.profile != ProfileId.COMPLETE:
        raise MicroLiveInputError(
            "Build-12 Micro-live source payload must stay on profile=COMPLETE"
        )
    if payload.runtime_mode != RuntimeMode.SHADOW:
        raise MicroLiveInputError(
            "Build-12 Micro-live source payload must originate from runtime_mode=SHADOW"
        )


def _validate_shadow_import_status(replay_import: object) -> None:
    normalized_status = replay_import.validation_status.strip().casefold()
    if normalized_status != "accepted":
        raise MicroLiveInputError(
            "Build-12 Micro-live requires an accepted replay import_validation_status"
        )
    if replay_import.exported_from != "local":
        raise MicroLiveInputError(
            "Build-12 Micro-live requires replay import_exported_from=local"
        )
    if replay_import.source_profile != "complete":
        raise MicroLiveInputError(
            "Build-12 Micro-live requires replay import_source_profile=complete"
        )
    if replay_import.rejection_reasons:
        raise MicroLiveInputError(
            "Build-12 Micro-live requires empty replay import_rejection_reasons"
        )
    if replay_import.review_state not in {"pending", "approved"}:
        raise MicroLiveInputError(
            "Build-12 Micro-live requires replay import_review_state to stay pending or approved"
        )
    if not replay_import.dataset_ref:
        raise MicroLiveInputError(
            "Build-12 Micro-live requires replay import_dataset_ref"
        )
    if not replay_import.clock_ref:
        raise MicroLiveInputError(
            "Build-12 Micro-live requires replay import_clock_ref"
        )
    if replay_import.activation_stage != "shadow_ready":
        raise MicroLiveInputError(
            "Build-12 Micro-live requires replay import_activation_stage=shadow_ready"
        )
    if replay_import.health_state != "active":
        raise MicroLiveInputError(
            "Build-12 Micro-live requires replay import_health_state=active"
        )
    if replay_import.compatibility_status == "rejected":
        raise MicroLiveInputError(
            "Build-12 Micro-live requires a non-rejected replay import_compatibility_status"
        )


def _validate_shadow_feature_surface(replay_import: object) -> None:
    if not replay_import.feature_lineage_required:
        raise MicroLiveInputError(
            "Build-12 Micro-live requires replay import_feature_lineage_required=True"
        )
    if not replay_import.feature_lineage_present:
        raise MicroLiveInputError(
            "Build-12 Micro-live requires replay import_feature_lineage_present=True"
        )
    if replay_import.feature_lineage_status != "ok":
        raise MicroLiveInputError(
            "Build-12 Micro-live requires replay import_feature_lineage_status=ok"
        )
    if not replay_import.transform_whitelist_required:
        raise MicroLiveInputError(
            "Build-12 Micro-live requires replay import_transform_whitelist_required=True"
        )
    if not replay_import.transform_whitelist_present:
        raise MicroLiveInputError(
            "Build-12 Micro-live requires replay import_transform_whitelist_present=True"
        )
    if replay_import.transform_whitelist_status != "ok":
        raise MicroLiveInputError(
            "Build-12 Micro-live requires replay import_transform_whitelist_status=ok"
        )
    if replay_import.signature_check_status != "verified":
        raise MicroLiveInputError(
            "Build-12 Micro-live requires a non-rejected replay import_signature_check_status"
        )


def _validate_shadow_import_conflicts(replay_import: object) -> None:
    if replay_import.conflict_resolution_mode != "no_trade_then_strictest":
        raise MicroLiveInputError(
            "Build-12 Micro-live requires replay import_conflict_resolution_mode=no_trade_then_strictest"
        )
    if replay_import.conflict_hard_veto_action != "no_trade":
        raise MicroLiveInputError(
            "Build-12 Micro-live requires replay import_conflict_hard_veto_action=no_trade"
        )
    if replay_import.conflict_score_aggregation_mode != "bounded_sum_with_global_cap":
        raise MicroLiveInputError(
            "Build-12 Micro-live requires replay import_conflict_score_aggregation_mode=bounded_sum_with_global_cap"
        )
    if replay_import.conflict_size_reduce_mode != "min_factor_wins":
        raise MicroLiveInputError(
            "Build-12 Micro-live requires replay import_conflict_size_reduce_mode=min_factor_wins"
        )
    if replay_import.conflict_rank_adjust_mode != "bounded_sum":
        raise MicroLiveInputError(
            "Build-12 Micro-live requires replay import_conflict_rank_adjust_mode=bounded_sum"
        )
    if not replay_import.conflict_additive_soft_boosts_allowed:
        raise MicroLiveInputError(
            "Build-12 Micro-live requires replay import_conflict_additive_soft_boosts_allowed=True"
        )
    if not replay_import.conflict_additive_soft_reduces_allowed:
        raise MicroLiveInputError(
            "Build-12 Micro-live requires replay import_conflict_additive_soft_reduces_allowed=True"
        )
    if replay_import.registry_atomicity_mode != "atomic_snapshot_swap":
        raise MicroLiveInputError(
            "Build-12 Micro-live requires replay import_registry_atomicity_mode=atomic_snapshot_swap"
        )
    if replay_import.registry_concurrency_model != "single_writer_multi_reader":
        raise MicroLiveInputError(
            "Build-12 Micro-live requires replay import_registry_concurrency_model=single_writer_multi_reader"
        )
    if not replay_import.registry_publish_requires_atomic_replace:
        raise MicroLiveInputError(
            "Build-12 Micro-live requires replay import_registry_publish_requires_atomic_replace=True"
        )
    if not replay_import.registry_publish_requires_fsync:
        raise MicroLiveInputError(
            "Build-12 Micro-live requires replay import_registry_publish_requires_fsync=True"
        )
    if not replay_import.registry_rollback_to_last_known_good:
        raise MicroLiveInputError(
            "Build-12 Micro-live requires replay import_registry_rollback_to_last_known_good=True"
        )


def _validate_shadow_import_artifacts(
    shadow_summary: ShadowRunSummary,
    replay_import: object,
) -> None:
    if replay_import.payload_ref_count < 5:
        raise MicroLiveInputError(
            "Build-12 Micro-live requires replay import_payload_ref_count>=5"
        )
    if not replay_import.payload_bundle_present:
        raise MicroLiveInputError(
            "Build-12 Micro-live requires replay import_payload_bundle_present=True"
        )
    if not replay_import.review_export_ref:
        raise MicroLiveInputError(
            "Build-12 Micro-live requires replay import_review_export_ref"
        )
    if not replay_import.feature_bridge_ref:
        raise MicroLiveInputError(
            "Build-12 Micro-live requires replay import_feature_bridge_ref"
        )
    if not replay_import.parity_diagnostics_ref:
        raise MicroLiveInputError(
            "Build-12 Micro-live requires replay import_parity_diagnostics_ref"
        )
    if not replay_import.replay_metrics_ref:
        raise MicroLiveInputError(
            "Build-12 Micro-live requires replay import_replay_metrics_ref"
        )
    if not replay_import.replay_dtr_ref:
        raise MicroLiveInputError(
            "Build-12 Micro-live requires replay import_replay_dtr_ref"
        )
    if not replay_import.artifact_id or replay_import.artifact_id == "none":
        raise MicroLiveInputError(
            "Build-12 Micro-live requires a concrete replay import_artifact_id"
        )
    if not replay_import.lineage_version or replay_import.lineage_version == "n/a":
        raise MicroLiveInputError(
            "Build-12 Micro-live requires a concrete replay lineage_version"
        )
    if shadow_summary.import_artifact_id != replay_import.artifact_id:
        raise MicroLiveInputError(
            "Build-12 Micro-live requires matching Shadow/import artifact_id"
        )
    if shadow_summary.import_lineage_version != replay_import.lineage_version:
        raise MicroLiveInputError(
            "Build-12 Micro-live requires matching Shadow/import lineage_version"
        )


def _validate_shadow_import_consistency(
    shadow_summary: ShadowRunSummary,
    shadow_payload: TechnicalDashboardPayload,
) -> None:
    replay_import = shadow_payload.replay_import

    if shadow_summary.correlation_id != shadow_payload.correlation_id:
        raise MicroLiveInputError(
            "Build-12 Micro-live requires matching correlation_id between Shadow summary and payload"
        )
    _validate_shadow_import_status(replay_import)
    _validate_shadow_feature_surface(replay_import)
    _validate_shadow_import_conflicts(replay_import)
    _validate_shadow_import_artifacts(shadow_summary, replay_import)


def _resolve_shadow_component_verdicts(
    shadow_summary: ShadowRunSummary,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    if not shadow_summary.component_assessments:
        raise MicroLiveInputError(
            "Build-12 Micro-live requires component verdicts from the Build-11 Shadow report"
        )

    validated_light_engines = tuple(
        assessment.component_id
        for assessment in shadow_summary.component_assessments
        if assessment.component_kind == ShadowComponentKind.ENGINE
        and assessment.verdict == ShadowComponentVerdict.SHADOW_VALIDATED
    )
    dormant_components = tuple(
        assessment.component_id
        for assessment in shadow_summary.component_assessments
        if assessment.verdict == ShadowComponentVerdict.DORMANT
    )

    if not validated_light_engines:
        raise MicroLiveInputError(
            "Build-12 Micro-live requires at least one SHADOW_VALIDATED governed engine from Build-11"
        )

    return validated_light_engines, dormant_components


def _resolve_shadow_engine_judgment_scope(
    shadow_payload: TechnicalDashboardPayload,
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    cards = tuple(shadow_payload.engine_judgment.cards)
    if not cards:
        promotable_engines: list[str] = []
        shadow_only_engines: list[str] = []
        rewrite_required_engines: list[str] = []
        for engine in shadow_payload.engines:
            if engine.engine_id not in _SHADOW_ENGINE_IDS:
                continue
            if (
                engine.hard_blocked
                or engine.phantom_trade
                or engine.portfolio_verdict_code.startswith("rejected_")
                or engine.selection_outcome_code == "rejected_portfolio"
            ):
                rewrite_required_engines.append(engine.engine_id)
            elif (
                engine.selection_outcome_code == "rejected_ranking"
                or engine.risk_decision_severity == "critical"
                or engine.scoring_final_size_multiplier <= 0.1
            ):
                shadow_only_engines.append(engine.engine_id)
            else:
                promotable_engines.append(engine.engine_id)
        return (
            tuple(promotable_engines),
            tuple(shadow_only_engines),
            tuple(rewrite_required_engines),
        )

    promotable_engines = tuple(
        card.engine_id
        for card in cards
        if card.judgment_verdict == "promotable"
    )
    shadow_only_engines = tuple(
        card.engine_id
        for card in cards
        if card.judgment_verdict == "shadow-only"
    )
    rewrite_required_engines = tuple(
        card.engine_id
        for card in cards
        if card.judgment_verdict == "rewrite-required"
    )
    return promotable_engines, shadow_only_engines, rewrite_required_engines


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
    micro_live_input: MicroLiveInput,
) -> tuple[str, ...]:
    reasons: list[str] = []
    active_engines = set(micro_live_input.active_engines)
    shadow_validated_engines = set(micro_live_input.shadow_validated_engines)
    shadow_promotable_engines = set(micro_live_input.shadow_promotable_engines)
    shadow_shadow_only_engines = set(micro_live_input.shadow_shadow_only_engines)
    shadow_rewrite_required_engines = set(micro_live_input.shadow_rewrite_required_engines)
    shadow_dormant_components = set(micro_live_input.shadow_dormant_components)

    if not active_engines:
        reasons.append("Build-12 Micro-live requires at least one governed engine")
        return tuple(reasons)

    unknown_active_engines = active_engines - _SHADOW_ENGINE_IDS
    if unknown_active_engines:
        reasons.append(
            "Build-12 Micro-live allows only governed engines from the Full Shadow perimeter"
        )

    if not shadow_validated_engines:
        reasons.append("Build-12 Micro-live requires at least one SHADOW_VALIDATED engine")
    else:
        unknown_shadow_validated = shadow_validated_engines - _SHADOW_ENGINE_IDS
        if unknown_shadow_validated:
            reasons.append(
                "Build-12 Micro-live shadow_validated_engines must stay within the governed engine perimeter"
            )
        if not active_engines.issubset(shadow_validated_engines):
            reasons.append(
                "Build-12 Micro-live active_engines must be SHADOW_VALIDATED in Shadow"
            )

    if shadow_promotable_engines:
        unknown_shadow_promotable = shadow_promotable_engines - _SHADOW_ENGINE_IDS
        if unknown_shadow_promotable:
            reasons.append(
                "Build-12 Micro-live shadow_promotable_engines must stay within the governed engine perimeter"
            )
        if not active_engines.issubset(shadow_promotable_engines):
            reasons.append(
                "Build-12 Micro-live active_engines must be PROMOTABLE in Shadow judgment"
            )
    elif shadow_shadow_only_engines or shadow_rewrite_required_engines:
        reasons.append(
            "Build-12 Micro-live requires at least one PROMOTABLE engine in Shadow judgment"
        )

    if active_engines & shadow_shadow_only_engines:
        reasons.append(
            "Build-12 Micro-live must not activate engines marked SHADOW_ONLY in Shadow judgment"
        )
    if active_engines & shadow_rewrite_required_engines:
        reasons.append(
            "Build-12 Micro-live must not activate engines marked REWRITE_REQUIRED in Shadow judgment"
        )
    if active_engines & shadow_dormant_components:
        reasons.append(
            "Build-12 Micro-live must not activate components marked DORMANT in Shadow"
        )

    return tuple(reasons)


def _probe_surface_blocking_reasons(micro_live_input: MicroLiveInput) -> tuple[str, ...]:
    reasons: list[str] = []

    if not micro_live_input.probe_pairs:
        reasons.append("Build-12 Micro-live requires at least one probe pair")
    elif len(micro_live_input.probe_pairs) > len(ALL_PAIRS):
        reasons.append("Build-12 Micro-live must stay within the Complete pair scope")
    else:
        invalid_pairs = tuple(
            pair for pair in micro_live_input.probe_pairs if pair not in ALL_PAIRS
        )
        if invalid_pairs:
            reasons.append(
                "Build-12 Micro-live probe_pairs must stay within the Complete pair scope"
            )

    if micro_live_input.max_pair_notional_usdt > micro_live_input.max_total_notional_usdt:
        reasons.append("Micro-live max_pair_notional_usdt must stay within total budget")
    if (
        micro_live_input.requested_pair_notional_usdt
        > micro_live_input.requested_total_notional_usdt
    ):
        reasons.append(
            "Micro-live requested_pair_notional_usdt must stay within total request"
        )
    if (
        micro_live_input.requested_total_notional_usdt
        > micro_live_input.max_total_notional_usdt
    ):
        reasons.append("Micro-live requested_total_notional_usdt exceeds max budget")
    if (
        micro_live_input.requested_pair_notional_usdt
        > micro_live_input.max_pair_notional_usdt
    ):
        reasons.append("Micro-live requested_pair_notional_usdt exceeds max pair budget")
    if micro_live_input.order_probe_limit < 1 or micro_live_input.order_probe_limit > 10:
        reasons.append("Build-12 Micro-live requires order_probe_limit within [1, 10]")

    return tuple(reasons)


def _shadow_temporal_blocking_reasons(micro_live_input: MicroLiveInput) -> tuple[str, ...]:
    reasons: list[str] = []

    if micro_live_input.shadow_days_completed < micro_live_input.shadow_required_days:
        reasons.append("Build-12 Micro-live requires a completed 30-day Shadow")
    if not micro_live_input.shadow_report_ready:
        reasons.append("Build-12 Micro-live requires shadow_report_ready=True")
    if not micro_live_input.inter_engine_comparison_ready:
        reasons.append(
            "Build-12 Micro-live requires inter-engine A/B/C/D comparison evidence from Build-11"
        )
    if not micro_live_input.build14_contribution_ready:
        reasons.append(
            "Build-12 Micro-live requires Build-14 contribution evidence from Build-11"
        )

    return tuple(reasons)


def _governance_envelope_blocking_reasons(
    micro_live_input: MicroLiveInput,
) -> tuple[str, ...]:
    reasons: list[str] = []

    if not micro_live_input.correlation_id.strip():
        reasons.append("Build-12 Micro-live requires a concrete correlation_id")
    if micro_live_input.profile != ProfileId.COMPLETE:
        reasons.append("Build-12 Micro-live opens in COMPLETE profile only")
    if micro_live_input.runtime_mode != RuntimeMode.MICRO_LIVE:
        reasons.append("Build-12 Micro-live requires runtime_mode=MICRO_LIVE")
    if not micro_live_input.shadow_run_id.strip():
        reasons.append("Build-12 Micro-live requires a concrete shadow_run_id")
    if not micro_live_input.shadow_truth_set_ref.strip():
        reasons.append("Build-12 Micro-live requires a concrete shadow_truth_set_ref")
    if not micro_live_input.shadow_validation_set_ref.strip():
        reasons.append(
            "Build-12 Micro-live requires a concrete shadow_validation_set_ref"
        )
    if micro_live_input.backtest_profile is not None:
        reasons.append("BACKTEST_PROFILE is forbidden in the unified V5.3")
    if micro_live_input.creates_profile_fork:
        reasons.append("Local/VPS profile forks are forbidden")
    if micro_live_input.automatic_live_promotion_requested:
        reasons.append("Micro-live must not request automatic promotion to LIVE")
    if (
        micro_live_input.operator_safing_request is not None
        and micro_live_input.operator_safing_request.source_runtime_mode
        != micro_live_input.runtime_mode
    ):
        reasons.append(
            "Build-12 Micro-live operator_safing_request must match source_runtime_mode=MICRO_LIVE"
        )
    if micro_live_input.shadow_required_days != 30:
        reasons.append("Build-12 Micro-live requires shadow_required_days=30")
    if not micro_live_input.shadow_import_artifact_id or micro_live_input.shadow_import_artifact_id == "none":
        reasons.append(
            "Build-12 Micro-live requires a concrete shadow_import_artifact_id"
        )
    if (
        not micro_live_input.shadow_import_lineage_version
        or micro_live_input.shadow_import_lineage_version == "n/a"
    ):
        reasons.append(
            "Build-12 Micro-live requires a concrete shadow_import_lineage_version"
        )
    if not micro_live_input.import_artifact_id or micro_live_input.import_artifact_id == "none":
        reasons.append("Build-12 Micro-live requires a concrete import_artifact_id")
    if (
        not micro_live_input.import_lineage_version
        or micro_live_input.import_lineage_version == "n/a"
    ):
        reasons.append("Build-12 Micro-live requires a concrete lineage_version")

    return tuple(reasons)


def _resolve_shadow_scope(
    shadow_summary: ShadowRunSummary,
    shadow_payload: TechnicalDashboardPayload,
    *,
    active_engines: tuple[str, ...] | None,
) -> _ResolvedShadowScope:
    validated_light_engines, dormant_components = _resolve_shadow_component_verdicts(
        shadow_summary
    )
    promotable_engines, shadow_only_engines, rewrite_required_engines = (
        _resolve_shadow_engine_judgment_scope(shadow_payload)
    )
    portfolio_judgment = derive_shadow_portfolio_judgment(shadow_payload)
    eligible_promotable_engines = tuple(
        engine_id
        for engine_id in promotable_engines
        if engine_id in validated_light_engines
    )
    if shadow_payload.engine_judgment.cards and not eligible_promotable_engines:
        raise MicroLiveInputError(
            "Build-12 Micro-live requires at least one PROMOTABLE engine in Shadow judgment"
        )
    resolved_active_engines = (
        active_engines or eligible_promotable_engines or validated_light_engines
    )
    if eligible_promotable_engines:
        if not set(resolved_active_engines).issubset(set(eligible_promotable_engines)):
            raise MicroLiveInputError(
                "Build-12 Micro-live active_engines must be PROMOTABLE in Shadow judgment"
            )
    elif not set(resolved_active_engines).issubset(set(validated_light_engines)):
        raise MicroLiveInputError(
            "Build-12 Micro-live active_engines must be SHADOW_VALIDATED in Build-11"
        )
    return _ResolvedShadowScope(
        validated_engines=validated_light_engines,
        dormant_components=dormant_components,
        promotable_engines=promotable_engines,
        shadow_only_engines=shadow_only_engines,
        rewrite_required_engines=rewrite_required_engines,
        portfolio_judgment=portfolio_judgment,
        active_engines=resolved_active_engines,
    )


__all__ = [
    "_validate_shadow_source_payload_scope",
    "_validate_shadow_import_consistency",
    "_shadow_portfolio_blocking_reasons",
    "_shadow_engine_scope_blocking_reasons",
    "_probe_surface_blocking_reasons",
    "_shadow_temporal_blocking_reasons",
    "_governance_envelope_blocking_reasons",
    "_resolve_shadow_scope",
]
