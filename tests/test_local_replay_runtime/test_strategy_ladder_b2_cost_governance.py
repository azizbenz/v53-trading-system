from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from local_replay_runtime.strategy_ladder_economic_provenance import (
    EconomicProvenance,
)
from local_replay_runtime.strategy_ladder_models import (
    StrategyLadderCandidateEvent,
    StrategyLadderRawWindowManifest,
)
from local_replay_runtime.strategy_ladder_runner import (
    _apply_b2_measured_cost_governance,
    _materialize_native_candidate_event,
)


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    payload = "\n".join(json.dumps(row, sort_keys=True) for row in rows)
    path.write_text(f"{payload}\n" if payload else "", encoding="utf-8")


def _candidate() -> StrategyLadderCandidateEvent:
    return StrategyLadderCandidateEvent(
        candidate_id="cand-b2-cost",
        pair="BTCUSDT",
        timeframe="1m",
        engine_id="engine_b",
        strategy_id="engine_b",
        timestamp_ms=1_700_000_000_000,
        compatibility_payload={
            "side": "buy",
            "entry_price": 100.0,
            "close_price": 100.0,
            "planned_notional": 100.0,
        },
    )


def _window(tmp_path: Path, *, book_timestamp_ms: int) -> StrategyLadderRawWindowManifest:
    snapshot_path = tmp_path / "orderbook_snapshot.jsonl"
    delta_path = tmp_path / "orderbook_delta.jsonl"
    ohlcv_path = tmp_path / "ohlcv.jsonl"
    _write_jsonl(
        snapshot_path,
        [
            {
                "timestamp_ms": book_timestamp_ms - 1_000,
                "update_id": 10,
                "bids": [[99.9, 2.0]],
                "asks": [[100.1, 2.0]],
            }
        ],
    )
    _write_jsonl(
        delta_path,
        [
            {
                "timestamp_ms": book_timestamp_ms,
                "update_id": 11,
                "bids": [[100.0, 2.0]],
                "asks": [[100.1, 2.0]],
            }
        ],
    )
    _write_jsonl(
        ohlcv_path,
        [
            {
                "timestamp_ms": 1_700_000_060_000,
                "open": 100.0,
                "high": 100.8,
                "low": 99.9,
                "close": 100.4,
            }
        ],
    )
    return StrategyLadderRawWindowManifest(
        candidate_id="cand-b2-cost",
        pair="BTCUSDT",
        engine_id="engine_b",
        timestamp_ms=1_700_000_000_000,
        window_start_ms=1_699_999_940_000,
        window_end_ms=1_700_000_600_000,
        raw_trade_path="",
        raw_book_path=str(snapshot_path),
        raw_book_delta_path=str(delta_path),
        raw_ohlcv_path=str(ohlcv_path),
    )


def _base_provenance() -> EconomicProvenance:
    return EconomicProvenance(
        expected_edge_bps=12.0,
        expected_edge_provenance="GOVERNED_ML_ARTIFACT_BACKTEST_TRUTH",
        spread_bps=0.5,
        spread_provenance="DEFAULT_BY_BOOK_STATUS",
        slippage_bps=0.1,
        slippage_provenance="DEFAULT_TO_CALIBRATE",
        latency_penalty_bps=1.5,
        latency_provenance="STATIC_CONSERVATIVE_VENUE_MODEL",
        fee_bps=10.0,
        fee_provenance="MEASURED_FROM_VENUE_METADATA_BYBIT_RESEARCH",
    )


def _engine_output_emit() -> SimpleNamespace:
    return SimpleNamespace(
        decision="emit",
        raw_score=1.0,
        penalized_score=1.0,
        reason_codes=(),
        no_trade_reasons=(),
    )


def test_b2_fresh_depth20_promotes_measured_cost_usage(tmp_path: Path) -> None:
    candidate = _candidate()
    window = _window(tmp_path, book_timestamp_ms=1_700_000_000_000)
    governed = _apply_b2_measured_cost_governance(
        candidate=candidate,
        window=window,
        provenance=_base_provenance(),
        planned_notional=100.0,
    )

    assert governed.spread_provenance == "MEASURED_FROM_BOOK_RECONSTRUCTION"
    assert governed.slippage_provenance == "MEASURED_FROM_DEPTH20_BOOK_WALK"
    assert governed.measured_cost_governance["cost_source_used_for_break_even"] == "measured"
    assert governed.measured_cost_governance["expected_cost_truth_status"] == "FULLY_MEASURED_COST"

    materialized = _materialize_native_candidate_event(
        candidate=candidate,
        window=window,
        economic_provenance=governed,
        builder_status="TEST",
        builder_warnings=(),
        builder_provenance="TEST",
        engine_output=_engine_output_emit(),
        engine_input_payload={},
        build14_application=None,
        records_built=1,
        runner_invoked=True,
    )
    payload = dict(materialized.compatibility_payload or {})
    assert payload["target_decision_state"] == "selected"
    assert payload["cost_source_used_for_break_even"] == "measured"
    assert payload["expected_cost_truth_status"] == "FULLY_MEASURED_COST"
    assert payload["measured_spread_report"]["status"] == "SPREAD_MEASURED_FROM_BOOK"
    assert payload["measured_slippage_report"]["status"] == "SLIPPAGE_ESTIMATED_FROM_DEPTH20"


def test_b2_stale_depth20_hard_blocks_execution_realism(tmp_path: Path) -> None:
    candidate = _candidate()
    window = _window(tmp_path, book_timestamp_ms=1_699_999_994_000)
    governed = _apply_b2_measured_cost_governance(
        candidate=candidate,
        window=window,
        provenance=_base_provenance(),
        planned_notional=100.0,
    )

    assert governed.measured_cost_governance["expected_cost_truth_status"] == "STALE_AUDIT_ONLY_COST"
    assert governed.measured_cost_governance["expected_cost_block_reason"] == "B2_COST_STALE_AUDIT_ONLY"

    materialized = _materialize_native_candidate_event(
        candidate=candidate,
        window=window,
        economic_provenance=governed,
        builder_status="TEST",
        builder_warnings=(),
        builder_provenance="TEST",
        engine_output=_engine_output_emit(),
        engine_input_payload={},
        build14_application=None,
        records_built=1,
        runner_invoked=True,
    )
    payload = dict(materialized.compatibility_payload or {})
    assert payload["target_decision_state"] == "hard_blocked"
    assert "B2_COST_STALE_AUDIT_ONLY" in payload["hard_block_reasons"]
    assert (
        payload["measured_slippage_report"]["status"]
        == "SLIPPAGE_ESTIMATED_FROM_STALE_DEPTH20_AUDIT_ONLY"
    )


def test_b2_missing_depth20_fails_closed_without_proxy_truth() -> None:
    candidate = _candidate()
    governed = _apply_b2_measured_cost_governance(
        candidate=candidate,
        window=None,
        provenance=_base_provenance(),
        planned_notional=100.0,
    )

    assert governed.spread_bps == 0.0
    assert governed.slippage_bps == 0.0
    assert governed.measured_cost_governance["expected_cost_truth_status"] == "COST_MEASUREMENT_BLOCKED"
    assert governed.measured_cost_governance["cost_source_used_for_break_even"] == (
        "blocked_missing_measurement"
    )
    # Updated 2026-05-27 (Patch P0-SPLIT-1) — the legacy
    # `B2_COST_MEASUREMENT_BLOCKED` was split into three granular variants
    # so the operator can tell which side of the measurement is missing
    # (spread, slippage, or both). This test fixture has both spread and
    # slippage missing, so it lands on the `_SPREAD_AND_SLIPPAGE` variant.
    assert governed.measured_cost_governance["expected_cost_block_reason"] == (
        "B2_COST_MEASUREMENT_BLOCKED_SPREAD_AND_SLIPPAGE"
    )
