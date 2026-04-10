import json

from execution_backbone import VenueOrderEvent, VenueOrderEventType
from execution_backbone.order_decider.intent_builder import VenueConstraintSnapshot
from interface_contracts.binance_contracts import BinanceCredentials
from venue_adapters.binance_spot.bootstrap import build_binance_spot_execution_adapter
from venue_adapters.binance_spot.time_sync import BinanceAdapterConfig


class _FakeSocket:
    def __init__(self, messages):
        self._messages = list(messages)
        self.sent: list[str] = []

    def settimeout(self, timeout: float) -> None:
        return None

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
        return None


class FakeVenueConstraintProvider:
    def fetch_venue_constraints(self, pair: str) -> VenueConstraintSnapshot | None:
        if pair.upper() == "BTCUSDT":
            return VenueConstraintSnapshot(tick_size="0.1", step_size="0.001", min_notional="10")
        return None


def test_build_binance_spot_execution_adapter_injects_user_data_source():
    fake_socket = _FakeSocket(
        [
            json.dumps(
                {
                    "id": "v53-user-data-subscribe",
                    "status": 200,
                    "result": {"subscriptionId": 7},
                }
            ),
            json.dumps(
                {
                    "subscriptionId": 7,
                    "event": {
                        "e": "executionReport",
                        "E": 1_710_000_005_000,
                        "s": "BTCUSDT",
                        "c": "v53_engine_a_intent-1",
                        "S": "BUY",
                        "o": "LIMIT",
                        "f": "GTC",
                        "q": "0.25000000",
                        "p": "50000.10000000",
                        "x": "NEW",
                        "X": "NEW",
                        "i": 123460,
                        "l": "0.00000000",
                        "z": "0.00000000",
                        "L": "0.00000000",
                        "n": "0",
                        "N": None,
                        "t": -1,
                        "r": "NONE",
                    },
                }
            ),
        ]
    )
    adapter = build_binance_spot_execution_adapter(
        credentials=BinanceCredentials(
            api_key="test-api-key",
            secret_key="test-api-secret",
            label="testnet",
        ),
        config=BinanceAdapterConfig(rest_base_url="https://testnet.binance.vision"),
        venue_constraint_provider=FakeVenueConstraintProvider(),
        user_data_stream_enabled=True,
        user_data_socket_factory=lambda endpoint, connect_timeout_s, recv_timeout_s: fake_socket,
        clock_ms=lambda: 1_710_000_000_000,
    )

    assert adapter.fetch_venue_constraints("BTCUSDT") == VenueConstraintSnapshot(
        tick_size="0.1",
        step_size="0.001",
        min_notional="10",
    )
    assert adapter.poll_order_events() == (
        VenueOrderEvent(
            order_id="123460",
            event_type=VenueOrderEventType.ACK,
            timestamp=1_710_000_005.0,
        ),
    )
    assert len(fake_socket.sent) == 1
