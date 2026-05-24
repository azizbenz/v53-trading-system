"""Feature/gold-store loader for the canonical Strategy Ladder runner."""

from __future__ import annotations

import csv
from datetime import UTC, datetime
import gzip
import importlib
import json
from pathlib import Path

from local_replay_runtime.strategy_ladder_models import (
    StrategyLadderFeatureRow,
    StrategyLadderFeatureStoreResult,
)


_SUPPORTED_SUFFIXES = (".json", ".jsonl", ".csv", ".parquet", ".gz")


def _normalize_loose_iso_date(raw_value: str) -> str:
    value = (raw_value or "").strip()
    if not value:
        return ""
    if "T" in value or " " in value:
        return value
    parts = value.split("-")
    if len(parts) != 3 or not all(part.strip().isdigit() for part in parts):
        return value
    year, month, day = (part.strip() for part in parts)
    return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"


def _is_date_only_boundary(value: str) -> bool:
    stripped = (value or "").strip()
    if not stripped or "T" in stripped or " " in stripped:
        return False
    parts = stripped.split("-")
    return len(parts) == 3 and all(part.strip().isdigit() for part in parts)


def parse_time_boundary_to_ms(raw_value: str, *, end_of_day: bool = False) -> int | None:
    """Parse a numeric or ISO-like boundary string into epoch milliseconds."""

    value = (raw_value or "").strip()
    if not value:
        return None
    if value.isdigit():
        numeric = int(value)
        if numeric > 10_000_000_000:
            return numeric
        return numeric * 1000
    normalized = _normalize_loose_iso_date(value).replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    timestamp_ms = int(parsed.timestamp() * 1000)
    if end_of_day and _is_date_only_boundary(value):
        return timestamp_ms + 86_399_999
    return timestamp_ms


def _iter_supported_paths(root: Path) -> tuple[Path, ...]:
    resolved = root.resolve()
    if resolved.is_file():
        return (resolved,) if _is_supported_path(resolved) else ()
    if not resolved.is_dir():
        return ()
    return tuple(
        sorted(
            path
            for path in resolved.rglob("*")
            if path.is_file() and _is_supported_path(path)
        )
    )


def _is_supported_path(path: Path) -> bool:
    suffix = path.suffix.lower()
    if suffix in {".json", ".jsonl", ".csv", ".parquet"}:
        return True
    return path.name.lower().endswith(".jsonl.gz")


def _normalize_csv_row(row: dict[str, str]) -> dict[str, object]:
    payload: dict[str, object] = {}
    feature_payload: dict[str, object] = {}
    for key, value in row.items():
        if key is None:
            continue
        stripped_key = key.strip()
        raw_value = "" if value is None else value.strip()
        if not stripped_key:
            continue
        if stripped_key.startswith("feature__"):
            feature_payload[stripped_key.removeprefix("feature__")] = raw_value
            continue
        if stripped_key.startswith("feature_") and stripped_key != "feature_values":
            feature_payload[stripped_key.removeprefix("feature_")] = raw_value
            continue
        payload[stripped_key] = raw_value
    if feature_payload and "feature_values" not in payload:
        payload["feature_values"] = feature_payload
    return payload


def _load_json_records(path: Path) -> tuple[dict[str, object], ...]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(payload, list):
        return tuple(item for item in payload if isinstance(item, dict))
    if isinstance(payload, dict):
        records = payload.get("records", ())
        if isinstance(records, list):
            return tuple(item for item in records if isinstance(item, dict))
        return (payload,)
    raise ValueError(f"Unsupported JSON feature-store payload in {path}")


def _load_jsonl_records(path: Path) -> tuple[dict[str, object], ...]:
    records: list[dict[str, object]] = []
    if path.name.lower().endswith(".jsonl.gz"):
        payload_lines = gzip.open(path, "rt", encoding="utf-8-sig").read().splitlines()
    else:
        payload_lines = path.read_text(encoding="utf-8-sig").splitlines()
    for line in payload_lines:
        stripped = line.strip()
        if not stripped:
            continue
        payload = json.loads(stripped)
        if not isinstance(payload, dict):
            raise ValueError(f"Strategy Ladder JSONL rows must be objects in {path}")
        records.append(payload)
    return tuple(records)


def _load_csv_records(path: Path) -> tuple[dict[str, object], ...]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return tuple(_normalize_csv_row(dict(row)) for row in reader)


def _load_parquet_records(path: Path) -> tuple[dict[str, object], ...]:
    if importlib.util.find_spec("pyarrow") is None:
        raise RuntimeError("Parquet support requires pyarrow to already be available")
    table = importlib.import_module("pyarrow.parquet").read_table(path)
    rows = table.to_pylist()
    return tuple(item for item in rows if isinstance(item, dict))


def _load_path_records(path: Path) -> tuple[dict[str, object], ...]:
    lowered_name = path.name.lower()
    suffix = path.suffix.lower()
    if suffix == ".json":
        return _load_json_records(path)
    if suffix == ".jsonl" or lowered_name.endswith(".jsonl.gz"):
        return _load_jsonl_records(path)
    if suffix == ".csv":
        return _load_csv_records(path)
    if suffix == ".parquet":
        return _load_parquet_records(path)
    raise ValueError(f"Unsupported feature-store suffix: {suffix}")


def load_strategy_ladder_feature_store(
    root: Path,
    *,
    pairs: tuple[str, ...] = (),
    engines: tuple[str, ...] = (),
    timeframes: tuple[str, ...] = (),
    start_ms: int | None = None,
    end_ms: int | None = None,
) -> StrategyLadderFeatureStoreResult:
    """Load and filter feature-store rows for Strategy Ladder candidate discovery."""

    input_paths = _iter_supported_paths(root)
    if not input_paths:
        return StrategyLadderFeatureStoreResult(
            feature_store_status="FEATURE_STORE_MISSING",
            input_paths=(str(root.resolve()),),
            blocker_codes=("FEATURE_STORE_MISSING",),
        )

    rows: list[StrategyLadderFeatureRow] = []
    invalid_row_count = 0
    rejected_future_leak_count = 0
    blockers: list[str] = []
    pair_filter = set(pairs)
    engine_filter = set(engines)
    timeframe_filter = set(timeframes)

    for path in input_paths:
        try:
            records = _load_path_records(path)
        except Exception:
            invalid_row_count += 1
            blockers.append("FEATURE_STORE_SCHEMA_INVALID")
            continue
        for payload in records:
            try:
                row = StrategyLadderFeatureRow.model_validate(
                    {
                        **payload,
                        "source_ref": str(payload.get("source_ref") or path.resolve()),
                    }
                )
            except ValueError as exc:
                invalid_row_count += 1
                if "available_at_timestamp_ms" in str(exc):
                    rejected_future_leak_count += 1
                    blockers.append("FEATURE_STORE_FUTURE_LEAK_REJECTED")
                else:
                    blockers.append("FEATURE_STORE_SCHEMA_INVALID")
                continue
            if pair_filter and row.pair not in pair_filter:
                continue
            if timeframe_filter and row.timeframe not in timeframe_filter:
                continue
            if engine_filter and not set(row.resolved_engine_ids) & engine_filter:
                continue
            if start_ms is not None and row.resolved_timestamp_ms < start_ms:
                continue
            if end_ms is not None and row.resolved_timestamp_ms > end_ms:
                continue
            rows.append(row)

    ordered_rows = tuple(sorted(rows, key=lambda row: (row.resolved_timestamp_ms, row.pair, row.strategy_id or "", row.engine_id or "")))
    if not ordered_rows:
        status = "FEATURE_STORE_SCHEMA_INVALID" if invalid_row_count > 0 else "FEATURE_STORE_PARTIAL"
        if status == "FEATURE_STORE_PARTIAL":
            blockers.append("FEATURE_STORE_NO_FILTERED_ROWS")
        return StrategyLadderFeatureStoreResult(
            feature_store_status=status,
            rows=(),
            input_paths=tuple(str(path.resolve()) for path in input_paths),
            invalid_row_count=invalid_row_count,
            rejected_future_leak_count=rejected_future_leak_count,
            blocker_codes=tuple(dict.fromkeys(blockers)),
        )

    status = "FEATURE_STORE_READY" if invalid_row_count == 0 and rejected_future_leak_count == 0 else "FEATURE_STORE_PARTIAL"
    return StrategyLadderFeatureStoreResult(
        feature_store_status=status,
        rows=ordered_rows,
        input_paths=tuple(str(path.resolve()) for path in input_paths),
        invalid_row_count=invalid_row_count,
        rejected_future_leak_count=rejected_future_leak_count,
        blocker_codes=tuple(dict.fromkeys(blockers)),
    )


__all__ = [
    "load_strategy_ladder_feature_store",
    "parse_time_boundary_to_ms",
]
