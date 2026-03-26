"""
4.5.1 — Connection Manager: open/close sockets, session management, reconnection.

Invariant: each connection has an explicit status at all times.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class ConnectionState(StrEnum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"


class ConnectionStatus(BaseModel, frozen=True):
    """Snapshot of a single WS connection's state."""

    endpoint: str
    state: ConnectionState
    connect_count: int = 0
    last_connect_time: float | None = None
    last_disconnect_time: float | None = None
    error_message: str = ""


class ConnectionManager:
    """Manages WS connection lifecycle.

    Not async — provides the state machine and bookkeeping.
    Actual socket I/O is delegated to an adapter (injected at runtime).
    """

    def __init__(self) -> None:
        self._connections: dict[str, ConnectionStatus] = {}

    def register_endpoint(self, endpoint: str) -> None:
        if endpoint in self._connections:
            return
        self._connections[endpoint] = ConnectionStatus(
            endpoint=endpoint,
            state=ConnectionState.DISCONNECTED,
        )

    def mark_connecting(self, endpoint: str) -> ConnectionStatus:
        old = self._get(endpoint)
        new = ConnectionStatus(
            endpoint=endpoint,
            state=ConnectionState.CONNECTING,
            connect_count=old.connect_count,
            last_connect_time=old.last_connect_time,
            last_disconnect_time=old.last_disconnect_time,
        )
        self._connections[endpoint] = new
        return new

    def mark_connected(self, endpoint: str, connect_time: float) -> ConnectionStatus:
        old = self._get(endpoint)
        new = ConnectionStatus(
            endpoint=endpoint,
            state=ConnectionState.CONNECTED,
            connect_count=old.connect_count + 1,
            last_connect_time=connect_time,
            last_disconnect_time=old.last_disconnect_time,
        )
        self._connections[endpoint] = new
        return new

    def mark_disconnected(self, endpoint: str, disconnect_time: float, error: str = "") -> ConnectionStatus:
        old = self._get(endpoint)
        new = ConnectionStatus(
            endpoint=endpoint,
            state=ConnectionState.DISCONNECTED,
            connect_count=old.connect_count,
            last_connect_time=old.last_connect_time,
            last_disconnect_time=disconnect_time,
            error_message=error,
        )
        self._connections[endpoint] = new
        return new

    def mark_reconnecting(self, endpoint: str) -> ConnectionStatus:
        old = self._get(endpoint)
        new = ConnectionStatus(
            endpoint=endpoint,
            state=ConnectionState.RECONNECTING,
            connect_count=old.connect_count,
            last_connect_time=old.last_connect_time,
            last_disconnect_time=old.last_disconnect_time,
        )
        self._connections[endpoint] = new
        return new

    def mark_failed(self, endpoint: str, error: str) -> ConnectionStatus:
        old = self._get(endpoint)
        new = ConnectionStatus(
            endpoint=endpoint,
            state=ConnectionState.FAILED,
            connect_count=old.connect_count,
            last_connect_time=old.last_connect_time,
            last_disconnect_time=old.last_disconnect_time,
            error_message=error,
        )
        self._connections[endpoint] = new
        return new

    def get_status(self, endpoint: str) -> ConnectionStatus | None:
        return self._connections.get(endpoint)

    def get_all_statuses(self) -> dict[str, ConnectionStatus]:
        return dict(self._connections)

    def _get(self, endpoint: str) -> ConnectionStatus:
        if endpoint not in self._connections:
            raise KeyError(f"Endpoint '{endpoint}' not registered")
        return self._connections[endpoint]
