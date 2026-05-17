"""Pure storage budget estimation helpers shared by replay and cockpit surfaces."""

from __future__ import annotations

from pathlib import Path


_DEFAULT_EXPANSION_RATIOS_JSONL: dict[str, float] = {
    "orderbook": 7.0,
    "orderbook_snapshot": 0.05,
    "orderbook_delta": 7.0,
    "trades": 2.5,
    "klines": 1.3,
    "metadata": 1.0,
}
_GZIP_COMPRESSION_RATIO: float = 8.0


def normalize_silver_storage_format(storage_format: str | None) -> str:
    """Normalize operator-facing storage mode labels to canonical writer modes."""

    fmt = (storage_format or "jsonl").strip().lower().replace("_", "-")
    if fmt == "jsonl-debug":
        return "jsonl-debug"
    if fmt == "jsonl-gz":
        return "jsonl-gz"
    return "jsonl"


def classify_raw_data_type(path: Path) -> str:
    """Best-effort raw-file classification by path tokens."""

    parts = {part.lower() for part in path.parts}
    name_lower = path.name.lower()
    if {"orderbook_snapshot"} & parts:
        return "orderbook_snapshot"
    if {"orderbook_delta"} & parts:
        return "orderbook_delta"
    if "ob200" in name_lower or {"orderbook"} & parts or "book" in name_lower:
        return "orderbook"
    if "trades" in parts or "trade" in parts:
        return "trades"
    if "klines" in parts or "kline" in parts or "ohlcv" in parts:
        return "klines"
    if "metadata" in parts or "filters" in parts or "symbol_filters" in parts:
        return "metadata"
    return "unknown"


def estimate_silver_size_for_paths(
    raw_paths: tuple[Path, ...],
    *,
    storage_format: str = "jsonl",
) -> tuple[int, int]:
    """Return ``(raw_size_bytes, silver_size_estimate_bytes)`` without opening files."""

    fmt = normalize_silver_storage_format(storage_format)
    raw_total = 0
    silver_total = 0.0
    for path in raw_paths:
        if not path.exists() or not path.is_file():
            continue
        try:
            raw_size = path.stat().st_size
        except OSError:
            continue
        raw_total += raw_size
        data_type = classify_raw_data_type(path)
        ratio = _DEFAULT_EXPANSION_RATIOS_JSONL.get(data_type, 2.0)
        silver_estimate = raw_size * ratio
        if fmt == "jsonl-gz":
            silver_estimate /= _GZIP_COMPRESSION_RATIO
        silver_total += silver_estimate
    return raw_total, int(silver_total)


__all__ = [
    "classify_raw_data_type",
    "estimate_silver_size_for_paths",
    "normalize_silver_storage_format",
]
