"""Bounded Binance Spot execution adapter for the Build-3 runtime."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from typing import cast

from execution_backbone.execution_runtime_models import (
    ExecutionVenueAdapter,
    RemoteExecutionState,
    ReplaceReceipt,
    SubmitReceipt,
)
from execution_backbone.order_decider.intent_builder import ExecutionIntent, VenueConstraintSnapshot
from execution_backbone.venue_constraints_provider import VenueConstraintProvider
from interface_contracts import execution_decimal
from interface_contracts.binance_contracts import BinanceAccountSnapshot, BinanceOpenOrder, BinanceOrderAck
from venue_adapters.binance_spot.order_translator import translate_execution_intent_to_binance_order
from venue_adapters.binance_spot.rest_client import BinanceRestClient
from venue_adapters.binance_spot.time_sync import BinanceAdapterConfig
from venue_adapters.binance_spot.user_data_events import (
    BinanceUserDataEventSource,
    parse_binance_user_data_payloads,
)


def _run_async(awaitable: Awaitable[object]) -> object:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(awaitable)
    raise RuntimeError(
        "BinanceSpotExecutionAdapter cannot be used inside a running event loop; "
        "inject an async-aware execution adapter instead"
    )


def _map_binance_open_order_status(status: str) -> str:
    normalized = status.strip().upper()
    mapping = {
        "NEW": "acked",
        "PARTIALLY_FILLED": "partially_filled",
        "FILLED": "filled",
        "CANCELED": "cancelled",
        "CANCELLED": "cancelled",
        "EXPIRED": "expired",
        "REJECTED": "rejected",
        "PENDING_NEW": "pending",
    }
    return mapping.get(normalized, normalized.lower())


class BinanceSpotExecutionAdapter(ExecutionVenueAdapter):
    """Synchronous bridge over the bounded Binance REST client.

    This adapter intentionally stays minimal:
    - submit / cancel / replace are supported
    - remote-state reconciliation uses open orders + account balances only
    - event polling is optional and drains a bounded authenticated user-data source when injected
    """

    def __init__(
        self,
        *,
        rest_client: BinanceRestClient,
        config: BinanceAdapterConfig,
        venue_constraint_provider: VenueConstraintProvider | None = None,
        user_data_event_source: BinanceUserDataEventSource | None = None,
    ) -> None:
        self._rest_client = rest_client
        self._config = config
        self._venue_constraint_provider = venue_constraint_provider
        self._user_data_event_source = user_data_event_source
        self._pair_by_order_id: dict[str, str] = {}

    def fetch_venue_constraints(self, pair: str) -> VenueConstraintSnapshot | None:
        if self._venue_constraint_provider is None:
            return None
        return self._venue_constraint_provider.fetch_venue_constraints(pair)

    def submit_order(self, intent: ExecutionIntent, now: float) -> SubmitReceipt:
        request = translate_execution_intent_to_binance_order(intent)
        ack = cast(
            BinanceOrderAck,
            _run_async(
                self._rest_client.submit_order(
                    request,
                    recv_window_ms=self._config.recv_window_ms,
                )
            ),
        )
        submitted_at = ack.transact_time_ms / 1000.0
        order_id = str(ack.order_id)
        self._pair_by_order_id[order_id] = intent.pair
        return SubmitReceipt(
            order_id=order_id,
            submitted_at=submitted_at,
        )

    def replace_order(self, original_order_id: str, intent: ExecutionIntent, now: float) -> ReplaceReceipt:
        replacement_request = translate_execution_intent_to_binance_order(intent)
        _run_async(
            self._rest_client.cancel_order(
                pair=intent.pair,
                order_id=int(original_order_id),
                recv_window_ms=self._config.recv_window_ms,
            )
        )
        ack = cast(
            BinanceOrderAck,
            _run_async(
                self._rest_client.submit_order(
                    replacement_request,
                    recv_window_ms=self._config.recv_window_ms,
                )
            ),
        )
        submitted_at = ack.transact_time_ms / 1000.0
        replacement_order_id = str(ack.order_id)
        self._pair_by_order_id.pop(original_order_id, None)
        self._pair_by_order_id[replacement_order_id] = intent.pair
        return ReplaceReceipt(
            original_order_id=original_order_id,
            replacement_order_id=replacement_order_id,
            replaced_at=now,
            submitted_at=submitted_at,
        )

    def cancel_order(self, order_id: str, now: float, reason: str = "") -> None:
        # The runtime remains the authoritative local state owner; the adapter only
        # keeps enough pair metadata to resolve Binance cancel requests safely.
        pair = self._pair_by_order_id.get(order_id)
        if pair is None:
            pair = self._resolve_pair_for_cancel(order_id)
        _run_async(
            self._rest_client.cancel_order(
                pair=pair,
                order_id=int(order_id),
                recv_window_ms=self._config.recv_window_ms,
            )
        )

    def poll_order_events(self) -> tuple:
        if self._user_data_event_source is None:
            return ()
        return parse_binance_user_data_payloads(self._user_data_event_source.poll_events())

    def fetch_remote_state(self) -> RemoteExecutionState:
        open_orders = cast(
            tuple[BinanceOpenOrder, ...],
            _run_async(
                self._rest_client.get_open_orders(
                    recv_window_ms=self._config.recv_window_ms,
                )
            ),
        )
        account_snapshot = cast(
            BinanceAccountSnapshot,
            _run_async(
                self._rest_client.get_account_snapshot(
                    recv_window_ms=self._config.recv_window_ms,
                )
            ),
        )
        positions: dict[str, float] = {}
        for balance in account_snapshot.balances:
            total = execution_decimal(balance.free) + execution_decimal(balance.locked)
            if total <= 0:
                continue
            positions[balance.asset] = float(total)
        return RemoteExecutionState(
            orders={
                str(order.order_id): _map_binance_open_order_status(order.status)
                for order in open_orders
            },
            fills={},
            positions=positions,
        )

    def _resolve_pair_for_cancel(self, order_id: str) -> str:
        open_orders = cast(
            tuple[BinanceOpenOrder, ...],
            _run_async(
                self._rest_client.get_open_orders(
                    recv_window_ms=self._config.recv_window_ms,
                )
            ),
        )
        for order in open_orders:
            if str(order.order_id) == str(order_id):
                return order.symbol
        raise KeyError(f"Unknown Binance open order id '{order_id}'")

    def close(self) -> None:
        close_user_data = getattr(self._user_data_event_source, "close", None)
        if callable(close_user_data):
            close_user_data()
        _run_async(self._rest_client.aclose())


__all__ = ["BinanceSpotExecutionAdapter"]
