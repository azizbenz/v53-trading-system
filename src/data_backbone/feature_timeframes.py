"""Canonical declaration of timeframes supported by the gold feature builder.

This module is the single source of truth for which timeframes the V5.3 gold
feature pipeline knows how to materialize. Adding a new timeframe means
extending ``SUPPORTED_GOLD_TIMEFRAMES`` here and proving downstream support;
nothing in the pipeline may invent timeframes outside this whitelist.

Reason codes emitted by ``strategy_ladder_data_factory._write_gold_features``
when a silver timeframe is not materialized in gold:

- ``TIMEFRAME_FEATURE_GENERATION_NOT_SUPPORTED``: silver carries this
  timeframe but it is not in ``SUPPORTED_GOLD_TIMEFRAMES``; explicit refusal,
  not a wiring gap.
- ``TIMEFRAME_FEATURE_INPUT_MISSING``: timeframe is requested and supported
  but no silver entry exists for it.
- ``TIMEFRAME_FEATURE_BUILD_FAILED``: a build exception was caught for this
  timeframe; the row count for the timeframe stays zero.
- ``TIMEFRAME_PRUNED_NOT_REQUESTED``: silver carries this timeframe, the
  registry supports it, but the caller's ``request.timeframes`` filter did
  not include it. Surfaced so prunes are never silent.
"""

from __future__ import annotations


SUPPORTED_GOLD_TIMEFRAMES: frozenset[str] = frozenset({"1m", "5m", "10m", "15m"})
"""Canonical whitelist of timeframes the gold builder may materialize."""

DEFAULT_GOLD_TIMEFRAMES: tuple[str, ...] = ("1m", "5m", "10m", "15m")
"""Default request value when callers do not pin an explicit subset.

Kept as a sorted tuple so it can be used directly as a default in frozen
Pydantic models. Order follows ascending bar duration.
"""

TIMEFRAME_FEATURE_GENERATION_NOT_SUPPORTED = "TIMEFRAME_FEATURE_GENERATION_NOT_SUPPORTED"
TIMEFRAME_FEATURE_INPUT_MISSING = "TIMEFRAME_FEATURE_INPUT_MISSING"
TIMEFRAME_FEATURE_BUILD_FAILED = "TIMEFRAME_FEATURE_BUILD_FAILED"
TIMEFRAME_PRUNED_NOT_REQUESTED = "TIMEFRAME_PRUNED_NOT_REQUESTED"


def normalize_timeframe(value: str | None) -> str:
    """Lowercase + strip a timeframe label. Empty input returns ``""``."""

    if value is None:
        return ""
    return str(value).strip().lower()


def is_supported_gold_timeframe(value: str | None) -> bool:
    """Return True when ``value`` (after normalization) is in the whitelist."""

    return normalize_timeframe(value) in SUPPORTED_GOLD_TIMEFRAMES


__all__ = [
    "SUPPORTED_GOLD_TIMEFRAMES",
    "DEFAULT_GOLD_TIMEFRAMES",
    "TIMEFRAME_FEATURE_GENERATION_NOT_SUPPORTED",
    "TIMEFRAME_FEATURE_INPUT_MISSING",
    "TIMEFRAME_FEATURE_BUILD_FAILED",
    "TIMEFRAME_PRUNED_NOT_REQUESTED",
    "normalize_timeframe",
    "is_supported_gold_timeframe",
]
