"""Bounded halal trade authorization guard."""

from __future__ import annotations

from collections.abc import Mapping

from .asset_blacklist import is_blacklisted_asset_pair, is_blacklisted_pair, split_pair_assets
from .asset_whitelist import is_whitelisted_pair
from .contracts import ShariaPermit, ShariaPolicy, ShariaRejection, ShariaTradeRequest
from .pair_screening import evaluate_pair_screening, load_pair_screening_snapshot
from .stablecoin_policy import is_quote_asset_permitted, resolve_quote_asset

_KNOWN_QUOTE_SUFFIXES = (
    "USDT",
    "FDUSD",
    "USDC",
    "BUSD",
    "TUSD",
    "BTC",
    "ETH",
    "BNB",
    "EUR",
    "USD",
)


def authorize_trade_type(
    request: ShariaTradeRequest,
    policy: ShariaPolicy,
) -> ShariaPermit | ShariaRejection:
    metadata = request.metadata
    if _is_short_direction(request.side, metadata):
        return _reject(policy, "SHORT_FORBIDDEN", "short selling is forbidden under the active spot-halal policy")
    if _resolve_trade_mode(metadata) != "SPOT":
        return _reject(policy, "NON_SPOT_FORBIDDEN", "only spot trading is permitted under the active halal policy")
    leverage = _resolve_leverage(metadata)
    if leverage > 1.0:
        return _reject(policy, "LEVERAGE_FORBIDDEN", "leveraged trading is forbidden under the active halal policy")
    if bool(metadata.get("margin_required", False)):
        return _reject(policy, "MARGIN_FORBIDDEN", "margin borrowing is forbidden under the active halal policy")

    base_asset, _quote_asset = split_pair_assets(
        request.pair,
        known_quote_suffixes=_KNOWN_QUOTE_SUFFIXES,
    )
    if is_blacklisted_pair(request.pair, policy):
        return _reject(policy, "PAIR_BLACKLISTED", f"pair {request.pair.upper()} is explicitly blacklisted")
    if is_blacklisted_asset_pair(
        request.pair,
        policy,
        known_quote_suffixes=_KNOWN_QUOTE_SUFFIXES,
    ):
        return _reject(policy, "ASSET_BLACKLISTED", f"asset policy forbids {request.pair.upper()}")
    if not is_whitelisted_pair(
        request.pair,
        policy,
        known_quote_suffixes=_KNOWN_QUOTE_SUFFIXES,
    ):
        return _reject(policy, "PAIR_NOT_WHITELISTED", f"base asset {base_asset} is not whitelisted")
    if not is_quote_asset_permitted(
        request.pair,
        policy,
        known_quote_suffixes=_KNOWN_QUOTE_SUFFIXES,
    ):
        quote_asset = resolve_quote_asset(
            request.pair,
            known_quote_suffixes=_KNOWN_QUOTE_SUFFIXES,
        )
        return _reject(policy, "QUOTE_ASSET_FORBIDDEN", f"quote asset {quote_asset} is not allowed by stablecoin policy")
    try:
        pair_screening = load_pair_screening_snapshot(metadata)
    except ValueError as exc:
        return _reject(policy, "PAIR_SCREENING_INVALID", str(exc))
    if _resolve_pair_screening_required(metadata) and pair_screening is None:
        return _reject(
            policy,
            "PAIR_SCREENING_MISSING",
            f"AAOIFI pair screening is required for {request.pair.upper()}",
        )
    if pair_screening is not None:
        if pair_screening.pair.strip().upper() != request.pair.strip().upper():
            return _reject(
                policy,
                "PAIR_SCREENING_MISMATCH",
                f"screening pair {pair_screening.pair.upper()} does not match request {request.pair.upper()}",
            )
        screening_result = evaluate_pair_screening(pair_screening, policy=policy)
        if not screening_result.passed:
            return _reject(policy, "PAIR_SCREENING_FAILED", screening_result.detail)
    return ShariaPermit(
        policy_version=policy.policy_version,
        detail=f"{request.pair.upper()} allowed by halal policy {policy.policy_version}",
    )


def _resolve_trade_mode(metadata: Mapping[str, object]) -> str:
    product_type = str(metadata.get("product_type", metadata.get("trade_mode", "SPOT"))).strip().upper()
    if not product_type:
        return "SPOT"
    return product_type


def _resolve_leverage(metadata: Mapping[str, object]) -> float:
    value = metadata.get("leverage", 1.0)
    if isinstance(value, bool):
        return 1.0
    if isinstance(value, int | float):
        return float(value)
    try:
        return float(str(value))
    except ValueError:
        return 1.0


def _resolve_pair_screening_required(metadata: Mapping[str, object]) -> bool:
    value = metadata.get("pair_screening_required", False)
    if isinstance(value, bool):
        return value
    if isinstance(value, int | float):
        return bool(value)
    return str(value).strip().lower() in {"1", "true", "yes", "required"}


def _is_short_direction(side: str, metadata: Mapping[str, object]) -> bool:
    side_value = side.strip().lower()
    if side_value == "short":
        return True
    position_type = str(metadata.get("position_type", "")).strip().lower()
    return position_type == "short"


def _reject(policy: ShariaPolicy, reason_code: str, detail: str) -> ShariaRejection:
    return ShariaRejection(
        reason_code=reason_code,
        policy_version=policy.policy_version,
        detail=detail,
    )


__all__ = ["authorize_trade_type"]
