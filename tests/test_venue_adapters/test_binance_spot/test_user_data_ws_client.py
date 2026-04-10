import json

import pytest

from interface_contracts.binance_contracts import BinanceCredentials
from venue_adapters.binance_spot.user_data_ws_client import (
    BinanceUserDataWebSocketConfig,
    BinanceUserDataWebSocketEventSource,
    build_user_data_subscribe_request,
)


class _FakeSocket:
    def __init__(self, messages):
        self._messages = list(messages)
        self.sent: list[str] = []
        self.closed = False
        self.timeout = None

    def settimeout(self, timeout: float) -> None:
        self.timeout = timeout

    def send(self, payload: str) -> None:
        self.sent.append(payload)

    def recv(self):
        if not self._messages:
            raise TimeoutError("no more messages")
        next_message = self._messages.pop(0)
        if isinstance(next_message, Exception):
            raise next_message
        return next_message

    def close(self) -> None:
        self.closed = True


def _credentials() -> BinanceCredentials:
    return BinanceCredentials(
        api_key="test-api-key",
        secret_key="test-api-secret",
        label="testnet",
    )


def test_build_user_data_subscribe_request_signs_payload():
    request = build_user_data_subscribe_request(
        _credentials(),
        recv_window_ms=5000,
        timestamp_ms=1_710_000_000_000,
        request_id="req-1",
    )

    assert request["id"] == "req-1"
    assert request["method"] == "userDataStream.subscribe.signature"
    params = request["params"]
    assert params["apiKey"] == "test-api-key"
    assert params["recvWindow"] == 5000
    assert params["timestamp"] == 1_710_000_000_000
    assert "signature" in params
    assert len(str(params["signature"])) == 64


def test_user_data_ws_source_connects_and_polls_execution_payloads():
    socket = _FakeSocket(
        [
            json.dumps(
                {
                    "id": "req-1",
                    "status": 200,
                    "result": {"subscriptionId": 7},
                }
            ),
            json.dumps(
                {
                    "subscriptionId": 7,
                    "event": {
                        "e": "executionReport",
                        "E": 1_710_000_004_500,
                        "s": "BTCUSDT",
                    },
                }
            ),
        ]
    )
    source = BinanceUserDataWebSocketEventSource(
        credentials=_credentials(),
        config=BinanceUserDataWebSocketConfig(max_messages_per_poll=4),
        socket_factory=lambda endpoint, connect_timeout_s, recv_timeout_s: socket,
        clock_ms=lambda: 1_710_000_000_000,
        request_id="req-1",
    )

    source.connect()
    payloads = source.poll_events()

    assert source.authenticated is True
    assert source.subscription_id == 7
    assert payloads == (
        {
            "subscriptionId": 7,
            "event": {
                "e": "executionReport",
                "E": 1_710_000_004_500,
                "s": "BTCUSDT",
            },
        },
    )
    assert len(socket.sent) == 1
    sent_request = json.loads(socket.sent[0])
    assert sent_request["id"] == "req-1"
    assert sent_request["params"]["apiKey"] == "test-api-key"
    assert "signature" in sent_request["params"]


def test_user_data_ws_source_raises_on_failed_subscription():
    socket = _FakeSocket(
        [
            json.dumps(
                {
                    "id": "req-1",
                    "status": 400,
                    "error": {"msg": "signature invalid"},
                }
            ),
        ]
    )
    source = BinanceUserDataWebSocketEventSource(
        credentials=_credentials(),
        config=BinanceUserDataWebSocketConfig(max_messages_per_poll=2),
        socket_factory=lambda endpoint, connect_timeout_s, recv_timeout_s: socket,
        clock_ms=lambda: 1_710_000_000_000,
        request_id="req-1",
    )

    source.connect()
    with pytest.raises(RuntimeError, match="signature invalid"):
        source.poll_events()
