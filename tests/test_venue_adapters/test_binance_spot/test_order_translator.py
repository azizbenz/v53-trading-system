from execution_backbone.order_decider.intent_builder import ExecutionIntent, OrderType
from interface_contracts.binance_contracts import (
    BinanceOrderSide,
    BinanceSpotOrderType,
    BinanceTimeInForce,
)
from venue_adapters.binance_spot.order_translator import (
    build_binance_client_order_id,
    translate_execution_intent_to_binance_order,
)


def _intent(
    *,
    intent_id: str = "intent-1",
    order_type: OrderType = OrderType.MARKET,
    quantity_exact: str = "0.25",
    price_limit_exact: str | None = None,
    price_limit: float | None = None,
) -> ExecutionIntent:
    return ExecutionIntent(
        intent_id=intent_id,
        pair="BTCUSDT",
        engine_id="engine_a",
        side="buy",
        order_type=order_type,
        quantity=0.25,
        quantity_exact=quantity_exact,
        price_limit=price_limit,
        price_limit_exact=price_limit_exact,
        expected_cost=0.001,
        expected_gain=0.01,
        score=0.8,
        justification="test",
        timeout_s=5.0,
        profile="COMPLETE",
    )


def test_translate_market_intent_to_binance_order():
    request = translate_execution_intent_to_binance_order(_intent())

    assert request.symbol == "BTCUSDT"
    assert request.side == BinanceOrderSide.BUY
    assert request.order_type == BinanceSpotOrderType.MARKET
    assert request.quantity == "0.25"
    assert request.price is None
    assert request.time_in_force is None
    assert request.client_order_id == build_binance_client_order_id(
        engine_id="engine_a", pair_id="BTCUSDT", intent_id="intent-1"
    )


def test_translate_limit_intent_to_binance_order():
    request = translate_execution_intent_to_binance_order(
        _intent(
            order_type=OrderType.LIMIT,
            quantity_exact="0.123",
            price_limit_exact="50000.1",
        )
    )

    assert request.order_type == BinanceSpotOrderType.LIMIT
    assert request.quantity == "0.123"
    assert request.price == "50000.1"
    assert request.time_in_force == BinanceTimeInForce.GTC


def test_translate_limit_requires_price():
    try:
        translate_execution_intent_to_binance_order(
            _intent(order_type=OrderType.LIMIT, price_limit_exact=None, price_limit=None)
        )
    except ValueError as exc:
        assert "price_limit" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_translate_no_trade_intent_is_rejected():
    try:
        translate_execution_intent_to_binance_order(_intent(order_type=OrderType.NO_TRADE))
    except ValueError as exc:
        assert "NO_TRADE" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_build_binance_client_order_id_stays_deterministic_and_bounded():
    intent_id = "x" * 80
    first = build_binance_client_order_id(engine_id="engine_b", pair_id="ETHUSDT", intent_id=intent_id)
    second = build_binance_client_order_id(engine_id="engine_b", pair_id="ETHUSDT", intent_id=intent_id)

    assert first == second
    assert len(first) == 36
    assert "-" in first  # UUIDv5 format


def test_build_binance_client_order_id_differs_by_pair() -> None:
    """Same engine + intent but different pair must produce different order ids."""
    base = dict(engine_id="engine_a", intent_id="intent-99")
    btc_id = build_binance_client_order_id(**base, pair_id="BTCUSDT")
    eth_id = build_binance_client_order_id(**base, pair_id="ETHUSDT")
    sol_id = build_binance_client_order_id(**base, pair_id="SOLUSDT")
    assert btc_id != eth_id
    assert eth_id != sol_id
    assert btc_id != sol_id


def test_build_binance_client_order_id_pair_case_insensitive() -> None:
    """Lowercase and uppercase pair produce the same id."""
    lower = build_binance_client_order_id(engine_id="engine_a", pair_id="btcusdt", intent_id="i1")
    upper = build_binance_client_order_id(engine_id="engine_a", pair_id="BTCUSDT", intent_id="i1")
    assert lower == upper
