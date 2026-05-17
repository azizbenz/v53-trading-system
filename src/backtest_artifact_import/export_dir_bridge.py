"""Typed bridge from governed LOCAL_REPLAY export directories to import/upload contracts."""

from __future__ import annotations
from datetime import date, datetime, timedelta, UTC
from pathlib import Path

from pydantic import BaseModel, Field

from backtest_artifact_import.contracts import (
    ArtifactImportDecision,
    ArtifactImportRequest,
    ArtifactPayloadRefBundle,
    ArtifactUploadDecision,
    ArtifactUploadContext,
    ArtifactUploadRequest,
)
from backtest_artifact_import.capital_profile_builder import discover_capital_profile_refs
from backtest_artifact_import.export_dir_bridge_support import (
    _load_json_payload_from_ref,
    _load_json_sidecar_with_backup,
    _load_payload_bundle_sidecars,
    _resolve_canonical_feature_entry,
    _validate_manifest_sidecar_consistency,
)
from backtest_artifact_import.export_dir_bridge_models import (
    LocalReplayExportDiscovery,
    LocalReplayImportBuildContext,
    ReplayPlanImportBuildContext,
    ReplayPlanUploadBuildContext,
)
from backtest_artifact_import.upload_bridge import (
    build_artifact_upload_decision,
    build_import_request_from_upload_request,
)
from interface_contracts import (
    ActionUnit,
    ArtifactActivationStage,
    ArtifactActionKind,
    ArtifactClass,
    ArtifactExportBundle,
    ArtifactLifecyclePolicy,
    ArtifactLogicFormat,
    ArtifactProofSummary,
    ArtifactSignatureEnvelope,
    DistilledRule,
    FeatureLineageLock,
    FeatureLineageRecord,
    HookId,
    PromotionState,
    ReviewState,
    RuntimeMode,
    TransformWhitelistId,
    TransformWhitelistLock,
    canonical_transform_ids,
)
from local_replay_runtime import (
    LocalReplayOrchestrator,
    LocalReplayRequest,
    LocalReplayRuntimeEvidence,
    ReplayClockRef,
    ReplayDatasetRef,
    ReplayExecutionPlan,
    ReplayRunManifest,
    discover_promotion_artifact_refs,
)


def _discover_export_file(
    export_dir: Path,
    *,
    label: str,
    tokens: tuple[str, ...],
    suffixes: tuple[str, ...],
    canonical_names: tuple[str, ...] = (),
) -> Path:
    candidates: list[Path] = []
    for canonical_name in canonical_names:
        candidate = export_dir / canonical_name
        if candidate.is_file():
            candidates.append(candidate.resolve())
    for item in export_dir.iterdir():
        if not item.is_file():
            continue
        lowered = item.name.lower()
        if item.suffix.lower() not in suffixes:
            continue
        if any(token in lowered for token in tokens):
            candidates.append(item.resolve())
    unique_candidates = tuple(dict.fromkeys(candidates))
    if len(unique_candidates) > 1:
        raise ValueError(
            f"Multiple governed export files found for {label}: "
            + ", ".join(path.name for path in unique_candidates)
        )
    if not unique_candidates:
        raise FileNotFoundError(
            f"Missing governed export file for {label} in {export_dir}"
        )
    return unique_candidates[0]


def _require_export_member(
    export_dir: Path,
    candidate: Path,
    *,
    label: str,
) -> Path:
    resolved_export_dir = export_dir.resolve()
    resolved_candidate = candidate.resolve()
    try:
        resolved_candidate.relative_to(resolved_export_dir)
    except ValueError as exc:
        raise ValueError(
            f"governed export {label} must resolve inside export_dir"
        ) from exc
    return resolved_candidate


def build_feature_locks_from_feature_bridge(
    feature_bridge_ref: str,
    *,
    feature_set_version: str,
    transform_set_version: str,
) -> tuple[
    FeatureLineageLock,
    TransformWhitelistLock,
    tuple[str, ...],
    tuple[TransformWhitelistId, ...],
]:
    feature_bridge_payload = _load_json_payload_from_ref(
        feature_bridge_ref,
        label="feature_bridge",
        allow_symbolic_ref=True,
    )
    embedded_feature_lineage_lock = feature_bridge_payload.get("feature_lineage_lock")
    embedded_transform_whitelist_lock = feature_bridge_payload.get("transform_whitelist_lock")
    if isinstance(embedded_feature_lineage_lock, dict):
        feature_lineage_lock = FeatureLineageLock.model_validate(
            embedded_feature_lineage_lock
        )
        if feature_lineage_lock.feature_set_version != feature_set_version:
            raise ValueError(
                "embedded feature_lineage_lock feature_set_version must match manifest"
            )
        if feature_lineage_lock.transform_set_version != transform_set_version:
            raise ValueError(
                "embedded feature_lineage_lock transform_set_version must match manifest"
            )
        if isinstance(embedded_transform_whitelist_lock, dict):
            transform_whitelist_lock = TransformWhitelistLock.model_validate(
                embedded_transform_whitelist_lock
            )
        else:
            transform_whitelist_lock = TransformWhitelistLock(
                transform_set_version=transform_set_version,
                allowed_transform_ids=tuple(
                    dict.fromkeys(
                        transform_id
                        for record in feature_lineage_lock.records
                        for transform_id in record.transform_ids
                    )
                ) or canonical_transform_ids(),
            )
        if transform_whitelist_lock.transform_set_version != transform_set_version:
            raise ValueError(
                "embedded transform_whitelist_lock transform_set_version must match manifest"
            )
        return (
            feature_lineage_lock,
            transform_whitelist_lock,
            tuple(record.feature_id for record in feature_lineage_lock.records),
            tuple(transform_whitelist_lock.allowed_transform_ids),
        )
    raw_feature_keys_payload = feature_bridge_payload.get("recognized_feature_keys")
    if raw_feature_keys_payload is None:
        raw_feature_keys_payload = feature_bridge_payload.get("feature_keys") or ()
    raw_feature_keys = tuple(str(item) for item in raw_feature_keys_payload)
    feature_ids = tuple(dict.fromkeys(raw_feature_keys))

    records: list[FeatureLineageRecord] = []
    transform_ids: list[TransformWhitelistId] = []
    for feature_id in feature_ids:
        entry = _resolve_canonical_feature_entry(feature_id)
        if entry is None:
            raise ValueError(
                f"recognized feature key has no canonical lineage mapping: {feature_id}"
            )
        records.append(
            FeatureLineageRecord(
                feature_id=feature_id,
                family=entry.family,
                source_inputs=("historical_prices",),
                transform_ids=entry.default_transform_ids,
                equation_id=entry.equation_id,
                feature_set_version=feature_set_version,
                transform_set_version=transform_set_version,
            )
        )
        transform_ids.extend(entry.default_transform_ids)

    unique_transform_ids = tuple(dict.fromkeys(transform_ids)) or canonical_transform_ids()
    return (
        FeatureLineageLock(
            feature_set_version=feature_set_version,
            transform_set_version=transform_set_version,
            records=tuple(records),
        ),
        TransformWhitelistLock(
            transform_set_version=transform_set_version,
            allowed_transform_ids=unique_transform_ids,
        ),
        feature_ids,
        unique_transform_ids,
    )


def discover_local_replay_export(export_dir: Path) -> LocalReplayExportDiscovery:
    """Discover the canonical manifest and payload refs of a governed export directory."""

    resolved_export_dir = export_dir.resolve()
    run_manifest_path = _require_export_member(
        resolved_export_dir,
        _discover_export_file(
            resolved_export_dir,
            label="replay_run_manifest",
            tokens=("replay_run_manifest", "run_manifest"),
            suffixes=(".json",),
            canonical_names=("replay_run_manifest.json",),
        ),
        label="replay_run_manifest",
    )
    payload_bundle = ArtifactPayloadRefBundle(
        review_export_ref=str(
            _require_export_member(
                resolved_export_dir,
                _discover_export_file(
                    resolved_export_dir,
                    label="review_export",
                    tokens=("review_export", "learning_review_export"),
                    suffixes=(".md", ".json", ".txt"),
                    canonical_names=("review_export.md",),
                ),
                label="review_export",
            )
        ),
        feature_bridge_ref=str(
            _require_export_member(
                resolved_export_dir,
                _discover_export_file(
                    resolved_export_dir,
                    label="feature_bridge",
                    tokens=("feature_bridge",),
                    suffixes=(".json", ".jsonl", ".csv", ".parquet"),
                    canonical_names=("feature_bridge.json",),
                ),
                label="feature_bridge",
            )
        ),
        parity_diagnostics_ref=str(
            _require_export_member(
                resolved_export_dir,
                _discover_export_file(
                    resolved_export_dir,
                    label="parity_diagnostics",
                    tokens=("parity_diagnostics",),
                    suffixes=(".json", ".jsonl", ".txt", ".csv", ".parquet"),
                    canonical_names=("parity_diagnostics.json",),
                ),
                label="parity_diagnostics",
            )
        ),
        replay_metrics_ref=str(
            _require_export_member(
                resolved_export_dir,
                _discover_export_file(
                    resolved_export_dir,
                    label="replay_metrics",
                    tokens=("replay_metrics",),
                    suffixes=(".json", ".jsonl", ".txt", ".csv", ".parquet"),
                    canonical_names=("replay_metrics.json",),
                ),
                label="replay_metrics",
            )
        ),
        replay_dtr_ref=str(
            _require_export_member(
                resolved_export_dir,
                _discover_export_file(
                    resolved_export_dir,
                    label="replay_dtr",
                    tokens=("replay_dtr",),
                    suffixes=(".json", ".jsonl", ".csv", ".parquet"),
                    canonical_names=("replay_dtr.jsonl", "replay_dtr.json"),
                ),
                label="replay_dtr",
            )
        ),
        supplementary_refs=(
            *discover_capital_profile_refs(resolved_export_dir),
            *discover_promotion_artifact_refs(resolved_export_dir),
        ),
    )
    sidecars = _load_payload_bundle_sidecars(payload_bundle)
    run_manifest = _load_json_sidecar_with_backup(
        run_manifest_path,
        label="replay_run_manifest",
        parser=ReplayRunManifest.model_validate_json,
    )
    _validate_manifest_sidecar_consistency(run_manifest, sidecars)
    return LocalReplayExportDiscovery(
        export_dir=resolved_export_dir,
        run_manifest=run_manifest,
        payload_bundle=payload_bundle,
    )


def build_replay_plan_from_export_dir(
    export_dir: Path,
    *,
    activation_stage: ArtifactActivationStage = ArtifactActivationStage.SHADOW_READY,
    candidate_ids: tuple[str, ...] | None = None,
) -> tuple[LocalReplayExportDiscovery, ReplayExecutionPlan]:
    """Rebuild the typed LOCAL_REPLAY execution plan directly from a governed export."""

    discovery = discover_local_replay_export(export_dir)
    run_manifest = discovery.run_manifest
    payload_bundle = discovery.payload_bundle
    replay_plan = LocalReplayOrchestrator.prepare_bundle(
        LocalReplayRequest(
            correlation_id=run_manifest.run_id,
            profile=run_manifest.profile_scope,
            runtime_mode=RuntimeMode.LOCAL_REPLAY,
            strategy_classification=run_manifest.strategy_classification,
            lineage_version=run_manifest.lineage_version,
            replay_reason=f"Governed local replay export {run_manifest.run_id}",
        ),
        artifact_id=run_manifest.artifact_hash,
        strategy_version=run_manifest.strategy_version,
        payload_refs=payload_bundle.payload_refs,
        dataset_ref=ReplayDatasetRef(
            dataset_id=run_manifest.dataset_manifest_id,
            pair_scope=run_manifest.tested_pairs,
            record_count=run_manifest.record_count,
        ),
        clock_ref=ReplayClockRef(
            clock_id=run_manifest.clock_id,
            mode=run_manifest.performance_mode,
            start_timestamp_ms=run_manifest.start_timestamp_ms,
            end_timestamp_ms=run_manifest.end_timestamp_ms,
            tick_count=run_manifest.tick_count,
        ),
        candidate_ids=(
            candidate_ids
            if candidate_ids is not None
            else (f"candidate:{run_manifest.strategy_id}",)
        ),
        review_export_ref=payload_bundle.review_export_ref,
        feature_bridge_ref=payload_bundle.feature_bridge_ref,
        parity_diagnostics_ref=payload_bundle.parity_diagnostics_ref,
        replay_metrics_ref=payload_bundle.replay_metrics_ref,
        replay_dtr_ref=payload_bundle.replay_dtr_ref,
        notes=(
            "Governed local replay export path for LOCAL_REPLAY -> VPS import -> SHADOW. "
            f"strategy_id={run_manifest.strategy_id} / "
            f"feature_set={run_manifest.feature_set_version} / "
            f"formula_set={run_manifest.formula_set_version} / "
            f"scoring={run_manifest.scoring_version} / "
            f"regime={run_manifest.regime_version} / "
            f"risk={run_manifest.risk_policy_version} / "
            f"cost={run_manifest.cost_model_version} / "
            f"performance_mode={run_manifest.performance_mode} / "
            f"artifact_schema={run_manifest.artifact_schema_version}"
        ),
    )
    replay_plan = replay_plan.model_copy(
        update={
            "bundle": replay_plan.bundle.model_copy(
                update={
                    "manifest": replay_plan.bundle.manifest.model_copy(
                        update={
                            "activation_stage": activation_stage,
                            "artifact_schema_version": run_manifest.artifact_schema_version,
                            "feature_set_version": run_manifest.feature_set_version,
                            "transform_set_version": run_manifest.transform_set_version,
                        }
                    )
                }
            )
        }
    )
    return discovery, replay_plan


def build_import_context_from_replay_plan(
    replay_plan: ReplayExecutionPlan,
    *,
    payload_bundle: ArtifactPayloadRefBundle,
    lifecycle_policy: ArtifactLifecyclePolicy,
    training_end: date,
    governance_reference_date: date,
    drift_score_threshold: float,
    observed_drift_score: float | None = None,
) -> ReplayPlanImportBuildContext:
    """Build a typed governed import handshake from a replay plan and payload bundle."""

    manifest = replay_plan.bundle.manifest
    (
        feature_lineage_lock,
        transform_whitelist_lock,
        expected_feature_ids,
        expected_transform_ids,
    ) = build_feature_locks_from_feature_bridge(
        payload_bundle.feature_bridge_ref,
        feature_set_version=manifest.feature_set_version,
        transform_set_version=manifest.transform_set_version,
    )

    import_request = ArtifactImportRequest(
        manifest=manifest,
        artifact_kind=replay_plan.bundle.artifact_kind,
        payload_bundle=payload_bundle,
        payload_refs=replay_plan.bundle.payload_refs,
        feature_lineage_lock=feature_lineage_lock,
        feature_lineage_required=True,
        expected_feature_ids=expected_feature_ids,
        transform_whitelist_lock=transform_whitelist_lock,
        transform_whitelist_required=True,
        expected_transform_ids=expected_transform_ids,
        lifecycle_policy=lifecycle_policy,
        training_end=training_end,
        governance_reference_date=governance_reference_date,
        drift_score_threshold=drift_score_threshold,
        observed_drift_score=observed_drift_score,
    )
    return ReplayPlanImportBuildContext(
        replay_plan=replay_plan,
        feature_lineage_lock=feature_lineage_lock,
        transform_whitelist_lock=transform_whitelist_lock,
        expected_feature_ids=expected_feature_ids,
        expected_transform_ids=expected_transform_ids,
        import_request=import_request,
    )


def build_artifact_export_bundle_from_replay_import_context(
    import_context: ReplayPlanImportBuildContext,
    *,
    local_replay_evidence: LocalReplayRuntimeEvidence,
    signature_envelope: ArtifactSignatureEnvelope,
    artifact_class: ArtifactClass,
    artifact_scope: str,
    governance_reference_date: date,
    lifecycle_policy: ArtifactLifecyclePolicy,
    drift_score_threshold: float,
    proof_summary: ArtifactProofSummary,
    artifact_version: str = "1.0.0",
    distilled_logic_format: ArtifactLogicFormat | None = None,
    rules: tuple[DistilledRule, ...] = (),
    allowed_hook_ids: tuple[HookId, ...] | None = None,
    allowed_action_kinds: tuple[ArtifactActionKind, ...] | None = None,
    allowed_action_units: tuple[ActionUnit, ...] | None = None,
    regime_features_used: tuple[str, ...] = (),
    covariance_shrinkage_matrix_ref: str = "matrix_ref:governed_replay",
) -> ArtifactExportBundle:
    """Build a governed artifact export bundle from replay/import state plus explicit proof metadata."""

    if not local_replay_evidence.replay_useful_ready:
        raise ValueError(
            "Artifact export bundle requires replay_useful_ready local replay evidence"
        )

    replay_plan = import_context.replay_plan
    manifest = replay_plan.bundle.manifest
    dataset_id = (
        replay_plan.dataset_ref.dataset_id
        if replay_plan.dataset_ref is not None
        else manifest.dataset_ref
    )
    if not dataset_id:
        raise ValueError("Artifact export bundle requires a governed dataset_id")

    if replay_plan.clock_ref is not None:
        training_start = datetime.fromtimestamp(
            replay_plan.clock_ref.start_timestamp_ms / 1000.0,
            tz=UTC,
        ).date()
    else:
        training_start = governance_reference_date - timedelta(days=1)
    training_end = governance_reference_date

    resolved_logic_format = distilled_logic_format
    if resolved_logic_format is None:
        if manifest.distilled_logic_format == ArtifactLogicFormat.RULE_AST_JSON and not rules:
            resolved_logic_format = ArtifactLogicFormat.THRESHOLD_JSON
        else:
            resolved_logic_format = manifest.distilled_logic_format

    return ArtifactExportBundle(
        artifact_id=manifest.artifact_id,
        artifact_version=artifact_version,
        artifact_class=artifact_class,
        artifact_scope=artifact_scope,
        allowed_hook_ids=(
            manifest.allowed_hook_ids if allowed_hook_ids is None else allowed_hook_ids
        ),
        allowed_action_kinds=(
            manifest.allowed_action_kinds
            if allowed_action_kinds is None
            else allowed_action_kinds
        ),
        allowed_action_units=(
            manifest.allowed_action_units
            if allowed_action_units is None
            else allowed_action_units
        ),
        distilled_logic_format=resolved_logic_format,
        rules=rules,
        payload_hash_sha256=signature_envelope.payload_hash_sha256,
        public_key_author_sig=signature_envelope.public_key_author_sig,
        dataset_id=dataset_id,
        feature_set_version=manifest.feature_set_version,
        transform_set_version=manifest.transform_set_version,
        feature_lineage_lock=import_context.feature_lineage_lock,
        transform_whitelist_lock=import_context.transform_whitelist_lock,
        training_start=training_start,
        training_end=training_end,
        lifecycle_policy=lifecycle_policy,
        regime_features_used=regime_features_used,
        covariance_shrinkage_matrix_ref=covariance_shrinkage_matrix_ref,
        drift_score_threshold=drift_score_threshold,
        proof_summary=proof_summary,
    )


def build_upload_request_from_replay_plan(
    replay_plan: ReplayExecutionPlan,
    *,
    payload_bundle: ArtifactPayloadRefBundle,
    bundle: ArtifactExportBundle,
    signature_envelope: ArtifactSignatureEnvelope,
    uploaded_by: str,
    upload_context: ArtifactUploadContext,
    governance_reference_date: date,
    target_runtime_mode: RuntimeMode = RuntimeMode.SHADOW,
    requested_promotion_state: PromotionState = PromotionState.REPLAY_ONLY,
    review_state: ReviewState = ReviewState.PENDING,
) -> ArtifactUploadRequest:
    """Build a governed upload dry-run request from a replay plan and upload metadata."""

    manifest = replay_plan.bundle.manifest.model_copy(
        update={
            "allowed_hook_ids": bundle.allowed_hook_ids,
            "allowed_action_kinds": bundle.allowed_action_kinds,
            "allowed_action_units": bundle.allowed_action_units,
            "distilled_logic_format": bundle.distilled_logic_format,
            "signature_envelope": signature_envelope,
        }
    )
    return ArtifactUploadRequest(
        bundle=bundle,
        manifest=manifest,
        payload_bundle=payload_bundle,
        uploaded_by=uploaded_by,
        upload_context=upload_context,
        governance_reference_date=governance_reference_date,
        artifact_kind=replay_plan.bundle.artifact_kind,
        target_runtime_mode=target_runtime_mode,
        requested_promotion_state=requested_promotion_state,
        review_state=review_state,
    )


def build_upload_context_from_replay_import_context(
    import_context: ReplayPlanImportBuildContext,
    *,
    local_replay_evidence: LocalReplayRuntimeEvidence,
    signature_envelope: ArtifactSignatureEnvelope,
    uploaded_by: str,
    upload_context: ArtifactUploadContext,
    governance_reference_date: date,
    artifact_class: ArtifactClass,
    artifact_scope: str,
    lifecycle_policy: ArtifactLifecyclePolicy,
    drift_score_threshold: float,
    proof_summary: ArtifactProofSummary,
    artifact_version: str = "1.0.0",
    distilled_logic_format: ArtifactLogicFormat | None = None,
    rules: tuple[DistilledRule, ...] = (),
    allowed_hook_ids: tuple[HookId, ...] | None = None,
    allowed_action_kinds: tuple[ArtifactActionKind, ...] | None = None,
    allowed_action_units: tuple[ActionUnit, ...] | None = None,
    regime_features_used: tuple[str, ...] = (),
    covariance_shrinkage_matrix_ref: str = "matrix_ref:governed_replay",
    target_runtime_mode: RuntimeMode = RuntimeMode.SHADOW,
    requested_promotion_state: PromotionState = PromotionState.REPLAY_ONLY,
    review_state: ReviewState = ReviewState.PENDING,
    import_decision: ArtifactImportDecision | None = None,
) -> ReplayPlanUploadBuildContext:
    """Build the full replay/evidence -> upload -> import contract chain."""

    payload_bundle = import_context.import_request.payload_bundle
    if payload_bundle is None:
        raise ValueError("Replay upload context requires a governed payload bundle")

    artifact_bundle = build_artifact_export_bundle_from_replay_import_context(
        import_context,
        local_replay_evidence=local_replay_evidence,
        signature_envelope=signature_envelope,
        artifact_class=artifact_class,
        artifact_scope=artifact_scope,
        governance_reference_date=governance_reference_date,
        lifecycle_policy=lifecycle_policy,
        drift_score_threshold=drift_score_threshold,
        proof_summary=proof_summary,
        artifact_version=artifact_version,
        distilled_logic_format=distilled_logic_format,
        rules=rules,
        allowed_hook_ids=allowed_hook_ids,
        allowed_action_kinds=allowed_action_kinds,
        allowed_action_units=allowed_action_units,
        regime_features_used=regime_features_used,
        covariance_shrinkage_matrix_ref=covariance_shrinkage_matrix_ref,
    )
    upload_request = build_upload_request_from_replay_plan(
        import_context.replay_plan,
        payload_bundle=payload_bundle,
        bundle=artifact_bundle,
        signature_envelope=signature_envelope,
        uploaded_by=uploaded_by,
        upload_context=upload_context,
        governance_reference_date=governance_reference_date,
        target_runtime_mode=target_runtime_mode,
        requested_promotion_state=requested_promotion_state,
        review_state=review_state,
    )
    upload_import_request = build_import_request_from_upload_request(upload_request)
    return ReplayPlanUploadBuildContext(
        import_context=import_context,
        local_replay_evidence=local_replay_evidence,
        artifact_bundle=artifact_bundle,
        signature_envelope=signature_envelope,
        upload_request=upload_request,
        import_request=upload_import_request,
        import_decision=import_decision,
        upload_decision=(
            None
            if import_decision is None
            else build_artifact_upload_decision(upload_request, import_decision)
        ),
    )


def build_import_context_from_export_dir(
    export_dir: Path,
    *,
    lifecycle_policy: ArtifactLifecyclePolicy,
    training_end: date,
    governance_reference_date: date,
    drift_score_threshold: float,
    observed_drift_score: float | None = None,
) -> LocalReplayImportBuildContext:
    """Build the full typed import handshake directly from a governed export directory."""

    discovery, replay_plan = build_replay_plan_from_export_dir(export_dir)
    plan_context = build_import_context_from_replay_plan(
        replay_plan,
        payload_bundle=discovery.payload_bundle,
        lifecycle_policy=lifecycle_policy,
        training_end=training_end,
        governance_reference_date=governance_reference_date,
        drift_score_threshold=drift_score_threshold,
        observed_drift_score=observed_drift_score,
    )
    return LocalReplayImportBuildContext(
        export_discovery=discovery,
        replay_plan=plan_context.replay_plan,
        feature_lineage_lock=plan_context.feature_lineage_lock,
        transform_whitelist_lock=plan_context.transform_whitelist_lock,
        expected_feature_ids=plan_context.expected_feature_ids,
        expected_transform_ids=plan_context.expected_transform_ids,
        import_request=plan_context.import_request,
    )


def build_upload_request_from_export_dir(
    export_dir: Path,
    *,
    bundle: ArtifactExportBundle,
    signature_envelope: ArtifactSignatureEnvelope,
    uploaded_by: str,
    upload_context: ArtifactUploadContext,
    governance_reference_date: date,
    target_runtime_mode: RuntimeMode = RuntimeMode.SHADOW,
    requested_promotion_state: PromotionState = PromotionState.REPLAY_ONLY,
    review_state: ReviewState = ReviewState.PENDING,
) -> ArtifactUploadRequest:
    """Build a governed upload dry-run request from a typed export directory plus upload metadata."""

    discovery, replay_plan = build_replay_plan_from_export_dir(export_dir)
    return build_upload_request_from_replay_plan(
        replay_plan,
        payload_bundle=discovery.payload_bundle,
        bundle=bundle,
        signature_envelope=signature_envelope,
        uploaded_by=uploaded_by,
        upload_context=upload_context,
        governance_reference_date=governance_reference_date,
        target_runtime_mode=target_runtime_mode,
        requested_promotion_state=requested_promotion_state,
        review_state=review_state,
    )


__all__ = [
    "LocalReplayExportDiscovery",
    "ReplayPlanImportBuildContext",
    "ReplayPlanUploadBuildContext",
    "LocalReplayImportBuildContext",
    "build_feature_locks_from_feature_bridge",
    "discover_local_replay_export",
    "build_replay_plan_from_export_dir",
    "build_import_context_from_replay_plan",
    "build_artifact_export_bundle_from_replay_import_context",
    "build_upload_request_from_replay_plan",
    "build_upload_context_from_replay_import_context",
    "build_import_context_from_export_dir",
    "build_upload_request_from_export_dir",
]
