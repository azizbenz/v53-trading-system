from __future__ import annotations

import json

from cockpit.state_lab_vps_transfer import read_lab_vps_transfer

from ._operational_helpers import build_paths, cleanup_scratch, scratch_dir, seed_phase25_files


def test_lab_vps_transfer_detects_matches_and_missing_artifacts() -> None:
    scratch = scratch_dir("lab_vps_transfer")
    try:
        paths = build_paths(scratch)
        seed_phase25_files(paths)
        snapshot = read_lab_vps_transfer(paths)
        items = {item.name: item for item in snapshot.items}
        assert snapshot.overall_status == "missing_on_vps"
        assert snapshot.hash_match_count == 2
        assert snapshot.missing_on_vps_count >= 1
        assert snapshot.mismatch_count == 0
        assert items["model_artifact"].status == "hash_match"
        assert items["review_bundle"].status == "missing_on_vps"
        assert items["feature_export"].status == "hash_match"
    finally:
        cleanup_scratch(scratch)


def test_lab_vps_transfer_detects_mismatch() -> None:
    scratch = scratch_dir("lab_vps_transfer_mismatch")
    try:
        paths = build_paths(scratch)
        seed_phase25_files(paths)
        manifest_path = paths.auto_exports_root / "2026-04-27" / "replay_run_manifest.json"
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        payload["artifact_hash"] = "different"
        manifest_path.write_text(json.dumps(payload), encoding="utf-8")
        snapshot = read_lab_vps_transfer(paths)
        items = {item.name: item for item in snapshot.items}
        assert snapshot.overall_status == "mismatch"
        assert snapshot.mismatch_count == 1
        assert items["model_artifact"].status == "mismatch"
    finally:
        cleanup_scratch(scratch)
