"""P0-C-strict (2026-05-29) — cockpit read-side for runtime feature parity.

Exposes `RuntimeFeatureParityManifest` data (status, blockers, train vs
runtime feature diff) to the cockpit dashboard.

Designed for templates that render a "Feature Parity" card showing:
  - status (READY / BLOCKED_BY_*)
  - blocker_codes (machine-readable)
  - training_feature_names + runtime_feature_names + diff sets
  - red banner when status starts with RUNTIME_PARITY_BLOCKED_BY_*

This is the cockpit-visibility component of the strict feature-parity
governance chain: train/runtime undertrained features no longer fail
silently. They produce a blocker in the manifest that this module surfaces.

Reads `runtime_feature_parity_manifest.json` produced by
`local_replay_runtime.data_science_quality_gates.write_quality_reports`.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field


RUNTIME_PARITY_MANIFEST_FILENAME = "runtime_feature_parity_manifest.json"
NOT_FOUND_STATUS = "RUNTIME_PARITY_MANIFEST_NOT_FOUND"
PARSE_ERROR_STATUS = "RUNTIME_PARITY_MANIFEST_PARSE_ERROR"
BLOCKED_PREFIX = "RUNTIME_PARITY_BLOCKED_BY_"


class RuntimeFeatureParityCardSnapshot(BaseModel, frozen=True):
    """Cockpit-facing view-model for the runtime feature parity card."""

    source_path: str = ""
    status: str = NOT_FOUND_STATUS
    is_blocked: bool = False
    blocker_codes: tuple[str, ...] = ()
    training_feature_names: tuple[str, ...] = ()
    runtime_feature_names: tuple[str, ...] = ()
    missing_runtime_feature_names: tuple[str, ...] = ()
    extra_runtime_feature_names: tuple[str, ...] = ()
    training_feature_count: int = Field(default=0, ge=0)
    runtime_feature_count: int = Field(default=0, ge=0)
    feature_hash: str = ""


def read_runtime_feature_parity_card(report_root: Path) -> RuntimeFeatureParityCardSnapshot:
    """Read the runtime feature parity manifest produced by A2/B2.

    Args:
      report_root: directory containing `runtime_feature_parity_manifest.json`
        (typically the phase_a2_data_factory or per-run report root).

    Returns:
      A frozen snapshot with status, blockers, and feature diff sets.
      When the manifest is missing or unparseable, returns a snapshot whose
      status reflects the failure mode (not an exception).
    """

    manifest_path = report_root / RUNTIME_PARITY_MANIFEST_FILENAME
    if not manifest_path.is_file():
        return RuntimeFeatureParityCardSnapshot(
            source_path=str(manifest_path),
            status=NOT_FOUND_STATUS,
            is_blocked=False,
        )
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return RuntimeFeatureParityCardSnapshot(
            source_path=str(manifest_path),
            status=PARSE_ERROR_STATUS,
            is_blocked=True,
            blocker_codes=(PARSE_ERROR_STATUS,),
        )
    if not isinstance(payload, dict):
        return RuntimeFeatureParityCardSnapshot(
            source_path=str(manifest_path),
            status=PARSE_ERROR_STATUS,
            is_blocked=True,
            blocker_codes=(PARSE_ERROR_STATUS,),
        )

    status = str(payload.get("status") or NOT_FOUND_STATUS)
    blocker_codes = tuple(str(code) for code in (payload.get("blocker_codes") or ()))
    training = tuple(str(name) for name in (payload.get("training_feature_names") or ()))
    runtime = tuple(str(name) for name in (payload.get("runtime_feature_names") or ()))
    missing = tuple(str(name) for name in (payload.get("missing_runtime_feature_names") or ()))
    extra = tuple(str(name) for name in (payload.get("extra_runtime_feature_names") or ()))

    return RuntimeFeatureParityCardSnapshot(
        source_path=str(manifest_path),
        status=status,
        is_blocked=status.startswith(BLOCKED_PREFIX),
        blocker_codes=blocker_codes,
        training_feature_names=training,
        runtime_feature_names=runtime,
        missing_runtime_feature_names=missing,
        extra_runtime_feature_names=extra,
        training_feature_count=len(training),
        runtime_feature_count=len(runtime),
        feature_hash=str(payload.get("feature_hash") or ""),
    )


__all__ = [
    "RUNTIME_PARITY_MANIFEST_FILENAME",
    "RuntimeFeatureParityCardSnapshot",
    "read_runtime_feature_parity_card",
]
