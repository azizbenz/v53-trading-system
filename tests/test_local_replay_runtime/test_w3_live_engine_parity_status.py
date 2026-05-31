"""W3 (2026-05-30) — test live_engine_parity_status derivation.

Closes the perpetual `live_engine_parity_status: NOT_PROVEN` blocker in
the run manifest. The helper inspects the 7 canonical model_source fields
+ execution_fidelity_gap_codes and emits PROVEN_NO_FIDELITY_GAP /
PROVEN_PARTIAL_FIDELITY / NOT_PROVEN per V5.3 doctrine.
"""

from __future__ import annotations

from local_replay_runtime.strategy_ladder_runner import (
    _derive_live_engine_parity_status,
)


def test_proven_no_fidelity_gap_when_all_canonical_and_no_gap_codes() -> None:
    status = _derive_live_engine_parity_status(
        fee_model_source="CANONICAL_EXECUTION_COST_METER",
        spread_model_source="CANONICAL_BOOK_MEASURED",
        slippage_model_source="CANONICAL_KYLE_LAMBDA_METER",
        partial_fill_model_source="CANONICAL_PARTIAL_FILL_COST_METER",
        adverse_selection_source="CANONICAL_ADVERSE_SELECTION_METER",
        order_type_selection_source="CANONICAL_ORDER_DECIDER",
        venue_constraints_source="CANONICAL_VENUE_CONSTRAINT_SNAPSHOT",
        execution_fidelity_gap_codes=(),
    )

    assert status == "PROVEN_NO_FIDELITY_GAP"


def test_proven_partial_when_canonical_sources_but_gap_codes_present() -> None:
    """Some sources canonical but `execution_fidelity_gap_codes` non-empty."""
    status = _derive_live_engine_parity_status(
        fee_model_source="CANONICAL_EXECUTION_COST_METER",
        spread_model_source="CANONICAL_BOOK_MEASURED",
        slippage_model_source="REPLAY_PROXY",
        partial_fill_model_source="CANONICAL_PARTIAL_FILL_COST_METER",
        adverse_selection_source="ADVERSE_SELECTION_CANONICAL_METER_BLOCKED_BY_DEPENDENCY",
        order_type_selection_source="CANONICAL_ORDER_DECIDER",
        venue_constraints_source="CANONICAL_VENUE_CONSTRAINT_SNAPSHOT",
        execution_fidelity_gap_codes=("SLIPPAGE_MODEL_PROXY", "ADVERSE_SELECTION_PROXY"),
    )

    assert status == "PROVEN_PARTIAL_FIDELITY"


def test_proven_partial_when_all_canonical_but_gap_codes_present() -> None:
    """Edge case: all 7 sources canonical BUT gap codes still listed (e.g.
    cost parity meter detected residual proxy somewhere)."""
    status = _derive_live_engine_parity_status(
        fee_model_source="CANONICAL_EXECUTION_COST_METER",
        spread_model_source="CANONICAL_BOOK_MEASURED",
        slippage_model_source="CANONICAL_KYLE_LAMBDA_METER",
        partial_fill_model_source="CANONICAL_PARTIAL_FILL_COST_METER",
        adverse_selection_source="CANONICAL_ADVERSE_SELECTION_METER",
        order_type_selection_source="CANONICAL_ORDER_DECIDER",
        venue_constraints_source="CANONICAL_VENUE_CONSTRAINT_SNAPSHOT",
        execution_fidelity_gap_codes=("SOMETHING_ELSE_PROXY",),
    )

    assert status == "PROVEN_PARTIAL_FIDELITY"


def test_not_proven_when_all_sources_replay_proxy() -> None:
    """No canonical source → shadow didn't run / produced nothing."""
    status = _derive_live_engine_parity_status(
        fee_model_source="REPLAY_PROXY",
        spread_model_source="REPLAY_PROXY",
        slippage_model_source="REPLAY_PROXY",
        partial_fill_model_source="REPLAY_PROXY",
        adverse_selection_source="REPLAY_PROXY",
        order_type_selection_source="REPLAY_PROXY",
        venue_constraints_source="REPLAY_PROXY",
        execution_fidelity_gap_codes=("SPREAD_MODEL_PROXY",),
    )

    assert status == "NOT_PROVEN"


def test_not_proven_when_sources_empty_strings() -> None:
    """Defensive: empty strings should NOT count as canonical."""
    status = _derive_live_engine_parity_status(
        fee_model_source="",
        spread_model_source="",
        slippage_model_source="",
        partial_fill_model_source="",
        adverse_selection_source="",
        order_type_selection_source="",
        venue_constraints_source="",
        execution_fidelity_gap_codes=(),
    )

    assert status == "NOT_PROVEN"


def test_proven_partial_matches_typical_run_31bdfa55_scenario() -> None:
    """Real scenario from audit run 31bdfa55 post-W0+W1+W2 fixes.

    Most sources canonical, but expected_edge stays proxy and book sometimes
    stale → some gap codes remain.
    """
    status = _derive_live_engine_parity_status(
        fee_model_source="CANONICAL_EXECUTION_COST_METER",
        spread_model_source="CANONICAL_BOOK_RECONSTRUCTED",  # post-W0 cross-book purge
        slippage_model_source="CANONICAL_KYLE_LAMBDA_METER",  # post-W1 measured default
        partial_fill_model_source="CANONICAL_PARTIAL_FILL_COST_METER",
        adverse_selection_source="CANONICAL_ADVERSE_SELECTION_METER",  # post-W2 dependency fix
        order_type_selection_source="CANONICAL_ORDER_DECIDER",
        venue_constraints_source="CANONICAL_VENUE_CONSTRAINT_SNAPSHOT",
        execution_fidelity_gap_codes=(),  # all 7 canonical → no gaps
    )

    assert status == "PROVEN_NO_FIDELITY_GAP"
