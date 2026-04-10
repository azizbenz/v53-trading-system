"""Tests for the governed LOCAL_REPLAY export launcher."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import shutil
import sys
from uuid import uuid4

import pytest
import yaml

from calibration_loader import CalibrationArtifact
from interface_contracts import ProfileId


def _load_launcher_module():
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "scripts" / "run_local_replay_export.py"
    module_name = "test_run_local_replay_export"
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _scratch_dir(label: str) -> Path:
    repo_root = Path(__file__).resolve().parents[2]
    base_dir = repo_root / "build" / "local_replay_export_launcher_tests"
    base_dir.mkdir(parents=True, exist_ok=True)
    output_dir = base_dir / f"{label}_{uuid4().hex}"
    output_dir.mkdir(parents=True, exist_ok=False)
    return output_dir


def test_local_replay_export_launcher_writes_canonical_files():
    launcher = _load_launcher_module()
    output_dir = _scratch_dir("export")

    try:
        exit_code = launcher.main(
            [
                "--output-dir",
                str(output_dir),
                "--run-id",
                "run-export-cli-1",
                "--strategy-version",
                "a.v5.0",
                "--lineage-version",
                "a.v5.0.r4",
                "--performance-mode",
                "shadow_fidelity_mode",
            ]
        )

        assert exit_code == 0
        assert (output_dir / "replay_session_config.json").exists()
        assert (output_dir / "replay_session_state.json").exists()
        assert (output_dir / "performance_mode_guard.json").exists()
        assert (output_dir / "run_consistency_guard.json").exists()
        assert (output_dir / "replay_run_manifest.json").exists()
        assert (output_dir / "review_export.md").exists()
        assert (output_dir / "feature_bridge.json").exists()
        assert (output_dir / "parity_diagnostics.json").exists()
        assert (output_dir / "replay_metrics.json").exists()
        assert (output_dir / "replay_dtr.jsonl").exists()

        run_manifest = json.loads(
            (output_dir / "replay_run_manifest.json").read_text(encoding="utf-8")
        )
        session_config = json.loads(
            (output_dir / "replay_session_config.json").read_text(encoding="utf-8")
        )
        session_state = json.loads(
            (output_dir / "replay_session_state.json").read_text(encoding="utf-8")
        )
        performance_guard = json.loads(
            (output_dir / "performance_mode_guard.json").read_text(encoding="utf-8")
        )
        consistency_guard = json.loads(
            (output_dir / "run_consistency_guard.json").read_text(encoding="utf-8")
        )
        assert run_manifest["run_id"] == "run-export-cli-1"
        assert run_manifest["strategy_version"] == "a.v5.0"
        assert run_manifest["lineage_version"] == "a.v5.0.r4"
        assert run_manifest["performance_mode"] == "shadow_fidelity_mode"
        assert run_manifest["profile_scope"] == ProfileId.COMPLETE.value
        assert session_config["input_kind"] == "demo_dataset"
        assert session_config["log_detail_level"] == "rich"
        assert session_state["lifecycle_state"] == "export_completed"
        assert performance_guard["guard_passed"] is True
        assert consistency_guard["consistent"] is True
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_local_replay_export_launcher_accepts_historical_dataset_file():
    launcher = _load_launcher_module()
    output_dir = _scratch_dir("dataset_export")
    dataset_path = output_dir / "historical_dataset.json"
    dataset_path.write_text(
        json.dumps(
            {
                "records": [
                    {
                        "opportunity_id": "row-1",
                        "timestamp_ms": 1_700_000_000_000,
                        "pair": "BTCUSDT",
                        "engine_id": "engine_a",
                        "raw_score": 0.91,
                        "penalized_score": 0.88,
                        "final_score": 0.86,
                        "expected_edge_bps": 17.0,
                        "spread_bps": 3.0,
                        "slippage_bps": 4.0,
                        "latency_penalty_bps": 1.0,
                        "fill_ratio": 1.0,
                        "target_decision_state": "executed",
                        "production_decision_state": "executed",
                        "production_final_score": 0.86,
                        "production_expected_cost": 0.00086,
                        "candidate_size": 1.0,
                        "final_size": 1.0,
                        "gross_return_bps": 20.0,
                        "feature_values": {"spread_bps": 3.0, "imbalance": 0.1},
                    },
                    {
                        "opportunity_id": "row-2",
                        "timestamp_ms": 1_700_000_060_000,
                        "pair": "ETHUSDT",
                        "engine_id": "engine_b",
                        "raw_score": 0.74,
                        "penalized_score": 0.7,
                        "final_score": 0.68,
                        "expected_edge_bps": 9.0,
                        "spread_bps": 4.0,
                        "slippage_bps": 2.0,
                        "latency_penalty_bps": 1.0,
                        "fill_ratio": 0.5,
                        "target_decision_state": "executed",
                        "production_decision_state": "reduced",
                        "production_final_score": 0.68,
                        "production_expected_cost": 0.00073,
                        "candidate_size": 1.0,
                        "final_size": 1.0,
                        "gross_return_bps": 9.0,
                        "feature_values": {"spread_bps": 4.0, "imbalance": -0.03},
                    },
                ]
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    try:
        exit_code = launcher.main(
            [
                "--output-dir",
                str(output_dir),
                "--dataset-path",
                str(dataset_path),
                "--run-id",
                "run-dataset-cli-1",
                "--strategy-id",
                "strategy-dataset-a",
                "--strategy-version",
                "a.v6.0",
                "--lineage-version",
                "a.v6.0.r2",
                "--performance-mode",
                "shadow_fidelity_mode",
            ]
        )

        assert exit_code == 0
        manifest = json.loads((output_dir / "replay_run_manifest.json").read_text(encoding="utf-8"))
        feature_bridge = json.loads((output_dir / "feature_bridge.json").read_text(encoding="utf-8"))
        parity = json.loads((output_dir / "parity_diagnostics.json").read_text(encoding="utf-8"))
        session_config = json.loads(
            (output_dir / "replay_session_config.json").read_text(encoding="utf-8")
        )
        performance_guard = json.loads(
            (output_dir / "performance_mode_guard.json").read_text(encoding="utf-8")
        )
        consistency_guard = json.loads(
            (output_dir / "run_consistency_guard.json").read_text(encoding="utf-8")
        )
        dtr_lines = (output_dir / "replay_dtr.jsonl").read_text(encoding="utf-8").strip().splitlines()

        assert manifest["strategy_id"] == "strategy-dataset-a"
        assert manifest["dataset_manifest_id"] == "historical_dataset"
        assert manifest["tested_pairs"] == ["BTCUSDT", "ETHUSDT"]
        assert manifest["record_count"] == 2
        assert manifest["tick_count"] == 2
        assert manifest["profile_scope"] == ProfileId.COMPLETE.value
        assert session_config["input_kind"] == "historical_dataset"
        assert performance_guard["guard_passed"] is True
        assert consistency_guard["consistent"] is True
        assert feature_bridge["bridge_status"] == "ok"
        assert feature_bridge["path_materialized"] is True
        assert parity["parity_status"] == "ok"
        assert len(dtr_lines) == 2
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_local_replay_export_launcher_accepts_historical_snapshot_file():
    launcher = _load_launcher_module()
    output_dir = _scratch_dir("snapshot_export")
    snapshot_path = output_dir / "historical_snapshots.json"
    snapshot_path.write_text(
        json.dumps(
            {
                "records": [
                    {
                        "event_type": "snapshot",
                        "event": {
                            "timestamp_ms": 1_700_000_000_000,
                            "pair": "BTCUSDT",
                            "last_price": 43250.0,
                            "bid": 43249.0,
                            "ask": 43251.0,
                            "volume_24h": 1200000.0,
                        },
                        "route_hint": {
                            "route_id": "route-btc-1",
                            "engine_id": "engine_a",
                            "raw_score": 0.91,
                            "penalized_score": 0.88,
                            "final_score": 0.86,
                            "expected_edge_bps": 17.0,
                            "slippage_bps": 4.6,
                            "latency_penalty_bps": 1.0,
                            "target_decision_state": "executed",
                            "production_decision_state": "executed",
                            "production_final_score": 0.86,
                            "production_expected_cost": 0.00086,
                            "candidate_size": 1.0,
                            "final_size": 1.0,
                            "gross_return_bps": 20.0,
                            "feature_values": {"custom_signal": 1.0},
                        },
                    },
                    {
                        "event_type": "kline",
                        "event": {
                            "timestamp_ms": 1_700_000_060_000,
                            "pair": "BTCUSDT",
                            "timeframe": "1m",
                            "open_price": 43240.0,
                            "high_price": 43280.0,
                            "low_price": 43230.0,
                            "close_price": 43270.0,
                            "volume": 250.0,
                        },
                        "route_hint": {
                            "route_id": "route-btc-1",
                            "engine_id": "engine_a",
                            "raw_score": 0.91,
                            "penalized_score": 0.88,
                            "final_score": 0.86,
                            "expected_edge_bps": 17.0,
                            "slippage_bps": 4.6,
                            "latency_penalty_bps": 1.0,
                            "target_decision_state": "executed",
                            "production_decision_state": "executed",
                            "production_final_score": 0.86,
                            "production_expected_cost": 0.00086,
                            "candidate_size": 1.0,
                            "final_size": 1.0,
                            "gross_return_bps": 20.0,
                        },
                    },
                ]
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    try:
        exit_code = launcher.main(
            [
                "--output-dir",
                str(output_dir),
                "--snapshot-path",
                str(snapshot_path),
                "--run-id",
                "run-snapshot-cli-1",
                "--strategy-id",
                "strategy-snapshot-a",
                "--strategy-version",
                "a.v7.0",
                "--lineage-version",
                "a.v7.0.r1",
            ]
        )

        assert exit_code == 0
        manifest = json.loads((output_dir / "replay_run_manifest.json").read_text(encoding="utf-8"))
        feature_bridge = json.loads((output_dir / "feature_bridge.json").read_text(encoding="utf-8"))
        parity = json.loads((output_dir / "parity_diagnostics.json").read_text(encoding="utf-8"))
        session_config = json.loads(
            (output_dir / "replay_session_config.json").read_text(encoding="utf-8")
        )
        performance_guard = json.loads(
            (output_dir / "performance_mode_guard.json").read_text(encoding="utf-8")
        )
        consistency_guard = json.loads(
            (output_dir / "run_consistency_guard.json").read_text(encoding="utf-8")
        )
        dtr_lines = (output_dir / "replay_dtr.jsonl").read_text(encoding="utf-8").strip().splitlines()

        assert manifest["strategy_id"] == "strategy-snapshot-a"
        assert manifest["dataset_manifest_id"] == "historical_snapshots"
        assert manifest["tested_pairs"] == ["BTCUSDT"]
        assert manifest["record_count"] == 1
        assert manifest["profile_scope"] == ProfileId.COMPLETE.value
        assert session_config["input_kind"] == "historical_snapshot_batch"
        assert performance_guard["guard_passed"] is True
        assert consistency_guard["consistent"] is True
        assert feature_bridge["bridge_status"] == "ok"
        assert "snapshot_last_price" in feature_bridge["feature_keys"]
        assert parity["parity_status"] == "ok"
        assert len(dtr_lines) == 1
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_local_replay_export_launcher_resumes_completed_export_without_reloading_inputs():
    launcher = _load_launcher_module()
    output_dir = _scratch_dir("resume_export")

    try:
        first_exit_code = launcher.main(
            [
                "--output-dir",
                str(output_dir),
                "--run-id",
                "run-export-resume-1",
                "--strategy-version",
                "a.v8.0",
                "--lineage-version",
                "a.v8.0.r1",
                "--chunk-count",
                "3",
                "--chunk-index",
                "2",
            ]
        )
        original_manifest = (output_dir / "replay_run_manifest.json").read_text(encoding="utf-8")

        resumed_exit_code = launcher.main(
            [
                "--output-dir",
                str(output_dir),
                "--resume",
            ]
        )

        session_config = json.loads(
            (output_dir / "replay_session_config.json").read_text(encoding="utf-8")
        )
        session_state = json.loads(
            (output_dir / "replay_session_state.json").read_text(encoding="utf-8")
        )

        assert first_exit_code == 0
        assert resumed_exit_code == 0
        assert session_config["run_id"] == "run-export-resume-1"
        assert session_config["chunk_count"] == 3
        assert session_config["chunk_index"] == 2
        assert session_state["lifecycle_state"] == "export_completed"
        assert (output_dir / "replay_run_manifest.json").read_text(encoding="utf-8") == original_manifest
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_local_replay_export_launcher_can_emit_edge_calibration_artifact():
    launcher = _load_launcher_module()
    output_dir = _scratch_dir("edge_calibration_export")
    dataset_path = output_dir / "historical_dataset.json"
    dataset_path.write_text(
        json.dumps(
            {
                "records": [
                    {
                        "opportunity_id": "row-1",
                        "timestamp_ms": 1_700_000_000_000,
                        "pair": "BTCUSDT",
                        "engine_id": "engine_a",
                        "raw_score": 0.91,
                        "penalized_score": 0.88,
                        "final_score": 0.86,
                        "expected_edge_bps": 41.0,
                        "spread_bps": 3.0,
                        "slippage_bps": 4.0,
                        "latency_penalty_bps": 1.0,
                        "fill_ratio": 1.0,
                        "target_decision_state": "executed",
                        "production_decision_state": "executed",
                        "production_final_score": 0.86,
                        "production_expected_cost": 0.0010,
                        "candidate_size": 1.0,
                        "final_size": 1.0,
                        "gross_return_bps": 40.0,
                        "feature_values": {"spread_bps": 3.0},
                    },
                    {
                        "opportunity_id": "row-2",
                        "timestamp_ms": 1_700_000_060_000,
                        "pair": "ETHUSDT",
                        "engine_id": "engine_b",
                        "raw_score": 0.84,
                        "penalized_score": 0.82,
                        "final_score": 0.80,
                        "expected_edge_bps": 39.0,
                        "spread_bps": 4.0,
                        "slippage_bps": 3.0,
                        "latency_penalty_bps": 1.0,
                        "fill_ratio": 1.0,
                        "target_decision_state": "executed",
                        "production_decision_state": "executed",
                        "production_final_score": 0.80,
                        "production_expected_cost": 0.0011,
                        "candidate_size": 1.0,
                        "final_size": 1.0,
                        "gross_return_bps": 41.0,
                        "feature_values": {"spread_bps": 4.0},
                    },
                    {
                        "opportunity_id": "row-3",
                        "timestamp_ms": 1_700_000_120_000,
                        "pair": "SOLUSDT",
                        "engine_id": "engine_c",
                        "raw_score": 0.82,
                        "penalized_score": 0.81,
                        "final_score": 0.79,
                        "expected_edge_bps": 37.0,
                        "spread_bps": 5.0,
                        "slippage_bps": 3.0,
                        "latency_penalty_bps": 1.0,
                        "fill_ratio": 1.0,
                        "target_decision_state": "executed",
                        "production_decision_state": "executed",
                        "production_final_score": 0.79,
                        "production_expected_cost": 0.0012,
                        "candidate_size": 1.0,
                        "final_size": 1.0,
                        "gross_return_bps": 39.0,
                        "feature_values": {"spread_bps": 5.0},
                    },
                    {
                        "opportunity_id": "row-4",
                        "timestamp_ms": 1_700_000_180_000,
                        "pair": "ADAUSDT",
                        "engine_id": "engine_d",
                        "raw_score": 0.80,
                        "penalized_score": 0.79,
                        "final_score": 0.78,
                        "expected_edge_bps": 42.0,
                        "spread_bps": 4.0,
                        "slippage_bps": 4.0,
                        "latency_penalty_bps": 1.0,
                        "fill_ratio": 1.0,
                        "target_decision_state": "executed",
                        "production_decision_state": "executed",
                        "production_final_score": 0.78,
                        "production_expected_cost": 0.0013,
                        "candidate_size": 1.0,
                        "final_size": 1.0,
                        "gross_return_bps": 44.0,
                        "feature_values": {"spread_bps": 4.0},
                    },
                    {
                        "opportunity_id": "row-5",
                        "timestamp_ms": 1_700_000_240_000,
                        "pair": "XRPUSDT",
                        "engine_id": "engine_a",
                        "raw_score": 0.78,
                        "penalized_score": 0.77,
                        "final_score": 0.75,
                        "expected_edge_bps": 38.0,
                        "spread_bps": 4.0,
                        "slippage_bps": 3.0,
                        "latency_penalty_bps": 1.0,
                        "fill_ratio": 1.0,
                        "target_decision_state": "executed",
                        "production_decision_state": "executed",
                        "production_final_score": 0.75,
                        "production_expected_cost": 0.0014,
                        "candidate_size": 1.0,
                        "final_size": 1.0,
                        "gross_return_bps": 42.0,
                        "feature_values": {"spread_bps": 4.0},
                    },
                    {
                        "opportunity_id": "row-6",
                        "timestamp_ms": 1_700_000_300_000,
                        "pair": "DOGEUSDT",
                        "engine_id": "engine_b",
                        "raw_score": 0.79,
                        "penalized_score": 0.78,
                        "final_score": 0.76,
                        "expected_edge_bps": 43.0,
                        "spread_bps": 5.0,
                        "slippage_bps": 4.0,
                        "latency_penalty_bps": 1.0,
                        "fill_ratio": 1.0,
                        "target_decision_state": "executed",
                        "production_decision_state": "executed",
                        "production_final_score": 0.76,
                        "production_expected_cost": 0.0015,
                        "candidate_size": 1.0,
                        "final_size": 1.0,
                        "gross_return_bps": 45.0,
                        "feature_values": {"spread_bps": 5.0},
                    },
                ]
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    try:
        exit_code = launcher.main(
            [
                "--output-dir",
                str(output_dir),
                "--dataset-path",
                str(dataset_path),
                "--run-id",
                "run-edge-cal-cli-1",
                "--strategy-id",
                "strategy-edge-cal-a",
                "--strategy-version",
                "a.v6.1",
                "--lineage-version",
                "a.v6.1.r1",
                "--performance-mode",
                "shadow_fidelity_mode",
                "--emit-edge-calibration",
                "--edge-calibration-signed-by",
                "operator.aziz",
                "--edge-bootstrap-samples",
                "250",
                "--edge-min-positive-trades",
                "5",
                "--edge-min-cost-observations",
                "6",
            ]
        )

        artifact_path = output_dir / "calibration" / "edge_gate.yml"
        artifact = CalibrationArtifact.model_validate(
            yaml.safe_load(artifact_path.read_text(encoding="utf-8"))
        )

        assert exit_code == 0
        assert artifact_path.exists()
        assert artifact.thresholds[0].threshold_id == "THR-E01"
        assert artifact.thresholds[1].threshold_id == "THR-E02"
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_local_replay_export_launcher_rejects_explicit_mismatched_resume_metadata():
    launcher = _load_launcher_module()
    output_dir = _scratch_dir("resume_export_mismatch")

    try:
        first_exit_code = launcher.main(
            [
                "--output-dir",
                str(output_dir),
                "--run-id",
                "run-export-resume-mismatch-1",
                "--strategy-version",
                "a.v8.0",
                "--lineage-version",
                "a.v8.0.r1",
            ]
        )

        assert first_exit_code == 0

        with pytest.raises(
            ValueError,
            match="LOCAL_REPLAY resume request does not match the persisted export",
        ):
            launcher.main(
                [
                    "--output-dir",
                    str(output_dir),
                    "--run-id",
                    "run-export-resume-mismatch-1",
                    "--strategy-version",
                    "a.v8.0",
                    "--lineage-version",
                    "a.v8.0.r1",
                    "--profile-scope",
                    ProfileId.LIGHT.value,
                    "--resume",
                ]
            )
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_local_replay_export_launcher_runs_all_chunks_and_writes_session_bundle():
    launcher = _load_launcher_module()
    output_dir = _scratch_dir("run_all_chunks")

    try:
        exit_code = launcher.main(
            [
                "--output-dir",
                str(output_dir),
                "--run-id",
                "run-export-all-chunks-1",
                "--strategy-version",
                "a.v8.1",
                "--lineage-version",
                "a.v8.1.r1",
                "--chunk-count",
                "3",
                "--run-all-chunks",
            ]
        )

        session_bundle = json.loads(
            (output_dir / "replay_chunk_session.json").read_text(encoding="utf-8")
        )
        manifest = json.loads((output_dir / "replay_run_manifest.json").read_text(encoding="utf-8"))
        dtr_lines = (output_dir / "replay_dtr.jsonl").read_text(encoding="utf-8").strip().splitlines()

        assert exit_code == 0
        assert session_bundle["aggregate_ready"] is True
        assert session_bundle["completed_chunk_indices"] == [1, 2, 3]
        assert manifest["record_count"] == 3
        assert len(dtr_lines) == 3
        assert (output_dir / "chunks" / "chunk_0001" / "replay_run_manifest.json").exists()
        assert (output_dir / "chunks" / "chunk_0002" / "replay_run_manifest.json").exists()
        assert (output_dir / "chunks" / "chunk_0003" / "replay_run_manifest.json").exists()
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_local_replay_export_launcher_resumes_complete_multi_chunk_session():
    launcher = _load_launcher_module()
    output_dir = _scratch_dir("run_all_chunks_resume")

    try:
        first_exit_code = launcher.main(
            [
                "--output-dir",
                str(output_dir),
                "--run-id",
                "run-export-all-chunks-resume-1",
                "--strategy-version",
                "a.v8.2",
                "--lineage-version",
                "a.v8.2.r1",
                "--chunk-count",
                "3",
                "--run-all-chunks",
            ]
        )
        resumed_exit_code = launcher.main(
            [
                "--output-dir",
                str(output_dir),
                "--run-id",
                "run-export-all-chunks-resume-1",
                "--strategy-version",
                "a.v8.2",
                "--lineage-version",
                "a.v8.2.r1",
                "--chunk-count",
                "3",
                "--run-all-chunks",
                "--resume",
            ]
        )

        session_bundle = json.loads(
            (output_dir / "replay_chunk_session.json").read_text(encoding="utf-8")
        )

        assert first_exit_code == 0
        assert resumed_exit_code == 0
        assert session_bundle["resumed_chunk_indices"] == [1, 2, 3]
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_local_replay_export_launcher_accepts_chunk_indices_selection():
    launcher = _load_launcher_module()
    output_dir = _scratch_dir("run_selected_chunks")

    try:
        exit_code = launcher.main(
            [
                "--output-dir",
                str(output_dir),
                "--run-id",
                "run-export-selected-chunks-1",
                "--strategy-version",
                "a.v8.3",
                "--lineage-version",
                "a.v8.3.r1",
                "--chunk-count",
                "3",
                "--chunk-indices",
                "1,3",
                "--run-all-chunks",
            ]
        )

        session_bundle = json.loads(
            (output_dir / "replay_chunk_session.json").read_text(encoding="utf-8")
        )
        dtr_lines = (output_dir / "replay_dtr.jsonl").read_text(encoding="utf-8").strip().splitlines()

        assert exit_code == 0
        assert session_bundle["selected_chunk_indices"] == [1, 3]
        assert len(dtr_lines) == 2
        assert not (output_dir / "chunks" / "chunk_0002").exists()
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_local_replay_export_launcher_accepts_time_window_filter():
    launcher = _load_launcher_module()
    output_dir = _scratch_dir("run_windowed")

    try:
        exit_code = launcher.main(
            [
                "--output-dir",
                str(output_dir),
                "--run-id",
                "run-export-windowed-1",
                "--strategy-version",
                "a.v8.4",
                "--lineage-version",
                "a.v8.4.r1",
                "--chunk-count",
                "2",
                "--run-all-chunks",
                "--window-start-ms",
                "1700000060000",
                "--window-end-ms",
                "1700000120000",
            ]
        )

        session_bundle = json.loads(
            (output_dir / "replay_chunk_session.json").read_text(encoding="utf-8")
        )
        manifest = json.loads((output_dir / "replay_run_manifest.json").read_text(encoding="utf-8"))

        assert exit_code == 0
        assert session_bundle["window_start_ms"] == 1700000060000
        assert session_bundle["window_end_ms"] == 1700000120000
        assert manifest["record_count"] == 2
        assert manifest["profile_scope"] == ProfileId.COMPLETE.value
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_local_replay_export_launcher_accepts_explicit_light_profile_scope():
    launcher = _load_launcher_module()
    output_dir = _scratch_dir("run_light_profile")

    try:
        exit_code = launcher.main(
            [
                "--output-dir",
                str(output_dir),
                "--run-id",
                "run-export-light-profile-1",
                "--strategy-version",
                "a.v8.5",
                "--lineage-version",
                "a.v8.5.r1",
                "--profile-scope",
                ProfileId.LIGHT.value,
            ]
        )

        manifest = json.loads((output_dir / "replay_run_manifest.json").read_text(encoding="utf-8"))

        assert exit_code == 0
        assert manifest["profile_scope"] == ProfileId.LIGHT.value
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
