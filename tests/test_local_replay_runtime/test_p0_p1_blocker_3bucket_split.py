"""P0 #1 + #2 + P1 #1 (2026-05-30) — test 3-bucket blocker semantic split.

Per audit run 31bdfa55481f6d8f, hard_block_reasons was mixing 3 semantic
categories (hard execution / promotion-blocker / diagnostic). The fix
splits them cleanly :

  - `hard_block_reasons` : REAL execution blockers only (ENGINE_NATIVE_NO_TRADE,
    engine-D cold start, etc.). Trade cannot execute.
  - `promotion_blockers` : Cost measurement blocked, edge proxy. Trade CAN
    execute but cannot be PROMOTED as backtest truth.
  - `diagnostic_status` : INFORMATIONAL (e.g. B2_ENGINE_NATIVE_DECISION_REUSED_FROM_B1).
    Not blocking anything; reported as info.

The test uses the public `_materialize_native_candidate_event` function via
`_run_native_engine_candidate` to validate the produced payload keys.
"""

from __future__ import annotations

# Direct unit test of the helpers used internally
from local_replay_runtime.strategy_ladder_economic_provenance import (
    EconomicProvenance,
)


def _build_provenance_with_cost_block(cost_block_reason: str = "B2_COST_MEASUREMENT_BLOCKED_SPREAD_AND_SLIPPAGE") -> EconomicProvenance:
    """Provenance with proxy edge + cost block reason (promotion blocker scenario)."""
    return EconomicProvenance(
        expected_edge_bps=5.0,
        expected_edge_provenance="DEFAULT_TO_CALIBRATE",  # proxy edge
        spread_bps=4.0,
        spread_provenance="DEFAULT_BY_BOOK_STATUS",
        slippage_bps=2.0,
        slippage_provenance="DEFAULT_TO_CALIBRATE",
        latency_penalty_bps=1.0,
        latency_provenance="DEFAULT_TO_CALIBRATE",
        fee_bps=10.0,
        fee_provenance="MEASURED_FROM_VENUE_METADATA",
        measured_cost_governance={
            "expected_cost_block_reason": cost_block_reason,
            "cost_source_used_for_break_even": "estimated",
        },
    )


def test_diagnostic_status_carries_decision_reused_when_runner_not_invoked() -> None:
    """When runner_invoked=False, B2_ENGINE_NATIVE_DECISION_REUSED_FROM_B1
    must land in diagnostic_status, NOT hard_block_reasons."""
    # Importing here to avoid runner-level imports breaking other tests
    from unittest.mock import MagicMock
    from local_replay_runtime.strategy_ladder_models import StrategyLadderCandidateEvent
    from local_replay_runtime.strategy_ladder_runner import _materialize_native_candidate_event

    candidate = StrategyLadderCandidateEvent(
        candidate_id="cand-1",
        pair="BTCUSDT",
        engine_id="engine_a",
        strategy_id="engine_a",
        timestamp_ms=1_700_000_000_000,
    )
    provenance = _build_provenance_with_cost_block()
    # Simulate not invoked
    result = _materialize_native_candidate_event(
        candidate=candidate,
        window=None,
        economic_provenance=provenance,
        builder_status="ENGINE_NATIVE_INPUT_BUILDER_NOT_RUN",
        builder_warnings=(),
        builder_provenance="TEST",
        engine_output=None,
        engine_input_payload={},
        build14_application=None,
        records_built=0,
        runner_invoked=False,
        ml_mode="ML_MODE_OFF",
    )
    payload = dict(result.compatibility_payload or {})
    diagnostic = payload.get("diagnostic_status", ())
    hard_block = payload.get("hard_block_reasons", ())
    assert "B2_ENGINE_NATIVE_DECISION_REUSED_FROM_B1" in diagnostic, (
        f"DECISION_REUSED must be in diagnostic_status, got {diagnostic}"
    )
    assert "B2_ENGINE_NATIVE_DECISION_REUSED_FROM_B1" not in hard_block, (
        f"DECISION_REUSED must NOT be in hard_block_reasons, got {hard_block}"
    )


def test_promotion_blockers_carries_cost_block_reason() -> None:
    """B2_COST_MEASUREMENT_BLOCKED_* must land in promotion_blockers, NOT hard_block."""
    from local_replay_runtime.strategy_ladder_models import StrategyLadderCandidateEvent
    from local_replay_runtime.strategy_ladder_runner import _materialize_native_candidate_event

    candidate = StrategyLadderCandidateEvent(
        candidate_id="cand-2",
        pair="BTCUSDT",
        engine_id="engine_a",
        strategy_id="engine_a",
        timestamp_ms=1_700_000_000_000,
    )
    provenance = _build_provenance_with_cost_block("B2_COST_MEASUREMENT_BLOCKED_SPREAD_AND_SLIPPAGE")
    result = _materialize_native_candidate_event(
        candidate=candidate,
        window=None,
        economic_provenance=provenance,
        builder_status="ENGINE_NATIVE_INPUT_BUILDER_NOT_RUN",
        builder_warnings=(),
        builder_provenance="TEST",
        engine_output=None,
        engine_input_payload={},
        build14_application=None,
        records_built=0,
        runner_invoked=False,
        ml_mode="ML_MODE_OFF",
    )
    payload = dict(result.compatibility_payload or {})
    promotion = payload.get("promotion_blockers", ())
    hard_block = payload.get("hard_block_reasons", ())
    assert "B2_COST_MEASUREMENT_BLOCKED_SPREAD_AND_SLIPPAGE" in promotion, (
        f"cost_block must be in promotion_blockers, got {promotion}"
    )
    assert "B2_COST_MEASUREMENT_BLOCKED_SPREAD_AND_SLIPPAGE" not in hard_block, (
        f"cost_block must NOT be in hard_block_reasons, got {hard_block}"
    )


def test_payload_has_three_distinct_bucket_keys() -> None:
    """compatibility_payload exposes all 3 buckets as distinct keys."""
    from local_replay_runtime.strategy_ladder_models import StrategyLadderCandidateEvent
    from local_replay_runtime.strategy_ladder_runner import _materialize_native_candidate_event

    candidate = StrategyLadderCandidateEvent(
        candidate_id="cand-3",
        pair="BTCUSDT",
        engine_id="engine_a",
        strategy_id="engine_a",
        timestamp_ms=1_700_000_000_000,
    )
    provenance = _build_provenance_with_cost_block()
    result = _materialize_native_candidate_event(
        candidate=candidate,
        window=None,
        economic_provenance=provenance,
        builder_status="ENGINE_NATIVE_INPUT_BUILDER_NOT_RUN",
        builder_warnings=(),
        builder_provenance="TEST",
        engine_output=None,
        engine_input_payload={},
        build14_application=None,
        records_built=0,
        runner_invoked=False,
        ml_mode="ML_MODE_OFF",
    )
    payload = dict(result.compatibility_payload or {})

    assert "hard_block_reasons" in payload
    assert "promotion_blockers" in payload
    assert "diagnostic_status" in payload
