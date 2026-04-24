"""Final Local IA Lab audit report joining profile comparison and VPS shadow diagnosis."""

from __future__ import annotations

from pydantic import BaseModel, Field

from calibration_methods import RegimeDetectorFeatureProfile
from interface_contracts import (
    DashboardGovernedCommandKind,
    DashboardGovernedCommandResult,
    DashboardGovernedCommandStatus,
    RegimeDetectorFeatureSetVersion,
    RegimeDetectorLabelConfig,
    RegimeDetectorShadowAuditBundle,
    RegimeDetectorShadowAuditDiagnosis,
    RegimeDetectorShadowAuditDiagnosisStatus,
)
from local_replay_runtime.historical_snapshot_loader import HistoricalSnapshotBatch
from local_replay_runtime.local_lab_regime_detector_artifact_training import (
    LocalLabRegimeDetectorArtifactTrainingReport,
    build_local_lab_regime_detector_artifact_training_report,
)
from local_replay_runtime.regime_detector_profile_comparison import (
    LocalLabRegimeDetectorProfileComparisonReport,
    build_local_lab_regime_detector_profile_comparison_report_from_reports,
)
from local_replay_runtime.regime_detector_shadow_audit_diagnosis import (
    build_local_lab_regime_detector_shadow_audit_diagnosis,
    load_regime_detector_shadow_audit_bundle,
)


_PROFILE_ORDER: tuple[RegimeDetectorFeatureProfile, ...] = (
    "core_v1",
    "extended_v2",
    "full_v2",
)


class LocalLabRegimeDetectorFinalAuditReport(BaseModel, frozen=True):
    """Unified IA-Lab view of profile comparison plus VPS-uploaded artifact diagnosis."""

    correlation_id: str = Field(..., min_length=1)
    status: str = Field(default="not_evaluated", min_length=1)
    audit_ready: bool = False
    comparison_ready: bool = False
    shadow_audit_present: bool = False
    calibration_version: str = Field(..., min_length=1)
    training_seed: int
    dataset_id: str = ""
    feature_set_version: RegimeDetectorFeatureSetVersion = (
        RegimeDetectorFeatureSetVersion.LOB_REGIME_FEATURE_SET_V1
    )
    pair_scope: tuple[str, ...] = ()
    winner_profile: str = ""
    recommended_default_profile: str = ""
    uploaded_profile: str = ""
    uploaded_artifact_hash: str = ""
    uploaded_profile_rank: int = Field(default=0, ge=0)
    uploaded_profile_matches_lab_default: bool = False
    final_recommendation: str = Field(default="not_evaluated", min_length=1)
    comparison_report: LocalLabRegimeDetectorProfileComparisonReport
    shadow_audit_diagnosis: RegimeDetectorShadowAuditDiagnosis | None = None
    blocking_reasons: tuple[str, ...] = ()
    caution_flags: tuple[str, ...] = ()


def _build_training_reports(
    *,
    batch: HistoricalSnapshotBatch,
    artifact_id_prefix: str,
    calibration_version: str,
    training_seed: int,
    dataset_id: str | None,
    label_config: RegimeDetectorLabelConfig | None,
    pair_scope: tuple[str, ...] | None,
    max_optuna_trials: int,
) -> tuple[LocalLabRegimeDetectorArtifactTrainingReport, ...]:
    return tuple(
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
        for feature_profile in _PROFILE_ORDER
    )


def _resolve_bundle(
    *,
    shadow_audit_bundle: RegimeDetectorShadowAuditBundle | None,
    shadow_audit_bundle_ref: str | None,
) -> RegimeDetectorShadowAuditBundle | None:
    if shadow_audit_bundle is not None and shadow_audit_bundle_ref is not None:
        raise ValueError("shadow_audit_bundle and shadow_audit_bundle_ref are mutually exclusive")
    if shadow_audit_bundle is not None:
        return shadow_audit_bundle
    if shadow_audit_bundle_ref is not None:
        return load_regime_detector_shadow_audit_bundle(shadow_audit_bundle_ref)
    return None


def _resolve_uploaded_profile_rank(
    comparison_report: LocalLabRegimeDetectorProfileComparisonReport,
    uploaded_profile: str,
) -> int:
    for profile in comparison_report.profiles:
        if profile.feature_profile == uploaded_profile:
            return profile.rank
    return 0


def _resolve_uploaded_report(
    training_reports: tuple[LocalLabRegimeDetectorArtifactTrainingReport, ...],
    *,
    uploaded_profile: str,
) -> LocalLabRegimeDetectorArtifactTrainingReport | None:
    for report in training_reports:
        if report.feature_profile == uploaded_profile:
            return report
    return None


def _resolve_status_and_recommendation(
    *,
    comparison_report: LocalLabRegimeDetectorProfileComparisonReport,
    diagnosis: RegimeDetectorShadowAuditDiagnosis | None,
    uploaded_profile_matches_lab_default: bool,
) -> tuple[str, bool, str, tuple[str, ...], tuple[str, ...]]:
    blocking_reasons: list[str] = list(comparison_report.blocking_reasons)
    caution_flags: list[str] = list(comparison_report.caution_flags)
    if diagnosis is None:
        caution_flags.append("REGIME_DETECTOR_VPS_SHADOW_AUDIT_BUNDLE_MISSING")
        return (
            "partial" if comparison_report.comparison_ready else "blocked",
            False,
            "collect_vps_shadow_audit_bundle",
            tuple(dict.fromkeys(blocking_reasons)),
            tuple(dict.fromkeys(caution_flags)),
        )
    blocking_reasons.extend(diagnosis.blocking_reasons)
    caution_flags.extend(diagnosis.caution_flags)
    if not comparison_report.comparison_ready:
        return (
            "blocked",
            False,
            "blocked_profile_comparison_not_ready",
            tuple(dict.fromkeys(blocking_reasons)),
            tuple(dict.fromkeys(caution_flags)),
        )
    if diagnosis.status == RegimeDetectorShadowAuditDiagnosisStatus.BLOCKED:
        return (
            "blocked",
            False,
            "investigate_uploaded_artifact_root_cause",
            tuple(dict.fromkeys(blocking_reasons)),
            tuple(dict.fromkeys(caution_flags)),
        )
    if diagnosis.status == RegimeDetectorShadowAuditDiagnosisStatus.CAUTION:
        return (
            "partial",
            False,
            "continue_shadow_and_monitor_uploaded_artifact",
            tuple(dict.fromkeys(blocking_reasons)),
            tuple(dict.fromkeys(caution_flags)),
        )
    if not uploaded_profile_matches_lab_default:
        caution_flags.append("REGIME_DETECTOR_UPLOADED_PROFILE_DIFFERS_FROM_LAB_DEFAULT")
        return (
            "partial",
            False,
            "uploaded_profile_differs_from_lab_default",
            tuple(dict.fromkeys(blocking_reasons)),
            tuple(dict.fromkeys(caution_flags)),
        )
    return (
        "ready",
        True,
        "uploaded_profile_matches_lab_recommendation",
        tuple(dict.fromkeys(blocking_reasons)),
        tuple(dict.fromkeys(caution_flags)),
    )


def build_local_lab_regime_detector_final_audit_report(
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
    shadow_audit_bundle: RegimeDetectorShadowAuditBundle | None = None,
    shadow_audit_bundle_ref: str | None = None,
) -> LocalLabRegimeDetectorFinalAuditReport:
    """Build the final IA-Lab audit report for profile comparison plus VPS diagnosis."""

    training_reports = _build_training_reports(
        batch=batch,
        artifact_id_prefix=artifact_id_prefix,
        calibration_version=calibration_version,
        training_seed=training_seed,
        dataset_id=dataset_id,
        label_config=label_config,
        pair_scope=pair_scope,
        max_optuna_trials=max_optuna_trials,
    )
    comparison_report = build_local_lab_regime_detector_profile_comparison_report_from_reports(
        correlation_id=correlation_id,
        calibration_version=calibration_version,
        training_seed=training_seed,
        reports=training_reports,
    )
    resolved_bundle = _resolve_bundle(
        shadow_audit_bundle=shadow_audit_bundle,
        shadow_audit_bundle_ref=shadow_audit_bundle_ref,
    )
    diagnosis = None
    uploaded_profile = ""
    uploaded_artifact_hash = ""
    uploaded_profile_rank = 0
    uploaded_profile_matches_lab_default = False
    if resolved_bundle is not None:
        uploaded_profile = resolved_bundle.feature_profile
        uploaded_artifact_hash = resolved_bundle.artifact_hash
        uploaded_profile_rank = _resolve_uploaded_profile_rank(
            comparison_report,
            uploaded_profile,
        )
        uploaded_report = _resolve_uploaded_report(
            training_reports,
            uploaded_profile=uploaded_profile,
        )
        diagnosis = build_local_lab_regime_detector_shadow_audit_diagnosis(
            resolved_bundle,
            expected_artifact=None if uploaded_report is None else uploaded_report.artifact,
            expected_feature_profile=uploaded_profile,
        )
        uploaded_profile_matches_lab_default = (
            uploaded_profile == comparison_report.recommended_default_profile
        )

    status, audit_ready, final_recommendation, blocking_reasons, caution_flags = (
        _resolve_status_and_recommendation(
            comparison_report=comparison_report,
            diagnosis=diagnosis,
            uploaded_profile_matches_lab_default=uploaded_profile_matches_lab_default,
        )
    )
    return LocalLabRegimeDetectorFinalAuditReport(
        correlation_id=correlation_id,
        status=status,
        audit_ready=audit_ready,
        comparison_ready=comparison_report.comparison_ready,
        shadow_audit_present=resolved_bundle is not None,
        calibration_version=calibration_version,
        training_seed=training_seed,
        dataset_id=comparison_report.dataset_id,
        feature_set_version=comparison_report.feature_set_version,
        pair_scope=comparison_report.pair_scope,
        winner_profile=comparison_report.winner_profile,
        recommended_default_profile=comparison_report.recommended_default_profile,
        uploaded_profile=uploaded_profile,
        uploaded_artifact_hash=uploaded_artifact_hash,
        uploaded_profile_rank=uploaded_profile_rank,
        uploaded_profile_matches_lab_default=uploaded_profile_matches_lab_default,
        final_recommendation=final_recommendation,
        comparison_report=comparison_report,
        shadow_audit_diagnosis=diagnosis,
        blocking_reasons=blocking_reasons,
        caution_flags=caution_flags,
    )


def build_local_lab_regime_detector_final_audit_report_from_vps_command_result(
    *,
    correlation_id: str,
    batch: HistoricalSnapshotBatch,
    artifact_id_prefix: str,
    calibration_version: str,
    training_seed: int,
    command_result: DashboardGovernedCommandResult,
    dataset_id: str | None = None,
    label_config: RegimeDetectorLabelConfig | None = None,
    pair_scope: tuple[str, ...] | None = None,
    max_optuna_trials: int = 100,
) -> LocalLabRegimeDetectorFinalAuditReport:
    """Resolve the final IA-Lab report from a VPS export result for the shadow audit bundle."""

    if (
        command_result.command_kind
        != DashboardGovernedCommandKind.REQUEST_EXPORT_REGIME_DETECTOR_SHADOW_AUDIT_BUNDLE
    ):
        raise ValueError(
            "command_result must come from request_export_regime_detector_shadow_audit_bundle"
        )
    if command_result.status != DashboardGovernedCommandStatus.COMPLETED:
        raise ValueError("command_result must be completed before IA-Lab re-audit")
    if not command_result.export_ref:
        raise ValueError("command_result must carry export_ref for the shadow audit bundle")
    return build_local_lab_regime_detector_final_audit_report(
        correlation_id=correlation_id,
        batch=batch,
        artifact_id_prefix=artifact_id_prefix,
        calibration_version=calibration_version,
        training_seed=training_seed,
        dataset_id=dataset_id,
        label_config=label_config,
        pair_scope=pair_scope,
        max_optuna_trials=max_optuna_trials,
        shadow_audit_bundle_ref=command_result.export_ref,
    )


__all__ = [
    "LocalLabRegimeDetectorFinalAuditReport",
    "build_local_lab_regime_detector_final_audit_report",
    "build_local_lab_regime_detector_final_audit_report_from_vps_command_result",
]
