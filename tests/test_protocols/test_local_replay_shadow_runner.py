"""Tests for the governed LOCAL_REPLAY -> VPS import -> SHADOW runner."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import shutil
import sys
from uuid import uuid4

from interface_contracts import ProfileId, StrategyClassification
from local_replay_runtime import (
    HistoricalReplayDataset,
    HistoricalReplayOpportunity,
    ReplayExecutionInput,
    ReplayOrchestratorRequest,
    ReplayRunManifest,
    execute_local_replay_export,
    orchestrate_local_replay_export,
)
from meta_minimal.dtr_core.decision_state_encoder import DecisionState
from meta_minimal.dtr_core.dtr_record_builder import build_dtr


def _load_runner_module():
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "scripts" / "run_local_replay_shadow.py"
    module_name = "test_run_local_replay_shadow"
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _scratch_dir(label: str) -> Path:
    repo_root = Path(__file__).resolve().parents[2]
    base_dir = repo_root / "build" / "local_replay_shadow_runner_tests"
    base_dir.mkdir(parents=True, exist_ok=True)
    output_dir = base_dir / f"{label}_{uuid4().hex}"
    output_dir.mkdir(parents=True, exist_ok=False)
    return output_dir


def _real_exports_dir() -> Path:
    repo_root = Path(__file__).resolve().parents[2]
    export_dir = repo_root / "build" / "local_replay_shadow_runner_tests" / f"real_exports_{uuid4().hex}"
    export_dir.mkdir(parents=True, exist_ok=False)
    execute_local_replay_export(
        export_dir,
        ReplayExecutionInput(
            run_manifest=ReplayRunManifest(
                run_id="run-local-export-1",
                strategy_id="strategy-a-1",
                strategy_version="a.v2.0",
                strategy_classification=StrategyClassification.A_VARIANT,
                lineage_version="a.v2.0.r3",
                profile_scope=ProfileId.LIGHT,
                engine_scope=("engine_a", "engine_b"),
                tested_pairs=("BTCUSDT", "ETHUSDT"),
                dataset_manifest_id="dataset-export-20260401",
                timeframe_scope="2026-03-01/2026-03-31",
                feature_set_version="feature.v2",
                formula_set_version="formula.v2",
                scoring_version="score.v2",
                regime_version="regime.v2",
                risk_policy_version="risk.v2",
                cost_model_version="cost.v2",
                performance_mode="research_fast_mode",
                artifact_schema_version="artifact.v2",
                artifact_hash="artifact-hash-local-export-1",
                clock_id="clock-local-export-1",
                start_timestamp_ms=1_700_000_000_000,
                end_timestamp_ms=1_700_003_600_000,
                tick_count=360,
                record_count=2048,
            ),
            total_opportunities=3,
            dtr_records=(
                build_dtr(
                    dtr_id="run-local-export-1:dtr:1",
                    pair="BTCUSDT",
                    engine_id="engine_a",
                    decision_state=DecisionState.SELECTED,
                    expected_cost=0.0010,
                    realized_cost=0.0011,
                    gross_return=0.0020,
                    ce_expected=0.0006,
                    runtime_mode="local_replay",
                    input_source="local_replay",
                    timestamp=1_700_000_000.0,
                ),
                build_dtr(
                    dtr_id="run-local-export-1:dtr:2",
                    pair="ETHUSDT",
                    engine_id="engine_b",
                    decision_state=DecisionState.REJECTED_RANKING,
                    expected_cost=0.0013,
                    realized_cost=0.0,
                    gross_return=-0.0003,
                    ce_expected=0.0001,
                    runtime_mode="local_replay",
                    input_source="local_replay",
                    timestamp=1_700_000_060.0,
                ),
            ),
            feature_bridge_payload={"bridge": "ok"},
            parity_diagnostics_payload={
                "parity_status": "ok",
                "decision_match_rate": 1.0,
            },
            review_notes=("runner integration export",),
        ),
    )
    return export_dir


def _chunked_exports_dir() -> Path:
    repo_root = Path(__file__).resolve().parents[2]
    export_dir = repo_root / "build" / "local_replay_shadow_runner_tests" / f"chunked_exports_{uuid4().hex}"
    export_dir.mkdir(parents=True, exist_ok=False)
    dataset = HistoricalReplayDataset.from_records(
        dataset_id="dataset-export-chunked-20260401",
        source_path="inmemory://dataset-export-chunked-20260401",
        source="test_dataset",
        records=(
            HistoricalReplayOpportunity(
                opportunity_id="chunk-op-1",
                timestamp_ms=1_700_000_000_000,
                pair="BTCUSDT",
                engine_id="engine_a",
                raw_score=0.91,
                penalized_score=0.88,
                final_score=0.86,
                expected_edge_bps=17.0,
                spread_bps=3.0,
                slippage_bps=4.0,
                latency_penalty_bps=1.0,
                fill_ratio=1.0,
                target_decision_state="executed",
                production_decision_state="executed",
                production_final_score=0.86,
                production_expected_cost=0.00086,
                candidate_size=1.0,
                final_size=1.0,
                gross_return_bps=18.0,
                feature_values={"spread_bps": 3.0},
            ),
            HistoricalReplayOpportunity(
                opportunity_id="chunk-op-2",
                timestamp_ms=1_700_000_060_000,
                pair="ETHUSDT",
                engine_id="engine_b",
                raw_score=0.84,
                penalized_score=0.8,
                final_score=0.77,
                expected_edge_bps=9.0,
                spread_bps=4.0,
                slippage_bps=3.0,
                latency_penalty_bps=1.0,
                fill_ratio=1.0,
                target_decision_state="executed",
                production_decision_state="executed",
                production_final_score=0.77,
                production_expected_cost=0.00077,
                candidate_size=1.0,
                final_size=1.0,
                gross_return_bps=11.0,
                feature_values={"spread_bps": 4.0},
            ),
            HistoricalReplayOpportunity(
                opportunity_id="chunk-op-3",
                timestamp_ms=1_700_000_120_000,
                pair="SOLUSDT",
                engine_id="engine_c",
                raw_score=0.62,
                penalized_score=0.58,
                final_score=0.52,
                expected_edge_bps=6.0,
                spread_bps=6.0,
                slippage_bps=2.0,
                latency_penalty_bps=1.0,
                fill_ratio=0.5,
                target_decision_state="reduced",
                production_decision_state="reduced",
                production_final_score=0.52,
                production_expected_cost=0.00071,
                candidate_size=1.0,
                final_size=0.5,
                gross_return_bps=5.0,
                feature_values={"spread_bps": 6.0},
            ),
        ),
    )
    orchestrate_local_replay_export(
        ReplayOrchestratorRequest(
            output_dir=export_dir,
            run_id="run-local-export-chunked-1",
            strategy_id="strategy-a-chunked-1",
            strategy_version="a.v2.1",
            strategy_classification=StrategyClassification.A_VARIANT,
            lineage_version="a.v2.1.r1",
            performance_mode="research_fast_mode",
            input_kind="historical_dataset",
            dataset=dataset,
            chunk_count=3,
            run_all_chunks=True,
        )
    )
    return export_dir


def test_export_local_replay_shadow_run_writes_governed_chain_sidecars():
    runner = _load_runner_module()
    output_dir = _scratch_dir("runner")

    try:
        artifacts = runner.export_local_replay_shadow_run(output_dir)

        assert artifacts.run_manifest_json_path is None
        assert artifacts.replay_plan_json_path.exists()
        assert artifacts.import_summary_json_path.exists()
        assert artifacts.local_replay_evidence_json_path.exists()
        assert artifacts.baseline_payload_json_path.exists()
        assert artifacts.candidate_payload_json_path.exists()
        assert artifacts.shadow_input_json_path.exists()
        assert artifacts.shadow_runtime_evidence_json_path.exists()
        assert artifacts.shadow_summary_json_path.exists()

        import_summary = json.loads(artifacts.import_summary_json_path.read_text(encoding="utf-8"))
        local_replay_evidence = json.loads(
            artifacts.local_replay_evidence_json_path.read_text(encoding="utf-8")
        )
        candidate_payload = json.loads(
            artifacts.candidate_payload_json_path.read_text(encoding="utf-8")
        )
        shadow_input = json.loads(artifacts.shadow_input_json_path.read_text(encoding="utf-8"))
        shadow_runtime_evidence = json.loads(
            artifacts.shadow_runtime_evidence_json_path.read_text(encoding="utf-8")
        )
        shadow_summary = json.loads(artifacts.shadow_summary_json_path.read_text(encoding="utf-8"))

        assert import_summary["accepted"] is True
        assert import_summary["validation_status"] == "accepted"
        assert local_replay_evidence["data_source"] == "recorded_replay"
        assert local_replay_evidence["replay_useful_ready"] is True
        assert candidate_payload["replay_import"]["validation_status"] == "accepted"
        assert candidate_payload["system"]["build14_status"] == "healthy"
        assert shadow_input["validation_set"]["runtime_data_source"] == "recorded_replay"
        assert shadow_input["validation_set"]["runtime_continuous_hours"] >= 24.0
        assert shadow_runtime_evidence["event_loop_ready"] is True
        assert shadow_runtime_evidence["config_loaded"] is True
        assert shadow_runtime_evidence["shadow_dtr_persisted"] is True
        assert shadow_runtime_evidence["continuous_hours"] >= 24.0
        assert shadow_summary["decision"]["accepted"] is True
        assert shadow_summary["decision"]["verdict"] == "accepted"
        assert shadow_summary["runtime_evidence_ready"] is True
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_export_local_replay_shadow_run_accepts_real_export_directory():
    runner = _load_runner_module()
    output_dir = _scratch_dir("real_dir")
    export_dir = _real_exports_dir()

    try:
        artifacts = runner.export_local_replay_shadow_run(output_dir, export_dir=export_dir)

        assert artifacts.run_manifest_json_path is not None
        assert artifacts.run_manifest_json_path.exists()
        import_summary = json.loads(artifacts.import_summary_json_path.read_text(encoding="utf-8"))
        replay_plan = json.loads(artifacts.replay_plan_json_path.read_text(encoding="utf-8"))
        local_replay_evidence = json.loads(
            artifacts.local_replay_evidence_json_path.read_text(encoding="utf-8")
        )
        run_manifest = json.loads(artifacts.run_manifest_json_path.read_text(encoding="utf-8"))

        assert import_summary["accepted"] is True
        assert import_summary["artifact_id"] == "artifact-hash-local-export-1"
        assert import_summary["lineage_version"] == "a.v2.0.r3"
        assert import_summary["review_export_ref"] == str((export_dir / "review_export.md").resolve())
        assert import_summary["feature_bridge_ref"] == str((export_dir / "feature_bridge.json").resolve())
        assert import_summary["parity_diagnostics_ref"] == str((export_dir / "parity_diagnostics.json").resolve())
        assert import_summary["replay_metrics_ref"] == str((export_dir / "replay_metrics.json").resolve())
        assert import_summary["replay_dtr_ref"] == str((export_dir / "replay_dtr.jsonl").resolve())
        assert replay_plan["request"]["correlation_id"] == "run-local-export-1"
        assert replay_plan["request"]["lineage_version"] == "a.v2.0.r3"
        assert replay_plan["request"]["strategy_classification"] == "a_variant"
        assert replay_plan["dataset_ref"]["dataset_id"] == "dataset-export-20260401"
        assert replay_plan["clock_ref"]["clock_id"] == "clock-local-export-1"
        assert replay_plan["bundle"]["manifest"]["strategy_version"] == "a.v2.0"
        assert replay_plan["bundle"]["payload_refs"] == [
            str((export_dir / "review_export.md").resolve()),
            str((export_dir / "feature_bridge.json").resolve()),
            str((export_dir / "parity_diagnostics.json").resolve()),
            str((export_dir / "replay_metrics.json").resolve()),
            str((export_dir / "replay_dtr.jsonl").resolve()),
        ]
        assert run_manifest["strategy_id"] == "strategy-a-1"
        assert run_manifest["performance_mode"] == "research_fast_mode"
        assert local_replay_evidence["replay_useful_ready"] is True
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
        shutil.rmtree(export_dir, ignore_errors=True)


def test_runner_main_accepts_output_dir():
    runner = _load_runner_module()
    output_dir = _scratch_dir("cli")

    try:
        exit_code = runner.main(["--output-dir", str(output_dir)])

        assert exit_code == 0
        assert (output_dir / "local_replay_shadow.shadow_summary.json").exists()
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_export_local_replay_shadow_run_accepts_chunked_aggregate_export_directory():
    runner = _load_runner_module()
    output_dir = _scratch_dir("chunked_dir")
    export_dir = _chunked_exports_dir()

    try:
        artifacts = runner.export_local_replay_shadow_run(output_dir, export_dir=export_dir)

        import_summary = json.loads(artifacts.import_summary_json_path.read_text(encoding="utf-8"))
        shadow_summary = json.loads(artifacts.shadow_summary_json_path.read_text(encoding="utf-8"))
        run_manifest = json.loads(artifacts.run_manifest_json_path.read_text(encoding="utf-8"))

        assert import_summary["accepted"] is True
        assert import_summary["artifact_id"] == "artifact-run-local-export-chunked-1"
        assert import_summary["feature_bridge_ref"] == str((export_dir / "feature_bridge.json").resolve())
        assert import_summary["replay_dtr_ref"] == str((export_dir / "replay_dtr.jsonl").resolve())
        assert run_manifest["record_count"] == 3
        assert shadow_summary["decision"]["accepted"] is True
        assert shadow_summary["runtime_evidence_ready"] is True
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
        shutil.rmtree(export_dir, ignore_errors=True)
