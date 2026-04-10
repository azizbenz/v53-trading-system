"""Helpers for explicit whitelist checks in the halal policy layer."""

from __future__ import annotations

from sharia_compliance.asset_blacklist import split_pair_assets
from sharia_compliance.contracts import AssetPolicy, ShariaPolicy


def get_base_asset_policy(
    pair: str,
    policy: ShariaPolicy,
    *,
    known_quote_suffixes: tuple[str, ...],
) -> AssetPolicy | None:
    base_asset, _quote_asset = split_pair_assets(pair, known_quote_suffixes=known_quote_suffixes)
    return policy.whitelisted_base_assets.get(base_asset)


def is_whitelisted_pair(
    pair: str,
    policy: ShariaPolicy,
    *,
    known_quote_suffixes: tuple[str, ...],
) -> bool:
    return get_base_asset_policy(
        pair,
        policy,
        known_quote_suffixes=known_quote_suffixes,
    ) is not None


__all__ = [
    "get_base_asset_policy",
    "is_whitelisted_pair",
]
