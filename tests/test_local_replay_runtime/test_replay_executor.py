"""Tests for the governed LOCAL_REPLAY session executor."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
from uuid import uuid4

from interface_contracts import ProfileId, StrategyClassification
from local_replay_runtime import (
    ReplayExecutionInput,
    ReplayRunManifest,
    build_replay_metrics_summary,
    execute_local_replay_export,
)
from meta_minimal.dtr_core.decision_state_encoder import DecisionState
from meta_minimal.dtr_core.dtr_record_builder import build_dtr
from tests.support_paths import repo_build_path


def _scratch_dir(name: str) -> Path:
    return repo_build_path("local_replay_executor_tests", f"{name}_{uuid4().hex}")


def _records():
    return (
        build_dtr(
            dtr_id="dtr-1",
            pair="BTCUSDT",
            engine_id="engine_a",
            decision_state=DecisionState.SELECTED,
            expected_cost=0.0010,
            realized_cost=0.0011,
            gross_return=0.0022,
            ce_expected=0.0006,
            runtime_mode="local_replay",
            input_source="local_replay",
            timestamp=1_700_000_000.0,
        ),
        build_dtr(
            dtr_id="dtr-2",
            pair="ETHUSDT",
            engine_id="engine_b",
            decision_state=DecisionState.HARD_BLOCKED,
            expected_cost=0.0014,
            realized_cost=0.0,
            gross_return=-0.0005,
            ce_expected=-0.0001,
            runtime_mode="local_replay",
            input_source="local_replay",
            timestamp=1_700_000_060.0,
        ),
    )


def test_build_replay_metrics_summary_aggregates_pairs_engines_and_drawdown():
    summary = build_replay_metrics_summary(_records(), total_opportunities=4)

    assert summary.total_records == 2
    assert summary.dtr_coverage == 0.5
    assert summary.selected_count == 1
    assert summary.hard_blocked_count == 1
    assert summary.ce_net == 0.0005
    assert summary.drawdown_proxy >= 0.0
    assert summary.pair_aggregates[0].pair == "BTCUSDT"
    assert summary.engine_aggregates[0].engine_id == "engine_a"


def test_execute_local_replay_export_builds_artifact_from_dtr_session():
    output_dir = _scratch_dir("export")
    shutil.rmtree(output_dir, ignore_errors=True)
    try:
        result = execute_local_replay_export(
            output_dir,
            ReplayExecutionInput(
                run_manifest=ReplayRunManifest(
                    run_id="run-executor-1",
                    strategy_id="strategy-executor-a",
                    strategy_version="a.v4.0",
                    strategy_classification=StrategyClassification.A_VARIANT,
                    lineage_version="a.v4.0.r1",
                    profile_scope=ProfileId.LIGHT,
                    engine_scope=("engine_a", "engine_b"),
                    tested_pairs=("BTCUSDT", "ETHUSDT"),
                    dataset_manifest_id="dataset-executor-1",
                    timeframe_scope="2026-03-01/2026-03-31",
        feature_set_version="4.0.0",
        transform_set_version="4.0.0",
        formula_set_version="formula.v4",
                    scoring_version="score.v4",
                    regime_version="regime.v4",
                    risk_policy_version="risk.v4",
                    cost_model_version="cost.v4",
                    performance_mode="research_fast_mode",
        artifact_schema_version="4.0.0",
                    artifact_hash="artifact-executor-1",
                    clock_id="clock-executor-1",
                    start_timestamp_ms=1_700_000_000_000,
                    end_timestamp_ms=1_700_000_600_000,
                    tick_count=600,
                    record_count=2,
                ),
                total_opportunities=4,
                dtr_records=_records(),
                feature_bridge_payload={
                    "bridge_status": "ok",
                    "dataset_id": "dataset-executor-1",
                    "feature_set_version": "4.0.0",
                    "transform_set_version": "4.0.0",
                    "pairs": ["BTCUSDT", "ETHUSDT"],
                    "engines": ["engine_a", "engine_b"],
                },
        parity_diagnostics_payload={
            "parity_status": "ok",
            "dataset_id": "dataset-executor-1",
            "decision_match_rate": 1.0,
        },
                review_notes=("executor smoke",),
            ),
        )

        metrics_payload = json.loads(
            result.export_result.replay_metrics_path.read_text(encoding="utf-8")
        )
        review_markdown = result.export_result.review_export_path.read_text(encoding="utf-8")
        replay_dtr_lines = result.export_result.replay_dtr_path.read_text(encoding="utf-8").strip().splitlines()

        assert result.metrics_summary.total_records == 2
        assert metrics_payload["dtr_coverage"] == 0.5
        assert metrics_payload["selected_count"] == 1
        assert "run-executor-1" in review_markdown
        assert "dtr_coverage: 0.500" in review_markdown
        assert len(replay_dtr_lines) == 2
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
