"""Load governed injected WebSocket frame streams from JSON or JSONL."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field


class InjectedWebSocketFrame(BaseModel, frozen=True):
    """Single injected WebSocket frame loaded from a governed file source."""

    endpoint: str = Field(default="wss://shadow.injected", min_length=1)
    pair: str = Field(..., min_length=1)
    stream_type: str = Field(..., min_length=1)
    payload: dict[str, object] = Field(default_factory=dict)
    recv_time: float = Field(..., gt=0.0)
    source: str = Field(default="recorded_websocket", min_length=1)
    sequence: int | None = None
    route_hint: dict[str, object] = Field(default_factory=dict)


def _load_json_frames(stream_path: Path) -> tuple[InjectedWebSocketFrame, ...]:
    payload = json.loads(stream_path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, list):
        raise ValueError(f"Injected websocket JSON must contain a list: {stream_path}")
    return tuple(
        InjectedWebSocketFrame.model_validate(item)
        for item in payload
        if isinstance(item, dict)
    )


def _load_jsonl_frames(stream_path: Path) -> tuple[InjectedWebSocketFrame, ...]:
    frames: list[InjectedWebSocketFrame] = []
    for line in stream_path.read_text(encoding="utf-8-sig").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        payload = json.loads(stripped)
        if not isinstance(payload, dict):
            raise ValueError(
                f"Injected websocket JSONL rows must be objects: {stream_path}"
            )
        frames.append(InjectedWebSocketFrame.model_validate(payload))
    return tuple(frames)


def load_injected_websocket_frames(stream_path: Path) -> tuple[InjectedWebSocketFrame, ...]:
    """Load injected websocket frames from JSON or JSONL."""

    resolved = stream_path.resolve()
    suffix = resolved.suffix.lower()
    if suffix == ".json":
        return _load_json_frames(resolved)
    if suffix == ".jsonl":
        return _load_jsonl_frames(resolved)
    raise ValueError("Injected websocket streams must use .json or .jsonl")


__all__ = [
    "InjectedWebSocketFrame",
    "load_injected_websocket_frames",
]
