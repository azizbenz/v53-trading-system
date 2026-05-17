from __future__ import annotations

import json
from pathlib import Path
import shutil
from uuid import uuid4

from cockpit.state_feature_bridge import read_feature_bridge


def _scratch_dir(label: str) -> Path:
    repo_root = Path(__file__).resolve().parents[2]
    base_dir = repo_root / ".test_tmp"
    base_dir.mkdir(parents=True, exist_ok=True)
    output_dir = base_dir / f"{label}_{uuid4().hex}"
    output_dir.mkdir(parents=True, exist_ok=False)
    return output_dir


def test_feature_bridge_extracts_feature_families() -> None:
    scratch = _scratch_dir("feature_bridge_families")
    try:
        export_dir = scratch / "auto_exports" / "2026-04-27"
        export_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "bridge_status": "ok",
            "feature_keys": [
                "snapshot_last_price",
                "snapshot_spread_bps",
                "trade_notional_usdt",
                "spread_bps",
            ],
            "recognized_feature_keys": ["snapshot_last_price", "trade_notional_usdt"],
            "unrecognized_feature_keys": ["snapshot_spread_bps", "spread_bps"],
        }
        (export_dir / "feature_bridge.json").write_text(
            json.dumps(payload, indent=2),
            encoding="utf-8",
        )

        snapshot = read_feature_bridge(scratch / "auto_exports")

        assert snapshot.source_status == "ok"
        assert snapshot.artifact_presence_status == "ARTIFACT_PRESENT_ONLY"
        assert snapshot.runtime_consumption_status == "NOT_PROVEN"
        assert snapshot.runtime_active is False
        assert snapshot.feature_families == ("snapshot", "trade", "spread")
        assert snapshot.recognized_feature_families == ("snapshot", "trade")
        assert snapshot.unrecognized_feature_families == ("snapshot", "spread")
        assert tuple(row.family for row in snapshot.feature_family_statuses) == (
            "snapshot",
            "trade",
            "spread",
        )
        assert all(row.runtime_status == "NOT_PROVEN" for row in snapshot.feature_family_statuses)
        assert all(row.runtime_lifecycle_status == "NOT_PROVEN" for row in snapshot.feature_family_statuses)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_feature_bridge_marks_research_only_registry_features_as_not_runtime_active() -> None:
    scratch = _scratch_dir("feature_bridge_research_only")
    try:
        export_dir = scratch / "auto_exports" / "2026-04-27"
        export_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "bridge_status": "ok",
            "feature_keys": ["pin.easley_kiefer_ohara_paperman"],
            "recognized_feature_keys": ["pin.easley_kiefer_ohara_paperman"],
            "unrecognized_feature_keys": [],
        }
        (export_dir / "feature_bridge.json").write_text(
            json.dumps(payload, indent=2),
            encoding="utf-8",
        )

        snapshot = read_feature_bridge(scratch / "auto_exports")

        assert snapshot.runtime_active is False
        assert snapshot.runtime_consumption_status == "NOT_PROVEN"
        assert len(snapshot.feature_family_statuses) == 1
        row = snapshot.feature_family_statuses[0]
        assert row.family == "pin"
        assert row.runtime_lifecycle_status == "FUTURE_RESERVED"
        assert row.registry_intent_status == "OFFLINE_PARAMETER_SEAM"
        assert row.display_status == "gray"
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
