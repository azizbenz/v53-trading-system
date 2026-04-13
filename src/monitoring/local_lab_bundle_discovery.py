"""Discovery helpers for Local IA Lab monitoring bundles."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from monitoring.local_lab_bundle_loader import (
    LocalLabMonitoringBundle,
    load_local_lab_monitoring_bundle,
)
from monitoring.local_lab_monitoring_bundle_manifest import LocalLabMonitoringBundleManifest


class LocalLabMonitoringBundleDiscoveryItem(BaseModel, frozen=True):
    """One discovered Local IA Lab monitoring bundle manifest."""

    bundle_dir: str = Field(..., min_length=1)
    manifest_path: str = Field(..., min_length=1)
    correlation_id: str = Field(..., min_length=1)
    profile: str = Field(..., min_length=1)
    runtime_mode: str = Field(..., min_length=1)
    timestamp_ms: int = Field(..., ge=0)
    backend_status: str = Field(..., min_length=1)
    ingestion_ready: bool = False
    observability_sample_count: int = Field(default=0, ge=0)
    calibration_methods_review_status: str = Field(default="not_evaluated", min_length=1)
    calibration_methods_review_ready: bool = False
    calibration_methods_dsr_pass: bool | None = None
    calibration_methods_walk_forward_plan_ready: bool = False
    execution_review_status: str = Field(default="not_evaluated", min_length=1)
    execution_review_ready: bool = False
    execution_ready_threshold_count: int = Field(default=0, ge=0)
    execution_partial_threshold_count: int = Field(default=0, ge=0)
    execution_blocked_threshold_count: int = Field(default=0, ge=0)
    multiple_testing_review_status: str = Field(default="not_evaluated", min_length=1)
    multiple_testing_review_ready: bool = False
    multiple_testing_correction_required: bool = False
    multiple_testing_family_count: int = Field(default=0, ge=0)


class LocalLabMonitoringBundleDiscovery(BaseModel, frozen=True):
    """Stable discovery result over multiple Local IA Lab monitoring bundles."""

    root_dir: str = Field(..., min_length=1)
    bundle_count: int = Field(default=0, ge=0)
    latest_bundle_dir: str = ""
    latest_correlation_id: str = ""
    latest_backend_status: str = ""
    latest_ingestion_ready: bool = False
    bundles: tuple[LocalLabMonitoringBundleDiscoveryItem, ...] = ()


def _load_manifest(path: Path) -> LocalLabMonitoringBundleManifest:
    return LocalLabMonitoringBundleManifest.model_validate_json(path.read_text(encoding="utf-8"))


def discover_local_lab_monitoring_bundles(root_dir: Path) -> LocalLabMonitoringBundleDiscovery:
    """Discover Local IA Lab monitoring bundles by their manifest sidecar."""

    resolved_root = root_dir.resolve()
    manifests: list[tuple[Path, LocalLabMonitoringBundleManifest]] = []
    for manifest_path in resolved_root.rglob("local_lab_monitoring_bundle_manifest.json"):
        manifest = _load_manifest(manifest_path)
        manifests.append((manifest_path, manifest))

    manifests.sort(key=lambda item: (item[1].timestamp_ms, item[0].as_posix()), reverse=True)
    items = tuple(
        LocalLabMonitoringBundleDiscoveryItem(
            bundle_dir=str(manifest_path.parent),
            manifest_path=str(manifest_path),
            correlation_id=manifest.correlation_id,
            profile=manifest.profile,
            runtime_mode=manifest.runtime_mode,
            timestamp_ms=manifest.timestamp_ms,
            backend_status=manifest.backend_status,
            ingestion_ready=manifest.ingestion_ready,
            observability_sample_count=manifest.observability_sample_count,
            calibration_methods_review_status=manifest.calibration_methods_review_status,
            calibration_methods_review_ready=manifest.calibration_methods_review_ready,
            calibration_methods_dsr_pass=manifest.calibration_methods_dsr_pass,
            calibration_methods_walk_forward_plan_ready=(
                manifest.calibration_methods_walk_forward_plan_ready
            ),
            execution_review_status=manifest.execution_review_status,
            execution_review_ready=manifest.execution_review_ready,
            execution_ready_threshold_count=manifest.execution_ready_threshold_count,
            execution_partial_threshold_count=manifest.execution_partial_threshold_count,
            execution_blocked_threshold_count=manifest.execution_blocked_threshold_count,
            multiple_testing_review_status=manifest.multiple_testing_review_status,
            multiple_testing_review_ready=manifest.multiple_testing_review_ready,
            multiple_testing_correction_required=manifest.multiple_testing_correction_required,
            multiple_testing_family_count=manifest.multiple_testing_family_count,
        )
        for manifest_path, manifest in manifests
    )

    latest = items[0] if items else None
    return LocalLabMonitoringBundleDiscovery(
        root_dir=str(resolved_root),
        bundle_count=len(items),
        latest_bundle_dir=latest.bundle_dir if latest else "",
        latest_correlation_id=latest.correlation_id if latest else "",
        latest_backend_status=latest.backend_status if latest else "",
        latest_ingestion_ready=latest.ingestion_ready if latest else False,
        bundles=items,
    )


def load_latest_local_lab_monitoring_bundle(root_dir: Path) -> LocalLabMonitoringBundle:
    """Load the newest Local IA Lab monitoring bundle discovered under one root."""

    discovery = discover_local_lab_monitoring_bundles(root_dir)
    if not discovery.bundles:
        raise FileNotFoundError(
            f"No Local IA Lab monitoring bundle manifest found under: {root_dir.resolve()}"
        )
    return load_local_lab_monitoring_bundle(Path(discovery.latest_bundle_dir))


__all__ = [
    "LocalLabMonitoringBundleDiscoveryItem",
    "LocalLabMonitoringBundleDiscovery",
    "discover_local_lab_monitoring_bundles",
    "load_latest_local_lab_monitoring_bundle",
]
