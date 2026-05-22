"""Replay-grounded execution and outcome evidence for Strategy Ladder B2."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from local_replay_runtime.strategy_ladder_engine_native_adapter import (
    _BookState,
    _iter_jsonl,
    _load_book_deltas_in_window_with_lookback,
    _load_book_snapshots,
    _reconstruct_book_states,
    _resolve_book_delta_path,
    _select_base_snapshot,
)
from local_replay_runtime.strategy_ladder_models import (
    StrategyLadderCandidateEvent,
    StrategyLadderRawWindowManifest,
)


_STALE_BOOK_WARN_MS = 5_000
_OUTCOME_BAR_HORIZONS = (1, 5, 10)
_MFE_MAE_MAX_BARS = 10


@dataclass(frozen=True)
class StrategyLadderReplayEvidenceBundle:
    measured_spread: dict[str, object]
    measured_slippage: dict[str, object]
    adverse_selection: dict[str, object]
    fill_realism: dict[str, object]
    replay_outcome: dict[str, object]


@dataclass(frozen=True)
class StrategyLadderReplayEvidenceCacheMetrics:
    cache_hits_book_state: int = 0
    cache_misses_book_state: int = 0
    cache_hits_ohlcv: int = 0
    cache_misses_ohlcv: int = 0


class StrategyLadderReplayEvidenceCache:
    """Per-candidate cache for shared replay evidence inputs."""

    def __init__(self) -> None:
        self._book_state_cache: dict[tuple[str, str, int, int, int], tuple[_BookState | None, str, str]] = {}
        self._ohlcv_cache: dict[tuple[str, int], list[dict[str, object]]] = {}
        self._cache_hits_book_state = 0
        self._cache_misses_book_state = 0
        self._cache_hits_ohlcv = 0
        self._cache_misses_ohlcv = 0

    def resolve_book_state(
        self,
        window_manifest: StrategyLadderRawWindowManifest | None,
        *,
        decision_timestamp_ms: int,
    ) -> tuple[_BookState | None, str, str]:
        if window_manifest is None:
            self._cache_misses_book_state += 1
            return _resolve_book_state(window_manifest, decision_timestamp_ms=decision_timestamp_ms)
        cache_key = (
            str(window_manifest.raw_book_path or ""),
            str(window_manifest.raw_book_delta_path or ""),
            int(window_manifest.window_start_ms),
            int(window_manifest.window_end_ms),
            int(decision_timestamp_ms),
        )
        cached = self._book_state_cache.get(cache_key)
        if cached is not None:
            self._cache_hits_book_state += 1
            return cached
        self._cache_misses_book_state += 1
        resolved = _resolve_book_state(
            window_manifest,
            decision_timestamp_ms=decision_timestamp_ms,
        )
        self._book_state_cache[cache_key] = resolved
        return resolved

    def load_ohlcv_rows(
        self,
        window_manifest: StrategyLadderRawWindowManifest | None,
    ) -> list[dict[str, object]]:
        if window_manifest is None or not window_manifest.raw_ohlcv_path:
            self._cache_misses_ohlcv += 1
            return []
        cache_key = (str(window_manifest.raw_ohlcv_path), int(window_manifest.window_end_ms))
        cached = self._ohlcv_cache.get(cache_key)
        if cached is not None:
            self._cache_hits_ohlcv += 1
            return cached
        self._cache_misses_ohlcv += 1
        rows = sorted(
            (
                row
                for row in _iter_jsonl(Path(window_manifest.raw_ohlcv_path))
                if isinstance(row.get("timestamp_ms"), (int, float))
            ),
            key=lambda row: int(row.get("timestamp_ms") or 0),
        )
        self._ohlcv_cache[cache_key] = rows
        return rows

    def metrics_snapshot(self) -> StrategyLadderReplayEvidenceCacheMetrics:
        return StrategyLadderReplayEvidenceCacheMetrics(
            cache_hits_book_state=self._cache_hits_book_state,
            cache_misses_book_state=self._cache_misses_book_state,
            cache_hits_ohlcv=self._cache_hits_ohlcv,
            cache_misses_ohlcv=self._cache_misses_ohlcv,
        )


def _candidate_payload(candidate: StrategyLadderCandidateEvent) -> dict[str, object]:
    return (
        dict(candidate.compatibility_payload)
        if isinstance(candidate.compatibility_payload, dict)
        else {}
    )


def _payload_side(payload: dict[str, object]) -> str:
    normalized = str(payload.get("side") or "").strip().lower()
    if normalized in {"buy", "sell"}:
        return normalized
    return ""


def _payload_entry_price(payload: dict[str, object]) -> float | None:
    for key in ("entry_price", "close_price"):
        raw_value = payload.get(key)
        try:
            value = float(raw_value)
        except (TypeError, ValueError):
            continue
        if value > 0.0:
            return value
    return None


def _book_state_from_snapshot(snapshot: dict[str, object], *, top_k: int = 20) -> _BookState | None:
    try:
        timestamp_ms = int(snapshot.get("timestamp_ms") or 0)
        update_id = int(snapshot.get("update_id") or 0)
    except (TypeError, ValueError):
        return None
    bid_levels: list[tuple[float, float]] = []
    ask_levels: list[tuple[float, float]] = []
    for level in snapshot.get("bids") or ():
        try:
            price = float(level[0])
            size = float(level[1])
        except (TypeError, ValueError, IndexError):
            continue
        if price > 0.0 and size > 0.0:
            bid_levels.append((price, size))
    for level in snapshot.get("asks") or ():
        try:
            price = float(level[0])
            size = float(level[1])
        except (TypeError, ValueError, IndexError):
            continue
        if price > 0.0 and size > 0.0:
            ask_levels.append((price, size))
    if not bid_levels or not ask_levels:
        return None
    bid_levels.sort(key=lambda item: -item[0])
    ask_levels.sort(key=lambda item: item[0])
    return _BookState(
        timestamp_ms=timestamp_ms,
        update_id=update_id,
        bid_levels=tuple(bid_levels[:top_k]),
        ask_levels=tuple(ask_levels[:top_k]),
    )


def _book_state_has_valid_top(state: _BookState | None) -> bool:
    if state is None or not state.bid_levels or not state.ask_levels:
        return False
    try:
        best_bid = float(state.bid_levels[0][0])
        best_ask = float(state.ask_levels[0][0])
    except (TypeError, ValueError, IndexError):
        return False
    return best_bid > 0.0 and best_ask > 0.0 and best_ask >= best_bid


def _resolve_reconstructed_book_state(
    *,
    raw_book_path: Path,
    raw_book_delta_path: str | None,
    base_snapshot: dict[str, object],
    window_start_ms: int,
    window_end_ms: int,
    decision_timestamp_ms: int,
) -> tuple[_BookState | None, str]:
    candidate_paths: list[Path] = []
    explicit_delta_path = _resolve_book_delta_path(raw_book_path, raw_book_delta_path)
    if explicit_delta_path is not None and explicit_delta_path.exists():
        candidate_paths.append(explicit_delta_path)
    derived_delta_path = _resolve_book_delta_path(raw_book_path, None)
    if (
        derived_delta_path is not None
        and derived_delta_path.exists()
        and all(path.resolve() != derived_delta_path.resolve() for path in candidate_paths)
    ):
        candidate_paths.append(derived_delta_path)
    base_update_id = int(base_snapshot.get("update_id") or 0)
    for delta_path in candidate_paths:
        deltas = _load_book_deltas_in_window_with_lookback(
            delta_path,
            base_update_id=base_update_id,
            window_end_ms=window_end_ms,
        )
        states = _reconstruct_book_states(
            base_snapshot=base_snapshot,
            deltas=deltas,
            window_start_ms=window_start_ms,
            window_end_ms=window_end_ms,
            top_k=20,
        )
        if not states:
            continue
        eligible = [
            state
            for state in states
            if state.timestamp_ms <= decision_timestamp_ms and _book_state_has_valid_top(state)
        ]
        if eligible:
            return eligible[-1], str(delta_path.resolve())
        for state in reversed(states):
            if _book_state_has_valid_top(state):
                return state, str(delta_path.resolve())
    return None, ""


def _candidate_base_snapshots(
    snapshots: list[dict[str, object]],
    *,
    window_start_ms: int,
) -> tuple[dict[str, object], ...]:
    if not snapshots:
        return ()
    candidates: list[dict[str, object]] = []
    primary = _select_base_snapshot(
        snapshots,
        window_start_ms=window_start_ms,
    )
    if primary is not None:
        candidates.append(primary)
    after_start = [
        snapshot
        for snapshot in snapshots
        if isinstance(snapshot.get("timestamp_ms"), (int, float))
        and int(snapshot["timestamp_ms"]) >= window_start_ms
    ]
    if after_start:
        fallback = min(after_start, key=lambda item: int(item["timestamp_ms"]))
        if all(candidate is not fallback for candidate in candidates):
            candidates.append(fallback)
    return tuple(candidates)


def _resolve_book_state(
    window_manifest: StrategyLadderRawWindowManifest | None,
    *,
    decision_timestamp_ms: int,
) -> tuple[_BookState | None, str, str]:
    if window_manifest is None or not window_manifest.raw_book_path:
        return None, "SPREAD_BLOCKED_BY_MISSING_BOOK", ""
    raw_book_path = Path(window_manifest.raw_book_path)
    snapshots = _load_book_snapshots(raw_book_path)
    if not snapshots:
        return None, "SPREAD_BLOCKED_BY_MISSING_BOOK", str(raw_book_path.resolve())
    base_snapshots = _candidate_base_snapshots(
        snapshots,
        window_start_ms=window_manifest.window_start_ms,
    )
    if not base_snapshots:
        return None, "SPREAD_BLOCKED_BY_MISSING_BOOK", str(raw_book_path.resolve())
    for base_snapshot in base_snapshots:
        reconstructed_state, reconstructed_source = _resolve_reconstructed_book_state(
            raw_book_path=raw_book_path,
            raw_book_delta_path=window_manifest.raw_book_delta_path,
            base_snapshot=base_snapshot,
            window_start_ms=window_manifest.window_start_ms,
            window_end_ms=window_manifest.window_end_ms,
            decision_timestamp_ms=decision_timestamp_ms,
        )
        if reconstructed_state is not None:
            return (
                reconstructed_state,
                "SPREAD_MEASURED_FROM_BOOK",
                reconstructed_source,
            )
    fallback_state = None
    fallback_source_path = str(raw_book_path.resolve())
    for base_snapshot in base_snapshots:
        fallback_state = _book_state_from_snapshot(base_snapshot, top_k=20)
        if fallback_state is not None and _book_state_has_valid_top(fallback_state):
            break
    if fallback_state is None:
        fallback_state = _book_state_from_snapshot(base_snapshots[0], top_k=20)
    if fallback_state is None:
        return None, "SPREAD_BLOCKED_BY_MISSING_BOOK", str(raw_book_path.resolve())
    return (
        fallback_state,
        "SPREAD_MEASURED_STALE_AUDIT_ONLY",
        fallback_source_path,
    )


def _signed_return_bps(*, entry_price: float, target_price: float, side: str) -> float:
    if entry_price <= 0.0 or target_price <= 0.0:
        return 0.0
    if side == "sell":
        return round(10_000.0 * (entry_price - target_price) / entry_price, 6)
    return round(10_000.0 * (target_price - entry_price) / entry_price, 6)


def _depth_notional(levels: tuple[tuple[float, float], ...], depth: int) -> float:
    return round(sum(price * size for price, size in levels[:depth]), 6)


def _walk_depth_cost_bps(
    *,
    side: str,
    levels: tuple[tuple[float, float], ...],
    planned_notional: float,
    mid_price: float,
) -> tuple[float | None, float]:
    if planned_notional <= 0.0 or mid_price <= 0.0:
        return None, 0.0
    remaining_notional = planned_notional
    filled_notional = 0.0
    filled_qty = 0.0
    for price, size in levels:
        if remaining_notional <= 0.0:
            break
        if price <= 0.0 or size <= 0.0:
            continue
        level_notional = price * size
        if level_notional <= 0.0:
            continue
        take_notional = min(remaining_notional, level_notional)
        filled_notional += take_notional
        filled_qty += take_notional / price
        remaining_notional -= take_notional
    if filled_qty <= 0.0:
        return None, 0.0
    avg_price = filled_notional / filled_qty
    if side == "sell":
        walk_cost_bps = max(0.0, 10_000.0 * (mid_price - avg_price) / mid_price)
    else:
        walk_cost_bps = max(0.0, 10_000.0 * (avg_price - mid_price) / mid_price)
    fill_ratio = 0.0 if planned_notional <= 0.0 else max(
        0.0,
        min(1.0, filled_notional / planned_notional),
    )
    return round(walk_cost_bps, 6), round(fill_ratio, 6)


def build_measured_spread_payload(
    *,
    window_manifest: StrategyLadderRawWindowManifest | None,
    decision_timestamp_ms: int,
    evidence_cache: StrategyLadderReplayEvidenceCache | None = None,
) -> dict[str, object]:
    resolver = (
        evidence_cache.resolve_book_state
        if evidence_cache is not None
        else _resolve_book_state
    )
    book_state, base_status, source_path = resolver(
        window_manifest,
        decision_timestamp_ms=decision_timestamp_ms,
    )
    if book_state is None:
        return {
            "status": base_status,
            "source_path": source_path,
            "source_timestamp_ms": None,
            "staleness_ms": None,
            "best_bid": None,
            "best_ask": None,
            "mid_price": None,
            "spread_abs": None,
            "spread_bps": None,
        }
    best_bid = float(book_state.bid_levels[0][0])
    best_ask = float(book_state.ask_levels[0][0])
    if best_bid <= 0.0 or best_ask <= 0.0 or best_ask < best_bid:
        return {
            "status": "SPREAD_BLOCKED_BY_MISSING_BOOK",
            "source_path": source_path,
            "source_timestamp_ms": book_state.timestamp_ms,
            "staleness_ms": max(decision_timestamp_ms - book_state.timestamp_ms, 0),
            "best_bid": None,
            "best_ask": None,
            "mid_price": None,
            "spread_abs": None,
            "spread_bps": None,
        }
    mid_price = (best_bid + best_ask) / 2.0
    spread_abs = max(best_ask - best_bid, 0.0)
    spread_bps = None if mid_price <= 0.0 else round(10_000.0 * spread_abs / mid_price, 6)
    staleness_ms = max(decision_timestamp_ms - book_state.timestamp_ms, 0)
    status = base_status
    if status == "SPREAD_MEASURED_FROM_BOOK" and staleness_ms > _STALE_BOOK_WARN_MS:
        status = "SPREAD_MEASURED_STALE_AUDIT_ONLY"
    return {
        "status": status,
        "source_path": source_path,
        "source_timestamp_ms": book_state.timestamp_ms,
        "staleness_ms": staleness_ms,
        "best_bid": round(best_bid, 8),
        "best_ask": round(best_ask, 8),
        "mid_price": round(mid_price, 8),
        "spread_abs": round(spread_abs, 8),
        "spread_bps": spread_bps,
    }


def build_measured_slippage_payload(
    *,
    candidate: StrategyLadderCandidateEvent,
    window_manifest: StrategyLadderRawWindowManifest | None,
    planned_notional: float | None,
    decision_timestamp_ms: int,
    evidence_cache: StrategyLadderReplayEvidenceCache | None = None,
) -> dict[str, object]:
    payload = _candidate_payload(candidate)
    side = _payload_side(payload)
    if side not in {"buy", "sell"}:
        return {
            "status": "SLIPPAGE_BLOCKED_BY_UNKNOWN_SIDE",
            "planned_notional": planned_notional,
            "side": side,
            "depth_top1_notional": None,
            "depth_top5_notional": None,
            "depth_top20_notional": None,
            "walk_cost_bps": None,
            "impact_bps": None,
            "depth_fill_ratio": 0.0,
            "partial_fill_status": "PARTIAL_FILL_STATUS_NOT_AVAILABLE",
            "source_timestamp_ms": None,
            "staleness_ms": None,
            "source_path": "",
            "kyle_lambda": None,
        }
    resolver = (
        evidence_cache.resolve_book_state
        if evidence_cache is not None
        else _resolve_book_state
    )
    book_state, _book_status, source_path = resolver(
        window_manifest,
        decision_timestamp_ms=decision_timestamp_ms,
    )
    if book_state is None:
        return {
            "status": "SLIPPAGE_BLOCKED_BY_MISSING_DEPTH20",
            "planned_notional": planned_notional,
            "side": side,
            "depth_top1_notional": None,
            "depth_top5_notional": None,
            "depth_top20_notional": None,
            "walk_cost_bps": None,
            "impact_bps": None,
            "depth_fill_ratio": 0.0,
            "partial_fill_status": "PARTIAL_FILL_STATUS_NOT_AVAILABLE",
            "source_timestamp_ms": None,
            "staleness_ms": None,
            "source_path": source_path,
            "kyle_lambda": None,
        }
    best_bid = float(book_state.bid_levels[0][0])
    best_ask = float(book_state.ask_levels[0][0])
    mid_price = (best_bid + best_ask) / 2.0
    levels = book_state.ask_levels if side == "buy" else book_state.bid_levels
    walk_cost_bps, fill_ratio = _walk_depth_cost_bps(
        side=side,
        levels=levels,
        planned_notional=max(float(planned_notional or 0.0), 0.0),
        mid_price=mid_price,
    )
    staleness_ms = max(decision_timestamp_ms - book_state.timestamp_ms, 0)
    if fill_ratio >= 0.999999:
        partial_fill_status = "FULL_DEPTH_FILL"
    elif fill_ratio > 0.0:
        partial_fill_status = "PARTIAL_DEPTH_FILL"
    else:
        partial_fill_status = "NO_DEPTH_FILL"
    status = "SLIPPAGE_ESTIMATED_FROM_DEPTH20"
    if staleness_ms > _STALE_BOOK_WARN_MS:
        status = "SLIPPAGE_ESTIMATED_FROM_STALE_DEPTH20_AUDIT_ONLY"
    return {
        "status": status,
        "planned_notional": None if planned_notional is None else round(float(planned_notional), 6),
        "side": side,
        "depth_top1_notional": _depth_notional(levels, 1),
        "depth_top5_notional": _depth_notional(levels, 5),
        "depth_top20_notional": _depth_notional(levels, 20),
        "walk_cost_bps": walk_cost_bps,
        "impact_bps": walk_cost_bps,
        "depth_fill_ratio": fill_ratio,
        "partial_fill_status": partial_fill_status,
        "source_timestamp_ms": book_state.timestamp_ms,
        "staleness_ms": staleness_ms,
        "source_path": source_path,
        "kyle_lambda": None,
    }


def _status_bucket(status: object) -> str:
    normalized = str(status or "").strip().upper()
    if not normalized:
        return "unknown"
    if normalized in {
        "SPREAD_MEASURED_FROM_BOOK",
        "SLIPPAGE_ESTIMATED_FROM_DEPTH20",
    }:
        return "measured"
    if "UNCLASSIFIED" in normalized or normalized.startswith("UNKNOWN"):
        return "unknown"
    if "STALE" in normalized:
        return "stale"
    if any(token in normalized for token in ("BLOCKED", "MISSING", "NOT_AVAILABLE", "NOT_PROVEN")):
        return "blocked"
    if normalized.startswith(("MEASURED_", "STATIC_CONSERVATIVE_")):
        return "measured"
    if any(token in normalized for token in ("DEFAULT", "PROXY", "FALLBACK", "TO_CALIBRATE")):
        return "proxy"
    return "unknown"


def _coerce_float(raw_value: object) -> float | None:
    try:
        value = float(raw_value)
    except (TypeError, ValueError):
        return None
    return value


def _spread_provenance_for_payload(measured_spread: dict[str, object]) -> str:
    status = str(measured_spread.get("status") or "").strip().upper()
    if status == "SPREAD_MEASURED_FROM_BOOK":
        return "MEASURED_FROM_BOOK_RECONSTRUCTION"
    if status == "SPREAD_MEASURED_STALE_AUDIT_ONLY":
        return "MEASURED_FROM_BOOK_SNAPSHOT_STALE"
    return "DEFAULT_BY_BOOK_STATUS"


def _slippage_provenance_for_payload(measured_slippage: dict[str, object]) -> str:
    status = str(measured_slippage.get("status") or "").strip().upper()
    if status == "SLIPPAGE_ESTIMATED_FROM_DEPTH20":
        return "MEASURED_FROM_DEPTH20_BOOK_WALK"
    if status == "SLIPPAGE_ESTIMATED_FROM_STALE_DEPTH20_AUDIT_ONLY":
        return "MEASURED_FROM_DEPTH20_BOOK_WALK_STALE"
    return "DEFAULT_TO_CALIBRATE"


def build_measured_cost_governance_payload(
    *,
    measured_spread: dict[str, object],
    measured_slippage: dict[str, object],
    fee_bps: float,
    fee_source_status: str,
    latency_penalty_bps: float,
    latency_source_status: str,
) -> dict[str, object]:
    spread_source_status = str(
        measured_spread.get("status") or _spread_provenance_for_payload(measured_spread)
    ).strip()
    slippage_source_status = str(
        measured_slippage.get("status") or _slippage_provenance_for_payload(measured_slippage)
    ).strip()
    spread_bucket = _status_bucket(spread_source_status)
    slippage_bucket = _status_bucket(slippage_source_status)
    fee_bucket = _status_bucket(fee_source_status)
    latency_bucket = _status_bucket(latency_source_status)
    partial_fill_status = str(
        measured_slippage.get("partial_fill_status") or "PARTIAL_FILL_STATUS_NOT_AVAILABLE"
    ).strip()
    spread_bps_measured = _coerce_float(measured_spread.get("spread_bps"))
    slippage_bps_measured = _coerce_float(measured_slippage.get("walk_cost_bps"))
    expected_cost_decimal_measured = None
    if spread_bps_measured is not None and slippage_bps_measured is not None:
        expected_cost_decimal_measured = round(
            (
                spread_bps_measured
                + slippage_bps_measured * 1.15
                + float(latency_penalty_bps or 0.0)
            )
            / 10_000.0,
            12,
        )
    best_bid = _coerce_float(measured_spread.get("best_bid"))
    best_ask = _coerce_float(measured_spread.get("best_ask"))
    mid_price = _coerce_float(measured_spread.get("mid_price"))
    depth_fill_ratio = _coerce_float(measured_slippage.get("depth_fill_ratio"))
    spread_staleness = measured_spread.get("staleness_ms")
    slippage_staleness = measured_slippage.get("staleness_ms")
    staleness_values = [
        int(value)
        for value in (spread_staleness, slippage_staleness)
        if isinstance(value, (int, float))
    ]
    book_staleness_ms = max(staleness_values) if staleness_values else None
    has_stale = spread_bucket == "stale" or slippage_bucket == "stale"
    has_blocked = spread_bucket == "blocked" or slippage_bucket == "blocked"
    has_unknown = spread_bucket == "unknown" or slippage_bucket == "unknown"
    spread_and_slippage_measured = spread_bucket == "measured" and slippage_bucket == "measured"
    all_core_costs_measured = (
        spread_and_slippage_measured
        and fee_bucket == "measured"
        and latency_bucket == "measured"
    )
    if has_unknown:
        expected_cost_truth_status = "COST_PROVENANCE_UNCLASSIFIED"
    elif has_blocked:
        expected_cost_truth_status = "COST_MEASUREMENT_BLOCKED"
    elif has_stale:
        expected_cost_truth_status = "STALE_AUDIT_ONLY_COST"
    elif partial_fill_status not in {"", "FULL_DEPTH_FILL", "PARTIAL_FILL_STATUS_NOT_AVAILABLE"}:
        expected_cost_truth_status = "PARTIALLY_MEASURED_COST"
    elif all_core_costs_measured:
        expected_cost_truth_status = "FULLY_MEASURED_COST"
    else:
        expected_cost_truth_status = "PARTIALLY_MEASURED_COST"

    if spread_and_slippage_measured:
        usage = "measured"
    elif has_stale:
        usage = "stale_audit_only"
    elif has_blocked:
        usage = "blocked_missing_measurement"
    elif has_unknown:
        usage = "unclassified"
    else:
        usage = "partially_measured_audit_only"

    if usage == "blocked_missing_measurement":
        block_reason = "B2_COST_MEASUREMENT_BLOCKED"
        fill_realism_status = "FILL_REALISM_BLOCKED_BY_MISSING_MEASUREMENT"
        impact_source_status = "IMPACT_SOURCE_MISSING"
    elif usage == "stale_audit_only":
        block_reason = "B2_COST_STALE_AUDIT_ONLY"
        fill_realism_status = "FILL_REALISM_STALE_AUDIT_ONLY"
        impact_source_status = "IMPACT_SOURCE_DEPTH20_MODEL"
    elif partial_fill_status == "PARTIAL_DEPTH_FILL":
        block_reason = ""
        fill_realism_status = "FILL_REALISM_PARTIAL_REPLAY"
        impact_source_status = "IMPACT_SOURCE_LIMITED_DEPTH_MODEL"
    elif partial_fill_status == "FULL_DEPTH_FILL":
        block_reason = ""
        fill_realism_status = "FILL_REALISM_SHADOW_MEASURED"
        impact_source_status = "IMPACT_SOURCE_DEPTH20_MODEL"
    else:
        block_reason = ""
        fill_realism_status = "FILL_REALISM_NOT_PROVEN"
        impact_source_status = "IMPACT_SOURCE_NOT_PROVEN"

    return {
        "measured_spread_report": measured_spread,
        "measured_slippage_report": measured_slippage,
        "book_staleness_ms": book_staleness_ms,
        "best_bid": best_bid,
        "best_ask": best_ask,
        "mid_price": mid_price,
        "spread_bps_measured": spread_bps_measured,
        "slippage_bps_measured": slippage_bps_measured,
        "expected_cost_decimal_measured": expected_cost_decimal_measured,
        "depth_fill_ratio": depth_fill_ratio,
        "partial_fill_status": partial_fill_status,
        "spread_source_status": spread_source_status,
        "slippage_source_status": slippage_source_status,
        "cost_source_used_for_break_even": usage,
        "cost_source_used_for_expected_ce_net": usage,
        "expected_cost_truth_status": expected_cost_truth_status,
        "expected_cost_block_reason": block_reason,
        "fill_realism_status": fill_realism_status,
        "impact_source_status": impact_source_status,
        "spread_provenance_for_payload": _spread_provenance_for_payload(measured_spread),
        "slippage_provenance_for_payload": _slippage_provenance_for_payload(
            measured_slippage
        ),
    }


def build_replay_outcome_payload(
    *,
    candidate: StrategyLadderCandidateEvent,
    window_manifest: StrategyLadderRawWindowManifest | None,
    decision_timestamp_ms: int,
    evidence_cache: StrategyLadderReplayEvidenceCache | None = None,
) -> dict[str, object]:
    payload = _candidate_payload(candidate)
    entry_price = _payload_entry_price(payload)
    side = _payload_side(payload) or "buy"
    if window_manifest is None or not window_manifest.raw_ohlcv_path:
        return {
            "status": "REPLAY_OUTCOME_BLOCKED_BY_MISSING_POST_WINDOW",
            "entry_reference_status": (
                "ENTRY_REFERENCE_DECISION_PRICE_PROXY"
                if entry_price is not None
                else "ENTRY_REFERENCE_NOT_AVAILABLE"
            ),
            "mfe_mae_status": (
                "MFE_MAE_BLOCKED_BY_MISSING_POST_WINDOW"
                if entry_price is not None
                else "MFE_MAE_BLOCKED_BY_NO_ENTRY_REFERENCE"
            ),
            "entry_ref": (
                {
                    "reference_type": "decision_price_proxy",
                    "timestamp_ms": decision_timestamp_ms,
                    "price": entry_price,
                    "source_field": "entry_price_or_close_price",
                }
                if entry_price is not None
                else {}
            ),
            "exit_ref": {},
            "invalidation_ref": {},
            "holding_time_ms": None,
            "forward_return_h1": None,
            "forward_return_h5": None,
            "forward_return_h10": None,
            "mfe_bps": None,
            "mae_bps": None,
        }
    if evidence_cache is not None:
        bars = evidence_cache.load_ohlcv_rows(window_manifest)
    else:
        bars = sorted(
            (
                row
                for row in _iter_jsonl(Path(window_manifest.raw_ohlcv_path))
                if isinstance(row.get("timestamp_ms"), (int, float))
            ),
            key=lambda row: int(row.get("timestamp_ms") or 0),
        )
    future_bars = [
        row for row in bars if int(row.get("timestamp_ms") or 0) > decision_timestamp_ms
    ]
    entry_ref = (
        {
            "reference_type": "decision_price_proxy",
            "timestamp_ms": decision_timestamp_ms,
            "price": entry_price,
            "source_field": "entry_price_or_close_price",
        }
        if entry_price is not None and entry_price > 0.0
        else {}
    )
    entry_reference_status = (
        "ENTRY_REFERENCE_DECISION_PRICE_PROXY"
        if entry_ref
        else "ENTRY_REFERENCE_NOT_AVAILABLE"
    )
    if not future_bars:
        return {
            "status": "REPLAY_OUTCOME_BLOCKED_BY_MISSING_POST_WINDOW",
            "entry_reference_status": entry_reference_status,
            "mfe_mae_status": (
                "MFE_MAE_BLOCKED_BY_MISSING_POST_WINDOW"
                if entry_ref
                else "MFE_MAE_BLOCKED_BY_NO_ENTRY_REFERENCE"
            ),
            "entry_ref": entry_ref,
            "exit_ref": {},
            "invalidation_ref": {},
            "holding_time_ms": None,
            "forward_return_h1": None,
            "forward_return_h5": None,
            "forward_return_h10": None,
            "mfe_bps": None,
            "mae_bps": None,
        }
    forward_returns: dict[int, float | None] = {}
    for horizon in _OUTCOME_BAR_HORIZONS:
        if len(future_bars) >= horizon and entry_price is not None and entry_price > 0.0:
            forward_returns[horizon] = _signed_return_bps(
                entry_price=entry_price,
                target_price=float(future_bars[horizon - 1].get("close") or 0.0),
                side=side,
            )
        else:
            forward_returns[horizon] = None
    if not entry_ref:
        return {
            "status": "REPLAY_OUTCOME_RESEARCH_ONLY",
            "entry_reference_status": entry_reference_status,
            "mfe_mae_status": "MFE_MAE_BLOCKED_BY_NO_ENTRY_REFERENCE",
            "entry_ref": {},
            "exit_ref": {},
            "invalidation_ref": {},
            "holding_time_ms": None,
            "forward_return_h1": forward_returns[1],
            "forward_return_h5": forward_returns[5],
            "forward_return_h10": forward_returns[10],
            "mfe_bps": None,
            "mae_bps": None,
        }
    bars_for_excursion = future_bars[: min(len(future_bars), _MFE_MAE_MAX_BARS)]
    highs = [float(row.get("high") or 0.0) for row in bars_for_excursion]
    lows = [float(row.get("low") or 0.0) for row in bars_for_excursion]
    if side == "sell":
        mfe_bps = round(
            max(_signed_return_bps(entry_price=entry_price, target_price=low, side=side) for low in lows),
            6,
        )
        mae_bps = round(
            min(_signed_return_bps(entry_price=entry_price, target_price=high, side=side) for high in highs),
            6,
        )
    else:
        mfe_bps = round(
            max(_signed_return_bps(entry_price=entry_price, target_price=high, side=side) for high in highs),
            6,
        )
        mae_bps = round(
            min(_signed_return_bps(entry_price=entry_price, target_price=low, side=side) for low in lows),
            6,
        )
    exit_bar = bars_for_excursion[-1]
    holding_time_ms = max(int(exit_bar.get("timestamp_ms") or 0) - decision_timestamp_ms, 0)
    return {
        "status": "REPLAY_OUTCOME_RESEARCH_ONLY",
        "entry_reference_status": entry_reference_status,
        "mfe_mae_status": "MFE_MAE_AVAILABLE_PROXY_ENTRY_REFERENCE",
        "entry_ref": entry_ref,
        "exit_ref": {
            "reference_type": "post_window_close_proxy",
            "timestamp_ms": int(exit_bar.get("timestamp_ms") or 0),
            "price": float(exit_bar.get("close") or 0.0),
        },
        "invalidation_ref": {},
        "holding_time_ms": holding_time_ms,
        "forward_return_h1": forward_returns[1],
        "forward_return_h5": forward_returns[5],
        "forward_return_h10": forward_returns[10],
        "mfe_bps": mfe_bps,
        "mae_bps": mae_bps,
    }


def build_adverse_selection_payload(
    *,
    replay_outcome: dict[str, object],
    execution_state: str,
) -> dict[str, object]:
    entry_reference_status = str(replay_outcome.get("entry_reference_status") or "")
    if entry_reference_status != "ENTRY_REFERENCE_EXECUTED_FILL_MEASURED":
        status = (
            "ADVERSE_SELECTION_BLOCKED_BY_NO_EXECUTED_TRADES"
            if execution_state not in {"executed", "reduced"}
            else "ADVERSE_SELECTION_BLOCKED_BY_NO_ENTRY_REFERENCE"
        )
        return {
            "status": status,
            "adverse_selection_bps": None,
            "source_timestamp_ms": None,
            "source_path": "",
        }
    return {
        "status": "ADVERSE_SELECTION_READY",
        "adverse_selection_bps": None,
        "source_timestamp_ms": None,
        "source_path": "",
    }


def build_fill_realism_payload(*, execution_state: str) -> dict[str, object]:
    if execution_state in {"executed", "reduced", "phantom"}:
        return {
            "status": "FILL_REALISM_PARTIAL_REPLAY",
            "queue_position_status": "QUEUE_POSITION_NOT_PROVEN",
        }
    return {
        "status": "FILL_REALISM_NOT_PROVEN",
        "queue_position_status": "QUEUE_POSITION_NOT_PROVEN",
    }


def build_strategy_ladder_replay_evidence(
    *,
    candidate: StrategyLadderCandidateEvent,
    window_manifest: StrategyLadderRawWindowManifest | None,
    planned_notional: float | None,
    execution_state: str,
    evidence_cache: StrategyLadderReplayEvidenceCache | None = None,
) -> StrategyLadderReplayEvidenceBundle:
    decision_timestamp_ms = candidate.resolved_timestamp_ms
    measured_spread = build_measured_spread_payload(
        window_manifest=window_manifest,
        decision_timestamp_ms=decision_timestamp_ms,
        evidence_cache=evidence_cache,
    )
    measured_slippage = build_measured_slippage_payload(
        candidate=candidate,
        window_manifest=window_manifest,
        planned_notional=planned_notional,
        decision_timestamp_ms=decision_timestamp_ms,
        evidence_cache=evidence_cache,
    )
    replay_outcome = build_replay_outcome_payload(
        candidate=candidate,
        window_manifest=window_manifest,
        decision_timestamp_ms=decision_timestamp_ms,
        evidence_cache=evidence_cache,
    )
    adverse_selection = build_adverse_selection_payload(
        replay_outcome=replay_outcome,
        execution_state=execution_state,
    )
    fill_realism = build_fill_realism_payload(execution_state=execution_state)
    return StrategyLadderReplayEvidenceBundle(
        measured_spread=measured_spread,
        measured_slippage=measured_slippage,
        adverse_selection=adverse_selection,
        fill_realism=fill_realism,
        replay_outcome=replay_outcome,
    )


__all__ = [
    "StrategyLadderReplayEvidenceCache",
    "StrategyLadderReplayEvidenceCacheMetrics",
    "StrategyLadderReplayEvidenceBundle",
    "build_measured_cost_governance_payload",
    "build_strategy_ladder_replay_evidence",
]
