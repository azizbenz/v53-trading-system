"""Helpers for stablecoin policy checks in the halal policy layer."""

from __future__ import annotations

from sharia_compliance.asset_blacklist import split_pair_assets
from sharia_compliance.contracts import ShariaPolicy


def resolve_quote_asset(
    pair: str,
    *,
    known_quote_suffixes: tuple[str, ...],
) -> str:
    _base_asset, quote_asset = split_pair_assets(pair, known_quote_suffixes=known_quote_suffixes)
    return quote_asset


def is_quote_asset_permitted(
    pair: str,
    policy: ShariaPolicy,
    *,
    known_quote_suffixes: tuple[str, ...],
) -> bool:
    quote_asset = resolve_quote_asset(pair, known_quote_suffixes=known_quote_suffixes)
    accepted_quotes = {asset.upper() for asset in policy.stablecoin_policy.accepted_quote_assets}
    return quote_asset in accepted_quotes


__all__ = [
    "is_quote_asset_permitted",
    "resolve_quote_asset",
]
