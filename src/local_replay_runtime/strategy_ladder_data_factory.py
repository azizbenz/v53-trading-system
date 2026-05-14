"""Patch 6 Data Factory orchestration for the canonical Strategy Ladder rail."""

from __future__ import annotations

import csv
from datetime import UTC, datetime
import gzip
import hashlib
import json
from json import JSONDecodeError
from pathlib import Path
import re
import zipfile

from interface_contracts.atomic_io import atomic_write_json, atomic_write_text
from interface_contracts.storage_budget_support import normalize_silver_storage_format
from local_replay_runtime.bybit_historical_metadata import (
    BYBIT_HISTORICAL_METADATA_NOT_PROVEN,
    BYBIT_HISTORICAL_METADATA_READY,
    BYBIT_METADATA_SOURCE_MODE,
    CONFIGURED_FEE_PROVENANCE_READY,
    CURRENT_METADATA_PROXY,
    FEE_PROVENANCE_NOT_PROVEN,
    METADATA_PAIR_NOT_FOUND,
    METADATA_TEMPORAL_NOT_PROVEN,
    HistoricalMetadataCacheResult,
    load_historical_metadata_cache,
)
from local_replay_runtime.strategy_ladder_data_factory_models import (
    StrategyLadderCompressionReport,
    StrategyLadderDataFactoryManifest,
    StrategyLadderDataFactoryRequest,
    StrategyLadderDataFactoryResult,
    StrategyLadderDataQualityReport,
    StrategyLadderGoldFeatureManifest,
    StrategyLadderPairCoverage,
    StrategyLadderPairUniverseReport,
    StrategyLadderRawFileClassification,
    StrategyLadderRawSource,
    StrategyLadderSilverIndexEntry,
    finalize_hashed_model,
)
from local_replay_runtime.strategy_ladder_economic_provenance import (
    compute_economic_provenance,
)
from local_replay_runtime.strategy_ladder_feature_store import parse_time_boundary_to_ms
from local_replay_runtime.strategy_ladder_models import StrategyLadderFeatureRow
from local_replay_runtime.strategy_ladder_orderbook_reconstructor import (
    reconstruct_strategy_ladder_orderbook,
)
from local_replay_runtime.strategy_ladder_raw_sources import (
    resolve_strategy_ladder_raw_sources,
)


_TRADE_FIELDS = {"id", "timestamp", "price", "volume"}
_KLINE_FIELDS = {"starttime", "open", "high", "low", "close", "volume", "turnover"}
_METADATA_FIELDS = {
    "venue",
    "exchange",
    "market_type",
    "pair",
    "symbol",
    "base_coin",
    "quote_coin",
    "status",
    "min_notional",
    "minnotional",
    "tick_size",
    "ticksize",
    "qty_step",
    "step_size",
    "stepsize",
    "min_order_qty",
    "maker_fee_rate",
    "taker_fee_rate",
    "maker_fee",
    "makerfee",
    "taker_fee",
    "takerfee",
    "fee_source",
    "metadata_purpose",
    "proof_level",
    "source",
    "fetched_at_utc",
    "raw_payload_hash",
    "metadata_temporal_status",
}
_PAIR_DATE_PATTERN = re.compile(r"^(?P<pair>[A-Z0-9]+)_(?P<date>\d{4}-\d{2}-\d{2})$")
_PAIR_TF_DATE_PATTERN = re.compile(
    r"^(?P<pair>[A-Z0-9]+)_(?P<timeframe>[A-Za-z0-9]+)_(?P<date>\d{4}-\d{2}-\d{2})$"
)
_DATE_PAIR_SUFFIX_PATTERN = re.compile(
    r"^(?P<date>\d{4}-\d{2}-\d{2})_(?P<pair>[A-Z0-9]+)(?:_.+)?$"
)
# Patch 6 batch 1 — fast filename-only date probe used BEFORE classify_raw_file
# so out-of-range files (e.g. 2024 trades when range is 2025-04-29..30) are
# never opened/hashed. This is the cheap path on the 322 GB trades silver tree.
_FILENAME_DATE_PROBE = re.compile(r"(?P<date>\d{4}-\d{2}-\d{2})")
_LOOSE_DATE_PATTERN = re.compile(
    r"^(?P<year>\d{4})-(?P<month>\d{1,2})-(?P<day>\d{1,2})$"
)


def _normalize_boundary_text(raw_value: str) -> str:
    value = (raw_value or "").strip()
    if not value:
        return ""
    match = _LOOSE_DATE_PATTERN.match(value)
    if not match:
        return value
    return (
        f"{int(match.group('year')):04d}-"
        f"{int(match.group('month')):02d}-"
        f"{int(match.group('day')):02d}"
    )


def _is_date_only_boundary(value: str) -> bool:
    return bool(value and "T" not in value and _LOOSE_DATE_PATTERN.match(value))


def _probe_filename_date(path: Path) -> str:
    """Extract an ISO YYYY-MM-DD substring from the filename, or empty string."""

    match = _FILENAME_DATE_PROBE.search(path.name)
    return match.group("date") if match else ""


def _optional_float(value: object) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _date_in_range(
    iso_date: str,
    *,
    start_ms: int | None,
    end_ms: int | None,
) -> bool:
    """Return True when ``iso_date`` overlaps the given start/end millisecond window."""

    if not iso_date or (start_ms is None and end_ms is None):
        return True
    try:
        file_start = int(datetime.fromisoformat(f"{iso_date}T00:00:00+00:00").timestamp() * 1000)
        file_end = int(datetime.fromisoformat(f"{iso_date}T23:59:59+00:00").timestamp() * 1000)
    except ValueError:
        return True
    if start_ms is not None and file_end < start_ms:
        return False
    if end_ms is not None and file_start > end_ms:
        return False
    return True


def _span_days(start_ms: int | None, end_ms: int | None) -> int:
    if start_ms is None or end_ms is None or end_ms < start_ms:
        return 0
    return int((end_ms - start_ms) / 86_400_000) + 1


def _date_range_status_for_entry(
    iso_date: str,
    *,
    start_ms: int | None,
    end_ms: int | None,
) -> bool:
    if not iso_date:
        return False
    return _date_in_range(iso_date, start_ms=start_ms, end_ms=end_ms)


def _raw_timestamp_value(row: dict[str, object]) -> object:
    return (
        row.get("timestamp_ms")
        or row.get("timestamp_ns")
        or row.get("timestamp")
        or row.get("ts")
        or row.get("cts")
        or row.get("startTime")
        or row.get("starttime")
    )


def _sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _logical_file_name(path: Path) -> str:
    name = path.name
    lowered = name.lower()
    for suffix in (".data.zip", ".jsonl.zip", ".json.zip", ".csv.gz", ".jsonl.gz", ".data.gz", ".json.gz"):
        if lowered.endswith(suffix):
            return name[: -len(suffix)] + suffix.rsplit(".", 1)[0]
    return name


def _logical_stem(path: Path) -> str:
    return Path(_logical_file_name(path)).stem


def _iter_text_lines(path: Path, *, limit: int | None = None) -> tuple[str, ...]:
    lowered = path.name.lower()
    rows: list[str] = []
    if lowered.endswith(".zip"):
        with zipfile.ZipFile(path) as archive:
            names = [name for name in archive.namelist() if not name.endswith("/")]
            if not names:
                return ()
            with archive.open(names[0], "r") as handle:
                for raw_line in handle:
                    rows.append(raw_line.decode("utf-8-sig"))
                    if limit is not None and len(rows) >= limit:
                        break
        return tuple(rows)
    if lowered.endswith(".gz"):
        with gzip.open(path, "rt", encoding="utf-8-sig", newline="") as handle:
            for raw_line in handle:
                rows.append(raw_line)
                if limit is not None and len(rows) >= limit:
                    break
        return tuple(rows)
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for raw_line in handle:
            rows.append(raw_line)
            if limit is not None and len(rows) >= limit:
                break
    return tuple(rows)


def _iter_non_empty_jsonl(path: Path, *, limit: int | None = None) -> tuple[dict[str, object], ...]:
    records: list[dict[str, object]] = []
    for line in _iter_text_lines(path, limit=limit):
        stripped = line.strip()
        if not stripped:
            continue
        payload = json.loads(stripped)
        if isinstance(payload, dict):
            records.append(payload)
            if limit is not None and len(records) >= limit:
                break
    return tuple(records)


def _iter_non_empty_jsonl_safe(path: Path, *, limit: int | None = None) -> tuple[tuple[dict[str, object], ...], str | None]:
    try:
        return _iter_non_empty_jsonl(path, limit=limit), None
    except (UnicodeDecodeError, gzip.BadGzipFile, zipfile.BadZipFile):
        signature = path.read_bytes()[:4]
        if signature.startswith(b"\x1f\x8b") or signature.startswith(b"\x28\xb5\x2f\xfd") or signature.startswith(b"PK\x03\x04"):
            return (), "ORDERBOOK_DATA_SCHEMA_COMPRESSED_NOT_SUPPORTED"
        return (), "ORDERBOOK_DATA_SCHEMA_UNKNOWN"
    except JSONDecodeError:
        return (), "ORDERBOOK_DATA_SCHEMA_INVALID"


def _iter_csv_records(path: Path, *, limit: int | None = None) -> tuple[dict[str, str], ...]:
    lowered = path.name.lower()
    if lowered.endswith(".gz"):
        handle = gzip.open(path, "rt", encoding="utf-8-sig", newline="")
    else:
        handle = path.open("r", encoding="utf-8-sig", newline="")
    with handle:
        reader = csv.DictReader(handle)
        rows: list[dict[str, str]] = []
        for row in reader:
            rows.append(dict(row))
            if limit is not None and len(rows) >= limit:
                break
        return tuple(rows)


def _normalize_pair(value: str) -> str:
    return str(value or "").strip().upper()


def _topic_pair(value: object) -> str:
    topic = str(value or "").strip()
    if not topic:
        return ""
    parts = [part.strip().upper() for part in topic.split(".") if part.strip()]
    if len(parts) < 2 or parts[0] != "ORDERBOOK":
        return ""
    candidate = parts[-1]
    return candidate if candidate.isalnum() else ""


def _normalize_pair_candidate(value: object) -> str:
    candidate = _normalize_pair(str(value or ""))
    return candidate if candidate.isalnum() else ""


def _infer_pair_and_date(path: Path) -> tuple[str, str, str]:
    stem = _logical_stem(path)
    match = _PAIR_TF_DATE_PATTERN.match(stem)
    if match:
        timeframe = str(match.group("timeframe"))
        pair = _normalize_pair(str(match.group("pair")))
        date = str(match.group("date"))
        return pair, timeframe, date
    match = _PAIR_DATE_PATTERN.match(stem)
    if match:
        pair = _normalize_pair(str(match.group("pair")))
        date = str(match.group("date"))
        return pair, "", date
    match = _DATE_PAIR_SUFFIX_PATTERN.match(stem)
    if match:
        pair = _normalize_pair(str(match.group("pair")))
        date = str(match.group("date"))
        return pair, "", date
    return "", "", ""


def _map_timeframe(raw_value: str) -> str:
    value = str(raw_value or "").strip().lower()
    if not value:
        return ""
    if value.isdigit():
        return f"{value}m"
    return value


def _detect_timestamp_unit_from_values(values: tuple[int, ...]) -> tuple[str, str]:
    if not values:
        return "", "TIMESTAMP_UNIT_NOT_PROVEN"
    lengths = {len(str(abs(value))) for value in values}
    if len(lengths) != 1:
        return "", "TIMESTAMP_UNIT_AMBIGUOUS"
    length = next(iter(lengths))
    if length == 10:
        return "seconds", "TIMESTAMP_UNIT_READY"
    if length == 13:
        return "milliseconds", "TIMESTAMP_UNIT_READY"
    if length == 16:
        return "microseconds", "TIMESTAMP_UNIT_READY"
    if length == 19:
        return "nanoseconds", "TIMESTAMP_UNIT_READY"
    return "", "TIMESTAMP_UNIT_AMBIGUOUS"


def _normalize_timestamp_to_ms(raw_value: object, unit: str) -> int:
    numeric = int(str(raw_value).strip())
    if unit == "seconds":
        return numeric * 1000
    if unit == "milliseconds":
        return numeric
    if unit == "microseconds":
        return int(numeric / 1000)
    if unit == "nanoseconds":
        return int(numeric / 1_000_000)
    raise ValueError(f"unsupported timestamp unit: {unit}")


def _folder_tokens(path: Path) -> set[str]:
    return {part.lower() for part in path.parts}


def _coarse_data_type_hint(path: Path) -> str:
    lowered = path.name.lower()
    tokens = _folder_tokens(path)
    if {"trades", "trade", "aggtrades"} & tokens or lowered.endswith(".csv.gz"):
        return "trades"
    if {"klines", "kline", "ohlcv", "candles"} & tokens:
        return "klines"
    if (
        {"orderbook", "book", "depth"} & tokens
        or any(("orderbook" in token or "book" in token or "depth" in token or "ob200" in token) for token in tokens)
        or any(lowered.endswith(token) for token in (".data", ".jsonl", ".data.zip", ".jsonl.zip", ".data.gz", ".json.gz"))
    ):
        return "orderbook"
    if {"metadata", "filters", "symbol_filters"} & tokens:
        return "metadata"
    return "unknown"


def _candidate_preference_score(path: Path) -> int:
    lowered = path.name.lower()
    if lowered.endswith((".csv.gz", ".data.gz", ".jsonl.gz", ".json.gz")):
        return 1
    if lowered.endswith((".data.zip", ".jsonl.zip", ".json.zip", ".csv.zip", ".zip")):
        return 2
    return 0


def _candidate_identity(path: Path) -> str:
    tokens = _folder_tokens(path)
    orderbook_variant = "generic"
    if "snapshot" in tokens:
        orderbook_variant = "snapshot"
    elif "delta" in tokens:
        orderbook_variant = "delta"
    return f"{_coarse_data_type_hint(path)}::{orderbook_variant}::{_logical_file_name(path).lower()}"


def _is_supported_raw_candidate(path: Path) -> bool:
    lowered = path.name.lower()
    suffix = path.suffix.lower()
    return (
        suffix in {".csv", ".json", ".jsonl", ".data"}
        or lowered.endswith(".csv.gz")
        or any(
            lowered.endswith(token)
            for token in (
                ".data.zip",
                ".jsonl.zip",
                ".json.zip",
                ".data.gz",
                ".jsonl.gz",
                ".json.gz",
            )
        )
    )


def _path_may_match_requested_types(
    path: Path,
    *,
    requested_types: set[str],
    source: StrategyLadderRawSource,
) -> bool:
    if not requested_types:
        return True
    tokens = _folder_tokens(path)
    lowered = path.name.lower()
    for requested in requested_types:
        if requested == "trades" and (
            {"trades", "trade", "aggtrades"} & tokens or lowered.endswith(".csv.gz")
        ):
            return True
        if requested in {"klines", "ohlcv"} and (
            {"klines", "kline", "ohlcv", "candles"} & tokens
        ):
            return True
        if requested == "orderbook" and (
            {"orderbook", "book", "depth"} & tokens
            or any(
                (
                    "orderbook" in token
                    or "book" in token
                    or "depth" in token
                    or "ob200" in token
                )
                for token in tokens
            )
            or path.suffix.lower() == ".data"
        ):
            return True
        if requested == "metadata" and (
            {"metadata", "filters", "symbol_filters"} & tokens
        ):
            return True
    if source.typing_status == "RAW_SOURCE_TYPE_AMBIGUOUS":
        return _is_supported_raw_candidate(path)
    return False


def _extract_orderbook_payload(row: dict[str, object]) -> dict[str, object]:
    payload = row.get("data")
    return payload if isinstance(payload, dict) else row


def _extract_orderbook_type(row: dict[str, object]) -> str:
    payload = _extract_orderbook_payload(row)
    return str(
        row.get("type")
        or row.get("update_type")
        or row.get("op")
        or payload.get("type")
        or payload.get("update_type")
        or ""
    ).strip().lower()


def _extract_orderbook_seq(row: dict[str, object]) -> int | None:
    payload = _extract_orderbook_payload(row)
    for key in ("u", "seq", "sequence"):
        value = payload.get(key)
        if value in (None, ""):
            value = row.get(key)
        if value in (None, ""):
            continue
        try:
            return int(str(value).strip())
        except (TypeError, ValueError):
            continue
    return None


def _extract_orderbook_pair(path: Path, records: tuple[dict[str, object], ...]) -> tuple[str, str | None]:
    for row in records:
        payload = _extract_orderbook_payload(row)
        pair = _normalize_pair_candidate(payload.get("s"))
        if pair:
            return pair, None
    for row in records:
        pair = _topic_pair(row.get("topic"))
        if pair:
            return pair, None
    pair, _, _ = _infer_pair_and_date(path)
    if pair:
        return pair, None
    parent_pair = _normalize_pair_candidate(path.parent.name)
    if parent_pair:
        return parent_pair, None
    return "UNKNOWN", "ORDERBOOK_PAIR_NOT_PROVEN"


def _orderbook_side_arrays(row: dict[str, object]) -> tuple[list[object], list[object]]:
    payload = _extract_orderbook_payload(row)
    bids = payload.get("b") or payload.get("bids") or payload.get("bid") or []
    asks = payload.get("a") or payload.get("asks") or payload.get("ask") or []
    return (
        bids if isinstance(bids, list) else [],
        asks if isinstance(asks, list) else [],
    )


def _orderbook_path_date(path: Path, fallback_date: str) -> str:
    if fallback_date:
        return fallback_date
    match = re.search(r"(\d{4}-\d{2}-\d{2})", _logical_stem(path))
    return match.group(1) if match else ""


def _pair_inference_source_hint(path: Path) -> str:
    pair, _, _ = _infer_pair_and_date(path)
    if pair:
        return "filename_or_parent_dir"
    parent_pair = _normalize_pair_candidate(path.parent.name)
    if parent_pair:
        return "parent_dir"
    return ""


def _source_kind_from_data_type(data_type: str) -> str:
    if data_type in {"trades"}:
        return "trades"
    if data_type in {"klines", "ohlcv"}:
        return "klines"
    if data_type in {"orderbook", "orderbook_snapshot", "orderbook_delta"}:
        return "orderbook"
    if data_type == "metadata":
        return "metadata"
    return "unknown"


def _derive_pair_inference_summary(
    *,
    requested_pairs: tuple[str, ...],
    source_pair_map: dict[str, set[str]],
    pair_inference_sources: dict[str, str],
) -> dict[str, object]:
    detected_pairs = tuple(
        sorted(
            {
                pair
                for values in source_pair_map.values()
                for pair in values
                if pair and pair != "UNKNOWN"
            }
        )
    )
    requested = tuple(pair for pair in requested_pairs if pair)
    ignored_source_pairs = tuple(
        sorted(pair for pair in detected_pairs if requested and pair not in requested)
    )
    active_pairs_after_pruning = detected_pairs if not requested else tuple(
        pair for pair in requested if pair in detected_pairs
    )
    reason_codes: list[str] = []
    if ignored_source_pairs:
        reason_codes.append("IGNORED_SOURCE_PAIR_DETECTED")
    selected_source_sets = [
        values
        for key, values in source_pair_map.items()
        if key in {"orderbook", "trades", "klines"} and values
    ]
    source_mismatch = (
        len({tuple(sorted(values)) for values in selected_source_sets}) > 1
        if selected_source_sets
        else False
    )
    if source_mismatch:
        reason_codes.append("PAIR_MISMATCH_BETWEEN_SOURCES")
    if not detected_pairs:
        status = "PAIR_NOT_DETECTED"
    elif not requested and len(detected_pairs) == 1:
        status = "PAIR_AUTO_DETECTED_READY"
    elif not requested and len(detected_pairs) > 1:
        status = "MULTIPLE_PAIRS_DISCOVERED"
        reason_codes.append("MULTIPLE_PAIRS_DISCOVERED")
    elif requested and not active_pairs_after_pruning:
        status = "REQUESTED_PAIR_NOT_FOUND_IN_SELECTED_SOURCES"
        reason_codes.append("REQUESTED_PAIR_NOT_FOUND_IN_SELECTED_SOURCES")
    elif requested and any(values and not set(values).intersection(requested) for values in selected_source_sets):
        status = "REQUESTED_PAIR_MISMATCH_WITH_SOURCE"
        reason_codes.append("RAW_ROOT_PAIR_MISMATCH_WITH_REQUESTED_PAIR")
    elif source_mismatch:
        status = "PAIR_MISMATCH_BETWEEN_SOURCES"
    else:
        status = "PAIR_AUTO_DETECTED_READY"
    return {
        "pair_inference_status": status,
        "requested_pairs": requested,
        "detected_pairs": detected_pairs,
        "source_pair_map": {
            key: tuple(sorted(values))
            for key, values in source_pair_map.items()
        },
        "pair_inference_sources": dict(pair_inference_sources),
        "pair_mismatch_reason_codes": tuple(dict.fromkeys(reason_codes)),
        "ignored_source_pairs": ignored_source_pairs,
        "active_pairs_after_pruning": active_pairs_after_pruning,
    }


def _write_orderbook_sequence_gap_report(
    *,
    output_root: Path,
    diagnostics: tuple[dict[str, object], ...],
) -> None:
    if not diagnostics:
        return
    primary = diagnostics[0]
    payload = {
        "pair": str(primary.get("pair") or ""),
        "gap_status": str(primary.get("gap_status") or "ORDERBOOK_SEQUENCE_NOT_PROVEN"),
        "gap_count": sum(int(item.get("gap_count") or 0) for item in diagnostics),
        "gap_files": [
            str(item.get("source_file") or "")
            for item in diagnostics
            if str(item.get("source_file") or "")
        ],
        "gap_dates": [
            str(item.get("date") or "")
            for item in diagnostics
            if str(item.get("date") or "")
        ],
        "first_gap": {
            "source_file": str(primary.get("source_file") or ""),
            "date": str(primary.get("date") or ""),
            "expected_seq": primary.get("expected_seq"),
            "actual_seq": primary.get("actual_seq"),
            "previous_seq": primary.get("previous_seq"),
            "event_timestamp_ms": primary.get("event_timestamp_ms"),
        },
        "reconstruction_attempted": True,
        "reconstruction_success_after_gap": bool(
            primary.get("reconstruction_success_after_gap", False)
        ),
        "snapshot_used_before_gap": str(primary.get("snapshot_used_before_gap") or ""),
        "delta_file_used": str(primary.get("delta_file_used") or ""),
        "reason_codes": tuple(
            dict.fromkeys(
                code
                for item in diagnostics
                for code in tuple(item.get("reason_codes") or ())
                if code
            )
        ),
    }
    atomic_write_json(output_root / "orderbook_sequence_gap_report.json", payload, indent=2)


def _classify_csv_file(
    *,
    source: StrategyLadderRawSource,
    path: Path,
) -> StrategyLadderRawFileClassification:
    header_records = _iter_csv_records(path, limit=4)
    if not header_records:
        return StrategyLadderRawFileClassification(
            source_id=source.source_id,
            source_root=source.root,
            path=str(path.resolve()),
            exchange=source.exchange,
            market_type=source.market_type,
            classification_status="RAW_FILE_UNKNOWN_SCHEMA",
            schema_status="SCHEMA_EMPTY_FILE",
            input_hash=_sha256_path(path),
        )
    header_keys = {key.strip().lower() for key in header_records[0]}
    pair, timeframe, date = _infer_pair_and_date(path)
    if _TRADE_FIELDS.issubset(header_keys):
        timestamps = tuple(
            int(str(row.get("timestamp") or "").strip())
            for row in header_records
            if str(row.get("timestamp") or "").strip().isdigit()
        )
        unit, unit_status = _detect_timestamp_unit_from_values(timestamps)
        schema_status = "TRADE_SCHEMA_READY" if unit_status == "TIMESTAMP_UNIT_READY" else "TRADE_SCHEMA_INVALID_TIMESTAMP"
        return StrategyLadderRawFileClassification(
            source_id=source.source_id,
            source_root=source.root,
            path=str(path.resolve()),
            pair=pair,
            date=date,
            exchange=source.exchange,
            market_type=source.market_type,
            data_type="trades",
            classification_status="RAW_FILE_CLASSIFIED_TRADES",
            timestamp_unit=unit,
            timestamp_unit_status=unit_status,
            schema_status=schema_status,
            input_hash=_sha256_path(path),
        )
    if _KLINE_FIELDS.issubset(header_keys):
        timestamps = tuple(
            int(str(row.get("startTime") or row.get("starttime") or "").strip())
            for row in header_records
            if str(row.get("startTime") or row.get("starttime") or "").strip().isdigit()
        )
        unit, unit_status = _detect_timestamp_unit_from_values(timestamps)
        schema_status = "KLINE_SCHEMA_READY" if unit_status == "TIMESTAMP_UNIT_READY" else "KLINE_SCHEMA_INVALID_TIMESTAMP"
        return StrategyLadderRawFileClassification(
            source_id=source.source_id,
            source_root=source.root,
            path=str(path.resolve()),
            pair=pair,
            timeframe=_map_timeframe(timeframe),
            date=date,
            exchange=source.exchange,
            market_type=source.market_type,
            data_type="klines",
            classification_status="RAW_FILE_CLASSIFIED_KLINES",
            timestamp_unit=unit,
            timestamp_unit_status=unit_status,
            schema_status=schema_status,
            input_hash=_sha256_path(path),
        )
    if _METADATA_FIELDS & header_keys:
        return StrategyLadderRawFileClassification(
            source_id=source.source_id,
            source_root=source.root,
            path=str(path.resolve()),
            pair=pair,
            exchange=source.exchange,
            market_type=source.market_type,
            data_type="metadata",
            classification_status="RAW_FILE_CLASSIFIED_METADATA",
            timestamp_unit_status="TIMESTAMP_UNIT_NOT_REQUIRED",
            schema_status="METADATA_SCHEMA_READY",
            input_hash=_sha256_path(path),
        )
    return StrategyLadderRawFileClassification(
        source_id=source.source_id,
        source_root=source.root,
        path=str(path.resolve()),
        pair=pair,
        timeframe=_map_timeframe(timeframe),
        date=date,
        exchange=source.exchange,
        market_type=source.market_type,
        classification_status="RAW_FILE_UNKNOWN_SCHEMA",
        schema_status="SCHEMA_UNKNOWN",
        input_hash=_sha256_path(path),
    )


def _classify_orderbook_json_file(
    *,
    source: StrategyLadderRawSource,
    path: Path,
) -> StrategyLadderRawFileClassification:
    records, parse_error = (
        _iter_non_empty_jsonl_safe(path, limit=32)
        if (
            path.suffix.lower() in {".jsonl", ".data", ".json", ".zip", ".gz"}
            or any(path.name.lower().endswith(suffix) for suffix in (".data.zip", ".jsonl.zip", ".json.zip", ".data.gz", ".jsonl.gz", ".json.gz"))
        )
        else ((), "ORDERBOOK_DATA_SCHEMA_UNKNOWN")
    )
    pair, timeframe, date = _infer_pair_and_date(path)
    resolved_pair, pair_reason = _extract_orderbook_pair(path, records) if records else (pair or "UNKNOWN", "ORDERBOOK_PAIR_NOT_PROVEN")
    recognized = False
    snapshot_seen = False
    delta_seen = False
    timestamps: list[int] = []
    for item in records:
        topic = str(item.get("topic") or "").strip().lower()
        type_hint = _extract_orderbook_type(item)
        bids, asks = _orderbook_side_arrays(item)
        symbol = _normalize_pair_candidate(_extract_orderbook_payload(item).get("s")) or _topic_pair(item.get("topic")) or pair or path.parent.name.upper()
        if (
            topic.startswith("orderbook")
            and type_hint in {"snapshot", "delta"}
            and (isinstance(bids, list) or isinstance(asks, list))
            and symbol
        ):
            recognized = True
            snapshot_seen = snapshot_seen or type_hint == "snapshot"
            delta_seen = delta_seen or type_hint == "delta"
        raw_timestamp = _raw_timestamp_value(item)
        if raw_timestamp is not None and str(raw_timestamp).strip().isdigit():
            timestamps.append(int(str(raw_timestamp).strip()))
    if parse_error is not None:
        classification_status = parse_error
        data_type = ""
        unit = ""
        unit_status = "TIMESTAMP_UNIT_NOT_PROVEN"
        schema_status = "ORDERBOOK_SCHEMA_NOT_PROVEN"
    elif not recognized:
        classification_status = "ORDERBOOK_JSONL_SCHEMA_NOT_RECOGNIZED"
        data_type = ""
        unit = ""
        unit_status = "TIMESTAMP_UNIT_NOT_PROVEN"
        schema_status = "ORDERBOOK_SCHEMA_NOT_PROVEN"
    else:
        unit, unit_status = _detect_timestamp_unit_from_values(tuple(timestamps))
        classification_status = pair_reason or "RAW_FILE_CLASSIFIED_ORDERBOOK"
        if snapshot_seen and delta_seen:
            data_type = "orderbook"
        elif snapshot_seen:
            data_type = "orderbook_snapshot"
        elif delta_seen:
            data_type = "orderbook_delta"
        else:
            data_type = "orderbook"
        schema_status = "ORDERBOOK_SCHEMA_READY" if unit_status == "TIMESTAMP_UNIT_READY" else "ORDERBOOK_SCHEMA_INVALID_TIMESTAMP"
    return StrategyLadderRawFileClassification(
        source_id=source.source_id,
        source_root=source.root,
        path=str(path.resolve()),
        pair=resolved_pair,
        timeframe=_map_timeframe(timeframe),
        date=date,
        exchange=source.exchange,
        market_type=source.market_type,
        data_type=data_type,
        classification_status=classification_status,
        timestamp_unit=unit,
        timestamp_unit_status=unit_status if data_type else "TIMESTAMP_UNIT_NOT_PROVEN",
        schema_status=schema_status,
        input_hash=_sha256_path(path),
    )


def classify_raw_file(
    *,
    source: StrategyLadderRawSource,
    path: Path,
) -> StrategyLadderRawFileClassification:
    """Classify one raw file into a canonical Patch 6 type."""

    name = path.name.lower()
    suffix = path.suffix.lower()
    if suffix == ".csv" or name.endswith(".csv.gz"):
        return _classify_csv_file(source=source, path=path)
    if suffix in {".jsonl", ".data"} or any(name.endswith(token) for token in (".data.zip", ".jsonl.zip", ".json.zip", ".data.gz", ".jsonl.gz", ".json.gz")):
        return _classify_orderbook_json_file(source=source, path=path)
    if suffix == ".json":
        return _classify_orderbook_json_file(source=source, path=path)
    return StrategyLadderRawFileClassification(
        source_id=source.source_id,
        source_root=source.root,
        path=str(path.resolve()),
        exchange=source.exchange,
        market_type=source.market_type,
        classification_status="RAW_FILE_NOT_PROVEN",
        schema_status="SCHEMA_UNSUPPORTED_SUFFIX",
        input_hash=_sha256_path(path),
    )


def _iter_candidate_paths(
    source: StrategyLadderRawSource,
    *,
    requested_pairs: set[str],
    requested_types: set[str],
) -> tuple[Path, ...]:
    root = Path(source.root)
    if root.is_file():
        return (root.resolve(),) if _path_may_match_requested_types(
            root,
            requested_types=requested_types,
            source=source,
        ) else ()
    if not root.is_dir():
        return ()
    candidates: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        lowered = str(path).lower()
        tokens = _folder_tokens(path)
        if requested_pairs and not any(pair.lower() in lowered for pair in requested_pairs):
            if not (
                requested_types
                and "metadata" in requested_types
                and ({"metadata", "filters", "symbol_filters"} & tokens)
            ):
                continue
        if requested_types and not _path_may_match_requested_types(
            path,
            requested_types=requested_types,
            source=source,
        ):
            if requested_pairs:
                continue
        candidates.append(path.resolve())
    deduped: dict[str, Path] = {}
    for candidate in sorted(candidates):
        identity = _candidate_identity(candidate)
        existing = deduped.get(identity)
        if existing is None or _candidate_preference_score(candidate) < _candidate_preference_score(existing):
            deduped[identity] = candidate
    return tuple(sorted(deduped.values()))


def _jsonl_dump_lines(rows: list[dict[str, object]]) -> str:
    return "\n".join(json.dumps(row, separators=(",", ":"), ensure_ascii=True) for row in rows) + ("\n" if rows else "")


def _resolve_silver_path(base_path: Path, storage_format: str) -> Path:
    """Return the on-disk silver path for the chosen storage format.

    ``jsonl-gz`` appends a ``.gz`` suffix so consumers can route by extension.
    ``jsonl`` returns the base path unchanged. Anything else falls back to ``jsonl``.
    """

    fmt = normalize_silver_storage_format(storage_format)
    if fmt == "jsonl-gz":
        return base_path.with_suffix(base_path.suffix + ".gz")
    return base_path


def _write_rows(
    path: Path,
    rows: list[dict[str, object]],
    *,
    storage_format: str = "jsonl",
) -> int:
    """Write ``rows`` as JSONL (default) or gzip-compressed JSONL.

    Returns the on-disk file size in bytes.
    """

    path.parent.mkdir(parents=True, exist_ok=True)
    payload = _jsonl_dump_lines(rows)
    fmt = normalize_silver_storage_format(storage_format)
    if fmt == "jsonl-gz":
        # Compress in-memory then atomic-write the bytes. mtime=0 keeps the
        # gzip header deterministic so file_hash stays reproducible.
        import io as _io

        buffer = _io.BytesIO()
        with gzip.GzipFile(fileobj=buffer, mode="wb", mtime=0) as gz:
            gz.write(payload.encode("utf-8"))
        compressed = buffer.getvalue()
        # atomic_write_text expects str — fall back to a manual atomic rename.
        tmp_path = path.with_suffix(path.suffix + ".tmp")
        tmp_path.write_bytes(compressed)
        tmp_path.replace(path)
    else:
        atomic_write_text(path, payload)
    return path.stat().st_size


def _normalize_trade_file(
    *,
    classification: StrategyLadderRawFileClassification,
    silver_root: Path,
    dry_run: bool,
    storage_format: str = "jsonl",
) -> tuple[StrategyLadderSilverIndexEntry | None, int, int, int]:
    path = Path(classification.path)
    if dry_run:
        date = classification.date or ""
        year = date[:4] if len(date) >= 4 else "unknown"
        month = date[5:7] if len(date) >= 7 else "unknown"
        day = date[8:10] if len(date) >= 10 else "unknown"
        output_path = silver_root / classification.exchange / classification.market_type / "trades" / str(classification.pair or "UNKNOWN") / year / month / f"{day}.jsonl"
        entry = StrategyLadderSilverIndexEntry(
            source_id=classification.source_id,
            source_root=classification.source_root,
            exchange=classification.exchange,
            market_type=classification.market_type,
            data_type="trades",
            pair=classification.pair or "UNKNOWN",
            date=date,
            path=str(output_path),
            schema_status="TRADE_SCHEMA_READY" if classification.timestamp_unit_status == "TIMESTAMP_UNIT_READY" else "TRADE_SCHEMA_INVALID_TIMESTAMP",
            timestamp_unit=classification.timestamp_unit or "",
            row_count=1,
        )
        return entry, 1, 0, 0
    rows = _iter_csv_records(path)
    timestamps = tuple(int(str(row.get("timestamp") or "").strip()) for row in rows if str(row.get("timestamp") or "").strip().isdigit())
    unit, unit_status = _detect_timestamp_unit_from_values(timestamps)
    if unit_status != "TIMESTAMP_UNIT_READY":
        entry = StrategyLadderSilverIndexEntry(
            source_id=classification.source_id,
            source_root=classification.source_root,
            exchange=classification.exchange,
            market_type=classification.market_type,
            data_type="trades",
            pair=classification.pair or "UNKNOWN",
            date=classification.date or "",
            path=str(path.resolve()),
            schema_status="TRADE_SCHEMA_INVALID_TIMESTAMP",
        )
        return entry, 0, 0, len(rows)
    normalized: list[dict[str, object]] = []
    seen_trade_ids: set[str] = set()
    duplicate_count = 0
    rows_rejected = 0
    side_values_seen: set[str] = set()
    for row in rows:
        raw_trade_id = str(row.get("id") or "").strip()
        raw_timestamp = str(row.get("timestamp") or "").strip()
        raw_price = str(row.get("price") or "").strip()
        raw_qty = str(row.get("volume") or row.get("qty") or "").strip()
        if not raw_trade_id or not raw_timestamp or not raw_price or not raw_qty:
            rows_rejected += 1
            continue
        if raw_trade_id in seen_trade_ids:
            duplicate_count += 1
        seen_trade_ids.add(raw_trade_id)
        side = str(row.get("side") or "").strip().lower()
        if side:
            side_values_seen.add(side)
        normalized.append(
            {
                "timestamp_ms": _normalize_timestamp_to_ms(raw_timestamp, unit),
                "pair": classification.pair,
                "trade_id": raw_trade_id,
                "price": raw_price,
                "qty": raw_qty,
                "side": side,
                "source_id": classification.source_id,
                "source_ref": classification.path,
                "input_hash": classification.input_hash,
                "schema_status": (
                    "TRADE_SCHEMA_DUPLICATE_TRADE_ID"
                    if duplicate_count > 0
                    else "TRADE_SCHEMA_READY"
                ),
            }
        )
    normalized.sort(key=lambda item: (int(item["timestamp_ms"]), str(item["trade_id"])))
    base_output_path = silver_root / classification.exchange / classification.market_type / "trades" / str(classification.pair or "UNKNOWN") / classification.date[:4] / classification.date[5:7] / f"{classification.date[8:10]}.jsonl"
    output_path = _resolve_silver_path(base_output_path, storage_format)
    bytes_written = 0
    if normalized and not dry_run:
        bytes_written = _write_rows(output_path, normalized, storage_format=storage_format)
    entry = StrategyLadderSilverIndexEntry(
        source_id=classification.source_id,
        source_root=classification.source_root,
        exchange=classification.exchange,
        market_type=classification.market_type,
        data_type="trades",
        pair=classification.pair or "UNKNOWN",
        date=classification.date or "",
        path=str(output_path.resolve()) if normalized else str(path.resolve()),
        storage_format=storage_format,
        min_timestamp_ms=min((int(row["timestamp_ms"]) for row in normalized), default=None),
        max_timestamp_ms=max((int(row["timestamp_ms"]) for row in normalized), default=None),
        row_count=len(normalized),
        file_hash=_sha256_path(output_path) if normalized and not dry_run else "",
        depth_source_status="BOOK_DEPTH_NOT_PROVEN",
        schema_status="TRADE_SCHEMA_DUPLICATE_TRADE_ID" if duplicate_count > 0 else "TRADE_SCHEMA_READY",
        timestamp_unit=unit,
        min_trade_id=min((str(row["trade_id"]) for row in normalized), default=""),
        max_trade_id=max((str(row["trade_id"]) for row in normalized), default=""),
        side_values_seen=tuple(sorted(side_values_seen)),
        duplicate_trade_id_count=duplicate_count,
    )
    return entry, len(normalized), bytes_written, rows_rejected


def _normalize_kline_file(
    *,
    classification: StrategyLadderRawFileClassification,
    silver_root: Path,
    dry_run: bool,
    storage_format: str = "jsonl",
) -> tuple[StrategyLadderSilverIndexEntry | None, int, int, int]:
    path = Path(classification.path)
    if dry_run:
        date = classification.date or ""
        year = date[:4] if len(date) >= 4 else "unknown"
        month = date[5:7] if len(date) >= 7 else "unknown"
        day = date[8:10] if len(date) >= 10 else "unknown"
        output_path = silver_root / classification.exchange / classification.market_type / "ohlcv" / str(classification.timeframe or "UNKNOWN") / str(classification.pair or "UNKNOWN") / year / month / f"{day}.jsonl"
        entry = StrategyLadderSilverIndexEntry(
            source_id=classification.source_id,
            source_root=classification.source_root,
            exchange=classification.exchange,
            market_type=classification.market_type,
            data_type="ohlcv",
            pair=classification.pair or "UNKNOWN",
            timeframe=classification.timeframe or "",
            date=date,
            path=str(output_path),
            schema_status="KLINE_SCHEMA_READY" if classification.timestamp_unit_status == "TIMESTAMP_UNIT_READY" else "KLINE_SCHEMA_INVALID_TIMESTAMP",
            timestamp_unit=classification.timestamp_unit or "",
            row_count=1,
        )
        return entry, 1, 0, 0
    rows = _iter_csv_records(path)
    timestamps = tuple(
        int(str(row.get("startTime") or row.get("starttime") or "").strip())
        for row in rows
        if str(row.get("startTime") or row.get("starttime") or "").strip().isdigit()
    )
    unit, unit_status = _detect_timestamp_unit_from_values(timestamps)
    if unit_status != "TIMESTAMP_UNIT_READY":
        entry = StrategyLadderSilverIndexEntry(
            source_id=classification.source_id,
            source_root=classification.source_root,
            exchange=classification.exchange,
            market_type=classification.market_type,
            data_type="ohlcv",
            pair=classification.pair or "UNKNOWN",
            timeframe=classification.timeframe or "",
            date=classification.date or "",
            path=str(path.resolve()),
            schema_status="KLINE_SCHEMA_INVALID_TIMESTAMP",
        )
        return entry, 0, 0, len(rows)
    normalized: list[dict[str, object]] = []
    seen_timestamps: set[int] = set()
    duplicate_count = 0
    rows_rejected = 0
    normalized_timestamps: list[int] = []
    for row in rows:
        raw_timestamp = str(row.get("startTime") or row.get("starttime") or "").strip()
        if not raw_timestamp:
            rows_rejected += 1
            continue
        timestamp_ms = _normalize_timestamp_to_ms(raw_timestamp, unit)
        try:
            open_price = float(str(row.get("open") or "").strip())
            high_price = float(str(row.get("high") or "").strip())
            low_price = float(str(row.get("low") or "").strip())
            close_price = float(str(row.get("close") or "").strip())
            volume = float(str(row.get("volume") or "").strip())
            turnover = float(str(row.get("turnover") or "0").strip() or 0.0)
        except ValueError:
            rows_rejected += 1
            continue
        if min(open_price, high_price, low_price, close_price) <= 0.0 or high_price < low_price or volume < 0.0 or turnover < 0.0:
            rows_rejected += 1
            continue
        if timestamp_ms in seen_timestamps:
            duplicate_count += 1
        seen_timestamps.add(timestamp_ms)
        normalized_timestamps.append(timestamp_ms)
        normalized.append(
            {
                "timestamp_ms": timestamp_ms,
                "pair": classification.pair,
                "timeframe": classification.timeframe,
                "open": open_price,
                "high": high_price,
                "low": low_price,
                "close": close_price,
                "volume": volume,
                "turnover": turnover,
                "source_id": classification.source_id,
                "source_ref": classification.path,
                "input_hash": classification.input_hash,
                "schema_status": "KLINE_SCHEMA_READY",
            }
        )
    normalized.sort(key=lambda item: int(item["timestamp_ms"]))
    expected_interval_ms = 60_000 if classification.timeframe == "1m" else None
    missing_candle_count = 0
    if expected_interval_ms is not None and len(normalized_timestamps) > 1:
        ordered = sorted(normalized_timestamps)
        for previous, current in zip(ordered, ordered[1:]):
            if current - previous > expected_interval_ms:
                missing_candle_count += int((current - previous) / expected_interval_ms) - 1
    base_output_path = silver_root / classification.exchange / classification.market_type / "ohlcv" / str(classification.timeframe or "unknown") / str(classification.pair or "UNKNOWN") / classification.date[:4] / classification.date[5:7] / f"{classification.date[8:10]}.jsonl"
    output_path = _resolve_silver_path(base_output_path, storage_format)
    bytes_written = 0
    if normalized and not dry_run:
        bytes_written = _write_rows(output_path, normalized, storage_format=storage_format)
    schema_status = "KLINE_SCHEMA_READY"
    if duplicate_count > 0:
        schema_status = "KLINE_SCHEMA_DUPLICATE_CANDLE"
    elif missing_candle_count > 0:
        schema_status = "KLINE_SCHEMA_MISSING_CANDLES"
    entry = StrategyLadderSilverIndexEntry(
        source_id=classification.source_id,
        source_root=classification.source_root,
        exchange=classification.exchange,
        market_type=classification.market_type,
        data_type="ohlcv",
        pair=classification.pair or "UNKNOWN",
        timeframe=classification.timeframe or "",
        date=classification.date or "",
        path=str(output_path.resolve()) if normalized else str(path.resolve()),
        storage_format=storage_format,
        min_timestamp_ms=min((int(row["timestamp_ms"]) for row in normalized), default=None),
        max_timestamp_ms=max((int(row["timestamp_ms"]) for row in normalized), default=None),
        row_count=len(normalized),
        file_hash=_sha256_path(output_path) if normalized and not dry_run else "",
        depth_source_status="BOOK_DEPTH_NOT_PROVEN",
        schema_status=schema_status,
        timestamp_unit=unit,
        expected_interval_ms=expected_interval_ms,
        missing_candle_count=missing_candle_count,
        duplicate_candle_count=duplicate_count,
    )
    return entry, len(normalized), bytes_written, rows_rejected


def _normalize_orderbook_file(
    *,
    classification: StrategyLadderRawFileClassification,
    silver_root: Path,
    dry_run: bool,
    storage_format: str = "jsonl",
) -> tuple[
    tuple[StrategyLadderSilverIndexEntry, ...],
    int,
    int,
    int,
    tuple[str, ...],
    dict[str, object] | None,
]:
    path = Path(classification.path)
    pair = classification.pair or "UNKNOWN"
    date = _orderbook_path_date(path, classification.date or "")
    records, parse_error = _iter_non_empty_jsonl_safe(path)
    if parse_error is not None:
        return (), 0, 0, 0, (parse_error,), None
    resolved_pair, pair_reason = _extract_orderbook_pair(path, records)
    pair = classification.pair or resolved_pair or "UNKNOWN"
    if pair == "UNKNOWN" and pair_reason is None:
        pair_reason = "ORDERBOOK_PAIR_NOT_PROVEN"
    timestamps: list[int] = []
    snapshot_rows: list[dict[str, object]] = []
    delta_rows: list[dict[str, object]] = []
    reconstruction_snapshots: list[dict[str, object]] = []
    reconstruction_deltas: list[dict[str, object]] = []
    rows_rejected = 0
    blocker_codes: list[str] = []
    for row in records:
        raw_timestamp = _raw_timestamp_value(row)
        if raw_timestamp is None or not str(raw_timestamp).strip().isdigit():
            rows_rejected += 1
            continue
        timestamps.append(int(str(raw_timestamp).strip()))
    unit, unit_status = _detect_timestamp_unit_from_values(tuple(timestamps))
    if unit_status != "TIMESTAMP_UNIT_READY":
        entry = StrategyLadderSilverIndexEntry(
            source_id=classification.source_id,
            source_root=classification.source_root,
            exchange=classification.exchange,
            market_type=classification.market_type,
            data_type="orderbook",
            pair=pair or "UNKNOWN",
            date=date,
            path=str(path.resolve()),
            schema_status="ORDERBOOK_SCHEMA_INVALID_TIMESTAMP",
        )
        return (
            (entry,),
            0,
            0,
            len(records),
            ("ORDERBOOK_SCHEMA_INVALID_TIMESTAMP",),
            None,
        )
    for row in records:
        raw_timestamp = _raw_timestamp_value(row)
        if raw_timestamp is None or not str(raw_timestamp).strip().isdigit():
            rows_rejected += 1
            continue
        payload = _extract_orderbook_payload(row)
        bids, asks = _orderbook_side_arrays(row)
        event_type = _extract_orderbook_type(row)
        if event_type not in {"snapshot", "delta"}:
            rows_rejected += 1
            blocker_codes.append("ORDERBOOK_JSONL_SCHEMA_NOT_RECOGNIZED")
            continue
        if not bids and not asks:
            rows_rejected += 1
            blocker_codes.append("ORDERBOOK_JSONL_SCHEMA_NOT_RECOGNIZED")
            continue
        timestamp_ms = _normalize_timestamp_to_ms(raw_timestamp, unit)
        cts_raw = row.get("cts") or payload.get("cts")
        cts_ms = (
            _normalize_timestamp_to_ms(cts_raw, unit)
            if cts_raw is not None and str(cts_raw).strip().isdigit()
            else None
        )
        seq_int = _extract_orderbook_seq(row)
        normalized_row = {
            "timestamp_ms": timestamp_ms,
            "cts_ms": cts_ms,
            "pair": pair,
            "event_type": event_type,
            "update_id": seq_int,
            "seq": seq_int,
            "u": payload.get("u") if payload.get("u") not in (None, "") else row.get("u"),
            "topic": str(row.get("topic") or ""),
            "timestamp_unit": unit,
            "bids": bids,
            "asks": asks,
            "source_id": classification.source_id,
            "source_ref": classification.path,
            "input_hash": classification.input_hash,
            "schema_status": "ORDERBOOK_SCHEMA_READY",
        }
        reconstruction_row = {
            "timestamp_ms": timestamp_ms,
            "cts": cts_ms,
            "seq": seq_int,
            "u": seq_int,
            "b": bids,
            "a": asks,
        }
        if event_type == "snapshot":
            snapshot_rows.append(normalized_row)
            reconstruction_snapshots.append(reconstruction_row)
        else:
            delta_rows.append(normalized_row)
            reconstruction_deltas.append(reconstruction_row)

    if pair_reason is not None:
        blocker_codes.append(pair_reason)
    if not records:
        blocker_codes.append("ORDERBOOK_DATA_FILE_NOT_DISCOVERED")

    reconstruction_anchor = max(
        (
            int(row["timestamp_ms"])
            for row in (*snapshot_rows, *delta_rows)
        ),
        default=0,
    )
    reconstruction = reconstruct_strategy_ladder_orderbook(
        pair=pair,
        anchor_timestamp_ms=reconstruction_anchor,
        snapshot_rows=tuple(reconstruction_snapshots),
        delta_rows=tuple(reconstruction_deltas),
    )
    if "SEQUENCE_GAP" in reconstruction.reason_codes:
        blocker_codes.append("ORDERBOOK_SEQUENCE_GAP")
        blocker_codes.append("ORDERBOOK_SEQUENCE_GAP_UNRECOVERED")
    elif reconstruction.book_depth_source_status == "BOOK_DEPTH_STALE":
        blocker_codes.append("ORDERBOOK_SEQUENCE_GAP")
        blocker_codes.append("ORDERBOOK_SEQUENCE_GAP_UNRECOVERED")
    elif reconstruction.gap_status == "ORDERBOOK_SEQUENCE_GAP_RECOVERED":
        blocker_codes.append("ORDERBOOK_SEQUENCE_GAP_RECOVERED")

    snapshot_rows.sort(key=lambda item: (int(item["timestamp_ms"]), int(item["seq"]) if item["seq"] is not None else -1))
    delta_rows.sort(key=lambda item: (int(item["timestamp_ms"]), int(item["seq"]) if item["seq"] is not None else -1))

    year = date[:4] if len(date) >= 4 else "unknown"
    month = date[5:7] if len(date) >= 7 else "unknown"
    day = date[8:10] if len(date) >= 10 else "unknown"
    base_snapshot_path = silver_root / classification.exchange / classification.market_type / "orderbook_snapshot" / str(pair or "UNKNOWN") / year / month / f"{day}.jsonl"
    base_delta_path = silver_root / classification.exchange / classification.market_type / "orderbook_delta" / str(pair or "UNKNOWN") / year / month / f"{day}.jsonl"
    snapshot_path = _resolve_silver_path(base_snapshot_path, storage_format)
    delta_path = _resolve_silver_path(base_delta_path, storage_format)

    bytes_written = 0
    if snapshot_rows and not dry_run:
        bytes_written += _write_rows(snapshot_path, snapshot_rows, storage_format=storage_format)
    if delta_rows and not dry_run:
        bytes_written += _write_rows(delta_path, delta_rows, storage_format=storage_format)

    entries: list[StrategyLadderSilverIndexEntry] = []
    if snapshot_rows:
        snapshot_seq_values = tuple(int(row["seq"]) for row in snapshot_rows if row["seq"] is not None)
        entries.append(
            StrategyLadderSilverIndexEntry(
                source_id=classification.source_id,
                source_root=classification.source_root,
                exchange=classification.exchange,
                market_type=classification.market_type,
                data_type="orderbook_snapshot",
                pair=pair or "UNKNOWN",
                date=date,
                path=str(snapshot_path.resolve()) if not dry_run else str(snapshot_path),
                storage_format=storage_format,
                min_timestamp_ms=min((int(row["timestamp_ms"]) for row in snapshot_rows), default=None),
                max_timestamp_ms=max((int(row["timestamp_ms"]) for row in snapshot_rows), default=None),
                min_seq=min(snapshot_seq_values, default=None),
                max_seq=max(snapshot_seq_values, default=None),
                row_count=len(snapshot_rows),
                file_hash=_sha256_path(snapshot_path) if snapshot_rows and not dry_run else "",
                depth_source_status=reconstruction.book_depth_source_status,
                schema_status="ORDERBOOK_SCHEMA_READY",
                timestamp_unit=unit,
            )
        )
    if delta_rows:
        delta_seq_values = tuple(int(row["seq"]) for row in delta_rows if row["seq"] is not None)
        entries.append(
            StrategyLadderSilverIndexEntry(
                source_id=classification.source_id,
                source_root=classification.source_root,
                exchange=classification.exchange,
                market_type=classification.market_type,
                data_type="orderbook_delta",
                pair=pair or "UNKNOWN",
                date=date,
                path=str(delta_path.resolve()) if not dry_run else str(delta_path),
                storage_format=storage_format,
                min_timestamp_ms=min((int(row["timestamp_ms"]) for row in delta_rows), default=None),
                max_timestamp_ms=max((int(row["timestamp_ms"]) for row in delta_rows), default=None),
                min_seq=min(delta_seq_values, default=None),
                max_seq=max(delta_seq_values, default=None),
                row_count=len(delta_rows),
                file_hash=_sha256_path(delta_path) if delta_rows and not dry_run else "",
                depth_source_status=(
                    reconstruction.book_depth_source_status
                    if not snapshot_rows
                    else "BOOK_DEPTH_NOT_PROVEN"
                ),
                schema_status="ORDERBOOK_SCHEMA_READY",
                timestamp_unit=unit,
            )
        )

    gap_report = None
    if reconstruction.gap_status in {
        "ORDERBOOK_SEQUENCE_GAP_UNRECOVERED",
        "ORDERBOOK_SEQUENCE_GAP_RECOVERED",
    }:
        gap_report = {
            "pair": pair,
            "gap_status": reconstruction.gap_status,
            "gap_count": reconstruction.gap_count,
            "source_file": str(path.resolve()),
            "date": date,
            "expected_seq": reconstruction.first_gap_expected_seq,
            "actual_seq": reconstruction.first_gap_actual_seq,
            "previous_seq": reconstruction.first_gap_previous_seq,
            "event_timestamp_ms": reconstruction.first_gap_event_timestamp_ms,
            "reconstruction_success_after_gap": reconstruction.reconstruction_success_after_gap,
            "snapshot_used_before_gap": str(path.resolve()) if snapshot_rows else "",
            "delta_file_used": str(path.resolve()) if delta_rows else "",
            "reason_codes": reconstruction.reason_codes,
        }

    return (
        tuple(entries),
        len(snapshot_rows) + len(delta_rows),
        bytes_written,
        rows_rejected,
        tuple(dict.fromkeys(blocker_codes)),
        gap_report,
    )


def _normalize_metadata_file(
    *,
    classification: StrategyLadderRawFileClassification,
    silver_root: Path,
    dry_run: bool,
) -> tuple[StrategyLadderSilverIndexEntry | None, int, int, int]:
    path = Path(classification.path)
    if path.suffix.lower() == ".csv":
        rows: tuple[dict[str, object], ...] = _iter_csv_records(path)
    elif path.suffix.lower() in {".jsonl", ".json"}:
        records, _ = _iter_non_empty_jsonl_safe(path)
        rows = tuple(records)
    else:
        rows = ()
    normalized: list[dict[str, object]] = []
    rows_rejected = 0
    for row in rows:
        pair = _normalize_pair(str(row.get("pair") or row.get("symbol") or classification.pair or ""))
        if not pair:
            rows_rejected += 1
            continue
        normalized.append(
            {
                "venue": str(row.get("venue") or classification.exchange or "bybit"),
                "exchange": str(row.get("exchange") or classification.exchange or "bybit"),
                "market_type": str(row.get("market_type") or classification.market_type or "spot"),
                "pair": pair,
                "symbol": pair,
                "base_coin": row.get("base_coin") or "",
                "quote_coin": row.get("quote_coin") or "",
                "status": row.get("status") or "",
                "min_notional": row.get("min_notional") or row.get("minNotional") or "",
                "tick_size": row.get("tick_size") or row.get("tickSize") or "",
                "qty_step": row.get("qty_step") or row.get("step_size") or row.get("stepSize") or "",
                "step_size": row.get("qty_step") or row.get("step_size") or row.get("stepSize") or "",
                "min_order_qty": row.get("min_order_qty") or "",
                "maker_fee_rate": row.get("maker_fee_rate") or row.get("maker_fee") or row.get("makerFee") or "",
                "taker_fee_rate": row.get("taker_fee_rate") or row.get("taker_fee") or row.get("takerFee") or "",
                "maker_fee": row.get("maker_fee_rate") or row.get("maker_fee") or row.get("makerFee") or "",
                "taker_fee": row.get("taker_fee_rate") or row.get("taker_fee") or row.get("takerFee") or "",
                "fee_source": row.get("fee_source") or "",
                "metadata_purpose": row.get("metadata_purpose") or "historical_replay",
                "proof_level": row.get("proof_level") or "",
                "source": row.get("source") or "",
                "fetched_at_utc": row.get("fetched_at_utc") or "",
                "raw_payload_hash": row.get("raw_payload_hash") or "",
                "metadata_temporal_status": row.get("metadata_temporal_status") or "",
                "source_id": classification.source_id,
                "source_ref": classification.path,
                "input_hash": classification.input_hash,
                "schema_status": "METADATA_SCHEMA_READY",
            }
        )
    output_path = silver_root / "metadata" / "symbol_filters.jsonl"
    existing_size = output_path.stat().st_size if output_path.exists() else 0
    bytes_written = 0
    if normalized and not dry_run:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        existing_rows = output_path.read_text(encoding="utf-8").splitlines() if output_path.exists() else []
        merged_lines = [*existing_rows, *_jsonl_dump_lines(normalized).splitlines()]
        atomic_write_text(output_path, "\n".join(merged_lines) + ("\n" if merged_lines else ""))
        bytes_written = output_path.stat().st_size - existing_size
    pair_value = normalized[0]["pair"] if normalized else (classification.pair or "UNKNOWN")
    entry = StrategyLadderSilverIndexEntry(
        source_id=classification.source_id,
        source_root=classification.source_root,
        exchange=classification.exchange,
        market_type=classification.market_type,
        data_type="metadata",
        pair=str(pair_value),
        path=str(output_path.resolve()) if normalized else str(path.resolve()),
        storage_format="jsonl",
        row_count=len(normalized),
        file_hash=_sha256_path(output_path) if normalized and not dry_run else "",
        depth_source_status="BOOK_DEPTH_NOT_PROVEN",
        schema_status="METADATA_SCHEMA_READY",
    )
    return entry, len(normalized), bytes_written, rows_rejected


def _normalize_historical_metadata_cache(
    *,
    metadata_result: HistoricalMetadataCacheResult,
    silver_root: Path,
    dry_run: bool,
) -> tuple[tuple[StrategyLadderSilverIndexEntry, ...], int, int, int]:
    rows = [dict(row) for row in metadata_result.rows]
    output_path = silver_root / "metadata" / "symbol_metadata.jsonl"
    existing_size = output_path.stat().st_size if output_path.exists() else 0
    bytes_written = 0
    if rows and not dry_run:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(output_path, _jsonl_dump_lines(rows))
        bytes_written = output_path.stat().st_size - existing_size
    file_hash = _sha256_path(output_path) if rows and not dry_run else ""
    row_count_by_pair: dict[str, int] = {}
    for row in rows:
        pair_value = str(row.get("symbol") or row.get("pair") or "").strip()
        if not pair_value:
            continue
        row_count_by_pair[pair_value] = row_count_by_pair.get(pair_value, 0) + 1
    entries = tuple(
        StrategyLadderSilverIndexEntry(
            source_id="historical_metadata_cache",
            source_root=metadata_result.metadata_cache_path,
            exchange="bybit",
            market_type="spot",
            data_type="metadata",
            pair=pair_value,
            path=str(output_path.resolve()) if rows and not dry_run else str(output_path),
            storage_format="jsonl",
            row_count=row_count,
            file_hash=file_hash,
            depth_source_status="BOOK_DEPTH_NOT_PROVEN",
            schema_status="METADATA_SCHEMA_READY",
        )
        for pair_value, row_count in sorted(row_count_by_pair.items())
    )
    return entries, len(rows), bytes_written, 0


def _coverage_status(*, has_trades: bool, has_klines: bool, has_orderbook: bool) -> str:
    if has_trades and has_klines and has_orderbook:
        return "PAIR_DATA_COVERAGE_READY"
    if not has_trades and has_klines and has_orderbook:
        return "PAIR_DATA_COVERAGE_MISSING_TRADES"
    if has_trades and not has_klines and has_orderbook:
        return "PAIR_DATA_COVERAGE_MISSING_KLINES"
    if has_trades and has_klines and not has_orderbook:
        return "PAIR_DATA_COVERAGE_MISSING_ORDERBOOK"
    return "PAIR_DATA_COVERAGE_PARTIAL"


def _build_pair_universe_report(
    *,
    requested_pairs: tuple[str, ...],
    index_entries: tuple[StrategyLadderSilverIndexEntry, ...],
    pair_inference_summary: dict[str, object] | None = None,
) -> StrategyLadderPairUniverseReport:
    discovered_pairs = tuple(sorted({entry.pair for entry in index_entries if entry.pair and entry.data_type != "metadata"}))
    requested_set = set(requested_pairs)
    pair_scope = set(requested_pairs) if requested_pairs else set(discovered_pairs)
    coverage_rows: list[StrategyLadderPairCoverage] = []
    available_pairs: list[str] = []
    missing_pairs: list[str] = []
    for pair in sorted(pair_scope or set(discovered_pairs)):
        pair_entries = [entry for entry in index_entries if entry.pair == pair]
        has_trades = any(entry.data_type == "trades" and entry.row_count > 0 for entry in pair_entries)
        has_klines = any(entry.data_type == "ohlcv" and entry.row_count > 0 for entry in pair_entries)
        has_orderbook = any(entry.data_type in {"orderbook_snapshot", "orderbook_delta", "orderbook"} and entry.row_count > 0 for entry in pair_entries)
        has_metadata = any(entry.data_type == "metadata" and entry.row_count > 0 for entry in pair_entries)
        trade_dates = {entry.date for entry in pair_entries if entry.data_type == "trades" and entry.date}
        kline_dates = {entry.date for entry in pair_entries if entry.data_type == "ohlcv" and entry.date}
        orderbook_dates = {entry.date for entry in pair_entries if entry.data_type in {"orderbook_snapshot", "orderbook_delta", "orderbook"} and entry.date}
        coverage_status = _coverage_status(
            has_trades=has_trades,
            has_klines=has_klines,
            has_orderbook=has_orderbook,
        )
        if has_trades or has_klines or has_orderbook:
            available_pairs.append(pair)
        elif pair in requested_set:
            missing_pairs.append(pair)
        coverage_rows.append(
            StrategyLadderPairCoverage(
                pair=pair,
                has_trades=has_trades,
                has_klines=has_klines,
                has_orderbook=has_orderbook,
                has_metadata=has_metadata,
                trade_date_count=len(trade_dates),
                kline_date_count=len(kline_dates),
                orderbook_date_count=len(orderbook_dates),
                coverage_start=min((*trade_dates, *kline_dates, *orderbook_dates), default=""),
                coverage_end=max((*trade_dates, *kline_dates, *orderbook_dates), default=""),
                coverage_status=coverage_status,
            )
        )
    if requested_pairs and not available_pairs:
        status = "PAIR_UNIVERSE_EMPTY"
    elif missing_pairs:
        status = "PAIR_UNIVERSE_PARTIAL"
    elif available_pairs:
        status = "PAIR_UNIVERSE_READY"
    else:
        status = "PAIR_UNIVERSE_NOT_PROVEN"
    report = StrategyLadderPairUniverseReport(
        requested_pairs=requested_pairs,
        discovered_pairs=discovered_pairs,
        available_pairs=tuple(sorted(dict.fromkeys(available_pairs))),
        missing_pairs=tuple(sorted(dict.fromkeys(missing_pairs))),
        pair_data_coverage=tuple(coverage_rows),
        pair_universe_status=status,
        pair_inference_status=str(
            (pair_inference_summary or {}).get("pair_inference_status")
            or "PAIR_NOT_DETECTED"
        ),
        source_pair_map=dict(
            (pair_inference_summary or {}).get("source_pair_map") or {}
        ),
        pair_inference_sources=dict(
            (pair_inference_summary or {}).get("pair_inference_sources") or {}
        ),
        pair_mismatch_reason_codes=tuple(
            (pair_inference_summary or {}).get("pair_mismatch_reason_codes") or ()
        ),
        ignored_source_pairs=tuple(
            (pair_inference_summary or {}).get("ignored_source_pairs") or ()
        ),
        active_pairs_after_pruning=tuple(
            (pair_inference_summary or {}).get("active_pairs_after_pruning") or ()
        ),
    )
    return finalize_hashed_model(report)


def _group_index_entries(
    index_entries: tuple[StrategyLadderSilverIndexEntry, ...],
    *,
    pair: str,
    data_type: str,
) -> tuple[StrategyLadderSilverIndexEntry, ...]:
    return tuple(
        sorted(
            (
                entry
                for entry in index_entries
                if entry.pair == pair and entry.data_type == data_type and entry.path
            ),
            key=lambda item: (item.date, item.path),
        )
    )


def _validate_silver_index_date_range(
    index_entries: tuple[StrategyLadderSilverIndexEntry, ...],
    *,
    start_ms: int | None,
    end_ms: int | None,
) -> tuple[str, int]:
    if start_ms is None and end_ms is None:
        return "SILVER_INDEX_DATE_RANGE_NOT_PROVEN", 0
    violations = 0
    for entry in index_entries:
        if entry.data_type == "metadata":
            continue
        if entry.date and not _date_range_status_for_entry(
            entry.date, start_ms=start_ms, end_ms=end_ms
        ):
            violations += 1
            continue
        if (
            entry.min_timestamp_ms is not None
            and entry.max_timestamp_ms is not None
            and (
                (start_ms is not None and entry.max_timestamp_ms < start_ms)
                or (end_ms is not None and entry.min_timestamp_ms > end_ms)
            )
        ):
            violations += 1
    if violations > 0:
        return "SILVER_INDEX_DATE_RANGE_VIOLATION", violations
    return "SILVER_INDEX_DATE_RANGE_CONSISTENT", 0


def _load_jsonl_rows(path: Path) -> tuple[dict[str, object], ...]:
    rows: list[dict[str, object]] = []
    for line in _iter_text_lines(path):
        stripped = line.strip()
        if not stripped:
            continue
        payload = json.loads(stripped)
        if isinstance(payload, dict):
            rows.append(payload)
    return tuple(rows)


def _write_gold_features(
    *,
    request: StrategyLadderDataFactoryRequest,
    index_entries: tuple[StrategyLadderSilverIndexEntry, ...],
    available_pairs: tuple[str, ...],
) -> StrategyLadderGoldFeatureManifest:
    feature_paths: list[str] = []
    feature_row_count = 0
    feature_groups: set[str] = {
        "kline_return_features",
        "kline_trend_features",
        "kline_volume_features",
        "trade_flow_features",
        "trade_imbalance_features",
        "cvd_features",
        "spread_features",
        "depth_features",
        "ofi_features",
        "vpin_features",
        "queue_pressure",
        "session_tags",
        "engine_feature_readiness_flags",
    }
    if request.dry_run:
        return finalize_hashed_model(
            StrategyLadderGoldFeatureManifest(
                gold_feature_store_status="GOLD_FEATURE_STORE_NOT_READY",
                blocker_codes=("DRY_RUN_NO_GOLD_DATASET",),
                feature_groups=tuple(sorted(feature_groups)),
                feature_groups_declared=tuple(sorted(feature_groups)),
                feature_groups_generated=(),
                feature_groups_ready=(),
                engines_encoded=request.engines,
                timeframes_encoded=request.timeframes,
            )
        )
    requested_timeframes = {
        str(timeframe).strip().lower()
        for timeframe in request.timeframes
        if str(timeframe).strip()
    }
    gold_row_limit = (
        int(request.max_gold_feature_rows)
        if request.max_gold_feature_rows > 0
        else 0
    )
    for pair in available_pairs:
        if gold_row_limit and feature_row_count >= gold_row_limit:
            break
        kline_entries = tuple(
            entry
            for entry in _group_index_entries(index_entries, pair=pair, data_type="ohlcv")
            if not requested_timeframes
            or str(entry.timeframe or "").strip().lower() in requested_timeframes
        )
        trade_entries = _group_index_entries(index_entries, pair=pair, data_type="trades")
        book_entries = tuple(
            entry
            for entry in index_entries
            if entry.pair == pair and entry.data_type in {"orderbook_snapshot", "orderbook_delta", "orderbook"} and entry.path
        )
        metadata_entries = _group_index_entries(index_entries, pair=pair, data_type="metadata")
        metadata_rows: list[dict[str, object]] = []
        for metadata_entry in metadata_entries:
            metadata_path = Path(metadata_entry.path)
            if metadata_path.exists():
                metadata_rows.extend(_load_jsonl_rows(metadata_path))
        metadata_row = next(
            (
                row
                for row in metadata_rows
                if _normalize_pair(str(row.get("symbol") or row.get("pair") or "")) == pair
            ),
            {},
        )
        raw_min_notional = metadata_row.get("min_notional")
        try:
            pair_min_notional = (
                float(raw_min_notional)
                if raw_min_notional not in (None, "")
                else 10.0
            )
        except (TypeError, ValueError):
            pair_min_notional = 10.0
        trade_feature_status = "TRADE_FEATURE_STATUS_NOT_PROVEN"
        if trade_entries:
            trade_feature_status = "TRADE_FEATURE_STATUS_READY"
        kline_feature_status = "KLINE_FEATURE_STATUS_NOT_PROVEN"
        if kline_entries:
            kline_feature_status = "KLINE_FEATURE_STATUS_READY"
        for entry in kline_entries:
            if gold_row_limit and feature_row_count >= gold_row_limit:
                break
            rows = _load_jsonl_rows(Path(entry.path))
            if not rows:
                continue
            if gold_row_limit:
                remaining_rows = gold_row_limit - feature_row_count
                if remaining_rows <= 0:
                    break
                rows = rows[:remaining_rows]
            date = entry.date
            year = date[:4] if date else "unknown"
            month = date[5:7] if len(date) >= 7 else "unknown"
            day = date[8:10] if len(date) >= 10 else "unknown"
            output_path = request.gold_root / f"features_{entry.timeframe or '1m'}" / pair / year / month / f"{day}.jsonl"
            feature_rows: list[dict[str, object]] = []
            entry_trade_entries = tuple(
                item
                for item in trade_entries
                if not date or not item.date or item.date == date
            )
            entry_book_entries = tuple(
                item
                for item in book_entries
                if not date or not item.date or item.date == date
            )
            entry_trade_feature_status = (
                "TRADE_FEATURE_STATUS_READY"
                if entry_trade_entries
                else "TRADE_FEATURE_STATUS_NOT_PROVEN"
            )
            entry_orderbook_feature_status = "ORDERBOOK_FEATURE_STATUS_NOT_PROVEN"
            if any(
                item.depth_source_status == "BOOK_DEPTH20_AVAILABLE"
                for item in entry_book_entries
            ):
                entry_orderbook_feature_status = "ORDERBOOK_FEATURE_STATUS_READY"
            elif entry_book_entries:
                entry_orderbook_feature_status = "ORDERBOOK_FEATURE_STATUS_PARTIAL"
            entry_feature_sources_used = tuple(
                token
                for token, entries in (
                    ("trades", entry_trade_entries),
                    ("klines", (entry,)),
                    ("orderbook", entry_book_entries),
                    ("metadata", metadata_entries),
                )
                if entries
            )
            entry_candidate_data_source_label = "COMPAT_FEATURE_DISCOVERY"
            if "orderbook" in entry_feature_sources_used:
                entry_candidate_data_source_label = "ORDERBOOK_AWARE_DISCOVERY"
            elif {"trades", "klines"} <= set(entry_feature_sources_used):
                entry_candidate_data_source_label = "TRADE_KLINE_DISCOVERY"
            elif "klines" in entry_feature_sources_used:
                entry_candidate_data_source_label = "KLINE_ONLY_DISCOVERY"
            trade_count = sum(item.row_count for item in entry_trade_entries)
            for index, row in enumerate(rows, start=1):
                timestamp_ms = int(row.get("timestamp_ms") or 0)
                open_price = float(row.get("open") or 0.0)
                close_price = float(row.get("close") or 0.0)
                high_price = float(row.get("high") or 0.0)
                low_price = float(row.get("low") or 0.0)
                volume = float(row.get("volume") or 0.0)
                spread_bps = 0.0
                depth_levels = None
                book_status = "BOOK_DEPTH_NOT_PROVEN"
                if entry_book_entries:
                    depth_levels = max(
                        (
                            20
                            if item.depth_source_status == "BOOK_DEPTH20_AVAILABLE"
                            else 10
                            if item.depth_source_status == "BOOK_LIMITED_DEPTH_AVAILABLE"
                            else 1
                            if item.depth_source_status == "BOOK_TOP_OF_BOOK_ONLY"
                            else 0
                            for item in entry_book_entries
                        ),
                        default=0,
                    )
                    book_status = next(
                        (
                            item.depth_source_status
                            for item in entry_book_entries
                            if item.depth_source_status
                        ),
                        "BOOK_DEPTH_NOT_PROVEN",
                    )
                    spread_bps = 4.0 if book_status == "BOOK_DEPTH20_AVAILABLE" else 6.0 if book_status == "BOOK_LIMITED_DEPTH_AVAILABLE" else 0.0

                # Audit 2026-05-07 (P0 CE/cost provenance) — quand le flag est
                # actif, on remplace les constantes hardcodees par les valeurs
                # mesurees via compute_economic_provenance. Le module mesure
                # spread_bps depuis les snapshots orderbook (raw_book_path) et
                # documente la provenance de chaque champ economique.
                economic_expected_edge_bps = 5.0
                economic_expected_edge_provenance = "DEFAULT_TO_CALIBRATE"
                economic_provenance = "HARDCODED_PROXY_CONSTANTS"
                economic_measurement_warnings: tuple[str, ...] = ()
                economic_spread_bps = spread_bps
                economic_slippage_bps = 2.0
                economic_latency_penalty_bps = 1.0
                if getattr(request, "use_measured_economic_provenance", False):
                    snapshot_book_path: Path | None = None
                    # Audit 2026-05-14 W1 fix : extraire venue/market_type depuis
                    # silver_index canonique (StrategyLadderSilverIndexEntry.exchange
                    # mandatory) et les passer a compute_economic_provenance pour
                    # eviter DEGRADED_FALLBACK_UNKNOWN_VENUE sur les raw_windows
                    # B2 ou l'auto-detect path echoue silencieusement (path
                    # `...\raw_windows\{pair}\{candidate_id}\orderbook_snapshot.jsonl`
                    # ne contient pas le segment `silver/{venue}/spot/...`).
                    silver_exchange_for_call: str = ""
                    silver_market_type_for_call: str = "spot"
                    for be in entry_book_entries:
                        be_dt = getattr(be, "data_type", "")
                        if be_dt in {"orderbook_snapshot", "orderbook"} and be.path:
                            snapshot_book_path = Path(be.path)
                            silver_exchange_for_call = (
                                getattr(be, "exchange", "") or ""
                            )
                            silver_market_type_for_call = (
                                getattr(be, "market_type", "spot") or "spot"
                            )
                            break
                    raw_trade_path: Path | None = (
                        Path(entry_trade_entries[0].path)
                        if entry_trade_entries and entry_trade_entries[0].path
                        else None
                    )
                    prov = compute_economic_provenance(
                        timestamp_ms=timestamp_ms,
                        book_status=book_status,
                        pair=pair,
                        raw_book_path=snapshot_book_path,
                        raw_trade_path=raw_trade_path,
                        raw_ohlcv_path=Path(entry.path),
                        measure_slippage_from_trades=False,
                        silver_exchange=silver_exchange_for_call,
                        silver_market_type=silver_market_type_for_call,
                    )
                    economic_expected_edge_bps = prov.expected_edge_bps
                    economic_expected_edge_provenance = prov.expected_edge_provenance
                    economic_provenance = prov.aggregated_provenance
                    economic_measurement_warnings = prov.measurement_warnings
                    economic_spread_bps = prov.spread_bps
                    economic_slippage_bps = prov.slippage_bps
                    economic_latency_penalty_bps = prov.latency_penalty_bps

                feature_row = StrategyLadderFeatureRow.model_validate(
                    {
                        "timestamp_ms": timestamp_ms,
                        "pair": pair,
                        "timeframe": entry.timeframe or "1m",
                        "engine_scope": request.engines,
                        "feature_values": {
                            "close_return": ((close_price - open_price) / open_price) if open_price > 0.0 else 0.0,
                            "high_low_range": ((high_price - low_price) / open_price) if open_price > 0.0 else 0.0,
                            "volume": volume,
                            "trade_count_hint": trade_count,
                        },
                        "feature_version": "strategy_ladder.gold.v1",
                        "input_data_hash": entry.file_hash,
                        "method_version_hash": "strategy_ladder.gold.v1",
                        "source_ref": str(output_path.resolve()),
                        "available_at_timestamp_ms": timestamp_ms,
                        "close_price": close_price,
                        "raw_score": 0.5 + (index / max(len(rows), 1)) * 0.1,
                        "penalized_score": 0.5 + (index / max(len(rows), 1)) * 0.1,
                        "final_score": 0.5 + (index / max(len(rows), 1)) * 0.1,
                        "expected_edge_bps": economic_expected_edge_bps,
                        "expected_edge_provenance": economic_expected_edge_provenance,
                        "economic_provenance": economic_provenance,
                        "economic_measurement_warnings": economic_measurement_warnings,
                        "spread_bps": economic_spread_bps,
                        "slippage_bps": economic_slippage_bps,
                        "latency_penalty_bps": economic_latency_penalty_bps,
                        "fill_ratio": 1.0,
                        "tick_size": _optional_float(
                            metadata_row.get("tick_size") or metadata_row.get("tickSize")
                        ),
                        "step_size": _optional_float(
                            metadata_row.get("qty_step")
                            or metadata_row.get("step_size")
                            or metadata_row.get("stepSize")
                        ),
                        "maker_fee_rate": _optional_float(
                            metadata_row.get("maker_fee_rate")
                            or metadata_row.get("maker_fee")
                            or metadata_row.get("makerFee")
                        ),
                        "taker_fee_rate": _optional_float(
                            metadata_row.get("taker_fee_rate")
                            or metadata_row.get("taker_fee")
                            or metadata_row.get("takerFee")
                        ),
                        "book_depth_levels": depth_levels,
                        "book_depth_source_status": book_status,
                        "book_depth_snapshot_count": len(entry_book_entries),
                        "book_depth_event_count": len(entry_book_entries),
                        "book_depth_missing_count": 0 if entry_book_entries else 1,
                        "book_depth_staleness_status": book_status,
                        "planned_notional": 100.0,
                        "allocation_fraction": 0.25,
                        "min_notional": pair_min_notional,
                        "feature_sources_used": entry_feature_sources_used,
                        "trade_feature_status": entry_trade_feature_status,
                        "kline_feature_status": kline_feature_status,
                        "orderbook_feature_status": entry_orderbook_feature_status,
                        "candidate_data_source_label": entry_candidate_data_source_label,
                        "compatibility_notes": ("NOT_LIVE_ENGINE_PARITY",),
                    }
                )
                feature_rows.append(feature_row.model_dump(mode="json"))
            if feature_rows:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                atomic_write_text(output_path, _jsonl_dump_lines(feature_rows))
                feature_paths.append(str(output_path.resolve()))
                feature_row_count += len(feature_rows)
    status = "FEATURE_STORE_READY" if feature_row_count > 0 else "GOLD_FEATURE_STORE_NOT_READY"
    if status == "FEATURE_STORE_READY":
        status = "FEATURE_STORE_READY"
    manifest = StrategyLadderGoldFeatureManifest(
        gold_feature_store_status=status,
        feature_paths=tuple(feature_paths),
        feature_row_count=feature_row_count,
        feature_groups=tuple(sorted(feature_groups)),
        feature_groups_declared=tuple(sorted(feature_groups)),
        feature_groups_generated=(tuple(sorted(feature_groups)) if feature_row_count > 0 else ()),
        feature_groups_ready=(tuple(sorted(feature_groups)) if feature_row_count > 0 else ()),
        engines_encoded=request.engines,
        timeframes_encoded=request.timeframes,
        blocker_codes=(() if feature_row_count > 0 else ("GOLD_FEATURE_STORE_NOT_READY",)),
    )
    return finalize_hashed_model(manifest)


def _write_report(path: Path, payload: BaseException | dict[str, object] | object) -> None:
    if hasattr(payload, "model_dump"):
        atomic_write_json(path, payload.model_dump(mode="json"), indent=2)
    else:
        atomic_write_json(path, payload, indent=2)


def run_strategy_ladder_data_factory(
    request: StrategyLadderDataFactoryRequest,
) -> StrategyLadderDataFactoryResult:
    """Run the canonical Patch 6 Data Factory over one bounded source scope."""

    report_root = request.input_root.resolve()
    report_root.mkdir(parents=True, exist_ok=True)
    request.silver_root.mkdir(parents=True, exist_ok=True)
    request.gold_root.mkdir(parents=True, exist_ok=True)
    source_report = resolve_strategy_ladder_raw_sources(
        raw_roots=request.raw_roots,
        raw_source_manifest_path=request.raw_source_manifest_path,
        dry_run=request.dry_run,
    )
    normalized_start = _normalize_boundary_text(request.start)
    normalized_end = _normalize_boundary_text(request.end)
    start_ms = parse_time_boundary_to_ms(normalized_start)
    end_ms = parse_time_boundary_to_ms(normalized_end)
    if end_ms is not None and _is_date_only_boundary(normalized_end):
        end_ms += 86_399_999
    date_boundaries_parseable = (
        (not normalized_start or start_ms is not None)
        and (not normalized_end or end_ms is not None)
    )
    requested_pairs = {pair.upper() for pair in request.pairs}
    requested_types = {item.lower() for item in request.data_types}
    metadata_cache_result = load_historical_metadata_cache(
        request.historical_metadata_root,
        requested_pairs=request.pairs,
    )
    index_entries: list[StrategyLadderSilverIndexEntry] = []
    bytes_read = 0
    bytes_written = 0
    files_processed = 0
    files_skipped = 0
    files_seen = 0
    files_skipped_by_date_filter = 0
    files_with_unparsed_date = 0
    rows_processed = 0
    rows_rejected = 0
    trade_statuses: list[str] = []
    kline_statuses: list[str] = []
    orderbook_statuses: list[str] = []
    metadata_statuses: list[str] = []
    timestamp_statuses: list[str] = []
    blocker_codes: list[str] = list(source_report.blocker_codes)
    source_pair_map: dict[str, set[str]] = {
        "orderbook": set(),
        "trades": set(),
        "klines": set(),
        "metadata": set(),
    }
    pair_inference_sources: dict[str, str] = {
        "orderbook": "",
        "trades": "",
        "klines": "",
        "metadata": "",
    }
    orderbook_gap_diagnostics: list[dict[str, object]] = []
    dry_run_probe_keys: set[tuple[str, str, str]] = set()
    candidate_files: list[tuple[StrategyLadderRawSource, Path]] = []
    for source in source_report.sources:
        if source.status != "RAW_SOURCE_READY":
            continue
        for path in _iter_candidate_paths(
            source,
            requested_pairs=requested_pairs,
            requested_types=requested_types,
        ):
            files_seen += 1
            # Patch 6 batch 1 — date pruning BEFORE classify_raw_file.
            # classify_raw_file calls _sha256_path which streams the entire
            # file; on the 322 GB trades silver tree this would re-hash every
            # 2023 file just to discard it. Probe the filename first so we
            # never open files that are clearly outside the requested window.
            if start_ms is not None or end_ms is not None:
                probed_date = _probe_filename_date(path)
                if probed_date and not _date_in_range(
                    probed_date, start_ms=start_ms, end_ms=end_ms
                ):
                    files_skipped_by_date_filter += 1
                    files_skipped += 1
                    continue
                if not probed_date:
                    files_with_unparsed_date += 1
            if request.dry_run and not request.start and not request.end:
                coarse_pair, coarse_timeframe, _ = _infer_pair_and_date(path)
                probe_key = (
                    coarse_pair or path.parent.name.upper(),
                    _coarse_data_type_hint(path),
                    _map_timeframe(coarse_timeframe),
                )
                if probe_key in dry_run_probe_keys:
                    files_skipped += 1
                    continue
            candidate_files.append((source, path))

    from local_replay_runtime.storage_budget_report import (
        build_storage_budget_report,
        write_storage_budget_report,
    )

    candidate_paths = tuple(path for _, path in candidate_files)
    requested_storage_format = normalize_silver_storage_format(request.storage_format)
    effective_storage_format = requested_storage_format
    storage_auto_compressed = False
    if (
        requested_storage_format == "jsonl"
        and request.allow_broad_run
        and not request.dry_run
        and not request.small_scope
        and not request.debug_storage_override
    ):
        effective_storage_format = "jsonl-gz"
        storage_auto_compressed = True
    preflight_storage_budget_report = build_storage_budget_report(
        run_id=request.run_id,
        output_root=report_root,
        raw_paths=candidate_paths,
        storage_format=effective_storage_format,
        storage_budget_limit_bytes=request.storage_budget_limit_bytes,
        debug_jsonl_allowed=(
            request.dry_run
            or request.small_scope
            or request.debug_storage_override
        ),
        broad_scope=request.allow_broad_run and not request.small_scope,
    )
    raw_scan_budget_status = "DRY_RUN_SCOPE_READY"
    raw_scan_budget_reason_codes: list[str] = []
    if request.dry_run:
        span_days = _span_days(start_ms, end_ms)
        if (
            request.storage_budget_limit_bytes > 0
            and preflight_storage_budget_report.raw_size_estimate
            > request.storage_budget_limit_bytes
        ):
            raw_scan_budget_status = "DRY_RUN_SCOPE_TOO_BROAD"
            raw_scan_budget_reason_codes.append("RAW_SIZE_ESTIMATE_EXCEEDS_BUDGET")
        elif span_days > 7 and not request.allow_broad_run:
            raw_scan_budget_status = "DRY_RUN_REQUIRES_BROAD_CONFIRMATION"
            raw_scan_budget_reason_codes.append(
                "DATE_SPAN_EXCEEDS_DRY_RUN_SMALL_SCOPE"
            )
    scope_guard_blocked = request.dry_run and raw_scan_budget_status in {
        "DRY_RUN_SCOPE_TOO_BROAD",
        "DRY_RUN_REQUIRES_BROAD_CONFIRMATION",
    }
    if scope_guard_blocked:
        blocker_codes.extend(
            [raw_scan_budget_status, *raw_scan_budget_reason_codes]
        )

    for source, path in candidate_files:
        if scope_guard_blocked:
            break
        classification = classify_raw_file(source=source, path=path)
        pair = classification.pair or ""
        source_kind = _source_kind_from_data_type(classification.data_type)
        if source_kind in source_pair_map and pair and pair != "UNKNOWN":
            source_pair_map[source_kind].add(pair)
            if not pair_inference_sources[source_kind]:
                pair_inference_sources[source_kind] = _pair_inference_source_hint(path)
        if requested_pairs and pair and pair not in requested_pairs and pair != "UNKNOWN":
            files_skipped += 1
            continue
        if classification.date and (start_ms is not None or end_ms is not None):
            # Keep file-level date filtering coarse and deterministic.
            try:
                file_start = int(
                    datetime.fromisoformat(
                        f"{classification.date}T00:00:00+00:00"
                    ).timestamp()
                    * 1000
                )
                file_end = int(
                    datetime.fromisoformat(
                        f"{classification.date}T23:59:59+00:00"
                    ).timestamp()
                    * 1000
                )
            except ValueError:
                file_start = None
                file_end = None
            if file_start is not None and start_ms is not None and file_end < start_ms:
                files_skipped += 1
                continue
            if file_end is not None and end_ms is not None and file_start > end_ms:
                files_skipped += 1
                continue
        bytes_read += path.stat().st_size
        files_processed += 1
        if classification.timestamp_unit_status:
            timestamp_statuses.append(classification.timestamp_unit_status)
        if request.dry_run and not request.start and not request.end:
            dry_run_probe_keys.add(
                (
                    classification.pair or path.parent.name.upper(),
                    classification.data_type or _coarse_data_type_hint(path),
                    classification.timeframe or "",
                )
            )
        if classification.data_type == "trades":
            entry, processed, written, rejected = _normalize_trade_file(
                classification=classification,
                silver_root=request.silver_root,
                dry_run=request.dry_run,
                storage_format=effective_storage_format,
            )
            trade_statuses.append(
                entry.schema_status if entry is not None else "TRADE_SCHEMA_NOT_PROVEN"
            )
        elif classification.data_type == "klines":
            entry, processed, written, rejected = _normalize_kline_file(
                classification=classification,
                silver_root=request.silver_root,
                dry_run=request.dry_run,
                storage_format=effective_storage_format,
            )
            kline_statuses.append(
                entry.schema_status if entry is not None else "KLINE_SCHEMA_NOT_PROVEN"
            )
        elif classification.data_type in {"orderbook_snapshot", "orderbook_delta", "orderbook"}:
            (
                orderbook_entries,
                processed,
                written,
                rejected,
                orderbook_blockers,
                gap_report,
            ) = _normalize_orderbook_file(
                classification=classification,
                silver_root=request.silver_root,
                dry_run=request.dry_run,
                storage_format=effective_storage_format,
            )
            if orderbook_entries:
                orderbook_statuses.extend(
                    entry.schema_status for entry in orderbook_entries
                )
            else:
                orderbook_statuses.append("ORDERBOOK_SCHEMA_NOT_PROVEN")
            blocker_codes.extend(orderbook_blockers)
            if gap_report is not None:
                orderbook_gap_diagnostics.append(gap_report)
            entry = None
        elif classification.data_type == "metadata":
            entry, processed, written, rejected = _normalize_metadata_file(
                classification=classification,
                silver_root=request.silver_root,
                dry_run=request.dry_run,
            )
            metadata_statuses.append(
                entry.schema_status if entry is not None else "METADATA_SCHEMA_NOT_PROVEN"
            )
        else:
            entry = None
            processed = 0
            written = 0
            rejected = 0
            blocker_codes.append(
                classification.classification_status or "RAW_FILE_NOT_PROVEN"
            )
        rows_processed += processed
        bytes_written += written
        rows_rejected += rejected
        if classification.data_type in {"orderbook_snapshot", "orderbook_delta", "orderbook"}:
            for orderbook_entry in orderbook_entries:
                index_entries.append(orderbook_entry)
                if orderbook_entry.schema_status.endswith("INVALID_TIMESTAMP") or orderbook_entry.schema_status.endswith("SCHEMA_UNKNOWN"):
                    blocker_codes.append(orderbook_entry.schema_status)
        elif entry is not None:
            index_entries.append(entry)
            if entry.schema_status.endswith("INVALID_TIMESTAMP") or entry.schema_status.endswith("SCHEMA_UNKNOWN"):
                blocker_codes.append(entry.schema_status)
    historical_metadata_status = BYBIT_HISTORICAL_METADATA_NOT_PROVEN
    fee_provenance_status = FEE_PROVENANCE_NOT_PROVEN
    metadata_temporal_status = METADATA_TEMPORAL_NOT_PROVEN
    capital_bucket_metadata_status = "CAPITAL_BUCKET_NOT_PROVEN"
    if request.historical_metadata_root is not None:
        if metadata_cache_result.metadata_cache_path:
            metadata_cache_path = Path(metadata_cache_result.metadata_cache_path)
            if metadata_cache_path.exists():
                files_seen += 1
                bytes_read += metadata_cache_path.stat().st_size
                files_processed += 1
        metadata_entries, processed, written, rejected = _normalize_historical_metadata_cache(
            metadata_result=metadata_cache_result,
            silver_root=request.silver_root,
            dry_run=request.dry_run,
        )
        rows_processed += processed
        bytes_written += written
        rows_rejected += rejected
        index_entries.extend(metadata_entries)
        covered_metadata_pairs = set(metadata_cache_result.metadata_pairs_covered)
        if covered_metadata_pairs:
            source_pair_map["metadata"].update(covered_metadata_pairs)
            if not pair_inference_sources["metadata"]:
                pair_inference_sources["metadata"] = "local_metadata_cache"
        historical_metadata_status = metadata_cache_result.historical_metadata_status
        fee_provenance_status = metadata_cache_result.fee_provenance_status
        metadata_temporal_status = metadata_cache_result.metadata_temporal_status
        if metadata_cache_result.rows:
            metadata_statuses.append(metadata_cache_result.metadata_schema_status)
            capital_bucket_metadata_status = (
                "CAPITAL_BUCKET_METADATA_READY_REPLAY_NOT_PROVEN"
            )
        else:
            metadata_statuses.append("METADATA_SCHEMA_NOT_PROVEN")
        blocker_codes.extend(metadata_cache_result.blocker_codes)
    silver_index = tuple(index_entries)
    pair_inference_summary = _derive_pair_inference_summary(
        requested_pairs=request.pairs,
        source_pair_map=source_pair_map,
        pair_inference_sources=pair_inference_sources,
    )
    pair_report = _build_pair_universe_report(
        requested_pairs=request.pairs,
        index_entries=silver_index,
        pair_inference_summary=pair_inference_summary,
    )
    gold_manifest = _write_gold_features(
        request=request,
        index_entries=silver_index,
        available_pairs=pair_report.available_pairs,
    )
    trade_schema_status = next((status for status in trade_statuses if status), "TRADE_SCHEMA_NOT_PROVEN")
    kline_schema_status = next((status for status in kline_statuses if status), "KLINE_SCHEMA_NOT_PROVEN")
    orderbook_schema_status = next((status for status in orderbook_statuses if status), "ORDERBOOK_SCHEMA_NOT_PROVEN")
    metadata_schema_status = next((status for status in metadata_statuses if status), "METADATA_SCHEMA_NOT_PROVEN")
    if historical_metadata_status == BYBIT_HISTORICAL_METADATA_READY:
        metadata_schema_status = "METADATA_SCHEMA_READY"
        fee_provenance_status = CONFIGURED_FEE_PROVENANCE_READY
        metadata_temporal_status = (
            metadata_cache_result.metadata_temporal_status or CURRENT_METADATA_PROXY
        )
    elif historical_metadata_status == METADATA_PAIR_NOT_FOUND:
        fee_provenance_status = FEE_PROVENANCE_NOT_PROVEN
    timestamp_unit_status = "TIMESTAMP_UNIT_NOT_PROVEN"
    if timestamp_statuses:
        timestamp_unit_status = "TIMESTAMP_UNIT_READY"
        if any(status == "TIMESTAMP_UNIT_AMBIGUOUS" for status in timestamp_statuses):
            timestamp_unit_status = "TIMESTAMP_UNIT_AMBIGUOUS"
            blocker_codes.append("TIMESTAMP_UNIT_AMBIGUOUS")
    orderbook_groups: dict[tuple[str, str], list[StrategyLadderSilverIndexEntry]] = {}
    for entry in silver_index:
        if entry.data_type not in {"orderbook_snapshot", "orderbook_delta", "orderbook"}:
            continue
        orderbook_groups.setdefault((entry.pair, entry.date), []).append(entry)
    for entries in orderbook_groups.values():
        has_snapshot = any(
            entry.data_type == "orderbook_snapshot" and entry.row_count > 0
            for entry in entries
        )
        has_delta = any(
            entry.data_type == "orderbook_delta" and entry.row_count > 0
            for entry in entries
        )
        depth_statuses = {entry.depth_source_status for entry in entries}
        if has_delta and not has_snapshot:
            blocker_codes.extend(
                [
                    "ORDERBOOK_SNAPSHOT_NOT_FOUND",
                    "ORDERBOOK_DELTA_ONLY_NOT_DEPTH_PROOF",
                    "ORDERBOOK_RECONSTRUCTION_NOT_PROVEN",
                ]
            )
            continue
        if "BOOK_DEPTH_STALE" in depth_statuses or "BOOK_SEQUENCE_GAP" in depth_statuses:
            blocker_codes.extend(
                ["ORDERBOOK_SEQUENCE_GAP", "ORDERBOOK_RECONSTRUCTION_NOT_PROVEN"]
            )
            continue
        if has_snapshot and not (
            {
                "BOOK_DEPTH20_AVAILABLE",
                "BOOK_LIMITED_DEPTH_AVAILABLE",
                "BOOK_TOP_OF_BOOK_ONLY",
            }
            & depth_statuses
        ):
            blocker_codes.append("ORDERBOOK_RECONSTRUCTION_NOT_PROVEN")
    silver_index_date_range_status, silver_index_date_range_violation_count = (
        _validate_silver_index_date_range(
            silver_index,
            start_ms=start_ms,
            end_ms=end_ms,
        )
    )
    silver_index_status = (
        "SILVER_INDEX_READY" if silver_index and not request.dry_run else "SILVER_INDEX_NOT_READY"
    )
    if silver_index_date_range_status == "SILVER_INDEX_DATE_RANGE_VIOLATION":
        silver_index_status = "SILVER_INDEX_DATE_RANGE_VIOLATION"
        blocker_codes.append("SILVER_INDEX_DATE_RANGE_VIOLATION")
    data_factory_status = "DATA_FACTORY_READY"
    if request.dry_run:
        data_factory_status = "DATA_FACTORY_PARTIAL"
    # Patch 6 batch 1 — non-dry-run hard guard for missing date window.
    # Without this, a silent broad scan can churn through hundreds of GB.
    if not request.dry_run and (not request.start or not request.end):
        if not request.allow_broad_run:
            blocker_codes.append("DATE_RANGE_REQUIRED_FOR_NON_DRY_RUN")
            data_factory_status = "DATA_FACTORY_BLOCKED_BY_DATE_RANGE"
    if source_report.raw_source_status in {"RAW_SOURCE_MISSING", "RAW_SOURCE_SCHEMA_INVALID"}:
        data_factory_status = "DATA_FACTORY_BLOCKED_BY_SOURCE_MISSING"
    elif any(status.endswith("INVALID_TIMESTAMP") or status.endswith("SCHEMA_UNKNOWN") for status in (*trade_statuses, *kline_statuses, *orderbook_statuses)):
        data_factory_status = "DATA_FACTORY_BLOCKED_BY_SCHEMA"
    elif not pair_report.available_pairs and request.pairs:
        data_factory_status = "DATA_FACTORY_BLOCKED_BY_RAW_DATA"
    elif not silver_index and not request.dry_run:
        data_factory_status = "DATA_FACTORY_BLOCKED_BY_RAW_DATA"
    if scope_guard_blocked:
        data_factory_status = "DATA_FACTORY_BLOCKED_BY_RAW_DATA"
    if silver_index_date_range_status == "SILVER_INDEX_DATE_RANGE_VIOLATION":
        data_factory_status = "DATA_FACTORY_BLOCKED_BY_RAW_DATA"
    if (
        request.historical_metadata_root is not None
        and historical_metadata_status != BYBIT_HISTORICAL_METADATA_READY
        and data_factory_status == "DATA_FACTORY_READY"
    ):
        data_factory_status = "DATA_FACTORY_PARTIAL"
    # Patch 6 corrective slice — date pruning + storage status classification.
    if normalized_start or normalized_end:
        if not date_boundaries_parseable:
            date_pruning_status = "DATE_PRUNING_FAILED"
            blocker_codes.append("DATE_PRUNING_FAILED")
        elif silver_index_date_range_status == "SILVER_INDEX_DATE_RANGE_VIOLATION":
            date_pruning_status = "DATE_PRUNING_FAILED_OUTPUT_OUT_OF_RANGE"
            blocker_codes.append("DATE_PRUNING_FAILED_OUTPUT_OUT_OF_RANGE")
        elif files_with_unparsed_date > 0:
            date_pruning_status = "DATE_PRUNING_PARTIAL"
        else:
            date_pruning_status = "DATE_PRUNING_READY"
    else:
        date_pruning_status = "DATE_PRUNING_NOT_PROVEN"
    storage_format = normalize_silver_storage_format(effective_storage_format)
    storage_format_token = (
        "jsonl_gz"
        if storage_format == "jsonl-gz"
        else "jsonl_debug"
        if storage_format == "jsonl-debug"
        else "jsonl"
    )
    if storage_format == "jsonl-gz":
        silver_storage_status = "SILVER_STORAGE_READY_COMPRESSED"
        if storage_auto_compressed:
            blocker_codes.append("SILVER_STORAGE_AUTO_COMPRESSED_FOR_BROAD_RUN")
    elif request.dry_run or request.small_scope:
        silver_storage_status = "SILVER_STORAGE_JSONL_DEBUG_ALLOWED"
    elif request.allow_broad_run:
        silver_storage_status = "SILVER_STORAGE_BLOAT_BLOCKER"
        blocker_codes.append("SILVER_STORAGE_JSONL_DEBUG_FOR_BROAD_RUN")
        blocker_codes.append("SILVER_STORAGE_BLOAT_BLOCKER")
    else:
        silver_storage_status = "SILVER_STORAGE_BLOAT_WARNING"
        blocker_codes.append("SILVER_STORAGE_BLOAT_WARNING")
    data_quality = finalize_hashed_model(
        StrategyLadderDataQualityReport(
            data_factory_status=data_factory_status,
            trade_schema_status=trade_schema_status,
            kline_schema_status=kline_schema_status,
            orderbook_schema_status=orderbook_schema_status,
            metadata_schema_status=metadata_schema_status,
            historical_metadata_status=historical_metadata_status,
            historical_data_venue=metadata_cache_result.historical_data_venue,
            historical_metadata_purpose=metadata_cache_result.historical_metadata_purpose,
            metadata_source_mode=metadata_cache_result.metadata_source_mode,
            metadata_cache_path=metadata_cache_result.metadata_cache_path,
            metadata_pairs_covered=metadata_cache_result.metadata_pairs_covered,
            missing_metadata_pairs=metadata_cache_result.missing_metadata_pairs,
            fee_provenance_status=fee_provenance_status,
            metadata_temporal_status=metadata_temporal_status,
            metadata_fetched_at_utc=metadata_cache_result.fetched_at_utc,
            metadata_preview_rows=metadata_cache_result.metadata_preview_rows,
            capital_bucket_metadata_status=capital_bucket_metadata_status,
            timestamp_unit_status=timestamp_unit_status,
            files_processed=files_processed,
            files_skipped=files_skipped,
            rows_processed=rows_processed,
            rows_rejected=rows_rejected,
            pair_inference_status=str(
                pair_inference_summary.get("pair_inference_status")
                or "PAIR_NOT_DETECTED"
            ),
            requested_pairs=tuple(
                pair_inference_summary.get("requested_pairs") or ()
            ),
            detected_pairs=tuple(
                pair_inference_summary.get("detected_pairs") or ()
            ),
            source_pair_map=dict(pair_inference_summary.get("source_pair_map") or {}),
            pair_inference_sources=dict(
                pair_inference_summary.get("pair_inference_sources") or {}
            ),
            pair_mismatch_reason_codes=tuple(
                pair_inference_summary.get("pair_mismatch_reason_codes") or ()
            ),
            ignored_source_pairs=tuple(
                pair_inference_summary.get("ignored_source_pairs") or ()
            ),
            active_pairs_after_pruning=tuple(
                pair_inference_summary.get("active_pairs_after_pruning") or ()
            ),
            blocker_codes=tuple(dict.fromkeys(blocker_codes)),
            date_filter_start=normalized_start or "",
            date_filter_end=normalized_end or "",
            files_seen=files_seen,
            files_skipped_by_date_filter=files_skipped_by_date_filter,
            date_pruning_status=date_pruning_status,
            silver_index_date_range_status=silver_index_date_range_status,
            silver_index_date_range_violation_count=silver_index_date_range_violation_count,
            raw_scan_budget_status=raw_scan_budget_status,
            raw_scan_budget_limit_bytes=request.storage_budget_limit_bytes,
            raw_scan_budget_reason_codes=tuple(
                dict.fromkeys(raw_scan_budget_reason_codes)
            ),
            silver_storage_format=storage_format_token,
            silver_storage_status=silver_storage_status,
        )
    )
    silver_size_actual = sum(
        Path(entry.path).stat().st_size
        for entry in silver_index
        if entry.path and Path(entry.path).exists()
    )
    gold_size_actual = sum(
        Path(path).stat().st_size
        for path in gold_manifest.feature_paths
        if Path(path).exists()
    )
    silver_bloat_ratio = (
        round(silver_size_actual / bytes_read, 6)
        if bytes_read > 0 and silver_size_actual > 0
        else None
    )
    if silver_bloat_ratio is not None and silver_bloat_ratio > 1.0:
        if storage_format != "jsonl-gz":
            silver_storage_status = (
                "SILVER_STORAGE_BLOAT_BLOCKER"
                if request.allow_broad_run and not request.small_scope and not request.dry_run
                else "SILVER_STORAGE_BLOAT_WARNING"
            )
        blocker_codes.append(silver_storage_status)
        data_quality = finalize_hashed_model(
            data_quality.model_copy(
                update={
                    "silver_storage_status": silver_storage_status,
                }
            )
        )
    compression = finalize_hashed_model(
        StrategyLadderCompressionReport(
            raw_size_bytes=bytes_read,
            silver_size_bytes=silver_size_actual,
            gold_size_bytes=gold_size_actual,
            silver_storage_format=storage_format_token,
            silver_storage_status=silver_storage_status,
            silver_bloat_ratio=silver_bloat_ratio,
            recommendation=(
                "Silver exceeds raw size. Prefer jsonl_gz or candidate-window replay extraction for broader runs."
                if silver_bloat_ratio is not None and silver_bloat_ratio > 1.0
                else ""
            ),
            compression_ratio_raw_to_silver=(
                round(bytes_read / max(silver_size_actual, 1), 6)
                if bytes_read > 0 and silver_index and any(entry.path for entry in silver_index)
                else None
            ),
            compression_ratio_raw_to_gold=(
                round(bytes_read / max(gold_size_actual, 1), 6)
                if bytes_read > 0 and gold_manifest.feature_paths
                else None
            ),
            files_processed=files_processed,
            files_skipped=files_skipped,
            rows_processed=rows_processed,
            rows_rejected=rows_rejected,
        )
    )
    manifest = finalize_hashed_model(
        StrategyLadderDataFactoryManifest(
            run_id=request.run_id,
            raw_roots=tuple(str(path.resolve()) for path in request.raw_roots),
            raw_source_manifest_path=str(request.raw_source_manifest_path.resolve()) if request.raw_source_manifest_path is not None else "",
            historical_metadata_root=str(request.historical_metadata_root.resolve()) if request.historical_metadata_root is not None else "",
            silver_root=str(request.silver_root.resolve()),
            gold_root=str(request.gold_root.resolve()),
            pairs=request.pairs,
            start=normalized_start,
            end=normalized_end,
            data_types=request.data_types,
            compression=request.compression,
            resume=request.resume,
            dry_run=request.dry_run,
            data_factory_status=data_factory_status,
            raw_source_status=source_report.raw_source_status,
            pair_universe_status=pair_report.pair_universe_status,
            silver_index_status=silver_index_status,
            gold_feature_store_status=gold_manifest.gold_feature_store_status,
            trade_schema_status=trade_schema_status,
            kline_schema_status=kline_schema_status,
            orderbook_schema_status=orderbook_schema_status,
            metadata_schema_status=metadata_schema_status,
            historical_metadata_status=historical_metadata_status,
            metadata_source_mode=metadata_cache_result.metadata_source_mode,
            fee_provenance_status=fee_provenance_status,
            metadata_temporal_status=metadata_temporal_status,
            compression_status=("COMPRESSION_READY" if bytes_written > 0 else "COMPRESSION_NOT_PROVEN"),
            silver_storage_format=storage_format_token,
            silver_storage_status=silver_storage_status,
            silver_bloat_ratio=silver_bloat_ratio,
            date_pruning_status=date_pruning_status,
            silver_index_date_range_status=silver_index_date_range_status,
            raw_scan_budget_status=raw_scan_budget_status,
            blocker_codes=tuple(dict.fromkeys(blocker_codes)),
            files_processed=files_processed,
            files_skipped=files_skipped,
            rows_processed=rows_processed,
            rows_rejected=rows_rejected,
            bytes_read=bytes_read,
            bytes_written=bytes_written,
        )
    )
    _write_report(report_root / "data_factory_manifest.json", manifest)
    enriched_source_report = finalize_hashed_model(
        source_report.model_copy(
            update={
                "pair_inference_status": str(
                    pair_inference_summary.get("pair_inference_status")
                    or "PAIR_NOT_DETECTED"
                ),
                "requested_pairs": tuple(
                    pair_inference_summary.get("requested_pairs") or ()
                ),
                "detected_pairs": tuple(
                    pair_inference_summary.get("detected_pairs") or ()
                ),
                "source_pair_map": dict(
                    pair_inference_summary.get("source_pair_map") or {}
                ),
                "pair_inference_sources": dict(
                    pair_inference_summary.get("pair_inference_sources") or {}
                ),
                "pair_mismatch_reason_codes": tuple(
                    pair_inference_summary.get("pair_mismatch_reason_codes") or ()
                ),
                "ignored_source_pairs": tuple(
                    pair_inference_summary.get("ignored_source_pairs") or ()
                ),
                "active_pairs_after_pruning": tuple(
                    pair_inference_summary.get("active_pairs_after_pruning") or ()
                ),
            }
        )
    )
    _write_report(report_root / "raw_source_report.json", enriched_source_report)
    _write_report(report_root / "pair_universe_report.json", pair_report)
    _write_report(report_root / "data_quality_report.json", data_quality)
    _write_report(
        report_root / "silver_index.json",
        {
            "schema_version": "v1",
            "entries": [entry.model_dump(mode="json") for entry in silver_index],
            "status": silver_index_status,
            "artifact_hash": hashlib.sha256(
                json.dumps([entry.model_dump(mode="json") for entry in silver_index], sort_keys=True).encode("utf-8")
            ).hexdigest(),
        },
    )
    _write_report(report_root / "gold_feature_manifest.json", gold_manifest)
    _write_report(report_root / "compression_report.json", compression)
    # Patch 6 batch 1 — emit the storage budget report from real silver sizes.
    from local_replay_runtime.storage_budget_report import (
        StorageBudgetReport,
        write_storage_budget_report,
    )
    storage_budget_total = silver_size_actual + gold_size_actual
    storage_budget_status = preflight_storage_budget_report.storage_budget_status
    storage_budget_reason_codes = list(
        preflight_storage_budget_report.storage_budget_reason_codes
    )
    if not request.dry_run:
        if (
            request.storage_budget_limit_bytes > 0
            and storage_budget_total > request.storage_budget_limit_bytes
        ):
            storage_budget_status = "STORAGE_BUDGET_EXCEEDED"
            storage_budget_reason_codes.append("RAW_SIZE_ESTIMATE_EXCEEDS_BUDGET")
        elif (
            storage_budget_total > 0
            and storage_budget_status == "STORAGE_BUDGET_NOT_PROVEN"
        ):
            storage_budget_status = "STORAGE_BUDGET_READY"
    elif (
        request.storage_budget_limit_bytes > 0
        and preflight_storage_budget_report.raw_size_estimate
        > request.storage_budget_limit_bytes
        and storage_budget_status
        not in {"STORAGE_BUDGET_EXCEEDED", "STORAGE_BUDGET_WARNING"}
    ):
        storage_budget_status = "STORAGE_BUDGET_WARNING"
        storage_budget_reason_codes.append("RAW_SIZE_ESTIMATE_EXCEEDS_BUDGET")
    storage_budget_report = finalize_hashed_model(
        StorageBudgetReport(
            run_id=request.run_id,
            output_root=str(report_root.resolve()),
            raw_size_bytes=preflight_storage_budget_report.raw_size_estimate,
            raw_size_estimate=preflight_storage_budget_report.raw_size_estimate,
            gold_size_bytes=gold_size_actual,
            phase1_gold_size=gold_size_actual,
            silver_size_bytes=silver_size_actual,
            silver_size_estimate=silver_size_actual,
            storage_format=storage_format,
            silver_storage_format=storage_format_token,
            silver_storage_status=silver_storage_status,
            silver_bloat_ratio=silver_bloat_ratio,
            storage_budget_status=storage_budget_status,
            storage_budget_limit_bytes=request.storage_budget_limit_bytes,
            storage_budget_reason_codes=tuple(
                dict.fromkeys(storage_budget_reason_codes)
            ),
            recommendation=(
                "Silver exceeds raw size. Prefer jsonl_gz or candidate-window replay extraction for broader runs."
                if silver_bloat_ratio is not None and silver_bloat_ratio > 1.0
                else ""
            ),
            blocker_severity=(
                "BLOCKER"
                if silver_storage_status == "SILVER_STORAGE_BLOAT_BLOCKER"
                or storage_budget_status == "STORAGE_BUDGET_EXCEEDED"
                else "WARNING"
                if silver_storage_status == "SILVER_STORAGE_BLOAT_WARNING"
                or storage_budget_status == "STORAGE_BUDGET_WARNING"
                else "READY"
            ),
        )
    )
    write_storage_budget_report(report_root, storage_budget_report)
    # Patch 6 batch 2 — emit the feature/threshold registry manifest.
    # Must be written BEFORE the proof matrix so the proof-matrix builder
    # can record the manifest path under feature_threshold_manifest_path.
    from local_replay_runtime.feature_threshold_manifest import (
        emit_feature_threshold_manifest,
    )

    emit_feature_threshold_manifest(
        output_root=report_root,
        run_id=request.run_id,
        pairs=request.pairs,
        start=normalized_start,
        end=normalized_end,
        timeframes=request.timeframes,
        engines=request.engines,
    )
    # Patch 6 — emit the typed backtest proof matrix alongside the other reports.
    # Imported lazily to avoid a circular import (the proof-matrix builder
    # depends only on serialized manifest contracts, never on runtime models).
    from local_replay_runtime.backtest_proof_matrix import emit_backtest_proof_matrix

    _write_orderbook_sequence_gap_report(
        output_root=report_root,
        diagnostics=tuple(orderbook_gap_diagnostics),
    )
    emit_backtest_proof_matrix(
        output_root=report_root,
        run_id=request.run_id,
        pairs=request.pairs,
        start=normalized_start,
        end=normalized_end,
        ml_mode="ML_MODE_OFF",
    )
    return StrategyLadderDataFactoryResult(
        manifest=manifest,
        raw_source_report=enriched_source_report,
        pair_universe_report=pair_report,
        data_quality_report=data_quality,
        silver_index=silver_index,
        compression_report=compression,
        gold_feature_manifest=gold_manifest,
    )


__all__ = [
    "StrategyLadderDataFactoryRequest",
    "StrategyLadderDataFactoryResult",
    "classify_raw_file",
    "run_strategy_ladder_data_factory",
]
