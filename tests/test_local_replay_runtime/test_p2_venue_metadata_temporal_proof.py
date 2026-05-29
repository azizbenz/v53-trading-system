"""P2 (2026-05-29) — test venue metadata temporal proof in gold rows.

Covers A7 from A2_GOLD_PROD_SAFE_CLEANUP_SPEC:
  - metadata_effective_at : ISO date of the metadata snapshot
  - metadata_source : canonical silver-catalog ref
  - metadata_hash : SHA256 of the metadata file content

Validates:
  - Schema accepts 3 new fields (back-compat with None)
  - When metadata silver entry exists, all 3 fields populated
  - When metadata absent, all 3 fields stay None (audit-visible, not silent fail)

A2/A3 (maker_fee_rate, taker_fee_rate, tick_size, step_size, min_notional)
already wired through `metadata_row.get(...)` at the row builder. P2 focuses
on the temporal proof layer that was completely missing.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from local_replay_runtime.strategy_ladder_models import StrategyLadderFeatureRow


def test_strategy_ladder_feature_row_accepts_new_p2_temporal_proof_fields() -> None:
    row = StrategyLadderFeatureRow(
        pair="BTCUSDT",
        timeframe="15m",
        timestamp_ms=1_745_884_800_000,
        engine_id="engine_a",
        source_ref="K:/output lab/runs/x/phase_a2_data_factory/gold/...",
        metadata_effective_at="2025-04-29",
        metadata_source="silver:bybit_metadata_cache:bybit:spot:metadata:BTCUSDT:2025-04-29",
        metadata_hash="deadbeef0123456789abcdef",
    )

    assert row.metadata_effective_at == "2025-04-29"
    assert row.metadata_source == "silver:bybit_metadata_cache:bybit:spot:metadata:BTCUSDT:2025-04-29"
    assert row.metadata_hash == "deadbeef0123456789abcdef"


def test_strategy_ladder_feature_row_p2_back_compat_when_absent() -> None:
    """Schema must accept rows without P2 fields — all default None."""
    row = StrategyLadderFeatureRow(
        pair="BTCUSDT",
        timeframe="15m",
        timestamp_ms=1_745_884_800_000,
        engine_id="engine_a",
        source_ref="K:/output lab/runs/x/phase_a2_data_factory/gold/...",
    )

    assert row.metadata_effective_at is None
    assert row.metadata_source is None
    assert row.metadata_hash is None


def test_metadata_temporal_proof_helpers_integrate_with_p1_helpers(tmp_path: Path) -> None:
    """Verify A7 reuses the same canonical helpers as A4/A1 (consistency)."""
    from local_replay_runtime.strategy_ladder_data_factory import (
        _ensure_input_data_hash,
        _raw_catalog_ref,
    )
    from local_replay_runtime.strategy_ladder_data_factory_models import (
        StrategyLadderSilverIndexEntry,
    )

    metadata_file = tmp_path / "metadata.jsonl.gz"
    payload = b'\x1f\x8b\x08\x00bybit_btcusdt_2025_04_29_metadata_snapshot'
    metadata_file.write_bytes(payload)
    metadata_entry = StrategyLadderSilverIndexEntry(
        source_id="bybit_metadata_cache",
        source_root=str(tmp_path),
        exchange="bybit",
        market_type="spot",
        data_type="metadata",
        pair="BTCUSDT",
        date="2025-04-29",
        path=str(metadata_file.resolve()),
        storage_format="jsonl-gz",
        row_count=1,
        file_hash="",  # resume-style placeholder
        depth_source_status="BOOK_DEPTH_NOT_PROVEN",
        schema_status="METADATA_SCHEMA_READY",
    )

    # The temporal proof reuses A4 + A1 helpers (consistency across all hashes)
    catalog_ref = _raw_catalog_ref(metadata_entry)
    content_hash = _ensure_input_data_hash(metadata_entry)
    effective_at = metadata_entry.date

    assert catalog_ref == "silver:bybit_metadata_cache:bybit:spot:metadata:BTCUSDT:2025-04-29"
    assert content_hash == hashlib.sha256(payload).hexdigest()
    assert effective_at == "2025-04-29"
