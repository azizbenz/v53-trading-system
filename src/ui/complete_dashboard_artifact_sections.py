"""Artifact-specific Build-17 dashboard sections."""

from __future__ import annotations

from typing import Protocol

from monitoring.contracts_artifacts import (
    ArtifactComparisonProjection,
    ArtifactRuntimeVisibilityProjection,
    ArtifactThresholdConsumerProjection,
    ArtifactVerdictBundleProjection,
)
from ui.contracts import DashboardCard, DashboardSection


class ArtifactSectionSupplement(Protocol):
    artifact_runtime_visibility: tuple[ArtifactRuntimeVisibilityProjection, ...]
    artifact_threshold_consumers: tuple[ArtifactThresholdConsumerProjection, ...]
    artifact_comparisons: tuple[ArtifactComparisonProjection, ...]
    artifact_verdict_bundle: ArtifactVerdictBundleProjection | None


def build_artifact_champions_section(
    supplement: ArtifactSectionSupplement,
) -> DashboardSection:
    champions = tuple(
        item for item in supplement.artifact_runtime_visibility if item.slot == "active"
    )
    cards = tuple(
        DashboardCard(
            key=f"complete_artifact_champion_{index}",
            label=item.artifact_id or item.artifact_kind,
            value=f"{item.artifact_kind} / {item.artifact_hash[:12] or 'none'}",
            status="info",
            detail=(
                f"lineage={item.lineage_version or 'n/a'} / "
                f"promotion={item.promotion_state or 'n/a'} / "
                f"review={item.review_state or 'n/a'} / "
                f"validation={item.validation_status or 'n/a'} / "
                f"calibration={item.calibration_version or 'n/a'} / "
                f"feature_hash={item.feature_hash[:12] or 'none'}"
            ),
        )
        for index, item in enumerate(champions, start=1)
    ) or (
        DashboardCard(
            key="complete_artifact_champions_empty",
            label="Champions",
            value="not available",
            status="planned",
            detail="No active champion artifact visibility projected",
        ),
    )
    return DashboardSection(title="Active Champion Artifacts", cards=cards)


def build_artifact_challengers_section(
    supplement: ArtifactSectionSupplement,
) -> DashboardSection:
    challengers = tuple(
        item
        for item in supplement.artifact_runtime_visibility
        if item.slot == "shadow_challenger"
    )
    cards = tuple(
        DashboardCard(
            key=f"complete_artifact_shadow_{index}",
            label=item.artifact_id or item.artifact_kind,
            value=f"{item.artifact_kind} / {item.artifact_hash[:12] or 'none'}",
            status="info",
            detail=(
                f"{item.influence_detail or 'shadow_only / non_influential'} / "
                f"lineage={item.lineage_version or 'n/a'} / "
                f"compare={_comparison_status_for_challenger(item.artifact_id, supplement.artifact_comparisons)} / "
                f"summary_ref={item.summary_ref or 'none'}"
            ),
        )
        for index, item in enumerate(challengers, start=1)
    ) or (
        DashboardCard(
            key="complete_artifact_shadow_empty",
            label="Shadow Challengers",
            value="not attached",
            status="planned",
            detail="No shadow challenger artifact projected",
        ),
    )
    return DashboardSection(title="Shadow Challengers", cards=cards)


def build_artifact_forecast_section(
    supplement: ArtifactSectionSupplement,
) -> DashboardSection:
    items = supplement.artifact_runtime_visibility
    cards = tuple(
        DashboardCard(
            key=f"complete_artifact_forecast_{index}",
            label=item.artifact_id or item.artifact_kind,
            value=(
                f"{item.forecast_target_class} / "
                f"{item.forecast_horizon_class} / "
                f"{item.bet_structure}"
            ),
            status="info",
            detail=(
                f"pairs={item.pair_universe_count} / "
                f"features={item.feature_count} / "
                f"feature_hash={item.feature_hash[:12] or 'none'} / "
                f"conditioning={item.conditioning_state_summary or 'n/a'} / "
                f"ref={item.top_feature_names_ref or item.summary_ref or 'none'}"
            ),
        )
        for index, item in enumerate(items, start=1)
    ) or (
        DashboardCard(
            key="complete_artifact_forecast_empty",
            label="Forecast / Feature Visibility",
            value="not available",
            status="planned",
            detail="No bounded artifact forecast visibility projected",
        ),
    )
    return DashboardSection(title="Forecast / Feature Visibility", cards=cards)


def build_artifact_threshold_compare_section(
    supplement: ArtifactSectionSupplement,
) -> DashboardSection:
    threshold_ids = tuple(
        consumer.threshold_id for consumer in supplement.artifact_threshold_consumers
    )
    comparison_cards = tuple(
        DashboardCard(
            key=f"complete_artifact_compare_{index}",
            label=f"{item.challenger_artifact_id or 'challenger'} compare",
            value=(
                f"{item.comparison_status} / "
                f"events={item.event_count} / "
                f"diff={item.decision_diff_rate:.3f}"
            ),
            status=_comparison_status(item.comparison_status),
            detail=(
                f"ce_delta={item.expected_ce_delta_mean:.6f} / "
                f"gain_delta={item.expected_gain_delta_mean:.6f} / "
                f"cost_delta={item.expected_cost_delta_mean:.6f} / "
                f"no_trade_delta={item.no_trade_delta:.3f} / "
                f"forecast_delta={item.forecast_strength_delta_mean:.3f} / "
                f"halal={item.halal_eligible_event_count}/"
                f"{item.halal_excluded_event_count} / "
                f"policy={item.sharia_policy_version or 'n/a'} / "
                f"scope={item.sharia_scope_mode or 'n/a'} / "
                f"ref={item.evidence_ref or 'none'}"
            ),
        )
        for index, item in enumerate(supplement.artifact_comparisons, start=1)
    )
    return DashboardSection(
        title="Threshold Consumers & Compare",
        cards=(
            DashboardCard(
                key="complete_artifact_thresholds",
                label="Threshold Consumers",
                value=str(len(supplement.artifact_threshold_consumers)),
                status="healthy" if supplement.artifact_threshold_consumers else "planned",
                detail=_join(threshold_ids, empty="No runtime threshold consumer projected"),
            ),
            DashboardCard(
                key="complete_artifact_compare_status",
                label="Champion vs Challenger",
                value=_join(
                    tuple(item.comparison_status for item in supplement.artifact_comparisons),
                    empty="No comparison projected",
                ),
                status="info" if supplement.artifact_comparisons else "planned",
                detail=_join(
                    tuple(
                        (
                            f"{item.champion_artifact_id}->{item.challenger_artifact_id}:"
                            f"{item.comparison_status}"
                        )
                        for item in supplement.artifact_comparisons
                    ),
                    empty="No comparison evidence projected",
                ),
            ),
            DashboardCard(
                key="complete_artifact_compare_refs",
                label="Evidence Refs",
                value=_join(
                    tuple(
                        item.evidence_ref or item.comparison_status
                        for item in supplement.artifact_comparisons
                    ),
                    empty="No evidence ref attached",
                ),
                status="info" if supplement.artifact_comparisons else "planned",
                detail=_join(
                    tuple(
                        f"ce_delta={item.expected_ce_delta_mean:.6f} / "
                        f"gain_delta={item.expected_gain_delta_mean:.6f} / "
                        f"halal={item.halal_eligible_event_count}/"
                        f"{item.halal_excluded_event_count}"
                        for item in supplement.artifact_comparisons
                    ),
                    empty="No bounded comparison delta projected",
                ),
            ),
        )
        + comparison_cards,
    )


def build_artifact_verdict_section(
    supplement: ArtifactSectionSupplement,
) -> DashboardSection:
    verdict = supplement.artifact_verdict_bundle
    cards = (
        DashboardCard(
            key="complete_artifact_verdict_bundle",
            label="Daily Verdict",
            value="not available" if verdict is None else verdict.overall_verdict,
            status="planned" if verdict is None else _verdict_status(verdict.overall_verdict),
            detail=(
                "No daily challenger verdict bundle projected"
                if verdict is None
                else (
                    f"recommendation={verdict.operator_recommendation} / "
                    f"configured={verdict.configured_family_count} / "
                    f"ready={verdict.ready_family_count} / "
                    f"invalid={verdict.invalid_family_count} / "
                    f"blocked={verdict.sharia_blocked_family_count} / "
                    f"runtime_inputs={verdict.runtime_inputs_missing_family_count}"
                )
            ),
        ),
        DashboardCard(
            key="complete_artifact_verdict_support",
            label="Reasons",
            value=(
                "not available"
                if verdict is None
                else _join(verdict.blocking_reasons, empty="no_blockers")
            ),
            status="planned" if verdict is None else "info",
            detail=(
                "No supporting reasons projected"
                if verdict is None
                else (
                    f"support={_join(verdict.supporting_reasons, empty='none')} / "
                    f"policy={verdict.sharia_policy_version or 'n/a'} / "
                    f"ref={verdict.evidence_ref or 'none'}"
                )
            ),
        ),
    )
    return DashboardSection(title="Shadow Challenger Verdict", cards=cards)


def _join(values: tuple[str, ...], *, empty: str) -> str:
    return ", ".join(values) if values else empty


def _comparison_status(status: str) -> str:
    if status == "shadow_ready":
        return "healthy"
    if status in {"shadow_runtime_inputs_missing", "shadow_pending_evidence"}:
        return "warning"
    if status in {"sharia_scope_blocked", "invalid_evidence"}:
        return "critical"
    return "info"


def _verdict_status(verdict: str) -> str:
    if verdict == "shadow_validated":
        return "healthy"
    if verdict in {"shadow_inconclusive", "shadow_runtime_inputs_missing"}:
        return "warning"
    if verdict in {"sharia_scope_blocked", "invalid_evidence"}:
        return "critical"
    return "info"


def _comparison_status_for_challenger(
    artifact_id: str,
    comparisons: tuple[ArtifactComparisonProjection, ...],
) -> str:
    for comparison in comparisons:
        if comparison.challenger_artifact_id == artifact_id:
            return comparison.comparison_status
    return "shadow_pending_evidence"


__all__ = [
    "build_artifact_challengers_section",
    "build_artifact_champions_section",
    "build_artifact_forecast_section",
    "build_artifact_threshold_compare_section",
    "build_artifact_verdict_section",
]
