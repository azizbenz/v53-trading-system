"""Typed contracts for governed capital-bucket profile artifacts."""

from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json

from pydantic import BaseModel, Field, model_validator

from .domain_types import RuntimeMode


REQUIRED_CAPITAL_BUCKETS: tuple[int, ...] = (400, 500, 1500, 4000)
_PROVEN_EXECUTED_RETURN_STATUSES = {
    "EXECUTED_NET_RETURN_PROVEN",
    "EXECUTED_RETURN_PROVEN",
}
_PROVEN_DRAWDOWN_STATUSES = {
    "TRUE_NET_EQUITY_DRAWDOWN_PROVEN",
    "MEASURED",
    "PROVEN",
}
_PROMOTION_READY_EXECUTION_FIDELITY_STATUSES = {
    "FULL_CANONICAL_EXECUTION",
    "SHADOW_OBSERVED",
    "MICRO_LIVE_OBSERVED",
}


class CapitalProfileBlockedPair(BaseModel, frozen=True):
    """Per-pair governed block decision carried by capital profile artifacts."""

    pair: str = Field(..., min_length=1)
    status: str = "PAIR_NOT_PROVEN"
    reason_codes: tuple[str, ...] = ()
    planned_notional: float | None = Field(default=None, ge=0.0)
    min_notional: float | None = Field(default=None, ge=0.0)
    metadata: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class CapitalBucketProfile(BaseModel, frozen=True):
    """Canonical capital-bucket viability artifact."""

    schema_version: str = Field(default="v1", min_length=1)
    capital_bucket: int = Field(..., ge=1)
    quote_currency: str = Field(default="USDT", min_length=1)
    initial_capital: float | None = Field(default=None, ge=0.0)
    usable_sizing_capital: float | None = Field(default=None, ge=0.0)
    reserve_buffer: float | None = Field(default=None, ge=0.0)
    capital_source_status: str = "CAPITAL_SOURCE_NOT_PROVEN"
    pair_universe: tuple[str, ...] = ()
    allowed_pairs: tuple[str, ...] = ()
    blocked_pairs: tuple[CapitalProfileBlockedPair, ...] = ()
    max_active_pairs: int | None = Field(default=None, ge=0)
    record_count: int | None = Field(default=None, ge=0)
    candidate_count: int | None = Field(default=None, ge=0)
    selected_count: int | None = Field(default=None, ge=0)
    executed_count: int | None = Field(default=None, ge=0)
    reduced_count: int | None = Field(default=None, ge=0)
    no_fill_count: int | None = Field(default=None, ge=0)
    hard_blocked_count: int | None = Field(default=None, ge=0)
    rejected_count: int | None = Field(default=None, ge=0)
    min_notional_block_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    capital_fragmentation_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    size_reduction_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    pair_universe_too_wide_status: str = "NOT_PROVEN"
    expected_ce_net: float | None = None
    executed_only_net_return: float | None = None
    executed_only_net_return_status: str = "EXECUTED_NET_RETURN_NOT_PROVEN"
    true_net_equity_max_drawdown: float | None = Field(default=None, ge=0.0, le=1.0)
    true_net_equity_drawdown_status: str = "TRUE_NET_EQUITY_DRAWDOWN_NOT_PROVEN"
    fee_source_status: str = "FEE_SOURCE_NOT_PROVEN"
    impact_source_status: str = "IMPACT_SOURCE_NOT_PROVEN"
    fill_realism_status: str = "FILL_REALISM_NOT_PROVEN"
    cost_parity_status: str = "REPLAY_LIVE_COST_PARITY_NOT_PROVEN"
    cost_model_completeness_status: str = "COST_MODEL_NOT_PROVEN"
    book_depth_source_status: str = "BOOK_DEPTH_NOT_PROVEN"
    impact_depth_readiness_status: str = "BOOK_DEPTH_NOT_PROVEN"
    execution_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    partial_fill_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    no_fill_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    sample_size_survival_status: str = "SAMPLE_SIZE_NOT_PROVEN"
    promotion_status: str = "CAPITAL_BUCKET_NOT_PROVEN"
    promotion_blockers: tuple[str, ...] = ()
    artifact_hash: str | None = None
    input_data_hash: str | None = None
    method_version_hash: str | None = None
    run_id: str | None = None
    strategy_ladder_manifest_ref: str | None = None
    execution_fidelity_status: str = "REPLAY_PROXY_EXECUTION"
    execution_fidelity_gap_codes: tuple[str, ...] = ()
    created_at: datetime | None = None
    expires_at: datetime | None = None

    @model_validator(mode="after")
    def validate_consistency(self) -> "CapitalBucketProfile":
        allowed = set(self.allowed_pairs)
        blocked = {item.pair for item in self.blocked_pairs}
        if allowed & blocked:
            raise ValueError("CapitalBucketProfile allowed_pairs and blocked_pairs must be disjoint")
        if self.max_active_pairs is not None and self.max_active_pairs > len(self.pair_universe):
            raise ValueError("CapitalBucketProfile max_active_pairs cannot exceed pair_universe size")
        return self

    @property
    def blocked_pair_symbols(self) -> tuple[str, ...]:
        return tuple(item.pair for item in self.blocked_pairs)

    @property
    def is_promotion_ready(self) -> bool:
        return (
            self.promotion_status == "CAPITAL_BUCKET_READY"
            and self.expires_at is not None
            and self.input_data_hash is not None
            and self.method_version_hash is not None
            and self.run_id is not None
            and self.strategy_ladder_manifest_ref is not None
            and self.execution_fidelity_status in _PROMOTION_READY_EXECUTION_FIDELITY_STATUSES
            and not self.execution_fidelity_gap_codes
            and self.artifact_hash == self.artifact_hash_sha256()
        )

    @property
    def has_proven_realized_profitability(self) -> bool:
        return self.executed_only_net_return_status in _PROVEN_EXECUTED_RETURN_STATUSES

    @property
    def has_proven_true_drawdown(self) -> bool:
        return self.true_net_equity_drawdown_status in _PROVEN_DRAWDOWN_STATUSES

    def artifact_hash_sha256(self) -> str:
        return capital_profile_artifact_hash(self)


class CapitalProfileValidationResult(BaseModel, frozen=True):
    """Validation outcome for a governed capital profile artifact."""

    status: str
    no_submit_status: str | None = None
    reasons: tuple[str, ...] = ()
    profile: CapitalBucketProfile | None = None


class CapitalProfileSelectionResult(BaseModel, frozen=True):
    """Bucket-selection result for governed runtime enforcement."""

    status: str
    live_capital: float | None = Field(default=None, ge=0.0)
    selected_bucket: int | None = Field(default=None, ge=1)
    profile: CapitalBucketProfile | None = None
    reasons: tuple[str, ...] = ()


class CapitalProfileEnforcementResult(BaseModel, frozen=True):
    """Enforcement outcome for governed allowed_pairs/max_active_pairs checks."""

    validation_status: str
    no_submit_status: str
    selected_bucket: int | None = Field(default=None, ge=1)
    allowed_pairs: tuple[str, ...] = ()
    blocked_pairs: tuple[CapitalProfileBlockedPair, ...] = ()
    max_active_pairs: int | None = Field(default=None, ge=0)
    runtime_mode: RuntimeMode = RuntimeMode.SHADOW
    reasons: tuple[str, ...] = ()


def _normalize_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def capital_profile_artifact_hash(profile: CapitalBucketProfile) -> str:
    """Return a deterministic hash over the profile content excluding self-hash."""

    payload = profile.model_copy(
        update={
            "artifact_hash": None,
            "created_at": _normalize_datetime(profile.created_at),
            "expires_at": _normalize_datetime(profile.expires_at),
        }
    ).model_dump(mode="json")
    encoded = json.dumps(
        payload,
        sort_keys=True,
        ensure_ascii=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


__all__ = [
    "REQUIRED_CAPITAL_BUCKETS",
    "CapitalBucketProfile",
    "CapitalProfileBlockedPair",
    "CapitalProfileEnforcementResult",
    "CapitalProfileSelectionResult",
    "CapitalProfileValidationResult",
    "capital_profile_artifact_hash",
]
