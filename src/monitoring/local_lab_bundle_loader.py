"""File-based loader for Local IA Lab monitoring bundles."""

from __future__ import annotations

from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from monitoring.local_lab_monitoring_bundle_manifest import LocalLabMonitoringBundleManifest
from monitoring.contracts import (
    LocalLabMonitoringBackendPayload,
    LocalLabMonitoringIngestionSummary,
    ObservabilityExport,
)

_ModelT = TypeVar("_ModelT", bound=BaseModel)


class LocalLabMonitoringBundle(BaseModel, frozen=True):
    """Validated Local IA Lab monitoring bundle loaded from one output directory."""

    bundle_dir: Path
    manifest: LocalLabMonitoringBundleManifest
    backend_payload: LocalLabMonitoringBackendPayload
    observability_export: ObservabilityExport
    ingestion_summary: LocalLabMonitoringIngestionSummary


def _load_model(path: Path, *, label: str, model_type: type[_ModelT]) -> _ModelT:
    if not path.is_file():
        raise FileNotFoundError(f"Missing Local IA Lab monitoring file for {label}: {path}")
    try:
        return model_type.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValidationError, ValueError) as exc:
        raise ValueError(
            f"Invalid Local IA Lab monitoring file for {label}: {path.name}"
        ) from exc


def _resolve_bundle_ref(bundle_dir: Path, ref: str) -> Path:
    path = Path(ref)
    if path.is_absolute():
        return path.resolve()
    if path.exists():
        return path.resolve()
    return (bundle_dir / path).resolve()


def _require_aligned_bundle(
    *,
    manifest: LocalLabMonitoringBundleManifest,
    backend_payload: LocalLabMonitoringBackendPayload,
    observability_export: ObservabilityExport,
    ingestion_summary: LocalLabMonitoringIngestionSummary,
) -> None:
    if manifest.correlation_id != backend_payload.correlation_id:
        raise ValueError(
            "Local IA Lab monitoring bundle requires matching correlation_id across manifest and backend payload"
        )
    if manifest.profile != backend_payload.profile.value:
        raise ValueError(
            "Local IA Lab monitoring bundle requires matching profile across manifest and backend payload"
        )
    if manifest.runtime_mode != backend_payload.runtime_mode.value:
        raise ValueError(
            "Local IA Lab monitoring bundle requires matching runtime_mode across manifest and backend payload"
        )
    if manifest.timestamp_ms != backend_payload.timestamp_ms:
        raise ValueError(
            "Local IA Lab monitoring bundle requires matching timestamp_ms across manifest and backend payload"
        )
    if observability_export.correlation_id != backend_payload.correlation_id:
        raise ValueError(
            "Local IA Lab monitoring bundle requires matching correlation_id across backend payload and observability export"
        )
    if ingestion_summary.correlation_id != backend_payload.correlation_id:
        raise ValueError(
            "Local IA Lab monitoring bundle requires matching correlation_id across backend payload and ingestion summary"
        )
    if observability_export.profile != backend_payload.profile:
        raise ValueError(
            "Local IA Lab monitoring bundle requires matching profile across backend payload and observability export"
        )
    if ingestion_summary.profile != backend_payload.profile:
        raise ValueError(
            "Local IA Lab monitoring bundle requires matching profile across backend payload and ingestion summary"
        )
    if observability_export.runtime_mode != backend_payload.runtime_mode:
        raise ValueError(
            "Local IA Lab monitoring bundle requires matching runtime_mode across backend payload and observability export"
        )
    if ingestion_summary.runtime_mode != backend_payload.runtime_mode:
        raise ValueError(
            "Local IA Lab monitoring bundle requires matching runtime_mode across backend payload and ingestion summary"
        )
    if observability_export.timestamp_ms != backend_payload.timestamp_ms:
        raise ValueError(
            "Local IA Lab monitoring bundle requires matching timestamp_ms across backend payload and observability export"
        )
    if ingestion_summary.timestamp_ms != backend_payload.timestamp_ms:
        raise ValueError(
            "Local IA Lab monitoring bundle requires matching timestamp_ms across backend payload and ingestion summary"
        )


def load_local_lab_monitoring_bundle(bundle_dir: Path) -> LocalLabMonitoringBundle:
    """Load and validate the Local IA Lab monitoring trio from one bundle directory."""

    resolved_dir = bundle_dir.resolve()
    manifest = _load_model(
        resolved_dir / "local_lab_monitoring_bundle_manifest.json",
        label="manifest",
        model_type=LocalLabMonitoringBundleManifest,
    )
    backend_payload = _load_model(
        _resolve_bundle_ref(resolved_dir, manifest.backend_payload_path),
        label="backend_payload",
        model_type=LocalLabMonitoringBackendPayload,
    )
    observability_export = _load_model(
        _resolve_bundle_ref(resolved_dir, manifest.observability_export_path),
        label="observability_export",
        model_type=ObservabilityExport,
    )
    ingestion_summary = _load_model(
        _resolve_bundle_ref(resolved_dir, manifest.ingestion_summary_path),
        label="ingestion_summary",
        model_type=LocalLabMonitoringIngestionSummary,
    )
    _require_aligned_bundle(
        manifest=manifest,
        backend_payload=backend_payload,
        observability_export=observability_export,
        ingestion_summary=ingestion_summary,
    )
    return LocalLabMonitoringBundle(
        bundle_dir=resolved_dir,
        manifest=manifest,
        backend_payload=backend_payload,
        observability_export=observability_export,
        ingestion_summary=ingestion_summary,
    )


__all__ = ["LocalLabMonitoringBundle", "load_local_lab_monitoring_bundle"]
