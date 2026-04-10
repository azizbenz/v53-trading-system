from interface_contracts.binance_contracts import BinanceOrderErrorKind
from venue_adapters.binance_spot.error_classifier import classify_binance_order_error


def test_classify_insufficient_balance_error():
    classification = classify_binance_order_error(
        {"code": -2010, "msg": "Account has insufficient balance for requested action."}
    )

    assert classification.kind == BinanceOrderErrorKind.INSUFFICIENT_BALANCE
    assert classification.retryable is False


def test_classify_invalid_lot_size_error():
    classification = classify_binance_order_error(
        {"code": -1013, "msg": "Filter failure: LOT_SIZE"}
    )

    assert classification.kind == BinanceOrderErrorKind.INVALID_LOT_SIZE


def test_classify_duplicate_client_order_id_error():
    classification = classify_binance_order_error(
        {"code": -2010, "msg": "Duplicate order sent."}
    )

    assert classification.kind == BinanceOrderErrorKind.DUPLICATE_CLIENT_ORDER_ID


def test_classify_timestamp_error_as_retryable():
    classification = classify_binance_order_error(
        {"code": -1021, "msg": "Timestamp for this request is outside of the recvWindow."}
    )

    assert classification.kind == BinanceOrderErrorKind.TIMESTAMP_OUT_OF_WINDOW
    assert classification.retryable is True
