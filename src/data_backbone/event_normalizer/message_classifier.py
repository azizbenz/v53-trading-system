"""
6.5.3 — Message Classifier: identify message type from raw payload.

Invariant: classification is deterministic and explicit. Unknown types are flagged.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class MessageClass(StrEnum):
    TRADE = "trade"
    DEPTH = "depth"
    KLINE = "kline"
    HEARTBEAT = "heartbeat"
    SNAPSHOT = "snapshot"
    UNKNOWN = "unknown"


class ClassificationResult(BaseModel, frozen=True):
    """Result of message classification."""

    message_class: MessageClass
    confidence: float = 1.0  # 1.0 = certain, <1.0 = heuristic
    reason: str = ""


def classify_message(
    payload: dict,
    stream_type_hint: str | None = None,
) -> ClassificationResult:
    """Classify a raw message into a known type.

    Uses stream_type_hint if provided (from subscription metadata).
    Falls back to payload inspection heuristics.
    """
    # Priority 1: explicit stream type hint from subscription
    if stream_type_hint:
        hint_lower = stream_type_hint.lower()
        known = {
            "trade": MessageClass.TRADE,
            "depth": MessageClass.DEPTH,
            "kline": MessageClass.KLINE,
            "heartbeat": MessageClass.HEARTBEAT,
            "snapshot": MessageClass.SNAPSHOT,
        }
        if hint_lower in known:
            return ClassificationResult(
                message_class=known[hint_lower],
                confidence=1.0,
                reason=f"stream_type_hint={stream_type_hint}",
            )

    # Priority 2: payload-based heuristics
    if "price" in payload and ("qty" in payload or "quantity" in payload):
        return ClassificationResult(
            message_class=MessageClass.TRADE,
            confidence=0.9,
            reason="payload contains price+qty fields",
        )

    if "bids" in payload and "asks" in payload:
        return ClassificationResult(
            message_class=MessageClass.DEPTH,
            confidence=0.9,
            reason="payload contains bids+asks fields",
        )

    if "open" in payload and "close" in payload and "high" in payload:
        return ClassificationResult(
            message_class=MessageClass.KLINE,
            confidence=0.9,
            reason="payload contains OHLC fields",
        )

    if payload.get("type") == "heartbeat" or payload.get("event") == "heartbeat":
        return ClassificationResult(
            message_class=MessageClass.HEARTBEAT,
            confidence=0.9,
            reason="payload type/event=heartbeat",
        )

    return ClassificationResult(
        message_class=MessageClass.UNKNOWN,
        confidence=0.0,
        reason="no matching classification rule",
    )
