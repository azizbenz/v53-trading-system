from __future__ import annotations

import json
from pathlib import Path

from local_replay_runtime.strategy_ladder_candidate_trade_semantics_audit import (
    CANDIDATE_THRESHOLD_AUDIT_FILENAME,
    CANDIDATE_TRADE_SEMANTICS_AUDIT_FILENAME,
    CANDIDATE_VS_ENGINE_DECISION_MATRIX_FILENAME,
    write_strategy_ladder_candidate_trade_semantics_audit,
)
from local_replay_runtime.strategy_ladder_gate_waterfall_analysis import (
    GATE_WATERFALL_ANALYSIS_FILENAME,
    write_strategy_ladder_gate_waterfall_reports,
)
from local_replay_runtime.strategy_ladder_models import (
    StrategyLadderBucketReplayResult,
    StrategyLadderCandidateEvent,
    StrategyLadderDetailedReplayArtifact,
    StrategyLadderRawWindowManifest,
    StrategyLadderReportSummary,
    StrategyLadderRunManifest,
    deterministic_payload_hash,
)
from tests.support_paths import make_repo_scratch_dir


def _scratch_dir(label: str) -> Path:
    return make_repo_scratch_dir(
        "strategy_ladder_candidate_trade_semantics_audit_tests",
        label,
    )


def _source_candidate(
    *,
    candidate_id: str,
    engine_id: str,
    timeframe: str,
    timestamp_ms: int,
    score: float,
) -> StrategyLadderCandidateEvent:
    return StrategyLadderCandidateEvent(
        run_id="fixture-run",
        candidate_id=candidate_id,
        timestamp_ms=timestamp_ms,
        pair="BTCUSDT",
        timeframe=timeframe,
        engine_id=engine_id,
        strategy_id=engine_id,
        candidate_source="COMPAT_FEATURE_DISCOVERY",
        feature_refs=(f"fixture://features/{candidate_id}",),
        preliminary_score=score,
        preliminary_reason_codes=(
            "COMPAT_FEATURE_DISCOVERY",
            "NOT_LIVE_ENGINE_PARITY",
        ),
        compatibility_payload={
            "timestamp_ms": timestamp_ms,
            "available_at_timestamp_ms": timestamp_ms - 60_000,
            "final_score": score,
            "feature_values": {"close_return": 0.01},
        },
    )


def _materialized_candidate(
    *,
    candidate_id: str,
    engine_id: str,
    timeframe: str,
    timestamp_ms: int,
    score: float,
    decision: str,
    reason_codes: tuple[str, ...],
    builder_status: str,
) -> StrategyLadderCandidateEvent:
    return StrategyLadderCandidateEvent(
        run_id="fixture-run",
        candidate_id=candidate_id,
        timestamp_ms=timestamp_ms,
        pair="BTCUSDT",
        timeframe=timeframe,
        engine_id=engine_id,
        strategy_id=engine_id,
        candidate_source="ENGINE_NATIVE",
        feature_refs=(f"fixture://features/{candidate_id}",),
        preliminary_score=score,
        preliminary_reason_codes=(
            "ENGINE_NATIVE_RUNNER_INVOKED",
            f"ENGINE_NATIVE_DECISION:{decision.upper()}",
            builder_status,
            *reason_codes,
        ),
        compatibility_payload={
            "timestamp_ms": timestamp_ms,
            "available_at_timestamp_ms": timestamp_ms - 60_000,
            "candidate_source": "ENGINE_NATIVE",
            "candidate_data_source_label": "ENGINE_NATIVE_A_B_C_D_RUNNER",
            "engine_native_decision": decision,
            "engine_native_builder_status": builder_status,
            "engine_native_input_provenance": "BUILDER_TEST_PROVENANCE",
            "hard_block_reasons": list(reason_codes),
            "final_score": score,
            "feature_values": {"close_return": 0.01},
        },
    )


def _write_materialized_candidates(
    run_root: Path,
) -> tuple[StrategyLadderCandidateEvent, ...]:
    rows = (
        _materialized_candidate(
            candidate_id="cand-direction",
            engine_id="engine_a",
            timeframe="1m",
            timestamp_ms=1_735_689_600_000,
            score=0.0,
            decision="no_trade",
            reason_codes=(
                "engine_internal.engine_a.direction.non_long",
                "engine_a.input.non_long_direction",
                "non_long_direction",
            ),
            builder_status="ENGINE_A_INPUT_BUILDER_READY",
        ),
        _materialized_candidate(
            candidate_id="cand-fragility",
            engine_id="engine_c",
            timeframe="5m",
            timestamp_ms=1_735_690_200_000,
            score=0.11,
            decision="no_trade",
            reason_codes=(
                "BUILD14_READER:execution_fragility_score:ELEVATED",
                "BUILD14_READER:false_breakout_model:ELEVATED",
            ),
            builder_status="ENGINE_C_INPUT_BUILDER_READY",
        ),
        _materialized_candidate(
            candidate_id="cand-history",
            engine_id="engine_d",
            timeframe="10m",
            timestamp_ms=1_735_690_500_000,
            score=0.08,
            decision="no_trade",
            reason_codes=(
                "ENGINE_D_HISTORY_BLOCKED_BY_MISSING_CLOSED_EPISODE_JOURNAL",
                "engine_d.no_trade.history_weak",
            ),
            builder_status="ENGINE_D_INPUT_BUILDER_READY_NO_FIRST_EPISODE",
        ),
        _materialized_candidate(
            candidate_id="cand-emit",
            engine_id="engine_b",
            timeframe="15m",
            timestamp_ms=1_735_690_800_000,
            score=0.84,
            decision="emit",
            reason_codes=(),
            builder_status="ENGINE_B_INPUT_BUILDER_READY",
        ),
    )
    target = run_root / "fast_candidates" / "candidate_events.jsonl"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        "\n".join(row.model_dump_json(exclude_none=False) for row in rows) + "\n",
        encoding="utf-8",
    )
    return rows


def _write_raw_windows(run_root: Path) -> None:
    fixtures = (
        ("cand-direction", "engine_a", 1_735_689_600_000),
        ("cand-fragility", "engine_c", 1_735_690_200_000),
        ("cand-history", "engine_d", 1_735_690_500_000),
        ("cand-emit", "engine_b", 1_735_690_800_000),
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


def _result(
    *,
    candidate_id: str,
    engine_id: str,
    timeframe: str,
    timestamp_ms: int,
    execution_state: str,
    reason_codes: tuple[str, ...],
) -> StrategyLadderBucketReplayResult:
    ready_parity = {
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
    return StrategyLadderBucketReplayResult(
        candidate_id=candidate_id,
        pair="BTCUSDT",
        engine_id=engine_id,
        strategy_id=engine_id,
        capital_bucket=400,
        timestamp_ms=timestamp_ms,
        execution_state=execution_state,
        executed_notional=100.0 if execution_state == "executed" else None,
        expected_ce_net=0.0010,
        executed_only_net_return=0.0008 if execution_state == "executed" else None,
        executed_only_net_return_status=(
            "EXECUTED_NET_RETURN_PROVEN"
            if execution_state == "executed"
            else "EXECUTED_NET_RETURN_INSUFFICIENT_EXECUTIONS"
        ),
        fee_source_status="FEE_SOURCE_PROVEN",
        impact_source_status="IMPACT_SOURCE_PROVEN",
        fill_realism_status="FILL_REALISM_PROVEN",
        cost_parity_status="REPLAY_LIVE_COST_PARITY_PROVEN",
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
        exit_ref={
            "reference_type": "post_window_close_proxy",
            "timestamp_ms": timestamp_ms + 60_000,
        },
        reason_codes=reason_codes,
        planned_notional=100.0,
        min_notional=5.0,
        min_notional_viable=True,
        input_data_hash="a" * 64,
        method_version_hash="test.v1",
        dtr_record={"dtr_id": f"{candidate_id}-400:dtr"},
        parity_payload=ready_parity,
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
            "hard_blocked",
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
            "cand-fragility",
            "engine_c",
            "5m",
            1_735_690_200_000,
            "hard_blocked",
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
            "hard_blocked",
            (
                "ENGINE_D_HISTORY_BLOCKED_BY_MISSING_CLOSED_EPISODE_JOURNAL",
                "engine_d.no_trade.history_weak",
            ),
        ),
        (
            "cand-emit",
            "engine_b",
            "15m",
            1_735_690_800_000,
            "executed",
            (),
        ),
    )
    for candidate_id, engine_id, timeframe, timestamp_ms, execution_state, reason_codes in fixtures:
        result = _result(
            candidate_id=candidate_id,
            engine_id=engine_id,
            timeframe=timeframe,
            timestamp_ms=timestamp_ms,
            execution_state=execution_state,
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


def test_candidate_trade_semantics_audit_reports_b1_b2_mismatches() -> None:
    scratch = _scratch_dir("mismatch_audit")
    run_root = scratch / "b2-run"
    source_candidates = (
        _source_candidate(
            candidate_id="cand-direction",
            engine_id="engine_a",
            timeframe="1m",
            timestamp_ms=1_735_689_600_000,
            score=0.0,
        ),
        _source_candidate(
            candidate_id="cand-fragility",
            engine_id="engine_c",
            timeframe="5m",
            timestamp_ms=1_735_690_200_000,
            score=0.11,
        ),
        _source_candidate(
            candidate_id="cand-history",
            engine_id="engine_d",
            timeframe="10m",
            timestamp_ms=1_735_690_500_000,
            score=0.08,
        ),
        _source_candidate(
            candidate_id="cand-emit",
            engine_id="engine_b",
            timeframe="15m",
            timestamp_ms=1_735_690_800_000,
            score=0.84,
        ),
    )
    materialized_candidates = _write_materialized_candidates(run_root)
    _write_raw_windows(run_root)
    _write_replay_artifacts(run_root)

    summary = StrategyLadderReportSummary(
        run_id="fixture-run",
        workflow_run_id="fixture-workflow",
        phase_run_id="phase-b2-fixture",
        candidate_count=4,
        replay_record_count=4,
        final_status="STRATEGY_LADDER_DIAGNOSTIC_FIXTURE",
    )
    run_manifest = StrategyLadderRunManifest(
        run_id="fixture-run",
        workflow_run_id="fixture-workflow",
        phase_run_id="phase-b2-fixture",
        pairs=("BTCUSDT",),
        start="2025-01-01",
        end="2025-01-01",
        executed_trade_count=1,
    )
    write_strategy_ladder_gate_waterfall_reports(
        run_dir=run_root,
        summary=summary,
        run_manifest=run_manifest,
    )

    result = write_strategy_ladder_candidate_trade_semantics_audit(
        run_dir=run_root,
        summary=summary,
        run_manifest=run_manifest,
        source_candidate_events=source_candidates,
        materialized_candidate_events=materialized_candidates,
    )

    assert result.status == "CANDIDATE_TRADE_SEMANTICS_AUDIT_READY"

    audit_payload = _read_json(run_root / "reports" / CANDIDATE_TRADE_SEMANTICS_AUDIT_FILENAME)
    gate_payload = _read_json(run_root / "reports" / GATE_WATERFALL_ANALYSIS_FILENAME)
    assert audit_payload["canonical_selected_count"] == gate_payload["canonical_selected_count"]
    assert audit_payload["canonical_executed_count"] == gate_payload["canonical_executed_count"]

    rows_by_candidate = {
        row["candidate_id"]: row
        for row in audit_payload["rows"]
    }
    assert rows_by_candidate["cand-direction"]["candidate_intent"] == "DISCOVERY_PRE_CANDIDATE"
    assert rows_by_candidate["cand-direction"]["semantic_classification"] == "ENGINE_NATIVE_NO_TRADE"
    assert rows_by_candidate["cand-direction"]["semantic_mismatch_status"] == "B1_MISSING_DIRECTION_GATE"
    assert rows_by_candidate["cand-fragility"]["semantic_mismatch_status"] == "B1_MISSING_FRAGILITY_GATE"
    assert rows_by_candidate["cand-emit"]["semantic_classification"] == "TRADE_ELIGIBLE_CANDIDATE"

    threshold_payload = _read_json(
        run_root / "reports" / CANDIDATE_THRESHOLD_AUDIT_FILENAME
    )
    threshold_rows = {
        row["threshold_key"]: row
        for row in threshold_payload["rows"]
    }
    assert threshold_rows["engine_a_direction_positive"]["threshold_source_status"] == "THRESHOLD_DEFAULT_TO_CALIBRATE"
    assert threshold_rows["engine_a_direction_positive"]["threshold_alignment_status"] == "THRESHOLD_TOO_LOOSE_FOR_B2"

    engine_matrix_payload = _read_json(
        run_root / "reports" / CANDIDATE_VS_ENGINE_DECISION_MATRIX_FILENAME
    )
    engine_rows = {row["engine_id"]: row for row in engine_matrix_payload["rows"]}
    assert "direction_layer" in engine_rows["engine_a"]["missing_b1_gate_coverage"]
    assert engine_rows["engine_b"]["trade_eligible_count"] == 1
