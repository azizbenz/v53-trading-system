"""Phase 2 adapter — read ``auto_exports/<date>/feature_bridge.json``."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from collections.abc import Mapping
from typing import Literal

from pydantic import BaseModel

from cockpit.state_replay_metrics import _latest_export_dir
from data_backbone.microstructure import get_feature_registry


_logger = logging.getLogger(__name__)
SourceStatus = Literal["ok", "missing", "parse_error"]
_RUNTIME_ACTIVE_STATUSES = frozenset(
    {
        "RUNTIME_CONSUMED",
        "ENGINE_CONSUMED",
        "SCORING_CONSUMED",
        "RISK_GATE_CONSUMED",
        "COST_GATE_CONSUMED",
        "EXECUTION_GATE_CONSUMED",
    }
)
_LIFECYCLE_ACTIVE_STATUSES = frozenset(
    {
        "ACTIVE_RUNTIME",
        "ACTIVE_ENGINE_INPUT",
        "ACTIVE_EXECUTION_GATE",
        "FALLBACK_ONLY",
    }
)


class FeatureBridgeFamilyStatus(BaseModel, frozen=True):
    family: str
    artifact_status: str = "ARTIFACT_PRESENT_ONLY"
    runtime_status: str = "NOT_PROVEN"
    runtime_lifecycle_status: str = "NOT_PROVEN"
    registry_intent_status: str | None = None
    registry_consumer_statuses: tuple[str, ...] = ()
    display_status: str = "gray"


class FeatureBridgeSnapshot(BaseModel, frozen=True):
    source_status: SourceStatus = "missing"
    source_path: str = ""
    bridge_status: str = ""
    feature_set_version: str = ""
    transform_set_version: str = ""
    canonical_feature_dictionary_size: int = 0
    canonical_transform_whitelist_size: int = 0
    record_count: int = 0
    rows_with_features: int = 0
    missing_feature_rows: int = 0
    pairs: tuple[str, ...] = ()
    engines: tuple[str, ...] = ()
    feature_keys: tuple[str, ...] = ()
    feature_families: tuple[str, ...] = ()
    recognized_feature_keys: tuple[str, ...] = ()
    recognized_feature_families: tuple[str, ...] = ()
    unrecognized_feature_keys: tuple[str, ...] = ()
    unrecognized_feature_families: tuple[str, ...] = ()
    artifact_presence_status: str = "NOT_PROVEN"
    runtime_consumption_status: str = "NOT_PROVEN"
    runtime_active: bool = False
    feature_family_statuses: tuple[FeatureBridgeFamilyStatus, ...] = ()
    lineage_lock_status: str = ""
    lineage_lock_reasons: tuple[str, ...] = ()
    feature_to_engine_path: str = ""

    @property
    def recognition_rate(self) -> float:
        if not self.feature_keys:
            return 0.0
        return len(self.recognized_feature_keys) / len(self.feature_keys)

    @property
    def runtime_consumption_proven(self) -> bool:
        return self.runtime_consumption_status in _RUNTIME_ACTIVE_STATUSES


def read_feature_bridge(auto_exports_root: Path) -> FeatureBridgeSnapshot:
    latest = _latest_export_dir(auto_exports_root)
    if latest is None:
        return FeatureBridgeSnapshot(source_status="missing")
    path = latest / "feature_bridge.json"
    if not path.is_file():
        return FeatureBridgeSnapshot(source_status="missing", source_path=str(path))
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _logger.warning("Cannot parse feature bridge %s: %s", path, exc)
        return FeatureBridgeSnapshot(source_status="parse_error", source_path=str(path))
    if not isinstance(payload, dict):
        return FeatureBridgeSnapshot(source_status="parse_error", source_path=str(path))
    feature_keys = tuple(str(k) for k in payload.get("feature_keys") or ())
    recognized_feature_keys = tuple(
        str(k) for k in payload.get("recognized_feature_keys") or ()
    )
    unrecognized_feature_keys = tuple(
        str(k) for k in payload.get("unrecognized_feature_keys") or ()
    )
    return FeatureBridgeSnapshot(
        source_status="ok",
        source_path=str(path),
        bridge_status=str(payload.get("bridge_status", "")),
        feature_set_version=str(payload.get("feature_set_version", "")),
        transform_set_version=str(payload.get("transform_set_version", "")),
        canonical_feature_dictionary_size=int(payload.get("canonical_feature_dictionary_size", 0)),
        canonical_transform_whitelist_size=int(payload.get("canonical_transform_whitelist_size", 0)),
        record_count=int(payload.get("record_count", 0)),
        rows_with_features=int(payload.get("rows_with_features", 0)),
        missing_feature_rows=int(payload.get("missing_feature_rows", 0)),
        pairs=tuple(str(p) for p in payload.get("pairs") or ()),
        engines=tuple(str(e) for e in payload.get("engines") or ()),
        feature_keys=feature_keys,
        feature_families=_feature_families(feature_keys),
        recognized_feature_keys=recognized_feature_keys,
        recognized_feature_families=_feature_families(recognized_feature_keys),
        unrecognized_feature_keys=unrecognized_feature_keys,
        unrecognized_feature_families=_feature_families(unrecognized_feature_keys),
        artifact_presence_status=str(payload.get("artifact_presence_status", "ARTIFACT_PRESENT_ONLY")),
        runtime_consumption_status=str(payload.get("runtime_consumption_status", "NOT_PROVEN")),
        runtime_active=str(payload.get("runtime_consumption_status", "NOT_PROVEN")) in _RUNTIME_ACTIVE_STATUSES,
        feature_family_statuses=_build_family_runtime_statuses(
            _feature_families(feature_keys),
        ),
        lineage_lock_status=str(payload.get("lineage_lock_status", "")),
        lineage_lock_reasons=tuple(str(r) for r in payload.get("lineage_lock_reasons") or ()),
        feature_to_engine_path=str(payload.get("feature_to_engine_path", "")),
    )


def _feature_families(feature_keys: tuple[str, ...]) -> tuple[str, ...]:
    families: list[str] = []
    seen: set[str] = set()
    for key in feature_keys:
        family = _feature_family(key)
        if family and family not in seen:
            seen.add(family)
            families.append(family)
    return tuple(families)


def _feature_family(feature_key: str) -> str:
    text = feature_key.strip()
    if not text:
        return ""
    for separator in ("__", ".", ":"):
        if separator in text:
            return text.split(separator, 1)[0]
    if "_" in text:
        return text.split("_", 1)[0]
    return text


def _build_family_runtime_statuses(
    feature_families: tuple[str, ...],
) -> tuple[FeatureBridgeFamilyStatus, ...]:
    registry = get_feature_registry()
    registry_metadata_by_family = _registry_metadata_by_family(registry)
    statuses: list[FeatureBridgeFamilyStatus] = []
    for family in feature_families:
        runtime_lifecycle_status, registry_intent_status, registry_statuses = registry_metadata_by_family.get(
            family,
            ("NOT_PROVEN", None, ()),
        )
        statuses.append(
            FeatureBridgeFamilyStatus(
                family=family,
                artifact_status="ARTIFACT_PRESENT_ONLY",
                runtime_status="NOT_PROVEN",
                runtime_lifecycle_status=runtime_lifecycle_status,
                registry_intent_status=registry_intent_status,
                registry_consumer_statuses=registry_statuses,
                display_status=_resolve_display_status(
                    runtime_status="NOT_PROVEN",
                    runtime_lifecycle_status=runtime_lifecycle_status,
                    registry_consumer_statuses=registry_statuses,
                ),
            )
        )
    return tuple(statuses)


def _registry_metadata_by_family(
    registry: Mapping[str, object],
) -> dict[str, tuple[str, str | None, tuple[str, ...]]]:
    metadata_by_family: dict[str, tuple[str, str | None, tuple[str, ...]]] = {}
    for spec in registry.values():
        family = _feature_family(spec.feature_id)
        family_statuses: list[str] = []
        for status in spec.consumer_statuses:
            if status not in family_statuses:
                family_statuses.append(status)
        metadata_by_family[family] = (
            spec.runtime_lifecycle_status,
            spec.registry_intent_status,
            tuple(family_statuses),
        )
    return metadata_by_family


def _resolve_display_status(
    *,
    runtime_status: str,
    runtime_lifecycle_status: str,
    registry_consumer_statuses: tuple[str, ...],
) -> str:
    if runtime_status in _RUNTIME_ACTIVE_STATUSES:
        return "green"
    if runtime_lifecycle_status in _LIFECYCLE_ACTIVE_STATUSES:
        return "yellow"
    if registry_consumer_statuses:
        return "gray"
    return "gray"


__all__ = ["FeatureBridgeFamilyStatus", "FeatureBridgeSnapshot", "read_feature_bridge"]
