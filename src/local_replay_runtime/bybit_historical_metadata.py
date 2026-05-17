"""Bybit historical metadata cache helpers for Patch 6 Strategy Ladder runs.

This module is intentionally split from the Data Factory runner:
- fetching uses Bybit public endpoints only
- normal backtest/Data Factory runs read local cache only
- configured research fees remain explicit and non-account-verified
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from interface_contracts.atomic_io import atomic_write_json, atomic_write_text


BYBIT_PUBLIC_INSTRUMENTS_INFO_URL = "https://api.bybit.com/v5/market/instruments-info"
BYBIT_RESEARCH_MAKER_FEE_RATE = "0.001"
BYBIT_RESEARCH_TAKER_FEE_RATE = "0.001"
BYBIT_METADATA_SOURCE_MODE = "LOCAL_METADATA_CACHE"
BYBIT_FETCH_MODE = "BYBIT_PUBLIC_METADATA_FETCH"
BYBIT_HISTORICAL_METADATA_READY = "BYBIT_HISTORICAL_METADATA_READY"
BYBIT_HISTORICAL_METADATA_NOT_PROVEN = "BYBIT_HISTORICAL_METADATA_NOT_PROVEN"
CONFIGURED_FEE_PROVENANCE_READY = "CONFIGURED_FEE_PROVENANCE_READY"
FEE_PROVENANCE_NOT_PROVEN = "FEE_PROVENANCE_NOT_PROVEN"
CURRENT_METADATA_PROXY = "CURRENT_METADATA_PROXY"
METADATA_TEMPORAL_NOT_PROVEN = "METADATA_TEMPORAL_NOT_PROVEN"
METADATA_PAIR_NOT_FOUND = "METADATA_PAIR_NOT_FOUND"
ACCOUNT_FEE_VERIFIED = "ACCOUNT_FEE_VERIFIED"

_CACHE_FILENAMES = ("symbol_metadata.csv", "symbol_metadata.jsonl")
_REQUIRED_CACHE_FIELDS = (
    "venue",
    "exchange",
    "market_type",
    "symbol",
    "base_coin",
    "quote_coin",
    "status",
    "tick_size",
    "qty_step",
    "min_order_qty",
    "min_notional",
    "maker_fee_rate",
    "taker_fee_rate",
    "fee_source",
    "metadata_purpose",
    "proof_level",
    "source",
    "fetched_at_utc",
    "raw_payload_hash",
    "metadata_temporal_status",
)
_CSV_HEADER = (
    "venue",
    "exchange",
    "market_type",
    "symbol",
    "base_coin",
    "quote_coin",
    "status",
    "tick_size",
    "qty_step",
    "min_order_qty",
    "min_notional",
    "maker_fee_rate",
    "taker_fee_rate",
    "fee_source",
    "metadata_purpose",
    "proof_level",
    "source",
    "fetched_at_utc",
    "raw_payload_hash",
    "metadata_temporal_status",
    "max_order_qty",
    "max_notional",
    "effective_from_utc",
    "effective_to_utc",
    "notes",
)


@dataclass(frozen=True)
class HistoricalMetadataCacheResult:
    historical_metadata_status: str
    metadata_schema_status: str
    fee_provenance_status: str
    metadata_temporal_status: str
    metadata_source_mode: str
    historical_data_venue: str
    historical_metadata_purpose: str
    metadata_cache_path: str
    metadata_pairs_covered: tuple[str, ...]
    missing_metadata_pairs: tuple[str, ...]
    fetched_at_utc: str
    rows: tuple[dict[str, object], ...]
    blocker_codes: tuple[str, ...]
    metadata_preview_rows: tuple[dict[str, object], ...]


def _utc_now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


def _normalize_pair(value: object) -> str:
    raw = str(value or "").strip().upper()
    return "".join(ch for ch in raw if ch.isalnum())


def _positive_string(value: object, *, default: str = "") -> str:
    text = str(value or "").strip()
    return text or default


def _find_cache_file(root: Path) -> Path | None:
    if root.is_file():
        return root.resolve()
    if not root.is_dir():
        return None
    for filename in _CACHE_FILENAMES:
        candidate = root / filename
        if candidate.is_file():
            return candidate.resolve()
    return None


def _load_csv_rows(path: Path) -> tuple[dict[str, object], ...]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return tuple(dict(row) for row in csv.DictReader(handle))


def _load_jsonl_rows(path: Path) -> tuple[dict[str, object], ...]:
    rows: list[dict[str, object]] = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        payload = json.loads(stripped)
        if isinstance(payload, dict):
            rows.append(payload)
    return tuple(rows)


def _canonicalize_metadata_row(row: dict[str, object]) -> dict[str, object]:
    symbol = _normalize_pair(row.get("symbol") or row.get("pair"))
    metadata_temporal_status = str(
        row.get("metadata_temporal_status") or CURRENT_METADATA_PROXY
    ).strip() or CURRENT_METADATA_PROXY
    fetched_at_utc = str(row.get("fetched_at_utc") or "").strip() or _utc_now_iso()
    canonical = {
        "venue": str(row.get("venue") or "bybit").strip() or "bybit",
        "exchange": str(row.get("exchange") or "bybit").strip() or "bybit",
        "market_type": str(row.get("market_type") or "spot").strip() or "spot",
        "symbol": symbol,
        "base_coin": str(row.get("base_coin") or "").strip(),
        "quote_coin": str(row.get("quote_coin") or "").strip(),
        "status": str(row.get("status") or "").strip(),
        "tick_size": _positive_string(row.get("tick_size")),
        "qty_step": _positive_string(row.get("qty_step") or row.get("step_size")),
        "min_order_qty": _positive_string(row.get("min_order_qty")),
        "min_notional": _positive_string(row.get("min_notional")),
        "maker_fee_rate": _positive_string(
            row.get("maker_fee_rate") or row.get("maker_fee"),
            default=BYBIT_RESEARCH_MAKER_FEE_RATE,
        ),
        "taker_fee_rate": _positive_string(
            row.get("taker_fee_rate") or row.get("taker_fee"),
            default=BYBIT_RESEARCH_TAKER_FEE_RATE,
        ),
        "fee_source": str(
            row.get("fee_source") or "bybit_configured_vip0_research"
        ).strip()
        or "bybit_configured_vip0_research",
        "metadata_purpose": str(
            row.get("metadata_purpose") or "historical_replay"
        ).strip()
        or "historical_replay",
        "proof_level": str(row.get("proof_level") or "configured").strip()
        or "configured",
        "source": str(
            row.get("source") or "bybit_public_instruments_info"
        ).strip()
        or "bybit_public_instruments_info",
        "fetched_at_utc": fetched_at_utc,
        "raw_payload_hash": str(row.get("raw_payload_hash") or "").strip(),
        "metadata_temporal_status": metadata_temporal_status,
        "max_order_qty": _positive_string(row.get("max_order_qty")),
        "max_notional": _positive_string(row.get("max_notional")),
        "effective_from_utc": str(row.get("effective_from_utc") or "").strip(),
        "effective_to_utc": str(row.get("effective_to_utc") or "").strip(),
        "notes": str(row.get("notes") or "").strip(),
        # Compatibility aliases used by existing replay/gold-store code.
        "pair": symbol,
        "step_size": _positive_string(row.get("qty_step") or row.get("step_size")),
        "maker_fee": _positive_string(
            row.get("maker_fee_rate") or row.get("maker_fee"),
            default=BYBIT_RESEARCH_MAKER_FEE_RATE,
        ),
        "taker_fee": _positive_string(
            row.get("taker_fee_rate") or row.get("taker_fee"),
            default=BYBIT_RESEARCH_TAKER_FEE_RATE,
        ),
    }
    return canonical


def _rows_cover_requested_pairs(
    rows: tuple[dict[str, object], ...], requested_pairs: tuple[str, ...]
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    covered = tuple(
        sorted(
            {
                _normalize_pair(row.get("symbol") or row.get("pair"))
                for row in rows
                if _normalize_pair(row.get("symbol") or row.get("pair"))
            }
        )
    )
    missing = tuple(
        sorted(
            pair
            for pair in (_normalize_pair(pair) for pair in requested_pairs)
            if pair and pair not in covered
        )
    )
    return covered, missing


def _report_preview_rows(rows: tuple[dict[str, object], ...]) -> tuple[dict[str, object], ...]:
    preview: list[dict[str, object]] = []
    for row in rows[:5]:
        preview.append(
            {
                "symbol": row.get("symbol") or row.get("pair") or "",
                "status": row.get("status") or "",
                "tick_size": row.get("tick_size") or "",
                "qty_step": row.get("qty_step") or row.get("step_size") or "",
                "min_order_qty": row.get("min_order_qty") or "",
                "min_notional": row.get("min_notional") or "",
                "maker_fee_rate": row.get("maker_fee_rate") or row.get("maker_fee") or "",
                "taker_fee_rate": row.get("taker_fee_rate") or row.get("taker_fee") or "",
                "fee_source": row.get("fee_source") or "",
                "proof_level": row.get("proof_level") or "",
                "metadata_temporal_status": row.get("metadata_temporal_status") or "",
                "fetched_at_utc": row.get("fetched_at_utc") or "",
            }
        )
    return tuple(preview)


def load_historical_metadata_cache(
    root: Path | None,
    *,
    requested_pairs: tuple[str, ...] = (),
) -> HistoricalMetadataCacheResult:
    """Load the local Bybit metadata cache without making any network calls."""

    if root is None:
        return HistoricalMetadataCacheResult(
            historical_metadata_status=BYBIT_HISTORICAL_METADATA_NOT_PROVEN,
            metadata_schema_status="METADATA_SCHEMA_NOT_PROVEN",
            fee_provenance_status=FEE_PROVENANCE_NOT_PROVEN,
            metadata_temporal_status=METADATA_TEMPORAL_NOT_PROVEN,
            metadata_source_mode=BYBIT_METADATA_SOURCE_MODE,
            historical_data_venue="BYBIT",
            historical_metadata_purpose="historical_replay",
            metadata_cache_path="",
            metadata_pairs_covered=(),
            missing_metadata_pairs=tuple(sorted(_normalize_pair(pair) for pair in requested_pairs if pair)),
            fetched_at_utc="",
            rows=(),
            blocker_codes=("BYBIT_HISTORICAL_METADATA_NOT_PROVEN",),
            metadata_preview_rows=(),
        )
    cache_file = _find_cache_file(root.expanduser().resolve())
    if cache_file is None:
        return HistoricalMetadataCacheResult(
            historical_metadata_status=BYBIT_HISTORICAL_METADATA_NOT_PROVEN,
            metadata_schema_status="METADATA_SCHEMA_NOT_PROVEN",
            fee_provenance_status=FEE_PROVENANCE_NOT_PROVEN,
            metadata_temporal_status=METADATA_TEMPORAL_NOT_PROVEN,
            metadata_source_mode=BYBIT_METADATA_SOURCE_MODE,
            historical_data_venue="BYBIT",
            historical_metadata_purpose="historical_replay",
            metadata_cache_path="",
            metadata_pairs_covered=(),
            missing_metadata_pairs=tuple(sorted(_normalize_pair(pair) for pair in requested_pairs if pair)),
            fetched_at_utc="",
            rows=(),
            blocker_codes=("BYBIT_HISTORICAL_METADATA_NOT_PROVEN",),
            metadata_preview_rows=(),
        )
    try:
        raw_rows = (
            _load_csv_rows(cache_file)
            if cache_file.suffix.lower() == ".csv"
            else _load_jsonl_rows(cache_file)
        )
    except (OSError, ValueError, json.JSONDecodeError):
        return HistoricalMetadataCacheResult(
            historical_metadata_status=BYBIT_HISTORICAL_METADATA_NOT_PROVEN,
            metadata_schema_status="METADATA_SCHEMA_NOT_PROVEN",
            fee_provenance_status=FEE_PROVENANCE_NOT_PROVEN,
            metadata_temporal_status=METADATA_TEMPORAL_NOT_PROVEN,
            metadata_source_mode=BYBIT_METADATA_SOURCE_MODE,
            historical_data_venue="BYBIT",
            historical_metadata_purpose="historical_replay",
            metadata_cache_path=str(cache_file),
            metadata_pairs_covered=(),
            missing_metadata_pairs=tuple(sorted(_normalize_pair(pair) for pair in requested_pairs if pair)),
            fetched_at_utc="",
            rows=(),
            blocker_codes=("METADATA_SCHEMA_NOT_PROVEN",),
            metadata_preview_rows=(),
        )
    if not raw_rows:
        return HistoricalMetadataCacheResult(
            historical_metadata_status=BYBIT_HISTORICAL_METADATA_NOT_PROVEN,
            metadata_schema_status="METADATA_SCHEMA_NOT_PROVEN",
            fee_provenance_status=FEE_PROVENANCE_NOT_PROVEN,
            metadata_temporal_status=METADATA_TEMPORAL_NOT_PROVEN,
            metadata_source_mode=BYBIT_METADATA_SOURCE_MODE,
            historical_data_venue="BYBIT",
            historical_metadata_purpose="historical_replay",
            metadata_cache_path=str(cache_file),
            metadata_pairs_covered=(),
            missing_metadata_pairs=tuple(sorted(_normalize_pair(pair) for pair in requested_pairs if pair)),
            fetched_at_utc="",
            rows=(),
            blocker_codes=("METADATA_SCHEMA_NOT_PROVEN",),
            metadata_preview_rows=(),
        )
    header_keys = {str(key).strip() for key in raw_rows[0]}
    if not set(_REQUIRED_CACHE_FIELDS).issubset(header_keys):
        return HistoricalMetadataCacheResult(
            historical_metadata_status=BYBIT_HISTORICAL_METADATA_NOT_PROVEN,
            metadata_schema_status="METADATA_SCHEMA_NOT_PROVEN",
            fee_provenance_status=FEE_PROVENANCE_NOT_PROVEN,
            metadata_temporal_status=METADATA_TEMPORAL_NOT_PROVEN,
            metadata_source_mode=BYBIT_METADATA_SOURCE_MODE,
            historical_data_venue="BYBIT",
            historical_metadata_purpose="historical_replay",
            metadata_cache_path=str(cache_file),
            metadata_pairs_covered=(),
            missing_metadata_pairs=tuple(sorted(_normalize_pair(pair) for pair in requested_pairs if pair)),
            fetched_at_utc="",
            rows=(),
            blocker_codes=("METADATA_SCHEMA_NOT_PROVEN",),
            metadata_preview_rows=(),
        )
    normalized_rows = tuple(_canonicalize_metadata_row(row) for row in raw_rows)
    covered_pairs, missing_pairs = _rows_cover_requested_pairs(normalized_rows, requested_pairs)
    fetched_at_utc = str(
        next(
            (
                row.get("fetched_at_utc")
                for row in normalized_rows
                if str(row.get("fetched_at_utc") or "").strip()
            ),
            "",
        )
    )
    if missing_pairs:
        historical_status = METADATA_PAIR_NOT_FOUND
        blocker_codes = (METADATA_PAIR_NOT_FOUND,)
    else:
        historical_status = BYBIT_HISTORICAL_METADATA_READY
        blocker_codes = ()
    metadata_temporal_status = str(
        next(
            (
                row.get("metadata_temporal_status")
                for row in normalized_rows
                if str(row.get("metadata_temporal_status") or "").strip()
            ),
            CURRENT_METADATA_PROXY,
        )
    )
    return HistoricalMetadataCacheResult(
        historical_metadata_status=historical_status,
        metadata_schema_status="METADATA_SCHEMA_READY",
        fee_provenance_status=CONFIGURED_FEE_PROVENANCE_READY,
        metadata_temporal_status=metadata_temporal_status or CURRENT_METADATA_PROXY,
        metadata_source_mode=BYBIT_METADATA_SOURCE_MODE,
        historical_data_venue="BYBIT",
        historical_metadata_purpose="historical_replay",
        metadata_cache_path=str(cache_file),
        metadata_pairs_covered=covered_pairs,
        missing_metadata_pairs=missing_pairs,
        fetched_at_utc=fetched_at_utc,
        rows=normalized_rows,
        blocker_codes=blocker_codes,
        metadata_preview_rows=_report_preview_rows(normalized_rows),
    )


def _hash_payload(payload: object) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _canonical_row_from_instrument(
    instrument: dict[str, Any],
    *,
    fetched_at_utc: str,
) -> dict[str, object]:
    price_filter = instrument.get("priceFilter")
    lot_size_filter = instrument.get("lotSizeFilter")
    price_filter = price_filter if isinstance(price_filter, dict) else {}
    lot_size_filter = lot_size_filter if isinstance(lot_size_filter, dict) else {}
    symbol = _normalize_pair(instrument.get("symbol"))
    payload_hash = _hash_payload(instrument)
    return {
        "venue": "bybit",
        "exchange": "bybit",
        "market_type": "spot",
        "symbol": symbol,
        "base_coin": str(instrument.get("baseCoin") or "").strip(),
        "quote_coin": str(instrument.get("quoteCoin") or "").strip(),
        "status": str(instrument.get("status") or "").strip(),
        "tick_size": _positive_string(price_filter.get("tickSize")),
        "qty_step": _positive_string(lot_size_filter.get("qtyStep")),
        "min_order_qty": _positive_string(lot_size_filter.get("minOrderQty")),
        "min_notional": _positive_string(lot_size_filter.get("minOrderAmt")),
        "maker_fee_rate": BYBIT_RESEARCH_MAKER_FEE_RATE,
        "taker_fee_rate": BYBIT_RESEARCH_TAKER_FEE_RATE,
        "fee_source": "bybit_configured_vip0_research",
        "metadata_purpose": "historical_replay",
        "proof_level": "configured",
        "source": "bybit_public_instruments_info",
        "fetched_at_utc": fetched_at_utc,
        "raw_payload_hash": payload_hash,
        "metadata_temporal_status": CURRENT_METADATA_PROXY,
        "max_order_qty": _positive_string(lot_size_filter.get("maxOrderQty")),
        "max_notional": _positive_string(lot_size_filter.get("maxOrderAmt")),
        "effective_from_utc": "",
        "effective_to_utc": "",
        "notes": "Current Bybit metadata is used as a research proxy for historical replay.",
    }


def _write_metadata_csv(path: Path, rows: tuple[dict[str, object], ...]) -> None:
    from io import StringIO

    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=_CSV_HEADER, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({column: str(row.get(column, "")) for column in _CSV_HEADER})
    atomic_write_text(path, buffer.getvalue())


def fetch_bybit_spot_metadata_cache(
    *,
    pairs: tuple[str, ...],
    output_root: Path,
    http_get: Any = None,
) -> dict[str, object]:
    """Fetch public Bybit spot instrument metadata and persist a local cache."""

    opener = http_get or urlopen
    output_root = output_root.expanduser().resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    fetched_at_utc = _utc_now_iso()
    rows: list[dict[str, object]] = []
    failure_rows: list[dict[str, object]] = []
    requested_pairs = tuple(dict.fromkeys(_normalize_pair(pair) for pair in pairs if pair))
    for pair in requested_pairs:
        query = urlencode({"category": "spot", "symbol": pair})
        request = Request(
            f"{BYBIT_PUBLIC_INSTRUMENTS_INFO_URL}?{query}",
            headers={"User-Agent": "v53-trading-system/bybit-metadata-fetcher"},
        )
        try:
            with opener(request, timeout=20) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            failure_rows.append(
                {
                    "symbol": pair,
                    "status": "FETCH_FAILED",
                    "reason": str(exc),
                }
            )
            continue
        result = payload.get("result") if isinstance(payload, dict) else None
        instruments = result.get("list") if isinstance(result, dict) else None
        instrument = instruments[0] if isinstance(instruments, list) and instruments else None
        if not isinstance(instrument, dict):
            failure_rows.append(
                {
                    "symbol": pair,
                    "status": "FETCH_FAILED",
                    "reason": "INSTRUMENT_NOT_FOUND",
                }
            )
            continue
        rows.append(_canonical_row_from_instrument(instrument, fetched_at_utc=fetched_at_utc))
    normalized_rows = tuple(_canonicalize_metadata_row(row) for row in rows)
    csv_path = output_root / "symbol_metadata.csv"
    jsonl_path = output_root / "symbol_metadata.jsonl"
    if normalized_rows:
        _write_metadata_csv(csv_path, normalized_rows)
        atomic_write_text(
            jsonl_path,
            "\n".join(
                json.dumps(row, separators=(",", ":"), ensure_ascii=True)
                for row in normalized_rows
            )
            + "\n",
        )
    missing_pairs = tuple(
        sorted(pair for pair in requested_pairs if pair not in {str(row["symbol"]) for row in normalized_rows})
    )
    if normalized_rows and not missing_pairs:
        fetch_status = "BYBIT_PUBLIC_METADATA_FETCH_READY"
    elif normalized_rows:
        fetch_status = "BYBIT_PUBLIC_METADATA_FETCH_PARTIAL"
    else:
        fetch_status = "BYBIT_PUBLIC_METADATA_FETCH_FAILED"
    report = {
        "schema_version": "v1",
        "fetch_status": fetch_status,
        "metadata_source_mode": BYBIT_FETCH_MODE,
        "historical_data_venue": "BYBIT",
        "historical_metadata_purpose": "historical_replay",
        "requested_pairs": list(requested_pairs),
        "pairs_fetched": [str(row["symbol"]) for row in normalized_rows],
        "missing_pairs": list(missing_pairs),
        "metadata_temporal_status": CURRENT_METADATA_PROXY,
        "fetched_at_utc": fetched_at_utc,
        "cache_files": [
            str(csv_path.resolve()) if csv_path.exists() else "",
            str(jsonl_path.resolve()) if jsonl_path.exists() else "",
        ],
        "failure_rows": failure_rows,
    }
    atomic_write_json(output_root / "metadata_fetch_report.json", report, indent=2)
    return report


__all__ = [
    "ACCOUNT_FEE_VERIFIED",
    "BYBIT_FETCH_MODE",
    "BYBIT_HISTORICAL_METADATA_NOT_PROVEN",
    "BYBIT_HISTORICAL_METADATA_READY",
    "BYBIT_METADATA_SOURCE_MODE",
    "BYBIT_PUBLIC_INSTRUMENTS_INFO_URL",
    "BYBIT_RESEARCH_MAKER_FEE_RATE",
    "BYBIT_RESEARCH_TAKER_FEE_RATE",
    "CONFIGURED_FEE_PROVENANCE_READY",
    "CURRENT_METADATA_PROXY",
    "FEE_PROVENANCE_NOT_PROVEN",
    "HistoricalMetadataCacheResult",
    "METADATA_PAIR_NOT_FOUND",
    "METADATA_TEMPORAL_NOT_PROVEN",
    "fetch_bybit_spot_metadata_cache",
    "load_historical_metadata_cache",
]
