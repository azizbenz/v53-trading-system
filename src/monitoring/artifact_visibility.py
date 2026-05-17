"""Bounded artifact visibility and comparison builders for Build-17 supervision."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel

from interface_contracts import (
    DashboardArtifactKind,
    DashboardArtifactTransferManifest,
    MlModelArtifact,
    MlModelSourceArtifactSummary,
    RegimeDetectorArtifact,
    RegimeDetectorArtifactSummary,
)
from monitoring.contracts_artifacts import (
    ArtifactComparisonProjection,
    ArtifactShadowComparisonEvidence,
    ArtifactShadowVerdictBundle,
    ArtifactRuntimeVisibilityProjection,
    ArtifactThresholdConsumerProjection,
    ArtifactVerdictBundleProjection,
)


def _artifact_refs(
    manifest: DashboardArtifactTransferManifest | None,
) -> tuple[str, ...]:
    if manifest is None:
        return ()
    refs = [manifest.source_ref, *manifest.payload_refs]
    return tuple(ref for ref in refs if ref)


def _read_text(path_ref: str) -> str | None:
    path = Path(path_ref)
    if not path.is_file():
        return None
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return None


def _load_json_mapping(path_ref: str) -> dict[str, object] | None:
    payload = _read_text(path_ref)
    if payload is None:
        return None
    try:
        parsed = json.loads(payload)
    except ValueError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _load_model_from_refs(
    refs: tuple[str, ...],
    model_type: type[BaseModel],
) -> BaseModel | None:
    for ref in refs:
        payload = _read_text(ref)
        if payload is None:
            continue
        try:
            return model_type.model_validate_json(payload)
        except (TypeError, ValueError):
            continue
    return None


def _load_forecast_sidecar(refs: tuple[str, ...]) -> dict[str, str]:
    required_keys = {
        "forecast_target_class",
        "forecast_horizon_class",
        "bet_structure",
    }
    for ref in refs:
        payload = _load_json_mapping(ref)
        if payload is None or not required_keys.issubset(payload):
            continue
        return {
            "forecast_target_class": str(payload.get("forecast_target_class", "not_available")),
            "forecast_horizon_class": str(payload.get("forecast_horizon_class", "not_available")),
            "bet_structure": str(payload.get("bet_structure", "not_available")),
            "conditioning_state_summary": _conditioning_state_summary(
                payload.get("conditioning_state")
            ),
        }
    return {
        "forecast_target_class": "not_available",
        "forecast_horizon_class": "not_available",
        "bet_structure": "not_available",
        "conditioning_state_summary": "",
    }


def _conditioning_state_summary(raw_value: object) -> str:
    if not isinstance(raw_value, list):
        return ""
    families: list[str] = []
    seen: set[str] = set()
    for item in raw_value:
        if not isinstance(item, dict):
            continue
        family = str(item.get("family", "")).strip()
        if family and family not in seen:
            seen.add(family)
            families.append(family)
    return ", ".join(families[:4])


def _summary_ref(refs: tuple[str, ...]) -> str:
    return refs[0] if refs else ""


def _threshold_family(threshold_id: str) -> str:
    if threshold_id.startswith("THR-X"):
        return "execution_runtime"
    if threshold_id.startswith("THR-E"):
        return "economics"
    return "unknown"


def build_artifact_runtime_visibility_projections(
    *,
    active_ml_artifact: DashboardArtifactTransferManifest | None = None,
    active_regime_detector_artifact: DashboardArtifactTransferManifest | None = None,
    shadow_ml_challenger_artifact: DashboardArtifactTransferManifest | None = None,
    shadow_regime_detector_challenger_artifact: DashboardArtifactTransferManifest | None = None,
) -> tuple[ArtifactRuntimeVisibilityProjection, ...]:
    """Project bounded artifact identity/forecast visibility from manifests and sidecars."""

    projections: list[ArtifactRuntimeVisibilityProjection] = []
    for slot, manifest, shadow_only in (
        ("active", active_ml_artifact, False),
        ("active", active_regime_detector_artifact, False),
        ("shadow_challenger", shadow_ml_challenger_artifact, True),
        ("shadow_challenger", shadow_regime_detector_challenger_artifact, True),
    ):
        projection = _build_runtime_visibility_projection(
            slot=slot,
            manifest=manifest,
            shadow_only=shadow_only,
        )
        if projection is not None:
            projections.append(projection)
    return tuple(projections)


def _build_runtime_visibility_projection(
    *,
    slot: str,
    manifest: DashboardArtifactTransferManifest | None,
    shadow_only: bool,
) -> ArtifactRuntimeVisibilityProjection | None:
    if manifest is None:
        return None
    refs = _artifact_refs(manifest)
    summary_ref = _summary_ref(refs)
    forecast_sidecar = _load_forecast_sidecar(refs)
    feature_set_version = manifest.feature_set_version
    feature_hash = ""
    dataset_hash = ""
    calibration_version = ""
    promotion_state = ""
    pair_universe_count = 0
    feature_count = 0
    top_feature_names_ref = ""
    if manifest.artifact_kind == DashboardArtifactKind.ML_MODEL_ARTIFACT:
        artifact = _load_model_from_refs(refs, MlModelArtifact)
        summary = _load_model_from_refs(refs, MlModelSourceArtifactSummary)
        if isinstance(artifact, MlModelArtifact):
            feature_hash = artifact.feature_hash
            dataset_hash = artifact.dataset_hash
            calibration_version = artifact.calibration_version
            promotion_state = artifact.promotion_state.value
            pair_universe_count = len(artifact.pair_universe)
            feature_count = len(artifact.feature_names)
            top_feature_names_ref = manifest.source_ref if artifact.feature_names else ""
        elif isinstance(summary, MlModelSourceArtifactSummary):
            feature_hash = summary.feature_hash
            dataset_hash = summary.dataset_hash
            calibration_version = summary.calibration_version
            promotion_state = summary.promotion_state.value
            pair_universe_count = len(summary.pair_universe)
        if not feature_set_version:
            feature_set_version = getattr(summary, "schema_version", "") if summary else ""
    elif manifest.artifact_kind == DashboardArtifactKind.REGIME_DETECTOR_ARTIFACT:
        artifact = _load_model_from_refs(refs, RegimeDetectorArtifact)
        summary = _load_model_from_refs(refs, RegimeDetectorArtifactSummary)
        if isinstance(artifact, RegimeDetectorArtifact):
            feature_set_version = (
                feature_set_version or artifact.feature_set_version.value
            )
            feature_hash = artifact.feature_hash
            dataset_hash = artifact.dataset_hash
            calibration_version = artifact.calibration_version
            promotion_state = artifact.promotion_state.value
            pair_universe_count = len(artifact.pair_universe)
            feature_count = len(artifact.feature_names)
            top_feature_names_ref = manifest.source_ref if artifact.feature_names else ""
        elif isinstance(summary, RegimeDetectorArtifactSummary):
            feature_set_version = feature_set_version or summary.feature_set_version.value
            feature_hash = summary.feature_hash
            dataset_hash = summary.dataset_hash
            calibration_version = summary.calibration_version
            promotion_state = summary.promotion_state.value
            pair_universe_count = len(summary.pair_universe)
    return ArtifactRuntimeVisibilityProjection(
        slot=slot,  # type: ignore[arg-type]
        artifact_kind=manifest.artifact_kind.value,
        artifact_id=manifest.artifact_id or "none",
        artifact_hash=manifest.artifact_hash,
        lineage_version=manifest.lineage_version or "n/a",
        feature_set_version=feature_set_version,
        feature_hash=feature_hash,
        dataset_hash=dataset_hash,
        calibration_version=calibration_version,
        promotion_state=promotion_state,
        review_state=manifest.review_state,
        validation_status=manifest.validation_status,
        pair_universe_count=pair_universe_count,
        feature_count=feature_count,
        forecast_target_class=forecast_sidecar["forecast_target_class"],
        forecast_horizon_class=forecast_sidecar["forecast_horizon_class"],
        bet_structure=forecast_sidecar["bet_structure"],
        conditioning_state_summary=forecast_sidecar["conditioning_state_summary"],
        top_feature_names_ref=top_feature_names_ref,
        summary_ref=summary_ref,
        shadow_only=shadow_only,
        influence_detail=(
            "shadow_only / non_influential"
            if shadow_only
            else "active_champion / runtime_influential"
        ),
    )


def build_artifact_threshold_consumer_projections(
    *,
    execution_runtime_projection_path: str | Path | None = None,
) -> tuple[ArtifactThresholdConsumerProjection, ...]:
    """Project bounded threshold-consumer visibility from the runtime projection artifact."""

    if execution_runtime_projection_path is None:
        return ()
    path = Path(execution_runtime_projection_path)
    projection = _load_json_mapping(str(path))
    if projection is None:
        return ()
    consumers = projection.get("consumers")
    if not isinstance(consumers, list):
        return ()
    projections: list[ArtifactThresholdConsumerProjection] = []
    for consumer in consumers:
        if not isinstance(consumer, dict):
            continue
        try:
            projections.append(
                _build_threshold_consumer_projection(
                    consumer=consumer,
                    source_ref=str(path),
                )
            )
        except ValueError:
            continue
    return tuple(projections)


def _build_threshold_consumer_projection(
    *,
    consumer: dict[str, object],
    source_ref: str,
) -> ArtifactThresholdConsumerProjection:
    threshold_id = str(consumer.get("threshold_id", "")).strip()
    consumer_id = str(consumer.get("consumer_id", "")).strip()
    consumer_interface = str(consumer.get("consumer_interface", "")).strip()
    method = str(consumer.get("method", "not_evaluated")).strip() or "not_evaluated"
    threshold_review_status = (
        str(consumer.get("threshold_review_status", "not_ready")).strip() or "not_ready"
    )
    if not threshold_id or not consumer_id or not consumer_interface:
        raise ValueError("Threshold consumer projection requires ids and interface")
    current_value = consumer.get("projection_value")
    return ArtifactThresholdConsumerProjection(
        threshold_id=threshold_id,
        threshold_family=_threshold_family(threshold_id),
        consumer_id=consumer_id,
        consumer_interface=consumer_interface,
        method=method,
        unit=str(consumer.get("unit", "")),
        current_value=(
            float(current_value)
            if isinstance(current_value, (int, float)) and not isinstance(current_value, bool)
            else None
        ),
        target_runtime_mode=str(consumer.get("target_runtime_mode", "shadow") or "shadow"),
        threshold_review_status=threshold_review_status,
        threshold_fit_ready=bool(consumer.get("threshold_fit_ready", False)),
        hard_cap_binding=_optional_bool(consumer.get("hard_cap_binding")),
        source_ref=source_ref,
        detail=str(consumer.get("projection_value_semantics", "")),
    )


def build_artifact_comparison_projections(
    *,
    active_ml_artifact: DashboardArtifactTransferManifest | None = None,
    active_regime_detector_artifact: DashboardArtifactTransferManifest | None = None,
    shadow_ml_challenger_artifact: DashboardArtifactTransferManifest | None = None,
    shadow_regime_detector_challenger_artifact: DashboardArtifactTransferManifest | None = None,
    ml_comparison_ref: str = "",
    regime_detector_comparison_ref: str = "",
) -> tuple[ArtifactComparisonProjection, ...]:
    """Project bounded champion-vs-challenger evidence when challenger slots are attached."""

    projections: list[ArtifactComparisonProjection] = []
    ml_projection = _build_artifact_comparison_projection(
        champion_manifest=active_ml_artifact,
        challenger_manifest=shadow_ml_challenger_artifact,
        comparison_ref=ml_comparison_ref,
    )
    if ml_projection is not None:
        projections.append(ml_projection)
    regime_projection = _build_artifact_comparison_projection(
        champion_manifest=active_regime_detector_artifact,
        challenger_manifest=shadow_regime_detector_challenger_artifact,
        comparison_ref=regime_detector_comparison_ref,
    )
    if regime_projection is not None:
        projections.append(regime_projection)
    return tuple(projections)


def _load_comparison_evidence(path_ref: str) -> ArtifactShadowComparisonEvidence | None:
    payload = _read_text(path_ref)
    if payload is None:
        return None
    try:
        return ArtifactShadowComparisonEvidence.model_validate_json(payload)
    except (TypeError, ValueError):
        return None


def _build_artifact_comparison_projection(
    *,
    champion_manifest: DashboardArtifactTransferManifest | None,
    challenger_manifest: DashboardArtifactTransferManifest | None,
    comparison_ref: str,
) -> ArtifactComparisonProjection | None:
    if champion_manifest is None or challenger_manifest is None:
        return None
    evidence = _load_comparison_evidence(comparison_ref) if comparison_ref else None
    if evidence is None and comparison_ref:
        return ArtifactComparisonProjection(
            champion_artifact_id=champion_manifest.artifact_id or "none",
            challenger_artifact_id=challenger_manifest.artifact_id or "none",
            comparison_status="invalid_evidence",
            evidence_ref=comparison_ref,
        )
    if evidence is None:
        return ArtifactComparisonProjection(
            champion_artifact_id=champion_manifest.artifact_id or "none",
            challenger_artifact_id=challenger_manifest.artifact_id or "none",
            comparison_status="shadow_pending_evidence",
        )
    return ArtifactComparisonProjection(
        champion_artifact_id=evidence.champion_artifact_id,
        challenger_artifact_id=evidence.challenger_artifact_id,
        event_count=evidence.event_count,
        decision_diff_rate=evidence.decision_diff_rate,
        no_trade_delta=evidence.no_trade_delta,
        forecast_strength_delta_mean=evidence.forecast_strength_delta_mean,
        expected_gain_delta_mean=evidence.expected_gain_delta_mean,
        expected_cost_delta_mean=evidence.expected_cost_delta_mean,
        expected_ce_delta_mean=evidence.expected_ce_delta_mean,
        realized_slippage_delta_mean_bps=evidence.realized_slippage_delta_mean_bps,
        reason_code_diff_summary=tuple(dict.fromkeys(evidence.reason_code_diff_summary))[:8],
        sharia_policy_version=evidence.sharia_policy_version,
        sharia_scope_mode=evidence.sharia_scope_mode,
        halal_eligible_event_count=evidence.halal_eligible_event_count,
        halal_excluded_event_count=evidence.halal_excluded_event_count,
        halal_exclusion_reason_summary=tuple(
            dict.fromkeys(evidence.halal_exclusion_reason_summary)
        )[:8],
        sharia_assumption_flags=tuple(dict.fromkeys(evidence.sharia_assumption_flags))[:8],
        comparison_status=evidence.comparison_status,
        evidence_ref=comparison_ref,
    )


def build_artifact_verdict_bundle_projection(
    *,
    verdict_bundle_ref: str = "",
    verdict_bundle_status: str = "not_available",
) -> ArtifactVerdictBundleProjection | None:
    """Project one bounded daily challenger verdict bundle when present."""

    if not verdict_bundle_ref:
        if verdict_bundle_status == "not_available":
            return None
        return ArtifactVerdictBundleProjection(
            overall_verdict=verdict_bundle_status,
            evidence_ref="",
        )
    payload = _read_text(verdict_bundle_ref)
    if payload is None:
        return ArtifactVerdictBundleProjection(
            overall_verdict="invalid_evidence",
            operator_recommendation="reject_or_retrain",
            evidence_ref=verdict_bundle_ref,
        )
    try:
        verdict = ArtifactShadowVerdictBundle.model_validate_json(payload)
    except (TypeError, ValueError):
        return ArtifactVerdictBundleProjection(
            overall_verdict="invalid_evidence",
            operator_recommendation="reject_or_retrain",
            evidence_ref=verdict_bundle_ref,
        )
    return ArtifactVerdictBundleProjection(
        session_date=verdict.session_date,
        overall_verdict=verdict.overall_verdict,
        operator_recommendation=verdict.operator_recommendation,
        configured_family_count=verdict.configured_family_count,
        ready_family_count=verdict.ready_family_count,
        invalid_family_count=verdict.invalid_family_count,
        sharia_blocked_family_count=verdict.sharia_blocked_family_count,
        runtime_inputs_missing_family_count=verdict.runtime_inputs_missing_family_count,
        ml_comparison_status=verdict.ml_comparison_status,
        regime_detector_comparison_status=verdict.regime_detector_comparison_status,
        ml_comparison_ref=verdict.ml_comparison_ref,
        regime_detector_comparison_ref=verdict.regime_detector_comparison_ref,
        sharia_policy_version=verdict.sharia_policy_version,
        blocking_reasons=tuple(dict.fromkeys(verdict.blocking_reasons))[:8],
        supporting_reasons=tuple(dict.fromkeys(verdict.supporting_reasons))[:8],
        evidence_ref=verdict_bundle_ref,
    )


def _optional_bool(value: object) -> bool | None:
    if isinstance(value, bool):
        return value
    return None


__all__ = [
    "build_artifact_comparison_projections",
    "build_artifact_runtime_visibility_projections",
    "build_artifact_threshold_consumer_projections",
    "build_artifact_verdict_bundle_projection",
]
