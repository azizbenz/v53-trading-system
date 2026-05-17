"""Phase 2.5 adapter - read Build-1 governance health exported by core smoke."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel

from cockpit.state_freshness import OperationalSourceSnapshot, source_stamp


class Build1CoreHealthSnapshot(OperationalSourceSnapshot):
    build1_manifest_status: str = "NOT_PROVEN"
    build1_dag_status: str = "NOT_PROVEN"
    build1_guardrail_status: str = "NOT_PROVEN"
    build1_smoke_status: str = "NOT_PROVEN"
    build1_core_health_status: str = "BLOCKED"


def read_build1_core_health(build_root: Path) -> Build1CoreHealthSnapshot:
    """Read the latest Build-1 governance health artifact."""

    artifact_path = build_root / "build9_core_smoke" / "build1_core_health.json"
    stamp = source_stamp(path=artifact_path, stale_after_seconds=86_400.0)
    if stamp["source_status"] != "ok":
        return Build1CoreHealthSnapshot(
            **stamp,
            build1_core_health_status="BLOCKED",
        )
    try:
        payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return Build1CoreHealthSnapshot(
            source_status="parse_error",
            source_file=str(artifact_path),
            last_modified_at=stamp["last_modified_at"],
            age_seconds=stamp["age_seconds"],
            reason_codes=("build1_core_health_parse_error",),
            build1_core_health_status="BLOCKED",
        )
    if not isinstance(payload, dict):
        return Build1CoreHealthSnapshot(
            source_status="parse_error",
            source_file=str(artifact_path),
            last_modified_at=stamp["last_modified_at"],
            age_seconds=stamp["age_seconds"],
            reason_codes=("build1_core_health_invalid_payload",),
            build1_core_health_status="BLOCKED",
        )
    stamp_without_reasons = {
        key: value for key, value in stamp.items() if key != "reason_codes"
    }
    return Build1CoreHealthSnapshot(
        **stamp_without_reasons,
        reason_codes=tuple(str(reason) for reason in payload.get("reason_codes") or ()),
        build1_manifest_status=str(payload.get("build1_manifest_status", "NOT_PROVEN")),
        build1_dag_status=str(payload.get("build1_dag_status", "NOT_PROVEN")),
        build1_guardrail_status=str(payload.get("build1_guardrail_status", "NOT_PROVEN")),
        build1_smoke_status=str(payload.get("build1_smoke_status", "NOT_PROVEN")),
        build1_core_health_status=str(payload.get("build1_core_health_status", "BLOCKED")),
    )


__all__ = ["Build1CoreHealthSnapshot", "read_build1_core_health"]
