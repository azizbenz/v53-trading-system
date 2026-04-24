"""IA-Lab import and root-cause diagnosis for RegimeDetector shadow audit bundles."""

from __future__ import annotations

from pathlib import Path

from interface_contracts import (
    RegimeDetectorArtifact,
    RegimeDetectorShadowAuditBundle,
    RegimeDetectorShadowAuditDiagnosis,
    RegimeDetectorShadowAuditDiagnosisStatus,
    RegimeDetectorShadowAuditFinding,
    RegimeDetectorShadowAuditFindingCode,
    RegimeDetectorShadowAuditFindingSeverity,
    RegimeDetectorShadowAuditSchemaMatchStatus,
)


_CANONICAL_SHADOW_DIFF_PCT_LIMIT = 0.1
_DEFAULT_OBSERVATION_COVERAGE_FLOOR = 0.60


def load_regime_detector_shadow_audit_bundle(
    bundle_ref: str,
) -> RegimeDetectorShadowAuditBundle:
    """Load and validate a typed RegimeDetector shadow audit bundle from disk."""

    path = Path(bundle_ref).resolve()
    try:
        payload = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"RegimeDetector shadow audit bundle unreadable: {path}") from exc
    try:
        return RegimeDetectorShadowAuditBundle.model_validate_json(payload)
    except ValueError as exc:
        raise ValueError(f"RegimeDetector shadow audit bundle invalid: {path}") from exc


def _rate(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return numerator / denominator


def _append_finding(
    findings: list[RegimeDetectorShadowAuditFinding],
    code: RegimeDetectorShadowAuditFindingCode,
    severity: RegimeDetectorShadowAuditFindingSeverity,
    detail: str,
) -> None:
    findings.append(
        RegimeDetectorShadowAuditFinding(
            code=code,
            severity=severity,
            detail=detail,
        )
    )


def _apply_empty_bundle_check(
    bundle: RegimeDetectorShadowAuditBundle,
    *,
    findings: list[RegimeDetectorShadowAuditFinding],
) -> None:
    if bundle.sample_count <= 0:
        _append_finding(
            findings,
            RegimeDetectorShadowAuditFindingCode.AUDIT_BUNDLE_EMPTY,
            RegimeDetectorShadowAuditFindingSeverity.BLOCKING,
            "No VPS shadow samples were exported for this RegimeDetector audit window.",
        )


def _apply_profile_check(
    bundle: RegimeDetectorShadowAuditBundle,
    *,
    expected_feature_profile: str | None,
    findings: list[RegimeDetectorShadowAuditFinding],
    blocking_reasons: list[str],
) -> None:
    if expected_feature_profile is not None and bundle.feature_profile != expected_feature_profile:
        blocking_reasons.append("REGIME_DETECTOR_FEATURE_PROFILE_MISMATCH")
        _append_finding(
            findings,
            RegimeDetectorShadowAuditFindingCode.FEATURE_PROFILE_MISMATCH,
            RegimeDetectorShadowAuditFindingSeverity.BLOCKING,
            f"Expected feature profile {expected_feature_profile}, got {bundle.feature_profile}.",
        )


def _apply_artifact_checks(
    bundle: RegimeDetectorShadowAuditBundle,
    *,
    expected_artifact: RegimeDetectorArtifact | None,
    findings: list[RegimeDetectorShadowAuditFinding],
    blocking_reasons: list[str],
) -> None:
    if expected_artifact is None:
        return
    if bundle.artifact_hash and bundle.artifact_hash != expected_artifact.artifact_hash:
        blocking_reasons.append("REGIME_DETECTOR_ARTIFACT_HASH_MISMATCH")
        _append_finding(
            findings,
            RegimeDetectorShadowAuditFindingCode.ARTIFACT_HASH_MISMATCH,
            RegimeDetectorShadowAuditFindingSeverity.BLOCKING,
            "VPS audit bundle artifact hash does not match the IA-Lab artifact.",
        )
    if bundle.feature_hash_at_runtime and bundle.feature_hash_at_runtime != expected_artifact.feature_hash:
        blocking_reasons.append("REGIME_DETECTOR_FEATURE_HASH_MISMATCH")
        _append_finding(
            findings,
            RegimeDetectorShadowAuditFindingCode.FEATURE_HASH_MISMATCH,
            RegimeDetectorShadowAuditFindingSeverity.BLOCKING,
            "VPS runtime feature hash does not match the IA-Lab artifact feature hash.",
        )
    if bundle.feature_set_version != expected_artifact.feature_set_version:
        blocking_reasons.append("REGIME_DETECTOR_FEATURE_SET_VERSION_MISMATCH")
        _append_finding(
            findings,
            RegimeDetectorShadowAuditFindingCode.FEATURE_SET_VERSION_MISMATCH,
            RegimeDetectorShadowAuditFindingSeverity.BLOCKING,
            "VPS audit feature-set version does not match the IA-Lab artifact.",
        )
    if bundle.pair and bundle.pair not in expected_artifact.pair_universe:
        blocking_reasons.append("REGIME_DETECTOR_PAIR_NOT_IN_UNIVERSE")
        _append_finding(
            findings,
            RegimeDetectorShadowAuditFindingCode.PAIR_NOT_IN_UNIVERSE,
            RegimeDetectorShadowAuditFindingSeverity.BLOCKING,
            f"Pair {bundle.pair} is outside the artifact pair_universe.",
        )


def _resolve_shadow_diff_pct(bundle: RegimeDetectorShadowAuditBundle) -> float | None:
    shadow_diff_pct = bundle.shadow_metrics.get("shadow_diff_pct")
    if not isinstance(shadow_diff_pct, (int, float)):
        return None
    return float(shadow_diff_pct)


def _apply_schema_and_drift_checks(
    bundle: RegimeDetectorShadowAuditBundle,
    *,
    findings: list[RegimeDetectorShadowAuditFinding],
    blocking_reasons: list[str],
) -> float | None:
    if bundle.schema_match_status == RegimeDetectorShadowAuditSchemaMatchStatus.MISMATCHED:
        blocking_reasons.append("REGIME_DETECTOR_SCHEMA_MISMATCH")
        _append_finding(
            findings,
            RegimeDetectorShadowAuditFindingCode.ARTIFACT_SCHEMA_MISMATCH,
            RegimeDetectorShadowAuditFindingSeverity.BLOCKING,
            "VPS shadow audit reports a feature schema mismatch.",
        )
    resolved_shadow_diff_pct = _resolve_shadow_diff_pct(bundle)
    if (
        resolved_shadow_diff_pct is not None
        and resolved_shadow_diff_pct >= _CANONICAL_SHADOW_DIFF_PCT_LIMIT
    ):
        blocking_reasons.append("REGIME_DETECTOR_SHADOW_DIFF_PCT_HIGH")
        _append_finding(
            findings,
            RegimeDetectorShadowAuditFindingCode.SHADOW_DRIFT_HIGH,
            RegimeDetectorShadowAuditFindingSeverity.BLOCKING,
            "shadow_diff_pct breached the canonical 0.1 limit.",
        )
    return resolved_shadow_diff_pct


def _apply_runtime_quality_checks(
    bundle: RegimeDetectorShadowAuditBundle,
    *,
    min_observation_coverage_ratio: float,
    findings: list[RegimeDetectorShadowAuditFinding],
    blocking_reasons: list[str],
    caution_flags: list[str],
) -> float | None:
    if bundle.runtime_stale_count > 0:
        caution_flags.append("REGIME_DETECTOR_RUNTIME_STALE_PRESENT")
        _append_finding(
            findings,
            RegimeDetectorShadowAuditFindingCode.RUNTIME_STALE_PRESENT,
            RegimeDetectorShadowAuditFindingSeverity.CAUTION,
            "Some VPS shadow samples were evaluated with a stale artifact state.",
        )

    if bundle.sample_count > 0 and bundle.insufficient_data_count >= bundle.sample_count:
        blocking_reasons.append("REGIME_DETECTOR_INSUFFICIENT_DATA_DOMINANT")
        _append_finding(
            findings,
            RegimeDetectorShadowAuditFindingCode.INSUFFICIENT_DATA_DOMINANT,
            RegimeDetectorShadowAuditFindingSeverity.BLOCKING,
            "All VPS shadow samples fell back to insufficient_data.",
        )
    elif bundle.insufficient_data_count > 0:
        caution_flags.append("REGIME_DETECTOR_INSUFFICIENT_DATA_PRESENT")

    coverage_summary = bundle.observation_coverage_ratio_summary
    resolved_coverage_mean = None if coverage_summary.count <= 0 else coverage_summary.mean_value
    if (
        resolved_coverage_mean is not None
        and resolved_coverage_mean < min_observation_coverage_ratio
    ):
        caution_flags.append("REGIME_DETECTOR_OBSERVATION_COVERAGE_LOW")
        _append_finding(
            findings,
            RegimeDetectorShadowAuditFindingCode.COVERAGE_TOO_LOW,
            RegimeDetectorShadowAuditFindingSeverity.CAUTION,
            f"Mean observation coverage {resolved_coverage_mean:.3f} is below {min_observation_coverage_ratio:.3f}.",
        )

    if bundle.sample_count > 0 and bundle.prediction_count <= 0:
        caution_flags.append("REGIME_DETECTOR_NO_ACTIVE_PREDICTIONS")
        _append_finding(
            findings,
            RegimeDetectorShadowAuditFindingCode.NO_ACTIVE_PREDICTIONS,
            RegimeDetectorShadowAuditFindingSeverity.CAUTION,
            "The VPS shadow bundle contains no active predictions to compare.",
        )
    return resolved_coverage_mean


def _resolve_status(
    findings: list[RegimeDetectorShadowAuditFinding],
    *,
    blocking_reasons: list[str],
    caution_flags: list[str],
) -> RegimeDetectorShadowAuditDiagnosisStatus:
    if any(
        finding.severity == RegimeDetectorShadowAuditFindingSeverity.BLOCKING
        for finding in findings
    ) or blocking_reasons:
        return RegimeDetectorShadowAuditDiagnosisStatus.BLOCKED
    if any(
        finding.severity == RegimeDetectorShadowAuditFindingSeverity.CAUTION
        for finding in findings
    ) or caution_flags:
        return RegimeDetectorShadowAuditDiagnosisStatus.CAUTION
    return RegimeDetectorShadowAuditDiagnosisStatus.HEALTHY


def build_local_lab_regime_detector_shadow_audit_diagnosis(
    bundle: RegimeDetectorShadowAuditBundle,
    *,
    expected_artifact: RegimeDetectorArtifact | None = None,
    expected_feature_profile: str | None = None,
    min_observation_coverage_ratio: float = _DEFAULT_OBSERVATION_COVERAGE_FLOOR,
) -> RegimeDetectorShadowAuditDiagnosis:
    """Build a bounded IA-Lab diagnosis from one VPS shadow audit bundle."""

    findings: list[RegimeDetectorShadowAuditFinding] = []
    blocking_reasons: list[str] = list(bundle.blocking_reasons)
    caution_flags: list[str] = []

    _apply_empty_bundle_check(bundle, findings=findings)
    _apply_profile_check(
        bundle,
        expected_feature_profile=expected_feature_profile,
        findings=findings,
        blocking_reasons=blocking_reasons,
    )
    _apply_artifact_checks(
        bundle,
        expected_artifact=expected_artifact,
        findings=findings,
        blocking_reasons=blocking_reasons,
    )
    resolved_shadow_diff_pct = _apply_schema_and_drift_checks(
        bundle,
        findings=findings,
        blocking_reasons=blocking_reasons,
    )
    resolved_coverage_mean = _apply_runtime_quality_checks(
        bundle,
        min_observation_coverage_ratio=min_observation_coverage_ratio,
        findings=findings,
        blocking_reasons=blocking_reasons,
        caution_flags=caution_flags,
    )

    return RegimeDetectorShadowAuditDiagnosis(
        status=_resolve_status(
            findings,
            blocking_reasons=blocking_reasons,
            caution_flags=caution_flags,
        ),
        diagnosis_ready=bundle.sample_count > 0,
        artifact_hash=bundle.artifact_hash,
        feature_set_version=bundle.feature_set_version,
        feature_profile=bundle.feature_profile,
        pair=bundle.pair,
        sample_count=bundle.sample_count,
        prediction_count=bundle.prediction_count,
        insufficient_data_rate=_rate(bundle.insufficient_data_count, bundle.sample_count),
        runtime_stale_rate=_rate(bundle.runtime_stale_count, bundle.sample_count),
        observation_coverage_mean=resolved_coverage_mean,
        shadow_diff_pct=resolved_shadow_diff_pct,
        finding_count=len(findings),
        blocking_reasons=tuple(dict.fromkeys(blocking_reasons)),
        caution_flags=tuple(dict.fromkeys(caution_flags)),
        findings=tuple(findings),
    )


__all__ = [
    "load_regime_detector_shadow_audit_bundle",
    "build_local_lab_regime_detector_shadow_audit_diagnosis",
]
