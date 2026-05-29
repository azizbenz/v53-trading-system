"""P0-C-strict (2026-05-29) — tests for cockpit runtime feature parity card."""

from __future__ import annotations

import json
from pathlib import Path

from cockpit.state_runtime_feature_parity import (
    BLOCKED_PREFIX,
    NOT_FOUND_STATUS,
    PARSE_ERROR_STATUS,
    RUNTIME_PARITY_MANIFEST_FILENAME,
    read_runtime_feature_parity_card,
)


def _write_manifest(report_root: Path, payload: dict) -> None:
    report_root.mkdir(parents=True, exist_ok=True)
    (report_root / RUNTIME_PARITY_MANIFEST_FILENAME).write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )


def test_read_card_returns_not_found_when_manifest_absent(tmp_path: Path) -> None:
    snapshot = read_runtime_feature_parity_card(tmp_path)

    assert snapshot.status == NOT_FOUND_STATUS
    assert snapshot.is_blocked is False
    assert snapshot.blocker_codes == ()


def test_read_card_returns_parse_error_when_manifest_malformed(tmp_path: Path) -> None:
    (tmp_path / RUNTIME_PARITY_MANIFEST_FILENAME).write_text("not json {{", encoding="utf-8")

    snapshot = read_runtime_feature_parity_card(tmp_path)

    assert snapshot.status == PARSE_ERROR_STATUS
    assert snapshot.is_blocked is True
    assert PARSE_ERROR_STATUS in snapshot.blocker_codes


def test_read_card_returns_ready_snapshot_when_parity_matches(tmp_path: Path) -> None:
    features = ["close_return", "high_low_range", "volume", "vpin", "kyle_lambda"]
    _write_manifest(
        tmp_path,
        {
            "status": "RUNTIME_PARITY_SCHEMA_MATCH_READY",
            "blocker_codes": [],
            "training_feature_names": features,
            "runtime_feature_names": features,
            "missing_runtime_feature_names": [],
            "extra_runtime_feature_names": [],
            "feature_hash": "abc123",
        },
    )

    snapshot = read_runtime_feature_parity_card(tmp_path)

    assert snapshot.status == "RUNTIME_PARITY_SCHEMA_MATCH_READY"
    assert snapshot.is_blocked is False
    assert snapshot.training_feature_count == 5
    assert snapshot.runtime_feature_count == 5
    assert snapshot.training_feature_names == tuple(features)
    assert snapshot.feature_hash == "abc123"


def test_read_card_surfaces_undertrained_blocker_with_extra_features(tmp_path: Path) -> None:
    """The new P0-C-strict blocker must surface as is_blocked=True."""
    _write_manifest(
        tmp_path,
        {
            "status": "RUNTIME_PARITY_BLOCKED_BY_UNDERTRAINED_FEATURES",
            "blocker_codes": ["RUNTIME_PARITY_BLOCKED_BY_UNDERTRAINED_FEATURES"],
            "training_feature_names": ["close_return", "high_low_range", "volume"],
            "runtime_feature_names": ["close_return", "high_low_range", "volume", "vpin", "kyle_lambda"],
            "missing_runtime_feature_names": [],
            "extra_runtime_feature_names": ["kyle_lambda", "vpin"],
        },
    )

    snapshot = read_runtime_feature_parity_card(tmp_path)

    assert snapshot.status == "RUNTIME_PARITY_BLOCKED_BY_UNDERTRAINED_FEATURES"
    assert snapshot.is_blocked is True
    assert snapshot.status.startswith(BLOCKED_PREFIX)
    assert "RUNTIME_PARITY_BLOCKED_BY_UNDERTRAINED_FEATURES" in snapshot.blocker_codes
    assert snapshot.extra_runtime_feature_names == ("kyle_lambda", "vpin")
    assert snapshot.training_feature_count == 3
    assert snapshot.runtime_feature_count == 5


def test_read_card_surfaces_missing_runtime_blocker(tmp_path: Path) -> None:
    _write_manifest(
        tmp_path,
        {
            "status": "RUNTIME_PARITY_BLOCKED_BY_MISSING_RUNTIME_FEATURES",
            "blocker_codes": ["RUNTIME_PARITY_BLOCKED_BY_MISSING_RUNTIME_FEATURES"],
            "training_feature_names": ["close_return", "kyle_lambda"],
            "runtime_feature_names": ["close_return"],
            "missing_runtime_feature_names": ["kyle_lambda"],
            "extra_runtime_feature_names": [],
        },
    )

    snapshot = read_runtime_feature_parity_card(tmp_path)

    assert snapshot.is_blocked is True
    assert snapshot.missing_runtime_feature_names == ("kyle_lambda",)
