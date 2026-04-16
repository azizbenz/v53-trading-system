"""Translate internal execution intents into bounded Binance Spot order requests."""

from __future__ import annotations

import uuid

from execution_backbone.order_decider.intent_builder import ExecutionIntent, OrderType
from interface_contracts import decimal_to_canonical_str, execution_decimal
from interface_contracts.binance_contracts import (
    BinanceOrderRequest,
    BinanceOrderSide,
    BinanceSpotOrderType,
    BinanceTimeInForce,
)

# Fixed namespace for V5.3 client order ids — never change after first live order.
_V53_ORDER_NAMESPACE = uuid.UUID("b9e2a8c1-4d3f-5a6b-8c9d-0e1f2a3b4c5d")


def build_binance_client_order_id(*, engine_id: str, pair_id: str, intent_id: str) -> str:
    """Build a deterministic UUIDv5 Binance-compatible client order id.

    The name encodes (engine_id, pair_id, intent_id) so that:
    - Distinct (engine, pair, intent) triplets never collide.
    - For multi-pair trading the pair is embedded for traceability:
      you can reverse-engineer which symbol an order belongs to from logs.
    - UUIDv5 produces exactly 36 chars (fits Binance 36-char limit).
    - Only hex digits and dashes (valid Binance clientOrderId characters).

    Note: pair_id is expected to be the canonical Binance symbol string,
    e.g. "BTCUSDT".  It is uppercased internally.
    """
    name = f"{engine_id}:{pair_id.upper()}:{intent_id}"
    return str(uuid.uuid5(_V53_ORDER_NAMESPACE, name))


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
                pair_id=intent.pair,
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
            pair_id=intent.pair,
            intent_id=intent.intent_id,
        ),
    )


__all__ = [
    "build_binance_client_order_id",
    "translate_execution_intent_to_binance_order",
]
