"""
V5.3 - REFUSAL_RECORDS
Version contrat : 1.0.0
Contrats de refus/no-trade/no-fill pour anti-survivorship-bias.
"""
from __future__ import annotations

from enum import Enum, unique

from pydantic import ConfigDict, Field, field_validator

from .domain_types import EngineId, TimestampedModel


@unique
class RefusalCategory(str, Enum):
    NO_TRADE = "no_trade"
    NO_FILL = "no_fill"
    PHANTOM = "phantom"
    HARD_BLOCK = "hard_block"
    PORTFOLIO_REJECTED = "portfolio_rejected"
    VERSION_INVALIDATED = "version_invalidated"


class RefusalRecord(TimestampedModel):
    """Journal entry for a governed refusal path."""

    pair: str = Field(..., min_length=5, max_length=20)
    engine_id: EngineId | None = Field(default=None)
    category: RefusalCategory = Field(...)
    reason_codes: tuple[str, ...] = Field(..., min_length=1)
    counterfactual_pnl: float | None = Field(default=None)

    model_config = ConfigDict(frozen=True, extra="forbid")

    @field_validator("pair")
    @classmethod
    def validate_pair(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("pair must not be empty")
        return normalized

    @field_validator("reason_codes")
    @classmethod
    def validate_reason_codes(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized: list[str] = []
        for reason_code in value:
            stripped = reason_code.strip()
            if not stripped:
                raise ValueError("reason_codes must not contain empty values")
            normalized.append(stripped)
        return tuple(normalized)


__all__ = ["RefusalCategory", "RefusalRecord"]
