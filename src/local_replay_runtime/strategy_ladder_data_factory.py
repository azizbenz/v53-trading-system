"""Patch 6 Data Factory orchestration for the canonical Strategy Ladder rail."""

from __future__ import annotations

import csv
from bisect import bisect_right
from collections.abc import Callable
from datetime import UTC, datetime
import gzip
import hashlib
import json
from math import isfinite
from json import JSONDecodeError
from pathlib import Path
import re
from time import perf_counter
import zipfile

from data_backbone.feature_timeframes import (
    SUPPORTED_GOLD_TIMEFRAMES,
    TIMEFRAME_FEATURE_BUILD_FAILED,
    TIMEFRAME_FEATURE_GENERATION_NOT_SUPPORTED,
    TIMEFRAME_FEATURE_INPUT_MISSING,
    TIMEFRAME_PRUNED_NOT_REQUESTED,
    normalize_timeframe,
)
from data_backbone.market_physics_math import (
    capratio,
    fragility_score_v1,
    sweep_score_v1,
)
from interface_contracts.atomic_io import atomic_write_json, atomic_write_text
from interface_contracts.storage_budget_support import normalize_silver_storage_format
from local_replay_runtime.backtest_replay_dataset_adapter import (
    build_backtest_replay_dataset_manifest,
    write_backtest_replay_dataset_manifest,
)
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
from local_replay_runtime.data_science_quality_gates import (
    build_data_science_quality_report,
    build_runtime_feature_parity_manifest,
    write_quality_reports,
)
from local_replay_runtime.gold_microstructure_feature_builder import (
    build_gold_microstructure_feature_manifest,
    write_gold_feature_reports,
)
from local_replay_runtime.ia_lab_feature_dataset_adapter import (
    build_expected_edge_feature_dataset,
)
from local_replay_runtime.raw_market_data_indexer import (
    build_bronze_market_index,
    scan_bybit_raw_root,
    write_bronze_market_index,
    write_bronze_market_index_markdown,
    write_raw_market_file_manifest_bundle,
)
from local_replay_runtime.silver_market_synchronizer import (
    build_silver_synchronized_market_manifest,
    write_silver_market_reports,
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
    derive_expected_edge_truth_status,
    derive_slippage_truth_status,
)
from local_replay_runtime.strategy_ladder_engine_native_adapter import (
    build_engine_c_microstructure_inputs_from_window,
    build_engine_c_requested_microstructure_features_from_window,
    evict_microstructure_file_cache,
    get_microstructure_file_cache_stats,
    reset_microstructure_file_cache_stats,
)
from local_replay_runtime.strategy_ladder_expected_edge_feature_contracts import (
    DEFAULT_EXPECTED_EDGE_FEATURE_NAMES,
    EXTENDED_MICROSTRUCTURE_EXPECTED_EDGE_FEATURE_NAMES,
    REPLAY_MICROSTRUCTURE_EXPECTED_EDGE_FEATURE_NAMES,
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
_REPLAY_CONTEXT_LOOKBACK_MS = 60 * 60 * 1000
_CRITICAL_OHLCV_TIMEFRAME_INTERVALS_MS: dict[str, int] = {
    "1m": 60_000,
    "10m": 10 * 60_000,
}
_CRITICAL_OHLCV_EXPECTED_ROWS_PER_DAY: dict[str, int] = {
    "1m": 1_440,
    "10m": 144,
}
# Patch D1+D2 (2026-05-21) — severity classifier OHLCV temporal completeness.
# Source raw L: dumps Bybit sont systématiquement tronqués à 1000 rows max
# (limite GET endpoint Bybit non-paginé). Sur 1m=1440 attendus → 1000 disponibles
# (69%); sur 10m=144 attendus → 100 disponibles (69%). Plutôt que fail-close
# total, on accepte les jours partiels au-dessus d'un seuil research-acceptable
# tout en flaggant pour audit. La promotion-grade exige le seuil strict 99%.
# missing_candle_count / duplicate_candle_count > 0 restent fail-close
# (gaps internes ou dupli ≠ truncation propre du suffix).
_OHLCV_DAILY_COMPLETENESS_MIN_ASSESSMENT_ROWS: dict[str, int] = {
    "1m": 100,
    "10m": 10,
}
_A2_ENGINE_NATIVE_BRIDGE_FEATURES = frozenset(
    {
        "kyle_lambda",
        "vpin",
        "cumulative_ofi",
        "queue_pressure",
        "realized_vol_current",
        "realized_vol_at_break",
    }
)
_A2_COST_FEATURES = frozenset(
    {
        "spread_bps",
        "slippage_bps",
        "latency_penalty_bps",
        "book_depth_levels",
    }
)
_A2_MATERIALIZABLE_FEATURES = frozenset(
    (
        *DEFAULT_EXPECTED_EDGE_FEATURE_NAMES,
        *REPLAY_MICROSTRUCTURE_EXPECTED_EDGE_FEATURE_NAMES,
        *EXTENDED_MICROSTRUCTURE_EXPECTED_EDGE_FEATURE_NAMES,
    )
)
_A2_MEASURED_SPREAD_PROVENANCE = frozenset(
    {"MEASURED_FROM_BOOK_SNAPSHOT", "MEASURED_FROM_BOOK_RECONSTRUCTION"}
)
_A2_MEASURED_SLIPPAGE_PROVENANCE = frozenset(
    {
        "MEASURED_FROM_KYLE_LAMBDA",
        "MEASURED_FROM_KYLE_LAMBDA_OVERRIDE",
        "MEASURED_FROM_DEPTH20_BOOK_WALK",
    }
)
_OHLCV_PARTIAL_DAY_RESEARCH_TOLERANCE_RATIO = 0.65
_OHLCV_PARTIAL_DAY_PROMOTION_TOLERANCE_RATIO = 0.99
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


def _compute_metadata_temporal_drift_days(
    *,
    fetched_at_utc: str,
    end_date: str,
) -> float | None:
    if not fetched_at_utc or not end_date:
        return None
    try:
        fetched_at = datetime.fromisoformat(fetched_at_utc)
        replay_end = datetime.fromisoformat(f"{end_date}T23:59:59+00:00")
    except ValueError:
        return None
    return round(abs((fetched_at - replay_end).total_seconds()) / 86_400.0, 3)


def _assess_ohlcv_temporal_completeness(
    *,
    index_entries: tuple[StrategyLadderSilverIndexEntry, ...],
    requested_timeframes: tuple[str, ...],
    expected_dates: tuple[str, ...] = (),
) -> tuple[str, int, tuple[str, ...], tuple[str, ...]]:
    critical_timeframes = tuple(
        tf for tf in requested_timeframes if tf in _CRITICAL_OHLCV_EXPECTED_ROWS_PER_DAY
    )
    if not critical_timeframes:
        return "OHLCV_TEMPORAL_COMPLETENESS_NOT_PROVEN", 0, (), ()
    observed_entries_by_timeframe = {tf: 0 for tf in critical_timeframes}
    blocker_codes: list[str] = []
    blocked_entry_count = 0
    partial_accepted_entry_count = 0
    has_promotion_partial_only = False
    for entry in index_entries:
        if entry.data_type != "ohlcv":
            continue
        if expected_dates and entry.date and entry.date not in expected_dates:
            continue
        timeframe = entry.timeframe or ""
        expected_rows = _CRITICAL_OHLCV_EXPECTED_ROWS_PER_DAY.get(timeframe)
        expected_interval_ms = _CRITICAL_OHLCV_TIMEFRAME_INTERVALS_MS.get(timeframe)
        if expected_rows is None or expected_interval_ms is None:
            continue
        observed_entries_by_timeframe[timeframe] = observed_entries_by_timeframe.get(
            timeframe,
            0,
        ) + 1
        # Patch D1+D2 (2026-05-21) — severity classifier
        # Conditions FAIL-CLOSE NON tolerées (interval mismatch / gaps internes /
        # dupli) — toujours BLOCKED car indique data integrity violée.
        hard_fail = (
            entry.expected_interval_ms != expected_interval_ms
            or entry.missing_candle_count > 0
            or entry.duplicate_candle_count > 0
        )
        if hard_fail:
            blocker_codes.append(
                f"OHLCV_{timeframe.upper()}_TEMPORAL_COMPLETENESS_BLOCKED"
            )
            blocked_entry_count += 1
            continue
        # Condition row_count != expected_rows : classifier par severity.
        if entry.row_count == expected_rows:
            continue  # READY pour ce row
        min_assessment_rows = _OHLCV_DAILY_COMPLETENESS_MIN_ASSESSMENT_ROWS.get(
            timeframe,
            1,
        )
        if entry.row_count < min_assessment_rows:
            blocker_codes.append(
                f"OHLCV_{timeframe.upper()}_TEMPORAL_COMPLETENESS_NOT_PROVEN"
            )
            continue
        ratio = (
            entry.row_count / float(expected_rows) if expected_rows > 0 else 0.0
        )
        if ratio >= _OHLCV_PARTIAL_DAY_PROMOTION_TOLERANCE_RATIO:
            # ≥99% : research-acceptable ET promotion-acceptable (rounding only)
            continue
        if ratio >= _OHLCV_PARTIAL_DAY_RESEARCH_TOLERANCE_RATIO:
            # 65-99% : research-acceptable, promotion BLOCKED
            blocker_codes.append(
                f"OHLCV_{timeframe.upper()}_PARTIAL_DAY_ACCEPTED"
            )
            partial_accepted_entry_count += 1
            has_promotion_partial_only = True
            continue
        # <65% : fail-close research et promotion
        blocker_codes.append(
            f"OHLCV_{timeframe.upper()}_TEMPORAL_COMPLETENESS_BLOCKED"
        )
        blocked_entry_count += 1
    for timeframe, count in observed_entries_by_timeframe.items():
        if count <= 0:
            blocker_codes.append(
                f"OHLCV_{timeframe.upper()}_TEMPORAL_COMPLETENESS_NOT_PROVEN"
            )
    deduped_blockers = tuple(dict.fromkeys(blocker_codes))
    has_hard_block = any(
        b.endswith("_TEMPORAL_COMPLETENESS_BLOCKED") for b in deduped_blockers
    )
    if not deduped_blockers:
        status = "OHLCV_TEMPORAL_COMPLETENESS_READY"
    elif has_hard_block:
        status = "OHLCV_TEMPORAL_COMPLETENESS_BLOCKED"
    elif has_promotion_partial_only:
        # Seulement PARTIAL_DAY_ACCEPTED → research-grade OK, promotion-grade NON
        status = "OHLCV_TEMPORAL_COMPLETENESS_PARTIAL_DAY_ACCEPTED"
    else:
        status = "OHLCV_TEMPORAL_COMPLETENESS_NOT_PROVEN"
    return status, blocked_entry_count, critical_timeframes, deduped_blockers
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


def _finite_record_value(record: object | None) -> float | None:
    if record is None:
        return None
    value = getattr(record, "value", None)
    if isinstance(value, bool):
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return numeric if isfinite(numeric) else None


def _a2_cost_feature_truth_status(
    *,
    spread_provenance: str,
    slippage_provenance: str,
) -> str:
    if (
        spread_provenance in _A2_MEASURED_SPREAD_PROVENANCE
        and slippage_provenance in _A2_MEASURED_SLIPPAGE_PROVENANCE
    ):
        return "A2_COST_FEATURES_MEASURED_EX_ANTE_NOT_EXECUTION_LABEL_TRUTH"
    return "A2_COST_FEATURES_RESEARCH_ONLY_NOT_REPLAY_TRUTH"


def _timeframe_interval_ms(value: str | None) -> int:
    timeframe = normalize_timeframe(value) or "1m"
    match = re.fullmatch(r"(?P<count>\d+)(?P<unit>[mhd])", timeframe)
    if not match:
        return 60_000
    count = max(int(match.group("count")), 1)
    unit = match.group("unit")
    if unit == "h":
        return count * 60 * 60_000
    if unit == "d":
        return count * 24 * 60 * 60_000
    return count * 60_000


def _requested_a2_feature_names(request: StrategyLadderDataFactoryRequest) -> frozenset[str]:
    return frozenset(
        feature_name
        for feature_name in (request.feature_names or DEFAULT_EXPECTED_EDGE_FEATURE_NAMES)
        if feature_name in _A2_MATERIALIZABLE_FEATURES
    )


_A2_GOLD_HEARTBEAT_ROW_INTERVAL = 25
_A2_MICROSTRUCTURE_CACHE_EVICT_ROW_THRESHOLD = 100_000


def _entry_path(entry: StrategyLadderSilverIndexEntry | None) -> Path | None:
    if entry is None or not entry.path:
        return None
    return Path(entry.path)


def _feature_overlay_from_engine_native_bridge(
    *,
    requested_feature_names: frozenset[str],
    pair: str,
    timeframe: str,
    timestamp_ms: int,
    raw_trade_path: Path | None,
    snapshot_book_path: Path | None,
    delta_book_path: Path | None,
) -> dict[str, object]:
    if not requested_feature_names.intersection(_A2_ENGINE_NATIVE_BRIDGE_FEATURES):
        return {}
    if raw_trade_path is None and snapshot_book_path is None:
        return {}
    window_end_ms = max(timestamp_ms, 0)
    window_start_ms = max(0, window_end_ms - _timeframe_interval_ms(timeframe))
    try:
        values = build_engine_c_requested_microstructure_features_from_window(
            pair=pair,
            window_start_ms=window_start_ms,
            window_end_ms=window_end_ms,
            requested_feature_names=requested_feature_names,
            raw_trade_path=raw_trade_path,
            raw_book_path=snapshot_book_path,
            raw_book_delta_path=delta_book_path,
        )
        if values:
            return dict(values)
    except Exception:  # noqa: BLE001 - fallback below preserves old behavior.
        pass
    try:
        bridge = build_engine_c_microstructure_inputs_from_window(
            candidate_id=f"a2-gold:{pair}:{timeframe}:{timestamp_ms}",
            pair=pair,
            window_start_ms=window_start_ms,
            window_end_ms=window_end_ms,
            raw_trade_path=raw_trade_path,
            raw_book_path=snapshot_book_path,
            raw_book_delta_path=delta_book_path,
        )
    except Exception:  # noqa: BLE001 - row stays explicit-missing on bridge failure.
        return {}
    values: dict[str, object] = {}
    candidates = {
        "kyle_lambda": _finite_record_value(bridge.kyle_lambda_record),
        "vpin": _finite_record_value(bridge.vpin_record),
        "cumulative_ofi": _finite_record_value(bridge.ofi_record),
        "queue_pressure": _finite_record_value(bridge.queue_pressure_record),
        "realized_vol_current": _finite_record_value(bridge.realized_kernel_vol_record),
        "realized_vol_at_break": _finite_record_value(bridge.realized_kernel_vol_record),
    }
    for feature_name, value in candidates.items():
        if feature_name in requested_feature_names and value is not None:
            values[feature_name] = value
    return values


def _feature_overlay_batch_from_engine_native_bridge(
    *,
    requested_feature_names: frozenset[str],
    pair: str,
    timeframe: str,
    rows: list[dict[str, object]],
    entry_trade_entries: tuple[StrategyLadderSilverIndexEntry, ...],
    entry_book_entries: tuple[StrategyLadderSilverIndexEntry, ...],
    progress_callback: Callable[[int, int, int], None] | None = None,
) -> tuple[dict[int, dict[str, object]], dict[str, object]]:
    requested_microstructure_features = tuple(
        sorted(requested_feature_names.intersection(_A2_ENGINE_NATIVE_BRIDGE_FEATURES))
    )
    if not requested_microstructure_features:
        return {}, {
            "batch_status": "A2_MICROSTRUCTURE_STREAMING_NOT_REQUIRED",
            "requested_row_count": 0,
            "overlay_row_count": 0,
            "missing_row_count": 0,
            "requested_features": (),
        }
    if not entry_trade_entries and not entry_book_entries:
        return {}, {
            "batch_status": "A2_MICROSTRUCTURE_STREAMING_NO_SOURCE",
            "requested_row_count": len(rows),
            "overlay_row_count": 0,
            "missing_row_count": len(rows),
            "requested_features": requested_microstructure_features,
        }

    overlays_by_timestamp: dict[int, dict[str, object]] = {}
    missing_row_count = 0
    raw_trade_path = _entry_path(entry_trade_entries[0]) if entry_trade_entries else None
    total_rows = len(rows)
    for row_index, row in enumerate(rows, start=1):
        timestamp_raw = row.get("timestamp_ms")
        if not isinstance(timestamp_raw, (int, float)):
            missing_row_count += 1
            if progress_callback and (
                row_index == 1
                or row_index % _A2_GOLD_HEARTBEAT_ROW_INTERVAL == 0
                or row_index == total_rows
            ):
                progress_callback(row_index, len(overlays_by_timestamp), missing_row_count)
            continue
        timestamp_ms = int(timestamp_raw)
        row_book_entries = _book_entries_covering_timestamp(
            entry_book_entries,
            timestamp_ms=timestamp_ms,
        )
        snapshot_book_entry = next(
            (
                item
                for item in row_book_entries
                if item.data_type in {"orderbook_snapshot", "orderbook"} and item.path
            ),
            None,
        )
        delta_book_entry = next(
            (
                item
                for item in row_book_entries
                if item.data_type == "orderbook_delta" and item.path
            ),
            None,
        )
        overlay = _feature_overlay_from_engine_native_bridge(
            requested_feature_names=requested_feature_names,
            pair=pair,
            timeframe=timeframe,
            timestamp_ms=timestamp_ms,
            raw_trade_path=raw_trade_path,
            snapshot_book_path=_entry_path(snapshot_book_entry),
            delta_book_path=_entry_path(delta_book_entry),
        )
        if overlay:
            overlays_by_timestamp[timestamp_ms] = overlay
        else:
            missing_row_count += 1
        if progress_callback and (
            row_index == 1
            or row_index % _A2_GOLD_HEARTBEAT_ROW_INTERVAL == 0
            or row_index == total_rows
        ):
            progress_callback(row_index, len(overlays_by_timestamp), missing_row_count)

    status = (
        "A2_MICROSTRUCTURE_STREAMING_READY"
        if overlays_by_timestamp
        else "A2_MICROSTRUCTURE_STREAMING_NO_VALUES"
    )
    return overlays_by_timestamp, {
        "batch_status": status,
        "requested_row_count": len(rows),
        "overlay_row_count": len(overlays_by_timestamp),
        "missing_row_count": missing_row_count,
        "requested_features": requested_microstructure_features,
        "builder_mode": "REQUESTED_ONLY_CANONICAL_CALCULATOR_BATCH",
        "equivalence_status": "CANONICAL_CALCULATORS_REUSED_NO_TRADING_DECISION_CHANGE",
    }


def _book_resiliency_penalty(book_status: str) -> float:
    if book_status == "BOOK_DEPTH20_AVAILABLE":
        return 0.0
    if book_status == "BOOK_LIMITED_DEPTH_AVAILABLE":
        return 0.35
    if book_status == "BOOK_TOP_OF_BOOK_ONLY":
        return 0.65
    return 1.0


def _session_tag(timestamp_ms: int) -> str:
    timestamp = datetime.fromtimestamp(max(timestamp_ms, 0) / 1000.0, tz=UTC)
    if timestamp.hour < 8:
        bucket = "ASIA"
    elif timestamp.hour < 16:
        bucket = "EUROPE"
    else:
        bucket = "US"
    weekday = "WEEKEND" if timestamp.weekday() >= 5 else "WEEKDAY"
    return f"UTC_{bucket}|{weekday}"


def _false_breakout_context(
    *,
    open_price: float,
    high_price: float,
    low_price: float,
    close_price: float,
    volume: float,
    trailing_mean_volume: float,
) -> float:
    epsilon = 1e-12
    candle_range = max(high_price - low_price, epsilon)
    candle_body = abs(close_price - open_price)
    upper_wick = max(high_price - max(open_price, close_price), 0.0)
    lower_wick = max(min(open_price, close_price) - low_price, 0.0)
    wick_ratio = max(upper_wick, lower_wick) / max(candle_body, candle_range * 0.1, epsilon)
    vol_burst = volume / max(trailing_mean_volume, epsilon)
    reject_indicator = (
        1.0
        if candle_body <= candle_range * 0.35 and max(upper_wick, lower_wick) >= candle_range * 0.4
        else 0.0
    )
    return float(
        sweep_score_v1(
            wick_ratio=wick_ratio,
            vol_burst=vol_burst,
            reject_indicator=reject_indicator,
        )
    )


def _fragility_context(
    *,
    open_price: float,
    high_price: float,
    low_price: float,
    spread_bps: float,
    book_status: str,
) -> float:
    if open_price <= 0.0:
        return 0.0
    price_range_bps = abs((high_price - low_price) / open_price) * 10_000.0
    base_fragility = capratio(price_range_bps, 35.0)
    spread_regime_penalty = capratio(spread_bps, 8.0)
    return float(
        fragility_score_v1(
            base_fragility,
            spread_regime_penalty=spread_regime_penalty,
            book_resiliency_penalty=_book_resiliency_penalty(book_status),
        )
    )


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


def _timestamp_in_window(
    timestamp_ms: int,
    *,
    start_ms: int | None,
    end_ms: int | None,
) -> bool:
    if start_ms is not None and timestamp_ms < start_ms:
        return False
    if end_ms is not None and timestamp_ms > end_ms:
        return False
    return True


def _gold_row_timestamp_ms(row: dict[str, object]) -> int:
    try:
        return int(row.get("timestamp_ms") or row.get("startTime") or row.get("starttime") or 0)
    except (TypeError, ValueError):
        return 0


def _gold_row_in_requested_window(
    row: dict[str, object],
    *,
    start_ms: int | None,
    end_ms: int | None,
) -> bool:
    timestamp_ms = _gold_row_timestamp_ms(row)
    if start_ms is not None and timestamp_ms < start_ms:
        return False
    if end_ms is not None and timestamp_ms > end_ms:
        return False
    return True


def _gold_row_has_temporal_book_coverage(
    row: dict[str, object],
    book_entries: tuple[StrategyLadderSilverIndexEntry, ...] = (),
) -> bool:
    timestamp_ms = _gold_row_timestamp_ms(row)
    for entry in book_entries:
        if entry.min_timestamp_ms is None or entry.max_timestamp_ms is None:
            return True
        if entry.min_timestamp_ms <= timestamp_ms <= entry.max_timestamp_ms:
            return True
    return False


def _book_entries_covering_timestamp(
    entries: tuple[StrategyLadderSilverIndexEntry, ...],
    *,
    timestamp_ms: int,
) -> tuple[StrategyLadderSilverIndexEntry, ...]:
    covered: list[StrategyLadderSilverIndexEntry] = []
    for entry in entries:
        if entry.min_timestamp_ms is None or entry.max_timestamp_ms is None:
            covered.append(entry)
            continue
        if entry.min_timestamp_ms <= timestamp_ms <= entry.max_timestamp_ms:
            covered.append(entry)
    return tuple(covered)


def _prioritize_requested_window_rows(
    rows: tuple[dict[str, object], ...] | list[dict[str, object]],
    *,
    start_ms: int | None,
    end_ms: int | None,
    book_entries: tuple[StrategyLadderSilverIndexEntry, ...] = (),
) -> list[dict[str, object]]:
    if start_ms is None and end_ms is None and not book_entries:
        return list(rows)
    in_window_with_book: list[dict[str, object]] = []
    in_window_without_book: list[dict[str, object]] = []
    context_with_book: list[dict[str, object]] = []
    context_without_book: list[dict[str, object]] = []
    for row in rows:
        in_window = _gold_row_in_requested_window(
            row,
            start_ms=start_ms,
            end_ms=end_ms,
        )
        has_book = _gold_row_has_temporal_book_coverage(row, book_entries)
        if in_window and has_book:
            in_window_with_book.append(row)
        elif in_window:
            in_window_without_book.append(row)
        elif has_book:
            context_with_book.append(row)
        else:
            context_without_book.append(row)
    return [
        *in_window_with_book,
        *in_window_without_book,
        *context_with_book,
        *context_without_book,
    ]


def _split_gold_decision_and_context_rows(
    rows: tuple[dict[str, object], ...] | list[dict[str, object]],
    *,
    start_ms: int | None,
    end_ms: int | None,
) -> tuple[list[dict[str, object]], int]:
    if start_ms is None and end_ms is None:
        return list(rows), 0
    decision_rows: list[dict[str, object]] = []
    context_row_count = 0
    for row in rows:
        if _gold_row_in_requested_window(row, start_ms=start_ms, end_ms=end_ms):
            decision_rows.append(row)
        else:
            context_row_count += 1
    return decision_rows, context_row_count


def _gold_entry_requested_window_rank(
    entry: StrategyLadderSilverIndexEntry,
    *,
    start_ms: int | None,
    end_ms: int | None,
) -> tuple[int, str, str]:
    if start_ms is None and end_ms is None:
        return (0, entry.date or "", entry.timeframe or "")
    if _date_in_range(entry.date or "", start_ms=start_ms, end_ms=end_ms):
        return (0, entry.date or "", entry.timeframe or "")
    return (1, entry.date or "", entry.timeframe or "")


def _span_days(start_ms: int | None, end_ms: int | None) -> int:
    if start_ms is None or end_ms is None or end_ms < start_ms:
        return 0
    return int((end_ms - start_ms) / 86_400_000) + 1


def _effective_context_start_ms(start_ms: int | None) -> int | None:
    if start_ms is None:
        return None
    return max(0, start_ms - _REPLAY_CONTEXT_LOOKBACK_MS)


def _effective_context_start_text(normalized_start: str, effective_start_ms: int | None) -> str:
    if effective_start_ms is None:
        return ""
    effective_dt = datetime.fromtimestamp(effective_start_ms / 1000.0, tz=UTC)
    return effective_dt.isoformat(timespec="seconds")


def _date_range_status_for_entry(
    iso_date: str,
    *,
    start_ms: int | None,
    end_ms: int | None,
) -> bool:
    if not iso_date:
        return False
    return _date_in_range(iso_date, start_ms=start_ms, end_ms=end_ms)


def _expected_date_scope(start: str, end: str) -> tuple[str, ...]:
    if not start or not end:
        return ()
    try:
        start_date = datetime.fromisoformat(f"{start[:10]}T00:00:00+00:00").date()
        end_date = datetime.fromisoformat(f"{end[:10]}T00:00:00+00:00").date()
    except ValueError:
        return ()
    if end_date < start_date:
        return ()
    days: list[str] = []
    cursor = start_date
    while cursor <= end_date:
        days.append(cursor.isoformat())
        cursor = datetime.fromtimestamp(
            datetime.combine(cursor, datetime.min.time(), tzinfo=UTC).timestamp()
            + 86_400,
            tz=UTC,
        ).date()
    return tuple(days)


# Patch P1-A5 (2026-05-29) — method_version_hash cache. Computed once at first
# use: SHA256-16 of this module's content + semantic version tag. Captures both
# the version intent and the actual code state for full reproducibility.
_GOLD_METHOD_VERSION_HASH_CACHE: str | None = None


def _gold_method_version_hash() -> str:
    """P1-A5 — SHA256-16 of gold builder module content + version tag."""

    global _GOLD_METHOD_VERSION_HASH_CACHE
    if _GOLD_METHOD_VERSION_HASH_CACHE is None:
        try:
            module_path = Path(__file__).resolve()
            content_hash = hashlib.sha256(module_path.read_bytes()).hexdigest()[:16]
        except OSError:
            content_hash = "unknown"
        _GOLD_METHOD_VERSION_HASH_CACHE = f"strategy_ladder.gold.v1#{content_hash}"
    return _GOLD_METHOD_VERSION_HASH_CACHE


def _feature_set_hash(feature_values: dict[str, object]) -> str:
    """P1-A6 — Deterministic SHA256-16 of the active feature names set.

    Used per-row so audit can verify reproducibility: same feature set →
    same hash. If features drift (e.g. a new microstructure feature added
    silently), the hash changes and validators upstream can flag mismatches.
    """

    names_csv = ",".join(sorted(str(k) for k in feature_values.keys()))
    return hashlib.sha256(names_csv.encode("utf-8")).hexdigest()[:16]


def _raw_catalog_ref(entry: StrategyLadderSilverIndexEntry) -> str:
    """P1-A4 — Canonical raw catalog reference for the silver index entry.

    Format: `silver:<source_id>:<exchange>:<market_type>:<data_type>:<pair>:<date>`
    Deterministic key that lets downstream audit trace any gold row back to
    its source silver index entry without ambiguity.
    """

    return (
        f"silver:{entry.source_id}:{entry.exchange}:{entry.market_type}:"
        f"{entry.data_type}:{entry.pair}:{entry.date}"
    )


def _ensure_input_data_hash(entry: StrategyLadderSilverIndexEntry) -> str:
    """P1-A1 — Populate input_data_hash even when entry.file_hash is empty.

    The v2 resume optimization (cf. RESUME-INDEX-GAP fix) stores resume entries
    with `file_hash=""` as stat-only placeholders. For gold reproducibility we
    need a real content hash — compute it lazily here when the gold row is
    being built. The cost (one SHA256 per resume entry consumed by gold) is
    amortized over gold building and only paid for entries actually used.
    """

    if entry.file_hash:
        return entry.file_hash
    try:
        path = Path(entry.path)
        if not path.is_file():
            return ""
        if path.stat().st_size == 0:
            return ""
        return _sha256_path(path)
    except OSError:
        return ""


def _entry_has_silver_data(entry: StrategyLadderSilverIndexEntry) -> bool:
    """Patch RESUME-INDEX-GAP (2026-05-29): treat resume placeholders as 'has data'.

    Resume entries built by `_resume_silver_file_eligible` use `row_count=0` +
    `file_hash=""` as stat-only placeholders that reference real silver files
    on disk containing data. Without this check, downstream consumers
    (pair_universe, coverage filters, gold builder) reject them as "no data"
    via `entry.row_count > 0`, leading to `PAIR_UNIVERSE_EMPTY` even though
    silver files are present and indexed.

    Returns True when:
      - `row_count > 0` (canonical counted entry), OR
      - `row_count == 0` and `file_hash == ""` (resume placeholder) AND
        the on-disk file exists with non-zero size.
    """

    if entry.row_count > 0:
        return True
    if entry.row_count == 0 and entry.file_hash == "":
        try:
            path = Path(entry.path)
            return path.is_file() and path.stat().st_size > 0
        except OSError:
            return False
    return False


def _data_type_dates(
    silver_index: tuple[StrategyLadderSilverIndexEntry, ...],
    *,
    data_types: set[str],
) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                entry.date
                for entry in silver_index
                if entry.data_type in data_types and entry.date and _entry_has_silver_data(entry)
            }
        )
    )


def _coverage_status_for_dates(
    *,
    expected_dates: tuple[str, ...],
    observed_dates: tuple[str, ...],
    ready_status: str,
    partial_status: str,
    missing_status: str,
) -> str:
    if not expected_dates:
        return ready_status if observed_dates else missing_status
    observed = set(observed_dates)
    if all(day in observed for day in expected_dates):
        return ready_status
    return partial_status if observed else missing_status


def _build_data_factory_prod_safety_report(
    *,
    request: StrategyLadderDataFactoryRequest,
    manifest: StrategyLadderDataFactoryManifest,
    data_quality: StrategyLadderDataQualityReport,
    silver_index: tuple[StrategyLadderSilverIndexEntry, ...],
    gold_manifest: StrategyLadderGoldFeatureManifest,
    storage_budget_report: object,
    normalized_start: str,
    normalized_end: str,
) -> dict[str, object]:
    expected_dates = _expected_date_scope(normalized_start, normalized_end)
    trade_dates = _data_type_dates(silver_index, data_types={"trades"})
    kline_dates = _data_type_dates(silver_index, data_types={"ohlcv", "klines"})
    orderbook_dates = _data_type_dates(
        silver_index,
        data_types={"orderbook", "orderbook_snapshot", "orderbook_delta"},
    )
    depth20_dates = tuple(
        sorted(
            {
                entry.date
                for entry in silver_index
                if entry.data_type in {"orderbook", "orderbook_snapshot", "orderbook_delta"}
                and entry.date
                and _entry_has_silver_data(entry)
                and entry.depth_source_status == "BOOK_DEPTH20_AVAILABLE"
            }
        )
    )
    trade_coverage_status = _coverage_status_for_dates(
        expected_dates=expected_dates,
        observed_dates=trade_dates,
        ready_status="TRADES_WINDOW_COVERED",
        partial_status="TRADES_WINDOW_PARTIAL",
        missing_status="TRADES_WINDOW_MISSING",
    )
    kline_coverage_status = _coverage_status_for_dates(
        expected_dates=expected_dates,
        observed_dates=kline_dates,
        ready_status="KLINES_WINDOW_COVERED",
        partial_status="KLINES_WINDOW_PARTIAL",
        missing_status="KLINES_WINDOW_MISSING",
    )
    orderbook_coverage_status = _coverage_status_for_dates(
        expected_dates=expected_dates,
        observed_dates=orderbook_dates,
        ready_status="ORDERBOOK_WINDOW_COVERED",
        partial_status="ORDERBOOK_WINDOW_PARTIAL",
        missing_status="ORDERBOOK_WINDOW_MISSING",
    )
    depth20_coverage_status = _coverage_status_for_dates(
        expected_dates=expected_dates,
        observed_dates=depth20_dates,
        ready_status="ORDERBOOK_DEPTH20_WINDOW_COVERED",
        partial_status="ORDERBOOK_DEPTH20_WINDOW_PARTIAL",
        missing_status="ORDERBOOK_DEPTH20_WINDOW_MISSING",
    )
    blocker_codes: list[str] = list(data_quality.blocker_codes)
    if request.dry_run:
        blocker_codes.append("DATA_FACTORY_DRY_RUN_NOT_PROD_SAFE")
    if manifest.data_factory_status != "DATA_FACTORY_READY":
        blocker_codes.append("DATA_FACTORY_NOT_READY")
    if manifest.raw_source_status != "RAW_SOURCE_READY":
        blocker_codes.append("RAW_SOURCE_NOT_READY")
    if manifest.silver_index_status != "SILVER_INDEX_READY":
        blocker_codes.append("SILVER_INDEX_NOT_READY")
    if manifest.gold_feature_store_status not in {
        "GOLD_FEATURE_STORE_READY",
        "FEATURE_STORE_READY",
    }:
        blocker_codes.append("GOLD_FEATURE_STORE_NOT_READY")
    if trade_coverage_status != "TRADES_WINDOW_COVERED":
        blocker_codes.append("TRADES_WINDOW_NOT_COVERED")
    if kline_coverage_status != "KLINES_WINDOW_COVERED":
        blocker_codes.append("KLINES_WINDOW_NOT_COVERED")
    if orderbook_coverage_status != "ORDERBOOK_WINDOW_COVERED":
        blocker_codes.append("ORDERBOOK_WINDOW_NOT_COVERED")
    if depth20_coverage_status != "ORDERBOOK_DEPTH20_WINDOW_COVERED":
        blocker_codes.append("ORDERBOOK_DEPTH20_NOT_PROVEN")
    if data_quality.ohlcv_temporal_completeness_status == "OHLCV_TEMPORAL_COMPLETENESS_BLOCKED":
        blocker_codes.append("DATA_FACTORY_GAPS_EXCEED_TOLERANCE")
    if data_quality.silver_index_date_range_status == "SILVER_INDEX_DATE_RANGE_VIOLATION":
        blocker_codes.append("DATA_FACTORY_DATE_RANGE_VIOLATION")
    if data_quality.historical_metadata_status != BYBIT_HISTORICAL_METADATA_READY:
        blocker_codes.append("METADATA_NOT_PROD_PROVEN")
    if data_quality.fee_provenance_status not in {
        CONFIGURED_FEE_PROVENANCE_READY,
        "FEE_SOURCE_PROVEN",
        "FEE_PROVENANCE_READY",
    }:
        blocker_codes.append("FEE_PROVENANCE_NOT_PROD_PROVEN")
    if manifest.pair_generalization_status != "MULTI_PAIR_GENERALIZATION_READY":
        blocker_codes.append("SINGLE_PAIR_RESEARCH_ONLY")
    if manifest.silver_storage_format != "jsonl_gz":
        blocker_codes.append("SILVER_STORAGE_NOT_COMPRESSED")
    if getattr(storage_budget_report, "storage_budget_status", "") not in {
        "STORAGE_BUDGET_READY",
        "STORAGE_BUDGET_WARNING",
    }:
        blocker_codes.append("STORAGE_BUDGET_NOT_READY")
    if not normalized_start or not normalized_end:
        blocker_codes.append("DATE_RANGE_NOT_PROVEN")

    blocker_codes = list(dict.fromkeys(code for code in blocker_codes if code))
    truth_blockers = {
        "TRADES_WINDOW_NOT_COVERED",
        "KLINES_WINDOW_NOT_COVERED",
        "ORDERBOOK_WINDOW_NOT_COVERED",
        "ORDERBOOK_DEPTH20_NOT_PROVEN",
        "DATA_FACTORY_GAPS_EXCEED_TOLERANCE",
        "DATA_FACTORY_DATE_RANGE_VIOLATION",
        "DATA_FACTORY_NOT_READY",
        "RAW_SOURCE_NOT_READY",
        "SILVER_INDEX_NOT_READY",
        "GOLD_FEATURE_STORE_NOT_READY",
    }
    truth_candidate_status = (
        "DATA_FACTORY_TRUTH_CANDIDATE"
        if not set(blocker_codes).intersection(truth_blockers)
        else "DATA_FACTORY_TRUTH_CANDIDATE_BLOCKED"
    )
    prod_safety_status = (
        "DATA_FACTORY_PROD_SAFE"
        if not blocker_codes
        else "RESEARCH_ONLY_NOT_PROD_SAFE"
    )
    # Patch P6 (2026-05-29) — A8 audit-conformant `allowed_usage` /
    # `blocked_usage` arrays. When prod_safe=False the data may only be used
    # for research/audit, never for ML promotion / profitability truth / live.
    is_prod_safe = prod_safety_status == "DATA_FACTORY_PROD_SAFE"
    allowed_usage = (
        (
            "RESEARCH",
            "B1_DISCOVERY",
            "B_ML_TRAINING_GOVERNED",
            "PROFITABILITY_TRUTH",
            "LIVE_PROMOTION",
        )
        if is_prod_safe
        else (
            "RESEARCH",
            "B1_DISCOVERY",
            "AUDIT",
            "B_ML_TRAINING_RESEARCH_ONLY",
        )
    )
    blocked_usage = (
        ()
        if is_prod_safe
        else (
            "ML_PROMOTION_TRAINING",
            "PROFITABILITY_TRUTH",
            "LIVE_PROMOTION",
            "BACKTEST_INSTITUTIONAL_VERDICT",
        )
    )
    return {
        "schema_version": "strategy_ladder.a2_gold_prod_safety_contract.v2",
        "run_id": request.run_id,
        "prod_safety_status": prod_safety_status,
        "truth_candidate_status": truth_candidate_status,
        "prod_safe": is_prod_safe,
        "allowed_usage": list(allowed_usage),
        "blocked_usage": list(blocked_usage),
        "requested_pairs": request.pairs,
        "start": normalized_start,
        "end": normalized_end,
        "expected_dates": expected_dates,
        "coverage": {
            "trades": {
                "status": trade_coverage_status,
                "observed_dates": trade_dates,
            },
            "klines": {
                "status": kline_coverage_status,
                "observed_dates": kline_dates,
            },
            "orderbook": {
                "status": orderbook_coverage_status,
                "observed_dates": orderbook_dates,
            },
            "orderbook_depth20": {
                "status": depth20_coverage_status,
                "observed_dates": depth20_dates,
            },
        },
        "quality_status": {
            "data_factory_status": manifest.data_factory_status,
            "raw_source_status": manifest.raw_source_status,
            "silver_index_status": manifest.silver_index_status,
            "gold_feature_store_status": manifest.gold_feature_store_status,
            "ohlcv_temporal_completeness_status": data_quality.ohlcv_temporal_completeness_status,
            "metadata_status": data_quality.historical_metadata_status,
            "fee_provenance_status": data_quality.fee_provenance_status,
            "pair_generalization_status": manifest.pair_generalization_status,
            "silver_storage_format": manifest.silver_storage_format,
            "silver_storage_status": manifest.silver_storage_status,
            "storage_budget_status": getattr(storage_budget_report, "storage_budget_status", ""),
            "gold_timeframes_generated": getattr(
                gold_manifest,
                "gold_timeframes_generated",
                getattr(gold_manifest, "timeframe_scope", ()),
            ),
        },
        "blocker_codes": tuple(blocker_codes),
        "created_at": datetime.now(tz=UTC).isoformat(),
    }


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


def _read_jsonl_lines(path: Path) -> list[str]:
    if not path.exists():
        return []
    if path.name.lower().endswith(".jsonl.gz"):
        with gzip.open(path, "rt", encoding="utf-8-sig") as handle:
            return [line.rstrip("\n") for line in handle if line.strip()]
    return path.read_text(encoding="utf-8-sig").splitlines()


# Patch RESUME-SILVER (2026-05-29) — opt-in skip of already-written silver files.
# Gated by request.resume. Each normalizer first computes its expected silver
# output path(s); if all required files exist and are non-empty we build a
# minimal SilverIndexEntry (stat-only) and short-circuit the raw read +
# normalize + write. This lets a crashed A2 run resume from the END instead of
# re-processing 12h of already-correct silver.
#
# DESIGN — stat-only, no file content read on the resume path.
# A previous version called _read_jsonl_lines() to compute row_count and
# first/last timestamps, but for ~3 GB of pre-existing orderbook_delta silver
# that meant decompressing ~60 GB of text per resume = 30-60 min of pure I/O
# burn before any new work started. We now skip metadata reconstruction
# entirely: row_count=0, min/max_timestamp_ms=None, file_hash="" act as
# placeholders ("not measured on resume"). Downstream consumers either ignore
# these fields or treat empty/None as "deferred"; no crash, slightly degraded
# fidelity in reports — accepted trade for instant resume.
def _resume_silver_file_eligible(path: Path) -> bool:
    """Return True if the silver file exists and is non-empty.

    A non-empty existing file is treated as "previously normalized successfully".
    This is a deliberate trust assumption: callers MUST delete partial/suspect
    files before re-launching with --resume.
    """

    try:
        return path.exists() and path.stat().st_size > 0
    except OSError:
        return False


def _normalize_trade_file(
    *,
    classification: StrategyLadderRawFileClassification,
    silver_root: Path,
    dry_run: bool,
    storage_format: str = "jsonl",
    window_start_ms: int | None = None,
    window_end_ms: int | None = None,
    resume: bool = False,
) -> tuple[StrategyLadderSilverIndexEntry | None, int, int, int]:
    path = Path(classification.path)
    # Patch RESUME-SILVER (2026-05-29) — short-circuit if silver already exists.
    if (
        resume
        and not dry_run
        and classification.date
        and len(classification.date) >= 10
    ):
        base_output_path = silver_root / classification.exchange / classification.market_type / "trades" / str(classification.pair or "UNKNOWN") / classification.date[:4] / classification.date[5:7] / f"{classification.date[8:10]}.jsonl"
        resume_output_path = _resolve_silver_path(base_output_path, storage_format)
        if _resume_silver_file_eligible(resume_output_path):
            # Stat-only resume entry — no file read, no hash compute.
            entry = StrategyLadderSilverIndexEntry(
                source_id=classification.source_id,
                source_root=classification.source_root,
                exchange=classification.exchange,
                market_type=classification.market_type,
                data_type="trades",
                pair=classification.pair or "UNKNOWN",
                date=classification.date or "",
                path=str(resume_output_path.resolve()),
                storage_format=storage_format,
                min_timestamp_ms=None,
                max_timestamp_ms=None,
                row_count=0,
                file_hash="",
                depth_source_status="BOOK_DEPTH_NOT_PROVEN",
                schema_status="TRADE_SCHEMA_READY",
                timestamp_unit=classification.timestamp_unit or "ms",
            )
            return entry, 0, 0, 0
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
        timestamp_ms = _normalize_timestamp_to_ms(raw_timestamp, unit)
        if not _timestamp_in_window(
            timestamp_ms,
            start_ms=window_start_ms,
            end_ms=window_end_ms,
        ):
            continue
        if raw_trade_id in seen_trade_ids:
            duplicate_count += 1
        seen_trade_ids.add(raw_trade_id)
        side = str(row.get("side") or "").strip().lower()
        if side:
            side_values_seen.add(side)
        normalized.append(
            {
                "timestamp_ms": timestamp_ms,
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
    window_start_ms: int | None = None,
    window_end_ms: int | None = None,
    resume: bool = False,
) -> tuple[StrategyLadderSilverIndexEntry | None, int, int, int]:
    # Patch RESUME-SILVER (2026-05-29) — short-circuit if silver already exists.
    if (
        resume
        and not dry_run
        and classification.date
        and len(classification.date) >= 10
    ):
        base_output_path = silver_root / classification.exchange / classification.market_type / "ohlcv" / str(classification.timeframe or "unknown") / str(classification.pair or "UNKNOWN") / classification.date[:4] / classification.date[5:7] / f"{classification.date[8:10]}.jsonl"
        resume_output_path = _resolve_silver_path(base_output_path, storage_format)
        if _resume_silver_file_eligible(resume_output_path):
            # Stat-only resume entry — no file read, no hash compute.
            expected_interval_ms = _CRITICAL_OHLCV_TIMEFRAME_INTERVALS_MS.get(
                classification.timeframe or ""
            )
            entry = StrategyLadderSilverIndexEntry(
                source_id=classification.source_id,
                source_root=classification.source_root,
                exchange=classification.exchange,
                market_type=classification.market_type,
                data_type="ohlcv",
                pair=classification.pair or "UNKNOWN",
                timeframe=classification.timeframe or "",
                date=classification.date or "",
                path=str(resume_output_path.resolve()),
                storage_format=storage_format,
                min_timestamp_ms=None,
                max_timestamp_ms=None,
                row_count=0,
                file_hash="",
                depth_source_status="BOOK_DEPTH_NOT_PROVEN",
                schema_status="KLINE_SCHEMA_READY",
                timestamp_unit=classification.timestamp_unit or "ms",
                expected_interval_ms=expected_interval_ms,
                missing_candle_count=0,
                duplicate_candle_count=0,
            )
            return entry, 0, 0, 0
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
        if not _timestamp_in_window(
            timestamp_ms,
            start_ms=window_start_ms,
            end_ms=window_end_ms,
        ):
            continue
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
    expected_interval_ms = _CRITICAL_OHLCV_TIMEFRAME_INTERVALS_MS.get(
        classification.timeframe or ""
    )
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
    window_start_ms: int | None = None,
    window_end_ms: int | None = None,
    resume: bool = False,
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
    # Patch RESUME-SILVER (2026-05-29) — short-circuit only if BOTH snapshot
    # and delta silver files exist. Orderbook normalize writes both atomically
    # but sequentially (snapshot then delta), so a crash between writes leaves
    # snapshot without delta. The "both must exist" rule re-normalizes such
    # half-done days, overwriting the suspect snapshot.
    if (
        resume
        and not dry_run
        and date
        and len(date) >= 10
        and pair
        and pair != "UNKNOWN"
    ):
        year = date[:4]
        month = date[5:7]
        day = date[8:10]
        resume_base_snapshot_path = silver_root / classification.exchange / classification.market_type / "orderbook_snapshot" / str(pair) / year / month / f"{day}.jsonl"
        resume_base_delta_path = silver_root / classification.exchange / classification.market_type / "orderbook_delta" / str(pair) / year / month / f"{day}.jsonl"
        resume_snapshot_path = _resolve_silver_path(resume_base_snapshot_path, storage_format)
        resume_delta_path = _resolve_silver_path(resume_base_delta_path, storage_format)
        if (
            _resume_silver_file_eligible(resume_snapshot_path)
            and _resume_silver_file_eligible(resume_delta_path)
        ):
            # Stat-only resume entries — no file read, no hash compute.
            resume_entries = (
                StrategyLadderSilverIndexEntry(
                    source_id=classification.source_id,
                    source_root=classification.source_root,
                    exchange=classification.exchange,
                    market_type=classification.market_type,
                    data_type="orderbook_snapshot",
                    pair=pair,
                    date=date,
                    path=str(resume_snapshot_path.resolve()),
                    storage_format=storage_format,
                    min_timestamp_ms=None,
                    max_timestamp_ms=None,
                    row_count=0,
                    file_hash="",
                    depth_source_status="BOOK_DEPTH20_AVAILABLE",
                    schema_status="ORDERBOOK_SCHEMA_READY",
                    timestamp_unit="ms",
                ),
                StrategyLadderSilverIndexEntry(
                    source_id=classification.source_id,
                    source_root=classification.source_root,
                    exchange=classification.exchange,
                    market_type=classification.market_type,
                    data_type="orderbook_delta",
                    pair=pair,
                    date=date,
                    path=str(resume_delta_path.resolve()),
                    storage_format=storage_format,
                    min_timestamp_ms=None,
                    max_timestamp_ms=None,
                    row_count=0,
                    file_hash="",
                    depth_source_status="BOOK_DEPTH20_AVAILABLE",
                    schema_status="ORDERBOOK_SCHEMA_READY",
                    timestamp_unit="ms",
                ),
            )
            return resume_entries, 0, 0, 0, (), None
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
        if not _timestamp_in_window(
            timestamp_ms,
            start_ms=window_start_ms,
            end_ms=window_end_ms,
        ):
            continue
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
                # Patch A2-OPT-2 (2026-05-26) — Propagate the reconstructor's
                # canonical `book_depth_source_status` to the delta entry as
                # well. The previous logic forced "BOOK_DEPTH_NOT_PROVEN" on
                # delta entries when snapshots existed, which downstream gold
                # compute then picked up via `next()` (often delta-first in the
                # silver_index iteration order) — causing every gold row to be
                # marked NOT_PROVEN even though the reconstruction proved
                # BOOK_DEPTH20_AVAILABLE. Both entries should reflect the same
                # ground truth from the reconstructor.
                depth_source_status=reconstruction.book_depth_source_status,
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
        has_trades = any(entry.data_type == "trades" and _entry_has_silver_data(entry) for entry in pair_entries)
        has_klines = any(entry.data_type == "ohlcv" and _entry_has_silver_data(entry) for entry in pair_entries)
        has_orderbook = any(entry.data_type in {"orderbook_snapshot", "orderbook_delta", "orderbook"} and _entry_has_silver_data(entry) for entry in pair_entries)
        has_metadata = any(entry.data_type == "metadata" and _entry_has_silver_data(entry) for entry in pair_entries)
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


def _write_gold_feature_build_heartbeat(
    *,
    request: StrategyLadderDataFactoryRequest,
    pair: str,
    timeframe: str,
    date: str,
    rows_seen_in_entry: int,
    feature_row_count: int,
    bytes_written: int,
    microstructure_requested_row_count: int,
    microstructure_overlay_row_count: int,
    microstructure_missing_row_count: int,
    stage_detail: str = "gold_row_build_running",
    entry_index: int | None = None,
    entry_count: int | None = None,
    cache_stats: dict[str, object] | None = None,
    extra: dict[str, object] | None = None,
) -> None:
    report_root = request.input_root
    payload: dict[str, object] = {
        "schema_version": "v53.a2_gold_progress_report.v1",
        "run_id": request.run_id,
        "status": "A2_RUNNING",
        "current_stage": "GOLD_FEATURE_BUILD_RUNNING",
        "stage_detail": stage_detail,
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "active_gold_partition": {
            "pair": pair,
            "timeframe": timeframe,
            "date": date,
            "rows_seen_in_entry": rows_seen_in_entry,
        },
        "counters": {
            "gold_feature_row_count": feature_row_count,
            "bytes_written": bytes_written,
            "microstructure_requested_row_count": microstructure_requested_row_count,
            "microstructure_overlay_row_count": microstructure_overlay_row_count,
            "microstructure_missing_row_count": microstructure_missing_row_count,
        },
    }
    if entry_index is not None or entry_count is not None:
        payload["entry_progress"] = {
            "entry_index": entry_index,
            "entry_count": entry_count,
        }
    if cache_stats is not None:
        payload["microstructure_cache"] = dict(cache_stats)
    if extra:
        payload["detail"] = dict(extra)
    try:
        atomic_write_json(
            report_root / "a2_gold_progress_report.json",
            payload,
            indent=2,
        )
    except OSError:
        return


def _microstructure_cache_stats_for_heartbeat() -> dict[str, object]:
    try:
        return get_microstructure_file_cache_stats()
    except Exception as exc:  # noqa: BLE001 - progress report must not fail A2.
        return {
            "cache_status": "A2_MICROSTRUCTURE_CACHE_STATS_UNAVAILABLE",
            "error": exc.__class__.__name__,
        }


def _maybe_evict_microstructure_cache_after_gold_entry(
    *,
    request: StrategyLadderDataFactoryRequest,
    pair: str,
    timeframe: str,
    date: str,
    entry_index: int,
    entry_count: int,
    feature_row_count: int,
    bytes_written: int,
    microstructure_requested_row_count: int,
    microstructure_overlay_row_count: int,
    microstructure_missing_row_count: int,
) -> None:
    stats = _microstructure_cache_stats_for_heartbeat()
    try:
        cached_row_count = int(stats.get("cached_row_count") or 0)
    except (TypeError, ValueError):
        cached_row_count = 0
    if cached_row_count < _A2_MICROSTRUCTURE_CACHE_EVICT_ROW_THRESHOLD:
        return
    evicted = evict_microstructure_file_cache()
    after_stats = _microstructure_cache_stats_for_heartbeat()
    _write_gold_feature_build_heartbeat(
        request=request,
        pair=pair,
        timeframe=timeframe,
        date=date,
        rows_seen_in_entry=0,
        feature_row_count=feature_row_count,
        bytes_written=bytes_written,
        microstructure_requested_row_count=microstructure_requested_row_count,
        microstructure_overlay_row_count=microstructure_overlay_row_count,
        microstructure_missing_row_count=microstructure_missing_row_count,
        stage_detail="microstructure_cache_evicted_after_partition",
        entry_index=entry_index,
        entry_count=entry_count,
        cache_stats=after_stats,
        extra={
            "eviction_reason": "A2_MICROSTRUCTURE_CACHE_ROW_THRESHOLD",
            "eviction_threshold_rows": _A2_MICROSTRUCTURE_CACHE_EVICT_ROW_THRESHOLD,
            **evicted,
        },
    )


def _write_gold_features(
    *,
    request: StrategyLadderDataFactoryRequest,
    index_entries: tuple[StrategyLadderSilverIndexEntry, ...],
    available_pairs: tuple[str, ...],
) -> StrategyLadderGoldFeatureManifest:
    feature_paths: list[str] = []
    feature_row_count = 0
    bytes_written = 0
    microstructure_streaming_batch_count = 0
    microstructure_streaming_requested_row_count = 0
    microstructure_streaming_overlay_row_count = 0
    microstructure_streaming_missing_row_count = 0
    microstructure_streaming_status_counts: dict[str, int] = {}
    gold_context_row_count = 0
    gold_context_rows_suppressed_count = 0
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
        "fragility_false_breakout_features",
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
        normalize_timeframe(timeframe)
        for timeframe in request.timeframes
        if normalize_timeframe(timeframe)
    }
    requested_feature_names = _requested_a2_feature_names(request)
    # Patch 2026-05-15 (timeframe propagation audit) — track silver inputs and
    # per-timeframe build outcomes so prunes between silver and gold are never
    # silent. Reasons are emitted as `blocker_codes` and as the per-timeframe
    # map `pruning_reason_by_timeframe` on the manifest.
    silver_timeframes_set: set[str] = {
        normalize_timeframe(entry.timeframe)
        for entry in index_entries
        if entry.data_type == "ohlcv"
        and normalize_timeframe(entry.timeframe)
    }
    per_timeframe_row_count: dict[str, int] = {}
    per_timeframe_errored: set[str] = set()
    gold_row_limit = (
        int(request.max_gold_feature_rows)
        if request.max_gold_feature_rows > 0
        else 0
    )
    requested_start_ms = parse_time_boundary_to_ms(_normalize_boundary_text(request.start))
    requested_end_ms = parse_time_boundary_to_ms(
        _normalize_boundary_text(request.end),
        end_of_day=True,
    )
    for pair in available_pairs:
        if gold_row_limit and feature_row_count >= gold_row_limit:
            break
        kline_entries = tuple(
            sorted(
                (
                    entry
                    for entry in _group_index_entries(index_entries, pair=pair, data_type="ohlcv")
                    if not requested_timeframes
                    or str(entry.timeframe or "").strip().lower() in requested_timeframes
                ),
                key=lambda entry: _gold_entry_requested_window_rank(
                    entry,
                    start_ms=requested_start_ms,
                    end_ms=requested_end_ms,
                ),
            )
        )
        trade_entries = _group_index_entries(index_entries, pair=pair, data_type="trades")
        book_entries = tuple(
            entry
            for entry in index_entries
            if entry.pair == pair and entry.data_type in {"orderbook_snapshot", "orderbook_delta", "orderbook"} and entry.path
        )
        # Patch P2 (2026-05-29) — A7 venue metadata temporal proof. Track WHICH
        # metadata entry produced the matching row so we can populate
        # metadata_effective_at + metadata_source + metadata_hash on the gold row.
        metadata_entries = _group_index_entries(index_entries, pair=pair, data_type="metadata")
        metadata_row: dict[str, object] = {}
        matched_metadata_entry: StrategyLadderSilverIndexEntry | None = None
        for metadata_entry in metadata_entries:
            metadata_path = Path(metadata_entry.path)
            if not metadata_path.exists():
                continue
            for row in _load_jsonl_rows(metadata_path):
                if _normalize_pair(str(row.get("symbol") or row.get("pair") or "")) == pair:
                    metadata_row = row
                    matched_metadata_entry = metadata_entry
                    break
            if matched_metadata_entry is not None:
                break
        if matched_metadata_entry is not None:
            pair_metadata_effective_at = matched_metadata_entry.date or None
            pair_metadata_source = _raw_catalog_ref(matched_metadata_entry)
            pair_metadata_hash = _ensure_input_data_hash(matched_metadata_entry)
        else:
            pair_metadata_effective_at = None
            pair_metadata_source = None
            pair_metadata_hash = None
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
        entry_count = len(kline_entries)
        for entry_index, entry in enumerate(kline_entries, start=1):
            if gold_row_limit and feature_row_count >= gold_row_limit:
                break
            rows = _load_jsonl_rows(Path(entry.path))
            if not rows:
                continue
            date = entry.date
            year = date[:4] if date else "unknown"
            month = date[5:7] if len(date) >= 7 else "unknown"
            day = date[8:10] if len(date) >= 10 else "unknown"
            output_path = request.gold_root / f"features_{entry.timeframe or '1m'}" / pair / year / f"{month}.jsonl.gz"
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
            if gold_row_limit:
                rows = _prioritize_requested_window_rows(
                    rows,
                    start_ms=requested_start_ms,
                    end_ms=requested_end_ms,
                    book_entries=entry_book_entries,
                )
            context_rows = sorted(rows, key=_gold_row_timestamp_ms)
            decision_rows, context_row_count = _split_gold_decision_and_context_rows(
                context_rows,
                start_ms=requested_start_ms,
                end_ms=requested_end_ms,
            )
            gold_context_row_count += context_row_count
            gold_context_rows_suppressed_count += context_row_count
            if not decision_rows:
                continue
            if gold_row_limit:
                remaining_rows = gold_row_limit - feature_row_count
                if remaining_rows <= 0:
                    break
                decision_rows = decision_rows[:remaining_rows]
            context_timestamps = tuple(_gold_row_timestamp_ms(item) for item in context_rows)
            requested_microstructure_feature_count = len(
                requested_feature_names.intersection(_A2_ENGINE_NATIVE_BRIDGE_FEATURES)
            )
            overlay_requested_row_count = (
                len(decision_rows) if requested_microstructure_feature_count > 0 else 0
            )
            _write_gold_feature_build_heartbeat(
                request=request,
                pair=pair,
                timeframe=entry.timeframe or "1m",
                date=date,
                rows_seen_in_entry=0,
                feature_row_count=feature_row_count,
                bytes_written=bytes_written,
                microstructure_requested_row_count=(
                    microstructure_streaming_requested_row_count + overlay_requested_row_count
                ),
                microstructure_overlay_row_count=microstructure_streaming_overlay_row_count,
                microstructure_missing_row_count=microstructure_streaming_missing_row_count,
                stage_detail=(
                    "microstructure_overlay_start"
                    if requested_microstructure_feature_count > 0
                    else "microstructure_overlay_not_required"
                ),
                entry_index=entry_index,
                entry_count=entry_count,
                cache_stats=_microstructure_cache_stats_for_heartbeat(),
            )

            def _gold_overlay_progress(
                rows_seen: int,
                overlay_row_count: int,
                missing_row_count: int,
            ) -> None:
                _write_gold_feature_build_heartbeat(
                    request=request,
                    pair=pair,
                    timeframe=entry.timeframe or "1m",
                    date=date,
                    rows_seen_in_entry=rows_seen,
                    feature_row_count=feature_row_count,
                    bytes_written=bytes_written,
                    microstructure_requested_row_count=(
                        microstructure_streaming_requested_row_count
                        + overlay_requested_row_count
                    ),
                    microstructure_overlay_row_count=(
                        microstructure_streaming_overlay_row_count + overlay_row_count
                    ),
                    microstructure_missing_row_count=(
                        microstructure_streaming_missing_row_count + missing_row_count
                    ),
                    stage_detail="microstructure_overlay_running",
                    entry_index=entry_index,
                    entry_count=entry_count,
                )

            microstructure_overlay_by_timestamp, microstructure_batch_stats = (
                _feature_overlay_batch_from_engine_native_bridge(
                    requested_feature_names=requested_feature_names,
                    pair=pair,
                    timeframe=entry.timeframe or "1m",
                    rows=list(decision_rows),
                    entry_trade_entries=entry_trade_entries,
                    entry_book_entries=entry_book_entries,
                    progress_callback=_gold_overlay_progress,
                )
            )
            batch_status = str(
                microstructure_batch_stats.get("batch_status")
                or "A2_MICROSTRUCTURE_STREAMING_NOT_PROVEN"
            )
            microstructure_streaming_status_counts[batch_status] = (
                microstructure_streaming_status_counts.get(batch_status, 0) + 1
            )
            if batch_status != "A2_MICROSTRUCTURE_STREAMING_NOT_REQUIRED":
                microstructure_streaming_batch_count += 1
                microstructure_streaming_requested_row_count += int(
                    microstructure_batch_stats.get("requested_row_count") or 0
                )
                microstructure_streaming_overlay_row_count += int(
                    microstructure_batch_stats.get("overlay_row_count") or 0
                )
                microstructure_streaming_missing_row_count += int(
                    microstructure_batch_stats.get("missing_row_count") or 0
                )
            _write_gold_feature_build_heartbeat(
                request=request,
                pair=pair,
                timeframe=entry.timeframe or "1m",
                date=date,
                rows_seen_in_entry=len(decision_rows),
                feature_row_count=feature_row_count,
                bytes_written=bytes_written,
                microstructure_requested_row_count=microstructure_streaming_requested_row_count,
                microstructure_overlay_row_count=microstructure_streaming_overlay_row_count,
                microstructure_missing_row_count=microstructure_streaming_missing_row_count,
                stage_detail="microstructure_overlay_complete",
                entry_index=entry_index,
                entry_count=entry_count,
                cache_stats=_microstructure_cache_stats_for_heartbeat(),
                extra={"batch_status": batch_status},
            )
            trade_count = sum(item.row_count for item in entry_trade_entries)
            for index, row in enumerate(decision_rows, start=1):
                timestamp_ms = int(row.get("timestamp_ms") or 0)
                open_price = float(row.get("open") or 0.0)
                close_price = float(row.get("close") or 0.0)
                high_price = float(row.get("high") or 0.0)
                low_price = float(row.get("low") or 0.0)
                volume = float(row.get("volume") or 0.0)
                row_book_entries = _book_entries_covering_timestamp(
                    entry_book_entries,
                    timestamp_ms=timestamp_ms,
                )
                row_orderbook_feature_status = "ORDERBOOK_FEATURE_STATUS_NOT_PROVEN"
                if any(
                    item.depth_source_status == "BOOK_DEPTH20_AVAILABLE"
                    for item in row_book_entries
                ):
                    row_orderbook_feature_status = "ORDERBOOK_FEATURE_STATUS_READY"
                elif row_book_entries:
                    row_orderbook_feature_status = "ORDERBOOK_FEATURE_STATUS_PARTIAL"
                row_feature_sources_used = tuple(
                    token
                    for token, entries in (
                        ("trades", entry_trade_entries),
                        ("klines", (entry,)),
                        ("orderbook", row_book_entries),
                        ("metadata", metadata_entries),
                    )
                    if entries
                )
                row_candidate_data_source_label = "COMPAT_FEATURE_DISCOVERY"
                if "orderbook" in row_feature_sources_used:
                    row_candidate_data_source_label = "ORDERBOOK_AWARE_DISCOVERY"
                elif {"trades", "klines"} <= set(row_feature_sources_used):
                    row_candidate_data_source_label = "TRADE_KLINE_DISCOVERY"
                elif "klines" in row_feature_sources_used:
                    row_candidate_data_source_label = "KLINE_ONLY_DISCOVERY"
                trailing_end_index = bisect_right(context_timestamps, timestamp_ms)
                trailing_rows = context_rows[max(0, trailing_end_index - 20) : trailing_end_index]
                trailing_mean_volume = (
                    sum(float(item.get("volume") or 0.0) for item in trailing_rows)
                    / max(len(trailing_rows), 1)
                )
                spread_bps = 0.0
                depth_levels = None
                book_status = "BOOK_DEPTH_NOT_PROVEN"
                if row_book_entries:
                    depth_levels = max(
                        (
                            20
                            if item.depth_source_status == "BOOK_DEPTH20_AVAILABLE"
                            else 10
                            if item.depth_source_status == "BOOK_LIMITED_DEPTH_AVAILABLE"
                            else 1
                            if item.depth_source_status == "BOOK_TOP_OF_BOOK_ONLY"
                            else 0
                            for item in row_book_entries
                        ),
                        default=0,
                    )
                    book_status = next(
                        (
                            item.depth_source_status
                            for item in row_book_entries
                            if item.depth_source_status
                        ),
                        "BOOK_DEPTH_NOT_PROVEN",
                    )
                    spread_bps = 4.0 if book_status == "BOOK_DEPTH20_AVAILABLE" else 6.0 if book_status == "BOOK_LIMITED_DEPTH_AVAILABLE" else 0.0

                snapshot_book_entry = next(
                    (
                        item
                        for item in row_book_entries
                        if item.data_type in {"orderbook_snapshot", "orderbook"}
                        and item.path
                    ),
                    None,
                )
                delta_book_entry = next(
                    (
                        item
                        for item in row_book_entries
                        if item.data_type == "orderbook_delta" and item.path
                    ),
                    None,
                )
                snapshot_book_path = _entry_path(snapshot_book_entry)
                delta_book_path = _entry_path(delta_book_entry)
                raw_trade_path = _entry_path(entry_trade_entries[0]) if entry_trade_entries else None
                silver_exchange_for_call = (
                    getattr(snapshot_book_entry, "exchange", "") or ""
                    if snapshot_book_entry is not None
                    else ""
                )
                silver_market_type_for_call = (
                    getattr(snapshot_book_entry, "market_type", "spot") or "spot"
                    if snapshot_book_entry is not None
                    else "spot"
                )

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
                # Audit 2026-05-14 P3-A : tier-aware spread_provenance defaut
                # quand `use_measured_economic_provenance` est off ; sinon
                # ecrase par prov.spread_provenance (cf. bloc plus bas).
                economic_spread_provenance = "DEFAULT_BY_BOOK_STATUS"
                # Audit 2026-05-14 P3-B : tier-aware slippage provenance defaut
                # quand `use_measured_economic_provenance` est off ; sinon
                # ecrase par prov.slippage_provenance (cf. bloc plus bas).
                economic_slippage_provenance = "DEFAULT_TO_CALIBRATE"
                # Patch P3 (2026-05-29) — capture book freshness temporal proof
                # even when use_measured_economic_provenance is off (defaults
                # below). Overwritten if measured path runs.
                economic_book_snapshot_age_ms: int | None = None
                economic_book_freshness_status: str = "BOOK_FRESHNESS_NOT_PROVEN"
                economic_book_freshness_tolerance_ms: int | None = None
                if getattr(request, "use_measured_economic_provenance", False):
                    prov = compute_economic_provenance(
                        timestamp_ms=timestamp_ms,
                        book_status=book_status,
                        pair=pair,
                        # Patch P3 (2026-05-29) — pass timeframe so the spread
                        # measurement derives per-TF tolerance (audit C5).
                        timeframe=entry.timeframe or None,
                        raw_book_path=snapshot_book_path,
                        raw_trade_path=raw_trade_path,
                        raw_ohlcv_path=Path(entry.path),
                        # Audit 2026-05-14 P3-B : flip de False → True. Le
                        # service Kyle lambda est implemente dans
                        # _measure_slippage_from_kyle_lambda ; le flag etait
                        # reste False pendant le design "SLIPPAGE_DEFERRED_TO_
                        # RAW_WINDOW_REPLAY" (stop-gap historique). Active
                        # maintenant pour que slippage_provenance devienne
                        # MEASURED_FROM_KYLE_LAMBDA quand suffisamment de
                        # trades existent, sinon fallback DEFAULT_TO_CALIBRATE
                        # (pas de false READY : echec Kyle ne leve pas le gate).
                        measure_slippage_from_trades=True,
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
                    economic_spread_provenance = prov.spread_provenance
                    economic_slippage_provenance = prov.slippage_provenance
                    # Patch P3 — book freshness temporal proof from prov.
                    # getattr-with-default keeps back-compat with mocked
                    # EconomicProvenance-like objects in legacy tests.
                    economic_book_snapshot_age_ms = getattr(prov, "book_snapshot_age_ms", None)
                    economic_book_freshness_status = getattr(
                        prov, "book_freshness_status", "BOOK_FRESHNESS_NOT_PROVEN"
                    )
                    economic_book_freshness_tolerance_ms = getattr(
                        prov, "book_freshness_tolerance_ms", None
                    )

                execution_fragility = _fragility_context(
                      open_price=open_price,
                      high_price=high_price,
                      low_price=low_price,
                      spread_bps=economic_spread_bps,
                      book_status=book_status,
                  )
                false_breakout_context = _false_breakout_context(
                      open_price=open_price,
                      high_price=high_price,
                      low_price=low_price,
                      close_price=close_price,
                      volume=volume,
                      trailing_mean_volume=trailing_mean_volume,
                  )
                maker_fee_rate = _optional_float(
                      metadata_row.get("maker_fee_rate")
                      or metadata_row.get("maker_fee")
                      or metadata_row.get("makerFee")
                  )
                taker_fee_rate = _optional_float(
                      metadata_row.get("taker_fee_rate")
                      or metadata_row.get("taker_fee")
                      or metadata_row.get("takerFee")
                  )
                break_even_bps = (
                      economic_spread_bps
                      + economic_slippage_bps
                      + max((taker_fee_rate or 0.0) * 10_000.0, 0.0)
                  )
                feature_values = {
                      "close_return": ((close_price - open_price) / open_price) if open_price > 0.0 else 0.0,
                      "high_low_range": ((high_price - low_price) / open_price) if open_price > 0.0 else 0.0,
                      "volume": volume,
                      "trade_count_hint": trade_count,
                      "sweep_score": false_breakout_context,
                      "false_breakout_context": false_breakout_context,
                      "fragility_score": execution_fragility,
                      "fragility": execution_fragility,
                      "break_even_bps": break_even_bps,
                      "session_tags": _session_tag(timestamp_ms),
                  }
                if "spread_bps" in requested_feature_names:
                    feature_values["spread_bps"] = economic_spread_bps
                if "slippage_bps" in requested_feature_names:
                    feature_values["slippage_bps"] = economic_slippage_bps
                if "latency_penalty_bps" in requested_feature_names:
                    feature_values["latency_penalty_bps"] = economic_latency_penalty_bps
                if "book_depth_levels" in requested_feature_names and depth_levels is not None:
                    feature_values["book_depth_levels"] = depth_levels
                feature_values.update(
                    microstructure_overlay_by_timestamp.get(timestamp_ms, {})
                )

                feature_row = StrategyLadderFeatureRow.model_validate(
                      {
                          "timestamp_ms": timestamp_ms,
                          "pair": pair,
                          "timeframe": entry.timeframe or "1m",
                          "engine_scope": request.engines,
                          "feature_values": feature_values,
                          "feature_version": "strategy_ladder.gold.v1",
                          # Patch P1 (2026-05-29) — A1 + A4 + A5 + A6: 4 hashes for
                          # full reproducibility. input_data_hash lazily computed
                          # for resume placeholders, method_version_hash captures
                          # actual gold builder content, raw_catalog_ref ties row
                          # back to silver index entry, feature_set_hash detects
                          # silent feature drift.
                          "input_data_hash": _ensure_input_data_hash(entry),
                          "method_version_hash": _gold_method_version_hash(),
                          "raw_catalog_ref": _raw_catalog_ref(entry),
                          "feature_set_hash": _feature_set_hash(feature_values),
                          # Patch P2 (2026-05-29) — A7 venue metadata temporal proof
                          "metadata_effective_at": pair_metadata_effective_at,
                          "metadata_source": pair_metadata_source,
                          "metadata_hash": pair_metadata_hash,
                          # Patch P3 (2026-05-29) — book freshness temporal proof
                          "book_snapshot_age_ms": economic_book_snapshot_age_ms,
                          "book_freshness_status": economic_book_freshness_status,
                          "book_freshness_tolerance_ms": economic_book_freshness_tolerance_ms,
                          # Patch P4 (2026-05-29) — slippage explicit truth status
                          "slippage_truth_status": derive_slippage_truth_status(
                              economic_slippage_provenance
                          ),
                          # Patch P5 (2026-05-29) — A9 expected-edge schema split.
                          # Proxy value populated when provenance is PROXY_*/DEFAULT;
                          # model value populated when provenance is GOVERNED_*/MEASURED_*.
                          # Mutually exclusive (only one is non-None per row).
                          "expected_edge_proxy_bps": (
                              economic_expected_edge_bps
                              if derive_expected_edge_truth_status(
                                  economic_expected_edge_provenance
                              )
                              in {
                                  "EXPECTED_EDGE_PROXY",
                                  "EXPECTED_EDGE_DEFAULT_PROXY",
                              }
                              else None
                          ),
                          "expected_edge_model_bps": (
                              economic_expected_edge_bps
                              if derive_expected_edge_truth_status(
                                  economic_expected_edge_provenance
                              )
                              in {
                                  "EXPECTED_EDGE_MODEL_GOVERNED",
                                  "EXPECTED_EDGE_MODEL_OVERRIDE",
                              }
                              else None
                          ),
                          "expected_edge_row_truth_status": derive_expected_edge_truth_status(
                              economic_expected_edge_provenance
                          ),
                        "source_ref": str(output_path.resolve()),
                        "available_at_timestamp_ms": timestamp_ms,
                        "feature_truth_boundary_status": (
                            "FEATURE_EX_ANTE_AVAILABLE_AT_DECISION"
                        ),
                        "feature_usage_policy": (
                            "A2_GOLD_EX_ANTE_FEATURES_ONLY_NOT_EXECUTION_TRUTH"
                        ),
                        "cost_feature_truth_status": _a2_cost_feature_truth_status(
                            spread_provenance=economic_spread_provenance,
                            slippage_provenance=economic_slippage_provenance,
                        ),
                        "close_price": close_price,
                        "raw_score": 0.5 + (index / max(len(decision_rows), 1)) * 0.1,
                        "penalized_score": 0.5 + (index / max(len(decision_rows), 1)) * 0.1,
                        "final_score": 0.5 + (index / max(len(decision_rows), 1)) * 0.1,
                        "expected_edge_bps": economic_expected_edge_bps,
                        "expected_edge_provenance": economic_expected_edge_provenance,
                        "economic_provenance": economic_provenance,
                        "economic_measurement_warnings": economic_measurement_warnings,
                        "spread_bps": economic_spread_bps,
                        "spread_provenance": economic_spread_provenance,
                        "slippage_bps": economic_slippage_bps,
                        "slippage_provenance": economic_slippage_provenance,
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
                          "maker_fee_rate": maker_fee_rate,
                          "taker_fee_rate": taker_fee_rate,
                          # Patch P7 (2026-05-29) — fee schedule temporal proof.
                          # Try explicit `fee_schedule_date` field from venue
                          # metadata snapshot, fall back to the silver metadata
                          # entry date (when the snapshot was captured).
                          "fee_schedule_date": (
                              str(metadata_row.get("fee_schedule_date"))
                              if metadata_row.get("fee_schedule_date")
                              else pair_metadata_effective_at
                          ),
                          "book_depth_levels": depth_levels,
                          "book_depth_source_status": book_status,
                          "book_depth_snapshot_count": len(row_book_entries),
                        "book_depth_event_count": len(row_book_entries),
                        "book_depth_missing_count": 0 if row_book_entries else 1,
                        "book_depth_staleness_status": book_status,
                        "planned_notional": 100.0,
                        "allocation_fraction": 0.25,
                        "min_notional": pair_min_notional,
                          "feature_sources_used": row_feature_sources_used,
                          "trade_feature_status": entry_trade_feature_status,
                          "kline_feature_status": kline_feature_status,
                          "orderbook_feature_status": row_orderbook_feature_status,
                          "candidate_data_source_label": row_candidate_data_source_label,
                          "compatibility_notes": (
                              "NOT_LIVE_ENGINE_PARITY",
                              "FRAGILITY_FALSE_BREAKOUT_DISCOVERY_GRADE",
                          ),
                      }
                )
                feature_rows.append(feature_row.model_dump(mode="json"))
                if (
                    index == 1
                    or index % _A2_GOLD_HEARTBEAT_ROW_INTERVAL == 0
                    or index == len(decision_rows)
                ):
                    _write_gold_feature_build_heartbeat(
                        request=request,
                        pair=pair,
                        timeframe=entry.timeframe or "1m",
                        date=date,
                        rows_seen_in_entry=index,
                        feature_row_count=feature_row_count + len(feature_rows),
                        bytes_written=bytes_written,
                        microstructure_requested_row_count=(
                            microstructure_streaming_requested_row_count
                        ),
                        microstructure_overlay_row_count=(
                            microstructure_streaming_overlay_row_count
                        ),
                        microstructure_missing_row_count=(
                            microstructure_streaming_missing_row_count
                        ),
                        stage_detail="gold_row_build_running",
                        entry_index=entry_index,
                        entry_count=entry_count,
                    )
            if feature_rows:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                existing_size = output_path.stat().st_size if output_path.exists() else 0
                merged_lines = [*_read_jsonl_lines(output_path), *_jsonl_dump_lines(feature_rows).splitlines()]
                merged_rows = [json.loads(line) for line in merged_lines if line.strip()]
                merged_rows.sort(key=_gold_row_timestamp_ms)
                _write_rows(output_path, merged_rows, storage_format="jsonl-gz")
                resolved_feature_path = str(output_path.resolve())
                if resolved_feature_path not in feature_paths:
                    feature_paths.append(resolved_feature_path)
                bytes_written += max(output_path.stat().st_size - existing_size, 0)
                feature_row_count += len(feature_rows)
                # Patch 2026-05-15 — per-timeframe row accounting for the
                # manifest. Falls back to "1m" only when the silver entry
                # itself carries no timeframe label (legacy paths).
                tf_normalized_written = normalize_timeframe(entry.timeframe) or "1m"
                per_timeframe_row_count[tf_normalized_written] = (
                    per_timeframe_row_count.get(tf_normalized_written, 0)
                    + len(feature_rows)
                )
                _write_gold_feature_build_heartbeat(
                    request=request,
                    pair=pair,
                    timeframe=entry.timeframe or "1m",
                    date=date,
                    rows_seen_in_entry=len(decision_rows),
                    feature_row_count=feature_row_count,
                    bytes_written=bytes_written,
                    microstructure_requested_row_count=(
                        microstructure_streaming_requested_row_count
                    ),
                    microstructure_overlay_row_count=(
                        microstructure_streaming_overlay_row_count
                    ),
                    microstructure_missing_row_count=(
                        microstructure_streaming_missing_row_count
                    ),
                    stage_detail="gold_partition_written",
                    entry_index=entry_index,
                    entry_count=entry_count,
                    cache_stats=_microstructure_cache_stats_for_heartbeat(),
                )
                _maybe_evict_microstructure_cache_after_gold_entry(
                    request=request,
                    pair=pair,
                    timeframe=entry.timeframe or "1m",
                    date=date,
                    entry_index=entry_index,
                    entry_count=entry_count,
                    feature_row_count=feature_row_count,
                    bytes_written=bytes_written,
                    microstructure_requested_row_count=(
                        microstructure_streaming_requested_row_count
                    ),
                    microstructure_overlay_row_count=(
                        microstructure_streaming_overlay_row_count
                    ),
                    microstructure_missing_row_count=(
                        microstructure_streaming_missing_row_count
                    ),
                )
    # Patch 2026-05-15 (timeframe propagation audit) — classify every silver
    # and requested timeframe and emit an explicit reason code for any that
    # did not materialize in gold. No prune may be silent.
    gold_timeframes_generated_set: set[str] = {
        tf for tf, count in per_timeframe_row_count.items() if count > 0
    }
    pruning_reason_by_timeframe: dict[str, str] = {}
    for tf in silver_timeframes_set:
        if tf in gold_timeframes_generated_set:
            continue
        if tf not in SUPPORTED_GOLD_TIMEFRAMES:
            pruning_reason_by_timeframe[tf] = TIMEFRAME_FEATURE_GENERATION_NOT_SUPPORTED
        elif requested_timeframes and tf not in requested_timeframes:
            pruning_reason_by_timeframe[tf] = TIMEFRAME_PRUNED_NOT_REQUESTED
        else:
            # Silver had it, registry supports it, request did not exclude it,
            # yet gold has zero rows. Treat as a build failure (empty silver
            # file, validation reject, or row limit truncation).
            pruning_reason_by_timeframe[tf] = TIMEFRAME_FEATURE_BUILD_FAILED
    for tf in requested_timeframes:
        if tf in gold_timeframes_generated_set or tf in silver_timeframes_set:
            continue
        if tf not in SUPPORTED_GOLD_TIMEFRAMES:
            pruning_reason_by_timeframe[tf] = TIMEFRAME_FEATURE_GENERATION_NOT_SUPPORTED
        else:
            pruning_reason_by_timeframe[tf] = TIMEFRAME_FEATURE_INPUT_MISSING
    timeframes_pruned = tuple(sorted(pruning_reason_by_timeframe))
    silver_timeframes_detected = tuple(sorted(silver_timeframes_set))
    gold_timeframes_generated = tuple(sorted(gold_timeframes_generated_set))
    blocker_set: set[str] = set(pruning_reason_by_timeframe.values())
    if feature_row_count == 0:
        blocker_set.add("GOLD_FEATURE_STORE_NOT_READY")
    blocker_codes = tuple(sorted(blocker_set))
    status = "FEATURE_STORE_READY" if feature_row_count > 0 else "GOLD_FEATURE_STORE_NOT_READY"
    if microstructure_streaming_batch_count <= 0:
        microstructure_streaming_status = "A2_MICROSTRUCTURE_STREAMING_NOT_REQUIRED"
    elif microstructure_streaming_overlay_row_count > 0:
        microstructure_streaming_status = "A2_MICROSTRUCTURE_STREAMING_READY"
    elif any(
        status_key == "A2_MICROSTRUCTURE_STREAMING_NO_SOURCE"
        for status_key in microstructure_streaming_status_counts
    ):
        microstructure_streaming_status = "A2_MICROSTRUCTURE_STREAMING_NO_SOURCE"
    else:
        microstructure_streaming_status = "A2_MICROSTRUCTURE_STREAMING_NO_VALUES"
    gold_decision_window_status = (
        "GOLD_DECISION_WINDOW_FILTER_READY"
        if requested_start_ms is not None or requested_end_ms is not None
        else "GOLD_DECISION_WINDOW_FILTER_NOT_REQUIRED"
    )
    if microstructure_streaming_status == "A2_MICROSTRUCTURE_STREAMING_READY":
        feature_equivalence_status = "A2_FEATURE_EQUIVALENCE_READY"
    elif microstructure_streaming_status == "A2_MICROSTRUCTURE_STREAMING_NOT_REQUIRED":
        feature_equivalence_status = "A2_FEATURE_EQUIVALENCE_NOT_REQUIRED"
    else:
        feature_equivalence_status = "A2_FEATURE_EQUIVALENCE_PARTIAL"
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
        silver_timeframes_detected=silver_timeframes_detected,
        gold_timeframes_generated=gold_timeframes_generated,
        timeframes_pruned=timeframes_pruned,
        pruning_reason_by_timeframe=dict(pruning_reason_by_timeframe),
        timeframe_feature_row_count=dict(per_timeframe_row_count),
        gold_decision_window_status=gold_decision_window_status,
        gold_context_row_count=gold_context_row_count,
        gold_context_rows_suppressed_count=gold_context_rows_suppressed_count,
        microstructure_cache_used=microstructure_streaming_batch_count > 0,
        feature_equivalence_status=feature_equivalence_status,
        microstructure_streaming_status=microstructure_streaming_status,
        microstructure_streaming_batch_count=microstructure_streaming_batch_count,
        microstructure_streaming_requested_row_count=(
            microstructure_streaming_requested_row_count
        ),
        microstructure_streaming_overlay_row_count=microstructure_streaming_overlay_row_count,
        microstructure_streaming_missing_row_count=microstructure_streaming_missing_row_count,
        microstructure_streaming_status_counts=dict(
            sorted(microstructure_streaming_status_counts.items())
        ),
        blocker_codes=blocker_codes,
    )
    return finalize_hashed_model(manifest)


def _write_report(path: Path, payload: BaseException | dict[str, object] | object) -> None:
    if hasattr(payload, "model_dump"):
        atomic_write_json(path, payload.model_dump(mode="json"), indent=2)
    else:
        atomic_write_json(path, payload, indent=2)


def _stage_elapsed_s(started_at: float) -> float:
    return round(max(perf_counter() - started_at, 0.0), 6)


def _progress_counter_payload(
    *,
    files_seen: int = 0,
    files_processed: int = 0,
    files_skipped: int = 0,
    files_skipped_by_date_filter: int = 0,
    rows_processed: int = 0,
    rows_rejected: int = 0,
    bytes_read: int = 0,
    bytes_written: int = 0,
    silver_entry_count: int = 0,
    gold_feature_row_count: int = 0,
) -> dict[str, object]:
    return {
        "files_seen": files_seen,
        "files_processed": files_processed,
        "files_skipped": files_skipped,
        "files_skipped_by_date_filter": files_skipped_by_date_filter,
        "rows_processed": rows_processed,
        "rows_rejected": rows_rejected,
        "bytes_read": bytes_read,
        "bytes_written": bytes_written,
        "silver_entry_count": silver_entry_count,
        "gold_feature_row_count": gold_feature_row_count,
    }


def _write_a2_progress_report(
    report_root: Path,
    *,
    run_id: str,
    status: str,
    current_stage: str,
    normalized_start: str,
    normalized_end: str,
    effective_start_text: str,
    requested_pairs: tuple[str, ...],
    requested_timeframes: tuple[str, ...],
    requested_feature_names: tuple[str, ...],
    stage_timings_s: dict[str, float],
    counters: dict[str, object],
    blocker_codes: tuple[str, ...] = (),
    extra: dict[str, object] | None = None,
) -> None:
    payload: dict[str, object] = {
        "schema_version": "v53.a2_gold_progress_report.v1",
        "run_id": run_id,
        "status": status,
        "current_stage": current_stage,
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "window": {
            "requested_start": normalized_start,
            "requested_end": normalized_end,
            "effective_context_start": effective_start_text,
            "replay_context_lookback_ms": _REPLAY_CONTEXT_LOOKBACK_MS,
            "context_policy": "REQUESTED_START_MINUS_1H_ROW_FILTERED",
        },
        "request": {
            "pairs": requested_pairs,
            "timeframes": requested_timeframes,
            "feature_names": requested_feature_names,
        },
        "stage_timings_s": dict(stage_timings_s),
        "counters": dict(counters),
        "blocker_codes": blocker_codes,
    }
    if extra:
        payload.update(extra)
    _write_report(report_root / "a2_gold_progress_report.json", payload)


def _build_a2_microstructure_cache_manifest(
    *,
    request: StrategyLadderDataFactoryRequest,
    requested_microstructure_features: tuple[str, ...],
    cache_stats: dict[str, object],
    cache_manifest_ref: str,
) -> dict[str, object]:
    hit_count = int(
        cache_stats.get("file_cache_hit_count")
        or cache_stats.get("hit_count")
        or 0
    )
    miss_count = int(
        cache_stats.get("file_cache_miss_count")
        or cache_stats.get("miss_count")
        or 0
    )
    cached_path_count = int(
        cache_stats.get("cached_path_count")
        or cache_stats.get("cached_file_count")
        or 0
    )
    cache_requested = bool(requested_microstructure_features)
    if not cache_requested:
        cache_status = "A2_MICROSTRUCTURE_FILE_CACHE_NOT_REQUIRED"
    elif request.dry_run:
        cache_status = "A2_MICROSTRUCTURE_FILE_CACHE_NOT_EXERCISED_DRY_RUN"
    elif cached_path_count > 0 or miss_count > 0 or hit_count > 0:
        cache_status = "A2_MICROSTRUCTURE_FILE_CACHE_READY"
    else:
        cache_status = "A2_MICROSTRUCTURE_FILE_CACHE_UNUSED_NO_PATHS"
    return {
        "schema_version": "v53.a2_microstructure_cache_manifest.v1",
        "run_id": request.run_id,
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "cache_status": cache_status,
        "cache_manifest_ref": cache_manifest_ref,
        "requested_features": tuple(request.feature_names),
        "requested_microstructure_features": requested_microstructure_features,
        "cache_requested": cache_requested,
        "cache_policy": {
            "scope": "A2_IN_MEMORY_PER_PROCESS_FILE_CACHE",
            "source_signature": "RESOLVED_PATH_MTIME_NS_SIZE",
            "decision_policy": "REPORTING_AND_IO_OPTIMIZATION_ONLY",
            "trading_decisions_modified": False,
            "proxy_promoted_to_truth": False,
        },
        "stats": dict(cache_stats),
    }


def _build_a2_feature_equivalence_report(
    *,
    request: StrategyLadderDataFactoryRequest,
    gold_manifest: StrategyLadderGoldFeatureManifest,
) -> dict[str, object]:
    streaming_used = (
        gold_manifest.microstructure_streaming_status
        == "A2_MICROSTRUCTURE_STREAMING_READY"
    )
    if streaming_used:
        status = "A2_FEATURE_EQUIVALENCE_READY"
        equivalence_status = "CANONICAL_CALCULATORS_REUSED_NO_NUMERIC_CHANGE"
    elif gold_manifest.microstructure_streaming_status == (
        "A2_MICROSTRUCTURE_STREAMING_NOT_REQUIRED"
    ):
        status = "A2_FEATURE_EQUIVALENCE_NOT_REQUIRED"
        equivalence_status = "MICROSTRUCTURE_FEATURES_NOT_REQUESTED"
    else:
        status = "A2_FEATURE_EQUIVALENCE_PARTIAL"
        equivalence_status = "INSUFFICIENT_MICROSTRUCTURE_VALUES_FOR_EQUIVALENCE"
    return {
        "schema_version": "v53.a2_feature_equivalence_report.v1",
        "run_id": request.run_id,
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "status": status,
        "equivalence_status": equivalence_status,
        "builder_mode": "REQUESTED_ONLY_CANONICAL_CALCULATOR_BATCH",
        "trading_decisions_modified": False,
        "proxy_promoted_to_truth": False,
        "post_decision_features_used": False,
        "requested_features": tuple(request.feature_names),
        "gold_decision_window": {
            "status": gold_manifest.gold_decision_window_status,
            "context_row_count": gold_manifest.gold_context_row_count,
            "context_rows_suppressed_count": (
                gold_manifest.gold_context_rows_suppressed_count
            ),
        },
        "microstructure_streaming": {
            "status": gold_manifest.microstructure_streaming_status,
            "batch_count": gold_manifest.microstructure_streaming_batch_count,
            "requested_row_count": (
                gold_manifest.microstructure_streaming_requested_row_count
            ),
            "overlay_row_count": gold_manifest.microstructure_streaming_overlay_row_count,
            "missing_row_count": gold_manifest.microstructure_streaming_missing_row_count,
            "status_counts": dict(gold_manifest.microstructure_streaming_status_counts),
        },
        "notes": (
            "Layer 3 computes only requested ex-ante microstructure features.",
            "The same canonical data_backbone calculators are reused.",
            "No Engine A/B/C/D thresholds or decisions are changed.",
        ),
    }


def _build_a2_microstructure_performance_report(
    *,
    request: StrategyLadderDataFactoryRequest,
    normalized_start: str,
    normalized_end: str,
    effective_start_text: str,
    stage_timings_s: dict[str, float],
    silver_index: tuple[StrategyLadderSilverIndexEntry, ...],
    gold_manifest: StrategyLadderGoldFeatureManifest,
    files_seen: int,
    files_processed: int,
    files_skipped: int,
    files_skipped_by_date_filter: int,
    rows_processed: int,
    rows_rejected: int,
    bytes_read: int,
    bytes_written: int,
    blocker_codes: tuple[str, ...],
    microstructure_cache_manifest: dict[str, object],
) -> dict[str, object]:
    silver_entry_count_by_type: dict[str, int] = {}
    silver_row_count_by_type: dict[str, int] = {}
    silver_timeframes = sorted(
        {
            normalize_timeframe(entry.timeframe or "")
            for entry in silver_index
            if entry.data_type == "ohlcv" and normalize_timeframe(entry.timeframe or "")
        }
    )
    for entry in silver_index:
        data_type = entry.data_type or "unknown"
        silver_entry_count_by_type[data_type] = silver_entry_count_by_type.get(data_type, 0) + 1
        silver_row_count_by_type[data_type] = (
            silver_row_count_by_type.get(data_type, 0) + int(entry.row_count or 0)
        )
    requested_timeframes = tuple(
        normalize_timeframe(timeframe) or timeframe for timeframe in request.timeframes
    )
    unexpected_timeframes = tuple(
        timeframe for timeframe in silver_timeframes if timeframe not in requested_timeframes
    )
    cache_stats = microstructure_cache_manifest.get("stats")
    if not isinstance(cache_stats, dict):
        cache_stats = {}
    cache_hit_count = int(
        cache_stats.get("file_cache_hit_count")
        or cache_stats.get("hit_count")
        or 0
    )
    cache_miss_count = int(
        cache_stats.get("file_cache_miss_count")
        or cache_stats.get("miss_count")
        or 0
    )
    cache_status = str(
        microstructure_cache_manifest.get("cache_status")
        or "A2_MICROSTRUCTURE_FILE_CACHE_NOT_REQUIRED"
    )
    if cache_status == "A2_MICROSTRUCTURE_FILE_CACHE_READY":
        repeated_raw_scan_status = "FILE_CACHE_ACTIVE"
    elif cache_status == "A2_MICROSTRUCTURE_FILE_CACHE_NOT_REQUIRED":
        repeated_raw_scan_status = "NOT_REQUIRED"
    else:
        repeated_raw_scan_status = "FILE_CACHE_NOT_EXERCISED"
    return {
        "schema_version": "v53.a2_microstructure_performance_report.v1",
        "run_id": request.run_id,
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "status": "A2_PERFORMANCE_REPORT_READY",
        "window": {
            "requested_start": normalized_start,
            "requested_end": normalized_end,
            "effective_context_start": effective_start_text,
            "replay_context_lookback_ms": _REPLAY_CONTEXT_LOOKBACK_MS,
            "context_policy": "REQUESTED_START_MINUS_1H_ROW_FILTERED",
        },
        "request": {
            "pairs": request.pairs,
            "timeframes": request.timeframes,
            "feature_names": request.feature_names,
            "data_types": request.data_types,
            "storage_format": request.storage_format,
            "dry_run": request.dry_run,
            "small_scope": request.small_scope,
        },
        "stage_timings_s": dict(stage_timings_s),
        "counters": _progress_counter_payload(
            files_seen=files_seen,
            files_processed=files_processed,
            files_skipped=files_skipped,
            files_skipped_by_date_filter=files_skipped_by_date_filter,
            rows_processed=rows_processed,
            rows_rejected=rows_rejected,
            bytes_read=bytes_read,
            bytes_written=bytes_written,
            silver_entry_count=len(silver_index),
            gold_feature_row_count=gold_manifest.feature_row_count,
        ),
        "silver": {
            "entry_count_by_type": silver_entry_count_by_type,
            "row_count_by_type": silver_row_count_by_type,
            "timeframes_detected": tuple(silver_timeframes),
            "unexpected_timeframes": unexpected_timeframes,
            "timeframe_pruning_status": (
                "SILVER_TIMEFRAME_PRUNING_READY"
                if not unexpected_timeframes
                else "SILVER_TIMEFRAME_PRUNING_VIOLATION"
            ),
        },
        "gold": {
            "feature_row_count": gold_manifest.feature_row_count,
            "timeframes_generated": gold_manifest.gold_timeframes_generated,
            "timeframe_feature_row_count": gold_manifest.timeframe_feature_row_count,
            "feature_paths": gold_manifest.feature_paths,
            "decision_window_status": gold_manifest.gold_decision_window_status,
            "context_row_count": gold_manifest.gold_context_row_count,
            "context_rows_suppressed_count": (
                gold_manifest.gold_context_rows_suppressed_count
            ),
            "microstructure_cache_used": gold_manifest.microstructure_cache_used,
            "feature_equivalence_status": gold_manifest.feature_equivalence_status,
            "microstructure_streaming_status": gold_manifest.microstructure_streaming_status,
            "microstructure_streaming_batch_count": (
                gold_manifest.microstructure_streaming_batch_count
            ),
            "microstructure_streaming_overlay_row_count": (
                gold_manifest.microstructure_streaming_overlay_row_count
            ),
        },
        "microstructure": {
            "cache_status": cache_status,
            "cache_manifest_ref": microstructure_cache_manifest.get("cache_manifest_ref", ""),
            "streaming_status": gold_manifest.microstructure_streaming_status,
            "streaming_batch_count": gold_manifest.microstructure_streaming_batch_count,
            "streaming_requested_row_count": (
                gold_manifest.microstructure_streaming_requested_row_count
            ),
            "streaming_overlay_row_count": (
                gold_manifest.microstructure_streaming_overlay_row_count
            ),
            "streaming_missing_row_count": (
                gold_manifest.microstructure_streaming_missing_row_count
            ),
            "streaming_status_counts": dict(
                gold_manifest.microstructure_streaming_status_counts
            ),
            "file_cache_hit_count": cache_hit_count,
            "file_cache_miss_count": cache_miss_count,
            "cached_path_count": int(
                cache_stats.get("cached_path_count")
                or cache_stats.get("cached_file_count")
                or 0
            ),
            "cached_row_count": int(cache_stats.get("cached_row_count") or 0),
            "time_index_hit_count": int(cache_stats.get("time_index_hit_count") or 0),
            "time_index_miss_count": int(cache_stats.get("time_index_miss_count") or 0),
            "time_indexed_path_count": int(
                cache_stats.get("time_indexed_path_count") or 0
            ),
            "time_indexed_row_count": int(cache_stats.get("time_indexed_row_count") or 0),
            "rows_loaded": int(cache_stats.get("rows_loaded") or 0),
            "bytes_loaded": int(cache_stats.get("bytes_loaded") or 0),
            "row_level_context_filter_status": "ROW_LEVEL_CONTEXT_FILTER_READY",
            "repeated_raw_scan_status": repeated_raw_scan_status,
        },
        "blocker_codes": blocker_codes,
    }


def _write_generated_raw_source_manifest(
    *,
    report_root: Path,
    source_report: StrategyLadderRawSourceReport,
) -> Path:
    manifest_path = report_root / "raw_source_manifest.json"
    payload = {
        "schema_version": "v1",
        "generated_by": "strategy_ladder_data_factory",
        "sources": [source.model_dump(mode="json") for source in source_report.sources],
    }
    atomic_write_json(manifest_path, payload, indent=2)
    return manifest_path.resolve()


def run_strategy_ladder_data_factory(
    request: StrategyLadderDataFactoryRequest,
) -> StrategyLadderDataFactoryResult:
    """Run the canonical Patch 6 Data Factory over one bounded source scope."""

    report_root = request.input_root.resolve()
    report_root.mkdir(parents=True, exist_ok=True)
    request.silver_root.mkdir(parents=True, exist_ok=True)
    request.gold_root.mkdir(parents=True, exist_ok=True)
    run_started_at = perf_counter()
    stage_timings_s: dict[str, float] = {}
    stage_started_at = perf_counter()
    source_report = resolve_strategy_ladder_raw_sources(
        raw_roots=request.raw_roots,
        raw_source_manifest_path=request.raw_source_manifest_path,
        dry_run=request.dry_run,
    )
    stage_timings_s["raw_source_resolution"] = _stage_elapsed_s(stage_started_at)
    normalized_start = _normalize_boundary_text(request.start)
    normalized_end = _normalize_boundary_text(request.end)
    start_ms = parse_time_boundary_to_ms(normalized_start)
    end_ms = parse_time_boundary_to_ms(normalized_end)
    effective_start_ms = _effective_context_start_ms(start_ms)
    effective_start_text = _effective_context_start_text(
        normalized_start,
        effective_start_ms,
    )
    if end_ms is not None and _is_date_only_boundary(normalized_end):
        end_ms += 86_399_999
    date_boundaries_parseable = (
        (not normalized_start or start_ms is not None)
        and (not normalized_end or end_ms is not None)
    )
    requested_pairs = {pair.upper() for pair in request.pairs}
    requested_types = {item.lower() for item in request.data_types}
    requested_timeframes = {
        normalize_timeframe(timeframe)
        for timeframe in request.timeframes
        if normalize_timeframe(timeframe)
    }
    _write_a2_progress_report(
        report_root,
        run_id=request.run_id,
        status="A2_RUNNING",
        current_stage="RAW_SOURCE_RESOLUTION_COMPLETE",
        normalized_start=normalized_start,
        normalized_end=normalized_end,
        effective_start_text=effective_start_text,
        requested_pairs=request.pairs,
        requested_timeframes=request.timeframes,
        requested_feature_names=request.feature_names,
        stage_timings_s=stage_timings_s,
        counters=_progress_counter_payload(),
        blocker_codes=tuple(source_report.blocker_codes),
    )
    metadata_cache_result = load_historical_metadata_cache(
        request.historical_metadata_root,
        requested_pairs=request.pairs,
        replay_start=normalized_start,
        replay_end=normalized_end,
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
    stage_started_at = perf_counter()
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
                    probed_date, start_ms=effective_start_ms, end_ms=end_ms
                ):
                    files_skipped_by_date_filter += 1
                    files_skipped += 1
                    continue
                if not probed_date:
                    files_with_unparsed_date += 1
            if requested_timeframes and _coarse_data_type_hint(path) == "klines":
                _, coarse_timeframe, _ = _infer_pair_and_date(path)
                mapped_timeframe = normalize_timeframe(_map_timeframe(coarse_timeframe))
                if mapped_timeframe and mapped_timeframe not in requested_timeframes:
                    files_skipped += 1
                    continue
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
    stage_timings_s["candidate_file_scan"] = _stage_elapsed_s(stage_started_at)
    _write_a2_progress_report(
        report_root,
        run_id=request.run_id,
        status="A2_RUNNING",
        current_stage="CANDIDATE_FILE_SCAN_COMPLETE",
        normalized_start=normalized_start,
        normalized_end=normalized_end,
        effective_start_text=effective_start_text,
        requested_pairs=request.pairs,
        requested_timeframes=request.timeframes,
        requested_feature_names=request.feature_names,
        stage_timings_s=stage_timings_s,
        counters=_progress_counter_payload(
            files_seen=files_seen,
            files_skipped=files_skipped,
            files_skipped_by_date_filter=files_skipped_by_date_filter,
        ),
        blocker_codes=tuple(blocker_codes),
        extra={"candidate_file_count": len(candidate_files)},
    )

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
    stage_started_at = perf_counter()
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
    stage_timings_s["storage_budget_preflight"] = _stage_elapsed_s(stage_started_at)
    _write_a2_progress_report(
        report_root,
        run_id=request.run_id,
        status="A2_RUNNING",
        current_stage="STORAGE_BUDGET_PREFLIGHT_COMPLETE",
        normalized_start=normalized_start,
        normalized_end=normalized_end,
        effective_start_text=effective_start_text,
        requested_pairs=request.pairs,
        requested_timeframes=request.timeframes,
        requested_feature_names=request.feature_names,
        stage_timings_s=stage_timings_s,
        counters=_progress_counter_payload(
            files_seen=files_seen,
            files_skipped=files_skipped,
            files_skipped_by_date_filter=files_skipped_by_date_filter,
        ),
        blocker_codes=tuple(blocker_codes),
        extra={
            "storage_budget_status": preflight_storage_budget_report.storage_budget_status,
            "candidate_file_count": len(candidate_files),
        },
    )
    raw_scan_budget_status = "DRY_RUN_SCOPE_READY"
    raw_scan_budget_reason_codes: list[str] = []
    if request.dry_run:
        span_days = _span_days(effective_start_ms, end_ms)
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

    stage_started_at = perf_counter()
    for source, path in candidate_files:
        if scope_guard_blocked:
            break
        classification = classify_raw_file(source=source, path=path)
        pair = classification.pair or ""
        source_kind = _source_kind_from_data_type(classification.data_type)
        if (
            classification.data_type == "klines"
            and requested_timeframes
            and normalize_timeframe(classification.timeframe or "") not in requested_timeframes
        ):
            files_skipped += 1
            continue
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
            if (
                file_start is not None
                and effective_start_ms is not None
                and file_end < effective_start_ms
            ):
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
                window_start_ms=effective_start_ms,
                window_end_ms=end_ms,
                resume=request.resume,
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
                window_start_ms=effective_start_ms,
                window_end_ms=end_ms,
                resume=request.resume,
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
                window_start_ms=effective_start_ms,
                window_end_ms=end_ms,
                resume=request.resume,
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
    stage_timings_s["silver_normalization"] = _stage_elapsed_s(stage_started_at)
    silver_index = tuple(index_entries)
    _write_a2_progress_report(
        report_root,
        run_id=request.run_id,
        status="A2_RUNNING",
        current_stage="SILVER_NORMALIZATION_COMPLETE",
        normalized_start=normalized_start,
        normalized_end=normalized_end,
        effective_start_text=effective_start_text,
        requested_pairs=request.pairs,
        requested_timeframes=request.timeframes,
        requested_feature_names=request.feature_names,
        stage_timings_s=stage_timings_s,
        counters=_progress_counter_payload(
            files_seen=files_seen,
            files_processed=files_processed,
            files_skipped=files_skipped,
            files_skipped_by_date_filter=files_skipped_by_date_filter,
            rows_processed=rows_processed,
            rows_rejected=rows_rejected,
            bytes_read=bytes_read,
            bytes_written=bytes_written,
            silver_entry_count=len(silver_index),
        ),
        blocker_codes=tuple(blocker_codes),
    )
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
    requested_a2_features_for_cache = _requested_a2_feature_names(request)
    requested_microstructure_features_for_cache = tuple(
        sorted(
            requested_a2_features_for_cache.intersection(
                _A2_ENGINE_NATIVE_BRIDGE_FEATURES
            )
        )
    )
    reset_microstructure_file_cache_stats(clear_cache=True)
    stage_started_at = perf_counter()
    gold_manifest = _write_gold_features(
        request=request,
        index_entries=silver_index,
        available_pairs=pair_report.available_pairs,
    )
    microstructure_cache_stats = get_microstructure_file_cache_stats()
    microstructure_cache_report_path = (
        report_root / "a2_microstructure_cache_manifest.json"
    )
    microstructure_cache_manifest = _build_a2_microstructure_cache_manifest(
        request=request,
        requested_microstructure_features=requested_microstructure_features_for_cache,
        cache_stats=microstructure_cache_stats,
        cache_manifest_ref=str(microstructure_cache_report_path.resolve()),
    )
    _write_report(microstructure_cache_report_path, microstructure_cache_manifest)
    feature_equivalence_report_path = report_root / "a2_feature_equivalence_report.json"
    feature_equivalence_report = _build_a2_feature_equivalence_report(
        request=request,
        gold_manifest=gold_manifest,
    )
    _write_report(feature_equivalence_report_path, feature_equivalence_report)
    stage_timings_s["gold_feature_build"] = _stage_elapsed_s(stage_started_at)
    _write_a2_progress_report(
        report_root,
        run_id=request.run_id,
        status="A2_RUNNING",
        current_stage="GOLD_FEATURE_BUILD_COMPLETE",
        normalized_start=normalized_start,
        normalized_end=normalized_end,
        effective_start_text=effective_start_text,
        requested_pairs=request.pairs,
        requested_timeframes=request.timeframes,
        requested_feature_names=request.feature_names,
        stage_timings_s=stage_timings_s,
        counters=_progress_counter_payload(
            files_seen=files_seen,
            files_processed=files_processed,
            files_skipped=files_skipped,
            files_skipped_by_date_filter=files_skipped_by_date_filter,
            rows_processed=rows_processed,
            rows_rejected=rows_rejected,
            bytes_read=bytes_read,
            bytes_written=bytes_written,
            silver_entry_count=len(silver_index),
            gold_feature_row_count=gold_manifest.feature_row_count,
        ),
        blocker_codes=tuple(blocker_codes),
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
    metadata_temporal_drift_days = _compute_metadata_temporal_drift_days(
        fetched_at_utc=metadata_cache_result.fetched_at_utc,
        end_date=normalized_end,
    )
    (
        ohlcv_temporal_completeness_status,
        ohlcv_temporal_blocked_entry_count,
        ohlcv_temporal_critical_timeframes,
        ohlcv_temporal_blocker_codes,
    ) = _assess_ohlcv_temporal_completeness(
        index_entries=silver_index,
        requested_timeframes=request.timeframes,
        expected_dates=_expected_date_scope(normalized_start, normalized_end),
    )
    blocker_codes.extend(ohlcv_temporal_blocker_codes)
    orderbook_groups: dict[tuple[str, str], list[StrategyLadderSilverIndexEntry]] = {}
    for entry in silver_index:
        if entry.data_type not in {"orderbook_snapshot", "orderbook_delta", "orderbook"}:
            continue
        orderbook_groups.setdefault((entry.pair, entry.date), []).append(entry)
    for entries in orderbook_groups.values():
        has_snapshot = any(
            entry.data_type == "orderbook_snapshot" and _entry_has_silver_data(entry)
            for entry in entries
        )
        has_delta = any(
            entry.data_type == "orderbook_delta" and _entry_has_silver_data(entry)
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
            start_ms=effective_start_ms,
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
        not request.dry_run
        and ohlcv_temporal_completeness_status == "OHLCV_TEMPORAL_COMPLETENESS_BLOCKED"
        and data_factory_status in {"DATA_FACTORY_READY", "DATA_FACTORY_PARTIAL"}
    ):
        data_factory_status = "DATA_FACTORY_BLOCKED_BY_OHLCV_TEMPORAL_COMPLETENESS"
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
    active_pairs_after_pruning = tuple(
        pair_inference_summary.get("active_pairs_after_pruning") or ()
    )
    pair_generalization_status = (
        "MULTI_PAIR_GENERALIZATION_READY"
        if len(active_pairs_after_pruning) >= 3
        else "SINGLE_PAIR_RESEARCH_ONLY"
    )
    if pair_generalization_status != "MULTI_PAIR_GENERALIZATION_READY":
        blocker_codes.append("SINGLE_PAIR_RESEARCH_ONLY")
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
            metadata_temporal_drift_days=metadata_temporal_drift_days,
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
            active_pairs_after_pruning=active_pairs_after_pruning,
            pair_generalization_status=pair_generalization_status,
            blocker_codes=tuple(dict.fromkeys(blocker_codes)),
            date_filter_start=normalized_start or "",
            date_filter_end=normalized_end or "",
            date_filter_effective_start=effective_start_text,
            replay_context_lookback_ms=_REPLAY_CONTEXT_LOOKBACK_MS,
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
            raw_source_typing_status=source_report.raw_source_typing_status,
            ohlcv_temporal_completeness_status=ohlcv_temporal_completeness_status,
            ohlcv_temporal_blocked_entry_count=ohlcv_temporal_blocked_entry_count,
            ohlcv_temporal_critical_timeframes=ohlcv_temporal_critical_timeframes,
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
            raw_source_manifest_path="",
            raw_source_provenance_status=(
                "RAW_SOURCE_MANIFEST_PROVIDED"
                if request.raw_source_manifest_path is not None
                else "RAW_SOURCE_MANIFEST_GENERATED"
            ),
            raw_source_typing_status=source_report.raw_source_typing_status,
            historical_metadata_root=str(request.historical_metadata_root.resolve()) if request.historical_metadata_root is not None else "",
            silver_root=str(request.silver_root.resolve()),
            gold_root=str(request.gold_root.resolve()),
            pairs=request.pairs,
            start=normalized_start,
            end=normalized_end,
            effective_start=effective_start_text,
            replay_context_lookback_ms=_REPLAY_CONTEXT_LOOKBACK_MS,
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
            metadata_temporal_drift_days=metadata_temporal_drift_days,
            pair_generalization_status=data_quality.pair_generalization_status,
            compression_status=("COMPRESSION_READY" if bytes_written > 0 else "COMPRESSION_NOT_PROVEN"),
            silver_storage_format=storage_format_token,
            silver_storage_status=silver_storage_status,
            silver_bloat_ratio=silver_bloat_ratio,
            ohlcv_temporal_completeness_status=ohlcv_temporal_completeness_status,
            ohlcv_temporal_blocked_entry_count=ohlcv_temporal_blocked_entry_count,
            ohlcv_temporal_critical_timeframes=ohlcv_temporal_critical_timeframes,
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
    generated_raw_source_manifest_path = (
        request.raw_source_manifest_path.resolve()
        if request.raw_source_manifest_path is not None
        else _write_generated_raw_source_manifest(
            report_root=report_root,
            source_report=source_report,
        )
    )
    enriched_source_report = finalize_hashed_model(
        source_report.model_copy(
            update={
                "sources": tuple(
                    source.model_copy(
                        update={
                            "typing_status": (
                                "RAW_SOURCE_TYPED_READY"
                                if source.data_types
                                else source.typing_status
                            ),
                            "reason_codes": tuple(
                                dict.fromkeys(
                                    (
                                        *source.reason_codes,
                                        *(
                                            ("RAW_SOURCE_MANIFEST_GENERATED",)
                                            if request.raw_source_manifest_path is None
                                            else ("RAW_SOURCE_MANIFEST_PROVIDED",)
                                        ),
                                    )
                                )
                            ),
                        }
                    )
                    for source in source_report.sources
                ),
                "raw_source_manifest_path": str(generated_raw_source_manifest_path),
                "raw_source_provenance_status": (
                    "RAW_SOURCE_MANIFEST_PROVIDED"
                    if request.raw_source_manifest_path is not None
                    else "RAW_SOURCE_MANIFEST_GENERATED"
                ),
                "raw_source_typing_status": (
                    "RAW_SOURCE_TYPED_READY"
                    if all(source.data_types for source in source_report.sources)
                    else source_report.raw_source_typing_status
                ),
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
    manifest = finalize_hashed_model(
        manifest.model_copy(
            update={
                "raw_source_manifest_path": str(generated_raw_source_manifest_path),
                "raw_source_typing_status": enriched_source_report.raw_source_typing_status,
            }
        )
    )
    _write_report(report_root / "data_factory_manifest.json", manifest)
    _write_report(report_root / "pair_universe_report.json", pair_report)
    _write_report(report_root / "data_quality_report.json", data_quality)
    silver_index_report_path = report_root / "silver_index.json"
    _write_report(
        silver_index_report_path,
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
    primary_symbol = next(
        iter(
            pair_report.available_pairs
            or pair_report.discovered_pairs
            or request.pairs
            or source_report.active_pairs_after_pruning
            or ("UNKNOWN",)
        )
    )
    canonical_raw_roots = (
        tuple(request.raw_roots)
        + ((request.historical_metadata_root,) if request.historical_metadata_root is not None else ())
    )
    canonical_source_types = tuple(
        dict.fromkeys(
            (
                *request.data_types,
                *(
                    ("metadata",)
                    if request.historical_metadata_root is not None
                    else ()
                ),
            )
        )
    )
    canonical_raw_manifests = scan_bybit_raw_root(
        raw_roots=canonical_raw_roots,
        symbol=primary_symbol,
        start=normalized_start,
        end=normalized_end,
        source_types=canonical_source_types,
    )
    write_raw_market_file_manifest_bundle(
        report_root / "raw_file_manifest.jsonl.gz",
        canonical_raw_manifests,
    )
    bronze_index = build_bronze_market_index(
        canonical_raw_manifests,
        symbol=primary_symbol,
    )
    write_bronze_market_index(report_root / "bronze_market_index.json", bronze_index)
    write_bronze_market_index_markdown(report_root / "bronze_market_index.md", bronze_index)
    silver_sync_manifest = build_silver_synchronized_market_manifest(
        symbol=primary_symbol,
        bronze_index=bronze_index,
        silver_index=silver_index,
    )
    write_silver_market_reports(
        report_root,
        manifest=silver_sync_manifest,
        bronze_index=bronze_index,
    )
    canonical_gold_manifest = build_gold_microstructure_feature_manifest(
        gold_root=request.gold_root,
        pairs=(primary_symbol,),
        timeframes=request.timeframes,
        start=normalized_start,
        end=normalized_end,
    )
    write_gold_feature_reports(report_root, canonical_gold_manifest)
    expected_edge_manifest = build_expected_edge_feature_dataset(
        gold_root=request.gold_root,
        output_dir=report_root,
        dataset_id=f"{request.run_id}.expected_edge_features",
        pairs=(primary_symbol,),
        timeframes=request.timeframes,
        start=normalized_start,
        end=normalized_end,
        feature_names=canonical_gold_manifest.feature_names,
        purge_window_minutes=1,
        embargo_window_minutes=1,
        source_silver_index_ref=str(silver_index_report_path.resolve()),
        gold_manifest=canonical_gold_manifest,
    )
    backtest_manifest = build_backtest_replay_dataset_manifest(
        pair_scope=canonical_gold_manifest.symbol_scope or (primary_symbol,),
        timeframe_scope=canonical_gold_manifest.timeframe_scope or request.timeframes,
        silver_index=silver_index,
        gold_manifest=canonical_gold_manifest,
    )
    write_backtest_replay_dataset_manifest(report_root, backtest_manifest)
    runtime_parity_manifest = build_runtime_feature_parity_manifest(
        gold_manifest=canonical_gold_manifest,
        expected_edge_manifest=expected_edge_manifest,
        source_silver_index_ref=str(silver_index_report_path.resolve()),
    )
    data_science_report = build_data_science_quality_report(
        expected_edge_manifest=expected_edge_manifest,
    )
    write_quality_reports(
        report_root,
        data_science_report=data_science_report,
        runtime_parity_manifest=runtime_parity_manifest,
        raw_manifests=canonical_raw_manifests,
        bronze_index=bronze_index,
        silver_manifest=silver_sync_manifest,
        gold_manifest=canonical_gold_manifest,
        expected_edge_manifest=expected_edge_manifest,
        backtest_manifest=backtest_manifest,
    )
    propagated_quality_blockers = tuple(
        dict.fromkeys(
            (
                *data_quality.blocker_codes,
                *silver_sync_manifest.blocker_codes,
                *runtime_parity_manifest.blocker_codes,
            )
        )
    )
    if propagated_quality_blockers != data_quality.blocker_codes:
        data_quality = finalize_hashed_model(
            data_quality.model_copy(
                update={"blocker_codes": propagated_quality_blockers}
            )
        )
        _write_report(report_root / "data_quality_report.json", data_quality)
    propagated_manifest_blockers = tuple(
        dict.fromkeys(
            (
                *manifest.blocker_codes,
                *silver_sync_manifest.blocker_codes,
                *runtime_parity_manifest.blocker_codes,
            )
        )
    )
    if propagated_manifest_blockers != manifest.blocker_codes:
        manifest = finalize_hashed_model(
            manifest.model_copy(
                update={"blocker_codes": propagated_manifest_blockers}
            )
        )
        _write_report(report_root / "data_factory_manifest.json", manifest)
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
    # Patch P6 (2026-05-29) — A8 emit prod-safety contract under both names:
    # the canonical audit-conformant name `a2_gold_prod_safety_contract.json`
    # AND the legacy `data_factory_prod_safety_report.json` (back-compat with
    # `a2_cache.py` and operator dashboards that still reference the old name).
    _prod_safety_payload = _build_data_factory_prod_safety_report(
        request=request,
        manifest=manifest,
        data_quality=data_quality,
        silver_index=silver_index,
        gold_manifest=canonical_gold_manifest,
        storage_budget_report=storage_budget_report,
        normalized_start=normalized_start,
        normalized_end=normalized_end,
    )
    _write_report(
        report_root / "a2_gold_prod_safety_contract.json",
        _prod_safety_payload,
    )
    _write_report(
        report_root / "data_factory_prod_safety_report.json",
        _prod_safety_payload,
    )
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
    stage_timings_s["total"] = _stage_elapsed_s(run_started_at)
    performance_report = _build_a2_microstructure_performance_report(
        request=request,
        normalized_start=normalized_start,
        normalized_end=normalized_end,
        effective_start_text=effective_start_text,
        stage_timings_s=stage_timings_s,
        silver_index=silver_index,
        gold_manifest=gold_manifest,
        files_seen=files_seen,
        files_processed=files_processed,
        files_skipped=files_skipped,
        files_skipped_by_date_filter=files_skipped_by_date_filter,
        rows_processed=rows_processed,
        rows_rejected=rows_rejected,
        bytes_read=bytes_read,
        bytes_written=bytes_written,
        blocker_codes=manifest.blocker_codes,
        microstructure_cache_manifest=microstructure_cache_manifest,
    )
    performance_report_path = report_root / "a2_microstructure_performance_report.json"
    _write_report(performance_report_path, performance_report)
    _write_a2_progress_report(
        report_root,
        run_id=request.run_id,
        status="A2_COMPLETE",
        current_stage=manifest.data_factory_status,
        normalized_start=normalized_start,
        normalized_end=normalized_end,
        effective_start_text=effective_start_text,
        requested_pairs=request.pairs,
        requested_timeframes=request.timeframes,
        requested_feature_names=request.feature_names,
        stage_timings_s=stage_timings_s,
        counters=_progress_counter_payload(
            files_seen=files_seen,
            files_processed=files_processed,
            files_skipped=files_skipped,
            files_skipped_by_date_filter=files_skipped_by_date_filter,
            rows_processed=rows_processed,
            rows_rejected=rows_rejected,
            bytes_read=bytes_read,
            bytes_written=bytes_written,
            silver_entry_count=len(silver_index),
            gold_feature_row_count=gold_manifest.feature_row_count,
        ),
        blocker_codes=manifest.blocker_codes,
        extra={
            "performance_report_ref": str(performance_report_path.resolve()),
            "microstructure_cache_manifest_ref": str(
                microstructure_cache_report_path.resolve()
            ),
            "feature_equivalence_report_ref": str(
                feature_equivalence_report_path.resolve()
            ),
            "data_factory_status": manifest.data_factory_status,
            "silver_index_status": manifest.silver_index_status,
            "gold_feature_store_status": manifest.gold_feature_store_status,
        },
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
