"""Content-addressable cache for the canonical A2 Data Factory output.

A2 (silver + gold + microstructure features) is the slowest stage of a V5.3
backtest workflow (~2h30 for 54 days BTCUSDT 15m with the full microstructure
feature set). Without caching, every iteration on the downstream B1/B2/B_ML
stages forces a complete A2 rebuild even though the A2 inputs are unchanged.

This module implements a deterministic, content-addressable cache:

  hash = sha256(serialize(canonical_inputs))
  cache_root = L:/cache/a2/{hash}/

When the runner enters A2 it computes the hash from the typed
`StrategyLadderDataFactoryRequest` plus a cheap fingerprint of the raw source
files (sorted (path, size, mtime_ms)). On a cache hit the silver + gold
directories are restored from the cache (copy by default, optional symlink),
the progress report is rewritten with `A2_CACHE_HIT` status and the runner
exits the A2 stage in seconds. On a cache miss the runner runs A2 normally
and, at the end, populates the cache from the produced run directory so the
next iteration with the same inputs becomes O(1).

The cache is decision-neutral: no engine, threshold, gate, label, proxy or
trading semantic is affected. The schema_version field is bumped whenever the
hash inputs or the cache layout change, so an upgrade automatically invalidates
older entries.
"""

from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
import os
import shutil
from pathlib import Path

from pydantic import BaseModel, Field

from interface_contracts.atomic_io import atomic_write_json


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


A2_CACHE_KEY_SCHEMA_VERSION = "v53.a2_cache_key.v1"
# Schema version bumped 2026-05-28 — entry now carries the source run's
# prod_safety_status + blocker_codes so a cache hit cannot silently launder
# a research-only A2 output into something that *looks* prod-safe to a
# downstream consumer. The cache propagates the truth as-is.
A2_CACHE_ENTRY_SCHEMA_VERSION = "v53.a2_cache_entry.v2"
# Patch P6 (2026-05-29) — canonical audit-conformant name first, legacy second.
# The producer writes both files (back-compat). Reader tries canonical, then
# falls back to legacy if a pre-P6 run is in the cache.
PROD_SAFETY_CONTRACT_FILENAME = "a2_gold_prod_safety_contract.json"
PROD_SAFETY_REPORT_FILENAME = "data_factory_prod_safety_report.json"  # legacy alias
ANTI_LEAKAGE_REPORT_FILENAME = "anti_leakage_precheck_report.json"
# Patch 2026-05-28 — the cached `StrategyLadderDataFactoryResult` is
# serialized to JSON and stored alongside the silver/gold tree so the cache
# hit path can return a real typed result without re-running A2.
A2_CACHE_RESULT_BLOB_FILENAME = "_a2_cache_result_blob.json"
# Patch 2026-05-28 — the cache also captures the per-run reports
# directory snapshot (manifest, data_quality, prod_safety, anti_leakage,
# microstructure_performance, etc.) so a hit restores ALL the downstream
# inputs B1/B2 expect from a normal A2 completion.
A2_CACHE_REPORTS_SUBDIR = "reports"
A2_CACHE_HIT_STATUS = "A2_CACHE_HIT"
A2_CACHE_POPULATED_STATUS = "A2_CACHE_POPULATED"
A2_CACHE_MISS_STATUS = "A2_CACHE_MISS"
A2_CACHE_INVALID_STATUS = "A2_CACHE_INVALID"
A2_CACHE_METADATA_FILENAME = "a2_cache_entry.json"
A2_CACHE_SILVER_SUBDIR = "silver"
A2_CACHE_GOLD_SUBDIR = "gold"
A2_CACHE_PROGRESS_REPORT_FILENAME = "a2_gold_progress_report.json"


class RawSourceFingerprintEntry(BaseModel, frozen=True):
    """One file in the cheap raw-source fingerprint."""

    path: str = Field(..., min_length=1)
    size_bytes: int = Field(..., ge=0)
    mtime_ms: int = Field(..., ge=0)


class A2CacheKey(BaseModel, frozen=True):
    """The canonical, deterministic inputs that decide the A2 output.

    Two A2 runs with identical `A2CacheKey` produce byte-identical silver and
    gold artefacts. Non-deterministic fields of `StrategyLadderDataFactoryRequest`
    (run_id, output paths, resume/dry_run flags, storage budget, etc.) are
    intentionally absent from this key.
    """

    schema_version: str = A2_CACHE_KEY_SCHEMA_VERSION
    raw_roots_fingerprint: str = Field(..., min_length=1)
    historical_metadata_fingerprint: str = Field(default="ABSENT", min_length=1)
    pairs: tuple[str, ...]
    engines: tuple[str, ...]
    timeframes: tuple[str, ...]
    feature_names: tuple[str, ...]
    start: str
    end: str
    data_types: tuple[str, ...]
    compression: str
    storage_format: str
    max_gold_feature_rows: int = Field(default=0, ge=0)
    use_measured_economic_provenance: bool = False


class A2CacheEntry(BaseModel, frozen=True):
    """Metadata about one populated cache entry.

    Stored as `a2_cache_entry.json` at the cache_root so that a future cache
    lookup can verify the entry without re-reading the entire silver/gold
    tree.

    Patch 2026-05-28 — the entry now carries an honest snapshot of the
    source run's `data_factory_prod_safety_report.json` verdict
    (`prod_safety_status`, `prod_safe`, `blocker_codes`) and the
    `anti_leakage_precheck_report.json` status. A cache hit re-emits these
    values verbatim; promotion to `prod_safe = True` requires re-running A2
    with the upstream blockers actually resolved (e.g. raw venue verified,
    historical metadata fetched for the actual window). The cache neither
    invents nor hides safety claims.
    """

    schema_version: str = A2_CACHE_ENTRY_SCHEMA_VERSION
    input_hash: str = Field(..., min_length=1)
    cache_root: str = Field(..., min_length=1)
    source_run_id: str = Field(..., min_length=1)
    created_at: str = Field(..., min_length=1)
    silver_relpath: str = A2_CACHE_SILVER_SUBDIR
    gold_relpath: str = A2_CACHE_GOLD_SUBDIR
    progress_report_relpath: str = A2_CACHE_PROGRESS_REPORT_FILENAME
    gold_feature_row_count: int = Field(default=0, ge=0)
    silver_entry_count: int = Field(default=0, ge=0)
    counters_snapshot: dict[str, int] = Field(default_factory=dict)
    key: A2CacheKey
    prod_safety_status: str = "PROD_SAFETY_NOT_PROVEN"
    prod_safe: bool = False
    prod_safety_blocker_codes: tuple[str, ...] = ()
    anti_leakage_status: str = "ANTI_LEAKAGE_NOT_PROVEN"
    anti_leakage_blocker_codes: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# Fingerprint helpers
# ---------------------------------------------------------------------------


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def fingerprint_raw_paths(
    raw_roots: tuple[Path, ...],
    *,
    extensions: tuple[str, ...] = (
        ".zip",
        ".csv",
        ".gz",
        ".jsonl",
        ".jsonl.gz",
        ".parquet",
    ),
) -> tuple[str, tuple[RawSourceFingerprintEntry, ...]]:
    """Compute a cheap content-fingerprint of all raw input files.

    Returns a `(fingerprint_hex, entries)` pair so the caller can persist the
    entries alongside the cache metadata for audit. Files are sorted by their
    resolved absolute path so the fingerprint is deterministic across machines
    with the same data layout.

    The fingerprint is intentionally cheap: it does NOT read file contents,
    only `(path, size, mtime)`. This is enough to detect raw data overwrites
    while keeping the lookup near instant. Bit-exact content addressing can be
    layered on top later if the data lake guarantees immutable raw files.
    """

    entries: list[RawSourceFingerprintEntry] = []
    seen: set[str] = set()
    for raw_root in raw_roots:
        if raw_root is None:
            continue
        root = Path(raw_root)
        if not root.exists():
            continue
        if root.is_file():
            iterables: tuple[Path, ...] = (root,)
        else:
            iterables = tuple(p for p in sorted(root.rglob("*")) if p.is_file())
        for path in iterables:
            if extensions and path.suffix.lower() not in extensions:
                lowered_name = path.name.lower()
                if not any(lowered_name.endswith(ext) for ext in extensions):
                    continue
            resolved = str(path.resolve())
            if resolved in seen:
                continue
            seen.add(resolved)
            try:
                stat = path.stat()
            except OSError:
                continue
            entries.append(
                RawSourceFingerprintEntry(
                    path=resolved,
                    size_bytes=int(stat.st_size),
                    mtime_ms=int(stat.st_mtime * 1000),
                )
            )
    entries.sort(key=lambda e: e.path)
    payload = json.dumps(
        [entry.model_dump(mode="json") for entry in entries],
        sort_keys=True,
        separators=(",", ":"),
    )
    return _hash_text(payload), tuple(entries)


def fingerprint_historical_metadata(path: Path | None) -> str:
    """Cheap fingerprint of the historical metadata cache root if present."""

    if path is None:
        return "ABSENT"
    candidate = Path(path)
    if not candidate.exists():
        return "MISSING"
    fingerprint, _ = fingerprint_raw_paths(
        (candidate,),
        extensions=(".json", ".yml", ".yaml"),
    )
    return fingerprint


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_a2_cache_key(
    *,
    raw_roots: tuple[Path, ...],
    historical_metadata_root: Path | None,
    pairs: tuple[str, ...],
    engines: tuple[str, ...],
    timeframes: tuple[str, ...],
    feature_names: tuple[str, ...],
    start: str,
    end: str,
    data_types: tuple[str, ...],
    compression: str,
    storage_format: str,
    max_gold_feature_rows: int = 0,
    use_measured_economic_provenance: bool = False,
) -> A2CacheKey:
    """Build a canonical `A2CacheKey` from the typed inputs of an A2 request."""

    raw_fingerprint, _ = fingerprint_raw_paths(raw_roots)
    return A2CacheKey(
        raw_roots_fingerprint=raw_fingerprint,
        historical_metadata_fingerprint=fingerprint_historical_metadata(
            historical_metadata_root
        ),
        pairs=tuple(p.upper() for p in pairs),
        engines=tuple(engines),
        timeframes=tuple(timeframes),
        feature_names=tuple(feature_names),
        start=str(start or ""),
        end=str(end or ""),
        data_types=tuple(sorted({t.lower() for t in data_types})),
        compression=str(compression or ""),
        storage_format=str(storage_format or ""),
        max_gold_feature_rows=int(max_gold_feature_rows),
        use_measured_economic_provenance=bool(use_measured_economic_provenance),
    )


def compute_input_hash(key: A2CacheKey) -> str:
    """Stable SHA256 of the canonical JSON of an `A2CacheKey`."""

    payload = key.model_dump_json()
    return _hash_text(payload)


def cache_root_for_hash(cache_base: Path, input_hash: str) -> Path:
    """Return `cache_base / input_hash` (creates nothing)."""

    return Path(cache_base) / input_hash


def lookup_a2_cache(
    cache_base: Path,
    input_hash: str,
) -> A2CacheEntry | None:
    """Return the cached entry for `input_hash` if it exists and validates.

    Validation is intentionally lightweight: existence of the metadata JSON,
    schema_version match, and presence of the silver+gold subdirs.
    """

    candidate = cache_root_for_hash(cache_base, input_hash)
    if not candidate.is_dir():
        return None
    metadata_path = candidate / A2_CACHE_METADATA_FILENAME
    if not metadata_path.is_file():
        return None
    try:
        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(payload, dict):
        return None
    if str(payload.get("schema_version")) != A2_CACHE_ENTRY_SCHEMA_VERSION:
        return None
    if str(payload.get("input_hash")) != input_hash:
        return None
    silver_path = candidate / str(
        payload.get("silver_relpath") or A2_CACHE_SILVER_SUBDIR
    )
    gold_path = candidate / str(payload.get("gold_relpath") or A2_CACHE_GOLD_SUBDIR)
    if not silver_path.is_dir() or not gold_path.is_dir():
        return None
    try:
        return A2CacheEntry.model_validate(payload)
    except Exception:  # noqa: BLE001 - defensive
        return None


def read_prod_safety_snapshot(
    source_report_dir: Path | None,
) -> tuple[str, bool, tuple[str, ...]]:
    """Read prod-safety verdict from the source run's report directory.

    Returns `(prod_safety_status, prod_safe, blocker_codes)`. Defaults to
    `("PROD_SAFETY_NOT_PROVEN", False, ())` if the report is missing or
    malformed, so a cache populated without the report is honestly tagged as
    `not proven` rather than silently `prod_safe`.
    """

    if source_report_dir is None:
        return "PROD_SAFETY_NOT_PROVEN", False, ()
    # Patch P6 (2026-05-29) — try canonical name first, fall back to legacy
    # for pre-P6 cached runs.
    candidate = Path(source_report_dir) / PROD_SAFETY_CONTRACT_FILENAME
    if not candidate.is_file():
        candidate = Path(source_report_dir) / PROD_SAFETY_REPORT_FILENAME
    if not candidate.is_file():
        return "PROD_SAFETY_NOT_PROVEN", False, ()
    try:
        payload = json.loads(candidate.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return "PROD_SAFETY_NOT_PROVEN", False, ()
    if not isinstance(payload, dict):
        return "PROD_SAFETY_NOT_PROVEN", False, ()
    status = str(payload.get("prod_safety_status") or "PROD_SAFETY_NOT_PROVEN")
    safe = bool(payload.get("prod_safe", False))
    raw_blockers = payload.get("blocker_codes") or ()
    blocker_codes = tuple(
        str(code) for code in raw_blockers if isinstance(code, (str, int))
    )
    return status, safe, blocker_codes


def read_anti_leakage_snapshot(
    source_report_dir: Path | None,
) -> tuple[str, tuple[str, ...]]:
    """Read anti-leakage verdict from the source run's report directory.

    Returns `(status, blocker_codes)`. Defaults to
    `("ANTI_LEAKAGE_NOT_PROVEN", ())` if the report is missing.
    """

    if source_report_dir is None:
        return "ANTI_LEAKAGE_NOT_PROVEN", ()
    candidate = Path(source_report_dir) / ANTI_LEAKAGE_REPORT_FILENAME
    if not candidate.is_file():
        return "ANTI_LEAKAGE_NOT_PROVEN", ()
    try:
        payload = json.loads(candidate.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return "ANTI_LEAKAGE_NOT_PROVEN", ()
    if not isinstance(payload, dict):
        return "ANTI_LEAKAGE_NOT_PROVEN", ()
    status = str(payload.get("status") or "ANTI_LEAKAGE_NOT_PROVEN")
    raw_blockers = payload.get("blocker_codes") or ()
    blocker_codes = tuple(
        str(code) for code in raw_blockers if isinstance(code, (str, int))
    )
    return status, blocker_codes


def populate_a2_cache(
    *,
    cache_base: Path,
    key: A2CacheKey,
    source_run_id: str,
    source_silver_root: Path,
    source_gold_root: Path,
    source_progress_report_path: Path | None = None,
    counters_snapshot: dict[str, int] | None = None,
    gold_feature_row_count: int = 0,
    silver_entry_count: int = 0,
    source_report_dir: Path | None = None,
    result_blob_json: str | None = None,
) -> A2CacheEntry:
    """Copy the A2 output of a completed run into the cache.

    Implementation note: we copy (not move) so the source run directory stays
    intact for the operator. The cache always contains a fully self-contained
    snapshot. Atomic publication is achieved by writing into a `<hash>.tmp`
    sibling and renaming at the end.

    Patch 2026-05-28 — if `source_report_dir` is provided we read the
    canonical `data_factory_prod_safety_report.json` and
    `anti_leakage_precheck_report.json` so the cache entry truthfully carries
    the source run's safety verdict. If the report dir is None the cache
    entry is tagged `PROD_SAFETY_NOT_PROVEN` / `ANTI_LEAKAGE_NOT_PROVEN`
    rather than silently `prod_safe`.
    """

    prod_safety_status, prod_safe, prod_safety_blockers = read_prod_safety_snapshot(
        source_report_dir
    )
    anti_leakage_status, anti_leakage_blockers = read_anti_leakage_snapshot(
        source_report_dir
    )
    input_hash = compute_input_hash(key)
    target_root = cache_root_for_hash(cache_base, input_hash)
    if target_root.exists():
        return _load_existing_or_overwrite(
            cache_base=cache_base,
            input_hash=input_hash,
            target_root=target_root,
            key=key,
            source_run_id=source_run_id,
            source_silver_root=source_silver_root,
            source_gold_root=source_gold_root,
            source_progress_report_path=source_progress_report_path,
            counters_snapshot=counters_snapshot,
            gold_feature_row_count=gold_feature_row_count,
            silver_entry_count=silver_entry_count,
            prod_safety_status=prod_safety_status,
            prod_safe=prod_safe,
            prod_safety_blockers=prod_safety_blockers,
            anti_leakage_status=anti_leakage_status,
            anti_leakage_blockers=anti_leakage_blockers,
            source_report_dir=source_report_dir,
            result_blob_json=result_blob_json,
        )
    return _publish_new_cache_entry(
        cache_base=cache_base,
        input_hash=input_hash,
        target_root=target_root,
        key=key,
        source_run_id=source_run_id,
        source_silver_root=source_silver_root,
        source_gold_root=source_gold_root,
        source_progress_report_path=source_progress_report_path,
        counters_snapshot=counters_snapshot,
        gold_feature_row_count=gold_feature_row_count,
        silver_entry_count=silver_entry_count,
        prod_safety_status=prod_safety_status,
        prod_safe=prod_safe,
        prod_safety_blockers=prod_safety_blockers,
        anti_leakage_status=anti_leakage_status,
        anti_leakage_blockers=anti_leakage_blockers,
        source_report_dir=source_report_dir,
        result_blob_json=result_blob_json,
    )


def restore_a2_from_cache(
    *,
    entry: A2CacheEntry,
    cache_base: Path,
    target_silver_root: Path,
    target_gold_root: Path,
    target_progress_report_path: Path | None = None,
    target_report_dir: Path | None = None,
) -> None:
    """Materialise a cached A2 output into the current run's silver/gold dirs.

    The target dirs are created if missing. If they already contain data, the
    cache contents are merged on top (existing files are overwritten so the
    final state is byte-identical to what A2 would have produced).

    Patch 2026-05-28 — when `target_report_dir` is provided, the cached
    reports snapshot (data_factory_manifest.json, data_quality_report.json,
    anti_leakage_precheck_report.json, etc.) is restored too so the
    downstream B1/B2 stages find every artifact A2 normally writes.
    """

    source_root = cache_root_for_hash(cache_base, entry.input_hash)
    src_silver = source_root / entry.silver_relpath
    src_gold = source_root / entry.gold_relpath
    if not src_silver.is_dir() or not src_gold.is_dir():
        raise FileNotFoundError(
            f"A2 cache entry {entry.input_hash!r} is missing silver or gold subdir"
        )
    Path(target_silver_root).mkdir(parents=True, exist_ok=True)
    Path(target_gold_root).mkdir(parents=True, exist_ok=True)
    _copy_tree(src_silver, Path(target_silver_root))
    _copy_tree(src_gold, Path(target_gold_root))
    if target_progress_report_path is not None:
        src_progress = source_root / entry.progress_report_relpath
        if src_progress.is_file():
            target = Path(target_progress_report_path)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_progress, target)
    if target_report_dir is not None:
        src_reports = source_root / A2_CACHE_REPORTS_SUBDIR
        if src_reports.is_dir():
            Path(target_report_dir).mkdir(parents=True, exist_ok=True)
            for report_file in src_reports.iterdir():
                if report_file.is_file():
                    shutil.copy2(report_file, Path(target_report_dir) / report_file.name)


def read_cached_result_blob(
    cache_base: Path,
    entry: A2CacheEntry,
) -> str | None:
    """Return the cached `StrategyLadderDataFactoryResult.model_dump_json()`
    blob if it was stored at populate time, else None.
    """

    source_root = cache_root_for_hash(cache_base, entry.input_hash)
    candidate = source_root / A2_CACHE_RESULT_BLOB_FILENAME
    if not candidate.is_file():
        return None
    try:
        return candidate.read_text(encoding="utf-8")
    except OSError:
        return None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _publish_new_cache_entry(
    *,
    cache_base: Path,
    input_hash: str,
    target_root: Path,
    key: A2CacheKey,
    source_run_id: str,
    source_silver_root: Path,
    source_gold_root: Path,
    source_progress_report_path: Path | None,
    counters_snapshot: dict[str, int] | None,
    gold_feature_row_count: int,
    silver_entry_count: int,
    prod_safety_status: str = "PROD_SAFETY_NOT_PROVEN",
    prod_safe: bool = False,
    prod_safety_blockers: tuple[str, ...] = (),
    anti_leakage_status: str = "ANTI_LEAKAGE_NOT_PROVEN",
    anti_leakage_blockers: tuple[str, ...] = (),
    source_report_dir: Path | None = None,
    result_blob_json: str | None = None,
) -> A2CacheEntry:
    tmp_root = Path(str(target_root) + ".tmp")
    if tmp_root.exists():
        shutil.rmtree(tmp_root, ignore_errors=True)
    tmp_root.mkdir(parents=True, exist_ok=False)
    silver_dst = tmp_root / A2_CACHE_SILVER_SUBDIR
    gold_dst = tmp_root / A2_CACHE_GOLD_SUBDIR
    silver_dst.mkdir(parents=True, exist_ok=True)
    gold_dst.mkdir(parents=True, exist_ok=True)
    if Path(source_silver_root).is_dir():
        _copy_tree(Path(source_silver_root), silver_dst)
    if Path(source_gold_root).is_dir():
        _copy_tree(Path(source_gold_root), gold_dst)
    if source_progress_report_path is not None and Path(
        source_progress_report_path
    ).is_file():
        shutil.copy2(
            Path(source_progress_report_path),
            tmp_root / A2_CACHE_PROGRESS_REPORT_FILENAME,
        )
    # Patch 2026-05-28 — snapshot the full reports directory (excluding
    # silver/gold/the progress file we already copied) so B1/B2 find every
    # JSON they expect when the cache hits.
    if source_report_dir is not None and Path(source_report_dir).is_dir():
        reports_dst = tmp_root / A2_CACHE_REPORTS_SUBDIR
        reports_dst.mkdir(parents=True, exist_ok=True)
        for entry_path in Path(source_report_dir).iterdir():
            if not entry_path.is_file():
                continue
            if entry_path.name in (A2_CACHE_PROGRESS_REPORT_FILENAME,):
                continue
            shutil.copy2(entry_path, reports_dst / entry_path.name)
    if result_blob_json:
        (tmp_root / A2_CACHE_RESULT_BLOB_FILENAME).write_text(
            result_blob_json,
            encoding="utf-8",
        )
    entry = A2CacheEntry(
        input_hash=input_hash,
        cache_root=str(target_root.resolve()),
        source_run_id=source_run_id,
        created_at=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        counters_snapshot=dict(counters_snapshot or {}),
        gold_feature_row_count=int(gold_feature_row_count),
        silver_entry_count=int(silver_entry_count),
        key=key,
        prod_safety_status=prod_safety_status,
        prod_safe=prod_safe,
        prod_safety_blocker_codes=prod_safety_blockers,
        anti_leakage_status=anti_leakage_status,
        anti_leakage_blocker_codes=anti_leakage_blockers,
    )
    atomic_write_json(tmp_root / A2_CACHE_METADATA_FILENAME, entry.model_dump(mode="json"))
    Path(cache_base).mkdir(parents=True, exist_ok=True)
    os.replace(tmp_root, target_root)
    # Re-read the entry so the returned path is the final one
    return A2CacheEntry.model_validate(
        json.loads((target_root / A2_CACHE_METADATA_FILENAME).read_text(encoding="utf-8"))
    )


def _load_existing_or_overwrite(
    *,
    cache_base: Path,
    input_hash: str,
    target_root: Path,
    key: A2CacheKey,
    source_run_id: str,
    source_silver_root: Path,
    source_gold_root: Path,
    source_progress_report_path: Path | None,
    counters_snapshot: dict[str, int] | None,
    gold_feature_row_count: int,
    silver_entry_count: int,
    prod_safety_status: str = "PROD_SAFETY_NOT_PROVEN",
    prod_safe: bool = False,
    prod_safety_blockers: tuple[str, ...] = (),
    anti_leakage_status: str = "ANTI_LEAKAGE_NOT_PROVEN",
    anti_leakage_blockers: tuple[str, ...] = (),
    source_report_dir: Path | None = None,
    result_blob_json: str | None = None,
) -> A2CacheEntry:
    existing = lookup_a2_cache(cache_base, input_hash)
    if existing is not None:
        return existing
    # The directory exists but the metadata is missing or stale → atomic rebuild.
    shutil.rmtree(target_root, ignore_errors=True)
    return _publish_new_cache_entry(
        cache_base=cache_base,
        input_hash=input_hash,
        target_root=target_root,
        key=key,
        source_run_id=source_run_id,
        source_silver_root=source_silver_root,
        source_gold_root=source_gold_root,
        source_progress_report_path=source_progress_report_path,
        counters_snapshot=counters_snapshot,
        gold_feature_row_count=gold_feature_row_count,
        silver_entry_count=silver_entry_count,
        prod_safety_status=prod_safety_status,
        prod_safe=prod_safe,
        prod_safety_blockers=prod_safety_blockers,
        anti_leakage_status=anti_leakage_status,
        anti_leakage_blockers=anti_leakage_blockers,
        source_report_dir=source_report_dir,
        result_blob_json=result_blob_json,
    )


def _copy_tree(src: Path, dst: Path) -> None:
    """Copy `src` into `dst`, preserving structure and overwriting on conflict."""

    Path(dst).mkdir(parents=True, exist_ok=True)
    for entry in src.rglob("*"):
        rel = entry.relative_to(src)
        target = Path(dst) / rel
        if entry.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        elif entry.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(entry, target)


__all__ = [
    "A2_CACHE_ENTRY_SCHEMA_VERSION",
    "A2_CACHE_GOLD_SUBDIR",
    "A2_CACHE_HIT_STATUS",
    "A2_CACHE_INVALID_STATUS",
    "A2_CACHE_KEY_SCHEMA_VERSION",
    "A2_CACHE_METADATA_FILENAME",
    "A2_CACHE_MISS_STATUS",
    "A2_CACHE_POPULATED_STATUS",
    "A2_CACHE_PROGRESS_REPORT_FILENAME",
    "A2_CACHE_REPORTS_SUBDIR",
    "A2_CACHE_RESULT_BLOB_FILENAME",
    "A2_CACHE_SILVER_SUBDIR",
    "ANTI_LEAKAGE_REPORT_FILENAME",
    "PROD_SAFETY_CONTRACT_FILENAME",
    "PROD_SAFETY_REPORT_FILENAME",
    "A2CacheEntry",
    "A2CacheKey",
    "RawSourceFingerprintEntry",
    "build_a2_cache_key",
    "cache_root_for_hash",
    "compute_input_hash",
    "fingerprint_historical_metadata",
    "fingerprint_raw_paths",
    "lookup_a2_cache",
    "populate_a2_cache",
    "read_anti_leakage_snapshot",
    "read_cached_result_blob",
    "read_prod_safety_snapshot",
    "restore_a2_from_cache",
]
