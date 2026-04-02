"""Tests for the external daily Shadow orchestration launcher."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import shutil
import sys
from uuid import uuid4

from interface_contracts import ProfileId, StrategyClassification
from local_replay_runtime import (
    ReplayExecutionInput,
    ReplayRunManifest,
    execute_local_replay_export,
)
from meta_minimal.dtr_core.decision_state_encoder import DecisionState
from meta_minimal.dtr_core.dtr_record_builder import build_dtr


def _load_launcher_module():
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "scripts" / "run_shadow_daily_orchestrator.py"
    module_name = "test_run_shadow_daily_orchestrator"
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _scratch_dir(label: str) -> Path:
    repo_root = Path(__file__).resolve().parents[2]
    base_dir = repo_root / "build" / "shadow_daily_orchestrator_launcher_tests"
    base_dir.mkdir(parents=True, exist_ok=True)
    output_dir = base_dir / f"{label}_{uuid4().hex}"
    output_dir.mkdir(parents=True, exist_ok=False)
    return output_dir


def _write_daily_export(export_dir: Path, session_date: str, run_suffix: str) -> None:
    execute_local_replay_export(
        export_dir,
        ReplayExecutionInput(
            run_manifest=ReplayRunManifest(
                run_id=f"run-shadow-daily-{run_suffix}",
                strategy_id=f"strategy-shadow-daily-{run_suffix}",
                strategy_version="a.v3.0",
                strategy_classification=StrategyClassification.A_VARIANT,
                lineage_version=f"a.v3.0.r{run_suffix}",
                profile_scope=ProfileId.LIGHT,
                engine_scope=("engine_a", "engine_b"),
                tested_pairs=("BTCUSDT", "ETHUSDT"),
                dataset_manifest_id=f"dataset-shadow-daily-{session_date}",
                timeframe_scope=f"{session_date}/{session_date}",
                feature_set_version="feature.v3",
                formula_set_version="formula.v3",
                scoring_version="score.v3",
                regime_version="regime.v3",
                risk_policy_version="risk.v3",
                cost_model_version="cost.v3",
                performance_mode="research_fast_mode",
                artifact_schema_version="artifact.v3",
                artifact_hash=f"artifact-shadow-daily-{run_suffix}",
                clock_id=f"clock-shadow-daily-{run_suffix}",
                start_timestamp_ms=1_700_000_000_000,
                end_timestamp_ms=1_700_003_600_000,
                tick_count=360,
                record_count=1024,
            ),
            total_opportunities=2,
            dtr_records=(
                build_dtr(
                    dtr_id=f"run-shadow-daily-{run_suffix}:dtr:1",
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
            ),
            feature_bridge_payload={"bridge": "ok"},
            parity_diagnostics_payload={
                "parity_status": "ok",
                "decision_match_rate": 1.0,
            },
            review_notes=(f"daily export {session_date}",),
        ),
    )


def test_shadow_daily_orchestrator_launcher_consumes_next_dated_export_dir():
    launcher = _load_launcher_module()
    output_dir = _scratch_dir("launcher")

    try:
        exports_root = output_dir / "exports_root"
        shadow_output_dir = output_dir / "shadow_session"
        day_one_dir = exports_root / "2026-04-01"
        day_two_dir = exports_root / "2026-04-02"
        day_one_dir.mkdir(parents=True, exist_ok=False)
        day_two_dir.mkdir(parents=True, exist_ok=False)
        _write_daily_export(day_one_dir, "2026-04-01", "1")
        _write_daily_export(day_two_dir, "2026-04-02", "2")

        first_exit = launcher.main(
            [
                "--output-dir",
                str(output_dir),
                "--shadow-output-dir",
                str(shadow_output_dir),
                "--exports-root",
                str(exports_root),
            ]
        )
        second_exit = launcher.main(
            [
                "--output-dir",
                str(output_dir),
                "--shadow-output-dir",
                str(shadow_output_dir),
                "--exports-root",
                str(exports_root),
            ]
        )

        assert first_exit == 0
        assert second_exit == 0

        state = json.loads(
            (output_dir / "shadow_daily_orchestrator.state.json").read_text(
                encoding="utf-8"
            )
        )
        last_run = json.loads(
            (output_dir / "shadow_daily_orchestrator.last_run.json").read_text(
                encoding="utf-8"
            )
        )
        shadow_session_summary = json.loads(
            (shadow_output_dir / "local_replay_shadow.shadow_session_summary.json").read_text(
                encoding="utf-8"
            )
        )

        completed_dates = [
            record["session_date"] for record in state["completed_runs"]
        ]
        assert completed_dates == ["2026-04-01", "2026-04-02"]
        assert last_run["session_date"] == "2026-04-02"
        assert last_run["consecutive_days"] == 2
        assert last_run["local_replay_evidence_ref"].endswith(
            "local_replay_shadow.local_replay_evidence.json"
        )
        assert last_run["shadow_runtime_evidence_ref"].endswith(
            "local_replay_shadow.shadow_runtime_evidence.json"
        )
        assert shadow_session_summary["consecutive_days"] == 2
        assert shadow_session_summary["session_dates"] == ["2026-04-02"]
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
