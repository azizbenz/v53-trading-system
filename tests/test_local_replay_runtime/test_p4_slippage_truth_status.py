"""P4 (2026-05-29) — test slippage explicit truth status enum on gold rows.

Covers B3 from A2_GOLD_PROD_SAFE_CLEANUP_SPEC:
  - derive_slippage_truth_status helper maps provenance → audit-explicit enum
  - separates A2 Kyle/research-only from B2 depth-walk truth
  - schema field added on StrategyLadderFeatureRow

Validates the audit's discipline: each gold row carries an EXPLICIT label of
slippage truth quality, so downstream validators (P5) can fail-closed on
promotion without ambiguity.
"""

from __future__ import annotations

from local_replay_runtime.strategy_ladder_economic_provenance import (
    derive_slippage_truth_status,
)
from local_replay_runtime.strategy_ladder_models import StrategyLadderFeatureRow


def test_derive_slippage_truth_status_kyle_measured() -> None:
    assert derive_slippage_truth_status(
        "MEASURED_FROM_KYLE_LAMBDA"
    ) == "SLIPPAGE_A2_KYLE_MEASURED"


def test_derive_slippage_truth_status_kyle_override() -> None:
    assert derive_slippage_truth_status(
        "MEASURED_FROM_KYLE_LAMBDA_OVERRIDE"
    ) == "SLIPPAGE_A2_KYLE_OVERRIDE"


def test_derive_slippage_truth_status_research_only_default() -> None:
    assert derive_slippage_truth_status(
        "DEFAULT_TO_CALIBRATE"
    ) == "SLIPPAGE_A2_RESEARCH_ONLY_DEFAULT"


def test_derive_slippage_truth_status_b2_depth_walk_future() -> None:
    """Forward-compat: B2 replay-time measurement maps to depth20 truth."""
    assert derive_slippage_truth_status(
        "MEASURED_FROM_DEPTH20_BOOK_WALK"
    ) == "SLIPPAGE_B2_DEPTH20_BOOK_WALK_MEASURED"
    assert derive_slippage_truth_status(
        "MEASURED_FROM_BOOK_WALK_TIER1"
    ) == "SLIPPAGE_B2_DEPTH20_BOOK_WALK_MEASURED"


def test_derive_slippage_truth_status_unknown_measured_method() -> None:
    """Future MEASURED_FROM_* methods (Amihud, etc.) accepted as A2-measured."""
    status = derive_slippage_truth_status("MEASURED_FROM_AMIHUD_ILLIQUIDITY")
    assert status == "SLIPPAGE_A2_MEASURED_FROM_AMIHUD_ILLIQUIDITY"


def test_derive_slippage_truth_status_not_proven_when_empty_or_unknown() -> None:
    assert derive_slippage_truth_status("") == "SLIPPAGE_NOT_PROVEN"
    assert derive_slippage_truth_status(None) == "SLIPPAGE_NOT_PROVEN"
    assert derive_slippage_truth_status(
        "RANDOM_INVALID_PROVENANCE"
    ) == "SLIPPAGE_NOT_PROVEN"


def test_derive_slippage_truth_status_normalizes_case() -> None:
    assert derive_slippage_truth_status(
        "measured_from_kyle_lambda"
    ) == "SLIPPAGE_A2_KYLE_MEASURED"


def test_strategy_ladder_feature_row_accepts_p4_slippage_truth_field() -> None:
    row = StrategyLadderFeatureRow(
        pair="BTCUSDT",
        timeframe="15m",
        timestamp_ms=1_745_884_800_000,
        engine_id="engine_a",
        source_ref="K:/output lab/runs/x/phase_a2_data_factory/gold/...",
        slippage_truth_status="SLIPPAGE_A2_KYLE_MEASURED",
    )

    assert row.slippage_truth_status == "SLIPPAGE_A2_KYLE_MEASURED"


def test_strategy_ladder_feature_row_p4_back_compat_default() -> None:
    row = StrategyLadderFeatureRow(
        pair="BTCUSDT",
        timeframe="15m",
        timestamp_ms=1_745_884_800_000,
        engine_id="engine_a",
        source_ref="K:/output lab/runs/x/phase_a2_data_factory/gold/...",
    )

    assert row.slippage_truth_status == "SLIPPAGE_NOT_PROVEN"
