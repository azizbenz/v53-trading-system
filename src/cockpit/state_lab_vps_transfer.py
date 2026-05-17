"""Phase 2.5 adapter - Local IA Lab output visibility vs VPS-visible imports."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, Field

from cockpit.state_freshness import (
    OperationalSourceSnapshot,
    latest_matching_file,
    read_json_dict,
    sha256_file,
    source_stamp,
    worst_status,
)

if TYPE_CHECKING:
    from cockpit.state import CockpitPaths


TransferStatus = Literal[
    "hash_match",
    "missing_on_vps",
    "missing_on_local",
    "mismatch",
    "unknown",
]


class TransferProofItem(BaseModel, frozen=True):
    name: str = Field(..., min_length=1)
    local_ref: str | None = None
    local_hash: str | None = None
    vps_ref: str | None = None
    vps_hash: str | None = None
    local_lineage_version: str = ""
    vps_lineage_version: str = ""
    status: TransferStatus = "unknown"


class LabVpsTransferSnapshot(OperationalSourceSnapshot):
    overall_status: TransferStatus = "unknown"
    hash_match_count: int = 0
    missing_on_vps_count: int = 0
    missing_on_local_count: int = 0
    mismatch_count: int = 0
    items: tuple[TransferProofItem, ...] = ()


def read_lab_vps_transfer(paths: CockpitPaths) -> LabVpsTransferSnapshot:
    """Compare local IA Lab outputs with what is visible on the VPS runtime side."""

    build_root = paths.build_root or paths.service_dir.parent.parent
    local_bundle = latest_matching_file(build_root, "meta_learning_review.bundle.json")
    local_governed = latest_matching_file(build_root, "governed_input_summary.json")
    latest_export = latest_matching_file(paths.auto_exports_root, "replay_run_manifest.json")
    latest_feature_export = latest_matching_file(paths.auto_exports_root, "feature_bridge.json")
    local_governed_payload = read_json_dict(local_governed) if local_governed else None
    vps_manifest = read_json_dict(latest_export) if latest_export else None
    local_feature_ref = (
        Path(str(local_governed_payload.get("feature_bridge_ref", ""))).resolve()
        if local_governed_payload and local_governed_payload.get("feature_bridge_ref")
        else None
    )
    items = (
        _item(
            name="review_bundle",
            local_ref=local_bundle,
            vps_ref=None,
        ),
        _item(
            name="calibration_artifact",
            local_ref=None,
            vps_ref=None,
        ),
        _item(
            name="feature_export",
            local_ref=local_feature_ref,
            vps_ref=latest_feature_export,
        ),
        _item(
            name="model_artifact",
            local_ref=local_governed,
            vps_ref=latest_export,
            local_declared_hash=str(local_governed_payload.get("artifact_hash", ""))
            if local_governed_payload
            else "",
            vps_declared_hash=str(vps_manifest.get("artifact_hash", ""))
            if vps_manifest
            else "",
            local_lineage_version=str(local_governed_payload.get("lineage_version", ""))
            if local_governed_payload
            else "",
            vps_lineage_version=str(vps_manifest.get("lineage_version", ""))
            if vps_manifest
            else "",
        ),
    )
    primary_path = local_governed or latest_export or local_bundle or latest_feature_export
    stamp = source_stamp(path=primary_path, stale_after_seconds=86400.0)
    hash_match_count = sum(1 for item in items if item.status == "hash_match")
    missing_on_vps_count = sum(1 for item in items if item.status == "missing_on_vps")
    missing_on_local_count = sum(1 for item in items if item.status == "missing_on_local")
    mismatch_count = sum(1 for item in items if item.status == "mismatch")
    if mismatch_count > 0:
        overall_status: TransferStatus = "mismatch"
    elif missing_on_vps_count > 0:
        overall_status = "missing_on_vps"
    elif missing_on_local_count > 0:
        overall_status = "missing_on_local"
    elif hash_match_count > 0:
        overall_status = "hash_match"
    else:
        overall_status = "unknown"
    return LabVpsTransferSnapshot(
        source_status=worst_status(*(_item_status_to_source(item.status) for item in items)),
        source_file=str(primary_path) if primary_path is not None else None,
        last_modified_at=stamp["last_modified_at"],
        age_seconds=stamp["age_seconds"],
        reason_codes=tuple(
            sorted({f"{item.name}:{item.status}" for item in items if item.status != "hash_match"})
        ),
        overall_status=overall_status,
        hash_match_count=hash_match_count,
        missing_on_vps_count=missing_on_vps_count,
        missing_on_local_count=missing_on_local_count,
        mismatch_count=mismatch_count,
        items=items,
    )


def _item(
    *,
    name: str,
    local_ref: Path | None,
    vps_ref: Path | None,
    local_declared_hash: str = "",
    vps_declared_hash: str = "",
    local_lineage_version: str = "",
    vps_lineage_version: str = "",
) -> TransferProofItem:
    local_hash = local_declared_hash or (sha256_file(local_ref) if local_ref else None)
    vps_hash = vps_declared_hash or (sha256_file(vps_ref) if vps_ref else None)
    if local_hash and vps_hash:
        status: TransferStatus = "hash_match" if local_hash == vps_hash else "mismatch"
    elif local_hash and not vps_hash:
        status = "missing_on_vps"
    elif vps_hash and not local_hash:
        status = "missing_on_local"
    else:
        status = "unknown"
    return TransferProofItem(
        name=name,
        local_ref=str(local_ref) if local_ref is not None else None,
        local_hash=local_hash,
        vps_ref=str(vps_ref) if vps_ref is not None else None,
        vps_hash=vps_hash,
        local_lineage_version=local_lineage_version,
        vps_lineage_version=vps_lineage_version,
        status=status,
    )


def _item_status_to_source(status: TransferStatus) -> str:
    if status == "mismatch":
        return "stale"
    if status in {"missing_on_local", "missing_on_vps"}:
        return "missing"
    if status == "unknown":
        return "unknown"
    return "ok"


__all__ = ["LabVpsTransferSnapshot", "TransferProofItem", "read_lab_vps_transfer"]
