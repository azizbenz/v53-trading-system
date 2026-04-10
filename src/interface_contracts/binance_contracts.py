"""Typed contracts for the Binance Spot venue adapter."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, SecretStr, model_validator


class BinanceCredentials(BaseModel, frozen=True):
    """Authenticated Binance API credentials."""

    api_key: SecretStr = Field(..., min_length=1)
    secret_key: SecretStr = Field(..., min_length=1)
    label: str = ""


class BinanceServerTime(BaseModel, frozen=True):
    """Snapshot of Binance server time."""

    server_time_ms: int = Field(..., ge=0)


class BinanceTimeSyncResult(BaseModel, frozen=True):
    """Clock-drift comparison between local runtime and Binance server time."""

    server_time_ms: int = Field(..., ge=0)
    local_time_ms: int = Field(..., ge=0)
    drift_ms: int
    threshold_ms: int = Field(..., ge=0)
    alert_triggered: bool = False


class BinanceRateLimit(BaseModel, frozen=True):
    """Normalized Binance rate-limit metadata."""

    rate_limit_type: str = Field(..., min_length=1)
    interval: str = Field(..., min_length=1)
    interval_num: int = Field(..., ge=1)
    limit: int = Field(..., ge=0)


class BinanceSymbolInfo(BaseModel, frozen=True):
    """Normalized Binance symbol metadata."""

    symbol: str = Field(..., min_length=1)
    status: str = ""
    base_asset: str = ""
    quote_asset: str = ""
    is_spot_trading_allowed: bool = False
    tick_size: str = ""
    step_size: str = ""
    min_notional: str = ""


class BinanceExchangeInfo(BaseModel, frozen=True):
    """Read-only normalized exchange metadata."""

    timezone: str = ""
    server_time_ms: int = Field(..., ge=0)
    rate_limits: tuple[BinanceRateLimit, ...] = ()
    symbols: tuple[BinanceSymbolInfo, ...] = ()


class BinanceAssetBalance(BaseModel, frozen=True):
    """Normalized account balance row."""

    asset: str = Field(..., min_length=1)
    free: str = Field(..., min_length=1)
    locked: str = Field(..., min_length=1)


class BinanceAccountSnapshot(BaseModel, frozen=True):
    """Read-only authenticated account snapshot."""

    maker_commission: int = Field(default=0, ge=0)
    taker_commission: int = Field(default=0, ge=0)
    buyer_commission: int = Field(default=0, ge=0)
    seller_commission: int = Field(default=0, ge=0)
    can_trade: bool = False
    can_withdraw: bool = False
    can_deposit: bool = False
    account_type: str = ""
    update_time_ms: int = Field(default=0, ge=0)
    balances: tuple[BinanceAssetBalance, ...] = ()


class BinanceOrderSide(StrEnum):
    BUY = "BUY"
    SELL = "SELL"


class BinanceSpotOrderType(StrEnum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"


class BinanceTimeInForce(StrEnum):
    GTC = "GTC"


class BinanceOrderRequest(BaseModel, frozen=True):
    """Normalized Binance Spot order request."""

    symbol: str = Field(..., min_length=1)
    side: BinanceOrderSide
    order_type: BinanceSpotOrderType
    quantity: str = Field(..., min_length=1)
    client_order_id: str = Field(..., min_length=1, max_length=36)
    price: str | None = None
    time_in_force: BinanceTimeInForce | None = None

    @model_validator(mode="after")
    def validate_shape(self) -> "BinanceOrderRequest":
        if self.order_type == BinanceSpotOrderType.LIMIT:
            if not self.price:
                raise ValueError("LIMIT order requires price")
            if self.time_in_force is None:
                raise ValueError("LIMIT order requires time_in_force")
        elif self.price is not None or self.time_in_force is not None:
            raise ValueError("MARKET order must not provide price or time_in_force")
        return self


class BinanceOrderAck(BaseModel, frozen=True):
    """Minimal Binance Spot new-order acknowledgement."""

    symbol: str = Field(..., min_length=1)
    order_id: int = Field(..., ge=0)
    client_order_id: str = Field(..., min_length=1, max_length=36)
    transact_time_ms: int = Field(..., ge=0)
    status: str = ""
    side: BinanceOrderSide
    order_type: BinanceSpotOrderType
    price: str = "0"
    orig_qty: str = "0"
    executed_qty: str = "0"
    time_in_force: str = ""


class BinanceOpenOrder(BaseModel, frozen=True):
    """Minimal Binance Spot open-order projection."""

    symbol: str = Field(..., min_length=1)
    order_id: int = Field(..., ge=0)
    client_order_id: str = Field(..., min_length=1, max_length=36)
    status: str = ""
    side: BinanceOrderSide
    order_type: BinanceSpotOrderType
    price: str = "0"
    orig_qty: str = "0"
    executed_qty: str = "0"
    time_in_force: str = ""
    update_time_ms: int = Field(default=0, ge=0)


class BinanceApiErrorResponse(BaseModel, frozen=True):
    """Normalized Binance API error payload."""

    model_config = ConfigDict(populate_by_name=True)

    code: int
    message: str = Field(alias="msg", min_length=1)


class BinanceUserDataExecutionReport(BaseModel, frozen=True):
    """Minimal normalized Binance Spot executionReport payload."""

    model_config = ConfigDict(populate_by_name=True)

    event_type: str = Field(alias="e", min_length=1)
    event_time_ms: int = Field(alias="E", ge=0)
    symbol: str = Field(alias="s", min_length=1)
    client_order_id: str = Field(alias="c", min_length=1)
    side: BinanceOrderSide = Field(alias="S")
    order_type: BinanceSpotOrderType = Field(alias="o")
    time_in_force: str = Field(default="", alias="f")
    order_quantity: str = Field(default="0", alias="q", min_length=1)
    order_price: str = Field(default="0", alias="p", min_length=1)
    execution_type: str = Field(alias="x", min_length=1)
    order_status: str = Field(alias="X", min_length=1)
    order_id: int = Field(alias="i", ge=0)
    last_executed_quantity: str = Field(default="0", alias="l", min_length=1)
    cumulative_filled_quantity: str = Field(default="0", alias="z", min_length=1)
    last_executed_price: str = Field(default="0", alias="L", min_length=1)
    commission_amount: str = Field(default="0", alias="n", min_length=1)
    commission_asset: str | None = Field(default=None, alias="N")
    trade_id: int = Field(default=-1, alias="t")
    reject_reason: str = Field(default="", alias="r")


class BinanceOrderErrorKind(StrEnum):
    INSUFFICIENT_BALANCE = "insufficient_balance"
    INVALID_LOT_SIZE = "invalid_lot_size"
    INVALID_PRICE_FILTER = "invalid_price_filter"
    INVALID_MIN_NOTIONAL = "invalid_min_notional"
    DUPLICATE_CLIENT_ORDER_ID = "duplicate_client_order_id"
    ORDER_NOT_FOUND = "order_not_found"
    RATE_LIMITED = "rate_limited"
    TIMESTAMP_OUT_OF_WINDOW = "timestamp_out_of_window"
    UNKNOWN = "unknown"


class BinanceOrderErrorClassification(BaseModel, frozen=True):
    """Bounded classification of a Binance order API error."""

    kind: BinanceOrderErrorKind
    retryable: bool = False
    detail: str = ""


__all__ = [
    "BinanceAccountSnapshot",
    "BinanceAssetBalance",
    "BinanceApiErrorResponse",
    "BinanceCredentials",
    "BinanceExchangeInfo",
    "BinanceOpenOrder",
    "BinanceOrderAck",
    "BinanceOrderErrorClassification",
    "BinanceOrderErrorKind",
    "BinanceOrderRequest",
    "BinanceOrderSide",
    "BinanceUserDataExecutionReport",
    "BinanceRateLimit",
    "BinanceServerTime",
    "BinanceSpotOrderType",
    "BinanceSymbolInfo",
    "BinanceTimeInForce",
    "BinanceTimeSyncResult",
]
