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
    base_snapshot = _select_base_snapshot(
        snapshots,
        window_start_ms=window_manifest.window_start_ms,
    )
    if base_snapshot is None:
        return None, "SPREAD_BLOCKED_BY_MISSING_BOOK", str(raw_book_path.resolve())
    delta_path = _resolve_book_delta_path(
        raw_book_path,
        window_manifest.raw_book_delta_path,
    )
    states: list[_BookState] = []
    if delta_path is not None and delta_path.exists():
        deltas = _load_book_deltas_in_window_with_lookback(
            delta_path,
            base_update_id=int(base_snapshot.get("update_id") or 0),
            window_end_ms=window_manifest.window_end_ms,
        )
        states = _reconstruct_book_states(
            base_snapshot=base_snapshot,
            deltas=deltas,
            window_start_ms=window_manifest.window_start_ms,
            window_end_ms=window_manifest.window_end_ms,
            top_k=20,
        )
    if states:
        eligible = [
            state
            for state in states
            if state.timestamp_ms <= decision_timestamp_ms
        ]
        selected = eligible[-1] if eligible else states[0]
        return (
            selected,
            "SPREAD_MEASURED_FROM_BOOK",
            str((delta_path or raw_book_path).resolve()),
        )
    fallback_state = _book_state_from_snapshot(base_snapshot, top_k=20)
    if fallback_state is None:
        return None, "SPREAD_BLOCKED_BY_MISSING_BOOK", str(raw_book_path.resolve())
    return (
        fallback_state,
        "SPREAD_MEASURED_STALE_AUDIT_ONLY",
        str(raw_book_path.resolve()),
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
            "status": "SLIPPAGE_BLOCKED_BY_INSUFFICIENT_TRADES",
            "planned_notional": planned_notional,
            "side": side,
            "depth_top1_notional": None,
            "depth_top5_notional": None,
            "depth_top20_notional": None,
            "walk_cost_bps": None,
            "impact_bps": None,
            "depth_fill_ratio": 0.0,
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
    return {
        "status": "SLIPPAGE_ESTIMATED_FROM_DEPTH20",
        "planned_notional": None if planned_notional is None else round(float(planned_notional), 6),
        "side": side,
        "depth_top1_notional": _depth_notional(levels, 1),
        "depth_top5_notional": _depth_notional(levels, 5),
        "depth_top20_notional": _depth_notional(levels, 20),
        "walk_cost_bps": walk_cost_bps,
        "impact_bps": walk_cost_bps,
        "depth_fill_ratio": fill_ratio,
        "source_timestamp_ms": book_state.timestamp_ms,
        "staleness_ms": max(decision_timestamp_ms - book_state.timestamp_ms, 0),
        "source_path": source_path,
        "kyle_lambda": None,
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
    "build_strategy_ladder_replay_evidence",
]
