"""Optional report-section helpers for the governed Shadow gate report."""

from __future__ import annotations

import math
from collections.abc import Mapping


def _as_mapping(value: object) -> Mapping[str, object] | None:
    return value if isinstance(value, Mapping) else None


def _coerce_float(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        numeric = float(value)
        return numeric if math.isfinite(numeric) else None
    if isinstance(value, str):
        try:
            numeric = float(value)
        except ValueError:
            return None
        return numeric if math.isfinite(numeric) else None
    return None


def _coerce_bool(value: object) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"pass", "passed", "true", "ok"}:
            return True
        if lowered in {"fail", "failed", "false", "ko"}:
            return False
    return None


def _resolve_engine_section_mapping(
    evidence: Mapping[str, object],
    engine_id: str,
    section_key: str,
) -> Mapping[str, object] | None:
    raw = _as_mapping(evidence.get(section_key))
    if raw is None:
        return None
    nested = _as_mapping(raw.get(engine_id))
    if nested is not None:
        return nested
    return raw


def build_refusal_analysis(
    *,
    engine_id: str,
    evidence: Mapping[str, object],
) -> dict[str, object]:
    refusal_mapping = _resolve_engine_section_mapping(evidence, engine_id, "refusal_analysis")
    if refusal_mapping is None:
        return {
            "status": "not_provided",
            "total_refusals": None,
            "hard_block_refusals": None,
            "portfolio_refusals": None,
            "reason": "refusal_analysis not provided",
        }
    total_refusals = _coerce_float(refusal_mapping.get("total_refusals"))
    hard_block_refusals = _coerce_float(refusal_mapping.get("hard_block_refusals"))
    portfolio_refusals = _coerce_float(refusal_mapping.get("portfolio_refusals"))
    if total_refusals is None:
        return {
            "status": "missing_input",
            "total_refusals": None,
            "hard_block_refusals": hard_block_refusals,
            "portfolio_refusals": portfolio_refusals,
            "reason": "refusal_analysis.total_refusals missing",
        }
    return {
        "status": "ready",
        "total_refusals": int(total_refusals),
        "hard_block_refusals": None if hard_block_refusals is None else int(hard_block_refusals),
        "portfolio_refusals": None if portfolio_refusals is None else int(portfolio_refusals),
    }


def build_capital_usage(
    *,
    engine_id: str,
    evidence: Mapping[str, object],
) -> dict[str, object]:
    capital_mapping = _resolve_engine_section_mapping(evidence, engine_id, "capital_usage")
    if capital_mapping is None:
        return {
            "status": "not_provided",
            "tier_cap_respected": None,
            "max_capital_fraction_used": None,
            "capital_tier": None,
            "reason": "capital_usage not provided",
        }
    tier_cap_respected = _coerce_bool(capital_mapping.get("tier_cap_respected"))
    max_capital_fraction_used = _coerce_float(capital_mapping.get("max_capital_fraction_used"))
    capital_tier = capital_mapping.get("capital_tier")
    if tier_cap_respected is None:
        return {
            "status": "missing_input",
            "tier_cap_respected": None,
            "max_capital_fraction_used": max_capital_fraction_used,
            "capital_tier": capital_tier if isinstance(capital_tier, str) else None,
            "reason": "capital_usage.tier_cap_respected missing",
        }
    return {
        "status": "ready",
        "tier_cap_respected": tier_cap_respected,
        "max_capital_fraction_used": max_capital_fraction_used,
        "capital_tier": capital_tier if isinstance(capital_tier, str) and capital_tier else None,
    }


def build_execution_stats(
    *,
    engine_id: str,
    evidence: Mapping[str, object],
) -> dict[str, object]:
    execution_mapping = _resolve_engine_section_mapping(evidence, engine_id, "execution_stats")
    if execution_mapping is None:
        return {
            "status": "not_provided",
            "fill_rate": None,
            "average_slippage_bps": None,
            "average_spread_paid_bps": None,
            "reason": "execution_stats not provided",
        }
    fill_rate = _coerce_float(execution_mapping.get("fill_rate"))
    average_slippage_bps = _coerce_float(execution_mapping.get("average_slippage_bps"))
    average_spread_paid_bps = _coerce_float(execution_mapping.get("average_spread_paid_bps"))
    if fill_rate is None:
        return {
            "status": "missing_input",
            "fill_rate": None,
            "average_slippage_bps": average_slippage_bps,
            "average_spread_paid_bps": average_spread_paid_bps,
            "reason": "execution_stats.fill_rate missing",
        }
    return {
        "status": "ready",
        "fill_rate": fill_rate,
        "average_slippage_bps": average_slippage_bps,
        "average_spread_paid_bps": average_spread_paid_bps,
    }


__all__ = [
    "build_capital_usage",
    "build_execution_stats",
    "build_refusal_analysis",
]
