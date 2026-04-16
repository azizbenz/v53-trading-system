"""Bounded Binance Spot adapter surfaces for P0-1."""

from __future__ import annotations

from venue_adapters.binance_spot.account_feature_provider import BinanceAccountFeatureAuditProvider
from venue_adapters.binance_spot.credential_loader import (
    BinanceCredentialLoadError,
    load_binance_credentials,
    load_binance_credentials_from_env,
    load_binance_credentials_from_file,
)
from venue_adapters.binance_spot.bootstrap import build_binance_spot_execution_adapter
from venue_adapters.binance_spot.execution_adapter import BinanceSpotExecutionAdapter
from venue_adapters.binance_spot.error_classifier import classify_binance_order_error
from venue_adapters.binance_spot.order_translator import (
    build_binance_client_order_id,
    translate_execution_intent_to_binance_order,
)
from venue_adapters.binance_spot.rest_client import BinanceRestClient
from venue_adapters.binance_spot.time_sync import (
    BinanceAdapterConfig,
    BinanceTimeSync,
    load_binance_adapter_config,
    resolve_time_sync_threshold_ms,
    resolve_websocket_gap_threshold_s,
)
from venue_adapters.binance_spot.orderbook_manager import (
    BinanceDepthDelta,
    BinanceDepthSnapshot,
    BinanceOrderBookManager,
    BinanceOrderBookStatus,
    OrderBookSyncState,
)
from venue_adapters.binance_spot.rate_limiter import (
    BinanceApiRateLimiter,
    BinanceApiRateLimiterConfig,
    BinanceApiRateLimiterSnapshot,
    BinanceApiRateLimitExceededError,
    BinanceRequestQuotaCost,
    classify_binance_request_quota_cost,
)
from venue_adapters.binance_spot.ws_client import (
    BinanceDepthWebSocketClient,
    BinanceWsClientConfig,
    BinanceWsClientPollResult,
    build_rest_depth_snapshot_provider,
)
from venue_adapters.binance_spot.user_data_events import (
    BinanceUserDataEventSource,
    BufferedBinanceUserDataEventSource,
    parse_binance_user_data_payload,
    parse_binance_user_data_payloads,
)
from venue_adapters.binance_spot.user_data_ws_client import (
    BinanceUserDataWebSocketConfig,
    BinanceUserDataWebSocketEventSource,
    build_user_data_subscribe_request,
)

__all__ = [
    "BinanceAdapterConfig",
    "BinanceAccountFeatureAuditProvider",
    "BinanceDepthDelta",
    "BinanceDepthSnapshot",
    "BinanceDepthWebSocketClient",
    "BinanceOrderBookManager",
    "BinanceOrderBookStatus",
    "BinanceApiRateLimiter",
    "BinanceApiRateLimiterConfig",
    "BinanceApiRateLimiterSnapshot",
    "BinanceApiRateLimitExceededError",
    "BinanceCredentialLoadError",
    "BinanceRestClient",
    "BinanceSpotExecutionAdapter",
    "BinanceTimeSync",
    "BinanceUserDataEventSource",
    "BinanceUserDataWebSocketConfig",
    "BinanceUserDataWebSocketEventSource",
    "BinanceWsClientConfig",
    "BinanceWsClientPollResult",
    "BufferedBinanceUserDataEventSource",
    "BinanceRequestQuotaCost",
    "OrderBookSyncState",
    "build_binance_spot_execution_adapter",
    "build_user_data_subscribe_request",
    "build_rest_depth_snapshot_provider",
    "build_binance_client_order_id",
    "classify_binance_request_quota_cost",
    "classify_binance_order_error",
    "load_binance_adapter_config",
    "load_binance_credentials",
    "load_binance_credentials_from_env",
    "load_binance_credentials_from_file",
    "parse_binance_user_data_payload",
    "parse_binance_user_data_payloads",
    "resolve_time_sync_threshold_ms",
    "resolve_websocket_gap_threshold_s",
    "translate_execution_intent_to_binance_order",
]
