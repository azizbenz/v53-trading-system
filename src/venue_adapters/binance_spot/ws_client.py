"""Bounded websocket depth client with explicit stale/resync state."""

from __future__ import annotations

import asyncio
import time
from typing import Callable, Protocol

from data_backbone.websocket_gateway.heartbeat_monitor import HeartbeatMonitor, HeartbeatStatus
from data_backbone.websocket_gateway.runtime_gateway import (
    AdapterMessage,
    WebSocketGatewayAdapter,
    WebSocketGatewayRuntime,
)
from pydantic import BaseModel, Field
from venue_adapters.binance_spot.orderbook_manager import (
    BinanceDepthDelta,
    BinanceDepthSnapshot,
    BinanceOrderBookManager,
    BinanceOrderBookStatus,
    OrderBookSyncState,
)
from venue_adapters.binance_spot.rest_client import BinanceRestClient


class DepthSnapshotProvider(Protocol):
    def __call__(self, pair: str) -> BinanceDepthSnapshot:
        ...


class BinanceWsClientConfig(BaseModel, frozen=True):
    endpoint: str = Field(default="wss://stream.binance.com:9443/ws", min_length=1)
    stream_type: str = Field(default="depth", min_length=1)
    gap_threshold_s: float = Field(default=5.0, ge=0.0)
    silence_threshold_s: float = Field(default=30.0, ge=0.0)


class BinanceWsClientPollResult(BaseModel, frozen=True):
    status: BinanceOrderBookStatus
    reconnected: bool = False
    reconnect_requires_resync: bool = False
    raw_message_seen: bool = False


def build_rest_depth_snapshot_provider(
    rest_client: BinanceRestClient,
    *,
    snapshot_limit: int,
) -> DepthSnapshotProvider:
    """Build a sync snapshot provider from the async REST client.

    The current websocket wrapper is sync by design; this helper keeps the
    bridge explicit and fails fast if someone tries to use it from a running
    event loop.
    """

    if snapshot_limit <= 0:
        raise ValueError("snapshot_limit must be > 0")

    def _provider(pair: str) -> BinanceDepthSnapshot:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(rest_client.get_depth_snapshot(pair=pair, limit=snapshot_limit))
        raise RuntimeError(
            "build_rest_depth_snapshot_provider cannot be used inside a running event loop; "
            "inject an async-aware snapshot provider instead"
        )

    return _provider


class BinanceDepthWebSocketClient:
    """Uses the existing Build-2 gateway runtime and a bounded order-book manager."""

    def __init__(
        self,
        *,
        pair: str,
        snapshot_provider: DepthSnapshotProvider,
        adapter: WebSocketGatewayAdapter,
        config: BinanceWsClientConfig,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self._pair = pair.upper()
        self._snapshot_provider = snapshot_provider
        self._config = config
        self._clock = clock or time.time
        self._gateway = WebSocketGatewayRuntime(
            adapter,
            heartbeat_monitor=HeartbeatMonitor(
                heartbeat_interval_s=config.silence_threshold_s,
                late_threshold_s=config.silence_threshold_s,
            ),
        )
        self._manager = BinanceOrderBookManager(
            pair=self._pair,
            gap_threshold_s=config.gap_threshold_s,
            silence_threshold_s=config.silence_threshold_s,
        )
        self._gateway.register_endpoint(config.endpoint)

    def start(self, now: float | None = None) -> BinanceOrderBookStatus:
        current_time = self._clock() if now is None else now
        snapshot = self._snapshot_provider(self._pair)
        status = self._manager.apply_snapshot(snapshot)
        self._gateway.subscribe(self._pair, self._config.stream_type, self._config.endpoint)
        self._gateway.connect(self._config.endpoint, current_time)
        return status

    def resync(self, now: float | None = None) -> BinanceOrderBookStatus:
        current_time = self._clock() if now is None else now
        snapshot = self._snapshot_provider(self._pair)
        return self._manager.apply_snapshot(
            snapshot.model_copy(update={"recv_time_s": current_time})
        )

    def poll_once(self, now: float | None = None) -> BinanceWsClientPollResult:
        current_time = self._clock() if now is None else now
        gateway_result = self._gateway.poll_once(self._config.endpoint, current_time)
        if gateway_result.reconnect_event is not None:
            status = self._manager.mark_stale(
                reason="reconnect_resync_required",
                now=current_time,
            )
            return BinanceWsClientPollResult(
                status=status,
                reconnected=True,
                reconnect_requires_resync=True,
                raw_message_seen=gateway_result.raw_message is not None,
            )
        raw_message = gateway_result.raw_message
        if raw_message is not None:
            status = self._handle_raw_message(raw_message)
            return BinanceWsClientPollResult(
                status=status,
                raw_message_seen=True,
            )
        status = self._manager.build_status(now=current_time)
        if gateway_result.heartbeat_state.status == HeartbeatStatus.SILENT:
            status = self._manager.mark_stale(reason="heartbeat_silent", now=current_time)
        return BinanceWsClientPollResult(status=status)

    def _handle_raw_message(self, raw_message: AdapterMessage) -> BinanceOrderBookStatus:
        if raw_message.stream_type != "depth":
            return self._manager.build_status(now=raw_message.recv_time or self._clock())
        payload = raw_message.payload
        delta = BinanceDepthDelta(
            pair=raw_message.pair,
            first_update_id=int(payload.get("first_update_id", payload.get("last_update_id", 0))),
            final_update_id=int(payload.get("final_update_id", payload.get("last_update_id", 0))),
            bids=tuple(tuple(level) for level in payload.get("bids", [])),
            asks=tuple(tuple(level) for level in payload.get("asks", [])),
            recv_time_s=raw_message.recv_time if raw_message.recv_time is not None else self._clock(),
        )
        return self._manager.apply_delta(delta)


class MultiSymbolPollResult(BaseModel, frozen=True):
    """Aggregate poll result across all managed pairs."""

    statuses: dict[str, BinanceOrderBookStatus]
    raw_messages_seen: int = 0
    reconnected_pairs: tuple[str, ...] = ()


class MultiSymbolDepthWsClient:
    """Manages a Binance combined-stream depth subscription for N pairs.

    Uses the Binance combined stream endpoint:
      wss://stream.binance.com/stream?streams=btcusdt@depth@100ms/ethusdt@depth@100ms/...

    One ``BinanceOrderBookManager`` is maintained per pair.  Incoming
    messages are routed by the ``stream`` field Binance embeds in each
    combined-stream payload (e.g. ``"btcusdt@depth@100ms"``).

    Lifecycle::
        client = MultiSymbolDepthWsClient(pairs=["BTCUSDT", "ETHUSDT"], ...)
        client.start()
        while running:
            result = client.poll_once()
        client.stop()
    """

    _COMBINED_STREAM_BASE = "wss://stream.binance.com/stream"

    def __init__(
        self,
        *,
        pairs: list[str],
        snapshot_provider: DepthSnapshotProvider,
        adapter: WebSocketGatewayAdapter,
        config: BinanceWsClientConfig | None = None,
        clock: Callable[[], float] | None = None,
    ) -> None:
        if not pairs:
            raise ValueError("pairs must be non-empty")
        self._pairs = [p.upper() for p in pairs]
        self._snapshot_provider = snapshot_provider
        self._config = config or BinanceWsClientConfig()
        self._clock = clock or time.time
        self._managers: dict[str, BinanceOrderBookManager] = {
            pair: BinanceOrderBookManager(
                pair=pair,
                gap_threshold_s=self._config.gap_threshold_s,
                silence_threshold_s=self._config.silence_threshold_s,
            )
            for pair in self._pairs
        }
        # Build combined-stream URL:
        #   wss://stream.binance.com/stream?streams=btcusdt@depth@100ms/ethusdt@...
        stream_names = "/".join(
            f"{pair.lower()}@{self._config.stream_type}@100ms" for pair in self._pairs
        )
        self._endpoint = f"{self._COMBINED_STREAM_BASE}?streams={stream_names}"
        self._gateway = WebSocketGatewayRuntime(
            adapter,
            heartbeat_monitor=HeartbeatMonitor(
                heartbeat_interval_s=self._config.silence_threshold_s,
                late_threshold_s=self._config.silence_threshold_s,
            ),
        )
        self._gateway.register_endpoint(self._endpoint)

    def start(self, now: float | None = None) -> dict[str, BinanceOrderBookStatus]:
        """Fetch initial snapshots for all pairs and connect the combined stream."""
        current_time = self._clock() if now is None else now
        statuses: dict[str, BinanceOrderBookStatus] = {}
        for pair in self._pairs:
            snapshot = self._snapshot_provider(pair)
            statuses[pair] = self._managers[pair].apply_snapshot(snapshot)
            # In combined streams we subscribe via the query-string URL;
            # the gateway subscribe call maps pair→stream_type for message routing.
            self._gateway.subscribe(pair, self._config.stream_type, self._endpoint)
        self._gateway.connect(self._endpoint, current_time)
        return statuses

    def resync(self, pair: str, now: float | None = None) -> BinanceOrderBookStatus:
        """Re-fetch snapshot for a single pair (e.g. after a reconnect event)."""
        current_time = self._clock() if now is None else now
        pair = pair.upper()
        manager = self._managers.get(pair)
        if manager is None:
            raise KeyError(f"pair {pair!r} not in this MultiSymbolDepthWsClient")
        snapshot = self._snapshot_provider(pair)
        return manager.apply_snapshot(
            snapshot.model_copy(update={"recv_time_s": current_time})
        )

    def poll_once(self, now: float | None = None) -> MultiSymbolPollResult:
        """Poll the gateway once and dispatch to the matching pair manager."""
        current_time = self._clock() if now is None else now
        gateway_result = self._gateway.poll_once(self._endpoint, current_time)

        reconnected_pairs: list[str] = []
        raw_messages_seen = 0

        if gateway_result.reconnect_event is not None:
            # Mark ALL managed pairs stale — we lost connection for the whole stream.
            for pair, manager in self._managers.items():
                manager.mark_stale(reason="reconnect_resync_required", now=current_time)
                reconnected_pairs.append(pair)
            statuses = {p: m.build_status(now=current_time) for p, m in self._managers.items()}
            return MultiSymbolPollResult(
                statuses=statuses,
                raw_messages_seen=0,
                reconnected_pairs=tuple(reconnected_pairs),
            )

        raw_message = gateway_result.raw_message
        if raw_message is not None:
            raw_messages_seen = 1
            # Combined stream wraps each event in {"stream": "btcusdt@depth", "data": {...}}
            # The gateway may already unwrap; fall back to raw_message.pair for routing.
            target_pair = raw_message.pair.upper() if raw_message.pair else None
            if target_pair and target_pair in self._managers:
                payload = raw_message.payload
                delta = BinanceDepthDelta(
                    pair=target_pair,
                    first_update_id=int(
                        payload.get("first_update_id", payload.get("last_update_id", 0))
                    ),
                    final_update_id=int(
                        payload.get("final_update_id", payload.get("last_update_id", 0))
                    ),
                    bids=tuple(tuple(level) for level in payload.get("bids", [])),
                    asks=tuple(tuple(level) for level in payload.get("asks", [])),
                    recv_time_s=(
                        raw_message.recv_time if raw_message.recv_time is not None
                        else current_time
                    ),
                )
                self._managers[target_pair].apply_delta(delta)

        # Check heartbeat silence on the combined stream
        if gateway_result.heartbeat_state.status == HeartbeatStatus.SILENT:
            for pair, manager in self._managers.items():
                manager.mark_stale(reason="heartbeat_silent", now=current_time)

        statuses = {p: m.build_status(now=current_time) for p, m in self._managers.items()}
        return MultiSymbolPollResult(
            statuses=statuses,
            raw_messages_seen=raw_messages_seen,
            reconnected_pairs=tuple(reconnected_pairs),
        )

    def get_status(self, pair: str, now: float | None = None) -> BinanceOrderBookStatus:
        """Return the current order-book status for a single pair."""
        current_time = self._clock() if now is None else now
        manager = self._managers.get(pair.upper())
        if manager is None:
            raise KeyError(f"pair {pair!r} not managed by this client")
        return manager.build_status(now=current_time)

    def get_all_statuses(self, now: float | None = None) -> dict[str, BinanceOrderBookStatus]:
        current_time = self._clock() if now is None else now
        return {p: m.build_status(now=current_time) for p, m in self._managers.items()}

    @property
    def pairs(self) -> list[str]:
        return list(self._pairs)

    @property
    def endpoint(self) -> str:
        return self._endpoint


__all__ = [
    "BinanceDepthWebSocketClient",
    "BinanceWsClientConfig",
    "BinanceWsClientPollResult",
    "DepthSnapshotProvider",
    "MultiSymbolDepthWsClient",
    "MultiSymbolPollResult",
    "build_rest_depth_snapshot_provider",
]
