"""Compact monitoring feed over discovered Local IA Lab bundles."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from monitoring.local_lab_bundle_discovery import (
    LocalLabMonitoringBundleDiscovery,
    discover_local_lab_monitoring_bundles,
)


class LocalLabMonitoringFeedItem(BaseModel, frozen=True):
    """One compact Local IA Lab monitoring feed item."""

    bundle_dir: str = Field(..., min_length=1)
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


class LocalLabMonitoringFeed(BaseModel, frozen=True):
    """Compact feed summarizing discovered Local IA Lab monitoring bundles."""

    root_dir: str = Field(..., min_length=1)
    bundle_count: int = Field(default=0, ge=0)
    latest_correlation_id: str = ""
    latest_backend_status: str = ""
    latest_ingestion_ready: bool = False
    ready_bundle_count: int = Field(default=0, ge=0)
    warning_bundle_count: int = Field(default=0, ge=0)
    critical_bundle_count: int = Field(default=0, ge=0)
    info_bundle_count: int = Field(default=0, ge=0)
    calibration_ready_bundle_count: int = Field(default=0, ge=0)
    calibration_partial_bundle_count: int = Field(default=0, ge=0)
    calibration_blocked_bundle_count: int = Field(default=0, ge=0)
    execution_ready_bundle_count: int = Field(default=0, ge=0)
    execution_partial_bundle_count: int = Field(default=0, ge=0)
    execution_blocked_bundle_count: int = Field(default=0, ge=0)
    multiple_testing_ready_bundle_count: int = Field(default=0, ge=0)
    multiple_testing_partial_bundle_count: int = Field(default=0, ge=0)
    multiple_testing_blocked_bundle_count: int = Field(default=0, ge=0)
    items: tuple[LocalLabMonitoringFeedItem, ...] = ()


def build_local_lab_monitoring_feed(
    discovery: LocalLabMonitoringBundleDiscovery,
) -> LocalLabMonitoringFeed:
    """Project bundle discovery into a compact monitoring feed."""

    items = tuple(
        LocalLabMonitoringFeedItem(
            bundle_dir=item.bundle_dir,
            correlation_id=item.correlation_id,
            profile=item.profile,
            runtime_mode=item.runtime_mode,
            timestamp_ms=item.timestamp_ms,
            backend_status=item.backend_status,
            ingestion_ready=item.ingestion_ready,
            observability_sample_count=item.observability_sample_count,
            calibration_methods_review_status=item.calibration_methods_review_status,
            calibration_methods_review_ready=item.calibration_methods_review_ready,
            calibration_methods_dsr_pass=item.calibration_methods_dsr_pass,
            calibration_methods_walk_forward_plan_ready=(
                item.calibration_methods_walk_forward_plan_ready
            ),
            execution_review_status=item.execution_review_status,
            execution_review_ready=item.execution_review_ready,
            execution_ready_threshold_count=item.execution_ready_threshold_count,
            execution_partial_threshold_count=item.execution_partial_threshold_count,
            execution_blocked_threshold_count=item.execution_blocked_threshold_count,
            multiple_testing_review_status=item.multiple_testing_review_status,
            multiple_testing_review_ready=item.multiple_testing_review_ready,
            multiple_testing_correction_required=item.multiple_testing_correction_required,
            multiple_testing_family_count=item.multiple_testing_family_count,
        )
        for item in discovery.bundles
    )
    return LocalLabMonitoringFeed(
        root_dir=discovery.root_dir,
        bundle_count=discovery.bundle_count,
        latest_correlation_id=discovery.latest_correlation_id,
        latest_backend_status=discovery.latest_backend_status,
        latest_ingestion_ready=discovery.latest_ingestion_ready,
        ready_bundle_count=sum(1 for item in items if item.ingestion_ready),
        warning_bundle_count=sum(1 for item in items if item.backend_status == "warning"),
        critical_bundle_count=sum(1 for item in items if item.backend_status == "critical"),
        info_bundle_count=sum(1 for item in items if item.backend_status == "info"),
        calibration_ready_bundle_count=sum(
            1 for item in items if item.calibration_methods_review_status == "ready"
        ),
        calibration_partial_bundle_count=sum(
            1 for item in items if item.calibration_methods_review_status == "partial"
        ),
        calibration_blocked_bundle_count=sum(
            1 for item in items if item.calibration_methods_review_status == "blocked"
        ),
        execution_ready_bundle_count=sum(
            1 for item in items if item.execution_review_status == "ready"
        ),
        execution_partial_bundle_count=sum(
            1 for item in items if item.execution_review_status == "partial"
        ),
        execution_blocked_bundle_count=sum(
            1 for item in items if item.execution_review_status == "blocked"
        ),
        multiple_testing_ready_bundle_count=sum(
            1 for item in items if item.multiple_testing_review_status == "ready"
        ),
        multiple_testing_partial_bundle_count=sum(
            1 for item in items if item.multiple_testing_review_status == "partial"
        ),
        multiple_testing_blocked_bundle_count=sum(
            1 for item in items if item.multiple_testing_review_status == "blocked"
        ),
        items=items,
    )


def build_local_lab_monitoring_feed_from_root(root_dir: str) -> LocalLabMonitoringFeed:
    """Discover Local IA Lab monitoring bundles under one root and build the compact feed."""

    discovery = discover_local_lab_monitoring_bundles(Path(root_dir))
    return build_local_lab_monitoring_feed(discovery)


__all__ = [
    "LocalLabMonitoringFeedItem",
    "LocalLabMonitoringFeed",
    "build_local_lab_monitoring_feed",
    "build_local_lab_monitoring_feed_from_root",
]
