"""Cockpit read helpers for Strategy Ladder run-class component coverage."""

from __future__ import annotations

import json
from pathlib import Path


def load_component_coverage_dashboard_fields(output_root: Path) -> dict[str, object]:
    """Return compact dashboard fields from run_class_component_coverage.json."""

    path = output_root / "run_class_component_coverage.json"
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, TypeError, ValueError):
        return {}
    if not isinstance(payload, dict):
        return {}
    components = payload.get("components")
    rows = tuple(
        {
            "component_id": str(item.get("component_id") or ""),
            "component_family": str(item.get("component_family") or ""),
            "status": str(item.get("status") or ""),
            "expected_for_run_class": bool(item.get("expected_for_run_class", False)),
            "invoked": bool(item.get("invoked", False)),
            "consumed_by": tuple(str(value) for value in item.get("consumed_by") or ()),
            "proof_artifact": str(item.get("proof_artifact") or ""),
            "reason_codes": tuple(str(value) for value in item.get("reason_codes") or ()),
        }
        for item in (components if isinstance(components, list) else ())
        if isinstance(item, dict)
    )
    counts = payload.get("component_status_counts")
    return {
        "run_class_component_coverage_path": str(path.resolve()),
        "run_class": str(payload.get("run_class") or "RUN_CLASS_NOT_PROVEN"),
        "run_class_id": str(payload.get("run_class_id") or "RUN_CLASS_NOT_PROVEN"),
        "component_status_counts": dict(counts) if isinstance(counts, dict) else {},
        "component_coverage_rows": rows[:40],
    }


__all__ = ["load_component_coverage_dashboard_fields"]
