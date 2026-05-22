"""Recollect incomplete raw Bybit kline files with strict V5.3 validation."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from io import StringIO
import json
from pathlib import Path
import re
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from interface_contracts.atomic_io import atomic_write_json, atomic_write_text


BYBIT_PUBLIC_KLINE_URL = "https://api.bybit.com/v5/market/kline"
BYBIT_KLINE_FETCH_MODE = "BYBIT_PUBLIC_KLINE_RECOLLECTION"
BYBIT_KLINE_READY = "BYBIT_KLINE_RECOLLECTION_READY"
BYBIT_KLINE_PARTIAL = "BYBIT_KLINE_RECOLLECTION_PARTIAL"
BYBIT_KLINE_FAILED = "BYBIT_KLINE_RECOLLECTION_FAILED"
BYBIT_KLINE_USER_AGENT = "v53-trading-system/bybit-kline-recollection"
_DAY_MS = 24 * 60 * 60 * 1000
_MAX_PAGE_SIZE = 1000
_CSV_HEADER = ("startTime", "open", "high", "low", "close", "volume", "turnover")
_DATE_PATTERN = re.compile(r"(?P<date>\d{4}-\d{2}-\d{2})")
_RESUME_SKIP_STATUSES = frozenset(
    {"REPAIRED", "DRY_RUN_READY", "SKIPPED_EXISTING_COMPLETE", "SKIPPED_RESUME_STATE"}
)
ProgressFn = Callable[[str], None]


@dataclass(frozen=True)
class BybitKlineTimeframeSpec:
    timeframe: str
    interval_ms: int
    expected_rows_per_day: int
    path_component: str
    year_partition_default: bool
    source_timeframe: str
    fetch_interval: str
    fetch_interval_ms: int
    aggregation_factor: int


_TIMEFRAME_SPECS = {
    "1m": BybitKlineTimeframeSpec(
        timeframe="1m",
        interval_ms=60_000,
        expected_rows_per_day=1440,
        path_component="1",
        year_partition_default=True,
        source_timeframe="1m",
        fetch_interval="1",
        fetch_interval_ms=60_000,
        aggregation_factor=1,
    ),
    "5m": BybitKlineTimeframeSpec(
        timeframe="5m",
        interval_ms=5 * 60_000,
        expected_rows_per_day=288,
        path_component="5",
        year_partition_default=False,
        source_timeframe="5m",
        fetch_interval="5",
        fetch_interval_ms=5 * 60_000,
        aggregation_factor=1,
    ),
    "10m": BybitKlineTimeframeSpec(
        timeframe="10m",
        interval_ms=10 * 60_000,
        expected_rows_per_day=144,
        path_component="10",
        year_partition_default=False,
        source_timeframe="1m",
        fetch_interval="1",
        fetch_interval_ms=60_000,
        aggregation_factor=10,
    ),
    "15m": BybitKlineTimeframeSpec(
        timeframe="15m",
        interval_ms=15 * 60_000,
        expected_rows_per_day=96,
        path_component="15",
        year_partition_default=False,
        source_timeframe="15m",
        fetch_interval="15",
        fetch_interval_ms=15 * 60_000,
        aggregation_factor=1,
    ),
}
_TIMEFRAME_ALIASES = {
    "1": "1m",
    "1m": "1m",
    "5": "5m",
    "5m": "5m",
    "10": "10m",
    "10m": "10m",
    "15": "15m",
    "15m": "15m",
}


class BybitKlineFetchError(RuntimeError):
    """Raised when the Bybit public kline fetch fails closed."""


def _normalize_symbol(value: object) -> str:
    return "".join(ch for ch in str(value or "").strip().upper() if ch.isalnum())


def normalize_timeframe(value: object) -> str:
    normalized = _TIMEFRAME_ALIASES.get(str(value or "").strip().lower())
    if normalized is None:
        raise ValueError(f"Unsupported timeframe: {value!r}")
    return normalized


def _utc_now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


def _parse_iso_date(value: str | date) -> date:
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value or "").strip()[:10])


def _iter_days(start_day: date, end_day: date) -> tuple[date, ...]:
    if end_day < start_day:
        raise ValueError("end_date must be greater than or equal to start_date")
    cursor = start_day
    days: list[date] = []
    while cursor <= end_day:
        days.append(cursor)
        cursor += timedelta(days=1)
    return tuple(days)


def _day_start_ms(day: date) -> int:
    return int(datetime(day.year, day.month, day.day, tzinfo=UTC).timestamp() * 1000)


def _expected_last_bucket_ms(day: date, spec: BybitKlineTimeframeSpec) -> int:
    return _day_start_ms(day) + _DAY_MS - spec.interval_ms


def _timestamp_to_iso(timestamp_ms: int | None) -> str | None:
    if timestamp_ms is None:
        return None
    return datetime.fromtimestamp(timestamp_ms / 1000, tz=UTC).isoformat()


def _coerce_timestamp_ms(value: object) -> int | None:
    try:
        return int(str(value or "").strip())
    except (TypeError, ValueError):
        return None


def _coerce_decimal(value: object) -> Decimal:
    try:
        return Decimal(str(value or "").strip() or "0")
    except InvalidOperation as exc:
        raise BybitKlineFetchError(f"Invalid decimal value in kline payload: {value!r}") from exc


def _decimal_to_str(value: Decimal) -> str:
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def _extract_date_from_name(name: str) -> date | None:
    match = _DATE_PATTERN.search(str(name or ""))
    if not match:
        return None
    return _parse_iso_date(match.group("date"))


def _canonicalize_row(raw_row: object) -> dict[str, object] | None:
    if isinstance(raw_row, (list, tuple)):
        if len(raw_row) < 7:
            return None
        timestamp_ms = _coerce_timestamp_ms(raw_row[0])
        if timestamp_ms is None:
            return None
        return {
            "startTime": timestamp_ms,
            "open": str(raw_row[1]),
            "high": str(raw_row[2]),
            "low": str(raw_row[3]),
            "close": str(raw_row[4]),
            "volume": str(raw_row[5]),
            "turnover": str(raw_row[6]),
        }
    if isinstance(raw_row, dict):
        timestamp_ms = _coerce_timestamp_ms(
            raw_row.get("startTime")
            or raw_row.get("start_time")
            or raw_row.get("timestamp")
        )
        if timestamp_ms is None:
            return None
        return {
            "startTime": timestamp_ms,
            "open": str(raw_row.get("open") or ""),
            "high": str(raw_row.get("high") or ""),
            "low": str(raw_row.get("low") or ""),
            "close": str(raw_row.get("close") or ""),
            "volume": str(raw_row.get("volume") or ""),
            "turnover": str(raw_row.get("turnover") or ""),
        }
    return None


def _parse_bybit_payload(payload: object) -> tuple[dict[str, object], ...]:
    if not isinstance(payload, dict):
        raise BybitKlineFetchError("Bybit payload is not a JSON object.")
    ret_code = payload.get("retCode")
    if str(ret_code) not in {"0", "None"} and ret_code != 0 and ret_code is not None:
        raise BybitKlineFetchError(
            f"Bybit rejected the kline request: retCode={ret_code} retMsg={payload.get('retMsg')}"
        )
    result = payload.get("result")
    if not isinstance(result, dict):
        raise BybitKlineFetchError("Bybit payload is missing result.")
    raw_rows = result.get("list")
    if not isinstance(raw_rows, list):
        raise BybitKlineFetchError("Bybit payload is missing result.list.")
    rows: list[dict[str, object]] = []
    for raw_row in raw_rows:
        row = _canonicalize_row(raw_row)
        if row is not None:
            rows.append(row)
    rows.sort(key=lambda item: int(item["startTime"]))
    return tuple(rows)


def _target_path(
    *,
    kline_root: Path,
    symbol: str,
    spec: BybitKlineTimeframeSpec,
    day: date,
) -> Path:
    filename = f"{symbol}_{spec.path_component}_{day.isoformat()}.csv"
    timeframe_root = kline_root / symbol / spec.path_component
    year_partition = timeframe_root / f"{day.year:04d}" / filename
    flat_layout = timeframe_root / filename
    if year_partition.exists():
        return year_partition.resolve()
    if flat_layout.exists():
        return flat_layout.resolve()
    if (timeframe_root / f"{day.year:04d}").is_dir():
        return year_partition.resolve()
    if timeframe_root.is_dir():
        try:
            if any(
                child.is_dir() and child.name.isdigit() and len(child.name) == 4
                for child in timeframe_root.iterdir()
            ):
                return year_partition.resolve()
        except OSError:
            pass
        return flat_layout.resolve()
    if spec.year_partition_default:
        return year_partition.resolve()
    return flat_layout.resolve()


def _read_csv_rows(path: Path) -> tuple[dict[str, object], ...]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows: list[dict[str, object]] = []
        for raw_row in reader:
            row = _canonicalize_row(raw_row)
            if row is not None:
                rows.append(row)
        rows.sort(key=lambda item: int(item["startTime"]))
        return tuple(rows)


def _validate_rows(
    rows: tuple[dict[str, object], ...],
    *,
    spec: BybitKlineTimeframeSpec,
    day: date,
) -> dict[str, object]:
    ordered_timestamps = [int(row["startTime"]) for row in rows]
    first_timestamp_ms = ordered_timestamps[0] if ordered_timestamps else None
    last_timestamp_ms = ordered_timestamps[-1] if ordered_timestamps else None
    expected_first_ms = _day_start_ms(day)
    expected_last_ms = _expected_last_bucket_ms(day, spec)
    expected_timestamps = tuple(
        range(expected_first_ms, expected_last_ms + spec.interval_ms, spec.interval_ms)
    )
    actual_set = set(ordered_timestamps)
    missing_timestamps = [timestamp for timestamp in expected_timestamps if timestamp not in actual_set]
    duplicates = len(ordered_timestamps) - len(actual_set)
    unexpected_deltas: list[int] = []
    out_of_order_count = 0
    for previous, current in zip(ordered_timestamps, ordered_timestamps[1:]):
        delta = current - previous
        if delta <= 0:
            out_of_order_count += 1
        if delta != spec.interval_ms:
            unexpected_deltas.append(delta)
    validation_errors: list[str] = []
    if len(rows) != spec.expected_rows_per_day:
        validation_errors.append(
            f"ROW_COUNT_MISMATCH expected={spec.expected_rows_per_day} got={len(rows)}"
        )
    if first_timestamp_ms != expected_first_ms:
        validation_errors.append(
            f"FIRST_TIMESTAMP_MISMATCH expected={expected_first_ms} got={first_timestamp_ms}"
        )
    if last_timestamp_ms != expected_last_ms:
        validation_errors.append(
            f"LAST_TIMESTAMP_MISMATCH expected={expected_last_ms} got={last_timestamp_ms}"
        )
    if missing_timestamps:
        validation_errors.append(f"MISSING_BUCKETS count={len(missing_timestamps)}")
    if duplicates:
        validation_errors.append(f"DUPLICATE_TIMESTAMPS count={duplicates}")
    if out_of_order_count:
        validation_errors.append(f"OUT_OF_ORDER_ROWS count={out_of_order_count}")
    if unexpected_deltas:
        validation_errors.append(
            "UNEXPECTED_INTERVAL_DELTAS samples="
            + ",".join(str(delta) for delta in unexpected_deltas[:5])
        )
    return {
        "is_complete": not validation_errors,
        "expected_row_count": spec.expected_rows_per_day,
        "row_count": len(rows),
        "first_timestamp_ms": first_timestamp_ms,
        "first_timestamp_utc": _timestamp_to_iso(first_timestamp_ms),
        "last_timestamp_ms": last_timestamp_ms,
        "last_timestamp_utc": _timestamp_to_iso(last_timestamp_ms),
        "expected_first_timestamp_ms": expected_first_ms,
        "expected_first_timestamp_utc": _timestamp_to_iso(expected_first_ms),
        "expected_last_timestamp_ms": expected_last_ms,
        "expected_last_timestamp_utc": _timestamp_to_iso(expected_last_ms),
        "missing_bucket_count": len(missing_timestamps),
        "missing_bucket_samples_utc": [
            str(_timestamp_to_iso(timestamp)) for timestamp in missing_timestamps[:5]
        ],
        "duplicate_timestamp_count": duplicates,
        "unexpected_delta_count": len(unexpected_deltas),
        "unexpected_delta_examples_ms": unexpected_deltas[:5],
        "validation_errors": validation_errors,
    }


def _inspect_existing_file(
    path: Path,
    *,
    spec: BybitKlineTimeframeSpec,
    day: date,
) -> dict[str, object]:
    if not path.exists():
        return {
            "path": str(path),
            "exists": False,
            "status": "MISSING",
            "validation": None,
        }
    try:
        rows = _read_csv_rows(path)
    except (OSError, UnicodeDecodeError, csv.Error) as exc:
        return {
            "path": str(path),
            "exists": True,
            "status": "UNREADABLE",
            "error": str(exc),
            "validation": None,
        }
    validation = _validate_rows(rows, spec=spec, day=day)
    return {
        "path": str(path),
        "exists": True,
        "status": "COMPLETE" if bool(validation["is_complete"]) else "INCOMPLETE",
        "validation": validation,
    }


def _render_csv(rows: tuple[dict[str, object], ...]) -> str:
    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=_CSV_HEADER, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow(
            {
                "startTime": str(row["startTime"]),
                "open": str(row["open"]),
                "high": str(row["high"]),
                "low": str(row["low"]),
                "close": str(row["close"]),
                "volume": str(row["volume"]),
                "turnover": str(row["turnover"]),
            }
        )
    return buffer.getvalue()


def _aggregate_rows(
    rows: tuple[dict[str, object], ...],
    *,
    target_spec: BybitKlineTimeframeSpec,
) -> tuple[dict[str, object], ...]:
    if target_spec.aggregation_factor <= 1:
        return rows
    aggregated_rows: list[dict[str, object]] = []
    chunk_size = target_spec.aggregation_factor
    for offset in range(0, len(rows), chunk_size):
        chunk = rows[offset : offset + chunk_size]
        if len(chunk) != chunk_size:
            raise BybitKlineFetchError(
                f"Cannot aggregate {target_spec.timeframe}: incomplete source chunk at offset {offset}."
            )
        highs = [_coerce_decimal(item["high"]) for item in chunk]
        lows = [_coerce_decimal(item["low"]) for item in chunk]
        volumes = [_coerce_decimal(item["volume"]) for item in chunk]
        turnovers = [_coerce_decimal(item["turnover"]) for item in chunk]
        aggregated_rows.append(
            {
                "startTime": int(chunk[0]["startTime"]),
                "open": str(chunk[0]["open"]),
                "high": _decimal_to_str(max(highs)),
                "low": _decimal_to_str(min(lows)),
                "close": str(chunk[-1]["close"]),
                "volume": _decimal_to_str(sum(volumes, Decimal("0"))),
                "turnover": _decimal_to_str(sum(turnovers, Decimal("0"))),
            }
        )
    return tuple(aggregated_rows)


def _load_json_file(path: Path) -> dict[str, object] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _emit_progress(progress: ProgressFn | None, message: str) -> None:
    if progress is not None:
        progress(message)


def _discover_pairs(root: Path) -> tuple[str, ...]:
    resolved_root = root.expanduser().resolve()
    if not resolved_root.is_dir():
        return ()
    pairs = sorted(
        _normalize_symbol(item.name)
        for item in resolved_root.iterdir()
        if item.is_dir() and _normalize_symbol(item.name)
    )
    return tuple(pair for pair in pairs if pair)


def _discover_orderbook_window(orderbook_root: Path, symbol: str) -> dict[str, object]:
    pair_root = orderbook_root.expanduser().resolve() / symbol
    if not pair_root.is_dir():
        return {
            "pair_root": str(pair_root),
            "has_orderbook": False,
            "first_date": None,
            "last_date": None,
            "day_count": 0,
        }
    dates = sorted(
        {
            item_date
            for item in pair_root.iterdir()
            if (item_date := _extract_date_from_name(item.name)) is not None
        }
    )
    if not dates:
        dates = sorted(
            {
                item_date
                for item in pair_root.rglob("*")
                if (item_date := _extract_date_from_name(item.name)) is not None
            }
        )
    if not dates:
        return {
            "pair_root": str(pair_root),
            "has_orderbook": False,
            "first_date": None,
            "last_date": None,
            "day_count": 0,
        }
    return {
        "pair_root": str(pair_root),
        "has_orderbook": True,
        "first_date": dates[0].isoformat(),
        "last_date": dates[-1].isoformat(),
        "day_count": len(dates),
    }


def _discover_kline_date_bounds(
    kline_root: Path,
    symbol: str,
    spec: BybitKlineTimeframeSpec,
) -> dict[str, object]:
    timeframe_root = kline_root.expanduser().resolve() / symbol / spec.path_component
    if not timeframe_root.is_dir():
        return {
            "timeframe": spec.timeframe,
            "path_root": str(timeframe_root),
            "has_files": False,
            "first_date": None,
            "last_date": None,
            "file_count": 0,
        }
    dates = sorted(
        {
            item_date
            for item in timeframe_root.rglob("*.csv")
            if (item_date := _extract_date_from_name(item.name)) is not None
        }
    )
    if not dates:
        return {
            "timeframe": spec.timeframe,
            "path_root": str(timeframe_root),
            "has_files": False,
            "first_date": None,
            "last_date": None,
            "file_count": 0,
        }
    return {
        "timeframe": spec.timeframe,
        "path_root": str(timeframe_root),
        "has_files": True,
        "first_date": dates[0].isoformat(),
        "last_date": dates[-1].isoformat(),
        "file_count": len(dates),
    }


def _summarize_timeframe_window(
    *,
    kline_root: Path,
    symbol: str,
    spec: BybitKlineTimeframeSpec,
    start_day: date,
    end_day: date,
    max_examples: int,
) -> dict[str, object]:
    total_days = 0
    complete_days = 0
    incomplete_days = 0
    missing_days = 0
    unreadable_days = 0
    examples: list[dict[str, object]] = []
    for current_day in _iter_days(start_day, end_day):
        total_days += 1
        target_path = _target_path(
            kline_root=kline_root,
            symbol=symbol,
            spec=spec,
            day=current_day,
        )
        inspection = _inspect_existing_file(target_path, spec=spec, day=current_day)
        status = str(inspection.get("status") or "")
        if status == "COMPLETE":
            complete_days += 1
            continue
        if status == "MISSING":
            missing_days += 1
        elif status == "UNREADABLE":
            unreadable_days += 1
        else:
            incomplete_days += 1
        if len(examples) < max_examples:
            examples.append(
                {
                    "date": current_day.isoformat(),
                    "path": str(target_path),
                    "status": status,
                    "validation": inspection.get("validation"),
                    "error": inspection.get("error"),
                }
            )
    return {
        "timeframe": spec.timeframe,
        "window_start_date": start_day.isoformat(),
        "window_end_date": end_day.isoformat(),
        "window_day_count": total_days,
        "complete_day_count": complete_days,
        "incomplete_day_count": incomplete_days,
        "missing_day_count": missing_days,
        "unreadable_day_count": unreadable_days,
        "all_days_complete": total_days > 0 and complete_days == total_days,
        "problem_examples": examples,
    }


def _load_resume_state(path: Path) -> dict[str, object]:
    payload = _load_json_file(path)
    if payload is not None:
        return payload
    return {
        "schema_version": "v1",
        "updated_at_utc": _utc_now_iso(),
        "target_state": {},
    }


def _save_resume_state(path: Path, state: dict[str, object]) -> None:
    state["updated_at_utc"] = _utc_now_iso()
    atomic_write_json(path, state, indent=2)


def _target_key(symbol: str, timeframe: str, day: date) -> str:
    return f"{symbol}|{timeframe}|{day.isoformat()}"


def _source_key(symbol: str, timeframe: str, day: date) -> str:
    return f"{symbol}|{timeframe}|{day.isoformat()}"


def _source_cache_path(report_root: Path, symbol: str, timeframe: str, day: date) -> Path:
    return (
        report_root
        / "resume_cache"
        / symbol
        / timeframe
        / f"{symbol}_{timeframe}_{day.isoformat()}.json"
    )


def _load_source_cache(path: Path) -> dict[str, object] | None:
    payload = _load_json_file(path)
    if payload is None:
        return None
    rows = payload.get("rows")
    page_reports = payload.get("page_reports")
    if not isinstance(rows, list) or not isinstance(page_reports, list):
        return None
    return payload


def _save_source_cache(
    path: Path,
    *,
    rows: tuple[dict[str, object], ...],
    page_reports: tuple[dict[str, object], ...],
    next_end_ms: int | None,
    completed: bool,
) -> None:
    atomic_write_json(
        path,
        {
            "schema_version": "v1",
            "completed": completed,
            "next_end_ms": next_end_ms,
            "page_reports": list(page_reports),
            "rows": list(rows),
            "updated_at_utc": _utc_now_iso(),
        },
        indent=2,
    )


def _fetch_day_rows(
    *,
    symbol: str,
    fetch_interval: str,
    fetch_interval_ms: int,
    day: date,
    http_get: Any,
    timeout_s: int,
    cache_path: Path | None = None,
    progress: ProgressFn | None = None,
) -> tuple[tuple[dict[str, object], ...], tuple[dict[str, object], ...]]:
    cached_payload = _load_source_cache(cache_path) if cache_path is not None else None
    if cached_payload is not None and bool(cached_payload.get("completed")):
        _emit_progress(
            progress,
            f"[Resume] source cache hit {symbol} {fetch_interval} {day.isoformat()} -> {cache_path}",
        )
        cached_rows = tuple(
            row
            for row in (
                _canonicalize_row(item)
                for item in cached_payload.get("rows", [])
            )
            if row is not None
        )
        cached_page_reports = tuple(
            item for item in cached_payload.get("page_reports", []) if isinstance(item, dict)
        )
        return cached_rows, cached_page_reports
    requested_start_ms = _day_start_ms(day)
    requested_end_ms = requested_start_ms + _DAY_MS - fetch_interval_ms
    collected_by_timestamp: dict[int, dict[str, object]] = {}
    page_reports: list[dict[str, object]] = []
    next_end_ms = requested_end_ms
    if cached_payload is not None:
        for raw_row in cached_payload.get("rows", []):
            row = _canonicalize_row(raw_row)
            if row is not None:
                collected_by_timestamp[int(row["startTime"])] = row
        page_reports = [
            item for item in cached_payload.get("page_reports", []) if isinstance(item, dict)
        ]
        cached_next_end_ms = _coerce_timestamp_ms(cached_payload.get("next_end_ms"))
        if cached_next_end_ms is not None:
            next_end_ms = cached_next_end_ms
    page_index = len(page_reports)
    while True:
        page_index += 1
        _emit_progress(
            progress,
            f"[Fetch] {symbol} {fetch_interval} {day.isoformat()} page={page_index} request_end={_timestamp_to_iso(next_end_ms)}",
        )
        query = urlencode(
            {
                "category": "spot",
                "symbol": symbol,
                "interval": fetch_interval,
                "start": str(requested_start_ms),
                "end": str(next_end_ms),
                "limit": str(_MAX_PAGE_SIZE),
            }
        )
        request = Request(
            f"{BYBIT_PUBLIC_KLINE_URL}?{query}",
            headers={"User-Agent": BYBIT_KLINE_USER_AGENT},
        )
        try:
            with http_get(request, timeout=timeout_s) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            raise BybitKlineFetchError(str(exc)) from exc
        page_rows = _parse_bybit_payload(payload)
        scoped_rows = tuple(
            row
            for row in page_rows
            if requested_start_ms <= int(row["startTime"]) <= requested_end_ms
        )
        for row in scoped_rows:
            collected_by_timestamp[int(row["startTime"])] = row
        earliest_timestamp_ms = (
            min(int(row["startTime"]) for row in scoped_rows) if scoped_rows else None
        )
        latest_timestamp_ms = (
            max(int(row["startTime"]) for row in scoped_rows) if scoped_rows else None
        )
        page_reports.append(
            {
                "page_index": page_index,
                "request_start_ms": requested_start_ms,
                "request_start_utc": _timestamp_to_iso(requested_start_ms),
                "request_end_ms": next_end_ms,
                "request_end_utc": _timestamp_to_iso(next_end_ms),
                "returned_row_count": len(page_rows),
                "scoped_row_count": len(scoped_rows),
                "earliest_timestamp_ms": earliest_timestamp_ms,
                "earliest_timestamp_utc": _timestamp_to_iso(earliest_timestamp_ms),
                "latest_timestamp_ms": latest_timestamp_ms,
                "latest_timestamp_utc": _timestamp_to_iso(latest_timestamp_ms),
            }
        )
        _emit_progress(
            progress,
            f"[Fetch] {symbol} {fetch_interval} {day.isoformat()} page={page_index} rows={len(scoped_rows)} earliest={_timestamp_to_iso(earliest_timestamp_ms)} latest={_timestamp_to_iso(latest_timestamp_ms)}",
        )
        if not scoped_rows:
            break
        if earliest_timestamp_ms is None or earliest_timestamp_ms <= requested_start_ms:
            next_end_ms = None
            break
        candidate_end_ms = earliest_timestamp_ms - fetch_interval_ms
        if candidate_end_ms >= next_end_ms:
            raise BybitKlineFetchError("Pagination did not move backwards; aborting fail-closed.")
        next_end_ms = candidate_end_ms
        if cache_path is not None:
            _save_source_cache(
                cache_path,
                rows=tuple(collected_by_timestamp[timestamp] for timestamp in sorted(collected_by_timestamp)),
                page_reports=tuple(page_reports),
                next_end_ms=next_end_ms,
                completed=False,
            )
        if page_index >= 8:
            raise BybitKlineFetchError("Pagination exceeded the bounded page limit.")
    ordered_rows = tuple(
        collected_by_timestamp[timestamp]
        for timestamp in sorted(collected_by_timestamp)
    )
    if cache_path is not None:
        _save_source_cache(
            cache_path,
            rows=ordered_rows,
            page_reports=tuple(page_reports),
            next_end_ms=next_end_ms,
            completed=True,
        )
    return ordered_rows, tuple(page_reports)


def audit_bybit_recollection_scope(
    *,
    kline_root: Path,
    timeframes: tuple[str, ...],
    orderbook_root: Path | None = None,
    pairs: tuple[str, ...] | None = None,
    start_date: str | date | None = None,
    end_date: str | date | None = None,
    require_orderbook: bool = False,
    bound_start_to_orderbook: bool = True,
    bound_end_to_orderbook: bool = True,
    max_problem_examples: int = 5,
) -> dict[str, object]:
    resolved_kline_root = kline_root.expanduser().resolve()
    resolved_orderbook_root = (
        orderbook_root.expanduser().resolve() if orderbook_root is not None else None
    )
    specs = tuple(
        _TIMEFRAME_SPECS[normalize_timeframe(timeframe)]
        for timeframe in dict.fromkeys(timeframes)
    )
    if pairs:
        requested_pairs = tuple(
            dict.fromkeys(_normalize_symbol(pair) for pair in pairs if _normalize_symbol(pair))
        )
    else:
        auto_pairs = set(_discover_pairs(resolved_kline_root))
        if resolved_orderbook_root is not None:
            auto_pairs.update(_discover_pairs(resolved_orderbook_root))
        requested_pairs = tuple(sorted(auto_pairs))
    start_bound = _parse_iso_date(start_date) if start_date is not None else None
    end_bound = _parse_iso_date(end_date) if end_date is not None else None
    pair_reports: list[dict[str, object]] = []
    eligible_pairs = 0
    for symbol in requested_pairs:
        orderbook_window = (
            _discover_orderbook_window(resolved_orderbook_root, symbol)
            if resolved_orderbook_root is not None
            else {
                "pair_root": "",
                "has_orderbook": False,
                "first_date": None,
                "last_date": None,
                "day_count": 0,
            }
        )
        kline_bounds_by_timeframe = {
            spec.timeframe: _discover_kline_date_bounds(resolved_kline_root, symbol, spec)
            for spec in specs
        }
        effective_start = start_bound
        effective_end = end_bound
        if resolved_orderbook_root is not None and bool(orderbook_window["has_orderbook"]):
            orderbook_first = _parse_iso_date(str(orderbook_window["first_date"]))
            orderbook_last = _parse_iso_date(str(orderbook_window["last_date"]))
            if bound_start_to_orderbook or effective_start is None:
                effective_start = orderbook_first if effective_start is None else max(effective_start, orderbook_first)
            if bound_end_to_orderbook or effective_end is None:
                effective_end = orderbook_last if effective_end is None else min(effective_end, orderbook_last)
        eligible = True
        eligibility_reason = "ELIGIBLE"
        if require_orderbook and not bool(orderbook_window["has_orderbook"]):
            eligible = False
            eligibility_reason = "ORDERBOOK_MISSING"
        elif effective_start is None or effective_end is None:
            eligible = False
            eligibility_reason = "DATE_WINDOW_UNRESOLVED"
        elif effective_end < effective_start:
            eligible = False
            eligibility_reason = "EMPTY_EFFECTIVE_WINDOW"
        timeframe_reports: dict[str, object] = {}
        if eligible and effective_start is not None and effective_end is not None:
            eligible_pairs += 1
            for spec in specs:
                timeframe_reports[spec.timeframe] = _summarize_timeframe_window(
                    kline_root=resolved_kline_root,
                    symbol=symbol,
                    spec=spec,
                    start_day=effective_start,
                    end_day=effective_end,
                    max_examples=max_problem_examples,
                )
        pair_reports.append(
            {
                "symbol": symbol,
                "eligible_for_v53_orderbook_bounded_recollection": eligible,
                "eligibility_reason": eligibility_reason,
                "orderbook_window": orderbook_window,
                "effective_start_date": effective_start.isoformat() if effective_start is not None else None,
                "effective_end_date": effective_end.isoformat() if effective_end is not None else None,
                "kline_date_bounds_by_timeframe": kline_bounds_by_timeframe,
                "timeframe_reports": timeframe_reports,
            }
        )
    report = {
        "schema_version": "v1",
        "audit_mode": "ORDERBOOK_BOUNDED_RECOLLECTION_SCOPE"
        if require_orderbook
        else "KLINE_RECOLLECTION_SCOPE",
        "generated_at_utc": _utc_now_iso(),
        "kline_root": str(resolved_kline_root),
        "orderbook_root": str(resolved_orderbook_root) if resolved_orderbook_root is not None else None,
        "requested_pairs": list(requested_pairs),
        "timeframes": [spec.timeframe for spec in specs],
        "start_date_bound": start_bound.isoformat() if start_bound is not None else None,
        "end_date_bound": end_bound.isoformat() if end_bound is not None else None,
        "require_orderbook": require_orderbook,
        "bound_start_to_orderbook": bound_start_to_orderbook,
        "bound_end_to_orderbook": bound_end_to_orderbook,
        "pair_count": len(requested_pairs),
        "eligible_pair_count": eligible_pairs,
        "pair_reports": pair_reports,
    }
    return report


def recollect_bybit_kline_days(
    *,
    symbol: str,
    timeframes: tuple[str, ...],
    start_date: str | date,
    end_date: str | date,
    kline_root: Path,
    report_root: Path,
    dry_run: bool = False,
    force_fetch: bool = False,
    timeout_s: int = 20,
    http_get: Any = None,
    resume: bool = True,
    resume_state_path: Path | None = None,
    stop_after_targets: int | None = None,
    progress: ProgressFn | None = None,
) -> dict[str, object]:
    normalized_symbol = _normalize_symbol(symbol)
    if not normalized_symbol:
        raise ValueError("symbol must not be empty")
    specs = tuple(
        _TIMEFRAME_SPECS[normalize_timeframe(timeframe)]
        for timeframe in dict.fromkeys(timeframes)
    )
    if not specs:
        raise ValueError("At least one timeframe is required")
    resolved_kline_root = kline_root.expanduser().resolve()
    resolved_report_root = report_root.expanduser().resolve()
    resolved_report_root.mkdir(parents=True, exist_ok=True)
    start_day = _parse_iso_date(start_date)
    end_day = _parse_iso_date(end_date)
    requested_days = _iter_days(start_day, end_day)
    opener = http_get or urlopen
    effective_resume_state_path = (
        resume_state_path.expanduser().resolve()
        if resume_state_path is not None
        else resolved_report_root / f"resume_{normalized_symbol}_{start_day.isoformat()}_{end_day.isoformat()}.json"
    )
    resume_state = _load_resume_state(effective_resume_state_path) if resume else {"target_state": {}}
    target_state = resume_state.setdefault("target_state", {})
    report_entries: list[dict[str, object]] = []
    success_count = 0
    failure_count = 0
    processed_target_count = 0
    interrupted_for_testing = False
    source_cache: dict[
        tuple[str, date],
        tuple[tuple[dict[str, object], ...], tuple[dict[str, object], ...], dict[str, object]],
    ] = {}
    total_target_count = len(specs) * len(requested_days)
    _emit_progress(
        progress,
        f"[Pair] {normalized_symbol} targets={total_target_count} report_root={resolved_report_root}",
    )
    _emit_progress(
        progress,
        f"[Pair] {normalized_symbol} repaired CSVs go to {resolved_kline_root / normalized_symbol}",
    )
    for spec in specs:
        for day in requested_days:
            target_key = _target_key(normalized_symbol, spec.timeframe, day)
            target_resume_state = (
                target_state.get(target_key) if isinstance(target_state, dict) else None
            )
            target_path = _target_path(
                kline_root=resolved_kline_root,
                symbol=normalized_symbol,
                spec=spec,
                day=day,
            )
            existing_file = _inspect_existing_file(target_path, spec=spec, day=day)
            entry: dict[str, object] = {
                "symbol": normalized_symbol,
                "timeframe": spec.timeframe,
                "date": day.isoformat(),
                "target_path": str(target_path),
                "dry_run": dry_run,
                "fetch_mode": BYBIT_KLINE_FETCH_MODE,
                "existing_file": existing_file,
                "requested_range_start_ms": _day_start_ms(day),
                "requested_range_start_utc": _timestamp_to_iso(_day_start_ms(day)),
                "requested_range_end_ms": _expected_last_bucket_ms(day, spec),
                "requested_range_end_utc": _timestamp_to_iso(_expected_last_bucket_ms(day, spec)),
                "source_timeframe": spec.source_timeframe,
                "collection_mode": (
                    "BYBIT_PUBLIC_DIRECT"
                    if spec.aggregation_factor == 1
                    else f"BYBIT_PUBLIC_{spec.source_timeframe.upper()}_AGGREGATED_TO_{spec.timeframe.upper()}"
                ),
                "resume_state_path": str(effective_resume_state_path),
            }
            resumed_status = ""
            if isinstance(target_resume_state, dict):
                resumed_status = str(target_resume_state.get("status") or "")
            if resume and resumed_status in _RESUME_SKIP_STATUSES:
                _emit_progress(
                    progress,
                    f"[Resume] skip {normalized_symbol} {spec.timeframe} {day.isoformat()} status={resumed_status}",
                )
                entry["validation"] = target_resume_state.get("validation") if isinstance(target_resume_state, dict) else None
                entry["fetched_page_count"] = int(target_resume_state.get("fetched_page_count") or 0) if isinstance(target_resume_state, dict) else 0
                entry["fetched_row_count"] = int(target_resume_state.get("fetched_row_count") or 0) if isinstance(target_resume_state, dict) else 0
                entry["repair_status"] = "SKIPPED_RESUME_STATE"
                report_entries.append(entry)
                success_count += 1
                processed_target_count += 1
            elif not force_fetch and existing_file["status"] == "COMPLETE":
                _emit_progress(
                    progress,
                    f"[Skip] existing complete {normalized_symbol} {spec.timeframe} {day.isoformat()} -> {target_path}",
                )
                entry["fetched_page_count"] = 0
                entry["fetched_row_count"] = existing_file["validation"]["row_count"]  # type: ignore[index]
                entry["validation"] = existing_file["validation"]
                entry["repair_status"] = "SKIPPED_EXISTING_COMPLETE"
                report_entries.append(entry)
                target_state[target_key] = {
                    "status": entry["repair_status"],
                    "validation": entry["validation"],
                    "fetched_page_count": entry["fetched_page_count"],
                    "fetched_row_count": entry["fetched_row_count"],
                    "updated_at_utc": _utc_now_iso(),
                }
                if resume:
                    _save_resume_state(effective_resume_state_path, resume_state)
                success_count += 1
                processed_target_count += 1
            else:
                _emit_progress(
                    progress,
                    f"[Target] {normalized_symbol} {spec.timeframe} {day.isoformat()} -> {target_path}",
                )
                try:
                    source_key = (spec.source_timeframe, day)
                    source_spec = _TIMEFRAME_SPECS[spec.source_timeframe]
                    if source_key not in source_cache:
                        source_rows, page_reports = _fetch_day_rows(
                            symbol=normalized_symbol,
                            fetch_interval=source_spec.fetch_interval,
                            fetch_interval_ms=source_spec.fetch_interval_ms,
                            day=day,
                            http_get=opener,
                            timeout_s=timeout_s,
                            cache_path=_source_cache_path(
                                resolved_report_root,
                                normalized_symbol,
                                spec.source_timeframe,
                                day,
                            )
                            if resume
                            else None,
                            progress=progress,
                        )
                        source_validation = _validate_rows(source_rows, spec=source_spec, day=day)
                        source_cache[source_key] = (source_rows, page_reports, source_validation)
                    source_rows, page_reports, source_validation = source_cache[source_key]
                    if spec.aggregation_factor > 1 and not bool(source_validation["is_complete"]):
                        raise BybitKlineFetchError(
                            f"Cannot derive {spec.timeframe} from incomplete {spec.source_timeframe} source rows."
                        )
                    rows = _aggregate_rows(source_rows, target_spec=spec)
                    validation = _validate_rows(rows, spec=spec, day=day)
                    entry["page_reports"] = list(page_reports)
                    entry["fetched_page_count"] = len(page_reports)
                    entry["fetched_row_count"] = len(rows)
                    if spec.aggregation_factor > 1:
                        entry["source_validation"] = source_validation
                    entry["validation"] = validation
                    if bool(validation["is_complete"]):
                        entry["replacement_mode"] = "DRY_RUN_ONLY" if dry_run else "ATOMIC_REPLACE"
                        entry["would_replace_existing"] = bool(existing_file["exists"])
                        if not dry_run:
                            atomic_write_text(target_path, _render_csv(rows))
                            entry["repair_status"] = "REPAIRED"
                            _emit_progress(
                                progress,
                                f"[Write] repaired {normalized_symbol} {spec.timeframe} {day.isoformat()} -> {target_path}",
                            )
                        else:
                            entry["repair_status"] = "DRY_RUN_READY"
                            _emit_progress(
                                progress,
                                f"[DryRun] ready {normalized_symbol} {spec.timeframe} {day.isoformat()} -> would replace {target_path}",
                            )
                        success_count += 1
                    else:
                        entry["repair_status"] = "VALIDATION_FAILED"
                        _emit_progress(
                            progress,
                            f"[Fail] validation failed {normalized_symbol} {spec.timeframe} {day.isoformat()} -> {target_path}",
                        )
                        failure_count += 1
                except BybitKlineFetchError as exc:
                    entry["page_reports"] = []
                    entry["fetched_page_count"] = 0
                    entry["fetched_row_count"] = 0
                    entry["validation"] = None
                    entry["repair_status"] = "FETCH_FAILED"
                    entry["error"] = str(exc)
                    _emit_progress(
                        progress,
                        f"[Fail] fetch failed {normalized_symbol} {spec.timeframe} {day.isoformat()} -> {exc}",
                    )
                    failure_count += 1
                report_entries.append(entry)
                target_state[target_key] = {
                    "status": entry["repair_status"],
                    "validation": entry.get("validation"),
                    "fetched_page_count": entry.get("fetched_page_count", 0),
                    "fetched_row_count": entry.get("fetched_row_count", 0),
                    "updated_at_utc": _utc_now_iso(),
                }
                if resume:
                    _save_resume_state(effective_resume_state_path, resume_state)
                processed_target_count += 1
            if (
                stop_after_targets is not None
                and processed_target_count >= stop_after_targets
                and processed_target_count < total_target_count
            ):
                interrupted_for_testing = True
                _emit_progress(
                    progress,
                    f"[Stop] intentional stop_after_targets reached for {normalized_symbol} after {processed_target_count} targets",
                )
                break
        if interrupted_for_testing:
            break
    if interrupted_for_testing:
        batch_status = BYBIT_KLINE_PARTIAL
    elif failure_count == 0:
        batch_status = BYBIT_KLINE_READY
    elif success_count > 0:
        batch_status = BYBIT_KLINE_PARTIAL
    else:
        batch_status = BYBIT_KLINE_FAILED
    report = {
        "schema_version": "v1",
        "batch_status": batch_status,
        "fetch_mode": BYBIT_KLINE_FETCH_MODE,
        "symbol": normalized_symbol,
        "timeframes": [spec.timeframe for spec in specs],
        "start_date": start_day.isoformat(),
        "end_date": end_day.isoformat(),
        "dry_run": dry_run,
        "force_fetch": force_fetch,
        "resume": resume,
        "resume_state_path": str(effective_resume_state_path),
        "kline_root": str(resolved_kline_root),
        "report_root": str(resolved_report_root),
        "generated_at_utc": _utc_now_iso(),
        "requested_file_count": total_target_count,
        "processed_target_count": processed_target_count,
        "success_count": success_count,
        "failure_count": failure_count,
        "interrupted_for_testing": interrupted_for_testing,
        "entries": report_entries,
    }
    report_name = (
        f"bybit_kline_recollection_{normalized_symbol}_{start_day.isoformat()}_{end_day.isoformat()}.json"
    )
    report_path = resolved_report_root / report_name
    atomic_write_json(report_path, report, indent=2)
    report["report_path"] = str(report_path.resolve())
    _emit_progress(progress, f"[Pair] {normalized_symbol} report -> {report['report_path']}")
    return report


def recollect_bybit_kline_batch(
    *,
    timeframes: tuple[str, ...],
    kline_root: Path,
    report_root: Path,
    orderbook_root: Path | None = None,
    pairs: tuple[str, ...] | None = None,
    start_date: str | date | None = None,
    end_date: str | date | None = None,
    require_orderbook: bool = False,
    bound_start_to_orderbook: bool = True,
    bound_end_to_orderbook: bool = True,
    audit_only: bool = False,
    dry_run: bool = False,
    force_fetch: bool = False,
    timeout_s: int = 20,
    http_get: Any = None,
    resume: bool = True,
    stop_after_targets: int | None = None,
    progress: ProgressFn | None = None,
) -> dict[str, object]:
    resolved_report_root = report_root.expanduser().resolve()
    resolved_report_root.mkdir(parents=True, exist_ok=True)
    _emit_progress(progress, f"[Batch] report root -> {resolved_report_root}")
    audit_report = audit_bybit_recollection_scope(
        kline_root=kline_root,
        timeframes=timeframes,
        orderbook_root=orderbook_root,
        pairs=pairs,
        start_date=start_date,
        end_date=end_date,
        require_orderbook=require_orderbook,
        bound_start_to_orderbook=bound_start_to_orderbook,
        bound_end_to_orderbook=bound_end_to_orderbook,
    )
    audit_path = resolved_report_root / "bybit_kline_scope_audit.json"
    atomic_write_json(audit_path, audit_report, indent=2)
    _emit_progress(progress, f"[Audit] scope report -> {audit_path.resolve()}")
    _emit_progress(
        progress,
        f"[Audit] eligible pairs={audit_report['eligible_pair_count']} / {audit_report['pair_count']}",
    )
    for pair_audit in audit_report["pair_reports"]:
        symbol = str(pair_audit["symbol"])
        eligible = bool(pair_audit["eligible_for_v53_orderbook_bounded_recollection"])
        if eligible:
            _emit_progress(
                progress,
                f"[Audit] {symbol} window={pair_audit['effective_start_date']}..{pair_audit['effective_end_date']}",
            )
        else:
            _emit_progress(
                progress,
                f"[Audit] {symbol} skipped={pair_audit['eligibility_reason']}",
            )
    if audit_only:
        result = {
            "schema_version": "v1",
            "batch_status": BYBIT_KLINE_READY,
            "mode": "AUDIT_ONLY",
            "generated_at_utc": _utc_now_iso(),
            "audit_report_path": str(audit_path.resolve()),
            "audit_report": audit_report,
            "pair_reports": [],
            "eligible_pair_count": audit_report["eligible_pair_count"],
        }
        batch_report_path = resolved_report_root / "bybit_kline_batch_report.json"
        atomic_write_json(batch_report_path, result, indent=2)
        result["report_path"] = str(batch_report_path.resolve())
        _emit_progress(progress, f"[Batch] audit-only report -> {result['report_path']}")
        return result
    pair_run_reports: list[dict[str, object]] = []
    remaining_stop_budget = stop_after_targets
    for pair_audit in audit_report["pair_reports"]:
        if not bool(pair_audit["eligible_for_v53_orderbook_bounded_recollection"]):
            pair_run_reports.append(
                {
                    "symbol": pair_audit["symbol"],
                    "batch_status": "SKIPPED_NOT_ELIGIBLE",
                    "effective_start_date": pair_audit["effective_start_date"],
                    "effective_end_date": pair_audit["effective_end_date"],
                    "eligibility_reason": pair_audit["eligibility_reason"],
                }
            )
            continue
        symbol = str(pair_audit["symbol"])
        pair_report_root = resolved_report_root / symbol
        pair_resume_state_path = pair_report_root / "resume_state.json"
        pair_report = recollect_bybit_kline_days(
            symbol=symbol,
            timeframes=timeframes,
            start_date=str(pair_audit["effective_start_date"]),
            end_date=str(pair_audit["effective_end_date"]),
            kline_root=kline_root,
            report_root=pair_report_root,
            dry_run=dry_run,
            force_fetch=force_fetch,
            timeout_s=timeout_s,
            http_get=http_get,
            resume=resume,
            resume_state_path=pair_resume_state_path,
            stop_after_targets=remaining_stop_budget,
            progress=progress,
        )
        pair_report["effective_start_date"] = pair_audit["effective_start_date"]
        pair_report["effective_end_date"] = pair_audit["effective_end_date"]
        pair_run_reports.append(pair_report)
        if remaining_stop_budget is not None:
            remaining_stop_budget = max(0, remaining_stop_budget - int(pair_report["processed_target_count"]))
            if bool(pair_report["interrupted_for_testing"]):
                break
    eligible_pair_count = int(audit_report["eligible_pair_count"])
    successful_pair_count = sum(
        1 for item in pair_run_reports if str(item.get("batch_status")) == BYBIT_KLINE_READY
    )
    interrupted_for_testing = any(bool(item.get("interrupted_for_testing")) for item in pair_run_reports)
    failure_pair_count = sum(
        1
        for item in pair_run_reports
        if str(item.get("batch_status")) in {BYBIT_KLINE_FAILED, BYBIT_KLINE_PARTIAL}
    )
    if interrupted_for_testing:
        batch_status = BYBIT_KLINE_PARTIAL
    elif eligible_pair_count == 0:
        batch_status = BYBIT_KLINE_FAILED
    elif successful_pair_count == eligible_pair_count:
        batch_status = BYBIT_KLINE_READY
    elif successful_pair_count > 0:
        batch_status = BYBIT_KLINE_PARTIAL
    else:
        batch_status = BYBIT_KLINE_FAILED
    result = {
        "schema_version": "v1",
        "batch_status": batch_status,
        "mode": "MULTI_PAIR_BATCH",
        "generated_at_utc": _utc_now_iso(),
        "kline_root": str(kline_root.expanduser().resolve()),
        "orderbook_root": str(orderbook_root.expanduser().resolve()) if orderbook_root is not None else None,
        "timeframes": list(dict.fromkeys(normalize_timeframe(timeframe) for timeframe in timeframes)),
        "audit_report_path": str(audit_path.resolve()),
        "audit_report": audit_report,
        "pair_reports": pair_run_reports,
        "eligible_pair_count": eligible_pair_count,
        "successful_pair_count": successful_pair_count,
        "failure_pair_count": failure_pair_count,
        "interrupted_for_testing": interrupted_for_testing,
    }
    batch_report_path = resolved_report_root / "bybit_kline_batch_report.json"
    atomic_write_json(batch_report_path, result, indent=2)
    result["report_path"] = str(batch_report_path.resolve())
    _emit_progress(progress, f"[Batch] final report -> {result['report_path']}")
    return result


__all__ = [
    "BYBIT_KLINE_FAILED",
    "BYBIT_KLINE_FETCH_MODE",
    "BYBIT_KLINE_PARTIAL",
    "BYBIT_KLINE_READY",
    "BYBIT_PUBLIC_KLINE_URL",
    "audit_bybit_recollection_scope",
    "normalize_timeframe",
    "recollect_bybit_kline_batch",
    "recollect_bybit_kline_days",
]
