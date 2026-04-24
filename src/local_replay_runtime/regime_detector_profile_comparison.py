"""Local IA Lab comparison of RegimeDetector feature profiles."""

from __future__ import annotations

from collections.abc import Mapping

from pydantic import BaseModel, Field

from calibration_methods import RegimeDetectorFeatureProfile
from interface_contracts import (
    RegimeDetectorFeatureSetVersion,
    RegimeDetectorLabelConfig,
)
from local_replay_runtime.historical_snapshot_loader import HistoricalSnapshotBatch
from local_replay_runtime.local_lab_regime_detector_artifact_training import (
    LocalLabRegimeDetectorArtifactTrainingReport,
    build_local_lab_regime_detector_artifact_training_report,
)


_PROFILE_ORDER: tuple[RegimeDetectorFeatureProfile, ...] = (
    "core_v1",
    "extended_v2",
    "full_v2",
)

_PROFILE_TIEBREAK: dict[str, int] = {
    "core_v1": 0,
    "extended_v2": 1,
    "full_v2": 2,
}


class LocalLabRegimeDetectorProfileComparisonEntry(BaseModel, frozen=True):
    """One audit-ready profile result in a triple-profile RegimeDetector comparison."""

    feature_profile: str = Field(..., min_length=1)
    rank: int = Field(default=0, ge=0)
    status: str = Field(default="not_evaluated", min_length=1)
    ready: bool = False
    dataset_id: str = Field(default="", min_length=0)
    feature_set_version: RegimeDetectorFeatureSetVersion = (
        RegimeDetectorFeatureSetVersion.LOB_REGIME_FEATURE_SET_V1
    )
    sample_count: int = Field(default=0, ge=0)
    training_row_count: int = Field(default=0, ge=0)
    selected_feature_count: int = Field(default=0, ge=0)
    selected_feature_names: tuple[str, ...] = ()
    pair_scope: tuple[str, ...] = ()
    artifact_hash: str | None = None
    transition_accuracy: float | None = Field(default=None, ge=0.0, le=1.0)
    transition_brier_score: float | None = Field(default=None, ge=0.0)
    feature_ks_min_pvalue: float | None = Field(default=None, ge=0.0, le=1.0)
    shadow_diff_pct: float | None = Field(default=None, ge=0.0)
    blocking_reasons: tuple[str, ...] = ()


class LocalLabRegimeDetectorProfileComparisonReport(BaseModel, frozen=True):
    """Unified Local IA Lab comparison of core_v1, extended_v2, and full_v2."""

    correlation_id: str = Field(..., min_length=1)
    status: str = Field(default="not_evaluated", min_length=1)
    comparison_ready: bool = False
    calibration_version: str = Field(..., min_length=1)
    training_seed: int
    dataset_id: str = ""
    feature_set_version: RegimeDetectorFeatureSetVersion = (
        RegimeDetectorFeatureSetVersion.LOB_REGIME_FEATURE_SET_V1
    )
    pair_scope: tuple[str, ...] = ()
    compared_profile_count: int = Field(default=0, ge=0)
    ready_profile_count: int = Field(default=0, ge=0)
    winner_profile: str = ""
    recommended_default_profile: str = ""
    recommendation: str = Field(default="not_evaluated", min_length=1)
    full_v2_disposition: str = Field(default="research_only", min_length=1)
    profiles: tuple[LocalLabRegimeDetectorProfileComparisonEntry, ...] = ()
    blocking_reasons: tuple[str, ...] = ()
    caution_flags: tuple[str, ...] = ()


def _metric(
    report: LocalLabRegimeDetectorArtifactTrainingReport,
    key: str,
) -> float | None:
    if report.artifact is None:
        return None
    value = report.artifact.oos_metrics.get(key)
    if not isinstance(value, (int, float)):
        return None
    return float(value)


def _entry_from_report(
    report: LocalLabRegimeDetectorArtifactTrainingReport,
) -> LocalLabRegimeDetectorProfileComparisonEntry:
    shadow_diff_pct = None
    if report.artifact is not None:
        raw_shadow_diff = report.artifact.shadow_metrics.get("shadow_diff_pct")
        if isinstance(raw_shadow_diff, (int, float)):
            shadow_diff_pct = float(raw_shadow_diff)
    return LocalLabRegimeDetectorProfileComparisonEntry(
        feature_profile=report.feature_profile,
        status=report.status,
        ready=report.ready,
        dataset_id=report.dataset_id,
        feature_set_version=report.feature_set_version,
        sample_count=report.sample_count,
        training_row_count=report.training_row_count,
        selected_feature_count=report.selected_feature_count,
        selected_feature_names=report.selected_feature_names,
        pair_scope=report.pair_scope,
        artifact_hash=report.artifact_hash,
        transition_accuracy=_metric(report, "transition_accuracy"),
        transition_brier_score=_metric(report, "transition_brier_score"),
        feature_ks_min_pvalue=_metric(report, "feature_ks_min_pvalue"),
        shadow_diff_pct=shadow_diff_pct,
        blocking_reasons=report.blocking_reasons,
    )


def _profile_sort_key(
    entry: LocalLabRegimeDetectorProfileComparisonEntry,
) -> tuple[float | int, ...]:
    return (
        0 if entry.ready else 1,
        -(entry.transition_accuracy if entry.transition_accuracy is not None else -1.0),
        entry.transition_brier_score if entry.transition_brier_score is not None else 1.0,
        -(entry.feature_ks_min_pvalue if entry.feature_ks_min_pvalue is not None else -1.0),
        entry.selected_feature_count,
        _PROFILE_TIEBREAK.get(entry.feature_profile, 99),
    )


def _rank_entries(
    entries: tuple[LocalLabRegimeDetectorProfileComparisonEntry, ...],
) -> tuple[LocalLabRegimeDetectorProfileComparisonEntry, ...]:
    ranked = sorted(entries, key=_profile_sort_key)
    return tuple(
        entry.model_copy(update={"rank": index + 1})
        for index, entry in enumerate(ranked)
    )


def _first_ready_entry(
    entries_by_profile: Mapping[str, LocalLabRegimeDetectorProfileComparisonEntry],
    profile: str,
) -> LocalLabRegimeDetectorProfileComparisonEntry | None:
    entry = entries_by_profile.get(profile)
    if entry is None or not entry.ready:
        return None
    return entry


def _core_outperforms_extended(
    core: LocalLabRegimeDetectorProfileComparisonEntry | None,
    extended: LocalLabRegimeDetectorProfileComparisonEntry | None,
) -> bool:
    if core is None or extended is None:
        return False
    if core.transition_accuracy is None or extended.transition_accuracy is None:
        return False
    if core.transition_brier_score is None or extended.transition_brier_score is None:
        return False
    if core.feature_ks_min_pvalue is None or extended.feature_ks_min_pvalue is None:
        return False
    return (
        core.transition_accuracy >= extended.transition_accuracy
        and core.transition_brier_score <= extended.transition_brier_score
        and core.feature_ks_min_pvalue >= extended.feature_ks_min_pvalue
        and core.selected_feature_count < extended.selected_feature_count
    )


def _full_is_candidate(
    full: LocalLabRegimeDetectorProfileComparisonEntry | None,
    core: LocalLabRegimeDetectorProfileComparisonEntry | None,
    extended: LocalLabRegimeDetectorProfileComparisonEntry | None,
) -> bool:
    if full is None or core is None or extended is None:
        return False
    comparable = (
        full.transition_accuracy,
        core.transition_accuracy,
        extended.transition_accuracy,
        full.transition_brier_score,
        core.transition_brier_score,
        extended.transition_brier_score,
        full.feature_ks_min_pvalue,
        core.feature_ks_min_pvalue,
        extended.feature_ks_min_pvalue,
    )
    if any(value is None for value in comparable):
        return False
    return (
        full.transition_accuracy > core.transition_accuracy
        and full.transition_accuracy > extended.transition_accuracy
        and full.transition_brier_score <= core.transition_brier_score
        and full.transition_brier_score <= extended.transition_brier_score
        and full.feature_ks_min_pvalue >= core.feature_ks_min_pvalue
        and full.feature_ks_min_pvalue >= extended.feature_ks_min_pvalue
    )


def _resolve_consistency(
    entries: tuple[LocalLabRegimeDetectorProfileComparisonEntry, ...],
) -> tuple[str, RegimeDetectorFeatureSetVersion, tuple[str, ...], tuple[str, ...]]:
    ready_entries = tuple(entry for entry in entries if entry.ready)
    blocking_reasons: list[str] = []
    if not ready_entries:
        return "", RegimeDetectorFeatureSetVersion.LOB_REGIME_FEATURE_SET_V1, (), (
            "REGIME_DETECTOR_PROFILE_COMPARISON_NO_READY_PROFILES",
        )
    dataset_ids = {entry.dataset_id for entry in ready_entries}
    if len(dataset_ids) != 1:
        blocking_reasons.append("REGIME_DETECTOR_PROFILE_COMPARISON_DATASET_ID_MISMATCH")
    feature_set_versions = {entry.feature_set_version for entry in ready_entries}
    if len(feature_set_versions) != 1:
        blocking_reasons.append("REGIME_DETECTOR_PROFILE_COMPARISON_FEATURE_SET_VERSION_MISMATCH")
    pair_scopes = {entry.pair_scope for entry in ready_entries}
    if len(pair_scopes) != 1:
        blocking_reasons.append("REGIME_DETECTOR_PROFILE_COMPARISON_PAIR_SCOPE_MISMATCH")
    return (
        ready_entries[0].dataset_id if len(dataset_ids) == 1 else "",
        ready_entries[0].feature_set_version,
        ready_entries[0].pair_scope if len(pair_scopes) == 1 else (),
        tuple(blocking_reasons),
    )


def _resolve_recommendation(
    entries_by_profile: Mapping[str, LocalLabRegimeDetectorProfileComparisonEntry],
) -> tuple[str, str, str]:
    core = _first_ready_entry(entries_by_profile, "core_v1")
    extended = _first_ready_entry(entries_by_profile, "extended_v2")
    full = _first_ready_entry(entries_by_profile, "full_v2")
    if extended is not None:
        if _full_is_candidate(full, core, extended):
            return "extended_v2", "promote_full_v2_candidate", "candidate_real"
        if _core_outperforms_extended(core, extended):
            return "core_v1", "fallback_to_core_v1", "research_only"
        return "extended_v2", "keep_extended_v2_default", "research_only"
    if core is not None:
        return "core_v1", "fallback_to_core_v1", "research_only"
    if full is not None:
        return "full_v2", "fallback_to_full_v2_only_ready_profile", "research_only"
    return "", "blocked_no_ready_profiles", "research_only"


def _resolve_status(
    *,
    ready_profile_count: int,
    blocking_reasons: tuple[str, ...],
) -> tuple[str, bool, tuple[str, ...]]:
    caution_flags: list[str] = []
    if ready_profile_count >= 3 and not blocking_reasons:
        return "ready", True, ()
    if ready_profile_count >= 2:
        caution_flags.append("REGIME_DETECTOR_PROFILE_COMPARISON_PARTIAL")
        return "partial", True, tuple(caution_flags)
    if ready_profile_count == 1:
        caution_flags.append("REGIME_DETECTOR_PROFILE_COMPARISON_ONLY_ONE_READY_PROFILE")
        return "partial", False, tuple(caution_flags)
    return "blocked", False, ()


def build_local_lab_regime_detector_profile_comparison_report_from_reports(
    *,
    correlation_id: str,
    calibration_version: str,
    training_seed: int,
    reports: tuple[LocalLabRegimeDetectorArtifactTrainingReport, ...],
) -> LocalLabRegimeDetectorProfileComparisonReport:
    """Build a profile comparison report from precomputed training reports."""

    ranked_entries = _rank_entries(tuple(_entry_from_report(report) for report in reports))
    entries_by_profile = {entry.feature_profile: entry for entry in ranked_entries}
    ready_profile_count = sum(1 for entry in ranked_entries if entry.ready)
    dataset_ref, feature_set_version, resolved_pair_scope, consistency_blockers = _resolve_consistency(
        ranked_entries
    )
    recommended_default_profile, recommendation, full_v2_disposition = _resolve_recommendation(
        entries_by_profile
    )
    status, comparison_ready, caution_flags = _resolve_status(
        ready_profile_count=ready_profile_count,
        blocking_reasons=consistency_blockers,
    )
    winner_profile = ""
    for entry in ranked_entries:
        if entry.ready:
            winner_profile = entry.feature_profile
            break

    return LocalLabRegimeDetectorProfileComparisonReport(
        correlation_id=correlation_id,
        status=status,
        comparison_ready=comparison_ready,
        calibration_version=calibration_version,
        training_seed=training_seed,
        dataset_id=dataset_ref,
        feature_set_version=feature_set_version,
        pair_scope=resolved_pair_scope,
        compared_profile_count=len(ranked_entries),
        ready_profile_count=ready_profile_count,
        winner_profile=winner_profile,
        recommended_default_profile=recommended_default_profile,
        recommendation=recommendation,
        full_v2_disposition=full_v2_disposition,
        profiles=ranked_entries,
        blocking_reasons=consistency_blockers,
        caution_flags=caution_flags,
    )


def build_local_lab_regime_detector_profile_comparison_report(
    *,
    correlation_id: str,
    batch: HistoricalSnapshotBatch,
    artifact_id_prefix: str,
    calibration_version: str,
    training_seed: int,
    dataset_id: str | None = None,
    label_config: RegimeDetectorLabelConfig | None = None,
    pair_scope: tuple[str, ...] | None = None,
    max_optuna_trials: int = 100,
) -> LocalLabRegimeDetectorProfileComparisonReport:
    """Run core_v1, extended_v2, and full_v2 on one governed dataset and compare them."""

    reports: list[LocalLabRegimeDetectorArtifactTrainingReport] = []
    for feature_profile in _PROFILE_ORDER:
        reports.append(
            build_local_lab_regime_detector_artifact_training_report(
                batch=batch,
                artifact_id=f"{artifact_id_prefix}:{feature_profile}",
                calibration_version=calibration_version,
                training_seed=training_seed,
                dataset_id=dataset_id,
                label_config=label_config,
                pair_scope=pair_scope,
                feature_profile=feature_profile,
                max_optuna_trials=max_optuna_trials,
            )
        )
    return build_local_lab_regime_detector_profile_comparison_report_from_reports(
        correlation_id=correlation_id,
        calibration_version=calibration_version,
        training_seed=training_seed,
        reports=tuple(reports),
    )


__all__ = [
    "LocalLabRegimeDetectorProfileComparisonEntry",
    "LocalLabRegimeDetectorProfileComparisonReport",
    "build_local_lab_regime_detector_profile_comparison_report_from_reports",
    "build_local_lab_regime_detector_profile_comparison_report",
]
