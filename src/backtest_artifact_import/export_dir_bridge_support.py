"""Support helpers for governed LOCAL_REPLAY export discovery and validation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, TypeVar

from pydantic import BaseModel, ValidationError

from backtest_artifact_import.contracts import ArtifactPayloadRefBundle
from interface_contracts import CANONICAL_PHYSICS_FEATURE_DICTIONARY, FeatureDictionaryEntry
from local_replay_runtime import ReplayMetricsSummary, ReplayParityDiagnosticsSummary
from local_replay_runtime.replay_run_manifest import ReplayRunManifest
from local_replay_runtime.replay_metrics_collector import (
    ReplayBookDepthAvailability,
    ReplayCostParityEvidence,
    ReplayFeeProvenance,
    ReplayFillRealismEvidence,
    ReplayImpactProvenance,
    build_replay_metrics_summary,
)
from meta_minimal.dtr_core.dtr_record_builder import DTRRecord

_LoadedBridgeModelT = TypeVar("_LoadedBridgeModelT")


class _ValidatedReplaySidecars(BaseModel, frozen=True):
    """Typed governed sidecars loaded from an export directory."""

    review_export_text: str
    feature_bridge_payload: dict
    parity_diagnostics: ReplayParityDiagnosticsSummary
    replay_metrics: ReplayMetricsSummary
    replay_dtr_records: tuple[DTRRecord, ...]


def _resolve_canonical_feature_entry(
    feature_id: str,
) -> FeatureDictionaryEntry | None:
    entry = CANONICAL_PHYSICS_FEATURE_DICTIONARY.get(feature_id)
    if entry is not None:
        return entry

    if "_" in feature_id:
        prefix, suffix = feature_id.rsplit("_", 1)
        if suffix.endswith("m") and suffix[:-1].isdigit():
            return CANONICAL_PHYSICS_FEATURE_DICTIONARY.get(prefix)

    return None


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


def _validate_review_export_fields(
    run_manifest: ReplayRunManifest,
    review_export_fields: dict[str, str],
) -> None:
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


def _validate_feature_bridge_consistency(
    run_manifest: ReplayRunManifest,
    feature_bridge_payload: dict,
) -> None:
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


def _validate_metrics_consistency(
    run_manifest: ReplayRunManifest,
    review_export_fields: dict[str, str],
    replay_metrics: ReplayMetricsSummary,
    replay_dtr_records: tuple[DTRRecord, ...],
    parity_diagnostics: ReplayParityDiagnosticsSummary,
) -> None:
    if parity_diagnostics.dataset_id != run_manifest.dataset_manifest_id:
        raise ValueError(
            "governed export parity_diagnostics dataset_id must match replay_run_manifest dataset_manifest_id"
        )
    if replay_metrics.total_records != len(replay_dtr_records):
        raise ValueError(
            "governed export replay_metrics total_records must match replay_dtr count"
        )
    sidecar_payload = replay_metrics.model_dump(mode="python")
    expected_replay_metrics = build_replay_metrics_summary(
        replay_dtr_records,
        total_opportunities=replay_metrics.total_opportunities,
        capital_bucket_profiles=replay_metrics.capital_bucket_profiles,
        fee_provenance=ReplayFeeProvenance.model_validate(
            {
                key: sidecar_payload.get(key)
                for key in ReplayFeeProvenance.model_fields
            }
        ),
        impact_provenance=ReplayImpactProvenance.model_validate(
            {
                key: sidecar_payload.get(key)
                for key in ReplayImpactProvenance.model_fields
            }
        ),
        book_depth_availability=ReplayBookDepthAvailability.model_validate(
            {
                key: sidecar_payload.get(key)
                for key in ReplayBookDepthAvailability.model_fields
            }
        ),
        fill_realism=ReplayFillRealismEvidence.model_validate(
            {
                key: sidecar_payload.get(key)
                for key in ReplayFillRealismEvidence.model_fields
            }
        ),
        cost_parity=ReplayCostParityEvidence.model_validate(
            {
                key: sidecar_payload.get(key)
                for key in ReplayCostParityEvidence.model_fields
            }
        ),
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


def _validate_scope_consistency(
    run_manifest: ReplayRunManifest,
    replay_metrics: ReplayMetricsSummary,
    replay_dtr_records: tuple[DTRRecord, ...],
    feature_bridge_payload: dict,
) -> None:
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
                "governed export replay_dtr engines must stay within replay_run_manifest engine_scope"
            )


def _validate_manifest_sidecar_consistency(
    run_manifest: ReplayRunManifest,
    sidecars: _ValidatedReplaySidecars,
) -> None:
    review_export_fields = _parse_review_export_fields(sidecars.review_export_text)
    _validate_review_export_fields(run_manifest, review_export_fields)
    _validate_feature_bridge_consistency(run_manifest, sidecars.feature_bridge_payload)
    _validate_metrics_consistency(
        run_manifest,
        review_export_fields,
        sidecars.replay_metrics,
        sidecars.replay_dtr_records,
        sidecars.parity_diagnostics,
    )
    _validate_scope_consistency(
        run_manifest,
        sidecars.replay_metrics,
        sidecars.replay_dtr_records,
        sidecars.feature_bridge_payload,
    )
