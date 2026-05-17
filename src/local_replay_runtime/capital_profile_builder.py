"""Shared capital-profile artifact generation and fail-closed enforcement."""

from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Iterable

from pydantic import BaseModel, Field

from interface_contracts.atomic_io import atomic_write_json
from interface_contracts.capital_profile_contracts import (
    REQUIRED_CAPITAL_BUCKETS,
    CapitalBucketProfile,
    CapitalProfileBlockedPair,
    CapitalProfileEnforcementResult,
    CapitalProfileSelectionResult,
    CapitalProfileValidationResult,
    capital_profile_artifact_hash,
)
from interface_contracts.domain_types import RuntimeMode


_PROVEN_EXECUTED_RETURN_STATUSES = {
    "EXECUTED_NET_RETURN_PROVEN",
    "EXECUTED_RETURN_PROVEN",
}
_PROVEN_DRAWDOWN_STATUSES = {
    "TRUE_NET_EQUITY_DRAWDOWN_PROVEN",
    "MEASURED",
    "PROVEN",
}
_PROMOTION_READY_COST_STATUSES = {"COST_MODEL_COMPLETE"}
_PROMOTION_READY_FILL_STATUSES = {
    "FILL_REALISM_PROVEN",
    "FILL_REALISM_SHADOW_MEASURED",
}
_PROMOTION_READY_DEPTH_STATUSES = {"BOOK_DEPTH20_AVAILABLE"}
_PROMOTION_READY_SAMPLE_STATUSES = {"MEASURED", "PASS", "PROVEN"}
_PROMOTION_READY_FEE_STATUSES = {
    "FEE_SOURCE_PROVEN",
    "FEE_SOURCE_CONFIGURED",
    "FEE_SOURCE_EXCHANGE_METADATA",
}
_PROMOTION_READY_IMPACT_STATUSES = {
    "IMPACT_SOURCE_PROVEN",
    "IMPACT_SOURCE_DEPTH20_MODEL",
}
_PROMOTION_READY_PARITY_STATUSES = {
    "REPLAY_LIVE_COST_PARITY_PROVEN",
    "REPLAY_SHADOW_COST_PARITY_PROVEN",
}
_PROMOTION_READY_EXECUTION_FIDELITY_STATUSES = {
    "FULL_CANONICAL_EXECUTION",
    "SHADOW_OBSERVED",
    "MICRO_LIVE_OBSERVED",
}


class CapitalProfileBuildInput(BaseModel, frozen=True):
    """Typed build input for a single capital-bucket profile artifact."""

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
    promotion_status: str | None = None
    promotion_blockers: tuple[str, ...] = ()
    input_data_hash: str | None = None
    method_version_hash: str | None = None
    run_id: str | None = None
    strategy_ladder_manifest_ref: str | None = None
    execution_fidelity_status: str = "REPLAY_PROXY_EXECUTION"
    execution_fidelity_gap_codes: tuple[str, ...] = ()
    created_at: datetime | None = None
    expires_at: datetime | None = None


def _normalize_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _derive_promotion_status(
    payload: CapitalProfileBuildInput,
) -> tuple[str, tuple[str, ...]]:
    blockers = list(payload.promotion_blockers)
    created_at = _normalize_datetime(payload.created_at) or datetime.now(tz=UTC)
    expires_at = _normalize_datetime(payload.expires_at)
    if payload.record_count in {None, 0}:
        blockers.append("BLOCKED_BY_BACKTEST")
    if not payload.input_data_hash:
        blockers.append("BLOCKED_BY_INPUT_DATA_HASH")
    if not payload.method_version_hash:
        blockers.append("BLOCKED_BY_METHOD_VERSION_HASH")
    if not payload.run_id:
        blockers.append("BLOCKED_BY_RUN_ID")
    if not payload.strategy_ladder_manifest_ref:
        blockers.append("BLOCKED_BY_STRATEGY_LADDER_MANIFEST")
    if expires_at is None or expires_at <= created_at:
        blockers.append("BLOCKED_BY_FRESHNESS")
    if payload.execution_fidelity_status not in _PROMOTION_READY_EXECUTION_FIDELITY_STATUSES:
        blockers.append("BLOCKED_BY_EXECUTION_FIDELITY")
    if payload.execution_fidelity_gap_codes:
        blockers.append("BLOCKED_BY_EXECUTION_FIDELITY")
        blockers.extend(str(code) for code in payload.execution_fidelity_gap_codes if str(code))
    if payload.executed_only_net_return_status not in _PROVEN_EXECUTED_RETURN_STATUSES:
        blockers.append("BLOCKED_BY_EXECUTED_RETURN")
    if payload.true_net_equity_drawdown_status not in _PROVEN_DRAWDOWN_STATUSES:
        blockers.append("BLOCKED_BY_DRAWDOWN")
    if payload.cost_model_completeness_status not in _PROMOTION_READY_COST_STATUSES:
        blockers.append("BLOCKED_BY_COST_COMPLETENESS")
    if payload.fee_source_status not in _PROMOTION_READY_FEE_STATUSES:
        blockers.append("BLOCKED_BY_COST_COMPLETENESS")
    if payload.impact_source_status not in _PROMOTION_READY_IMPACT_STATUSES:
        blockers.append("BLOCKED_BY_COST_COMPLETENESS")
    if payload.cost_parity_status not in _PROMOTION_READY_PARITY_STATUSES:
        blockers.append("BLOCKED_BY_COST_COMPLETENESS")
    if payload.fill_realism_status not in _PROMOTION_READY_FILL_STATUSES:
        blockers.append("BLOCKED_BY_FILL_REALISM")
    if payload.book_depth_source_status not in _PROMOTION_READY_DEPTH_STATUSES:
        blockers.append("BLOCKED_BY_DEPTH")
    if payload.sample_size_survival_status not in _PROMOTION_READY_SAMPLE_STATUSES:
        blockers.append("BLOCKED_BY_SAMPLE_SIZE")
    if payload.min_notional_block_rate is not None and payload.min_notional_block_rate > 0.0:
        blockers.append("BLOCKED_BY_MIN_NOTIONAL")
    if payload.pair_universe_too_wide_status in {
        "PAIR_UNIVERSE_TOO_WIDE_FOR_CAPITAL",
        "FRAGMENTATION_HIGH",
    }:
        blockers.append("BLOCKED_BY_FRAGMENTATION")
    unique_blockers = tuple(dict.fromkeys(blockers))
    if payload.promotion_status:
        if payload.promotion_status == "CAPITAL_BUCKET_READY" and unique_blockers:
            return "CAPITAL_BUCKET_NOT_PROVEN", unique_blockers
        return payload.promotion_status, unique_blockers
    if not unique_blockers and payload.allowed_pairs:
        return "CAPITAL_BUCKET_READY", unique_blockers
    return "CAPITAL_BUCKET_NOT_PROVEN", unique_blockers


def build_capital_bucket_profile(payload: CapitalProfileBuildInput) -> CapitalBucketProfile:
    """Materialize a governed capital profile with deterministic self-hash."""

    promotion_status, promotion_blockers = _derive_promotion_status(payload)
    blocked_pairs = list(payload.blocked_pairs)
    allowed_pairs = payload.allowed_pairs
    if promotion_status != "CAPITAL_BUCKET_READY" and allowed_pairs:
        blocked_symbols = {item.pair for item in blocked_pairs}
        reason_map = {
            "CAPITAL_BUCKET_BLOCKED_BY_MIN_NOTIONAL": "PAIR_BLOCKED_MIN_NOTIONAL",
            "CAPITAL_BUCKET_BLOCKED_BY_COST_COMPLETENESS": "PAIR_BLOCKED_COST_COMPLETENESS",
            "CAPITAL_BUCKET_BLOCKED_BY_DEPTH": "PAIR_BLOCKED_DEPTH_LIMITATION",
            "CAPITAL_BUCKET_BLOCKED_BY_FILL_REALISM": "PAIR_BLOCKED_FILL_REALISM",
            "CAPITAL_BUCKET_BLOCKED_BY_DRAWDOWN": "PAIR_BLOCKED_DRAWDOWN",
            "CAPITAL_BUCKET_BLOCKED_BY_SAMPLE_SIZE": "PAIR_BLOCKED_SAMPLE_SIZE",
        }
        pair_reason = reason_map.get(promotion_status, "PAIR_NOT_PROVEN")
        for pair in allowed_pairs:
            if pair in blocked_symbols:
                continue
            blocked_pairs.append(
                CapitalProfileBlockedPair(
                    pair=pair,
                    status=pair_reason,
                    reason_codes=(pair_reason,),
                )
            )
        allowed_pairs = ()
    profile = CapitalBucketProfile(
        schema_version="v1",
        capital_bucket=payload.capital_bucket,
        quote_currency=payload.quote_currency,
        initial_capital=payload.initial_capital,
        usable_sizing_capital=payload.usable_sizing_capital,
        reserve_buffer=payload.reserve_buffer,
        capital_source_status=payload.capital_source_status,
        pair_universe=payload.pair_universe,
        allowed_pairs=allowed_pairs,
        blocked_pairs=tuple(blocked_pairs),
        max_active_pairs=payload.max_active_pairs,
        record_count=payload.record_count,
        candidate_count=payload.candidate_count,
        selected_count=payload.selected_count,
        executed_count=payload.executed_count,
        reduced_count=payload.reduced_count,
        no_fill_count=payload.no_fill_count,
        hard_blocked_count=payload.hard_blocked_count,
        rejected_count=payload.rejected_count,
        min_notional_block_rate=payload.min_notional_block_rate,
        capital_fragmentation_rate=payload.capital_fragmentation_rate,
        size_reduction_rate=payload.size_reduction_rate,
        pair_universe_too_wide_status=payload.pair_universe_too_wide_status,
        expected_ce_net=payload.expected_ce_net,
        executed_only_net_return=payload.executed_only_net_return,
        executed_only_net_return_status=payload.executed_only_net_return_status,
        true_net_equity_max_drawdown=payload.true_net_equity_max_drawdown,
        true_net_equity_drawdown_status=payload.true_net_equity_drawdown_status,
        fee_source_status=payload.fee_source_status,
        impact_source_status=payload.impact_source_status,
        fill_realism_status=payload.fill_realism_status,
        cost_parity_status=payload.cost_parity_status,
        cost_model_completeness_status=payload.cost_model_completeness_status,
        book_depth_source_status=payload.book_depth_source_status,
        impact_depth_readiness_status=payload.impact_depth_readiness_status,
        execution_rate=payload.execution_rate,
        partial_fill_rate=payload.partial_fill_rate,
        no_fill_rate=payload.no_fill_rate,
        sample_size_survival_status=payload.sample_size_survival_status,
        promotion_status=promotion_status,
        promotion_blockers=promotion_blockers,
        input_data_hash=payload.input_data_hash,
        method_version_hash=payload.method_version_hash,
        run_id=payload.run_id,
        strategy_ladder_manifest_ref=payload.strategy_ladder_manifest_ref,
        execution_fidelity_status=payload.execution_fidelity_status,
        execution_fidelity_gap_codes=payload.execution_fidelity_gap_codes,
        created_at=_normalize_datetime(payload.created_at),
        expires_at=_normalize_datetime(payload.expires_at),
    )
    artifact_hash = capital_profile_artifact_hash(profile)
    return profile.model_copy(update={"artifact_hash": artifact_hash})


def build_contract_validation_capital_profiles(
    *,
    buckets: Iterable[int] = REQUIRED_CAPITAL_BUCKETS,
    quote_currency: str = "USDT",
    method_version_hash: str = "capital_profile_builder.v1",
) -> tuple[CapitalBucketProfile, ...]:
    """Build contract-only NOT_PROVEN profiles without inventing measured evidence."""

    return tuple(
        build_capital_bucket_profile(
            CapitalProfileBuildInput(
                capital_bucket=int(bucket),
                quote_currency=quote_currency,
                method_version_hash=method_version_hash,
                promotion_status="CAPITAL_BUCKET_NOT_PROVEN",
                promotion_blockers=("BLOCKED_BY_BACKTEST",),
            )
        )
        for bucket in buckets
    )


def load_capital_profile(path: str | Path) -> CapitalBucketProfile:
    """Load a capital profile artifact from disk."""

    return CapitalBucketProfile.model_validate_json(Path(path).read_text(encoding="utf-8"))


def validate_capital_profile(
    profile: CapitalBucketProfile | None,
    *,
    as_of: datetime | None = None,
    expected_hash: str | None = None,
) -> CapitalProfileValidationResult:
    """Validate hash, freshness, and proof status for a capital profile artifact."""

    if profile is None:
        return CapitalProfileValidationResult(
            status="CAPITAL_PROFILE_MISSING",
            no_submit_status="NO_SUBMIT_CAPITAL_PROFILE_INVALID",
            reasons=("CAPITAL_PROFILE_MISSING",),
        )
    computed_hash = capital_profile_artifact_hash(profile)
    if expected_hash is not None and expected_hash != computed_hash:
        return CapitalProfileValidationResult(
            status="CAPITAL_PROFILE_HASH_INVALID",
            no_submit_status="NO_SUBMIT_CAPITAL_PROFILE_INVALID",
            reasons=("CAPITAL_PROFILE_HASH_INVALID",),
            profile=profile,
        )
    if profile.artifact_hash not in {None, computed_hash}:
        return CapitalProfileValidationResult(
            status="CAPITAL_PROFILE_HASH_INVALID",
            no_submit_status="NO_SUBMIT_CAPITAL_PROFILE_INVALID",
            reasons=("CAPITAL_PROFILE_HASH_INVALID",),
            profile=profile,
        )
    now = _normalize_datetime(as_of) or datetime.now(tz=UTC)
    expires_at = _normalize_datetime(profile.expires_at)
    metadata_reasons: list[str] = []
    if expires_at is None:
        metadata_reasons.append("CAPITAL_PROFILE_EXPIRY_MISSING")
    if expires_at is not None and now > expires_at:
        return CapitalProfileValidationResult(
            status="CAPITAL_PROFILE_STALE",
            no_submit_status="NO_SUBMIT_CAPITAL_PROFILE_INVALID",
            reasons=("CAPITAL_PROFILE_STALE",),
            profile=profile,
        )
    if not profile.input_data_hash:
        metadata_reasons.append("CAPITAL_PROFILE_INPUT_DATA_HASH_MISSING")
    if not profile.method_version_hash:
        metadata_reasons.append("CAPITAL_PROFILE_METHOD_VERSION_HASH_MISSING")
    if not profile.run_id:
        metadata_reasons.append("CAPITAL_PROFILE_RUN_ID_MISSING")
    if not profile.strategy_ladder_manifest_ref:
        metadata_reasons.append("CAPITAL_PROFILE_STRATEGY_LADDER_MANIFEST_REF_MISSING")
    if profile.execution_fidelity_status not in _PROMOTION_READY_EXECUTION_FIDELITY_STATUSES:
        metadata_reasons.append("CAPITAL_PROFILE_EXECUTION_FIDELITY_NOT_PROMOTION_READY")
    if profile.execution_fidelity_gap_codes:
        metadata_reasons.append("CAPITAL_PROFILE_EXECUTION_FIDELITY_GAPS_PRESENT")
        metadata_reasons.extend(
            str(code) for code in profile.execution_fidelity_gap_codes if str(code)
        )
    if metadata_reasons and profile.promotion_status == "CAPITAL_BUCKET_READY":
        return CapitalProfileValidationResult(
            status="CAPITAL_PROFILE_NOT_PROVEN",
            no_submit_status="NO_SUBMIT_CAPITAL_PROFILE_INVALID",
            reasons=tuple(dict.fromkeys(metadata_reasons)),
            profile=profile,
        )
    if profile.promotion_status in {
        "CAPITAL_BUCKET_NOT_PROVEN",
        "CAPITAL_BUCKET_BLOCKED_BY_BACKTEST",
    }:
        return CapitalProfileValidationResult(
            status="CAPITAL_PROFILE_NOT_PROVEN",
            no_submit_status="NO_SUBMIT_CAPITAL_PROFILE_INVALID",
            reasons=("CAPITAL_PROFILE_NOT_PROVEN",),
            profile=profile,
        )
    return CapitalProfileValidationResult(
        status="CAPITAL_PROFILE_VALID",
        no_submit_status=None,
        reasons=("CAPITAL_PROFILE_VALID",),
        profile=profile,
    )


def select_lower_proven_capital_bucket(
    *,
    live_capital: float,
    profiles: Iterable[CapitalBucketProfile],
    as_of: datetime | None = None,
) -> CapitalProfileSelectionResult:
    """Choose the highest valid bucket that does not exceed available live capital."""

    valid_profiles: list[CapitalBucketProfile] = []
    reasons: list[str] = []
    for profile in sorted(profiles, key=lambda item: item.capital_bucket):
        validation = validate_capital_profile(profile, as_of=as_of)
        if validation.status == "CAPITAL_PROFILE_VALID":
            valid_profiles.append(profile)
        else:
            reasons.extend(validation.reasons)
    eligible = [profile for profile in valid_profiles if profile.capital_bucket <= live_capital]
    if not eligible:
        return CapitalProfileSelectionResult(
            status="CAPITAL_PROFILE_NOT_PROVEN",
            live_capital=live_capital,
            reasons=tuple(dict.fromkeys(reasons or ["CAPITAL_PROFILE_NOT_PROVEN"])),
        )
    selected = max(eligible, key=lambda item: item.capital_bucket)
    return CapitalProfileSelectionResult(
        status="CAPITAL_PROFILE_VALID",
        live_capital=live_capital,
        selected_bucket=selected.capital_bucket,
        profile=selected,
        reasons=("CAPITAL_PROFILE_VALID",),
    )


def enforce_capital_profile(
    *,
    runtime_mode: RuntimeMode,
    profile: CapitalBucketProfile | None,
    requested_pairs: tuple[str, ...] = (),
    configured_pairs: tuple[str, ...] = (),
    active_pair_count: int = 0,
    as_of: datetime | None = None,
) -> CapitalProfileEnforcementResult:
    """Apply governed allowed_pairs/max_active_pairs no-submit checks."""

    validation = validate_capital_profile(profile, as_of=as_of)
    if validation.status != "CAPITAL_PROFILE_VALID" or validation.profile is None:
        return CapitalProfileEnforcementResult(
            validation_status=validation.status,
            no_submit_status="NO_SUBMIT_CAPITAL_PROFILE_INVALID",
            runtime_mode=runtime_mode,
            reasons=validation.reasons or ("NO_SUBMIT_CAPITAL_PROFILE_INVALID",),
        )
    validated = validation.profile
    allowed_pairs = tuple(
        pair for pair in dict.fromkeys((*configured_pairs, *requested_pairs)) if pair in set(validated.allowed_pairs)
    )
    blocked_rows = list(validated.blocked_pairs)
    for pair in dict.fromkeys((*configured_pairs, *requested_pairs)):
        if pair not in set(validated.allowed_pairs):
            blocked_rows.append(
                CapitalProfileBlockedPair(
                    pair=pair,
                    status="PAIR_NOT_PROVEN",
                    reason_codes=("CAPITAL_PROFILE_PAIR_NOT_ALLOWED",),
                )
            )
    reasons: list[str] = []
    if validated.max_active_pairs is not None and active_pair_count > validated.max_active_pairs:
        reasons.append("CAPITAL_PROFILE_MAX_ACTIVE_PAIRS_EXCEEDED")
    if not allowed_pairs and (*configured_pairs, *requested_pairs):
        reasons.append("CAPITAL_PROFILE_ALLOWED_PAIRS_EMPTY")
    deduped_blocked_pairs: list[CapitalProfileBlockedPair] = []
    seen_blocked_keys: set[tuple[str, str, tuple[str, ...]]] = set()
    for row in blocked_rows:
        key = (row.pair, row.status, tuple(row.reason_codes))
        if key in seen_blocked_keys:
            continue
        seen_blocked_keys.add(key)
        deduped_blocked_pairs.append(row)
    no_submit_status = (
        "NO_SUBMIT_CAPITAL_PROFILE_INVALID"
        if reasons and runtime_mode in {RuntimeMode.MICRO_LIVE, RuntimeMode.LIVE}
        else "CAPITAL_PROFILE_VALID"
    )
    return CapitalProfileEnforcementResult(
        validation_status=validation.status,
        no_submit_status=no_submit_status,
        selected_bucket=validated.capital_bucket,
        allowed_pairs=allowed_pairs,
        blocked_pairs=tuple(deduped_blocked_pairs),
        max_active_pairs=validated.max_active_pairs,
        runtime_mode=runtime_mode,
        reasons=tuple(dict.fromkeys(reasons or validation.reasons)),
    )


def discover_capital_profile_refs(export_dir: Path) -> tuple[str, ...]:
    """Return sorted capital profile refs from a governed replay export directory."""

    capital_dir = export_dir / "capital_profiles"
    if not capital_dir.is_dir():
        return ()
    def _bucket_key(path: Path) -> tuple[int, str]:
        try:
            return (int(path.stem), path.name)
        except ValueError:
            return (10**9, path.name)
    return tuple(
        str(path.resolve())
        for path in sorted(capital_dir.glob("*.json"), key=_bucket_key)
        if path.is_file()
    )


def serialize_capital_profiles(
    profiles: Iterable[CapitalBucketProfile],
) -> dict[str, dict[str, object]]:
    """Return bucket-keyed payloads suitable for replay artifact export."""

    return {
        str(profile.capital_bucket): profile.model_dump(mode="json")
        for profile in sorted(profiles, key=lambda item: item.capital_bucket)
    }


def write_capital_profile_artifacts(
    output_dir: Path,
    profiles: Iterable[CapitalBucketProfile],
) -> tuple[Path, ...]:
    """Write canonical `capital_profiles/<bucket>.json` artifacts."""

    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for profile in sorted(profiles, key=lambda item: item.capital_bucket):
        path = output_dir / f"{profile.capital_bucket}.json"
        atomic_write_json(path, profile.model_dump(mode="json"))
        written.append(path)
    return tuple(written)


__all__ = [
    "CapitalProfileBuildInput",
    "build_capital_bucket_profile",
    "build_contract_validation_capital_profiles",
    "discover_capital_profile_refs",
    "enforce_capital_profile",
    "load_capital_profile",
    "select_lower_proven_capital_bucket",
    "serialize_capital_profiles",
    "validate_capital_profile",
    "write_capital_profile_artifacts",
]
