"""Arrow-backed raw-window extraction core (Parquet + in-RAM vectorized slice).

PERF (2026-06-01) — replaces the JSONL row-based + per-row ``json.loads`` +
per-candidate re-read pattern with the institutional recipe: load the silver
source ONCE into an Apache Arrow table (RAM), then slice each candidate window
with a vectorized predicate. Measured on real BTCUSDT trades (941k rows, 12
windows): JSONL re-parse 77.85s vs Arrow in-RAM 0.72s = **107x**, parquet.zstd
3.73 MB vs jsonl.gz 7.49 MB = **2x smaller**, rows **bit-identical**.

Doctrine-safe: this changes only HOW ticks are stored/loaded (columnar), never
WHICH ticks — the full trades + L2 book microstructure is preserved bit-for-bit
(the engines' forward-looking order-flow signal is untouched).

Phase 0 (fondation): this module is self-contained + parity-tested. Wiring it
into the extractor / cache / readers is Phase 1-2 of the migration spec
(2026-06-01_PARQUET_ARROW_WINDOW_MIGRATION_SPEC.md).
"""

from __future__ import annotations

import gzip
import hashlib
import json
import os
import uuid
from functools import lru_cache
from pathlib import Path

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.ipc as ipc
import pyarrow.parquet as pq

DEFAULT_TS_COLUMN = "timestamp_ms"
# Internal positional-index column appended to every loaded table. It lets the
# extractor map each sliced row back to its VERBATIM source line (byte-exact
# output) without caching raw text in RAM. It is dropped before any Parquet
# persistence and popped by the dict-returning readers — it is never part of
# the silver schema and never reaches downstream consumers.
ROW_INDEX_COLUMN = "__row_idx__"


def _parse_jsonl_records(path: Path) -> list[tuple[str, dict]]:
    """Parse a jsonl(.gz) source into ``(raw_line, row_dict)`` per kept row.

    Single source of truth for line parsing + skip rules (blank line, malformed
    JSON, non-dict row). Both the typed Arrow table and the extractor's
    verbatim-line writer derive from this, so their row order and ``__row_idx__``
    positions align exactly."""
    name = path.name.lower()
    opener = gzip.open if name.endswith(".gz") else open
    records: list[tuple[str, dict]] = []
    with opener(path, "rt", encoding="utf-8-sig") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            try:
                row = json.loads(stripped)
            except ValueError:
                continue
            if isinstance(row, dict):
                records.append((stripped, row))
    return records


def _with_row_index(table: pa.Table) -> pa.Table:
    """Append the internal positional-index column (idempotent)."""
    if ROW_INDEX_COLUMN in table.column_names:
        return table
    idx = pa.array(range(table.num_rows), type=pa.int64())
    return table.append_column(ROW_INDEX_COLUMN, idx)


def _normalize_union_keys(rows: list[dict]) -> list[dict]:
    """Return ``rows`` re-keyed to the UNION of all keys (first-seen order).

    ``pa.Table.from_pylist`` infers its schema from the FIRST row only, which
    would silently DROP any field present on later rows but absent from row 0
    (e.g. an optional ``trade_id``) — a microstructure-payload loss. Normalising
    to the union before building the table keeps every field."""
    key_order: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row.keys():
            if key not in seen:
                seen.add(key)
                key_order.append(key)
    return [{key: row.get(key) for key in key_order} for row in rows]


def _read_rows_to_table(path: Path) -> pa.Table:
    """Read a silver source (jsonl, jsonl.gz, or parquet) into an Arrow table.

    JSON rows are parsed into a columnar table whose schema is the UNION of every
    row's keys (see ``_normalize_union_keys``). Parquet is read directly (already
    columnar)."""
    name = path.name.lower()
    if name.endswith(".parquet"):
        return _with_row_index(pq.read_table(path))
    rows = [row for _, row in _parse_jsonl_records(path)]
    if not rows:
        return pa.table(
            {
                DEFAULT_TS_COLUMN: pa.array([], pa.int64()),
                ROW_INDEX_COLUMN: pa.array([], pa.int64()),
            }
        )
    return _with_row_index(pa.Table.from_pylist(_normalize_union_keys(rows)))


def write_rows_parquet(
    rows: list[dict],
    target_path: Path,
    *,
    compression: str = "zstd",
) -> int:
    """Write in-memory ``rows`` (list of dicts) as a Parquet file (union-key
    schema, columnar, compressed). Returns the row count.

    Used for the silver dual-write Parquet sidecar (migration spec Phase 2): the
    canonical jsonl(.gz) file is written by the data factory as before, and this
    emits the equivalent ``.parquet`` next to it. No internal ``__row_idx__``
    column is added — this is a persisted artifact."""
    target_path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        table = pa.table({DEFAULT_TS_COLUMN: pa.array([], pa.int64())})
    else:
        table = pa.Table.from_pylist(_normalize_union_keys(rows))
    pq.write_table(table, target_path, compression=compression)
    return table.num_rows


_IPC_CACHE_ENV = "V53_IPC_CACHE_DIR"


def _ipc_cache_dir() -> str | None:
    value = os.environ.get(_IPC_CACHE_ENV)
    return value or None


def _ipc_sidecar_path(source_path_str: str, cache_dir: str) -> Path:
    """Deterministic IPC sidecar path (every worker derives the same path)."""
    digest = hashlib.sha1(source_path_str.encode("utf-8")).hexdigest()[:20]
    stem = Path(source_path_str).name.replace(".", "_")
    return Path(cache_dir) / f"{stem}.{digest}.arrow"


def _read_ipc_table(ipc_path: Path, *, source_path: Path) -> pa.Table | None:
    """Memory-map a fresh IPC sidecar (zero-copy, shared OS page cache). Returns
    None when the sidecar is missing, stale, or unreadable (-> caller re-parses)."""
    try:
        if not ipc_path.is_file():
            return None
        if (
            source_path.is_file()
            and ipc_path.stat().st_mtime < source_path.stat().st_mtime
        ):
            return None  # source changed after the sidecar was written
        source = pa.memory_map(str(ipc_path), "r")
        return ipc.open_file(source).read_all()
    except (OSError, pa.ArrowInvalid, pa.ArrowIOError):
        return None


def _atomic_write_ipc(table: pa.Table, ipc_path: Path) -> None:
    """Write an Arrow IPC sidecar atomically (unique temp + os.replace) so a
    concurrent worker never observes a partially written file. Best-effort: a
    failure just means workers re-parse (slower, still correct)."""
    tmp: Path | None = None
    try:
        ipc_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = ipc_path.with_name(f"{ipc_path.name}.{uuid.uuid4().hex}.tmp")
        with pa.OSFile(str(tmp), "wb") as sink:
            with ipc.new_file(sink, table.schema) as writer:
                writer.write_table(table)
        os.replace(tmp, ipc_path)  # atomic on the same volume
    except OSError:
        if tmp is not None:
            try:
                tmp.unlink()
            except OSError:
                pass


@lru_cache(maxsize=4)
def load_silver_table(path_str: str) -> pa.Table:
    """Load + parse a silver source ONCE per path into an Arrow table (LRU 4).

    The ~250 candidate windows in a partition reuse this single parse instead of
    re-reading the file per candidate. Tests that rewrite a path must call
    ``load_silver_table.cache_clear()``.

    Phase 3 cross-process sharing: when ``V53_IPC_CACHE_DIR`` is set, a
    memory-mappable Arrow IPC sidecar is reused across processes — the first
    reader parses the jsonl(.gz)/parquet and writes the sidecar atomically;
    every other worker mmaps it (zero-copy, shared OS page cache) instead of
    re-parsing the source. The returned table is identical either way."""
    cache_dir = _ipc_cache_dir()
    if cache_dir and not path_str.lower().endswith(".arrow"):
        source_path = Path(path_str)
        sidecar = _ipc_sidecar_path(path_str, cache_dir)
        cached = _read_ipc_table(sidecar, source_path=source_path)
        if cached is not None:
            return cached
        table = _read_rows_to_table(source_path)
        _atomic_write_ipc(table, sidecar)
        return table
    return _read_rows_to_table(Path(path_str))


def read_raw_source_lines(path_str: str) -> list[str] | None:
    """Return the verbatim source lines (kept rows, in table order) for a jsonl
    source, or ``None`` for parquet (no original text available).

    Aligned by position with ``load_silver_table``'s ``__row_idx__`` so the
    extractor can emit byte-exact slices. Intentionally NOT cached: caching raw
    text would reintroduce the RAM bloat the Parquet migration set out to remove
    (the typed table stays cached; the raw text is read transiently per run)."""
    path = Path(path_str)
    if path.name.lower().endswith(".parquet"):
        return None
    return [raw for raw, _ in _parse_jsonl_records(path)]


def slice_window(
    table: pa.Table,
    window_start_ms: int,
    window_end_ms: int,
    *,
    ts_column: str = DEFAULT_TS_COLUMN,
) -> pa.Table:
    """Return rows with ``window_start_ms <= ts <= window_end_ms`` (inclusive
    both ends, identical to the previous per-row linear filter) via a vectorized
    Arrow predicate. Preserves source row order."""
    if table.num_rows == 0 or ts_column not in table.column_names:
        return table.slice(0, 0)
    col = table.column(ts_column)
    mask = pc.and_(
        pc.greater_equal(col, window_start_ms),
        pc.less_equal(col, window_end_ms),
    )
    return table.filter(mask)


def slice_window_with_anchor(
    table: pa.Table,
    window_start_ms: int,
    window_end_ms: int,
    *,
    ts_column: str = DEFAULT_TS_COLUMN,
) -> pa.Table:
    """Like ``slice_window`` but also prepends the last row strictly before
    ``window_start_ms`` when one exists.

    This preserves the anchor-row semantics of the JSONL streaming extractor:
    the last snapshot/delta row before the window start is prepended so that
    book-reconstruction can anchor from the correct state.  The anchor row is
    only included when it has ``ts < window_start_ms`` (never equal — that row
    is already included in the window slice itself)."""
    sliced = slice_window(table, window_start_ms, window_end_ms, ts_column=ts_column)
    if table.num_rows == 0 or ts_column not in table.column_names:
        return sliced
    ts_col = table.column(ts_column)
    # Match the streaming writer: nearest timestamp strictly before the window,
    # but no duplicate anchor when the first in-window row sits on the boundary.
    anchor_table = table.filter(pc.less(ts_col, window_start_ms))
    if anchor_table.num_rows == 0:
        return sliced
    if sliced.num_rows > 0:
        first_window_ts = sliced.column(ts_column)[0].as_py()
        if first_window_ts == window_start_ms:
            return sliced
    anchor_ts_col = anchor_table.column(ts_column)
    anchor_ts = pc.max(anchor_ts_col).as_py()
    nearest_anchor_rows = anchor_table.filter(pc.equal(anchor_ts_col, anchor_ts))
    anchor_row = nearest_anchor_rows.slice(nearest_anchor_rows.num_rows - 1, 1)
    return pa.concat_tables([anchor_row, sliced])


def resolve_slice_path(directory: Path, stem: str) -> Path:
    """Resolve a raw-window slice path: prefer .jsonl.gz (the compressed canonical
    slice format), then plain .jsonl, then .parquet. This makes callers
    format-agnostic so the slice writer can compress without touching readers."""
    for suffix in (".jsonl.gz", ".jsonl", ".parquet"):
        candidate = directory / f"{stem}{suffix}"
        if candidate.is_file():
            return candidate
    return directory / f"{stem}.jsonl.gz"


def write_window_parquet(
    table: pa.Table,
    target_path: Path,
    *,
    compression: str = "zstd",
) -> int:
    """Write a window slice as Parquet (columnar, compressed). Returns rows.

    The internal ``__row_idx__`` column is stripped so it never reaches a
    persisted artifact."""
    target_path.parent.mkdir(parents=True, exist_ok=True)
    persisted = table
    if ROW_INDEX_COLUMN in table.column_names:
        persisted = table.select(
            [name for name in table.column_names if name != ROW_INDEX_COLUMN]
        )
    pq.write_table(persisted, target_path, compression=compression)
    return persisted.num_rows


__all__ = [
    "load_silver_table",
    "read_raw_source_lines",
    "slice_window",
    "slice_window_with_anchor",
    "resolve_slice_path",
    "write_window_parquet",
    "write_rows_parquet",
    "DEFAULT_TS_COLUMN",
    "ROW_INDEX_COLUMN",
]
