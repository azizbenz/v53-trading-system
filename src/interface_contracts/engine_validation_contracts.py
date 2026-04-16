"""Shared Engine C/D validation-hook contracts."""

from __future__ import annotations

from pydantic import BaseModel, Field


class EngineCVoidValidationInput(BaseModel, frozen=True):
    """Bounded typed input for the Engine C void-validation hook."""

    context_id: str = Field(..., min_length=1)
    pair: str = Field(..., min_length=1)
    engine_id: str = Field(..., min_length=1)
    scoring_version: str = Field(..., min_length=1)
    breakout_type: str = ""
    continuation_context: str = ""
    raw_score: float = 0.0
    penalized_score: float = 0.0
    expected_cost: float = 0.0
    expected_ce: float = 0.0
    conviction: str = ""
    tier: str = ""


class EngineCVoidValidationOutcome(BaseModel, frozen=True):
    """Deterministic outcome of the bounded Engine C void-validation hook."""

    accepted: bool = True
    reason_codes: tuple[str, ...] = ()
    detail: str = ""


class EngineDReentryValidationInput(BaseModel, frozen=True):
    """Bounded typed input for the Engine D re-entry validation hook."""

    context_id: str = ""
    trade_id: str = ""
    pair: str = Field(..., min_length=1)
    engine_id: str = Field(..., min_length=1)
    scoring_version: str = Field(..., min_length=1)
    link_type: str = ""
    structure_reformed_detected: bool = False
    raw_score: float = 0.0
    penalized_score: float = 0.0
    expected_cost: float = 0.0
    expected_ce: float = 0.0
    conviction: str = ""
    tier: str = ""
    first_episode_id: str = ""
    first_episode_engine_id: str = ""
    first_episode_close_reason: str = ""
    consecutive_stop_count: int = Field(default=0, ge=0)
    last_stop_at_ns: int | None = Field(default=None, ge=1_000_000_000_000_000_000, le=9_999_999_999_999_999_999)
    last_fresh_a_detection_at_ns: int | None = Field(
        default=None,
        ge=1_000_000_000_000_000_000,
        le=9_999_999_999_999_999_999,
    )
    anti_revenge_state: str = ""


class EngineDReentryValidationOutcome(BaseModel, frozen=True):
    """Deterministic outcome of the bounded Engine D re-entry validation hook."""

    accepted: bool = True
    reason_codes: tuple[str, ...] = ()
    detail: str = ""
    episode_reference_id: str = ""
    anti_revenge_state: str = ""
    observability_tags: tuple[str, ...] = ()


__all__ = [
    "EngineCVoidValidationInput",
    "EngineCVoidValidationOutcome",
    "EngineDReentryValidationInput",
    "EngineDReentryValidationOutcome",
]
