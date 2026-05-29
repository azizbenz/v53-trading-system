"""P1 (2026-05-29) — test 4 hashes for gold row reproducibility.

Covers A1+A4+A5+A6 from A2_GOLD_PROD_SAFE_CLEANUP_SPEC:
  - A1 input_data_hash : SHA256 of raw source file (lazily computed on resume)
  - A4 raw_catalog_ref : canonical silver index entry reference
  - A5 method_version_hash : SHA256-16 of gold builder module content + version
  - A6 feature_set_hash : deterministic hash of active feature names set

Validates:
  - Helpers individually (4 tests)
  - Schema accepts new fields (1 test)
  - Resume placeholder triggers lazy file hash computation (1 test)
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from local_replay_runtime.strategy_ladder_data_factory import (
    _ensure_input_data_hash,
    _feature_set_hash,
    _gold_method_version_hash,
    _raw_catalog_ref,
)
from local_replay_runtime.strategy_ladder_data_factory_models import (
    StrategyLadderSilverIndexEntry,
)
from local_replay_runtime.strategy_ladder_models import StrategyLadderFeatureRow


def _make_entry(*, file_hash: str = "", path: Path | None = None) -> StrategyLadderSilverIndexEntry:
    return StrategyLadderSilverIndexEntry(
        source_id="raw_bybit_spot",
        source_root="L:/klines",
        exchange="bybit",
        market_type="spot",
        data_type="ohlcv",
        pair="BTCUSDT",
        date="2025-04-29",
        path=str(path or Path("L:/klines/BTCUSDT/15m/2025/04/29.jsonl.gz")),
        storage_format="jsonl-gz",
        row_count=96,
        file_hash=file_hash,
        depth_source_status="BOOK_DEPTH_NOT_PROVEN",
        schema_status="TRADE_SCHEMA_READY",
    )


def test_gold_method_version_hash_returns_versioned_content_digest() -> None:
    h = _gold_method_version_hash()

    assert h.startswith("strategy_ladder.gold.v1#")
    suffix = h.split("#", 1)[1]
    assert len(suffix) == 16
    assert all(c in "0123456789abcdef" for c in suffix)
    # Idempotent (cached)
    assert _gold_method_version_hash() == h


def test_feature_set_hash_is_deterministic_for_same_keys() -> None:
    h1 = _feature_set_hash({"close_return": 0.001, "volume": 12.0, "vpin": 0.3})
    h2 = _feature_set_hash({"vpin": 99.9, "volume": 1.0, "close_return": -0.5})

    # Same keys, different values → same hash (we hash NAMES not values)
    assert h1 == h2
    assert len(h1) == 16


def test_feature_set_hash_changes_when_keys_change() -> None:
    h1 = _feature_set_hash({"close_return": 0.001, "volume": 12.0})
    h2 = _feature_set_hash({"close_return": 0.001, "volume": 12.0, "vpin": 0.3})

    # Adding a new feature → different hash → detects silent feature drift
    assert h1 != h2


def test_raw_catalog_ref_builds_canonical_silver_reference() -> None:
    entry = _make_entry()

    ref = _raw_catalog_ref(entry)

    assert ref == "silver:raw_bybit_spot:bybit:spot:ohlcv:BTCUSDT:2025-04-29"


def test_ensure_input_data_hash_returns_existing_file_hash_when_present() -> None:
    entry = _make_entry(file_hash="abc123def456")

    result = _ensure_input_data_hash(entry)

    assert result == "abc123def456"


def test_ensure_input_data_hash_computes_sha256_when_resume_placeholder_with_real_file(
    tmp_path: Path,
) -> None:
    """Resume entries have file_hash='' but file exists on disk.

    The helper must compute the SHA256 of the file content rather than return
    empty (which is the legacy bug propagated into gold rows as
    `input_data_hash: ""`).
    """
    silver_file = tmp_path / "real.jsonl.gz"
    silver_file.write_bytes(b"\x1f\x8b\x08\x00real_compressed_data_xyz")
    entry = _make_entry(file_hash="", path=silver_file)

    result = _ensure_input_data_hash(entry)

    expected = hashlib.sha256(silver_file.read_bytes()).hexdigest()
    assert result == expected
    assert result != ""


def test_ensure_input_data_hash_returns_empty_when_resume_placeholder_with_missing_file(
    tmp_path: Path,
) -> None:
    entry = _make_entry(file_hash="", path=tmp_path / "does_not_exist.jsonl.gz")

    result = _ensure_input_data_hash(entry)

    assert result == ""


def test_ensure_input_data_hash_returns_empty_when_file_is_zero_bytes(tmp_path: Path) -> None:
    empty = tmp_path / "empty.jsonl.gz"
    empty.write_bytes(b"")
    entry = _make_entry(file_hash="", path=empty)

    result = _ensure_input_data_hash(entry)

    assert result == ""


def test_strategy_ladder_feature_row_accepts_new_p1_fields() -> None:
    """Schema must accept raw_catalog_ref + feature_set_hash without crash."""
    row = StrategyLadderFeatureRow(
        pair="BTCUSDT",
        timeframe="15m",
        timestamp_ms=1_745_884_800_000,
        engine_id="engine_a",
        source_ref="K:/output lab/runs/x/phase_a2_data_factory/gold/...",
        input_data_hash="abc123",
        method_version_hash="strategy_ladder.gold.v1#deadbeefcafef00d",
        raw_catalog_ref="silver:raw_bybit_spot:bybit:spot:ohlcv:BTCUSDT:2025-04-29",
        feature_set_hash="1234567890abcdef",
    )

    assert row.input_data_hash == "abc123"
    assert row.method_version_hash == "strategy_ladder.gold.v1#deadbeefcafef00d"
    assert row.raw_catalog_ref == "silver:raw_bybit_spot:bybit:spot:ohlcv:BTCUSDT:2025-04-29"
    assert row.feature_set_hash == "1234567890abcdef"


def test_strategy_ladder_feature_row_back_compat_when_p1_fields_absent() -> None:
    """Existing rows without P1 fields must still validate (optional fields)."""
    row = StrategyLadderFeatureRow(
        pair="BTCUSDT",
        timeframe="15m",
        timestamp_ms=1_745_884_800_000,
        engine_id="engine_a",
        source_ref="K:/output lab/runs/x/phase_a2_data_factory/gold/...",
    )

    assert row.raw_catalog_ref is None
    assert row.feature_set_hash is None
