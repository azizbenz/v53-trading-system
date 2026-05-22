"""Canonical raw -> bronze scanning for bounded Bybit historical roots."""

from __future__ import annotations

import csv
from datetime import UTC, date, datetime
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
import zipfile

from interface_contracts.atomic_io import atomic_write_json, atomic_write_text
from local_replay_runtime.raw_data_processing_contracts import (
    BronzeMarketIndexManifest,
    RawMarketFileManifest,
    finalize_hashed_model,
)
from local_replay_runtime.strategy_ladder_raw_sources import normalize_raw_root_inputs


_PAIR_TF_DATE_PATTERN = re.compile(
    r"(?P<symbol>[A-Z0-9]+)_(?P<timeframe>[A-Za-z0-9]+)_(?P<date>\d{4}-\d{2}-\d{2})"
)
_PAIR_DATE_PATTERN = re.compile(r"(?P<symbol>[A-Z0-9]+)_(?P<date>\d{4}-\d{2}-\d{2})")
_DATE_PAIR_PATTERN = re.compile(r"(?P<date>\d{4}-\d{2}-\d{2})_(?P<symbol>[A-Z0-9]+)")
_DATE_PATTERN = re.compile(r"(?P<date>\d{4}-\d{2}-\d{2})")
_EXPECTED_SOURCE_TYPES = (
    "trades",
    "orderbook_snapshot",
    "orderbook_delta",
    "klines",
    "metadata",
)


def _normalize_symbol(value: str) -> str:
    normalized = str(value or "").strip().upper()
    return normalized if normalized else "UNKNOWN"


def _parse_iso_date(raw_value: str) -> date | None:
    value = str(raw_value or "").strip()
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _file_date(path: Path) -> date | None:
    logical_name = path.name
    for suffix in (".data.zip", ".jsonl.zip", ".json.zip", ".csv.gz", ".jsonl.gz", ".data.gz", ".json.gz"):
        if logical_name.lower().endswith(suffix):
            logical_name = logical_name[: -len(suffix)] + suffix.rsplit(".", 1)[0]
            break
    stem = Path(logical_name).stem
    for pattern in (_PAIR_TF_DATE_PATTERN, _PAIR_DATE_PATTERN, _DATE_PAIR_PATTERN):
        match = pattern.search(stem)
        if match:
            return _parse_iso_date(str(match.group("date")))
    generic_match = _DATE_PATTERN.search(stem)
    if generic_match:
        return _parse_iso_date(str(generic_match.group("date")))
    return None


def _path_symbol(path: Path) -> str:
    logical_name = path.name
    for pattern in (_PAIR_TF_DATE_PATTERN, _PAIR_DATE_PATTERN, _DATE_PAIR_PATTERN):
        match = pattern.search(logical_name)
        if match:
            return _normalize_symbol(str(match.group("symbol")))
    for part in reversed(path.parts):
        candidate = _normalize_symbol(part)
        if candidate.isalnum() and candidate.endswith("USDT"):
            return candidate
    return "UNKNOWN"


def _matches_scope(
    path: Path,
    *,
    symbol: str,
    start_date: date | None,
    end_date: date | None,
    requested_source_types: set[str],
) -> bool:
    candidate_symbol = _path_symbol(path)
    if symbol and candidate_symbol not in {"UNKNOWN", _normalize_symbol(symbol)}:
        return False
    candidate_date = _file_date(path)
    if start_date is not None and candidate_date is not None and candidate_date < start_date:
        return False
    if end_date is not None and candidate_date is not None and candidate_date > end_date:
        return False
    if not requested_source_types:
        return True
    lowered_parts = {part.lower() for part in path.parts}
    lowered_name = path.name.lower()
    if "trades" in requested_source_types and ({"trades", "trade", "aggtrades"} & lowered_parts or lowered_name.endswith(".csv.gz")):
        return True
    if "klines" in requested_source_types and {"klines", "kline", "ohlcv"} & lowered_parts:
        return True
    if {"orderbook", "orderbook_snapshot", "orderbook_delta"} & requested_source_types and (
        {"orderbook", "book", "depth"} & lowered_parts
        or "ob200" in lowered_name
        or lowered_name.endswith((".data", ".data.zip", ".jsonl", ".jsonl.gz", ".data.gz", ".json", ".json.zip"))
    ):
        return True
    if "metadata" in requested_source_types and {"metadata", "filters", "symbol_filters"} & lowered_parts:
        return True
    return False


def _iter_candidate_paths(root: Path) -> tuple[Path, ...]:
    resolved = root.expanduser().resolve()
    if resolved.is_file():
        return (resolved,)
    if not resolved.is_dir():
        return ()
    return tuple(
        sorted(
            path
            for path in resolved.rglob("*")
            if path.is_file()
            and (
                path.suffix.lower() in {".csv", ".json", ".jsonl", ".data", ".parquet"}
                or path.name.lower().endswith(
                    (".csv.gz", ".jsonl.gz", ".data.gz", ".json.gz", ".data.zip", ".jsonl.zip", ".json.zip")
                )
            )
        )
    )


def _file_format(path: Path) -> tuple[str, str]:
    lowered = path.name.lower()
    if lowered.endswith(".csv.gz"):
        return "csv", "gz"
    if lowered.endswith((".jsonl.gz", ".data.gz", ".json.gz")):
        return "jsonl_gz", "gz"
    if lowered.endswith((".data.zip", ".jsonl.zip", ".json.zip")):
        return "zip", "zip"
    if path.suffix.lower() == ".csv":
        return "csv", "none"
    if path.suffix.lower() in {".jsonl", ".data"}:
        return "jsonl", "none"
    if path.suffix.lower() == ".parquet":
        return "parquet", "none"
    if path.suffix.lower() == ".json":
        return "jsonl", "none"
    return path.suffix.lower().lstrip(".") or "unknown", "none"


def _sha256_path(path: Path) -> str | None:
    try:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            while True:
                chunk = handle.read(1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
        return digest.hexdigest()
    except OSError:
        return None


def _iter_text_lines(path: Path) -> tuple[str, ...]:
    lowered = path.name.lower()
    if lowered.endswith(".zip"):
        with zipfile.ZipFile(path) as archive:
            inner_names = [name for name in archive.namelist() if not name.endswith("/")]
            if not inner_names:
                return ()
            with archive.open(inner_names[0], "r") as handle:
                return tuple(line.decode("utf-8-sig", errors="replace") for line in handle)
    if lowered.endswith(".gz"):
        with gzip.open(path, "rt", encoding="utf-8-sig", newline="") as handle:
            return tuple(handle.readlines())
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return tuple(handle.readlines())


def _iter_csv_rows(path: Path) -> tuple[dict[str, str], ...]:
    lowered = path.name.lower()
    if lowered.endswith(".gz"):
        handle = gzip.open(path, "rt", encoding="utf-8-sig", newline="")
    else:
        handle = path.open("r", encoding="utf-8-sig", newline="")
    with handle:
        return tuple(dict(row) for row in csv.DictReader(handle))


def _iter_json_records(path: Path) -> tuple[dict[str, object], ...]:
    records: list[dict[str, object]] = []
    for line in _iter_text_lines(path):
        stripped = line.strip()
        if not stripped:
            continue
        payload = json.loads(stripped)
        if isinstance(payload, dict):
            records.append(payload)
    return tuple(records)


def _coerce_timestamp_ms(raw_value: object) -> int | None:
    try:
        value = int(str(raw_value).strip())
    except (TypeError, ValueError):
        return None
    if value < 10_000_000_000:
        value *= 1000
    return value if value >= 0 else None


def _manifest(
    *,
    symbol: str,
    source_type: str,
    path: Path,
    format_name: str,
    compression: str,
    start_timestamp_ms: int | None,
    end_timestamp_ms: int | None,
    row_count: int,
    sha256: str | None,
    status_override: str | None = None,
) -> RawMarketFileManifest:
    created_at = None
    if path.exists():
        created_at = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
    if status_override is not None:
        status = status_override
    elif row_count == 0:
        status = "RAW_FILE_EMPTY"
    elif sha256 is None:
        status = "RAW_FILE_HASH_NOT_PROVEN"
    elif start_timestamp_ms is None or end_timestamp_ms is None:
        status = "RAW_FILE_TIME_RANGE_NOT_PROVEN"
    else:
        status = "RAW_FILE_READY"
    return finalize_hashed_model(
        RawMarketFileManifest(
            symbol=_normalize_symbol(symbol),
            source_type=source_type,
            path=str(path.resolve()),
            format=format_name,
            start_timestamp_ms=start_timestamp_ms,
            end_timestamp_ms=end_timestamp_ms,
            row_count=row_count,
            file_size_bytes=path.stat().st_size if path.exists() else 0,
            sha256=sha256,
            compression=compression,
            created_at=created_at,
            source_status=status,
        )
    )


def _build_csv_manifests(path: Path) -> tuple[RawMarketFileManifest, ...]:
    rows = _iter_csv_rows(path)
    if not rows:
        format_name, compression = _file_format(path)
        return (
            _manifest(
                symbol=_path_symbol(path),
                source_type="trades" if path.name.lower().endswith(".csv.gz") else "klines",
                path=path,
                format_name=format_name,
                compression=compression,
                start_timestamp_ms=None,
                end_timestamp_ms=None,
                row_count=0,
                sha256=_sha256_path(path),
            ),
        )
    header = {key.strip().lower() for key in rows[0]}
    format_name, compression = _file_format(path)
    if {"id", "timestamp", "price", "volume"} <= header:
        timestamps = tuple(
            timestamp
            for row in rows
            if (timestamp := _coerce_timestamp_ms(row.get("timestamp"))) is not None
        )
        return (
            _manifest(
                symbol=_path_symbol(path),
                source_type="trades",
                path=path,
                format_name=format_name,
                compression=compression,
                start_timestamp_ms=min(timestamps) if timestamps else None,
                end_timestamp_ms=max(timestamps) if timestamps else None,
                row_count=len(rows),
                sha256=_sha256_path(path),
            ),
        )
    if {"starttime", "open", "high", "low", "close", "volume", "turnover"} <= header:
        timestamps = tuple(
            timestamp
            for row in rows
            if (timestamp := _coerce_timestamp_ms(row.get("startTime") or row.get("starttime"))) is not None
        )
        return (
            _manifest(
                symbol=_path_symbol(path),
                source_type="klines",
                path=path,
                format_name=format_name,
                compression=compression,
                start_timestamp_ms=min(timestamps) if timestamps else None,
                end_timestamp_ms=max(timestamps) if timestamps else None,
                row_count=len(rows),
                sha256=_sha256_path(path),
            ),
        )
    if {"symbol", "pair", "tick_size", "qty_step"} & header:
        rows_by_symbol: dict[str, int] = {}
        for row in rows:
            symbol = _normalize_symbol(str(row.get("symbol") or row.get("pair") or ""))
            rows_by_symbol[symbol] = rows_by_symbol.get(symbol, 0) + 1
        if not rows_by_symbol:
            rows_by_symbol = {_path_symbol(path): len(rows)}
        return tuple(
            _manifest(
                symbol=symbol,
                source_type="metadata",
                path=path,
                format_name=format_name,
                compression=compression,
                start_timestamp_ms=None,
                end_timestamp_ms=None,
                row_count=row_count,
                sha256=_sha256_path(path),
            )
            for symbol, row_count in sorted(rows_by_symbol.items())
        )
    return (
        _manifest(
            symbol=_path_symbol(path),
            source_type="metadata",
            path=path,
            format_name=format_name,
            compression=compression,
            start_timestamp_ms=None,
            end_timestamp_ms=None,
            row_count=len(rows),
            sha256=_sha256_path(path),
            status_override="RAW_FILE_SCHEMA_UNKNOWN",
        ),
    )


def _build_json_manifests(path: Path) -> tuple[RawMarketFileManifest, ...]:
    try:
        records = _iter_json_records(path)
    except (json.JSONDecodeError, OSError, UnicodeDecodeError, gzip.BadGzipFile, zipfile.BadZipFile):
        format_name, compression = _file_format(path)
        return (
            _manifest(
                symbol=_path_symbol(path),
                source_type="metadata",
                path=path,
                format_name=format_name,
                compression=compression,
                start_timestamp_ms=None,
                end_timestamp_ms=None,
                row_count=0,
                sha256=_sha256_path(path),
                status_override="RAW_FILE_SCHEMA_UNKNOWN",
            ),
        )
    format_name, compression = _file_format(path)
    if not records:
        return (
            _manifest(
                symbol=_path_symbol(path),
                source_type="metadata",
                path=path,
                format_name=format_name,
                compression=compression,
                start_timestamp_ms=None,
                end_timestamp_ms=None,
                row_count=0,
                sha256=_sha256_path(path),
            ),
        )
    snapshot_count = 0
    delta_count = 0
    timestamps: list[int] = []
    symbol = _path_symbol(path)
    for item in records:
        if isinstance(item.get("data"), dict):
            payload = item["data"]
            symbol = _normalize_symbol(str(payload.get("s") or symbol))
        timestamp = _coerce_timestamp_ms(
            item.get("ts")
            or item.get("timestamp_ms")
            or item.get("timestamp")
            or item.get("cts")
            or item.get("u")
        )
        if timestamp is not None:
            timestamps.append(timestamp)
        raw_type = str(item.get("type") or "").strip().lower()
        if raw_type == "snapshot":
            snapshot_count += 1
        elif raw_type == "delta":
            delta_count += 1
    manifests: list[RawMarketFileManifest] = []
    sha256 = _sha256_path(path)
    start_timestamp_ms = min(timestamps) if timestamps else None
    end_timestamp_ms = max(timestamps) if timestamps else None
    if snapshot_count or delta_count:
        if snapshot_count:
            manifests.append(
                _manifest(
                    symbol=symbol,
                    source_type="orderbook_snapshot",
                    path=path,
                    format_name=format_name,
                    compression=compression,
                    start_timestamp_ms=start_timestamp_ms,
                    end_timestamp_ms=end_timestamp_ms,
                    row_count=snapshot_count,
                    sha256=sha256,
                )
            )
        if delta_count:
            manifests.append(
                _manifest(
                    symbol=symbol,
                    source_type="orderbook_delta",
                    path=path,
                    format_name=format_name,
                    compression=compression,
                    start_timestamp_ms=start_timestamp_ms,
                    end_timestamp_ms=end_timestamp_ms,
                    row_count=delta_count,
                    sha256=sha256,
                )
            )
        return tuple(manifests)
    rows_by_symbol: dict[str, int] = {}
    for item in records:
        candidate_symbol = _normalize_symbol(
            str(item.get("symbol") or item.get("pair") or item.get("s") or "")
        )
        rows_by_symbol[candidate_symbol] = rows_by_symbol.get(candidate_symbol, 0) + 1
    # Patch D3 (2026-05-21) — détection metadata-like records pour ne pas
    # escalader vers SCHEMA_UNKNOWN. Cohérence avec _build_csv_manifests:322
    # qui détecte metadata par header (symbol/pair/tick_size/qty_step) et
    # accepte RAW_FILE_TIME_RANGE_NOT_PROVEN sans SCHEMA_UNKNOWN. Avant ce fix,
    # symbol_metadata.jsonl (généré par bybit_historical_metadata.py) était
    # systématiquement SCHEMA_UNKNOWN car les metadata n'ont pas de timestamps,
    # ce qui déclenchait BRONZE_INDEX_BLOCKED_BY_SCHEMA en aval.
    metadata_marker_keys = frozenset({
        "tick_size", "qty_step", "min_notional", "min_order_qty",
        "maker_fee_rate", "taker_fee_rate", "base_coin", "quote_coin",
    })
    has_metadata_markers = any(
        bool(metadata_marker_keys & {str(k).lower() for k in item.keys()})
        for item in records
        if isinstance(item, dict)
    )

    def _resolve_metadata_status_override() -> str | None:
        if start_timestamp_ms is not None:
            return None
        if has_metadata_markers:
            return None  # accept TIME_RANGE_NOT_PROVEN (default for metadata)
        return "RAW_FILE_SCHEMA_UNKNOWN"

    if rows_by_symbol:
        return tuple(
            _manifest(
                symbol=row_symbol,
                source_type="metadata",
                path=path,
                format_name=format_name,
                compression=compression,
                start_timestamp_ms=start_timestamp_ms,
                end_timestamp_ms=end_timestamp_ms,
                row_count=row_count,
                sha256=sha256,
                status_override=_resolve_metadata_status_override(),
            )
            for row_symbol, row_count in sorted(rows_by_symbol.items())
        )
    return (
        _manifest(
            symbol=symbol,
            source_type="metadata",
            path=path,
            format_name=format_name,
            compression=compression,
            start_timestamp_ms=start_timestamp_ms,
            end_timestamp_ms=end_timestamp_ms,
            row_count=len(records),
            sha256=sha256,
            status_override=_resolve_metadata_status_override(),
        ),
    )


def build_raw_market_file_manifest(path: Path) -> tuple[RawMarketFileManifest, ...]:
    """Build one or more logical manifests from one raw file path."""

    resolved = Path(path).expanduser().resolve()
    if not resolved.exists():
        format_name, compression = _file_format(resolved)
        return (
            _manifest(
                symbol=_path_symbol(resolved),
                source_type="metadata",
                path=resolved,
                format_name=format_name,
                compression=compression,
                start_timestamp_ms=None,
                end_timestamp_ms=None,
                row_count=0,
                sha256=None,
                status_override="RAW_FILE_MISSING",
            ),
        )
    lowered = resolved.name.lower()
    if resolved.suffix.lower() == ".csv" or lowered.endswith(".csv.gz"):
        return _build_csv_manifests(resolved)
    if resolved.suffix.lower() in {".json", ".jsonl", ".data"} or lowered.endswith(
        (".jsonl.gz", ".data.gz", ".json.gz", ".data.zip", ".jsonl.zip", ".json.zip")
    ):
        return _build_json_manifests(resolved)
    format_name, compression = _file_format(resolved)
    return (
        _manifest(
            symbol=_path_symbol(resolved),
            source_type="metadata",
            path=resolved,
            format_name=format_name,
            compression=compression,
            start_timestamp_ms=None,
            end_timestamp_ms=None,
            row_count=0,
            sha256=_sha256_path(resolved),
            status_override="RAW_FILE_SCHEMA_UNKNOWN",
        ),
    )


def scan_bybit_raw_root(
    *,
    raw_root: Path | None = None,
    raw_roots: tuple[Path, ...] = (),
    raw_roots_csv: str = "",
    symbol: str = "",
    start: str = "",
    end: str = "",
    source_types: tuple[str, ...] = (),
) -> tuple[RawMarketFileManifest, ...]:
    """Scan one bounded raw scope and emit typed raw manifests."""

    roots = normalize_raw_root_inputs(raw_root=raw_root, raw_roots=raw_roots, raw_roots_csv=raw_roots_csv)
    requested_source_types = {
        ("orderbook_snapshot" if item == "orderbook" else item.strip().lower())
        for item in source_types
        if item.strip()
    }
    if "orderbook_snapshot" in requested_source_types:
        requested_source_types.add("orderbook_delta")
    start_date = _parse_iso_date(start)
    end_date = _parse_iso_date(end)
    manifests: list[RawMarketFileManifest] = []
    seen: set[tuple[str, str]] = set()
    for root in roots:
        for candidate in _iter_candidate_paths(root):
            if not _matches_scope(
                candidate,
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                requested_source_types=requested_source_types,
            ):
                continue
            for manifest in build_raw_market_file_manifest(candidate):
                if symbol and manifest.symbol != _normalize_symbol(symbol):
                    continue
                if requested_source_types and manifest.source_type not in requested_source_types:
                    continue
                identity = (manifest.path.lower(), manifest.source_type)
                if identity in seen:
                    continue
                seen.add(identity)
                manifests.append(manifest)
    # Patch D4 (2026-05-21) — déduplication ZIP/extracted.
    # Avant ce fix, un orderbook ob200.data.zip ET son contenu extrait
    # ob200.data étaient tous deux indexés comme fichiers distincts (paths
    # différents) → duplicate_timestamp_count gonflé (4 sur run f9bb2bdc :
    # 2 jours × 2 source_types delta+snapshot). Dédup par signature contenu
    # (symbol, source_type, start_ts, end_ts, row_count). En cas de doublon,
    # on garde la version non-zip (format != "zip") pour faciliter le parsing
    # downstream qui n'a pas à décompresser à chaque fois.
    content_seen: dict[tuple[str, str, int | None, int | None, int], RawMarketFileManifest] = {}
    for manifest in manifests:
        key = (
            manifest.symbol,
            manifest.source_type,
            manifest.start_timestamp_ms,
            manifest.end_timestamp_ms,
            manifest.row_count,
        )
        existing = content_seen.get(key)
        if existing is None:
            content_seen[key] = manifest
            continue
        # Doublon détecté : choisir la version non-zip si possible
        existing_is_zip = (existing.format or "").lower() == "zip"
        new_is_zip = (manifest.format or "").lower() == "zip"
        if existing_is_zip and not new_is_zip:
            content_seen[key] = manifest
        # sinon (les deux non-zip, ou les deux zip, ou existing déjà non-zip),
        # on garde existing → silently skip ce manifest doublon
    deduplicated_manifests = tuple(content_seen.values())
    return tuple(sorted(deduplicated_manifests, key=lambda item: (item.symbol, item.source_type, item.path)))


# Patch F2-A (2026-05-21) — timeframe extractor + interval lookup.
# Avant ce fix, le gap detection groupait toutes les klines (1m, 5m, 10m, 15m)
# sous source_type="klines" et triait par start_ts, ce qui mélangeait les
# timeframes et masquait les vrais gaps. Sur run f9bb2bdc, le "gap de 60s"
# rapporté était un artefact : transition normale entre dernière barre 1m
# d'un jour (23:59:00) et première barre 15m du jour suivant (00:00:00).
# Le VRAI gap (7h21min de truncation Bybit 1000-cap sur fichiers 1m) était
# masqué. Le fix groupe les klines par (source_type, timeframe) et utilise
# l'interval timeframe pour calculer le vrai end_ms = last_start + interval.
_KLINE_TIMEFRAME_INTERVAL_MS: dict[str, int] = {
    "1m": 60_000,
    "3m": 3 * 60_000,
    "5m": 5 * 60_000,
    "10m": 10 * 60_000,
    "15m": 15 * 60_000,
    "30m": 30 * 60_000,
    "1h": 60 * 60_000,
    "60m": 60 * 60_000,
    "4h": 4 * 60 * 60_000,
    "1d": 24 * 60 * 60_000,
}
_KLINE_PATH_TIMEFRAME_PATTERN = re.compile(
    r"[/\\\\]klines[/\\\\][A-Z0-9]+[/\\\\](?P<tf>\d+[mhd]?)[/\\\\]"
    r"|BTCUSDT_(?P<tf2>\d+[mhd]?)_\d{4}-\d{2}-\d{2}\.csv",
    re.IGNORECASE,
)


def _extract_kline_timeframe(path: str) -> str | None:
    """Extract kline timeframe label (e.g. '1m', '15m') from a raw kline path.

    Patch F2-A — supports two patterns:
    - Directory based: `L:/klines/BTCUSDT/1/2025/BTCUSDT_1_2025-07-23.csv` → "1m"
    - Filename based: `BTCUSDT_15_2025-07-24.csv` → "15m"

    Returns None if not parseable (caller falls back to generic source_type key).
    """
    if not path:
        return None
    match = _KLINE_PATH_TIMEFRAME_PATTERN.search(path)
    if match is None:
        return None
    raw = match.group("tf") or match.group("tf2")
    if not raw:
        return None
    raw = raw.lower()
    # Default suffix interpretation : digits-only → minutes (Bybit convention)
    if raw.isdigit():
        return f"{raw}m"
    return raw


def _gap_group_key(manifest: RawMarketFileManifest) -> str:
    """Patch F2-A — gap detection key per timeframe for klines, per source_type others.

    Klines (1m, 5m, 10m, 15m) sont indexés sous le même source_type="klines"
    par le raw manifest. Pour détecter les vrais gaps temporels, il faut les
    grouper par timeframe (sinon transitions naturelles entre barre 1m et 15m
    sont confondues avec des gaps).
    """
    if manifest.source_type == "klines":
        timeframe = _extract_kline_timeframe(manifest.path)
        if timeframe is not None:
            return f"klines:{timeframe}"
    return manifest.source_type


def _effective_end_timestamp_ms(manifest: RawMarketFileManifest) -> int:
    """Patch F2-A — compute true end_ms for kline manifests.

    OHLCV bars use start_ms as their timestamp ; the "end" of a kline file is
    actually `last_bar_start_ms + interval_ms` (la barre couvre
    [start, start+interval[). Sans ce calcul, comparer end_ms d'un fichier 1m
    (23:59:00) avec start_ms du fichier suivant (00:00:00) donne 60s de "gap"
    alors qu'il n'y a pas de trou réel (la barre 23:59 finit naturellement à
    24:00 = 00:00 next day).
    """
    base_end = manifest.end_timestamp_ms or 0
    if manifest.source_type != "klines":
        return base_end
    timeframe = _extract_kline_timeframe(manifest.path)
    if timeframe is None:
        return base_end
    interval = _KLINE_TIMEFRAME_INTERVAL_MS.get(timeframe)
    if interval is None:
        return base_end
    return base_end + interval


def build_bronze_market_index(
    manifests: tuple[RawMarketFileManifest, ...],
    *,
    symbol: str,
    exchange: str = "bybit",
    market_type: str = "spot",
) -> BronzeMarketIndexManifest:
    """Aggregate raw manifests into one bronze coverage summary."""

    relevant = tuple(item for item in manifests if item.symbol == _normalize_symbol(symbol))
    if not relevant:
        return finalize_hashed_model(
            BronzeMarketIndexManifest(
                exchange=exchange,
                market_type=market_type,
                symbol=_normalize_symbol(symbol),
                source_types_missing=_EXPECTED_SOURCE_TYPES,
                index_status="BRONZE_INDEX_BLOCKED_BY_MISSING_RAW",
            )
        )
    source_types_present = tuple(sorted({item.source_type for item in relevant}))
    source_types_missing = tuple(
        source_type for source_type in _EXPECTED_SOURCE_TYPES if source_type not in source_types_present
    )
    proven_starts = tuple(item.start_timestamp_ms for item in relevant if item.start_timestamp_ms is not None)
    proven_ends = tuple(item.end_timestamp_ms for item in relevant if item.end_timestamp_ms is not None)
    # Patch F2-A — sort + group by (gap_group_key, start_ts) au lieu de
    # (source_type, start_ts). Les klines sont sub-groupées par timeframe pour
    # éviter de mélanger 1m/5m/10m/15m dans la même séquence de gap detection.
    ordered_by_group = sorted(
        (item for item in relevant if item.start_timestamp_ms is not None and item.end_timestamp_ms is not None),
        key=lambda item: (
            _gap_group_key(item),
            item.start_timestamp_ms or 0,
            item.end_timestamp_ms or 0,
            item.path,
        ),
    )
    gap_count = 0
    largest_gap_ms = 0
    duplicate_timestamp_count = 0
    out_of_order_count = 0
    previous_by_group: dict[str, RawMarketFileManifest] = {}
    for manifest in ordered_by_group:
        group_key = _gap_group_key(manifest)
        previous = previous_by_group.get(group_key)
        if previous is not None:
            previous_effective_end = _effective_end_timestamp_ms(previous)
            current_start = manifest.start_timestamp_ms or 0
            if current_start < (previous.start_timestamp_ms or 0):
                out_of_order_count += 1
            if (
                manifest.start_timestamp_ms == previous.start_timestamp_ms
                and manifest.end_timestamp_ms == previous.end_timestamp_ms
            ):
                duplicate_timestamp_count += 1
            if current_start > previous_effective_end:
                gap = current_start - previous_effective_end
                if gap > 0:
                    gap_count += 1
                    largest_gap_ms = max(largest_gap_ms, gap)
        previous_by_group[group_key] = manifest
    status = "BRONZE_INDEX_READY"
    if any(item.source_status == "RAW_FILE_SCHEMA_UNKNOWN" for item in relevant):
        status = "BRONZE_INDEX_BLOCKED_BY_SCHEMA"
    elif not source_types_present:
        status = "BRONZE_INDEX_BLOCKED_BY_MISSING_RAW"
    elif source_types_missing:
        status = "BRONZE_INDEX_PARTIAL"
    return finalize_hashed_model(
        BronzeMarketIndexManifest(
            exchange=exchange,
            market_type=market_type,
            symbol=_normalize_symbol(symbol),
            coverage_start_ms=min(proven_starts) if proven_starts else None,
            coverage_end_ms=max(proven_ends) if proven_ends else None,
            source_files_count=len({item.path for item in relevant}),
            source_types_present=source_types_present,
            source_types_missing=source_types_missing,
            gap_count=gap_count,
            largest_gap_ms=largest_gap_ms,
            duplicate_timestamp_count=duplicate_timestamp_count,
            out_of_order_count=out_of_order_count,
            index_status=status,
            source_file_refs=tuple(sorted({item.path for item in relevant})),
        )
    )


def write_raw_market_file_manifest_bundle(
    path: Path,
    manifests: tuple[RawMarketFileManifest, ...],
) -> None:
    """Write the raw file manifest bundle as deterministic JSONL.GZ."""

    path.parent.mkdir(parents=True, exist_ok=True)
    payload = "\n".join(
        json.dumps(item.model_dump(mode="json"), sort_keys=True, ensure_ascii=True)
        for item in manifests
    )
    buffer = io.BytesIO()
    with gzip.GzipFile(fileobj=buffer, mode="wb", mtime=0) as gz:
        gz.write(payload.encode("utf-8"))
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_bytes(buffer.getvalue())
    tmp_path.replace(path)


def write_bronze_market_index(path: Path, manifest: BronzeMarketIndexManifest) -> None:
    """Write the bronze market index JSON payload."""

    atomic_write_json(path, manifest.model_dump(mode="json"), indent=2)


def write_bronze_market_index_markdown(path: Path, manifest: BronzeMarketIndexManifest) -> None:
    """Write a concise operator-facing bronze summary."""

    lines = [
        "# Bronze Market Index",
        "",
        f"- symbol: `{manifest.symbol}`",
        f"- status: `{manifest.index_status}`",
        f"- coverage_start_ms: `{manifest.coverage_start_ms}`",
        f"- coverage_end_ms: `{manifest.coverage_end_ms}`",
        f"- source_files_count: `{manifest.source_files_count}`",
        f"- source_types_present: `{', '.join(manifest.source_types_present) or 'none'}`",
        f"- source_types_missing: `{', '.join(manifest.source_types_missing) or 'none'}`",
        f"- gap_count: `{manifest.gap_count}`",
        f"- largest_gap_ms: `{manifest.largest_gap_ms}`",
        f"- duplicate_timestamp_count: `{manifest.duplicate_timestamp_count}`",
        f"- out_of_order_count: `{manifest.out_of_order_count}`",
    ]
    atomic_write_text(path, "\n".join(lines) + "\n")


__all__ = [
    "build_bronze_market_index",
    "build_raw_market_file_manifest",
    "scan_bybit_raw_root",
    "write_bronze_market_index",
    "write_bronze_market_index_markdown",
    "write_raw_market_file_manifest_bundle",
]
