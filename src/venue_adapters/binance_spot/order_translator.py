"""Translate internal execution intents into bounded Binance Spot order requests."""

from __future__ import annotations

import hashlib
import re

from execution_backbone.order_decider.intent_builder import ExecutionIntent, OrderType
from interface_contracts import decimal_to_canonical_str, execution_decimal
from interface_contracts.binance_contracts import (
    BinanceOrderRequest,
    BinanceOrderSide,
    BinanceSpotOrderType,
    BinanceTimeInForce,
)


_CLIENT_ORDER_ID_MAX_LEN = 36
_CLIENT_ORDER_ID_HASH_LEN = 8
_CLIENT_ORDER_ID_SEPARATOR_LEN = 1


def build_binance_client_order_id(*, engine_id: str, intent_id: str) -> str:
    """Build a deterministic Binance-compatible client order id."""

    raw = f"v53_{engine_id}_{intent_id}"
    normalized = re.sub(r"[^A-Za-z0-9_-]+", "-", raw).strip("-_")
    if not normalized:
        normalized = "v53_order"
    if len(normalized) <= _CLIENT_ORDER_ID_MAX_LEN:
        return normalized
    digest = hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:_CLIENT_ORDER_ID_HASH_LEN]
    prefix_len = (
        _CLIENT_ORDER_ID_MAX_LEN
        - _CLIENT_ORDER_ID_HASH_LEN
        - _CLIENT_ORDER_ID_SEPARATOR_LEN
    )
    prefix = normalized[:prefix_len].rstrip("-_")
    if not prefix:
        prefix = "v53"
    return f"{prefix}_{digest}"


def translate_execution_intent_to_binance_order(
    intent: ExecutionIntent,
) -> BinanceOrderRequest:
    """Translate a governed execution intent into a Binance Spot order request."""

    if intent.order_type == OrderType.NO_TRADE:
        raise ValueError("cannot translate NO_TRADE intent into Binance order request")

    quantity = intent.quantity_exact or decimal_to_canonical_str(
        execution_decimal(intent.quantity, name="quantity")
    )
    side = BinanceOrderSide(intent.side.upper())

    if intent.order_type == OrderType.MARKET:
        return BinanceOrderRequest(
            symbol=intent.pair.upper(),
            side=side,
            order_type=BinanceSpotOrderType.MARKET,
            quantity=quantity,
            client_order_id=build_binance_client_order_id(
                engine_id=intent.engine_id,
                intent_id=intent.intent_id,
            ),
        )

    if intent.price_limit_exact:
        price = intent.price_limit_exact
    elif intent.price_limit is not None:
        price = decimal_to_canonical_str(
            execution_decimal(intent.price_limit, name="price_limit")
        )
    else:
        raise ValueError("LIMIT execution intent requires a price_limit")

    return BinanceOrderRequest(
        symbol=intent.pair.upper(),
        side=side,
        order_type=BinanceSpotOrderType.LIMIT,
        quantity=quantity,
        price=price,
        time_in_force=BinanceTimeInForce.GTC,
        client_order_id=build_binance_client_order_id(
            engine_id=intent.engine_id,
            intent_id=intent.intent_id,
        ),
    )


__all__ = [
    "build_binance_client_order_id",
    "translate_execution_intent_to_binance_order",
]
