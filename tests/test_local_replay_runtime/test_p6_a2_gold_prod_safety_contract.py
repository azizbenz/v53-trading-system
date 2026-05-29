"""P6 (2026-05-29) — test A8 audit-conformant rename + allowed/blocked_usage arrays.

Covers A8 from A2_GOLD_PROD_SAFE_CLEANUP_SPEC:
  - Producer emits both `a2_gold_prod_safety_contract.json` (canonical) and
    `data_factory_prod_safety_report.json` (legacy back-compat)
  - Payload includes `allowed_usage[]` and `blocked_usage[]` arrays
  - Schema version bumped to v2
  - a2_cache reader handles both filenames with canonical-first fallback

This is a back-compat rename: zero breaking change for consumers reading
either filename, but new audit consumers can rely on the canonical name.
"""

from __future__ import annotations

import json
from pathlib import Path

from local_replay_runtime.a2_cache import (
    PROD_SAFETY_CONTRACT_FILENAME,
    PROD_SAFETY_REPORT_FILENAME,
    read_prod_safety_snapshot,
)


def test_a2_cache_exposes_both_canonical_and_legacy_filename_constants() -> None:
    assert PROD_SAFETY_CONTRACT_FILENAME == "a2_gold_prod_safety_contract.json"
    assert PROD_SAFETY_REPORT_FILENAME == "data_factory_prod_safety_report.json"


def _write_payload(report_dir: Path, filename: str, payload: dict) -> None:
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / filename).write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )


def test_read_prod_safety_snapshot_prefers_canonical_filename(tmp_path: Path) -> None:
    """When both files exist, the canonical one wins (post-P6 runs)."""
    canonical_payload = {
        "prod_safety_status": "DATA_FACTORY_PROD_SAFE",
        "prod_safe": True,
        "blocker_codes": [],
        "allowed_usage": ["RESEARCH", "B1_DISCOVERY", "B_ML_TRAINING_GOVERNED"],
        "blocked_usage": [],
    }
    legacy_payload = {
        "prod_safety_status": "STALE_LEGACY_VERDICT",
        "prod_safe": False,
        "blocker_codes": ["LEGACY_BLOCKER"],
    }
    _write_payload(tmp_path, PROD_SAFETY_CONTRACT_FILENAME, canonical_payload)
    _write_payload(tmp_path, PROD_SAFETY_REPORT_FILENAME, legacy_payload)

    status, prod_safe, blockers = read_prod_safety_snapshot(tmp_path)

    assert status == "DATA_FACTORY_PROD_SAFE"
    assert prod_safe is True
    assert blockers == ()


def test_read_prod_safety_snapshot_falls_back_to_legacy_filename(tmp_path: Path) -> None:
    """Pre-P6 cached runs only have the legacy file → reader must still find it."""
    legacy_payload = {
        "prod_safety_status": "RESEARCH_ONLY_NOT_PROD_SAFE",
        "prod_safe": False,
        "blocker_codes": ["RAW_SOURCE_TYPE_AMBIGUOUS", "METADATA_NOT_PROD_PROVEN"],
    }
    _write_payload(tmp_path, PROD_SAFETY_REPORT_FILENAME, legacy_payload)

    status, prod_safe, blockers = read_prod_safety_snapshot(tmp_path)

    assert status == "RESEARCH_ONLY_NOT_PROD_SAFE"
    assert prod_safe is False
    assert "RAW_SOURCE_TYPE_AMBIGUOUS" in blockers
    assert "METADATA_NOT_PROD_PROVEN" in blockers


def test_read_prod_safety_snapshot_returns_not_proven_when_neither_file_exists(
    tmp_path: Path,
) -> None:
    status, prod_safe, blockers = read_prod_safety_snapshot(tmp_path)

    assert status == "PROD_SAFETY_NOT_PROVEN"
    assert prod_safe is False
    assert blockers == ()


def test_payload_schema_version_bumped_and_includes_usage_arrays() -> None:
    """Sentinel: source code of _build_data_factory_prod_safety_report must
    reference the new schema version + the two usage-array literals.

    Full integration coverage of the producer lives in
    test_strategy_ladder_data_factory.py.
    """
    from local_replay_runtime import strategy_ladder_data_factory as df_module

    source = df_module._build_data_factory_prod_safety_report.__code__
    consts_repr = " ".join(repr(c) for c in source.co_consts)
    assert "a2_gold_prod_safety_contract.v2" in consts_repr
    assert "allowed_usage" in consts_repr
    assert "blocked_usage" in consts_repr
    # Audit-conformant usage taxonomy must appear in the constants
    assert "RESEARCH" in consts_repr
    assert "PROFITABILITY_TRUTH" in consts_repr
    assert "ML_PROMOTION_TRAINING" in consts_repr
    assert "LIVE_PROMOTION" in consts_repr
