"""Final IA-Lab audit report for the governed ML artifact export loop."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from interface_contracts import (
    DashboardGovernedCommandKind,
    DashboardGovernedCommandResult,
    DashboardGovernedCommandStatus,
    MlModelArtifact,
)
from local_replay_runtime.local_lab_ml_artifact_training import (
    LocalLabMlArtifactTrainingReport,
)


class LocalLabMlFinalAuditReport(BaseModel, frozen=True):
    """Operator-safe ML audit result after comparing VPS export vs IA-Lab recommendation."""

    correlation_id: str = Field(..., min_length=1)
    status: str = Field(default="not_evaluated", min_length=1)
    audit_ready: bool = False
    uploaded_artifact_present: bool = False
    recommended_artifact_hash: str = ""
    uploaded_artifact_hash: str = ""
    uploaded_artifact_id: str = ""
    uploaded_lineage_version: str = ""
    uploaded_feature_set_version: str = ""
    feature_set_compatible: bool = False
    artifact_matches_lab_recommendation: bool = False
    final_recommendation: str = Field(default="not_evaluated", min_length=1)
    blocking_reasons: tuple[str, ...] = ()
    caution_flags: tuple[str, ...] = ()
    training_report: LocalLabMlArtifactTrainingReport


def _load_uploaded_ml_artifact(path_ref: str) -> MlModelArtifact:
    path = Path(path_ref)
    if not path.is_file():
        raise ValueError("command_result export_ref must point to a persisted ML artifact")
    return MlModelArtifact.model_validate_json(path.read_text(encoding="utf-8"))


def build_local_lab_ml_final_audit_report_from_vps_command_result(
    *,
    correlation_id: str,
    training_report: LocalLabMlArtifactTrainingReport,
    command_result: DashboardGovernedCommandResult,
) -> LocalLabMlFinalAuditReport:
    """Compare the active VPS ML artifact export against the current IA-Lab recommendation."""

    if (
        command_result.command_kind
        != DashboardGovernedCommandKind.REQUEST_EXPORT_ACTIVE_ML_ARTIFACT
    ):
        raise ValueError("command_result must come from request_export_active_ml_artifact")
    if command_result.status != DashboardGovernedCommandStatus.COMPLETED:
        raise ValueError("command_result must be completed before IA-Lab ML re-audit")
    if not command_result.export_ref:
        raise ValueError("command_result must carry export_ref for the active ML artifact")

    blocking_reasons: list[str] = []
    caution_flags: list[str] = []
    recommended_artifact = training_report.artifact
    if recommended_artifact is None:
        blocking_reasons.append("ml.final_audit.recommended_artifact_missing")
    if not training_report.ready:
        blocking_reasons.extend(training_report.blocking_reasons)
        if not training_report.blocking_reasons:
            blocking_reasons.append("ml.final_audit.training_report_not_ready")

    try:
        uploaded_artifact = _load_uploaded_ml_artifact(command_result.export_ref)
    except ValueError:
        raise
    except Exception as exc:  # pragma: no cover - defensive parse failure path
        raise ValueError("command_result export_ref must resolve to a valid ML artifact") from exc

    uploaded_manifest = command_result.artifact_manifest
    if uploaded_manifest is None:
        blocking_reasons.append("ml.final_audit.upload_manifest_missing")
    elif uploaded_manifest.artifact_hash != uploaded_artifact.artifact_hash:
        blocking_reasons.append("ml.final_audit.upload_manifest_hash_mismatch")

    uploaded_feature_set_version = (
        "" if uploaded_manifest is None else uploaded_manifest.feature_set_version
    )
    uploaded_lineage_version = (
        "" if uploaded_manifest is None else uploaded_manifest.lineage_version
    )
    if not uploaded_feature_set_version:
        caution_flags.append("ml.final_audit.upload_feature_set_version_missing")

    feature_set_compatible = (
        recommended_artifact is not None
        and recommended_artifact.feature_hash == uploaded_artifact.feature_hash
    )
    if recommended_artifact is not None and not feature_set_compatible:
        blocking_reasons.append("ml.final_audit.feature_set_incompatible")

    artifact_matches_lab_recommendation = (
        recommended_artifact is not None
        and uploaded_artifact.artifact_hash == recommended_artifact.artifact_hash
    )
    if (
        recommended_artifact is not None
        and feature_set_compatible
        and not artifact_matches_lab_recommendation
    ):
        caution_flags.append("ml.final_audit.upload_differs_from_lab_recommendation")

    if blocking_reasons:
        status = "blocked"
        audit_ready = False
        final_recommendation = "resolve_ml_final_audit_blockers"
    elif not artifact_matches_lab_recommendation:
        status = "partial"
        audit_ready = False
        final_recommendation = "uploaded_ml_artifact_differs_from_lab_recommendation"
    else:
        status = "ready"
        audit_ready = True
        final_recommendation = "uploaded_ml_artifact_matches_lab_recommendation"

    return LocalLabMlFinalAuditReport(
        correlation_id=correlation_id,
        status=status,
        audit_ready=audit_ready,
        uploaded_artifact_present=True,
        recommended_artifact_hash=(
            "" if recommended_artifact is None else recommended_artifact.artifact_hash
        ),
        uploaded_artifact_hash=uploaded_artifact.artifact_hash,
        uploaded_artifact_id=(
            "" if uploaded_manifest is None else uploaded_manifest.artifact_id
        ),
        uploaded_lineage_version=uploaded_lineage_version,
        uploaded_feature_set_version=uploaded_feature_set_version,
        feature_set_compatible=feature_set_compatible,
        artifact_matches_lab_recommendation=artifact_matches_lab_recommendation,
        final_recommendation=final_recommendation,
        blocking_reasons=tuple(dict.fromkeys(blocking_reasons)),
        caution_flags=tuple(dict.fromkeys(caution_flags)),
        training_report=training_report,
    )


__all__ = [
    "LocalLabMlFinalAuditReport",
    "build_local_lab_ml_final_audit_report_from_vps_command_result",
]
