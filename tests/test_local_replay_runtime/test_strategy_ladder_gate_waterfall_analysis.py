from __future__ import annotations

import json
from pathlib import Path

from local_replay_runtime.strategy_ladder_gate_waterfall_analysis import (
    write_strategy_ladder_gate_waterfall_reports,
)
from local_replay_runtime.strategy_ladder_models import (
    StrategyLadderBucketReplayResult,
    StrategyLadderDetailedReplayArtifact,
    StrategyLadderRawWindowManifest,
    StrategyLadderReportSummary,
    StrategyLadderRunManifest,
    deterministic_payload_hash,
)
from tests.support_paths import make_repo_scratch_dir


def _scratch_dir(label: str) -> Path:
    return make_repo_scratch_dir("strategy_ladder_gate_waterfall_analysis_tests", label)


def _write_candidate_events(run_root: Path) -> None:
    rows = [
        {
            "schema_version": "v1",
            "run_id": "fixture-run",
            "candidate_id": "cand-direction",
            "timestamp_ms": 1_735_689_600_000,
            "pair": "BTCUSDT",
            "timeframe": "1m",
            "engine_id": "engine_a",
            "strategy_id": "engine_a",
            "feature_refs": ["fixture://features/cand-direction"],
            "compatibility_payload": {
                "timestamp_ms": 1_735_689_600_000,
                "available_at_timestamp_ms": 1_735_689_540_000,
                "spread_bps": 0.5,
                "slippage_bps": 0.1,
                "break_even_bps": 7.0,
                "feature_values": {"close_return": 0.01},
            },
        },
        {
            "schema_version": "v1",
            "run_id": "fixture-run",
            "candidate_id": "cand-expected-edge",
            "timestamp_ms": 1_735_689_900_000,
            "pair": "BTCUSDT",
            "timeframe": "15m",
            "engine_id": "engine_b",
            "strategy_id": "engine_b",
            "feature_refs": ["fixture://features/cand-expected-edge"],
            "compatibility_payload": {
                "timestamp_ms": 1_735_689_900_000,
                "available_at_timestamp_ms": 1_735_689_840_000,
                "spread_bps": 0.4,
                "slippage_bps": 0.1,
                "break_even_bps": 6.0,
                "feature_values": {"close_return": 0.02},
            },
        },
        {
            "schema_version": "v1",
            "run_id": "fixture-run",
            "candidate_id": "cand-fragility",
            "timestamp_ms": 1_735_690_200_000,
            "pair": "BTCUSDT",
            "timeframe": "5m",
            "engine_id": "engine_c",
            "strategy_id": "engine_c",
            "feature_refs": ["fixture://features/cand-fragility"],
            "compatibility_payload": {
                "timestamp_ms": 1_735_690_200_000,
                "available_at_timestamp_ms": 1_735_690_140_000,
                "spread_bps": 0.3,
                "slippage_bps": 0.1,
                "break_even_bps": 6.0,
                "feature_values": {"close_return": 0.03},
            },
        },
        {
            "schema_version": "v1",
            "run_id": "fixture-run",
            "candidate_id": "cand-history",
            "timestamp_ms": 1_735_690_500_000,
            "pair": "BTCUSDT",
            "timeframe": "10m",
            "engine_id": "engine_d",
            "strategy_id": "engine_d",
            "feature_refs": ["fixture://features/cand-history"],
            "compatibility_payload": {
                "timestamp_ms": 1_735_690_500_000,
                "available_at_timestamp_ms": 1_735_690_440_000,
                "spread_bps": 0.3,
                "slippage_bps": 0.1,
                "break_even_bps": 6.0,
                "feature_values": {"close_return": 0.04},
            },
        },
    ]
    path = run_root / "fast_candidates" / "candidate_events.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(row, separators=(",", ":")) for row in rows) + "\n",
        encoding="utf-8",
    )


def _write_raw_windows(run_root: Path) -> None:
    fixtures = (
        ("cand-direction", "engine_a", 1_735_689_600_000),
        ("cand-expected-edge", "engine_b", 1_735_689_900_000),
        ("cand-fragility", "engine_c", 1_735_690_200_000),
        ("cand-history", "engine_d", 1_735_690_500_000),
    )
    for candidate_id, engine_id, timestamp_ms in fixtures:
        manifest = StrategyLadderRawWindowManifest(
            candidate_id=candidate_id,
            pair="BTCUSDT",
            engine_id=engine_id,
            timestamp_ms=timestamp_ms,
            window_start_ms=timestamp_ms - 300_000,
            window_end_ms=timestamp_ms + 300_000,
            raw_trade_path="fixture://trades",
            raw_book_path="fixture://book",
            raw_ohlcv_path="fixture://ohlcv",
            raw_metadata_path="fixture://metadata",
            book_depth_levels_available=20,
            book_depth_source_status="BOOK_DEPTH20_AVAILABLE",
            window_extraction_status="RAW_WINDOW_READY",
            raw_sources_used=("trades", "orderbook", "klines", "metadata"),
            source_coverage_status="RAW_WINDOW_SOURCE_COVERAGE_COMPLETE",
            input_data_hash="1" * 64,
        ).model_copy(
            update={
                "artifact_hash": deterministic_payload_hash(
                    {"candidate_id": candidate_id, "timestamp_ms": timestamp_ms}
                )
            }
        )
        target = run_root / "raw_windows" / "BTCUSDT" / candidate_id / "window_manifest.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")


def _replay_result(
    *,
    candidate_id: str,
    engine_id: str,
    timeframe: str,
    timestamp_ms: int,
    reason_codes: tuple[str, ...],
) -> StrategyLadderBucketReplayResult:
    parity = {
        "measured_spread_report": {"status": "SPREAD_MEASURED_FROM_BOOK"},
        "measured_slippage_report": {"status": "SLIPPAGE_ESTIMATED_FROM_DEPTH20"},
        "adverse_selection_report": {"status": "ADVERSE_SELECTION_READY"},
        "fill_realism_report": {"status": "FILL_REALISM_PROVEN"},
        "replay_outcome_report": {
            "status": "REPLAY_OUTCOME_RESEARCH_ONLY",
            "entry_reference_status": "ENTRY_REFERENCE_DECISION_PRICE_PROXY",
            "mfe_mae_status": "MFE_MAE_AVAILABLE_PROXY_ENTRY_REFERENCE",
            "holding_time_ms": 60_000,
            "forward_return_h1": 1.0,
            "forward_return_h5": 2.0,
            "forward_return_h10": 3.0,
            "mfe_bps": 5.0,
            "mae_bps": -2.0,
        },
    }
    if candidate_id == "cand-direction":
        parity["adverse_selection_report"] = {
            "status": "ADVERSE_SELECTION_BLOCKED_BY_NO_EXECUTED_TRADES"
        }
        parity["fill_realism_report"] = {"status": "FILL_REALISM_NOT_PROVEN"}
    return StrategyLadderBucketReplayResult(
        candidate_id=candidate_id,
        pair="BTCUSDT",
        engine_id=engine_id,
        strategy_id=engine_id,
        capital_bucket=400,
        timestamp_ms=timestamp_ms,
        execution_state="hard_blocked",
        expected_ce_net=0.0005,
        executed_only_net_return=None,
        executed_only_net_return_status="EXECUTED_NET_RETURN_INSUFFICIENT_EXECUTIONS",
        fee_source_status="MEASURED_FROM_VENUE_METADATA_BYBIT_RESEARCH",
        impact_source_status="IMPACT_SOURCE_DEPTH20_MODEL",
        fill_realism_status=str(parity["fill_realism_report"]["status"]),
        cost_parity_status="REPLAY_LIVE_COST_PARITY_BLOCKED_BY_TELEMETRY",
        book_depth_source_status="BOOK_DEPTH20_AVAILABLE",
        impact_depth_readiness_status="DEPTH20_AVAILABLE",
        replay_outcome_status="REPLAY_OUTCOME_RESEARCH_ONLY",
        entry_reference_status="ENTRY_REFERENCE_DECISION_PRICE_PROXY",
        mfe_mae_status="MFE_MAE_AVAILABLE_PROXY_ENTRY_REFERENCE",
        holding_time_ms=60_000,
        forward_return_h1=1.0,
        forward_return_h5=2.0,
        forward_return_h10=3.0,
        mfe_bps=5.0,
        mae_bps=-2.0,
        entry_ref={"reference_type": "decision_price_proxy", "timestamp_ms": timestamp_ms},
        exit_ref={"reference_type": "post_window_close_proxy", "timestamp_ms": timestamp_ms + 60_000},
        reason_codes=reason_codes,
        planned_notional=100.0,
        min_notional=5.0,
        min_notional_viable=True,
        input_data_hash="a" * 64,
        method_version_hash="test.v1",
        dtr_record={"dtr_id": f"{candidate_id}-400:dtr"},
        parity_payload=parity,
    ).model_copy(
        update={
            "artifact_hash": deterministic_payload_hash(
                {"candidate_id": candidate_id, "engine_id": engine_id, "timeframe": timeframe}
            )
        }
    )


def _write_replay_artifacts(run_root: Path) -> None:
    replay_root = run_root / "detailed_replay"
    replay_root.mkdir(parents=True, exist_ok=True)
    fixtures = (
        (
            "cand-direction",
            "engine_a",
            "1m",
            1_735_689_600_000,
            (
                "EXPECTED_EDGE_NOT_GOVERNED_FOR_BACKTEST_TRUTH",
                "EXPECTED_EDGE_PROXY_BLOCKED",
                "BREAK_EVEN_PROXY_BLOCKED",
                "FEE_AWARE_EDGE_PROXY_BLOCKED",
                "engine_a.input.non_long_direction",
                "non_long_direction",
            ),
        ),
        (
            "cand-expected-edge",
            "engine_b",
            "15m",
            1_735_689_900_000,
            (
                "EXPECTED_EDGE_NOT_GOVERNED_FOR_BACKTEST_TRUTH",
                "EXPECTED_EDGE_PROXY_BLOCKED",
            ),
        ),
        (
            "cand-fragility",
            "engine_c",
            "5m",
            1_735_690_200_000,
            (
                "BUILD14_READER:execution_fragility_score:ELEVATED",
                "BUILD14_READER:false_breakout_model:ELEVATED",
            ),
        ),
        (
            "cand-history",
            "engine_d",
            "10m",
            1_735_690_500_000,
            (
                "ENGINE_D_HISTORY_BLOCKED_BY_MISSING_CLOSED_EPISODE_JOURNAL",
                "engine_d.no_trade.history_weak",
            ),
        ),
    )
    for candidate_id, engine_id, timeframe, timestamp_ms, reason_codes in fixtures:
        result = _replay_result(
            candidate_id=candidate_id,
            engine_id=engine_id,
            timeframe=timeframe,
            timestamp_ms=timestamp_ms,
            reason_codes=reason_codes,
        )
        artifact = StrategyLadderDetailedReplayArtifact(
            candidate_id=candidate_id,
            pair="BTCUSDT",
            engine_id=engine_id,
            strategy_id=engine_id,
            timestamp_ms=timestamp_ms,
            detailed_replay_status="DETAILED_REPLAY_READY",
            bucket_results=(result,),
            bucket_result_refs=(f"fixture://bucket/{candidate_id}",),
            input_data_hash="b" * 64,
            method_version_hash="test.v1",
        ).model_copy(
            update={
                "artifact_hash": deterministic_payload_hash(
                    {"candidate_id": candidate_id, "engine_id": engine_id}
                )
            }
        )
        (replay_root / f"{candidate_id}.json").write_text(
            artifact.model_dump_json(indent=2),
            encoding="utf-8",
        )


def _read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _build_reports(run_root: Path):
    summary = StrategyLadderReportSummary(
        run_id="fixture-run",
        workflow_run_id="fixture-workflow",
        phase_run_id="phase-b2-fixture",
        candidate_count=4,
        replay_record_count=4,
        final_status="STRATEGY_LADDER_BLOCKED_BY_NO_EXECUTED_TRADES",
    )
    run_manifest = StrategyLadderRunManifest(
        run_id="fixture-run",
        workflow_run_id="fixture-workflow",
        phase_run_id="phase-b2-fixture",
        pairs=("BTCUSDT",),
        start="2025-01-01",
        end="2025-01-01",
        executed_trade_count=0,
    )
    return write_strategy_ladder_gate_waterfall_reports(
        run_dir=run_root,
        summary=summary,
        run_manifest=run_manifest,
    )


def test_gate_waterfall_analysis_deterministic_and_counterfactual() -> None:
    scratch = _scratch_dir("deterministic")
    run_root = scratch / "b2-run"
    _write_candidate_events(run_root)
    _write_raw_windows(run_root)
    _write_replay_artifacts(run_root)

    result = _build_reports(run_root)

    assert result.status == "GATE_WATERFALL_ANALYSIS_READY"
    assert result.canonical_selected_count == 0
    assert result.canonical_executed_count == 0
    assert result.best_counterfactual_survival_count == 1

    waterfall = _read_json(run_root / "reports" / "gate_waterfall_analysis.json")
    assert waterfall["status"] == "GATE_WATERFALL_ANALYSIS_READY"
    assert waterfall["canonical_selected_count"] == 0
    assert waterfall["canonical_executed_count"] == 0

    funnel_rows = waterfall["funnel_metrics"]
    assert [row["gate_id"] for row in funnel_rows] == [
        "direction_layer",
        "structure_layer",
        "fragility_layer",
        "microstructure_layer",
        "expected_edge_layer",
        "break_even_layer",
        "fee_aware_edge_layer",
        "spread_slippage_realism_layer",
        "adverse_selection_layer",
        "fill_realism_layer",
        "governance_promotion_layer",
    ]

    matrix = _read_json(run_root / "reports" / "gate_counterfactual_matrix.json")
    rows_by_candidate = {row["candidate_id"]: row for row in matrix["rows"]}
    assert rows_by_candidate["cand-direction"]["first_blocking_gate"] == "direction_layer"
    assert rows_by_candidate["cand-expected-edge"]["first_blocking_gate"] == "expected_edge_layer"
    assert rows_by_candidate["cand-fragility"]["first_blocking_gate"] == "fragility_layer"
    assert rows_by_candidate["cand-history"]["first_blocking_gate"] == "governance_promotion_layer"
    assert rows_by_candidate["cand-expected-edge"]["would_survive_if_expected_edge_governed"] is True
    assert rows_by_candidate["cand-fragility"]["would_survive_if_engine_c_fragility_relaxed"] is True
    assert rows_by_candidate["cand-history"]["would_survive_if_engine_d_history_available"] is True

    scenarios = {
        row["scenario_id"]: row
        for row in waterfall["scenario_summaries"]
    }
    assert scenarios["expected_edge_governed"]["counterfactual_survival_count"] == 1
    assert scenarios["engine_c_fragility_relaxed"]["counterfactual_survival_count"] == 1
    assert scenarios["engine_d_history_available"]["counterfactual_survival_count"] == 1


def test_gate_waterfall_generates_engine_timeframe_and_readiness_reports() -> None:
    scratch = _scratch_dir("readiness")
    run_root = scratch / "b2-run"
    _write_candidate_events(run_root)
    _write_raw_windows(run_root)
    _write_replay_artifacts(run_root)

    _build_reports(run_root)

    by_engine = _read_json(run_root / "reports" / "gate_counterfactual_by_engine.json")
    engine_rows = {row["engine_id"]: row for row in by_engine["rows"]}
    assert engine_rows["engine_c"]["dominant_blocking_gate"] == "fragility_layer"
    assert engine_rows["engine_c"]["counterfactual_survival_count"] == 1
    assert engine_rows["engine_d"]["best_counterfactual_scenario"] == "engine_d_history_available"

    by_timeframe = _read_json(run_root / "reports" / "gate_counterfactual_by_timeframe.json")
    timeframes = {row["timeframe"] for row in by_timeframe["rows"]}
    assert timeframes == {"1m", "5m", "10m", "15m"}

    readiness = _read_json(run_root / "reports" / "expected_edge_readiness_audit.json")
    assert readiness["status"] == "EXPECTED_EDGE_READINESS_AUDIT_READY"
    assert readiness["verdict"] == "EXPECTED_EDGE_TRAINING_RESEARCH_ONLY_ALLOWED"
    assert readiness["anti_leakage_path_status"] == "ANTI_LEAKAGE_PATH_READY"
    assert readiness["counterfactual_uplift_status"] == "EXPECTED_EDGE_COUNTERFACTUAL_UPLIFT_PRESENT"
