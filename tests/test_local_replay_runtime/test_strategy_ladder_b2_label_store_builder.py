from __future__ import annotations

import json
from pathlib import Path

from local_replay_runtime.strategy_ladder_b2_label_store_builder import (
    LABEL_STORE_QUALITY_REPORT_FILENAME,
    LABEL_STORE_SUMMARY_FILENAME,
    StrategyLadderB2LabelStoreBuilderRequest,
    StrategyLadderB2LabelStoreQualityReport,
    StrategyLadderB2LabelStoreRow,
    StrategyLadderB2LabelStoreSummary,
    build_strategy_ladder_b2_label_store,
)
from local_replay_runtime.strategy_ladder_models import (
    StrategyLadderBucketReplayResult,
    StrategyLadderDetailedReplayArtifact,
    StrategyLadderRawWindowManifest,
    StrategyLadderSharedReplayPayload,
    deterministic_payload_hash,
)
from tests.support_paths import make_repo_scratch_dir


def _scratch_dir(label: str) -> Path:
    return make_repo_scratch_dir("strategy_ladder_b2_label_store_builder_tests", label)


def _write_candidate_events(run_root: Path) -> None:
    candidate_events_path = run_root / "fast_candidates" / "candidate_events.jsonl"
    candidate_events_path.parent.mkdir(parents=True, exist_ok=True)
    rows = [
        {
            "schema_version": "v1",
            "run_id": "fixture-run",
            "candidate_id": "cand-exec",
            "timestamp_ms": 1_735_689_600_000,
            "pair": "BTCUSDT",
            "timeframe": "5m",
            "engine_id": "engine_a",
            "strategy_id": "engine_a",
            "feature_refs": ["fixture://features/cand-exec"],
            "compatibility_payload": {
                "timestamp_ms": 1_735_689_600_000,
                "available_at_timestamp_ms": 1_735_689_540_000,
                "spread_bps": 4.0,
                "slippage_bps": 2.0,
                "break_even_bps": 7.0,
                "feature_values": {
                    "close_return": 0.01,
                    "high_low_range": 0.02,
                    "volume": 100.0,
                },
            },
        },
        {
            "schema_version": "v1",
            "run_id": "fixture-run",
            "candidate_id": "cand-proxy",
            "timestamp_ms": 1_735_775_000_000,
            "pair": "BTCUSDT",
            "timeframe": "5m",
            "engine_id": "engine_b",
            "strategy_id": "engine_b",
            "feature_refs": ["fixture://features/cand-proxy"],
            "compatibility_payload": {
                "timestamp_ms": 1_735_775_000_000,
                "available_at_timestamp_ms": 1_735_774_940_000,
                "spread_bps": 3.0,
                "slippage_bps": 1.5,
                "break_even_bps": 8.0,
                "feature_values": {
                    "close_return": -0.02,
                    "high_low_range": 0.04,
                    "volume": 150.0,
                },
            },
        },
    ]
    candidate_events_path.write_text(
        "\n".join(json.dumps(row, separators=(",", ":")) for row in rows) + "\n",
        encoding="utf-8",
    )


def _raw_window_manifest(candidate_id: str, timestamp_ms: int) -> StrategyLadderRawWindowManifest:
    return StrategyLadderRawWindowManifest(
        candidate_id=candidate_id,
        pair="BTCUSDT",
        engine_id="engine_a" if candidate_id == "cand-exec" else "engine_b",
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
                {
                    "candidate_id": candidate_id,
                    "timestamp_ms": timestamp_ms,
                }
            )
        }
    )


def _write_raw_windows(run_root: Path) -> None:
    for candidate_id, timestamp_ms in (
        ("cand-exec", 1_735_689_600_000),
        ("cand-proxy", 1_735_775_000_000),
    ):
        manifest = _raw_window_manifest(candidate_id, timestamp_ms)
        target = run_root / "raw_windows" / "BTCUSDT" / candidate_id / "window_manifest.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")


def _write_replay_artifacts(run_root: Path) -> None:
    replay_root = run_root / "detailed_replay"
    replay_root.mkdir(parents=True, exist_ok=True)
    shared_root = replay_root / "shared"
    shared_root.mkdir(parents=True, exist_ok=True)
    by_bucket_root = replay_root / "by_bucket"
    by_bucket_root.mkdir(parents=True, exist_ok=True)
    exec_shared_path = (shared_root / "cand-exec.json").resolve()
    exec_shared_payload = StrategyLadderSharedReplayPayload(
        candidate_id="cand-exec",
        pair="BTCUSDT",
        engine_id="engine_a",
        strategy_id="engine_a",
        timestamp_ms=1_735_689_600_000,
        window_start_ms=1_735_689_300_000,
        window_end_ms=1_735_689_900_000,
        raw_trade_path="fixture://trades",
        raw_book_path="fixture://book",
        raw_ohlcv_path="fixture://ohlcv",
        raw_metadata_path="fixture://metadata",
        raw_sources_used=("trades", "orderbook", "klines", "metadata"),
        book_depth_levels_available=20,
        book_depth_source_status="BOOK_DEPTH20_AVAILABLE",
        source_coverage_status="RAW_WINDOW_SOURCE_COVERAGE_COMPLETE",
        shared_parity_payload={
            "replay_outcome_report": {
                "entry_reference_status": "ENTRY_REFERENCE_DECISION_PRICE_PROXY",
                "mfe_mae_status": "MFE_MAE_AVAILABLE_PROXY_ENTRY_REFERENCE",
            }
        },
        input_data_hash="1" * 64,
        method_version_hash="test.v1",
    ).model_copy(
        update={"artifact_hash": deterministic_payload_hash({"candidate_id": "cand-exec", "shared": True})}
    )
    exec_shared_path.write_text(
        exec_shared_payload.model_dump_json(indent=2),
        encoding="utf-8",
    )
    exec_result = StrategyLadderBucketReplayResult(
        candidate_id="cand-exec",
        pair="BTCUSDT",
        engine_id="engine_a",
        strategy_id="engine_a",
        capital_bucket=400,
        timestamp_ms=1_735_689_600_000,
        execution_state="executed",
        executed_notional=100.0,
        expected_ce_net=0.0010,
        executed_only_net_return=0.0008,
        executed_only_net_return_status="EXECUTED_NET_RETURN_PROVEN",
        fee_source_status="FEE_SOURCE_PROVEN",
        impact_source_status="IMPACT_SOURCE_PROVEN",
        fill_realism_status="FILL_REALISM_PROVEN",
        cost_parity_status="REPLAY_LIVE_COST_PARITY_PROVEN",
        book_depth_source_status="BOOK_DEPTH20_AVAILABLE",
        impact_depth_readiness_status="DEPTH20_AVAILABLE",
        dtr_record={
            "dtr_id": "cand-exec-400:dtr",
            "gross_return": 0.0015,
        },
        parity_payload={
            "replay_fee_bps": 1.2,
            "replay_slippage_bps": 0.8,
            "adverse_selection_bps": 0.4,
            "holding_time_ms": 60_000,
            "mfe_bps": 18.0,
            "mae_bps": -6.0,
            "forward_return_h1": 10.0,
            "forward_return_h5": 12.0,
            "forward_return_h10": 15.0,
        },
        shared_payload_ref=str(exec_shared_path),
    )
    exec_result = exec_result.model_copy(
        update={"artifact_hash": deterministic_payload_hash(exec_result.model_dump(mode="json"))}
    )
    exec_bucket_path = (by_bucket_root / "400" / "cand-exec.json").resolve()
    exec_bucket_path.parent.mkdir(parents=True, exist_ok=True)
    exec_bucket_path.write_text(
        exec_result.model_dump_json(indent=2),
        encoding="utf-8",
    )
    exec_artifact = StrategyLadderDetailedReplayArtifact(
        candidate_id="cand-exec",
        pair="BTCUSDT",
        engine_id="engine_a",
        strategy_id="engine_a",
        timestamp_ms=1_735_689_600_000,
        detailed_replay_status="DETAILED_REPLAY_READY",
        bucket_results=(),
        bucket_result_refs=(str(exec_bucket_path),),
        shared_payload_ref=str(exec_shared_path),
        input_data_hash="1" * 64,
        method_version_hash="test.v1",
    ).model_copy(
        update={"artifact_hash": deterministic_payload_hash({"candidate_id": "cand-exec"})}
    )
    (replay_root / "cand-exec.json").write_text(
        exec_artifact.model_dump_json(indent=2),
        encoding="utf-8",
    )

    proxy_shared_path = (shared_root / "cand-proxy.json").resolve()
    proxy_shared_payload = StrategyLadderSharedReplayPayload(
        candidate_id="cand-proxy",
        pair="BTCUSDT",
        engine_id="engine_b",
        strategy_id="engine_b",
        timestamp_ms=1_735_775_000_000,
        window_start_ms=1_735_774_700_000,
        window_end_ms=1_735_775_300_000,
        raw_trade_path="fixture://trades",
        raw_book_path="fixture://book",
        raw_ohlcv_path="fixture://ohlcv",
        raw_metadata_path="fixture://metadata",
        raw_sources_used=("trades", "orderbook", "klines", "metadata"),
        book_depth_levels_available=20,
        book_depth_source_status="BOOK_DEPTH20_AVAILABLE",
        source_coverage_status="RAW_WINDOW_SOURCE_COVERAGE_COMPLETE",
        shared_parity_payload={
            "replay_outcome_report": {
                "entry_reference_status": "ENTRY_REFERENCE_NOT_AVAILABLE",
                "mfe_mae_status": "MFE_MAE_BLOCKED_BY_NO_ENTRY_REFERENCE",
            }
        },
        input_data_hash="2" * 64,
        method_version_hash="test.v1",
    ).model_copy(
        update={"artifact_hash": deterministic_payload_hash({"candidate_id": "cand-proxy", "shared": True})}
    )
    proxy_shared_path.write_text(
        proxy_shared_payload.model_dump_json(indent=2),
        encoding="utf-8",
    )
    proxy_result = StrategyLadderBucketReplayResult(
        candidate_id="cand-proxy",
        pair="BTCUSDT",
        engine_id="engine_b",
        strategy_id="engine_b",
        capital_bucket=500,
        timestamp_ms=1_735_775_000_000,
        execution_state="phantom",
        no_fill_flag=True,
        expected_ce_net=0.0003,
        executed_only_net_return=None,
        executed_only_net_return_status="EXECUTED_NET_RETURN_INSUFFICIENT_EXECUTIONS",
        fee_source_status="FEE_SOURCE_NOT_PROVEN",
        impact_source_status="IMPACT_SOURCE_DEPTH20_MODEL",
        fill_realism_status="FILL_REALISM_MODEL_ONLY",
        cost_parity_status="REPLAY_LIVE_COST_PARITY_BLOCKED_BY_TELEMETRY",
        book_depth_source_status="BOOK_DEPTH20_AVAILABLE",
        impact_depth_readiness_status="DEPTH20_AVAILABLE",
        dtr_record={"dtr_id": "cand-proxy-500:dtr"},
        parity_payload={},
        shared_payload_ref=str(proxy_shared_path),
    )
    proxy_result = proxy_result.model_copy(
        update={"artifact_hash": deterministic_payload_hash(proxy_result.model_dump(mode="json"))}
    )
    proxy_bucket_path = (by_bucket_root / "500" / "cand-proxy.json").resolve()
    proxy_bucket_path.parent.mkdir(parents=True, exist_ok=True)
    proxy_bucket_path.write_text(
        proxy_result.model_dump_json(indent=2),
        encoding="utf-8",
    )
    proxy_artifact = StrategyLadderDetailedReplayArtifact(
        candidate_id="cand-proxy",
        pair="BTCUSDT",
        engine_id="engine_b",
        strategy_id="engine_b",
        timestamp_ms=1_735_775_000_000,
        detailed_replay_status="DETAILED_REPLAY_READY",
        bucket_results=(),
        bucket_result_refs=(str(proxy_bucket_path),),
        shared_payload_ref=str(proxy_shared_path),
        input_data_hash="2" * 64,
        method_version_hash="test.v1",
    ).model_copy(
        update={"artifact_hash": deterministic_payload_hash({"candidate_id": "cand-proxy"})}
    )
    (replay_root / "cand-proxy.json").write_text(
        proxy_artifact.model_dump_json(indent=2),
        encoding="utf-8",
    )


def test_b2_label_store_builder_propagates_grounded_and_proxy_rows() -> None:
    scratch = _scratch_dir("propagation")
    run_root = scratch / "b2-run"
    output_dir = scratch / "label-store"
    _write_candidate_events(run_root)
    _write_raw_windows(run_root)
    _write_replay_artifacts(run_root)

    result = build_strategy_ladder_b2_label_store(
        StrategyLadderB2LabelStoreBuilderRequest(
            run_root=run_root,
            output_dir=output_dir,
        )
    )

    assert result.status == "LABEL_STORE_PARTIAL_PROXY_EXECUTION"
    assert result.promotion_state == "LABEL_STORE_RESEARCH_ONLY"
    assert result.replay_grounded_label_count == 1
    assert result.proxy_execution_label_count == 1

    dataset_path = output_dir / "strategy_ladder_b2_label_store.jsonl"
    rows = [
        StrategyLadderB2LabelStoreRow.model_validate_json(line)
        for line in dataset_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(rows) == 2

    exec_row = next(row for row in rows if row.candidate_id == "cand-exec")
    assert exec_row.feature_timestamp_ms <= exec_row.decision_timestamp_ms
    assert exec_row.mfe_bps == 18.0
    assert exec_row.mae_bps == -6.0
    assert exec_row.holding_time_ms == 60_000
    assert exec_row.label_forward_return_h1 == 10.0
    assert exec_row.label_forward_return_h5 == 12.0
    assert exec_row.label_forward_return_h10 == 15.0
    assert exec_row.fee_bps == 1.2
    assert exec_row.slippage_bps == 0.8
    assert exec_row.adverse_selection_bps == 0.4
    assert exec_row.evidence_class == "REPLAY_EXECUTED_ONLY_NET_RETURN"
    assert exec_row.execution_fidelity_status == "EXECUTION_FIDELITY_READY"
    assert exec_row.replay_grounded_label_flag is True
    assert exec_row.proxy_execution_label_flag is False
    assert exec_row.label_quality_status == "LABEL_QUALITY_RESEARCH_ONLY"
    assert exec_row.replay_grounded_status == "REPLAY_GROUNDED_PARTIAL"
    assert exec_row.entry_reference_status == "ENTRY_REFERENCE_DECISION_PRICE_PROXY"
    assert exec_row.mfe_mae_status == "MFE_MAE_AVAILABLE_PROXY_ENTRY_REFERENCE"

    proxy_row = next(row for row in rows if row.candidate_id == "cand-proxy")
    assert proxy_row.feature_timestamp_ms <= proxy_row.decision_timestamp_ms
    assert proxy_row.evidence_class == "REPLAY_EXPECTED_CE_NET_PROXY"
    assert proxy_row.execution_fidelity_status == "EXECUTION_FIDELITY_PROXY_EXECUTION"
    assert proxy_row.proxy_execution_label_flag is True
    assert proxy_row.replay_grounded_label_flag is False
    assert proxy_row.label_quality_status == "LABEL_QUALITY_RESEARCH_ONLY"
    assert proxy_row.fee_bps is None
    assert proxy_row.mfe_bps is None
    assert proxy_row.mae_bps is None

    summary = StrategyLadderB2LabelStoreSummary.model_validate_json(
        (output_dir / LABEL_STORE_SUMMARY_FILENAME).read_text(encoding="utf-8")
    )
    assert summary.label_source_type == "B2_REPLAY_EXECUTED_ONLY_AND_EXPECTED_CE_MIXED"
    assert summary.replay_grounded_label_count == 1
    assert summary.proxy_execution_label_count == 1

    quality = StrategyLadderB2LabelStoreQualityReport.model_validate_json(
        (output_dir / LABEL_STORE_QUALITY_REPORT_FILENAME).read_text(encoding="utf-8")
    )
    assert quality.no_future_timestamp_violations == 0
    assert quality.post_decision_replay_only is True
    assert quality.no_fabricated_trades is True
    assert quality.no_fabricated_costs is True
    assert quality.label_quality_status_counts["LABEL_QUALITY_RESEARCH_ONLY"] == 2
    assert quality.entry_reference_status_counts["ENTRY_REFERENCE_DECISION_PRICE_PROXY"] == 1
    assert quality.evidence_class_counts["REPLAY_EXPECTED_CE_NET_PROXY"] == 1


def test_b2_label_store_builder_blocks_when_replay_is_missing() -> None:
    scratch = _scratch_dir("missing_replay")
    run_root = scratch / "b2-run"
    output_dir = scratch / "label-store"
    _write_candidate_events(run_root)

    result = build_strategy_ladder_b2_label_store(
        StrategyLadderB2LabelStoreBuilderRequest(
            run_root=run_root,
            output_dir=output_dir,
        )
    )

    assert result.status == "LABEL_STORE_BLOCKED_BY_MISSING_REPLAY"
    summary = StrategyLadderB2LabelStoreSummary.model_validate_json(
        (output_dir / LABEL_STORE_SUMMARY_FILENAME).read_text(encoding="utf-8")
    )
    assert "B2_DETAILED_REPLAY_MISSING" in summary.blocking_reasons
