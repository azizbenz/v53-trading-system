"""Patch 6 batch 2 — Feature + threshold registry manifest.

Read-only typed manifest that surfaces which feature groups are available,
which thresholds are in use, and the *source* of each threshold so the
cockpit can clearly distinguish:

  - ``THRESHOLD_CALIBRATED`` — a calibration artefact pinned this value
  - ``THRESHOLD_DEFAULT``    — value comes from a code constant
  - ``THRESHOLD_RESEARCH_ONLY`` — value is research-grade, not promoted
  - ``THRESHOLD_NOT_PROVEN`` — value placeholder, no source
  - ``THRESHOLD_MISSING``    — feature group expects a threshold but none exists

This v1 builder does NOT introspect engines/scoring code. It reports:
  * gold feature groups listed in ``gold_feature_manifest.json``
  * a small built-in registry of known threshold names and their canonical
    source modules (no values — the values live in code as constants and
    must NOT be re-asserted here)

Crucial doctrine: this module never claims a threshold is calibrated unless
a calibration artefact path is supplied by the caller. By default everything
is reported as ``THRESHOLD_DEFAULT`` or ``THRESHOLD_NOT_PROVEN``.
"""

from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path

from pydantic import BaseModel, Field

from interface_contracts.atomic_io import atomic_write_json, atomic_write_text
from local_replay_runtime.strategy_ladder_data_factory_models import (
    finalize_hashed_model,
)


_ALLOWED_THRESHOLD_STATUSES: frozenset[str] = frozenset(
    {
        "THRESHOLD_CALIBRATED",
        "THRESHOLD_DEFAULT",
        "THRESHOLD_RESEARCH_ONLY",
        "THRESHOLD_NOT_PROVEN",
        "THRESHOLD_MISSING",
    }
)


# Canonical mapping: feature group → engines that consume it.
# Source: cockpit/runtime_support.StrategyLadderBacktestSummary feature groups
# enumerated by the Data Factory gold output.
_FEATURE_GROUP_ENGINE_USAGE: dict[str, tuple[str, ...]] = {
    "kline_return_features": ("engine_a", "engine_b", "engine_c", "engine_d"),
    "kline_trend_features": ("engine_a", "engine_b", "engine_c"),
    "kline_volume_features": ("engine_a", "engine_b", "engine_d"),
    "trade_flow_features": ("engine_a", "engine_b", "engine_c", "engine_d"),
    "trade_imbalance_features": ("engine_a", "engine_b", "engine_d"),
    "cvd_features": ("engine_a", "engine_b"),
    "spread_features": ("engine_c", "engine_d"),
    "depth_features": ("engine_c", "engine_d"),
    "ofi_features": ("engine_c", "engine_d"),
    "vpin_features": ("engine_c", "engine_d"),
    "queue_pressure": ("engine_c", "engine_d"),
    "session_tags": ("engine_a", "engine_b", "engine_c", "engine_d"),
    "engine_feature_readiness_flags": ("engine_a", "engine_b", "engine_c", "engine_d"),
}


# Built-in v1 threshold catalogue. Source paths are real but values are NOT
# re-asserted here — values live as code constants. This registry exists to
# make the *existence* and *source* of each threshold auditable.
_THRESHOLD_REGISTRY: tuple[tuple[str, str, str, str], ...] = (
    # (threshold_name, source_module, default_status, applies_to_engines_csv)
    (
        "ev_net_floor_bps",
        "src/scoring_backbone/ev_net_floor_thresholds.py",
        "THRESHOLD_DEFAULT",
        "engine_a,engine_b,engine_c,engine_d",
    ),
    (
        "cost_feasibility_min_edge_bps",
        "src/engines/engine_d/cost_feasibility_d.py",
        "THRESHOLD_DEFAULT",
        "engine_d",
    ),
    (
        "marginal_value_estimator_threshold",
        "src/engines/engine_d/marginal_value_estimator_d.py",
        "THRESHOLD_DEFAULT",
        "engine_d",
    ),
    (
        "first_episode_resolver_min_score",
        "src/engines/engine_d/first_episode_resolver_d.py",
        "THRESHOLD_DEFAULT",
        "engine_d",
    ),
    (
        "continuation_validator_min_score",
        "src/engines/engine_c/continuation_validator_c.py",
        "THRESHOLD_DEFAULT",
        "engine_c",
    ),
    (
        "spread_guard_max_spread_bps",
        "src/execution_backbone/spread_guard.py",
        "THRESHOLD_DEFAULT",
        "engine_c,engine_d",
    ),
)


class FeatureThresholdEntry(BaseModel, frozen=True):
    """One typed threshold with provenance and current status."""

    threshold_name: str = Field(..., min_length=1)
    source_module: str = Field(..., min_length=1)
    threshold_status: str = "THRESHOLD_NOT_PROVEN"
    threshold_source: str = "default"
    calibration_status: str = "CALIBRATION_NOT_PROVEN"
    calibration_artefact_path: str = ""
    applies_to_engines: tuple[str, ...] = ()
    reason_codes: tuple[str, ...] = ()


class FeatureGroupReadiness(BaseModel, frozen=True):
    """One feature group with engine consumers and gold-pipeline readiness."""

    feature_group: str = Field(..., min_length=1)
    feature_readiness_flag: str = "FEATURE_GROUP_NOT_PROVEN"
    used_by_engines: tuple[str, ...] = ()
    source_artifact: str = ""


class FeatureThresholdManifest(BaseModel, frozen=True):
    """Typed feature/threshold registry surfaced in the dashboard."""

    schema_version: str = Field(default="v1", min_length=1)
    run_id: str = ""
    pair: str = ""
    pairs: tuple[str, ...] = ()
    start: str = ""
    end: str = ""
    timeframes: tuple[str, ...] = ()
    engines: tuple[str, ...] = ("engine_a", "engine_b", "engine_c", "engine_d")
    output_root: str = ""

    feature_groups_available: tuple[FeatureGroupReadiness, ...] = ()
    feature_groups_missing: tuple[str, ...] = ()
    thresholds_used: tuple[FeatureThresholdEntry, ...] = ()

    # Status surfacing — copied from related manifests so the cockpit can
    # render one consolidated panel without joining multiple JSON files.
    orderbook_snapshot_status: str = "ORDERBOOK_SNAPSHOT_NOT_PROVEN"
    orderbook_delta_status: str = "ORDERBOOK_DELTA_NOT_PROVEN"
    depth20_proof_status: str = "BOOK_DEPTH_NOT_PROVEN"
    phase1_candidate_discovery_status: str = "PHASE1_FEATURE_DISCOVERY_NOT_PROVEN"
    phase2_detailed_replay_status: str = "PHASE2_DETAILED_REPLAY_NOT_PROVEN"

    reason_codes: tuple[str, ...] = ()
    artifact_hash: str | None = None
    created_at: datetime | None = None


def _read_json(path: Path) -> dict[str, object]:
    if not path.is_file():
        return {}
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {}
    try:
        payload = json.loads(text)
    except (TypeError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _classify_feature_group_readiness(
    group: str,
    *,
    gold_status: str,
    feature_paths: tuple[str, ...],
) -> str:
    """Map gold feature store status → per-group readiness."""

    if gold_status == "FEATURE_STORE_READY" and feature_paths:
        return "FEATURE_GROUP_READY"
    if gold_status == "FEATURE_STORE_READY":
        return "FEATURE_GROUP_READY"
    if gold_status.endswith("_PARTIAL"):
        return "FEATURE_GROUP_PARTIAL"
    return "FEATURE_GROUP_NOT_PROVEN"


def build_feature_threshold_manifest(
    *,
    output_root: Path,
    run_id: str = "",
    pairs: tuple[str, ...] = (),
    start: str = "",
    end: str = "",
    timeframes: tuple[str, ...] = (),
    engines: tuple[str, ...] = ("engine_a", "engine_b", "engine_c", "engine_d"),
    calibration_artefact_paths: dict[str, Path] | None = None,
) -> FeatureThresholdManifest:
    """Assemble the typed feature/threshold manifest.

    ``calibration_artefact_paths`` is an optional mapping
    ``{threshold_name: Path}`` — when supplied AND the path exists, the
    matching threshold flips to ``THRESHOLD_CALIBRATED`` with the source
    path recorded. Without a path or with a missing file, the threshold
    stays ``THRESHOLD_DEFAULT``. This module never claims calibration
    without explicit evidence.
    """

    gold_payload = _read_json(output_root / "gold_feature_manifest.json")
    gold_status = (
        str(gold_payload.get("gold_feature_store_status") or "GOLD_FEATURE_STORE_NOT_READY")
        if isinstance(gold_payload, dict)
        else "GOLD_FEATURE_STORE_NOT_READY"
    )
    feature_groups_raw = (
        gold_payload.get("feature_groups") if isinstance(gold_payload, dict) else None
    )
    feature_groups_present: tuple[str, ...] = (
        tuple(str(item) for item in feature_groups_raw)
        if isinstance(feature_groups_raw, list)
        else ()
    )
    feature_paths_raw = (
        gold_payload.get("feature_paths") if isinstance(gold_payload, dict) else None
    )
    feature_paths: tuple[str, ...] = (
        tuple(str(item) for item in feature_paths_raw)
        if isinstance(feature_paths_raw, list)
        else ()
    )

    # Build per-group readiness rows.
    available_rows: list[FeatureGroupReadiness] = []
    expected_groups = set(_FEATURE_GROUP_ENGINE_USAGE.keys())
    seen_groups: set[str] = set()
    for group in feature_groups_present:
        readiness = _classify_feature_group_readiness(
            group, gold_status=gold_status, feature_paths=feature_paths
        )
        engines_for_group = _FEATURE_GROUP_ENGINE_USAGE.get(group, engines)
        available_rows.append(
            FeatureGroupReadiness(
                feature_group=group,
                feature_readiness_flag=readiness,
                used_by_engines=engines_for_group,
                source_artifact="gold_feature_manifest.json",
            )
        )
        seen_groups.add(group)
    feature_groups_missing = tuple(sorted(expected_groups - seen_groups))

    # Build threshold registry entries.
    calib_paths = calibration_artefact_paths or {}
    threshold_rows: list[FeatureThresholdEntry] = []
    for name, source_module, default_status, engines_csv in _THRESHOLD_REGISTRY:
        applies_to = tuple(part.strip() for part in engines_csv.split(",") if part.strip())
        calib_path = calib_paths.get(name)
        if calib_path is not None and Path(calib_path).is_file():
            status = "THRESHOLD_CALIBRATED"
            threshold_source = "calibration_artefact"
            calibration_status = "CALIBRATION_READY"
            calibration_artefact_path = str(Path(calib_path).resolve())
            reason_codes: tuple[str, ...] = ()
        else:
            status = default_status if default_status in _ALLOWED_THRESHOLD_STATUSES else "THRESHOLD_NOT_PROVEN"
            threshold_source = "code_constant" if status == "THRESHOLD_DEFAULT" else "unknown"
            calibration_status = "CALIBRATION_NOT_PROVEN"
            calibration_artefact_path = ""
            reason_codes = (f"{name}_{status}",)
        threshold_rows.append(
            FeatureThresholdEntry(
                threshold_name=name,
                source_module=source_module,
                threshold_status=status,
                threshold_source=threshold_source,
                calibration_status=calibration_status,
                calibration_artefact_path=calibration_artefact_path,
                applies_to_engines=applies_to,
                reason_codes=reason_codes,
            )
        )

    # Surface related-manifest statuses for one-panel rendering.
    proof_payload = _read_json(output_root / "backtest_proof_matrix.json")
    orderbook_snapshot_status = str(
        proof_payload.get("orderbook_snapshot_status") or "ORDERBOOK_SNAPSHOT_NOT_PROVEN"
    ) if isinstance(proof_payload, dict) else "ORDERBOOK_SNAPSHOT_NOT_PROVEN"
    orderbook_delta_status = str(
        proof_payload.get("orderbook_delta_status") or "ORDERBOOK_DELTA_NOT_PROVEN"
    ) if isinstance(proof_payload, dict) else "ORDERBOOK_DELTA_NOT_PROVEN"
    depth20_proof_status = str(
        proof_payload.get("depth20_proof_status") or "BOOK_DEPTH_NOT_PROVEN"
    ) if isinstance(proof_payload, dict) else "BOOK_DEPTH_NOT_PROVEN"
    phase1_status = str(
        proof_payload.get("phase1_feature_discovery_status")
        or "PHASE1_FEATURE_DISCOVERY_NOT_PROVEN"
    ) if isinstance(proof_payload, dict) else "PHASE1_FEATURE_DISCOVERY_NOT_PROVEN"
    phase2_status = str(
        proof_payload.get("phase2_detailed_replay_status")
        or "PHASE2_DETAILED_REPLAY_NOT_PROVEN"
    ) if isinstance(proof_payload, dict) else "PHASE2_DETAILED_REPLAY_NOT_PROVEN"

    reason_codes: list[str] = []
    if not feature_groups_present:
        reason_codes.append("FEATURE_GROUPS_NOT_PROVEN")
    if not threshold_rows:
        reason_codes.append("THRESHOLDS_NOT_PROVEN")

    manifest = FeatureThresholdManifest(
        run_id=run_id,
        pair=pairs[0] if pairs else "",
        pairs=tuple(pairs),
        start=start,
        end=end,
        timeframes=tuple(timeframes),
        engines=tuple(engines),
        output_root=str(output_root.resolve()),
        feature_groups_available=tuple(available_rows),
        feature_groups_missing=feature_groups_missing,
        thresholds_used=tuple(threshold_rows),
        orderbook_snapshot_status=orderbook_snapshot_status,
        orderbook_delta_status=orderbook_delta_status,
        depth20_proof_status=depth20_proof_status,
        phase1_candidate_discovery_status=phase1_status,
        phase2_detailed_replay_status=phase2_status,
        reason_codes=tuple(dict.fromkeys(reason_codes)),
        created_at=datetime.now(tz=UTC),
    )
    return finalize_hashed_model(manifest)


def write_feature_threshold_manifest(
    output_root: Path,
    manifest: FeatureThresholdManifest,
    *,
    write_markdown: bool = True,
) -> Path:
    """Persist the manifest as ``feature_threshold_manifest.json``."""

    output_root.mkdir(parents=True, exist_ok=True)
    json_path = output_root / "feature_threshold_manifest.json"
    atomic_write_json(json_path, manifest.model_dump(mode="json"), indent=2)
    if write_markdown:
        atomic_write_text(
            output_root / "feature_threshold_manifest.md",
            _format_markdown(manifest),
        )
    return json_path


def _format_markdown(manifest: FeatureThresholdManifest) -> str:
    lines: list[str] = []
    lines.append(f"# Feature & Threshold Manifest — {manifest.run_id or 'unnamed'}")
    lines.append("")
    lines.append(f"- pairs: {', '.join(manifest.pairs) or '(none)'}")
    lines.append(f"- start / end: {manifest.start or '(none)'} / {manifest.end or '(none)'}")
    lines.append(f"- engines: {', '.join(manifest.engines)}")
    lines.append("")
    lines.append("## Feature groups available")
    if manifest.feature_groups_available:
        lines.append("| Group | Readiness | Used by |")
        lines.append("|---|---|---|")
        for row in manifest.feature_groups_available:
            lines.append(
                f"| {row.feature_group} | {row.feature_readiness_flag} | {', '.join(row.used_by_engines)} |"
            )
    else:
        lines.append("- (none)")
    lines.append("")
    if manifest.feature_groups_missing:
        lines.append("## Missing feature groups")
        for missing in manifest.feature_groups_missing:
            lines.append(f"- {missing}")
        lines.append("")
    lines.append("## Thresholds")
    lines.append("| Name | Status | Source | Calibration | Engines |")
    lines.append("|---|---|---|---|---|")
    for entry in manifest.thresholds_used:
        lines.append(
            f"| {entry.threshold_name} | {entry.threshold_status} | "
            f"`{entry.source_module}` | {entry.calibration_status} | "
            f"{', '.join(entry.applies_to_engines)} |"
        )
    return "\n".join(lines) + "\n"


def emit_feature_threshold_manifest(
    *,
    output_root: Path,
    run_id: str = "",
    pairs: tuple[str, ...] = (),
    start: str = "",
    end: str = "",
    timeframes: tuple[str, ...] = (),
    engines: tuple[str, ...] = ("engine_a", "engine_b", "engine_c", "engine_d"),
    calibration_artefact_paths: dict[str, Path] | None = None,
    write_markdown: bool = True,
) -> tuple[FeatureThresholdManifest, Path]:
    """Build and persist the manifest in one call."""

    manifest = build_feature_threshold_manifest(
        output_root=output_root,
        run_id=run_id,
        pairs=pairs,
        start=start,
        end=end,
        timeframes=timeframes,
        engines=engines,
        calibration_artefact_paths=calibration_artefact_paths,
    )
    json_path = write_feature_threshold_manifest(
        output_root, manifest, write_markdown=write_markdown
    )
    return manifest, json_path


__all__ = [
    "FeatureGroupReadiness",
    "FeatureThresholdEntry",
    "FeatureThresholdManifest",
    "build_feature_threshold_manifest",
    "emit_feature_threshold_manifest",
    "write_feature_threshold_manifest",
]
