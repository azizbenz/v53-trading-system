"""Deterministic snapshot+delta orderbook reconstruction for Patch 6."""

from __future__ import annotations

from dataclasses import dataclass

from data_backbone.microstructure import LobBookLevel, LobDepth20Snapshot


@dataclass(frozen=True)
class StrategyLadderOrderbookReconstructionResult:
    """Resolved orderbook state around one candidate timestamp."""

    pair: str
    anchor_timestamp_ms: int
    book_depth_source_status: str
    sequence_status: str
    reason_codes: tuple[str, ...]
    reconstructed_snapshot: LobDepth20Snapshot | None
    gap_status: str = "ORDERBOOK_SEQUENCE_NOT_PROVEN"
    gap_count: int = 0
    first_gap_expected_seq: int | None = None
    first_gap_actual_seq: int | None = None
    first_gap_previous_seq: int | None = None
    first_gap_event_timestamp_ms: int | None = None
    reconstruction_success_after_gap: bool = False


def _parse_levels(raw_levels: object) -> list[tuple[float, float]]:
    if not isinstance(raw_levels, list):
        return []
    normalized: list[tuple[float, float]] = []
    for item in raw_levels:
        if isinstance(item, dict):
            price = item.get("price")
            qty = item.get("qty") or item.get("quantity") or item.get("size")
        elif isinstance(item, (list, tuple)) and len(item) >= 2:
            price, qty = item[0], item[1]
        else:
            continue
        try:
            price_value = float(price)
            qty_value = float(qty)
        except (TypeError, ValueError):
            continue
        if price_value <= 0.0:
            continue
        normalized.append((price_value, qty_value))
    return normalized


def _sorted_bid_levels(book: dict[float, float]) -> tuple[LobBookLevel, ...]:
    return tuple(
        LobBookLevel(price=price, size=size)
        for price, size in sorted(book.items(), key=lambda item: item[0], reverse=True)[:20]
        if size > 0.0
    )


def _sorted_ask_levels(book: dict[float, float]) -> tuple[LobBookLevel, ...]:
    return tuple(
        LobBookLevel(price=price, size=size)
        for price, size in sorted(book.items(), key=lambda item: item[0])[:20]
        if size > 0.0
    )


def _apply_side_updates(book: dict[float, float], levels: list[tuple[float, float]]) -> None:
    for price, qty in levels:
        if qty == 0.0:
            book.pop(price, None)
            continue
        book[price] = qty


def _sequence_value(row: dict[str, object]) -> int | None:
    for key in ("u", "seq", "sequence"):
        value = row.get(key)
        if value in (None, ""):
            continue
        try:
            return int(value)
        except (TypeError, ValueError):
            continue
    return None


def reconstruct_strategy_ladder_orderbook(
    *,
    pair: str,
    anchor_timestamp_ms: int,
    snapshot_rows: tuple[dict[str, object], ...],
    delta_rows: tuple[dict[str, object], ...],
) -> StrategyLadderOrderbookReconstructionResult:
    """Reconstruct top20 depth from one snapshot chain and ordered deltas."""

    if not snapshot_rows:
        return StrategyLadderOrderbookReconstructionResult(
            pair=pair,
            anchor_timestamp_ms=anchor_timestamp_ms,
            book_depth_source_status="BOOK_DEPTH_NOT_PROVEN",
            sequence_status="MISSING_SNAPSHOT",
            gap_status="ORDERBOOK_SEQUENCE_NOT_PROVEN",
            reason_codes=("MISSING_SNAPSHOT",),
            reconstructed_snapshot=None,
        )
    timeline: list[tuple[int, int, dict[str, object]]] = []
    for row in snapshot_rows:
        timestamp_ms = int(row.get("timestamp_ms") or 0)
        if timestamp_ms <= anchor_timestamp_ms:
            timeline.append((timestamp_ms, 0, row))
    for row in delta_rows:
        timestamp_ms = int(row.get("timestamp_ms") or 0)
        if timestamp_ms <= anchor_timestamp_ms:
            timeline.append((timestamp_ms, 1, row))
    timeline.sort(
        key=lambda item: (
            item[0],
            item[1],
            _sequence_value(item[2]) if _sequence_value(item[2]) is not None else -1,
        )
    )
    bids_book: dict[float, float] = {}
    asks_book: dict[float, float] = {}
    previous_sequence: int | None = None
    gap_count = 0
    first_gap_expected_seq: int | None = None
    first_gap_actual_seq: int | None = None
    first_gap_previous_seq: int | None = None
    first_gap_event_timestamp_ms: int | None = None
    gap_detected = False
    recovered_after_gap = False
    chain_ready = False
    for timestamp_ms, event_rank, row in timeline:
        if event_rank == 0:
            bids_book = {}
            asks_book = {}
            _apply_side_updates(
                bids_book,
                _parse_levels(row.get("bids") or row.get("b") or []),
            )
            _apply_side_updates(
                asks_book,
                _parse_levels(row.get("asks") or row.get("a") or []),
            )
            previous_sequence = _sequence_value(row)
            if gap_detected:
                recovered_after_gap = True
            chain_ready = True
            continue
        if not chain_ready:
            continue
        current_sequence = _sequence_value(row)
        if (
            current_sequence is not None
            and previous_sequence is not None
            and current_sequence > previous_sequence + 1
        ):
            gap_detected = True
            gap_count += 1
            if first_gap_expected_seq is None:
                first_gap_expected_seq = previous_sequence + 1
                first_gap_actual_seq = current_sequence
                first_gap_previous_seq = previous_sequence
                first_gap_event_timestamp_ms = timestamp_ms
            bids_book = {}
            asks_book = {}
            previous_sequence = None
            chain_ready = False
            continue
        _apply_side_updates(
            bids_book, _parse_levels(row.get("bids") or row.get("b") or [])
        )
        _apply_side_updates(
            asks_book, _parse_levels(row.get("asks") or row.get("a") or [])
        )
        if current_sequence is not None:
            previous_sequence = current_sequence
    if gap_detected and not chain_ready:
        return StrategyLadderOrderbookReconstructionResult(
            pair=pair,
            anchor_timestamp_ms=anchor_timestamp_ms,
            book_depth_source_status="BOOK_DEPTH_STALE",
            sequence_status="SEQUENCE_GAP",
            gap_status="ORDERBOOK_SEQUENCE_GAP_UNRECOVERED",
            gap_count=gap_count,
            first_gap_expected_seq=first_gap_expected_seq,
            first_gap_actual_seq=first_gap_actual_seq,
            first_gap_previous_seq=first_gap_previous_seq,
            first_gap_event_timestamp_ms=first_gap_event_timestamp_ms,
            reconstruction_success_after_gap=False,
            reason_codes=(
                "SEQUENCE_GAP",
                "ORDERBOOK_SEQUENCE_GAP_UNRECOVERED",
                "NO_PROMOTION_GRADE_DEPTH_AFTER_GAP",
            ),
            reconstructed_snapshot=None,
        )
    bids = _sorted_bid_levels(bids_book)
    asks = _sorted_ask_levels(asks_book)
    if not bids or not asks:
        return StrategyLadderOrderbookReconstructionResult(
            pair=pair,
            anchor_timestamp_ms=anchor_timestamp_ms,
            book_depth_source_status="BOOK_DEPTH_NOT_PROVEN",
            sequence_status="EMPTY_RECONSTRUCTION",
            gap_status=(
                "ORDERBOOK_SEQUENCE_GAP_RECOVERED"
                if recovered_after_gap
                else "ORDERBOOK_SEQUENCE_READY"
            ),
            gap_count=gap_count,
            first_gap_expected_seq=first_gap_expected_seq,
            first_gap_actual_seq=first_gap_actual_seq,
            first_gap_previous_seq=first_gap_previous_seq,
            first_gap_event_timestamp_ms=first_gap_event_timestamp_ms,
            reconstruction_success_after_gap=recovered_after_gap,
            reason_codes=("EMPTY_RECONSTRUCTION",),
            reconstructed_snapshot=None,
        )
    if len(bids) >= 20 and len(asks) >= 20:
        status = "BOOK_DEPTH20_AVAILABLE"
    elif len(bids) > 1 and len(asks) > 1:
        status = "BOOK_LIMITED_DEPTH_AVAILABLE"
    else:
        status = "BOOK_TOP_OF_BOOK_ONLY"
    snapshot = LobDepth20Snapshot(
        pair=pair,
        timestamp_ns=anchor_timestamp_ms * 1_000_000,
        bids=bids,
        asks=asks,
    )
    return StrategyLadderOrderbookReconstructionResult(
        pair=pair,
        anchor_timestamp_ms=anchor_timestamp_ms,
        book_depth_source_status=status,
        sequence_status=(
            "SEQUENCE_GAP_RECOVERED" if recovered_after_gap else "SEQUENCE_READY"
        ),
        gap_status=(
            "ORDERBOOK_SEQUENCE_GAP_RECOVERED"
            if recovered_after_gap
            else "ORDERBOOK_SEQUENCE_READY"
        ),
        gap_count=gap_count,
        first_gap_expected_seq=first_gap_expected_seq,
        first_gap_actual_seq=first_gap_actual_seq,
        first_gap_previous_seq=first_gap_previous_seq,
        first_gap_event_timestamp_ms=first_gap_event_timestamp_ms,
        reconstruction_success_after_gap=recovered_after_gap,
        reason_codes=(
            ("ORDERBOOK_SEQUENCE_GAP_RECOVERED",)
            if recovered_after_gap
            else ()
        ),
        reconstructed_snapshot=snapshot,
    )


__all__ = [
    "StrategyLadderOrderbookReconstructionResult",
    "reconstruct_strategy_ladder_orderbook",
]
