"""Bounded Binance Spot order API error classification."""

from __future__ import annotations

from collections.abc import Mapping

from interface_contracts.binance_contracts import (
    BinanceApiErrorResponse,
    BinanceOrderErrorClassification,
    BinanceOrderErrorKind,
)


def classify_binance_order_error(
    payload: BinanceApiErrorResponse | Mapping[str, object],
) -> BinanceOrderErrorClassification:
    """Classify a normalized Binance error payload into a bounded kind."""

    error = (
        payload
        if isinstance(payload, BinanceApiErrorResponse)
        else BinanceApiErrorResponse.model_validate(payload)
    )
    message = error.message.upper()

    if error.code == -1003:
        return BinanceOrderErrorClassification(
            kind=BinanceOrderErrorKind.RATE_LIMITED,
            retryable=True,
            detail=error.message,
        )
    if error.code == -1021:
        return BinanceOrderErrorClassification(
            kind=BinanceOrderErrorKind.TIMESTAMP_OUT_OF_WINDOW,
            retryable=True,
            detail=error.message,
        )
    if error.code == -2011:
        return BinanceOrderErrorClassification(
            kind=BinanceOrderErrorKind.ORDER_NOT_FOUND,
            detail=error.message,
        )
    if "INSUFFICIENT BALANCE" in message:
        return BinanceOrderErrorClassification(
            kind=BinanceOrderErrorKind.INSUFFICIENT_BALANCE,
            detail=error.message,
        )
    if "LOT_SIZE" in message:
        return BinanceOrderErrorClassification(
            kind=BinanceOrderErrorKind.INVALID_LOT_SIZE,
            detail=error.message,
        )
    if "PRICE_FILTER" in message:
        return BinanceOrderErrorClassification(
            kind=BinanceOrderErrorKind.INVALID_PRICE_FILTER,
            detail=error.message,
        )
    if "MIN_NOTIONAL" in message or "NOTIONAL" in message:
        return BinanceOrderErrorClassification(
            kind=BinanceOrderErrorKind.INVALID_MIN_NOTIONAL,
            detail=error.message,
        )
    if "DUPLICATE ORDER SENT" in message:
        return BinanceOrderErrorClassification(
            kind=BinanceOrderErrorKind.DUPLICATE_CLIENT_ORDER_ID,
            detail=error.message,
        )
    return BinanceOrderErrorClassification(
        kind=BinanceOrderErrorKind.UNKNOWN,
        detail=error.message,
    )


__all__ = ["classify_binance_order_error"]
