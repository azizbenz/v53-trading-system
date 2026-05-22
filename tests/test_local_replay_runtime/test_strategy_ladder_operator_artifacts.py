from __future__ import annotations

import json
from pathlib import Path
import shutil
from uuid import uuid4

from local_replay_runtime.strategy_ladder_models import (
    StrategyLadderBucketReplayResult,
    StrategyLadderCandidateEvent,
    StrategyLadderRawWindowManifest,
    StrategyLadderSharedReplayPayload,
)
from local_replay_runtime.strategy_ladder_operator_artifacts import (
    write_strategy_ladder_operator_artifacts,
)


def _scratch_dir(label: str) -> Path:
    repo_root = Path(__file__).resolve().parents[2]
    base_dir = repo_root / ".test_tmp"
    base_dir.mkdir(parents=True, exist_ok=True)
    output_dir = base_dir / f"{label}_{uuid4().hex}"
    output_dir.mkdir(parents=True, exist_ok=False)
    return output_dir


def _load_jsonl_data_rows(path: Path) -> list[dict[str, object]]:
    return [
        payload
        for payload in (
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        )
        if not bool(payload.get("artifact_header"))
    ]


def test_write_strategy_ladder_operator_artifacts_materializes_ledgers() -> None:
    scratch = _scratch_dir("operator_artifacts")
    try:
        run_dir = scratch / "backtest_strategy_ladder" / "run-operator-artifacts"
        candidate_events = (
            StrategyLadderCandidateEvent(
                run_id="run-operator-artifacts",
                candidate_id="cand-executed",
                timestamp_ms=1745884800000,
                pair="BTCUSDT",
                timeframe="5m",
                engine_id="engine_c",
                strategy_id="strategy_ladder",
                compatibility_payload={
                    "side": "buy",
                    "close_price": 100.0,
                    "gross_return_bps": 12.0,
                    "spread_bps": 4.0,
                    "slippage_bps": 3.0,
                    "feature_values": {"ofi": 0.73},
                },
            ),
            StrategyLadderCandidateEvent(
                run_id="run-operator-artifacts",
                candidate_id="cand-phantom",
                timestamp_ms=1745884860000,
                pair="BTCUSDT",
                timeframe="5m",
                engine_id="engine_d",
                strategy_id="strategy_ladder",
                compatibility_payload={
                    "side": "buy",
                    "spread_bps": 5.0,
                    "expected_edge_bps": 8.0,
                },
            ),
        )
        raw_windows = (
            StrategyLadderRawWindowManifest(
                candidate_id="cand-executed",
                pair="BTCUSDT",
                engine_id="engine_c",
                timestamp_ms=1745884800000,
                window_start_ms=1745881200000,
                window_end_ms=1745888400000,
                raw_trade_path="K:/run/trades.jsonl",
                raw_book_path="K:/run/orderbook.jsonl",
                raw_book_delta_path="K:/run/orderbook_delta.jsonl",
                raw_ohlcv_path="K:/run/ohlcv.jsonl",
                book_depth_levels_available=20,
                book_depth_source_status="BOOK_DEPTH20_AVAILABLE",
                window_extraction_status="RAW_WINDOW_READY",
                source_coverage_status="RAW_WINDOW_SOURCE_READY",
            ),
            StrategyLadderRawWindowManifest(
                candidate_id="cand-phantom",
                pair="BTCUSDT",
                engine_id="engine_d",
                timestamp_ms=1745884860000,
                window_start_ms=1745881260000,
                window_end_ms=1745888460000,
                raw_trade_path="K:/run/trades.jsonl",
                raw_book_path="K:/run/orderbook.jsonl",
                raw_book_delta_path="K:/run/orderbook_delta.jsonl",
                raw_ohlcv_path="K:/run/ohlcv.jsonl",
                book_depth_levels_available=20,
                book_depth_source_status="BOOK_DEPTH20_AVAILABLE",
                window_extraction_status="RAW_WINDOW_READY",
                source_coverage_status="RAW_WINDOW_SOURCE_READY",
            ),
        )
        bucket_results = (
            StrategyLadderBucketReplayResult(
                candidate_id="cand-executed",
                pair="BTCUSDT",
                engine_id="engine_c",
                strategy_id="strategy_ladder",
                capital_bucket=400,
                timestamp_ms=1745884800000,
                execution_state="executed",
                executed_notional=100.0,
                executed_only_net_return=0.0012,
                executed_only_net_return_status="EXECUTED_NET_RETURN_PROVEN",
                fee_source_status="FEE_SOURCE_CONFIGURED",
                impact_source_status="IMPACT_SOURCE_DEPTH20_MODEL",
                fill_realism_status="FILL_REALISM_MODEL_ONLY",
                cost_parity_status="REPLAY_LIVE_COST_PARITY_BLOCKED_BY_TELEMETRY",
                book_depth_source_status="BOOK_DEPTH20_AVAILABLE",
                holding_time_ms=60_000,
                mfe_bps=12.0,
                mae_bps=-4.0,
                exit_ref={"timestamp_ms": 1745884860000, "price": 101.0},
                dtr_record={"final_size": 1.0, "realized_cost": 0.2},
                parity_payload={
                    "replay_fee_bps": 1.0,
                    "replay_slippage_bps": 2.0,
                    "replay_impact_bps": 0.5,
                    "measured_spread_report": {"status": "SPREAD_MEASURED_FROM_BOOK"},
                    "measured_slippage_report": {
                        "status": "SLIPPAGE_ESTIMATED_FROM_DEPTH20"
                    },
                    "adverse_selection_report": {
                        "status": "ADVERSE_SELECTION_BLOCKED_BY_NO_ENTRY_REFERENCE"
                    },
                    "fill_realism_report": {"status": "FILL_REALISM_PARTIAL_REPLAY"},
                    "replay_outcome_report": {
                        "status": "REPLAY_OUTCOME_RESEARCH_ONLY"
                    },
                },
            ),
            StrategyLadderBucketReplayResult(
                candidate_id="cand-phantom",
                pair="BTCUSDT",
                engine_id="engine_d",
                strategy_id="strategy_ladder",
                capital_bucket=400,
                timestamp_ms=1745884860000,
                execution_state="phantom",
                no_fill_flag=True,
                expected_ce_net=-0.00023,
                executed_only_net_return_status="EXECUTED_NET_RETURN_INSUFFICIENT_EXECUTIONS",
                fee_source_status="FEE_SOURCE_NOT_PROVEN",
                impact_source_status="IMPACT_SOURCE_DEPTH20_MODEL",
                fill_realism_status="FILL_REALISM_MODEL_ONLY",
                cost_parity_status="REPLAY_LIVE_COST_PARITY_BLOCKED_BY_TELEMETRY",
                book_depth_source_status="BOOK_DEPTH20_AVAILABLE",
                reason_codes=("economically_absurd",),
            ),
        )

        refs = write_strategy_ladder_operator_artifacts(
            run_dir=run_dir,
            candidate_events=candidate_events,
            raw_window_manifests=raw_windows,
            bucket_results=bucket_results,
            replay_artifact_refs={
                "cand-executed": "K:/run/detailed_replay/cand-executed.json",
                "cand-phantom": "K:/run/detailed_replay/cand-phantom.json",
            },
            replay_bucket_refs={
                "cand-executed": ("K:/run/detailed_replay/by_bucket/400/cand-executed.json",),
                "cand-phantom": ("K:/run/detailed_replay/by_bucket/400/cand-phantom.json",),
            },
        )

        assert Path(refs["trade_detail_ledger"]).is_file()
        assert Path(refs["refusal_ledger"]).is_file()
        assert Path(refs["loss_analysis_ledger"]).is_file()
        assert Path(refs["timeframe_matrix"]).is_file()
        assert Path(refs["candidate_replay_window_root"]).is_dir()
        assert Path(refs["closed_episode_journal"]).is_file()
        assert Path(refs["closed_episode_manifest"]).is_file()
        assert Path(refs["measured_spread_report"]).is_file()
        assert Path(refs["measured_slippage_report"]).is_file()
        assert Path(refs["adverse_selection_report"]).is_file()
        assert Path(refs["fill_realism_report"]).is_file()
        assert Path(refs["execution_realism_summary"]).is_file()

        trade_rows = _load_jsonl_data_rows(Path(refs["trade_detail_ledger"]))
        refusal_rows = _load_jsonl_data_rows(Path(refs["refusal_ledger"]))
        timeframe_rows = json.loads(Path(refs["timeframe_matrix"]).read_text(encoding="utf-8"))
        assert len(trade_rows) == 1
        assert trade_rows[0]["candidate_id"] == "cand-executed"
        assert trade_rows[0]["holding_time_seconds"] == 60.0
        assert trade_rows[0]["mfe_bps"] == 12.0
        assert trade_rows[0]["mae_bps"] == -4.0
        assert refusal_rows[0]["candidate_id"] == "cand-phantom"
        assert refusal_rows[0]["refusal_category"] == "phantom"
        assert timeframe_rows[0]["timeframe"] == "5m"
        assert (Path(refs["candidate_replay_window_root"]) / "cand-phantom.json").is_file()
        replay_window_payload = json.loads(
            (Path(refs["candidate_replay_window_root"]) / "cand-phantom.json").read_text(
                encoding="utf-8"
            )
        )
        assert replay_window_payload["raw_book_delta_path"] == "K:/run/orderbook_delta.jsonl"
        closed_episode_manifest = json.loads(
            Path(refs["closed_episode_manifest"]).read_text(encoding="utf-8")
        )
        assert (
            closed_episode_manifest["status"]
            == "CLOSED_EPISODE_JOURNAL_EMPTY_NO_VALID_EPISODES"
        )
        execution_summary = json.loads(
            Path(refs["execution_realism_summary"]).read_text(encoding="utf-8")
        )
        assert execution_summary["spread_status_counts"]["SPREAD_MEASURED_FROM_BOOK"] == 1
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_execution_realism_reports_hydrate_shared_spread_payloads() -> None:
    scratch = _scratch_dir("operator_artifacts_shared_spread")
    try:
        run_dir = scratch / "backtest_strategy_ladder" / "run-shared-spread"
        shared_path = run_dir / "detailed_replay" / "shared" / "cand-shared.json"
        shared_path.parent.mkdir(parents=True, exist_ok=True)
        shared_payload = StrategyLadderSharedReplayPayload(
            candidate_id="cand-shared",
            pair="BTCUSDT",
            engine_id="engine_c",
            strategy_id="strategy_ladder",
            timestamp_ms=1745884800000,
            shared_parity_payload={
                "measured_spread_report": {"status": "SPREAD_MEASURED_FROM_BOOK"},
            },
        )
        shared_path.write_text(
            shared_payload.model_dump_json(indent=2),
            encoding="utf-8",
        )
        candidate_events = (
            StrategyLadderCandidateEvent(
                run_id="run-shared-spread",
                candidate_id="cand-shared",
                timestamp_ms=1745884800000,
                pair="BTCUSDT",
                timeframe="5m",
                engine_id="engine_c",
                strategy_id="strategy_ladder",
                compatibility_payload={"side": "buy"},
            ),
        )
        raw_windows = (
            StrategyLadderRawWindowManifest(
                candidate_id="cand-shared",
                pair="BTCUSDT",
                engine_id="engine_c",
                timestamp_ms=1745884800000,
                window_start_ms=1745881200000,
                window_end_ms=1745888400000,
                raw_trade_path="K:/run/trades.jsonl",
                raw_book_path="K:/run/orderbook.jsonl",
                raw_ohlcv_path="K:/run/ohlcv.jsonl",
                book_depth_source_status="BOOK_DEPTH20_AVAILABLE",
                window_extraction_status="RAW_WINDOW_READY",
                source_coverage_status="RAW_WINDOW_SOURCE_READY",
            ),
        )
        bucket_results = (
            StrategyLadderBucketReplayResult(
                candidate_id="cand-shared",
                pair="BTCUSDT",
                engine_id="engine_c",
                strategy_id="strategy_ladder",
                capital_bucket=400,
                timestamp_ms=1745884800000,
                execution_state="executed",
                fill_realism_status="FILL_REALISM_PARTIAL_REPLAY",
                cost_parity_status="REPLAY_LIVE_COST_PARITY_BLOCKED_BY_TELEMETRY",
                book_depth_source_status="BOOK_DEPTH20_AVAILABLE",
                parity_payload={
                    "measured_slippage_report": {
                        "status": "SLIPPAGE_ESTIMATED_FROM_DEPTH20"
                    }
                },
                shared_payload_ref=str(shared_path.resolve()),
            ),
        )

        refs = write_strategy_ladder_operator_artifacts(
            run_dir=run_dir,
            candidate_events=candidate_events,
            raw_window_manifests=raw_windows,
            bucket_results=bucket_results,
            replay_artifact_refs={"cand-shared": "K:/run/detailed_replay/cand-shared.json"},
            replay_bucket_refs={
                "cand-shared": ("K:/run/detailed_replay/by_bucket/400/cand-shared.json",)
            },
        )

        spread_report = json.loads(
            Path(refs["measured_spread_report"]).read_text(encoding="utf-8")
        )
        assert spread_report["rows"][0]["status"] == "SPREAD_MEASURED_FROM_BOOK"
        execution_summary = json.loads(
            Path(refs["execution_realism_summary"]).read_text(encoding="utf-8")
        )
        assert execution_summary["spread_status_counts"]["SPREAD_MEASURED_FROM_BOOK"] == 1
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
