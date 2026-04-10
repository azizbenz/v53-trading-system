"""Helpers for explicit blacklist checks in the halal policy layer."""

from __future__ import annotations

from sharia_compliance.contracts import ShariaPolicy


def split_pair_assets(pair: str, *, known_quote_suffixes: tuple[str, ...]) -> tuple[str, str]:
    normalized = pair.strip().upper()
    for suffix in known_quote_suffixes:
        if normalized.endswith(suffix) and len(normalized) > len(suffix):
            return normalized[: -len(suffix)], suffix
    raise ValueError(f"Unable to resolve quote asset for pair '{pair}'")


def is_blacklisted_pair(pair: str, policy: ShariaPolicy) -> bool:
    return pair.strip().upper() in policy.blacklisted_pairs


def is_blacklisted_asset_pair(
    pair: str,
    policy: ShariaPolicy,
    *,
    known_quote_suffixes: tuple[str, ...],
) -> bool:
    base_asset, quote_asset = split_pair_assets(pair, known_quote_suffixes=known_quote_suffixes)
    return base_asset in policy.blacklisted_base_assets or quote_asset in policy.blacklisted_base_assets


__all__ = [
    "is_blacklisted_asset_pair",
    "is_blacklisted_pair",
    "split_pair_assets",
]
