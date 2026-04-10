from execution_backbone import VenueOrderEvent, VenueOrderEventType
from venue_adapters.binance_spot.user_data_events import (
    BufferedBinanceUserDataEventSource,
    parse_binance_user_data_payload,
    parse_binance_user_data_payloads,
)


def test_parse_binance_user_data_payload_maps_terminal_execution_reports():
    cancelled_payload = {
        "e": "executionReport",
        "E": 1_710_000_002_000,
        "s": "BTCUSDT",
        "c": "v53_engine_a_intent-1",
        "S": "BUY",
        "o": "LIMIT",
        "f": "GTC",
        "q": "0.25000000",
        "p": "50000.10000000",
        "x": "CANCELED",
        "X": "CANCELED",
        "i": 123456,
        "l": "0.00000000",
        "z": "0.05000000",
        "L": "0.00000000",
        "n": "0",
        "N": None,
        "t": -1,
        "r": "NONE",
    }
    rejected_payload = {
        "e": "executionReport",
        "E": 1_710_000_003_000,
        "s": "BTCUSDT",
        "c": "v53_engine_a_intent-1",
        "S": "BUY",
        "o": "LIMIT",
        "f": "GTC",
        "q": "0.25000000",
        "p": "50000.10000000",
        "x": "REJECTED",
        "X": "REJECTED",
        "i": 123457,
        "l": "0.00000000",
        "z": "0.00000000",
        "L": "0.00000000",
        "n": "0",
        "N": None,
        "t": -1,
        "r": "STOP_PRICE_WOULD_TRIGGER_IMMEDIATELY",
    }

    assert parse_binance_user_data_payload(cancelled_payload) == (
        VenueOrderEvent(
            order_id="123456",
            event_type=VenueOrderEventType.CANCELLED,
            timestamp=1_710_000_002.0,
            reason="canceled",
        ),
    )
    assert parse_binance_user_data_payload(rejected_payload) == (
        VenueOrderEvent(
            order_id="123457",
            event_type=VenueOrderEventType.REJECTED,
            timestamp=1_710_000_003.0,
            reason="STOP_PRICE_WOULD_TRIGGER_IMMEDIATELY",
        ),
    )


def test_parse_binance_user_data_payloads_ignores_non_execution_events():
    payloads = (
        {"e": "outboundAccountPosition", "E": 1_710_000_002_500},
        {
            "e": "executionReport",
            "E": 1_710_000_003_500,
            "s": "BTCUSDT",
            "c": "v53_engine_a_intent-1",
            "S": "BUY",
            "o": "LIMIT",
            "f": "GTC",
            "q": "0.25000000",
            "p": "50000.10000000",
            "x": "EXPIRED",
            "X": "EXPIRED",
            "i": 123458,
            "l": "0.00000000",
            "z": "0.00000000",
            "L": "0.00000000",
            "n": "0",
            "N": None,
            "t": -1,
            "r": "",
        },
    )

    assert parse_binance_user_data_payloads(payloads) == (
        VenueOrderEvent(
            order_id="123458",
            event_type=VenueOrderEventType.EXPIRED,
            timestamp=1_710_000_003.5,
            reason="expired",
        ),
    )


def test_parse_binance_user_data_payload_supports_nested_event_wrapper():
    payload = {
        "subscriptionId": 7,
        "event": {
            "e": "executionReport",
            "E": 1_710_000_004_000,
            "s": "BTCUSDT",
            "c": "v53_engine_a_intent-1",
            "S": "BUY",
            "o": "LIMIT",
            "f": "GTC",
            "q": "0.25000000",
            "p": "50000.10000000",
            "x": "NEW",
            "X": "NEW",
            "i": 123459,
            "l": "0.00000000",
            "z": "0.00000000",
            "L": "0.00000000",
            "n": "0",
            "N": None,
            "t": -1,
            "r": "NONE",
        },
    }

    assert parse_binance_user_data_payload(payload) == (
        VenueOrderEvent(
            order_id="123459",
            event_type=VenueOrderEventType.ACK,
            timestamp=1_710_000_004.0,
        ),
    )


def test_buffered_user_data_event_source_drains_once():
    source = BufferedBinanceUserDataEventSource(({"e": "executionReport", "i": 1},))

    assert source.poll_events() == ({"e": "executionReport", "i": 1},)
    assert source.poll_events() == ()
