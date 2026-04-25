"""Bootstrap helpers for building the bounded Binance Spot execution adapter."""

from __future__ import annotations

from collections.abc import Callable

import httpx

from execution_backbone.venue_constraints_provider import VenueConstraintProvider
from interface_contracts.binance_contracts import BinanceCredentials
from venue_adapters.binance_spot.execution_adapter import BinanceSpotExecutionAdapter
from venue_adapters.binance_spot.rest_client import BinanceRestClient
from venue_adapters.binance_spot.time_sync import BinanceAdapterConfig
from venue_adapters.binance_spot.user_data_ws_client import (
    BinanceUserDataWebSocketConfig,
    BinanceUserDataWebSocketEventSource,
    UserDataSocketFactory,
)


def build_binance_spot_execution_adapter(
    *,
    credentials: BinanceCredentials,
    config: BinanceAdapterConfig,
    venue_constraint_provider: VenueConstraintProvider | None = None,
    http_client: httpx.AsyncClient | None = None,
    user_data_stream_enabled: bool = False,
    user_data_socket_factory: UserDataSocketFactory | None = None,
    clock_ms: Callable[[], int] | None = None,
) -> BinanceSpotExecutionAdapter:
    """Build the bounded Binance Spot execution adapter from typed config."""

    rest_client = BinanceRestClient(
        credentials=credentials,
        base_url=config.rest_base_url,
        timeout_s=config.timeout_s,
        client=http_client,
        clock_ms=clock_ms,
    )
    user_data_event_source = None
    if user_data_stream_enabled:
        user_data_event_source = BinanceUserDataWebSocketEventSource(
            credentials=credentials,
            config=BinanceUserDataWebSocketConfig(
                endpoint=config.user_data_websocket_endpoint,
                connect_timeout_s=config.user_data_connect_timeout_s,
                recv_timeout_s=config.user_data_recv_timeout_s,
                recv_window_ms=config.recv_window_ms,
                max_messages_per_poll=config.user_data_max_messages_per_poll,
            ),
            socket_factory=user_data_socket_factory,
            clock_ms=clock_ms,
        )
    return BinanceSpotExecutionAdapter(
        rest_client=rest_client,
        config=config,
        venue_constraint_provider=venue_constraint_provider,
        user_data_event_source=user_data_event_source,
    )


__all__ = ["build_binance_spot_execution_adapter"]
