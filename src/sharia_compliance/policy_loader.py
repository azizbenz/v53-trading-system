"""YAML loader for the bounded halal policy."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import yaml

from .contracts import AssetPolicy, ShariaPolicy


def load_sharia_policy(path: Path | str) -> ShariaPolicy:
    policy_path = Path(path)
    if not policy_path.exists():
        raise FileNotFoundError(f"Sharia policy {policy_path} does not exist")
    payload = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError(f"Sharia policy {policy_path} must deserialize to a mapping")
    normalized = dict(payload)
    whitelist_raw = normalized.get("whitelisted_base_assets", {})
    if not isinstance(whitelist_raw, Mapping):
        raise ValueError("whitelisted_base_assets must deserialize to a mapping")
    normalized["whitelisted_base_assets"] = {
        str(symbol).upper(): AssetPolicy.model_validate(
            {"symbol": str(symbol).upper(), **dict(entry)}
            if isinstance(entry, Mapping)
            else {"symbol": str(symbol).upper(), "reason": str(entry), "last_review_date": "2026-04-09", "review_period_days": 180}
        )
        for symbol, entry in whitelist_raw.items()
    }
    normalized["blacklisted_base_assets"] = tuple(
        str(symbol).upper() for symbol in normalized.get("blacklisted_base_assets", ())
    )
    normalized["blacklisted_pairs"] = tuple(
        str(pair).upper() for pair in normalized.get("blacklisted_pairs", ())
    )
    stablecoin_policy = normalized.get("stablecoin_policy")
    if isinstance(stablecoin_policy, Mapping):
        normalized["stablecoin_policy"] = {
            **dict(stablecoin_policy),
            "accepted_quote_assets": tuple(
                str(asset).upper() for asset in stablecoin_policy.get("accepted_quote_assets", ())
            ),
        }
    return ShariaPolicy.model_validate(normalized)


__all__ = ["load_sharia_policy"]
