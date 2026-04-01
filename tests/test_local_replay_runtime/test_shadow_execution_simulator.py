"""Tests for the prudent Shadow-compatible execution simulator."""

from __future__ import annotations

from local_replay_runtime import (
    HistoricalReplayDataset,
    HistoricalReplayOpportunity,
    build_parity_diagnostics_payload,
    simulate_shadow_compatible_dtrs,
)


def _dataset() -> HistoricalReplayDataset:
    return HistoricalReplayDataset.from_records(
        dataset_id="dataset-simulator-1",
        source_path="inmemory://simulator",
        records=(
            HistoricalReplayOpportunity(
                opportunity_id="op-1",
                timestamp_ms=1_700_000_000_000,
                pair="BTCUSDT",
                engine_id="engine_a",
                raw_score=0.9,
                penalized_score=0.87,
                final_score=0.84,
                expected_edge_bps=18.0,
                spread_bps=3.0,
                slippage_bps=2.0,
                latency_penalty_bps=1.0,
                fill_ratio=1.0,
                target_decision_state="executed",
                production_decision_state="executed",
                production_final_score=0.84,
                production_expected_cost=0.00063,
                candidate_size=1.0,
                final_size=1.0,
                gross_return_bps=22.0,
                feature_values={"spread_bps": 3.0},
            ),
            HistoricalReplayOpportunity(
                opportunity_id="op-2",
                timestamp_ms=1_700_000_060_000,
                pair="ETHUSDT",
                engine_id="engine_b",
                raw_score=0.75,
                penalized_score=0.7,
                final_score=0.68,
                expected_edge_bps=10.0,
                spread_bps=4.0,
                slippage_bps=2.0,
                latency_penalty_bps=1.0,
                fill_ratio=0.4,
                target_decision_state="executed",
                production_decision_state="reduced",
                production_final_score=0.68,
                production_expected_cost=0.00073,
                candidate_size=1.0,
                final_size=1.0,
                gross_return_bps=10.0,
                feature_values={"spread_bps": 4.0},
            ),
            HistoricalReplayOpportunity(
                opportunity_id="op-3",
                timestamp_ms=1_700_000_120_000,
                pair="SOLUSDT",
                engine_id="engine_a",
                raw_score=0.2,
                final_score=0.1,
                expected_edge_bps=2.0,
                spread_bps=8.0,
                slippage_bps=3.0,
                latency_penalty_bps=2.0,
                target_decision_state="hard_blocked",
                production_decision_state="hard_blocked",
                production_final_score=0.1,
                production_expected_cost=0.00125,
                hard_block_reasons=("ce_negative",),
                primary_reason="ce_negative",
                feature_values={"spread_bps": 8.0},
            ),
        ),
    )


def test_simulate_shadow_compatible_dtrs_applies_prudent_execution_states():
    records = simulate_shadow_compatible_dtrs(_dataset())

    assert len(records) == 3
    assert records[0].decision_state == "executed"
    assert records[1].decision_state == "reduced"
    assert records[1].realized_cost > 0.0
    assert records[2].decision_state == "hard_blocked"
    assert records[2].realized_cost == 0.0


def test_build_parity_diagnostics_payload_reports_ok_when_baselines_match():
    dataset = _dataset()
    records = simulate_shadow_compatible_dtrs(dataset)
    payload = build_parity_diagnostics_payload(dataset, records)

    assert payload["parity_status"] == "ok"
    assert payload["decision_match_rate"] == 1.0
    assert payload["cost_alignment"] == "within_prudent_tolerance"
