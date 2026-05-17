"""Bounded authenticated Binance user-data event parsing for execution runtime."""

from __future__ import annotations

from collections import deque
from collections.abc import Iterable, Mapping
from typing import Protocol

from execution_backbone.execution_runtime_models import VenueOrderEvent, VenueOrderEventType
from interface_contracts import execution_decimal
from interface_contracts.binance_contracts import BinanceUserDataExecutionReport


class BinanceUserDataEventSource(Protocol):
    """Bounded raw Binance user-data event source for the execution adapter."""

    def poll_events(self) -> tuple[dict[str, object], ...]:
        ...


class BufferedBinanceUserDataEventSource(BinanceUserDataEventSource):
    """Simple in-memory buffer used by tests and future websocket bridges."""

    def __init__(
        self,
        initial_events: Iterable[dict[str, object]] = (),
        *,
        max_events: int = 2048,
    ) -> None:
        if max_events <= 0:
            raise ValueError("max_events must be > 0")
        self._events: deque[dict[str, object]] = deque(
            (dict(event) for event in initial_events),
            maxlen=max_events,
        )

    def push(self, *events: dict[str, object]) -> None:
        for event in events:
            self._events.append(dict(event))

    def poll_events(self) -> tuple[dict[str, object], ...]:
        drained = tuple(self._events)
        self._events.clear()
        return drained


def parse_binance_user_data_payloads(
    payloads: Iterable[Mapping[str, object]],
) -> tuple[VenueOrderEvent, ...]:
    """Convert bounded Binance user-data payloads into execution runtime events."""

    collected: list[VenueOrderEvent] = []
    for payload in payloads:
        collected.extend(parse_binance_user_data_payload(payload))
    return tuple(collected)


def parse_binance_user_data_payload(payload: Mapping[str, object]) -> tuple[VenueOrderEvent, ...]:
    normalized_payload = _resolve_event_payload(payload)
    event_type = str(normalized_payload.get("e", "")).strip()
    if event_type != "executionReport":
        return ()
    report = BinanceUserDataExecutionReport.model_validate(normalized_payload)
    event = _convert_execution_report(report)
    if event is None:
        return ()
    return (event,)


def _convert_execution_report(report: BinanceUserDataExecutionReport) -> VenueOrderEvent | None:
    execution_type = report.execution_type.strip().upper()
    order_status = report.order_status.strip().upper()
    timestamp = report.event_time_ms / 1000.0
    order_id = str(report.order_id)

    if execution_type == "NEW":
        return VenueOrderEvent(
            order_id=order_id,
            event_type=VenueOrderEventType.ACK,
            timestamp=timestamp,
        )

    if execution_type == "TRADE":
        fill_quantity = float(execution_decimal(report.last_executed_quantity))
        if fill_quantity <= 0:
            return None
        fill_id = None if report.trade_id < 0 else str(report.trade_id)
        return VenueOrderEvent(
            order_id=order_id,
            event_type=VenueOrderEventType.FILL,
            timestamp=timestamp,
            fill_id=fill_id,
            fill_quantity=fill_quantity,
            fill_price=float(execution_decimal(report.last_executed_price)),
            fee_amount=float(execution_decimal(report.commission_amount)),
            fee_asset=(report.commission_asset or "").strip(),
        )

    if execution_type in {"CANCELED", "CANCELLED"} or order_status in {"CANCELED", "CANCELLED"}:
        return VenueOrderEvent(
            order_id=order_id,
            event_type=VenueOrderEventType.CANCELLED,
            timestamp=timestamp,
            reason=_resolve_terminal_reason(report),
        )

    if execution_type == "EXPIRED" or order_status == "EXPIRED":
        return VenueOrderEvent(
            order_id=order_id,
            event_type=VenueOrderEventType.EXPIRED,
            timestamp=timestamp,
            reason=_resolve_terminal_reason(report),
        )

    if execution_type == "REJECTED" or order_status == "REJECTED":
        return VenueOrderEvent(
            order_id=order_id,
            event_type=VenueOrderEventType.REJECTED,
            timestamp=timestamp,
            reason=_resolve_terminal_reason(report),
        )

    return None


def _resolve_terminal_reason(report: BinanceUserDataExecutionReport) -> str:
    reason = report.reject_reason.strip()
    if reason and reason.upper() != "NONE":
        return reason
    return report.order_status.strip().lower()


def _resolve_event_payload(payload: Mapping[str, object]) -> Mapping[str, object]:
    nested = payload.get("event")
    if isinstance(nested, Mapping):
        return nested
    return payload


__all__ = [
    "BinanceUserDataEventSource",
    "BufferedBinanceUserDataEventSource",
    "parse_binance_user_data_payload",
    "parse_binance_user_data_payloads",
]
