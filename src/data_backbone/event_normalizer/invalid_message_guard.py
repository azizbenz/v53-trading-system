"""
6.5.4 — Invalid Message Guard: reject non-conforming messages explicitly.

Invariant: every parsing error is visible. No silent tolerance of missing fields.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Mapping

from pydantic import BaseModel, Field


class RejectionReason(StrEnum):
    MISSING_PAIR = "missing_pair"
    MISSING_RECV_TIME = "missing_recv_time"
    MISSING_SOURCE = "missing_source"
    EMPTY_PAYLOAD = "empty_payload"
    INVALID_TYPE = "invalid_type"
    SCHEMA_VIOLATION = "schema_violation"


class RejectedMessage(BaseModel, frozen=True):
    """A message that was rejected during normalization."""

    raw_payload: dict[str, object]
    reason: RejectionReason
    detail: str = ""
    timestamp: float = 0.0


class ValidationResult(BaseModel, frozen=True):
    """Result of message validation."""

    valid: bool
    rejections: tuple[RejectedMessage, ...] = ()


def validate_raw_message(
    payload: Mapping[str, object] | None,
    pair: str | None,
    source: str | None,
    recv_time: float | None,
    stream_type: str | None,
) -> ValidationResult:
    """Validate that a raw message meets minimum requirements for normalization.

    Required: pair, source, recv_time, non-empty payload.
    """
    rejections: list[RejectedMessage] = []
    ts = recv_time or 0.0
    raw_payload = dict(payload) if payload is not None else {}

    if not payload:
        rejections.append(RejectedMessage(
            raw_payload=raw_payload,
            reason=RejectionReason.EMPTY_PAYLOAD,
            detail="Payload is empty or None",
            timestamp=ts,
        ))

    if not pair:
        rejections.append(RejectedMessage(
            raw_payload=raw_payload,
            reason=RejectionReason.MISSING_PAIR,
            detail="pair is required",
            timestamp=ts,
        ))

    if not source:
        rejections.append(RejectedMessage(
            raw_payload=raw_payload,
            reason=RejectionReason.MISSING_SOURCE,
            detail="source is required",
            timestamp=ts,
        ))

    if recv_time is None or recv_time <= 0:
        rejections.append(RejectedMessage(
            raw_payload=raw_payload,
            reason=RejectionReason.MISSING_RECV_TIME,
            detail="recv_time must be a positive timestamp",
            timestamp=ts,
        ))

    if stream_type is not None and stream_type.lower() not in {
        "trade", "depth", "kline", "heartbeat", "snapshot",
    }:
        rejections.append(RejectedMessage(
            raw_payload=raw_payload,
            reason=RejectionReason.INVALID_TYPE,
            detail=f"Unknown stream type: {stream_type}",
            timestamp=ts,
        ))

    return ValidationResult(
        valid=len(rejections) == 0,
        rejections=tuple(rejections),
    )
