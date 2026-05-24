"""Shared Strategy Ladder expected-edge feature contracts."""

from __future__ import annotations


DEFAULT_EXPECTED_EDGE_FEATURE_NAMES = ("close_return", "high_low_range", "volume")
REPLAY_MICROSTRUCTURE_EXPECTED_EDGE_FEATURE_NAMES = (
    "spread_bps",
    "slippage_bps",
    "book_depth_levels",
    "break_even_bps",
    "fragility_score",
    "false_breakout_context",
    "vpin",
    "cumulative_ofi",
    "queue_pressure",
)
EXTENDED_MICROSTRUCTURE_EXPECTED_EDGE_FEATURE_NAMES = (
    "kyle_lambda",
    "realized_vol_current",
    "realized_vol_at_break",
    "latency_penalty_bps",
)
BUILD14_OBSERVED_EXPECTED_EDGE_FEATURE_NAMES = (
    "micro_edge_exit_governor_observed",
    "micro_edge_entry_timing_observed",
)
ENGINE_D_GOVERNANCE_EXPECTED_EDGE_FEATURE_NAMES = (
    "history_score",
    "marginal_value_score",
    "reentry_lateness",
    "concentration_headroom",
)
ANTI_REVENGE_STATE_ONE_HOT_FEATURE_NAMES = (
    "anti_revenge_state__active",
    "anti_revenge_state__cooling",
    "anti_revenge_state__idle",
)
SUPPORTED_EXPECTED_EDGE_FEATURE_NAMES = (
    *DEFAULT_EXPECTED_EDGE_FEATURE_NAMES,
    *REPLAY_MICROSTRUCTURE_EXPECTED_EDGE_FEATURE_NAMES,
    *EXTENDED_MICROSTRUCTURE_EXPECTED_EDGE_FEATURE_NAMES,
    *BUILD14_OBSERVED_EXPECTED_EDGE_FEATURE_NAMES,
    *ENGINE_D_GOVERNANCE_EXPECTED_EDGE_FEATURE_NAMES,
    *ANTI_REVENGE_STATE_ONE_HOT_FEATURE_NAMES,
)
EXPECTED_EDGE_AUGMENTED_FEATURE_KEYS = tuple(
    name
    for name in SUPPORTED_EXPECTED_EDGE_FEATURE_NAMES
    if name not in DEFAULT_EXPECTED_EDGE_FEATURE_NAMES
)
SUPPORTED_FEATURE_NAME_SET = frozenset(SUPPORTED_EXPECTED_EDGE_FEATURE_NAMES)
LEGACY_FEATURE_NAME_SET = frozenset(DEFAULT_EXPECTED_EDGE_FEATURE_NAMES)
ANTI_REVENGE_STATE_ONE_HOT_SET = frozenset(ANTI_REVENGE_STATE_ONE_HOT_FEATURE_NAMES)


def normalize_supported_expected_edge_feature_names(
    raw_feature_names: tuple[str, ...] | list[str] | set[str] | frozenset[str],
) -> tuple[str, ...]:
    """Normalize and validate the governed expected-edge feature tuple."""

    normalized = tuple(
        dict.fromkeys(item.strip() for item in raw_feature_names if item.strip())
    )
    if not normalized:
        raise ValueError("feature_names must not be empty")
    unsupported = tuple(item for item in normalized if item not in SUPPORTED_FEATURE_NAME_SET)
    if unsupported:
        raise ValueError(f"unsupported Strategy Ladder expected-edge features: {unsupported}")
    anti_revenge_subset = {
        item for item in normalized if item in ANTI_REVENGE_STATE_ONE_HOT_SET
    }
    if anti_revenge_subset and anti_revenge_subset != ANTI_REVENGE_STATE_ONE_HOT_SET:
        raise ValueError(
            "anti_revenge_state one-hot requires the full governed triplet: "
            f"{ANTI_REVENGE_STATE_ONE_HOT_FEATURE_NAMES}"
        )
    return normalized


__all__ = [
    "ANTI_REVENGE_STATE_ONE_HOT_FEATURE_NAMES",
    "ANTI_REVENGE_STATE_ONE_HOT_SET",
    "BUILD14_OBSERVED_EXPECTED_EDGE_FEATURE_NAMES",
    "DEFAULT_EXPECTED_EDGE_FEATURE_NAMES",
    "ENGINE_D_GOVERNANCE_EXPECTED_EDGE_FEATURE_NAMES",
    "EXPECTED_EDGE_AUGMENTED_FEATURE_KEYS",
    "EXTENDED_MICROSTRUCTURE_EXPECTED_EDGE_FEATURE_NAMES",
    "LEGACY_FEATURE_NAME_SET",
    "REPLAY_MICROSTRUCTURE_EXPECTED_EDGE_FEATURE_NAMES",
    "SUPPORTED_EXPECTED_EDGE_FEATURE_NAMES",
    "SUPPORTED_FEATURE_NAME_SET",
    "normalize_supported_expected_edge_feature_names",
]
