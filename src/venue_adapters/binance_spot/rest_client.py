"""Bounded async REST client for Binance Spot."""

from __future__ import annotations

import hashlib
import hmac
import time
from typing import Any, Callable, Mapping
from urllib.parse import urlencode

import httpx

from interface_contracts import decimal_to_canonical_str, execution_decimal
from interface_contracts.binance_contracts import (
    BinanceAccountSnapshot,
    BinanceAssetBalance,
    BinanceOpenOrder,
    BinanceCredentials,
    BinanceExchangeInfo,
    BinanceOrderAck,
    BinanceOrderRequest,
    BinanceRateLimit,
    BinanceServerTime,
    BinanceSymbolInfo,
)
from venue_adapters.binance_spot.orderbook_manager import BinanceDepthSnapshot


class BinanceRestClient:
    """Async bounded client for Binance Spot REST endpoints."""

    def __init__(
        self,
        *,
        credentials: BinanceCredentials | None = None,
        base_url: str = "https://api.binance.com",
        timeout_s: float = 5.0,
        client: httpx.AsyncClient | None = None,
        clock_ms: Callable[[], int] | None = None,
    ) -> None:
        if timeout_s <= 0:
            raise ValueError("timeout_s must be > 0")
        self._credentials = credentials
        self._clock_ms = clock_ms or (lambda: time.time_ns() // 1_000_000)
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            timeout=timeout_s,
        )

    async def __aenter__(self) -> "BinanceRestClient":
        return self

    async def __aexit__(self, *_exc_info: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def get_server_time(self) -> BinanceServerTime:
        payload = await self._request_json("/api/v3/time")
        return BinanceServerTime(server_time_ms=int(payload["serverTime"]))

    async def get_exchange_info(self, *, pair: str | None = None) -> BinanceExchangeInfo:
        params: dict[str, str] = {}
        if pair:
            params["symbol"] = pair.upper()
        payload = await self._request_json("/api/v3/exchangeInfo", params=params)
        return _parse_exchange_info(payload)

    async def get_depth_snapshot(self, *, pair: str, limit: int = 1000) -> BinanceDepthSnapshot:
        if limit <= 0:
            raise ValueError("limit must be > 0")
        payload = await self._request_json(
            "/api/v3/depth",
            params={"symbol": pair.upper(), "limit": str(limit)},
        )
        return _parse_depth_snapshot(
            payload,
            pair=pair.upper(),
            recv_time_s=self._clock_ms() / 1000.0,
        )

    async def get_account_snapshot(self, *, recv_window_ms: int) -> BinanceAccountSnapshot:
        if self._credentials is None:
            raise RuntimeError("Authenticated Binance credentials are required for /api/v3/account")
        payload = await self._request_json(
            "/api/v3/account",
            params={"recvWindow": str(recv_window_ms)},
            signed=True,
        )
        return _parse_account_snapshot(payload)

    async def get_account_feature_payload(
        self,
        *,
        path: str,
        recv_window_ms: int,
        params: Mapping[str, str] | None = None,
    ) -> Mapping[str, Any] | list[Any]:
        if self._credentials is None:
            raise RuntimeError("Authenticated Binance credentials are required for account feature audit endpoints")
        if path not in _ALLOWED_ACCOUNT_FEATURE_AUDIT_PATHS:
            raise ValueError(f"Unsupported Binance account feature audit path: {path}")
        request_params = {"recvWindow": str(recv_window_ms)}
        request_params.update(dict(params or {}))
        return await self._request_payload(
            path,
            params=request_params,
            signed=True,
        )

    async def submit_order(
        self,
        request: BinanceOrderRequest,
        *,
        recv_window_ms: int,
    ) -> BinanceOrderAck:
        if self._credentials is None:
            raise RuntimeError("Authenticated Binance credentials are required for /api/v3/order")
        payload = await self._request_json(
            "/api/v3/order",
            method="POST",
            params=_build_order_params(request, recv_window_ms=recv_window_ms),
            signed=True,
        )
        return _parse_order_ack(payload)

    async def get_open_orders(
        self,
        *,
        pair: str | None = None,
        recv_window_ms: int,
    ) -> tuple[BinanceOpenOrder, ...]:
        if self._credentials is None:
            raise RuntimeError("Authenticated Binance credentials are required for /api/v3/openOrders")
        params = {"recvWindow": str(recv_window_ms)}
        if pair:
            params["symbol"] = pair.upper()
        payload = await self._request_payload(
            "/api/v3/openOrders",
            params=params,
            signed=True,
        )
        if not isinstance(payload, list):
            raise TypeError("Binance openOrders response must be a list")
        return tuple(_parse_open_order(entry) for entry in payload if isinstance(entry, Mapping))

    async def cancel_order(
        self,
        *,
        pair: str,
        order_id: int | None = None,
        client_order_id: str | None = None,
        recv_window_ms: int,
    ) -> None:
        if self._credentials is None:
            raise RuntimeError("Authenticated Binance credentials are required for /api/v3/order")
        if order_id is None and client_order_id is None:
            raise ValueError("cancel_order requires order_id or client_order_id")
        params = {
            "symbol": pair.upper(),
            "recvWindow": str(recv_window_ms),
        }
        if order_id is not None:
            params["orderId"] = str(order_id)
        if client_order_id is not None:
            params["origClientOrderId"] = client_order_id
        await self._request_json(
            "/api/v3/order",
            method="DELETE",
            params=params,
            signed=True,
        )

    async def _request_json(
        self,
        path: str,
        *,
        method: str = "GET",
        params: Mapping[str, str] | None = None,
        signed: bool = False,
    ) -> Mapping[str, Any]:
        payload = await self._request_payload(
            path,
            method=method,
            params=params,
            signed=signed,
        )
        if not isinstance(payload, Mapping):
            raise TypeError(f"Binance response for {path} must be a mapping")
        return payload

    async def _request_payload(
        self,
        path: str,
        *,
        method: str = "GET",
        params: Mapping[str, str] | None = None,
        signed: bool = False,
    ) -> Mapping[str, Any] | list[Any]:
        request_params = dict(params or {})
        headers: dict[str, str] = {}
        if signed:
            if self._credentials is None:
                raise RuntimeError("Cannot sign Binance request without credentials")
            request_params["timestamp"] = str(self._clock_ms())
            query_string = urlencode(list(request_params.items()))
            signature = hmac.new(
                self._credentials.secret_key.get_secret_value().encode("utf-8"),
                query_string.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()
            request_params["signature"] = signature
            headers["X-MBX-APIKEY"] = self._credentials.api_key.get_secret_value()

        response = await self._client.request(method, path, params=request_params, headers=headers)
        response.raise_for_status()
        payload = response.json()
        return payload


def _build_order_params(
    request: BinanceOrderRequest,
    *,
    recv_window_ms: int,
) -> dict[str, str]:
    params = {
        "symbol": request.symbol,
        "side": request.side.value,
        "type": request.order_type.value,
        "quantity": request.quantity,
        "newClientOrderId": request.client_order_id,
        "recvWindow": str(recv_window_ms),
    }
    if request.price is not None:
        params["price"] = request.price
    if request.time_in_force is not None:
        params["timeInForce"] = request.time_in_force.value
    return params


_ALLOWED_ACCOUNT_FEATURE_AUDIT_PATHS = frozenset(
    {
        "/sapi/v1/margin/account",
        "/sapi/v1/savings/account",
        "/sapi/v1/lending/project/position/list",
        "/sapi/v1/staking/position",
        "/sapi/v1/futures/transfer",
    }
)


def _canonical_decimal_str(value: object) -> str:
    return decimal_to_canonical_str(execution_decimal(value))


def _parse_exchange_info(payload: Mapping[str, Any]) -> BinanceExchangeInfo:
    rate_limits_raw = payload.get("rateLimits", [])
    rate_limits: list[BinanceRateLimit] = []
    if isinstance(rate_limits_raw, list):
        for entry in rate_limits_raw:
            if not isinstance(entry, Mapping):
                continue
            rate_limits.append(
                BinanceRateLimit(
                    rate_limit_type=str(entry.get("rateLimitType", "")),
                    interval=str(entry.get("interval", "")),
                    interval_num=int(entry.get("intervalNum", 1)),
                    limit=int(entry.get("limit", 0)),
                )
            )

    symbols_raw = payload.get("symbols", [])
    symbols: list[BinanceSymbolInfo] = []
    if isinstance(symbols_raw, list):
        for entry in symbols_raw:
            if not isinstance(entry, Mapping):
                continue
            tick_size = ""
            step_size = ""
            min_notional = ""
            filters = entry.get("filters", [])
            if isinstance(filters, list):
                for filter_entry in filters:
                    if not isinstance(filter_entry, Mapping):
                        continue
                    filter_type = str(filter_entry.get("filterType", "")).upper()
                    if filter_type == "PRICE_FILTER":
                        tick_size = _canonical_decimal_str(filter_entry.get("tickSize", "0"))
                    elif filter_type == "LOT_SIZE":
                        step_size = _canonical_decimal_str(filter_entry.get("stepSize", "0"))
                    elif filter_type in {"MIN_NOTIONAL", "NOTIONAL"} and not min_notional:
                        min_notional = _canonical_decimal_str(filter_entry.get("minNotional", "0"))
            symbols.append(
                BinanceSymbolInfo(
                    symbol=str(entry.get("symbol", "")),
                    status=str(entry.get("status", "")),
                    base_asset=str(entry.get("baseAsset", "")),
                    quote_asset=str(entry.get("quoteAsset", "")),
                    is_spot_trading_allowed=bool(entry.get("isSpotTradingAllowed", False)),
                    tick_size=tick_size,
                    step_size=step_size,
                    min_notional=min_notional,
                )
            )

    return BinanceExchangeInfo(
        timezone=str(payload.get("timezone", "")),
        server_time_ms=int(payload.get("serverTime", 0)),
        rate_limits=tuple(rate_limits),
        symbols=tuple(symbols),
    )


def _parse_account_snapshot(payload: Mapping[str, Any]) -> BinanceAccountSnapshot:
    balances_raw = payload.get("balances", [])
    balances: list[BinanceAssetBalance] = []
    if isinstance(balances_raw, list):
        for entry in balances_raw:
            if not isinstance(entry, Mapping):
                continue
            balances.append(
                BinanceAssetBalance(
                    asset=str(entry.get("asset", "")),
                    free=_canonical_decimal_str(entry.get("free", "0")),
                    locked=_canonical_decimal_str(entry.get("locked", "0")),
                )
            )

    return BinanceAccountSnapshot(
        maker_commission=int(payload.get("makerCommission", 0)),
        taker_commission=int(payload.get("takerCommission", 0)),
        buyer_commission=int(payload.get("buyerCommission", 0)),
        seller_commission=int(payload.get("sellerCommission", 0)),
        can_trade=bool(payload.get("canTrade", False)),
        can_withdraw=bool(payload.get("canWithdraw", False)),
        can_deposit=bool(payload.get("canDeposit", False)),
        account_type=str(payload.get("accountType", "")),
        update_time_ms=int(payload.get("updateTime", 0)),
        balances=tuple(balances),
    )


def _parse_order_ack(payload: Mapping[str, Any]) -> BinanceOrderAck:
    return BinanceOrderAck(
        symbol=str(payload.get("symbol", "")),
        order_id=int(payload.get("orderId", 0)),
        client_order_id=str(payload.get("clientOrderId", "")),
        transact_time_ms=int(payload.get("transactTime", 0)),
        status=str(payload.get("status", "")),
        side=str(payload.get("side", "BUY")).upper(),
        order_type=str(payload.get("type", "MARKET")).upper(),
        price=_canonical_decimal_str(payload.get("price", "0")),
        orig_qty=_canonical_decimal_str(payload.get("origQty", "0")),
        executed_qty=_canonical_decimal_str(payload.get("executedQty", "0")),
        time_in_force=str(payload.get("timeInForce", "")),
    )


def _parse_open_order(payload: Mapping[str, Any]) -> BinanceOpenOrder:
    return BinanceOpenOrder(
        symbol=str(payload.get("symbol", "")),
        order_id=int(payload.get("orderId", 0)),
        client_order_id=str(payload.get("clientOrderId", "")),
        status=str(payload.get("status", "")),
        side=str(payload.get("side", "BUY")).upper(),
        order_type=str(payload.get("type", "MARKET")).upper(),
        price=_canonical_decimal_str(payload.get("price", "0")),
        orig_qty=_canonical_decimal_str(payload.get("origQty", "0")),
        executed_qty=_canonical_decimal_str(payload.get("executedQty", "0")),
        time_in_force=str(payload.get("timeInForce", "")),
        update_time_ms=int(payload.get("updateTime", 0)),
    )


def _parse_depth_snapshot(
    payload: Mapping[str, Any],
    *,
    pair: str,
    recv_time_s: float,
) -> BinanceDepthSnapshot:
    bids_raw = payload.get("bids", [])
    asks_raw = payload.get("asks", [])

    def _normalize_levels(raw_levels: object) -> tuple[tuple[str, str], ...]:
        if not isinstance(raw_levels, list):
            return ()
        levels: list[tuple[str, str]] = []
        for entry in raw_levels:
            if not isinstance(entry, list | tuple) or len(entry) < 2:
                continue
            levels.append(
                (
                    _canonical_decimal_str(entry[0]),
                    _canonical_decimal_str(entry[1]),
                )
            )
        return tuple(levels)

    return BinanceDepthSnapshot(
        pair=pair,
        last_update_id=int(payload.get("lastUpdateId", 0)),
        bids=_normalize_levels(bids_raw),
        asks=_normalize_levels(asks_raw),
        recv_time_s=recv_time_s,
    )


__all__ = ["BinanceRestClient"]
