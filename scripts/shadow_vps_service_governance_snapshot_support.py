#!/usr/bin/env python3
"""Governance snapshot persistence for the Shadow VPS service."""

from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path

from complete_enablers import evaluate_ml_model_promotion_gate
from interface_contracts import (
    DashboardArtifactTransferManifest,
    MlLiveDriftSnapshot,
    MlModelArtifact,
)
from interface_contracts.atomic_io import atomic_write_json
from local_replay_runtime.ml_governance_sidecars import (
    ML_ANTI_LEAKAGE_PROOF_FILENAME,
    ML_LIVE_DRIFT_SNAPSHOT_FILENAME,
    build_ml_live_drift_snapshot,
    load_ml_anti_leakage_proof,
    load_ml_live_drift_snapshot,
)
from meta_learning.model_risk_registry import (
    MlModelDriftSnapshot as RuntimeDriftSnapshot,
    MlModelRuntimeStage,
)
from monitoring.contracts_artifacts import ArtifactShadowComparisonEvidence
from run_governance_snapshot_seed import (
    synthesise_refusal_journal,
)
from shadow_vps_service_models import ShadowVpsServiceRuntimeContext


def _resolve_build_root(context: ShadowVpsServiceRuntimeContext) -> Path:
    try:
        return context.service_dir.resolve().parents[1]
    except IndexError:
        return context.service_dir.resolve().parent


def _hash_payload(payload: object) -> str:
    return hashlib.sha256(
        json.dumps(
            payload,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8")
    ).hexdigest()


def _load_json_model(path: Path, model_type: type[object]) -> object | None:
    if not path.is_file():
        return None
    try:
        return model_type.model_validate_json(path.read_text(encoding="utf-8-sig"))
    except (AttributeError, OSError, TypeError, ValueError):
        return None


def _load_ml_artifact(manifest: DashboardArtifactTransferManifest | None) -> MlModelArtifact | None:
    if manifest is None or not manifest.source_ref:
        return None
    artifact_path = Path(manifest.source_ref).resolve()
    return _load_json_model(artifact_path, MlModelArtifact)  # type: ignore[return-value]


def _adjacent_sidecar_path(
    manifest: DashboardArtifactTransferManifest,
    filename: str,
) -> Path:
    return (Path(manifest.source_ref).resolve().parent / filename).resolve()


def _load_shadow_ml_comparison_evidence(
    context: ShadowVpsServiceRuntimeContext,
) -> ArtifactShadowComparisonEvidence | None:
    ref = str(context.store.state.last_shadow_ml_artifact_comparison_ref or "").strip()
    if not ref:
        return None
    return _load_json_model(
        Path(ref).resolve(),
        ArtifactShadowComparisonEvidence,
    )  # type: ignore[return-value]


def _build_shadow_runtime_drift_snapshot(
    evidence: ArtifactShadowComparisonEvidence | None,
    *,
    ce_sign: float = 1.0,
) -> RuntimeDriftSnapshot | None:
    if evidence is None or evidence.artifact_family != "ml":
        return None
    if evidence.comparison_status != "shadow_ready" or evidence.event_count <= 0:
        return None
    return RuntimeDriftSnapshot(
        stage=MlModelRuntimeStage.SHADOW,
        created_at=datetime.now(tz=UTC),
        feature_ks_pvalue=None,
        shadow_diff_pct=evidence.decision_diff_rate,
        live_diff_pct=None,
        win_rate_delta=None,
        ce_delta=evidence.expected_ce_delta_mean * ce_sign,
    )


def _ensure_manifest_payload_refs(
    manifest: DashboardArtifactTransferManifest,
    *refs: str,
) -> DashboardArtifactTransferManifest:
    merged_refs = tuple(dict.fromkeys((*manifest.payload_refs, *(ref for ref in refs if ref))))
    if merged_refs == manifest.payload_refs:
        return manifest
    return manifest.model_copy(update={"payload_refs": merged_refs})


def _persist_challenger_shadow_drift_sidecar(
    manifest: DashboardArtifactTransferManifest | None,
    *,
    evidence: ArtifactShadowComparisonEvidence | None,
) -> tuple[DashboardArtifactTransferManifest | None, MlLiveDriftSnapshot | None]:
    if manifest is None:
        return None, None
    artifact = _load_ml_artifact(manifest)
    if artifact is None:
        return manifest, None
    runtime_snapshot = _build_shadow_runtime_drift_snapshot(evidence, ce_sign=1.0)
    sidecar_refs: list[str] = []
    anti_leakage_path = _adjacent_sidecar_path(manifest, ML_ANTI_LEAKAGE_PROOF_FILENAME)
    if anti_leakage_path.is_file():
        sidecar_refs.append(str(anti_leakage_path))
    live_drift_path = _adjacent_sidecar_path(manifest, ML_LIVE_DRIFT_SNAPSHOT_FILENAME)
    live_drift_snapshot = None
    if runtime_snapshot is not None:
        try:
            live_drift_snapshot = build_ml_live_drift_snapshot(
                artifact,
                runtime_snapshot=runtime_snapshot,
                created_at=runtime_snapshot.created_at,
                input_data_hash=(
                    None if evidence is None else _hash_payload(evidence.model_dump(mode="json"))
                ),
            )
            atomic_write_json(
                live_drift_path,
                live_drift_snapshot.model_dump(mode="json"),
                indent=2,
            )
            sidecar_refs.append(str(live_drift_path))
        except (OSError, TypeError, ValueError):
            live_drift_snapshot = None
    elif live_drift_path.is_file():
        sidecar_refs.append(str(live_drift_path))
        live_drift_snapshot = _load_json_model(
            live_drift_path,
            MlLiveDriftSnapshot,
        )  # type: ignore[assignment]
    return _ensure_manifest_payload_refs(manifest, *sidecar_refs), live_drift_snapshot


def _load_anti_leakage_proof(
    manifest: DashboardArtifactTransferManifest | None,
):
    if manifest is None:
        return None
    proof_path = _adjacent_sidecar_path(manifest, ML_ANTI_LEAKAGE_PROOF_FILENAME)
    if not proof_path.is_file():
        return None
    try:
        return load_ml_anti_leakage_proof(proof_path)
    except (OSError, TypeError, ValueError):
        return None


def _load_live_drift_snapshot(
    manifest: DashboardArtifactTransferManifest | None,
):
    if manifest is None:
        return None
    snapshot_path = _adjacent_sidecar_path(manifest, ML_LIVE_DRIFT_SNAPSHOT_FILENAME)
    if not snapshot_path.is_file():
        return None
    try:
        return load_ml_live_drift_snapshot(snapshot_path)
    except (OSError, TypeError, ValueError):
        return None


def _drift_score_from_snapshot(snapshot: object | None) -> float | None:
    if snapshot is None:
        return None
    live_diff = getattr(snapshot, "live_diff_pct", None)
    if isinstance(live_diff, (int, float)):
        return float(live_diff)
    shadow_diff = getattr(snapshot, "shadow_diff_pct", None)
    if isinstance(shadow_diff, (int, float)):
        return float(shadow_diff)
    return None


def _artifact_reference_payload(
    manifest: DashboardArtifactTransferManifest | None,
    *,
    drift_score: float | None = None,
    review_state: str | None = None,
) -> dict[str, object] | None:
    if manifest is None:
        return None
    return {
        "kind": manifest.artifact_kind.value,
        "profile_id": manifest.artifact_id or manifest.feature_profile or manifest.artifact_kind.value,
        "version": manifest.lineage_version or manifest.feature_set_version,
        "sha256": manifest.artifact_hash,
        "last_validated_at": datetime.now(tz=UTC).isoformat(),
        "drift_score": drift_score,
        "review_state": review_state or manifest.review_state or manifest.validation_status,
    }


def _synthesise_model_risk_register_payload(
    context: ShadowVpsServiceRuntimeContext,
    *,
    build_root: Path,
) -> tuple[dict[str, object], dict[str, object]]:
    del build_root  # The current source of truth is the persisted service state.
    state = context.store.state
    active_ml_manifest = state.active_ml_artifact
    shadow_ml_manifest = state.shadow_ml_challenger_artifact
    ml_comparison_evidence = _load_shadow_ml_comparison_evidence(context)
    updated_shadow_ml_manifest, challenger_live_drift_snapshot = _persist_challenger_shadow_drift_sidecar(
        shadow_ml_manifest,
        evidence=ml_comparison_evidence,
    )
    active_live_drift_snapshot = _load_live_drift_snapshot(active_ml_manifest)
    challenger_anti_leakage_proof = _load_anti_leakage_proof(updated_shadow_ml_manifest)
    challenger_artifact = _load_ml_artifact(updated_shadow_ml_manifest)
    promotion_eligible = False
    promotion_blocking_reasons: tuple[str, ...] = ()
    if challenger_artifact is not None:
        verdict = evaluate_ml_model_promotion_gate(
            challenger_artifact,
            anti_leakage_proof=challenger_anti_leakage_proof,
            live_drift_snapshot=challenger_live_drift_snapshot,
        )
        promotion_eligible = verdict.passed
        promotion_blocking_reasons = verdict.blocking_reasons

    state_updates: dict[str, object] = {}
    if updated_shadow_ml_manifest is not None and updated_shadow_ml_manifest != shadow_ml_manifest:
        state_updates["shadow_ml_challenger_artifact"] = updated_shadow_ml_manifest

    payload: dict[str, object] = {
        "snapshot_at": datetime.now(tz=UTC).isoformat(),
        "source": "shadow_vps_service_governance_snapshot_support",
        "source_status": "ok",
        "active_ml": _artifact_reference_payload(
            active_ml_manifest,
            drift_score=_drift_score_from_snapshot(active_live_drift_snapshot),
        ),
        "active_regime_detector": _artifact_reference_payload(
            state.active_regime_detector_artifact,
        ),
        "shadow_ml_challenger": _artifact_reference_payload(
            updated_shadow_ml_manifest,
            drift_score=(
                _drift_score_from_snapshot(challenger_live_drift_snapshot)
                if challenger_live_drift_snapshot is not None
                else (
                    None
                    if ml_comparison_evidence is None
                    else float(ml_comparison_evidence.decision_diff_rate)
                )
            ),
            review_state=state.last_shadow_ml_artifact_comparison_status,
        ),
        "shadow_regime_detector_challenger": _artifact_reference_payload(
            state.shadow_regime_detector_challenger_artifact,
            review_state=state.last_shadow_regime_detector_artifact_comparison_status,
        ),
        "promotion_eligible": promotion_eligible,
        "promotion_blocking_reasons": promotion_blocking_reasons,
        "info_note": (
            "Derived from persisted Shadow service manifests and bounded comparison evidence. "
            "ML promotion remains fail-closed unless anti-leakage and governed SHADOW/LIVE "
            "drift evidence are both present and green."
        ),
    }
    return payload, state_updates


def _refresh_shadow_vps_governance_snapshots(
    context: ShadowVpsServiceRuntimeContext,
) -> tuple[Path, Path]:
    service_dir = context.service_dir.resolve()
    build_root = _resolve_build_root(context)
    refusal_payload = synthesise_refusal_journal(
        auto_exports_root=context.resolved_auto_exports_root,
        build_root=build_root,
    )
    model_risk_payload, state_updates = _synthesise_model_risk_register_payload(
        context,
        build_root=build_root,
    )
    if state_updates:
        context.store.update_state(**state_updates)
    refusal_path = service_dir / "refusal_journal.snapshot.json"
    model_risk_path = service_dir / "model_risk_register.snapshot.json"
    atomic_write_json(refusal_path, refusal_payload, indent=2)
    atomic_write_json(model_risk_path, model_risk_payload, indent=2)
    return refusal_path, model_risk_path


__all__ = ["_refresh_shadow_vps_governance_snapshots"]
