"""Typed bridge from governed LOCAL_REPLAY export directories to import/upload contracts."""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, UTC
from pathlib import Path
from typing import Callable, TypeVar

from pydantic import BaseModel, Field, ValidationError

from backtest_artifact_import.contracts import (
    ArtifactImportDecision,
    ArtifactImportRequest,
    ArtifactPayloadRefBundle,
    ArtifactUploadDecision,
    ArtifactUploadContext,
    ArtifactUploadRequest,
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
    CANONICAL_PHYSICS_FEATURE_DICTIONARY,
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
    ReplayMetricsSummary,
    ReplayParityDiagnosticsSummary,
    ReplayRunManifest,
    build_replay_metrics_summary,
)
from meta_minimal.dtr_core.dtr_record_builder import DTRRecord

_LoadedBridgeModelT = TypeVar("_LoadedBridgeModelT")


class LocalReplayExportDiscovery(BaseModel, frozen=True):
    """Stable discovery result for a governed LOCAL_REPLAY export directory."""

    export_dir: Path
    run_manifest: ReplayRunManifest
    payload_bundle: ArtifactPayloadRefBundle


class ReplayPlanImportBuildContext(BaseModel, frozen=True):
    """Typed materialization of a governed replay plan into an import handshake."""

    replay_plan: ReplayExecutionPlan
    feature_lineage_lock: FeatureLineageLock
    transform_whitelist_lock: TransformWhitelistLock
    expected_feature_ids: tuple[str, ...] = ()
    expected_transform_ids: tuple[TransformWhitelistId, ...] = ()
    import_request: ArtifactImportRequest


class LocalReplayImportBuildContext(ReplayPlanImportBuildContext, frozen=True):
    """Typed materialization of the governed export -> import handshake."""

    export_discovery: LocalReplayExportDiscovery


class ReplayPlanUploadBuildContext(BaseModel, frozen=True):
    """Typed materialization of replay evidence into governed upload/import contracts."""

    import_context: ReplayPlanImportBuildContext
    local_replay_evidence: LocalReplayRuntimeEvidence
    artifact_bundle: ArtifactExportBundle
    signature_envelope: ArtifactSignatureEnvelope
    upload_request: ArtifactUploadRequest
    import_request: ArtifactImportRequest
    import_decision: ArtifactImportDecision | None = None
    upload_decision: ArtifactUploadDecision | None = None


class _ValidatedReplaySidecars(BaseModel, frozen=True):
    """Typed governed sidecars loaded from an export directory."""

    review_export_text: str
    feature_bridge_payload: dict
    parity_diagnostics: ReplayParityDiagnosticsSummary
    replay_metrics: ReplayMetricsSummary
    replay_dtr_records: tuple[DTRRecord, ...]


def _resolve_canonical_feature_entry(feature_id: str):
    entry = CANONICAL_PHYSICS_FEATURE_DICTIONARY.get(feature_id)
    if entry is not None:
        return entry

    if "_" in feature_id:
        prefix, suffix = feature_id.rsplit("_", 1)
        if suffix.endswith("m") and suffix[:-1].isdigit():
            return CANONICAL_PHYSICS_FEATURE_DICTIONARY.get(prefix)

    return None


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


def _load_json_sidecar_with_backup(
    path: Path,
    *,
    label: str,
    parser: Callable[[str], _LoadedBridgeModelT],
) -> _LoadedBridgeModelT:
    try:
        return parser(path.read_text(encoding="utf-8"))
    except (OSError, ValidationError, json.JSONDecodeError, TypeError, ValueError) as exc:
        backup = path.with_suffix(".corrupted")
        try:
            path.replace(backup)
        except OSError:
            pass
        raise ValueError(
            f"governed export sidecar is corrupted for {label}: {path.name}"
        ) from exc


def _load_json_payload_from_ref(
    ref: str,
    *,
    label: str,
    allow_symbolic_ref: bool = False,
) -> dict:
    candidate = Path(ref)
    if not candidate.is_file():
        if allow_symbolic_ref and not candidate.exists():
            return {}
        raise FileNotFoundError(f"Missing governed export file for {label}: {candidate}")
    if candidate.suffix.lower() not in {".json", ".jsonl"}:
        raise ValueError(
            f"governed export file for {label} must be JSON/JSONL, got {candidate.suffix!r}"
        )
    payload = _load_json_sidecar_with_backup(
        candidate,
        label=label,
        parser=json.loads,
    )
    if not isinstance(payload, dict):
        raise ValueError(f"governed export file for {label} must deserialize to a mapping")
    return payload


def _validate_text_sidecar(ref: str, *, label: str) -> None:
    candidate = Path(ref)
    if not candidate.is_file():
        raise FileNotFoundError(f"Missing governed export file for {label}: {candidate}")
    try:
        text = candidate.read_text(encoding="utf-8")
    except OSError as exc:
        backup = candidate.with_suffix(".corrupted")
        try:
            candidate.replace(backup)
        except OSError:
            pass
        raise ValueError(
            f"governed export sidecar is corrupted for {label}: {candidate.name}"
        ) from exc
    if not text.strip():
        raise ValueError(f"governed export file for {label} must not be empty")


def _load_text_sidecar(ref: str, *, label: str) -> str:
    candidate = Path(ref)
    if not candidate.is_file():
        raise FileNotFoundError(f"Missing governed export file for {label}: {candidate}")
    try:
        text = candidate.read_text(encoding="utf-8")
    except OSError as exc:
        backup = candidate.with_suffix(".corrupted")
        try:
            candidate.replace(backup)
        except OSError:
            pass
        raise ValueError(
            f"governed export sidecar is corrupted for {label}: {candidate.name}"
        ) from exc
    if not text.strip():
        raise ValueError(f"governed export file for {label} must not be empty")
    return text


def _validate_jsonl_sidecar(ref: str, *, label: str) -> None:
    candidate = Path(ref)
    if not candidate.is_file():
        raise FileNotFoundError(f"Missing governed export file for {label}: {candidate}")
    try:
        text = candidate.read_text(encoding="utf-8")
        suffix = candidate.suffix.lower()
        if suffix == ".json":
            payload = json.loads(text)
            if not isinstance(payload, list):
                raise ValueError("JSON replay_dtr payload must deserialize to a list")
            for item in payload:
                DTRRecord.model_validate(item)
            return
        if suffix != ".jsonl":
            raise ValueError(f"unsupported suffix {candidate.suffix!r}")
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            DTRRecord.model_validate(json.loads(stripped))
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        backup = candidate.with_suffix(".corrupted")
        try:
            candidate.replace(backup)
        except OSError:
            pass
        raise ValueError(
            f"governed export sidecar is corrupted for {label}: {candidate.name}"
        ) from exc


def _load_replay_dtr_records(ref: str, *, label: str) -> tuple[DTRRecord, ...]:
    candidate = Path(ref)
    if not candidate.is_file():
        raise FileNotFoundError(f"Missing governed export file for {label}: {candidate}")
    try:
        text = candidate.read_text(encoding="utf-8")
        suffix = candidate.suffix.lower()
        if suffix == ".json":
            payload = json.loads(text)
            if not isinstance(payload, list):
                raise ValueError("JSON replay_dtr payload must deserialize to a list")
            return tuple(DTRRecord.model_validate(item) for item in payload)
        if suffix != ".jsonl":
            raise ValueError(f"unsupported suffix {candidate.suffix!r}")
        records: list[DTRRecord] = []
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            records.append(DTRRecord.model_validate(json.loads(stripped)))
        return tuple(records)
    except (OSError, ValidationError, json.JSONDecodeError, TypeError, ValueError) as exc:
        backup = candidate.with_suffix(".corrupted")
        try:
            candidate.replace(backup)
        except OSError:
            pass
        raise ValueError(
            f"governed export sidecar is corrupted for {label}: {candidate.name}"
        ) from exc


def _load_payload_bundle_sidecars(
    payload_bundle: ArtifactPayloadRefBundle,
) -> _ValidatedReplaySidecars:
    review_export_text = _load_text_sidecar(
        payload_bundle.review_export_ref,
        label="review_export",
    )
    feature_bridge_payload = _load_json_payload_from_ref(
        payload_bundle.feature_bridge_ref,
        label="feature_bridge",
    )
    parity_diagnostics = _load_json_sidecar_with_backup(
        Path(payload_bundle.parity_diagnostics_ref),
        label="parity_diagnostics",
        parser=ReplayParityDiagnosticsSummary.model_validate_json,
    )
    replay_metrics = _load_json_sidecar_with_backup(
        Path(payload_bundle.replay_metrics_ref),
        label="replay_metrics",
        parser=ReplayMetricsSummary.model_validate_json,
    )
    replay_dtr_records = _load_replay_dtr_records(
        payload_bundle.replay_dtr_ref,
        label="replay_dtr",
    )
    return _ValidatedReplaySidecars(
        review_export_text=review_export_text,
        feature_bridge_payload=feature_bridge_payload,
        parity_diagnostics=parity_diagnostics,
        replay_metrics=replay_metrics,
        replay_dtr_records=replay_dtr_records,
    )


def _parse_review_export_fields(review_export_text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for raw_line in review_export_text.splitlines():
        line = raw_line.strip()
        if not line.startswith("- "):
            continue
        payload = line[2:]
        if ":" not in payload:
            continue
        key, value = payload.split(":", 1)
        fields[key.strip()] = value.strip()
    return fields


def _validate_manifest_sidecar_consistency(
    run_manifest: ReplayRunManifest,
    sidecars: _ValidatedReplaySidecars,
) -> None:
    review_export_fields = _parse_review_export_fields(sidecars.review_export_text)
    parity_diagnostics = sidecars.parity_diagnostics
    replay_metrics = sidecars.replay_metrics
    replay_dtr_records = sidecars.replay_dtr_records
    feature_bridge_payload = sidecars.feature_bridge_payload

    required_review_fields = (
        "run_id",
        "strategy_id",
        "strategy_version",
        "lineage_version",
        "profile_scope",
        "runtime_mode",
        "performance_mode",
        "total_opportunities",
        "total_records",
        "dtr_coverage",
        "status",
        "decision_match_rate",
    )
    missing_review_fields = tuple(
        field_name
        for field_name in required_review_fields
        if field_name not in review_export_fields
    )
    if missing_review_fields:
        raise ValueError(
            "governed export review_export is missing required provenance fields: "
            + ", ".join(missing_review_fields)
        )
    if review_export_fields["run_id"] != run_manifest.run_id:
        raise ValueError(
            "governed export review_export run_id must match replay_run_manifest run_id"
        )
    if review_export_fields["strategy_id"] != run_manifest.strategy_id:
        raise ValueError(
            "governed export review_export strategy_id must match replay_run_manifest strategy_id"
        )
    if review_export_fields["strategy_version"] != run_manifest.strategy_version:
        raise ValueError(
            "governed export review_export strategy_version must match replay_run_manifest strategy_version"
        )
    if review_export_fields["lineage_version"] != run_manifest.lineage_version:
        raise ValueError(
            "governed export review_export lineage_version must match replay_run_manifest lineage_version"
        )
    if review_export_fields["profile_scope"] != run_manifest.profile_scope.value:
        raise ValueError(
            "governed export review_export profile_scope must match replay_run_manifest profile_scope"
        )
    if review_export_fields["runtime_mode"] != run_manifest.runtime_mode.value:
        raise ValueError(
            "governed export review_export runtime_mode must match replay_run_manifest runtime_mode"
        )
    if review_export_fields["performance_mode"] != run_manifest.performance_mode:
        raise ValueError(
            "governed export review_export performance_mode must match replay_run_manifest performance_mode"
        )
    if parity_diagnostics.dataset_id != run_manifest.dataset_manifest_id:
        raise ValueError(
            "governed export parity_diagnostics dataset_id must match replay_run_manifest dataset_manifest_id"
        )
    if feature_bridge_payload.get("dataset_id") != run_manifest.dataset_manifest_id:
        raise ValueError(
            "governed export feature_bridge dataset_id must match replay_run_manifest dataset_manifest_id"
        )
    if feature_bridge_payload.get("feature_set_version") != run_manifest.feature_set_version:
        raise ValueError(
            "governed export feature_bridge feature_set_version must match replay_run_manifest feature_set_version"
        )
    if feature_bridge_payload.get("transform_set_version") != run_manifest.transform_set_version:
        raise ValueError(
            "governed export feature_bridge transform_set_version must match replay_run_manifest transform_set_version"
        )
    if replay_metrics.total_records != len(replay_dtr_records):
        raise ValueError(
            "governed export replay_metrics total_records must match replay_dtr count"
        )
    expected_replay_metrics = build_replay_metrics_summary(
        replay_dtr_records,
        total_opportunities=replay_metrics.total_opportunities,
    )
    if replay_metrics != expected_replay_metrics:
        raise ValueError(
            "governed export replay_metrics must stay consistent with replay_dtr records"
        )
    if review_export_fields["total_opportunities"] != str(replay_metrics.total_opportunities):
        raise ValueError(
            "governed export review_export total_opportunities must match replay_metrics total_opportunities"
        )
    if review_export_fields["total_records"] != str(replay_metrics.total_records):
        raise ValueError(
            "governed export review_export total_records must match replay_metrics total_records"
        )
    if review_export_fields["dtr_coverage"] != f"{replay_metrics.dtr_coverage:.3f}":
        raise ValueError(
            "governed export review_export dtr_coverage must match replay_metrics dtr_coverage"
        )
    if review_export_fields["status"] != parity_diagnostics.parity_status:
        raise ValueError(
            "governed export review_export parity status must match parity_diagnostics parity_status"
        )
    if review_export_fields["decision_match_rate"] != str(parity_diagnostics.decision_match_rate):
        raise ValueError(
            "governed export review_export decision_match_rate must match parity_diagnostics decision_match_rate"
        )
    if sum(item.record_count for item in replay_metrics.pair_aggregates) != replay_metrics.total_records:
        raise ValueError(
            "governed export replay_metrics pair_aggregates must sum to total_records"
        )
    if sum(item.record_count for item in replay_metrics.engine_aggregates) != replay_metrics.total_records:
        raise ValueError(
            "governed export replay_metrics engine_aggregates must sum to total_records"
        )

    tested_pairs = set(run_manifest.tested_pairs)
    engine_scope = set(run_manifest.engine_scope)
    feature_bridge_pairs = {
        str(item) for item in feature_bridge_payload.get("pairs", ())
    }
    feature_bridge_engines = {
        str(item) for item in feature_bridge_payload.get("engines", ())
    }
    if feature_bridge_pairs != tested_pairs:
        raise ValueError(
            "governed export feature_bridge pairs must match replay_run_manifest tested_pairs"
        )
    if feature_bridge_engines != engine_scope:
        raise ValueError(
            "governed export feature_bridge engines must match replay_run_manifest engine_scope"
        )
    for item in replay_metrics.pair_aggregates:
        if item.pair not in tested_pairs:
            raise ValueError(
                "governed export replay_metrics pair_aggregates must stay within replay_run_manifest tested_pairs"
            )
    for item in replay_metrics.engine_aggregates:
        if item.engine_id not in engine_scope:
            raise ValueError(
                "governed export replay_metrics engine_aggregates must stay within replay_run_manifest engine_scope"
            )
    for record in replay_dtr_records:
        if record.pair not in tested_pairs:
            raise ValueError(
                "governed export replay_dtr pairs must stay within replay_run_manifest tested_pairs"
            )
        if record.engine_id not in engine_scope:
            raise ValueError(
                "governed export replay_dtr engine_ids must stay within replay_run_manifest engine_scope"
            )
        if record.runtime_mode and record.runtime_mode != RuntimeMode.LOCAL_REPLAY.value:
            raise ValueError(
                "governed export replay_dtr runtime_mode must stay local_replay"
            )
        timestamp_ms = int(record.timestamp * 1000.0)
        if (
            timestamp_ms < run_manifest.start_timestamp_ms
            or timestamp_ms > run_manifest.end_timestamp_ms
        ):
            raise ValueError(
                "governed export replay_dtr timestamps must stay within replay_run_manifest clock range"
            )


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
