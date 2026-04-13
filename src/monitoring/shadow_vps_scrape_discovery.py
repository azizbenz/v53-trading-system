"""Discovery helpers for local-PC Prometheus scrape handoff from Shadow VPS manifests."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from monitoring.contracts import PrometheusFileSdEntry, ShadowVpsServiceScrapeManifest
from monitoring.shadow_vps_service_scrape_manifest import (
    build_shadow_vps_service_prometheus_file_sd,
)


class ShadowVpsScrapeDiscoveryItem(BaseModel, frozen=True):
    """One discovered Shadow VPS scrape manifest."""

    bundle_dir: str = Field(..., min_length=1)
    manifest_path: str = Field(..., min_length=1)
    correlation_id: str = Field(..., min_length=1)
    profile: str = Field(..., min_length=1)
    runtime_mode: str = Field(..., min_length=1)
    timestamp_ms: int = Field(..., ge=0)
    status: str = Field(..., min_length=1)
    vps_id: str = Field(..., min_length=1)
    node_exporter_target: str = Field(..., min_length=1)
    prometheus_job_name: str = Field(..., min_length=1)
    node_exporter_textfile_ready: bool = False


class ShadowVpsScrapeDiscovery(BaseModel, frozen=True):
    """Stable discovery result over multiple Shadow VPS scrape manifests."""

    root_dir: str = Field(..., min_length=1)
    manifest_count: int = Field(default=0, ge=0)
    target_count: int = Field(default=0, ge=0)
    latest_vps_id: str = ""
    latest_target: str = ""
    manifests: tuple[ShadowVpsScrapeDiscoveryItem, ...] = ()


def _load_manifest(path: Path) -> ShadowVpsServiceScrapeManifest:
    return ShadowVpsServiceScrapeManifest.model_validate_json(
        path.read_text(encoding="utf-8")
    )


def discover_shadow_vps_service_scrape_manifests(
    root_dir: Path,
) -> ShadowVpsScrapeDiscovery:
    """Discover Shadow VPS scrape manifests under one local root."""

    resolved_root = root_dir.resolve()
    manifests: list[tuple[Path, ShadowVpsServiceScrapeManifest]] = []
    for manifest_path in resolved_root.rglob("shadow_vps_service_scrape_manifest.json"):
        manifest = _load_manifest(manifest_path)
        manifests.append((manifest_path, manifest))

    manifests.sort(
        key=lambda item: (item[1].timestamp_ms, item[0].as_posix()),
        reverse=True,
    )
    items = tuple(
        ShadowVpsScrapeDiscoveryItem(
            bundle_dir=str(manifest_path.parent),
            manifest_path=str(manifest_path),
            correlation_id=manifest.correlation_id,
            profile=manifest.profile.value,
            runtime_mode=manifest.runtime_mode.value,
            timestamp_ms=manifest.timestamp_ms,
            status=manifest.status,
            vps_id=manifest.vps_id,
            node_exporter_target=manifest.node_exporter_target,
            prometheus_job_name=manifest.prometheus_job_name,
            node_exporter_textfile_ready=manifest.node_exporter_textfile_ready,
        )
        for manifest_path, manifest in manifests
    )
    latest = items[0] if items else None
    latest_per_target = {item.node_exporter_target: item for item in items}
    return ShadowVpsScrapeDiscovery(
        root_dir=str(resolved_root),
        manifest_count=len(items),
        target_count=len(latest_per_target),
        latest_vps_id=latest.vps_id if latest else "",
        latest_target=latest.node_exporter_target if latest else "",
        manifests=items,
    )


def build_shadow_vps_prometheus_file_sd_from_root(
    root_dir: Path,
) -> tuple[PrometheusFileSdEntry, ...]:
    """Build one de-duplicated Prometheus file_sd bundle from discovered VPS manifests."""

    discovery = discover_shadow_vps_service_scrape_manifests(root_dir)
    latest_by_target: dict[str, ShadowVpsServiceScrapeManifest] = {}
    for item in discovery.manifests:
        manifest = _load_manifest(Path(item.manifest_path))
        latest_by_target.setdefault(manifest.node_exporter_target, manifest)

    entries: list[PrometheusFileSdEntry] = []
    for target in sorted(latest_by_target):
        manifest = latest_by_target[target]
        entries.extend(build_shadow_vps_service_prometheus_file_sd(manifest))
    return tuple(entries)


__all__ = [
    "ShadowVpsScrapeDiscovery",
    "ShadowVpsScrapeDiscoveryItem",
    "build_shadow_vps_prometheus_file_sd_from_root",
    "discover_shadow_vps_service_scrape_manifests",
]
