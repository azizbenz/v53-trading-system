"""Tests for the A2 content-addressable cache."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from local_replay_runtime.a2_cache import (
    A2_CACHE_ENTRY_SCHEMA_VERSION,
    A2_CACHE_GOLD_SUBDIR,
    A2_CACHE_KEY_SCHEMA_VERSION,
    A2_CACHE_METADATA_FILENAME,
    A2_CACHE_PROGRESS_REPORT_FILENAME,
    A2_CACHE_SILVER_SUBDIR,
    ANTI_LEAKAGE_REPORT_FILENAME,
    PROD_SAFETY_REPORT_FILENAME,
    A2CacheKey,
    build_a2_cache_key,
    cache_root_for_hash,
    compute_input_hash,
    fingerprint_historical_metadata,
    fingerprint_raw_paths,
    lookup_a2_cache,
    populate_a2_cache,
    read_anti_leakage_snapshot,
    read_prod_safety_snapshot,
    restore_a2_from_cache,
)


def _write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def _make_raw_layout(root: Path) -> tuple[Path, ...]:
    """Create a small raw-source tree under `root` and return the root tuple."""

    _write(root / "BTCUSDT" / "2025-07-01.zip", b"PK\x03\x04A2_TEST_RAW_DATA")
    _write(root / "BTCUSDT" / "2025-07-02.zip", b"PK\x03\x04A2_TEST_RAW_DATA_2")
    _write(root / "BTCUSDT" / "ignored.txt", b"this is text, should be ignored")
    _write(root / "trades" / "2025-07-01.csv", b"ts,price,qty\n1,2,3\n")
    return (root,)


def _make_default_key(raw_roots: tuple[Path, ...]) -> A2CacheKey:
    return build_a2_cache_key(
        raw_roots=raw_roots,
        historical_metadata_root=None,
        pairs=("btcusdt",),
        engines=("engine_a", "engine_b"),
        timeframes=("15m",),
        feature_names=("close_return", "vpin", "cumulative_ofi"),
        start="2025-07-01",
        end="2025-07-03",
        data_types=("trades", "klines", "orderbook"),
        compression="zstd",
        storage_format="jsonl-gz",
        max_gold_feature_rows=0,
        use_measured_economic_provenance=False,
    )


def test_fingerprint_raw_paths_is_stable_and_filters_extensions(
    tmp_path: Path,
) -> None:
    raw_root = tmp_path / "raw"
    _make_raw_layout(raw_root)
    fingerprint_a, entries_a = fingerprint_raw_paths((raw_root,))
    fingerprint_b, entries_b = fingerprint_raw_paths((raw_root,))
    assert fingerprint_a == fingerprint_b
    # the .txt file must be filtered out
    paths = {entry.path for entry in entries_a}
    assert all(not p.endswith("ignored.txt") for p in paths)
    assert any(p.endswith("2025-07-01.zip") for p in paths)
    assert any(p.endswith("2025-07-01.csv") for p in paths)


def test_fingerprint_changes_when_file_size_changes(tmp_path: Path) -> None:
    raw_root = tmp_path / "raw"
    _make_raw_layout(raw_root)
    fingerprint_a, _ = fingerprint_raw_paths((raw_root,))
    # rewrite a file with different content/size
    (raw_root / "BTCUSDT" / "2025-07-01.zip").write_bytes(
        b"PK\x03\x04A2_TEST_RAW_DATA_NEW_AND_LONGER_PAYLOAD"
    )
    fingerprint_b, _ = fingerprint_raw_paths((raw_root,))
    assert fingerprint_a != fingerprint_b


def test_fingerprint_handles_missing_root(tmp_path: Path) -> None:
    missing_root = tmp_path / "does_not_exist"
    fingerprint, entries = fingerprint_raw_paths((missing_root,))
    assert fingerprint != ""
    assert entries == ()


def test_fingerprint_historical_metadata_absent_and_present(
    tmp_path: Path,
) -> None:
    assert fingerprint_historical_metadata(None) == "ABSENT"
    metadata_root = tmp_path / "metadata"
    metadata_root.mkdir(parents=True)
    (metadata_root / "pair.json").write_text('{"pair": "BTCUSDT"}', encoding="utf-8")
    fp = fingerprint_historical_metadata(metadata_root)
    assert fp not in {"", "ABSENT", "MISSING"}


def test_compute_input_hash_is_deterministic(tmp_path: Path) -> None:
    raw_root = tmp_path / "raw"
    _make_raw_layout(raw_root)
    key = _make_default_key((raw_root,))
    hash_a = compute_input_hash(key)
    hash_b = compute_input_hash(key)
    assert hash_a == hash_b
    assert len(hash_a) == 64  # sha256 hex


def test_compute_input_hash_changes_with_feature_names(tmp_path: Path) -> None:
    raw_root = tmp_path / "raw"
    _make_raw_layout(raw_root)
    key_a = _make_default_key((raw_root,))
    key_b = key_a.model_copy(update={"feature_names": ("close_return",)})
    assert compute_input_hash(key_a) != compute_input_hash(key_b)


def test_compute_input_hash_ignores_run_id_and_output_paths(
    tmp_path: Path,
) -> None:
    # The hash key intentionally does not contain run_id or output paths.
    # We assert this by building two keys with the same canonical fields and
    # comparing the hash.
    raw_root = tmp_path / "raw"
    _make_raw_layout(raw_root)
    key_a = _make_default_key((raw_root,))
    key_b = _make_default_key((raw_root,))
    assert compute_input_hash(key_a) == compute_input_hash(key_b)


def test_compute_input_hash_changes_with_use_measured_economic_provenance(
    tmp_path: Path,
) -> None:
    raw_root = tmp_path / "raw"
    _make_raw_layout(raw_root)
    key_a = _make_default_key((raw_root,))
    key_b = key_a.model_copy(update={"use_measured_economic_provenance": True})
    assert compute_input_hash(key_a) != compute_input_hash(key_b)


def test_lookup_returns_none_when_cache_root_missing(tmp_path: Path) -> None:
    cache_base = tmp_path / "cache"
    assert lookup_a2_cache(cache_base, "nonexistent-hash") is None


def test_populate_then_lookup_then_restore_roundtrip(tmp_path: Path) -> None:
    raw_root = tmp_path / "raw"
    _make_raw_layout(raw_root)
    silver_src = tmp_path / "run" / "phase_a2" / "silver"
    gold_src = tmp_path / "run" / "phase_a2" / "gold"
    progress_path = tmp_path / "run" / "phase_a2" / A2_CACHE_PROGRESS_REPORT_FILENAME
    _write(silver_src / "bybit" / "spot" / "BTCUSDT" / "2025-07-01.jsonl.gz", b"silver-1")
    _write(silver_src / "bybit" / "spot" / "BTCUSDT" / "2025-07-02.jsonl.gz", b"silver-2")
    _write(
        gold_src / "features_15m" / "BTCUSDT" / "2025" / "07" / "feat.jsonl.gz",
        b"gold-feat",
    )
    _write(progress_path, b'{"status": "A2_COMPLETE", "gold_feature_row_count": 192}')

    key = _make_default_key((raw_root,))
    cache_base = tmp_path / "cache"
    entry = populate_a2_cache(
        cache_base=cache_base,
        key=key,
        source_run_id="strategy_ladder_workflow-fake-roundtrip",
        source_silver_root=silver_src,
        source_gold_root=gold_src,
        source_progress_report_path=progress_path,
        counters_snapshot={"rows_processed": 57_219_705, "files_processed": 166},
        gold_feature_row_count=192,
        silver_entry_count=2,
    )
    assert entry.input_hash == compute_input_hash(key)
    assert entry.source_run_id == "strategy_ladder_workflow-fake-roundtrip"
    assert entry.gold_feature_row_count == 192
    assert entry.silver_entry_count == 2
    assert entry.counters_snapshot["rows_processed"] == 57_219_705
    assert entry.key.feature_names == key.feature_names
    assert entry.key.schema_version == A2_CACHE_KEY_SCHEMA_VERSION
    assert entry.schema_version == A2_CACHE_ENTRY_SCHEMA_VERSION

    # Lookup returns a structurally-equivalent entry
    found = lookup_a2_cache(cache_base, entry.input_hash)
    assert found is not None
    assert found.input_hash == entry.input_hash
    assert found.gold_feature_row_count == 192

    # Restore into a fresh empty target tree
    target_silver = tmp_path / "fresh_run" / "phase_a2" / "silver"
    target_gold = tmp_path / "fresh_run" / "phase_a2" / "gold"
    target_progress = tmp_path / "fresh_run" / "phase_a2" / A2_CACHE_PROGRESS_REPORT_FILENAME
    restore_a2_from_cache(
        entry=found,
        cache_base=cache_base,
        target_silver_root=target_silver,
        target_gold_root=target_gold,
        target_progress_report_path=target_progress,
    )
    restored_silver_files = sorted(p.name for p in target_silver.rglob("*.jsonl.gz"))
    restored_gold_files = sorted(p.name for p in target_gold.rglob("*.jsonl.gz"))
    assert restored_silver_files == ["2025-07-01.jsonl.gz", "2025-07-02.jsonl.gz"]
    assert restored_gold_files == ["feat.jsonl.gz"]
    assert target_progress.is_file()
    assert b"A2_COMPLETE" in target_progress.read_bytes()


def test_lookup_rejects_entry_with_mismatched_schema_version(
    tmp_path: Path,
) -> None:
    raw_root = tmp_path / "raw"
    _make_raw_layout(raw_root)
    key = _make_default_key((raw_root,))
    input_hash = compute_input_hash(key)
    cache_base = tmp_path / "cache"
    cache_root = cache_root_for_hash(cache_base, input_hash)
    (cache_root / A2_CACHE_SILVER_SUBDIR).mkdir(parents=True, exist_ok=True)
    (cache_root / A2_CACHE_GOLD_SUBDIR).mkdir(parents=True, exist_ok=True)
    bad_meta = {
        "schema_version": "v53.a2_cache_entry.v0_legacy",
        "input_hash": input_hash,
        "cache_root": str(cache_root),
        "source_run_id": "any",
        "created_at": "2026-05-28T00:00:00Z",
        "silver_relpath": A2_CACHE_SILVER_SUBDIR,
        "gold_relpath": A2_CACHE_GOLD_SUBDIR,
        "progress_report_relpath": A2_CACHE_PROGRESS_REPORT_FILENAME,
        "gold_feature_row_count": 0,
        "silver_entry_count": 0,
        "counters_snapshot": {},
        "key": json.loads(key.model_dump_json()),
    }
    (cache_root / A2_CACHE_METADATA_FILENAME).write_text(
        json.dumps(bad_meta), encoding="utf-8"
    )
    assert lookup_a2_cache(cache_base, input_hash) is None


def test_lookup_rejects_entry_with_mismatched_input_hash(
    tmp_path: Path,
) -> None:
    raw_root = tmp_path / "raw"
    _make_raw_layout(raw_root)
    key = _make_default_key((raw_root,))
    input_hash = compute_input_hash(key)
    cache_base = tmp_path / "cache"
    cache_root = cache_root_for_hash(cache_base, input_hash)
    (cache_root / A2_CACHE_SILVER_SUBDIR).mkdir(parents=True, exist_ok=True)
    (cache_root / A2_CACHE_GOLD_SUBDIR).mkdir(parents=True, exist_ok=True)
    bad_meta = {
        "schema_version": A2_CACHE_ENTRY_SCHEMA_VERSION,
        "input_hash": "ff" * 32,  # not equal to actual input_hash
        "cache_root": str(cache_root),
        "source_run_id": "any",
        "created_at": "2026-05-28T00:00:00Z",
        "silver_relpath": A2_CACHE_SILVER_SUBDIR,
        "gold_relpath": A2_CACHE_GOLD_SUBDIR,
        "progress_report_relpath": A2_CACHE_PROGRESS_REPORT_FILENAME,
        "gold_feature_row_count": 0,
        "silver_entry_count": 0,
        "counters_snapshot": {},
        "key": json.loads(key.model_dump_json()),
    }
    (cache_root / A2_CACHE_METADATA_FILENAME).write_text(
        json.dumps(bad_meta), encoding="utf-8"
    )
    assert lookup_a2_cache(cache_base, input_hash) is None


def test_populate_is_idempotent(tmp_path: Path) -> None:
    raw_root = tmp_path / "raw"
    _make_raw_layout(raw_root)
    silver_src = tmp_path / "run1" / "silver"
    gold_src = tmp_path / "run1" / "gold"
    _write(silver_src / "BTCUSDT.jsonl.gz", b"silver-content")
    _write(gold_src / "BTCUSDT" / "feat.jsonl.gz", b"gold-content")
    key = _make_default_key((raw_root,))
    cache_base = tmp_path / "cache"
    entry_a = populate_a2_cache(
        cache_base=cache_base,
        key=key,
        source_run_id="run1",
        source_silver_root=silver_src,
        source_gold_root=gold_src,
        source_progress_report_path=None,
    )
    entry_b = populate_a2_cache(
        cache_base=cache_base,
        key=key,
        source_run_id="run2",
        source_silver_root=silver_src,
        source_gold_root=gold_src,
        source_progress_report_path=None,
    )
    assert entry_a.input_hash == entry_b.input_hash
    # The second populate must keep the original entry (no overwrite of the
    # source_run_id, no destructive rebuild).
    assert entry_b.source_run_id == entry_a.source_run_id == "run1"


def test_populate_rebuilds_when_metadata_is_corrupted(tmp_path: Path) -> None:
    raw_root = tmp_path / "raw"
    _make_raw_layout(raw_root)
    silver_src = tmp_path / "run" / "silver"
    gold_src = tmp_path / "run" / "gold"
    _write(silver_src / "BTCUSDT.jsonl.gz", b"silver-content")
    _write(gold_src / "BTCUSDT" / "feat.jsonl.gz", b"gold-content")
    key = _make_default_key((raw_root,))
    input_hash = compute_input_hash(key)
    cache_base = tmp_path / "cache"
    target_root = cache_root_for_hash(cache_base, input_hash)
    target_root.mkdir(parents=True, exist_ok=True)
    # No metadata file — simulating a corrupted cache slot
    entry = populate_a2_cache(
        cache_base=cache_base,
        key=key,
        source_run_id="run-rebuild",
        source_silver_root=silver_src,
        source_gold_root=gold_src,
        source_progress_report_path=None,
    )
    assert entry.source_run_id == "run-rebuild"
    assert (target_root / A2_CACHE_METADATA_FILENAME).is_file()


def test_read_prod_safety_snapshot_defaults_when_missing(tmp_path: Path) -> None:
    status, safe, blockers = read_prod_safety_snapshot(None)
    assert status == "PROD_SAFETY_NOT_PROVEN"
    assert safe is False
    assert blockers == ()
    # Empty dir
    status, safe, blockers = read_prod_safety_snapshot(tmp_path / "empty")
    assert status == "PROD_SAFETY_NOT_PROVEN"
    assert safe is False
    assert blockers == ()


def test_read_prod_safety_snapshot_parses_real_report(tmp_path: Path) -> None:
    report_dir = tmp_path / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / PROD_SAFETY_REPORT_FILENAME).write_text(
        json.dumps(
            {
                "prod_safety_status": "RESEARCH_ONLY_NOT_PROD_SAFE",
                "prod_safe": False,
                "blocker_codes": [
                    "RAW_SOURCE_TYPE_INFERRED",
                    "CURRENT_METADATA_PROXY",
                    "SINGLE_PAIR_RESEARCH_ONLY",
                ],
            }
        ),
        encoding="utf-8",
    )
    status, safe, blockers = read_prod_safety_snapshot(report_dir)
    assert status == "RESEARCH_ONLY_NOT_PROD_SAFE"
    assert safe is False
    assert blockers == (
        "RAW_SOURCE_TYPE_INFERRED",
        "CURRENT_METADATA_PROXY",
        "SINGLE_PAIR_RESEARCH_ONLY",
    )


def test_read_anti_leakage_snapshot_defaults_when_missing(tmp_path: Path) -> None:
    status, blockers = read_anti_leakage_snapshot(None)
    assert status == "ANTI_LEAKAGE_NOT_PROVEN"
    assert blockers == ()


def test_read_anti_leakage_snapshot_parses_real_report(tmp_path: Path) -> None:
    report_dir = tmp_path / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / ANTI_LEAKAGE_REPORT_FILENAME).write_text(
        json.dumps(
            {
                "status": "DATA_SCIENCE_READY_FOR_RESEARCH",
                "blocker_codes": [],
            }
        ),
        encoding="utf-8",
    )
    status, blockers = read_anti_leakage_snapshot(report_dir)
    assert status == "DATA_SCIENCE_READY_FOR_RESEARCH"
    assert blockers == ()


def test_populate_carries_prod_safety_when_report_present(tmp_path: Path) -> None:
    raw_root = tmp_path / "raw"
    _make_raw_layout(raw_root)
    silver_src = tmp_path / "run" / "silver"
    gold_src = tmp_path / "run" / "gold"
    _write(silver_src / "BTCUSDT.jsonl.gz", b"silver-content")
    _write(gold_src / "BTCUSDT" / "feat.jsonl.gz", b"gold-content")
    report_dir = tmp_path / "run" / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / PROD_SAFETY_REPORT_FILENAME).write_text(
        json.dumps(
            {
                "prod_safety_status": "RESEARCH_ONLY_NOT_PROD_SAFE",
                "prod_safe": False,
                "blocker_codes": [
                    "RAW_SOURCE_TYPE_INFERRED",
                    "CURRENT_METADATA_PROXY",
                    "SINGLE_PAIR_RESEARCH_ONLY",
                ],
            }
        ),
        encoding="utf-8",
    )
    (report_dir / ANTI_LEAKAGE_REPORT_FILENAME).write_text(
        json.dumps(
            {"status": "DATA_SCIENCE_READY_FOR_RESEARCH", "blocker_codes": []}
        ),
        encoding="utf-8",
    )
    key = _make_default_key((raw_root,))
    cache_base = tmp_path / "cache"
    entry = populate_a2_cache(
        cache_base=cache_base,
        key=key,
        source_run_id="run-with-reports",
        source_silver_root=silver_src,
        source_gold_root=gold_src,
        source_report_dir=report_dir,
    )
    assert entry.prod_safety_status == "RESEARCH_ONLY_NOT_PROD_SAFE"
    assert entry.prod_safe is False
    assert entry.prod_safety_blocker_codes == (
        "RAW_SOURCE_TYPE_INFERRED",
        "CURRENT_METADATA_PROXY",
        "SINGLE_PAIR_RESEARCH_ONLY",
    )
    assert entry.anti_leakage_status == "DATA_SCIENCE_READY_FOR_RESEARCH"
    assert entry.anti_leakage_blocker_codes == ()


def test_populate_defaults_to_not_proven_without_reports(tmp_path: Path) -> None:
    raw_root = tmp_path / "raw"
    _make_raw_layout(raw_root)
    silver_src = tmp_path / "run" / "silver"
    gold_src = tmp_path / "run" / "gold"
    _write(silver_src / "BTCUSDT.jsonl.gz", b"silver-content")
    _write(gold_src / "BTCUSDT" / "feat.jsonl.gz", b"gold-content")
    key = _make_default_key((raw_root,))
    cache_base = tmp_path / "cache"
    entry = populate_a2_cache(
        cache_base=cache_base,
        key=key,
        source_run_id="run-no-reports",
        source_silver_root=silver_src,
        source_gold_root=gold_src,
    )
    assert entry.prod_safety_status == "PROD_SAFETY_NOT_PROVEN"
    assert entry.prod_safe is False
    assert entry.prod_safety_blocker_codes == ()
    assert entry.anti_leakage_status == "ANTI_LEAKAGE_NOT_PROVEN"


def test_restore_raises_when_silver_subdir_missing(tmp_path: Path) -> None:
    raw_root = tmp_path / "raw"
    _make_raw_layout(raw_root)
    silver_src = tmp_path / "run" / "silver"
    gold_src = tmp_path / "run" / "gold"
    _write(silver_src / "BTCUSDT.jsonl.gz", b"silver-content")
    _write(gold_src / "BTCUSDT" / "feat.jsonl.gz", b"gold-content")
    key = _make_default_key((raw_root,))
    cache_base = tmp_path / "cache"
    entry = populate_a2_cache(
        cache_base=cache_base,
        key=key,
        source_run_id="run-restore",
        source_silver_root=silver_src,
        source_gold_root=gold_src,
        source_progress_report_path=None,
    )
    # Sabotage the cached silver dir
    import shutil as _shutil

    cache_root = cache_root_for_hash(cache_base, entry.input_hash)
    _shutil.rmtree(cache_root / A2_CACHE_SILVER_SUBDIR)
    with pytest.raises(FileNotFoundError):
        restore_a2_from_cache(
            entry=entry,
            cache_base=cache_base,
            target_silver_root=tmp_path / "out_silver",
            target_gold_root=tmp_path / "out_gold",
        )
