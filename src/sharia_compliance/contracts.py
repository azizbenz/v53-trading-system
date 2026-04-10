"""Typed contracts for the bounded halal compliance layer."""

from __future__ import annotations

from decimal import Decimal
from datetime import date, datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class AssetPolicy(BaseModel, frozen=True):
    """Documented policy row for one allowed base asset."""

    symbol: str = Field(..., min_length=1)
    allowed: bool = True
    reason: str = Field(..., min_length=1)
    scholar_references: tuple[str, ...] = Field(default_factory=tuple)
    last_review_date: date
    review_period_days: int = Field(..., ge=1)


class StablecoinPolicy(BaseModel, frozen=True):
    """Bounded stablecoin policy for the active halal trading perimeter."""

    accepted_quote_assets: tuple[str, ...] = Field(default_factory=tuple)
    rationale: str = Field(..., min_length=1)
    scholar_reference: str = Field(..., min_length=1)
    review_date: date
    purification_required: bool = True
    purification_frequency_days: int = Field(default=30, ge=1)


class ShariaPolicy(BaseModel, frozen=True):
    """Versioned halal policy loaded from YAML."""

    schema_version: str = Field(default="sharia.policy.v1", min_length=1)
    policy_version: str = Field(..., min_length=1)
    fiqh_reference: str = Field(..., min_length=1)
    allow_spot_only: bool = True
    whitelisted_base_assets: dict[str, AssetPolicy] = Field(default_factory=dict)
    blacklisted_base_assets: tuple[str, ...] = Field(default_factory=tuple)
    blacklisted_pairs: tuple[str, ...] = Field(default_factory=tuple)
    stablecoin_policy: StablecoinPolicy


class ShariaTradeRequest(BaseModel, frozen=True):
    """Normalized trade request checked before execution submit."""

    intent_id: str = Field(..., min_length=1)
    pair: str = Field(..., min_length=1)
    engine_id: str = Field(..., min_length=1)
    side: str = Field(..., min_length=1)
    profile: str = Field(default="COMPLETE", min_length=1)
    metadata: dict[str, object] = Field(default_factory=dict)


class AaoifiPairScreeningSnapshot(BaseModel, frozen=True):
    """Deterministic AAOIFI/Usmani-style financial screening snapshot for one pair."""

    pair: str = Field(..., min_length=1)
    screening_provider: str = Field(..., min_length=1)
    provider_version: str = Field(..., min_length=1)
    reviewed_at: datetime
    debt_to_total_assets: Decimal = Field(..., ge=0, le=1)
    cash_and_interest_bearing_to_total_assets: Decimal = Field(..., ge=0, le=1)
    interest_income_to_total_revenue: Decimal = Field(..., ge=0, le=1)
    detail: str = ""


class AaoifiPairScreeningResult(BaseModel, frozen=True):
    """Deterministic AAOIFI pair-screening verdict."""

    passed: bool
    policy_version: str = Field(..., min_length=1)
    failure_codes: tuple[str, ...] = Field(default_factory=tuple)
    detail: str = ""


class AaoifiPairScreeningRegistry(BaseModel, frozen=True):
    """Versioned registry of deterministic pair-screening snapshots."""

    schema_version: str = Field(default="sharia.pair_screening_registry.v1", min_length=1)
    registry_version: str = Field(..., min_length=1)
    source_reference: str = Field(..., min_length=1)
    snapshots: tuple[AaoifiPairScreeningSnapshot, ...]

    @model_validator(mode="after")
    def validate_unique_pairs(self) -> "AaoifiPairScreeningRegistry":
        if not self.snapshots:
            raise ValueError("AaoifiPairScreeningRegistry snapshots must not be empty")
        pair_ids = tuple(snapshot.pair.strip().upper() for snapshot in self.snapshots)
        if len(pair_ids) != len(set(pair_ids)):
            raise ValueError("AaoifiPairScreeningRegistry pairs must be unique")
        return self


class AaoifiPairScreeningAuditFinding(BaseModel, frozen=True):
    """Single deterministic HC-4 screening violation."""

    pair: str = Field(..., min_length=1)
    reason_code: str = Field(..., min_length=1)
    detail: str = Field(..., min_length=1)


class AaoifiPairScreeningAuditReport(BaseModel, frozen=True):
    """Deterministic audit report for traded pairs versus screening registry."""

    scanned_at: datetime
    registry_version: str = Field(..., min_length=1)
    screened_pairs: tuple[str, ...] = Field(default_factory=tuple)
    findings: tuple[AaoifiPairScreeningAuditFinding, ...] = Field(default_factory=tuple)

    @property
    def clean(self) -> bool:
        return not self.findings


class PurificationSourceType(StrEnum):
    AIRDROP = "airdrop"
    FORK = "fork"
    STAKING = "staking"
    INTEREST = "interest"
    STABLECOIN_RESERVE = "stablecoin_reserve"


class PurificationEstimate(BaseModel, frozen=True):
    """Deterministic estimate of the amount that must be purified."""

    asset_symbol: str = Field(..., min_length=1)
    source_type: PurificationSourceType
    policy_version: str = Field(..., min_length=1)
    gross_amount_quote: Decimal = Field(..., ge=0)
    purification_amount_quote: Decimal = Field(..., ge=0)
    purification_rate: Decimal = Field(..., ge=0, le=1)
    detail: str = ""


class ShariaPermit(BaseModel, frozen=True):
    allowed: Literal[True] = True
    policy_version: str = Field(..., min_length=1)
    detail: str = ""


class ShariaRejection(BaseModel, frozen=True):
    allowed: Literal[False] = False
    reason_code: str = Field(..., min_length=1)
    policy_version: str = Field(..., min_length=1)
    detail: str = ""


class ShariaAuditEvent(BaseModel, frozen=True):
    """Append-only audit event for allow/reject decisions."""

    timestamp: datetime
    intent_id: str = Field(..., min_length=1)
    pair: str = Field(..., min_length=1)
    engine_id: str = Field(..., min_length=1)
    decision: Literal["permit", "reject"]
    reason_code: str = ""
    policy_version: str = Field(..., min_length=1)
    detail: str = ""


class AccountFeatureAuditFinding(BaseModel, frozen=True):
    """Single deterministic halal-account violation."""

    reason_code: str = Field(..., min_length=1)
    detail: str = Field(..., min_length=1)
    observation: str = Field(..., min_length=1)


class AccountFeaturesAuditReport(BaseModel, frozen=True):
    """Deterministic report of forbidden account features."""

    scanned_at: datetime
    audit_interval_s: int = Field(..., ge=1)
    findings: tuple[AccountFeatureAuditFinding, ...] = Field(default_factory=tuple)

    @property
    def clean(self) -> bool:
        return not self.findings


__all__ = [
    "AaoifiPairScreeningAuditFinding",
    "AaoifiPairScreeningAuditReport",
    "AaoifiPairScreeningRegistry",
    "AaoifiPairScreeningResult",
    "AaoifiPairScreeningSnapshot",
    "AccountFeatureAuditFinding",
    "AccountFeaturesAuditReport",
    "AssetPolicy",
    "PurificationEstimate",
    "PurificationSourceType",
    "ShariaAuditEvent",
    "ShariaPermit",
    "ShariaPolicy",
    "ShariaRejection",
    "ShariaTradeRequest",
    "StablecoinPolicy",
]
