"""File-based loader for Local IA Lab monitoring bundles."""

from __future__ import annotations

from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from monitoring.contracts import (
    LocalLabMonitoringBackendPayload,
    LocalLabMonitoringIngestionSummary,
    ObservabilityExport,
)

_ModelT = TypeVar("_ModelT", bound=BaseModel)


class LocalLabMonitoringBundle(BaseModel, frozen=True):
    """Validated Local IA Lab monitoring bundle loaded from one output directory."""

    bundle_dir: Path
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


def _require_aligned_bundle(
    *,
    backend_payload: LocalLabMonitoringBackendPayload,
    observability_export: ObservabilityExport,
    ingestion_summary: LocalLabMonitoringIngestionSummary,
) -> None:
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
    backend_payload = _load_model(
        resolved_dir / "local_lab_monitoring_backend_payload.json",
        label="backend_payload",
        model_type=LocalLabMonitoringBackendPayload,
    )
    observability_export = _load_model(
        resolved_dir / "local_lab_observability_export.json",
        label="observability_export",
        model_type=ObservabilityExport,
    )
    ingestion_summary = _load_model(
        resolved_dir / "local_lab_monitoring_ingestion_summary.json",
        label="ingestion_summary",
        model_type=LocalLabMonitoringIngestionSummary,
    )
    _require_aligned_bundle(
        backend_payload=backend_payload,
        observability_export=observability_export,
        ingestion_summary=ingestion_summary,
    )
    return LocalLabMonitoringBundle(
        bundle_dir=resolved_dir,
        backend_payload=backend_payload,
        observability_export=observability_export,
        ingestion_summary=ingestion_summary,
    )


__all__ = ["LocalLabMonitoringBundle", "load_local_lab_monitoring_bundle"]
