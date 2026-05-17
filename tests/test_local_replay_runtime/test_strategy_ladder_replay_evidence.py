from __future__ import annotations

import json
from pathlib import Path

from local_replay_runtime.strategy_ladder_models import (
    StrategyLadderCandidateEvent,
    StrategyLadderRawWindowManifest,
)
from local_replay_runtime.strategy_ladder_replay_evidence import (
    StrategyLadderReplayEvidenceCache,
    build_strategy_ladder_replay_evidence,
)


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    payload = "\n".join(json.dumps(row, sort_keys=True) for row in rows)
    path.write_text(f"{payload}\n" if payload else "", encoding="utf-8")


def _candidate(*, side: str = "buy") -> StrategyLadderCandidateEvent:
    return StrategyLadderCandidateEvent(
        candidate_id="cand-1",
        pair="BTCUSDT",
        timeframe="1m",
        engine_id="engine_c",
        strategy_id="engine_c",
        timestamp_ms=1_700_000_000_000,
        compatibility_payload={
            "side": side,
            "entry_price": 100.0,
            "close_price": 100.0,
        },
    )


def _window_manifest(
    *,
    tmp_path: Path,
    ohlcv_rows: list[dict[str, object]],
) -> StrategyLadderRawWindowManifest:
    snapshot_path = tmp_path / "orderbook_snapshot.jsonl"
    delta_path = tmp_path / "orderbook_delta.jsonl"
    ohlcv_path = tmp_path / "ohlcv.jsonl"
    _write_jsonl(
        snapshot_path,
        [
            {
                "timestamp_ms": 1_699_999_999_000,
                "update_id": 10,
                "bids": [[99.9, 2.0], [99.8, 3.0]],
                "asks": [[100.1, 2.0], [100.2, 3.0]],
            }
        ],
    )
    _write_jsonl(
        delta_path,
        [
            {
                "timestamp_ms": 1_700_000_000_000,
                "update_id": 11,
                "bids": [[100.0, 2.0]],
                "asks": [[100.1, 2.0]],
            }
        ],
    )
    _write_jsonl(ohlcv_path, ohlcv_rows)
    return StrategyLadderRawWindowManifest(
        candidate_id="cand-1",
        pair="BTCUSDT",
        engine_id="engine_c",
        timestamp_ms=1_700_000_000_000,
        window_start_ms=1_699_999_940_000,
        window_end_ms=1_700_000_600_000,
        raw_trade_path="",
        raw_book_path=str(snapshot_path),
        raw_book_delta_path=str(delta_path),
        raw_ohlcv_path=str(ohlcv_path),
    )


def test_replay_evidence_measures_book_and_marks_proxy_outcome(tmp_path: Path) -> None:
    evidence = build_strategy_ladder_replay_evidence(
        candidate=_candidate(),
        window_manifest=_window_manifest(
            tmp_path=tmp_path,
            ohlcv_rows=[
                {
                    "timestamp_ms": 1_700_000_060_000,
                    "open": 100.0,
                    "high": 101.2,
                    "low": 99.7,
                    "close": 100.8,
                },
                {
                    "timestamp_ms": 1_700_000_120_000,
                    "open": 100.8,
                    "high": 101.8,
                    "low": 100.1,
                    "close": 101.1,
                },
            ],
        ),
        planned_notional=100.0,
        execution_state="executed",
    )

    assert evidence.measured_spread["status"] == "SPREAD_MEASURED_FROM_BOOK"
    assert evidence.measured_spread["best_bid"] == 100.0
    assert evidence.measured_spread["best_ask"] == 100.1
    assert evidence.measured_slippage["status"] == "SLIPPAGE_ESTIMATED_FROM_DEPTH20"
    assert evidence.measured_slippage["side"] == "buy"
    assert evidence.replay_outcome["status"] == "REPLAY_OUTCOME_RESEARCH_ONLY"
    assert evidence.replay_outcome["entry_reference_status"] == "ENTRY_REFERENCE_DECISION_PRICE_PROXY"
    assert evidence.replay_outcome["mfe_mae_status"] == "MFE_MAE_AVAILABLE_PROXY_ENTRY_REFERENCE"
    assert evidence.replay_outcome["holding_time_ms"] == 120000
    assert evidence.replay_outcome["mfe_bps"] is not None
    assert evidence.replay_outcome["mae_bps"] is not None
    assert evidence.adverse_selection["status"] == "ADVERSE_SELECTION_BLOCKED_BY_NO_ENTRY_REFERENCE"
    assert evidence.fill_realism["status"] == "FILL_REALISM_PARTIAL_REPLAY"


def test_replay_evidence_blocks_mfe_mae_without_post_window(tmp_path: Path) -> None:
    evidence = build_strategy_ladder_replay_evidence(
        candidate=_candidate(),
        window_manifest=_window_manifest(
            tmp_path=tmp_path,
            ohlcv_rows=[
                {
                    "timestamp_ms": 1_700_000_000_000,
                    "open": 100.0,
                    "high": 100.1,
                    "low": 99.9,
                    "close": 100.0,
                }
            ],
        ),
        planned_notional=100.0,
        execution_state="hard_blocked",
    )

    assert evidence.replay_outcome["status"] == "REPLAY_OUTCOME_BLOCKED_BY_MISSING_POST_WINDOW"
    assert evidence.replay_outcome["entry_reference_status"] == "ENTRY_REFERENCE_DECISION_PRICE_PROXY"
    assert evidence.replay_outcome["mfe_mae_status"] == "MFE_MAE_BLOCKED_BY_MISSING_POST_WINDOW"
    assert evidence.replay_outcome["mfe_bps"] is None
    assert evidence.replay_outcome["mae_bps"] is None
    assert evidence.adverse_selection["status"] == "ADVERSE_SELECTION_BLOCKED_BY_NO_EXECUTED_TRADES"
    assert evidence.fill_realism["status"] == "FILL_REALISM_NOT_PROVEN"


def test_replay_evidence_marks_unknown_side_without_fabricated_slippage(tmp_path: Path) -> None:
    evidence = build_strategy_ladder_replay_evidence(
        candidate=_candidate(side=""),
        window_manifest=_window_manifest(
            tmp_path=tmp_path,
            ohlcv_rows=[
                {
                    "timestamp_ms": 1_700_000_060_000,
                    "open": 100.0,
                    "high": 100.5,
                    "low": 99.8,
                    "close": 100.2,
                }
            ],
        ),
        planned_notional=100.0,
        execution_state="executed",
    )

    assert evidence.measured_slippage["status"] == "SLIPPAGE_BLOCKED_BY_UNKNOWN_SIDE"
    assert evidence.measured_slippage["walk_cost_bps"] is None
    assert evidence.measured_slippage["impact_bps"] is None


def test_replay_evidence_reuses_book_and_ohlcv_cache_across_bucket_calls(
    monkeypatch, tmp_path: Path
) -> None:
    import local_replay_runtime.strategy_ladder_replay_evidence as evidence_module

    cache = StrategyLadderReplayEvidenceCache()
    counters = {"book": 0, "ohlcv": 0}
    original_resolve_book_state = evidence_module._resolve_book_state
    original_iter_jsonl = evidence_module._iter_jsonl

    def _counted_resolve_book_state(window_manifest, *, decision_timestamp_ms):
        counters["book"] += 1
        return original_resolve_book_state(
            window_manifest,
            decision_timestamp_ms=decision_timestamp_ms,
        )

    def _counted_iter_jsonl(path: Path):
        counters["ohlcv"] += 1
        return original_iter_jsonl(path)

    monkeypatch.setattr(
        evidence_module,
        "_resolve_book_state",
        _counted_resolve_book_state,
    )
    monkeypatch.setattr(evidence_module, "_iter_jsonl", _counted_iter_jsonl)

    manifest = _window_manifest(
        tmp_path=tmp_path,
        ohlcv_rows=[
            {
                "timestamp_ms": 1_700_000_060_000,
                "open": 100.0,
                "high": 101.2,
                "low": 99.7,
                "close": 100.8,
            },
            {
                "timestamp_ms": 1_700_000_120_000,
                "open": 100.8,
                "high": 101.8,
                "low": 100.1,
                "close": 101.1,
            },
        ],
    )

    for planned_notional in (100.0, 250.0, 500.0, 1500.0):
        evidence = build_strategy_ladder_replay_evidence(
            candidate=_candidate(),
            window_manifest=manifest,
            planned_notional=planned_notional,
            execution_state="executed",
            evidence_cache=cache,
        )
        assert evidence.measured_spread["status"] == "SPREAD_MEASURED_FROM_BOOK"
        assert evidence.replay_outcome["status"] == "REPLAY_OUTCOME_RESEARCH_ONLY"

    metrics = cache.metrics_snapshot()
    assert counters["book"] == 1
    assert counters["ohlcv"] == 1
    assert metrics.cache_hits_book_state >= 7
    assert metrics.cache_misses_book_state == 1
    assert metrics.cache_hits_ohlcv >= 3
    assert metrics.cache_misses_ohlcv == 1
