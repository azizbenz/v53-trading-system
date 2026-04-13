"""Tests for the external daily Shadow orchestration launcher."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import shutil
import sys
from uuid import uuid4

from interface_contracts import ProfileId, RuntimeMode, StrategyClassification
from local_replay_runtime import (
    LocalLabExecutionTelemetry,
    build_local_lab_execution_review,
    build_local_lab_execution_runtime_projection,
    ReplayExecutionInput,
    ReplayRunManifest,
    execute_local_replay_export,
)
from meta_minimal.dtr_core.decision_state_encoder import DecisionState
from meta_minimal.dtr_core.dtr_record_builder import build_dtr
from regime_classifier import RegimeLiteAssessment, RegimeLiteState
from risk_backbone import (
    InfoStressAssessment,
    InfoStressLevel,
    build_regime_lite_safing_recommendation,
)


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
                profile_scope=ProfileId.COMPLETE,
                engine_scope=("engine_a", "engine_b"),
                tested_pairs=("BTCUSDT", "ETHUSDT"),
                dataset_manifest_id=f"dataset-shadow-daily-{session_date}",
                timeframe_scope=f"{session_date}/{session_date}",
                feature_set_version="3.0.0",
                transform_set_version="3.0.0",
                formula_set_version="formula.v3",
                scoring_version="score.v3",
                regime_version="regime.v3",
                risk_policy_version="risk.v3",
                cost_model_version="cost.v3",
                performance_mode="research_fast_mode",
                artifact_schema_version="3.0.0",
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
            feature_bridge_payload={
                "bridge": "ok",
                "dataset_id": f"dataset-shadow-daily-{session_date}",
                "feature_set_version": "3.0.0",
                "transform_set_version": "3.0.0",
                "pairs": ["BTCUSDT", "ETHUSDT"],
                "engines": ["engine_a", "engine_b"],
            },
            parity_diagnostics_payload={
                "parity_status": "ok",
                "dataset_id": f"dataset-shadow-daily-{session_date}",
                "decision_match_rate": 1.0,
            },
            review_notes=(f"daily export {session_date}",),
        ),
    )


def _write_execution_runtime_projection(path: Path) -> None:
    projection = build_local_lab_execution_runtime_projection(
        build_local_lab_execution_review(
            correlation_id="corr-shadow-daily",
            export_dir="E:/lab/export",
            run_id="run-shadow-daily",
            telemetry=LocalLabExecutionTelemetry(
                correlation_id="corr-shadow-daily",
                export_dir="E:/lab/export",
                run_id="run-shadow-daily",
                quota_call_counts=(45, 48, 42, 46),
                quota_probe_durations_s=(60.0, 60.0, 60.0, 60.0),
                quota_limit_calls_per_minute_values=(100, 120),
                quota_calls_per_minute_observed=(45.0, 48.0, 42.0, 46.0),
                quota_observation_days=31.0,
                spread_bps=(6.0, 8.0, 9.0, 12.0),
                spread_observation_days=31.0,
                slippage_bps=(2.0, 2.8, 3.4, 4.0),
                slippage_observation_days=31.0,
                final_sizes=(1.0, 4.0, 9.0, 16.0),
            ),
        )
    )
    path.write_text(
        projection.model_dump_json(indent=2),
        encoding="utf-8",
    )


def _write_regime_lite_assessment(path: Path) -> None:
    assessment = RegimeLiteAssessment(
        state=RegimeLiteState.EXTREME,
        candidate_state=RegimeLiteState.EXTREME,
        previous_state=RegimeLiteState.STRESSED,
        state_changed=True,
        state_entered_ts=1_700_000_000_000,
        entries_blocked_until_ts=1_700_086_400_000,
        entries_blocked=True,
        sudden_event=True,
        transition_path=(RegimeLiteState.STRESSED, RegimeLiteState.EXTREME),
        reason_codes=("RG_EXTREME_BTC_DROP_1H",),
        btc_realized_vol_24h=0.09,
        btc_drop_1h=-0.08,
        intraday_drawdown=0.12,
        engine_return_dispersion=0.07,
    )
    path.write_text(assessment.model_dump_json(indent=2), encoding="utf-8")


def _write_regime_lite_safing_recommendation(path: Path) -> None:
    assessment = RegimeLiteAssessment(
        state=RegimeLiteState.EXTREME,
        candidate_state=RegimeLiteState.EXTREME,
        previous_state=RegimeLiteState.STRESSED,
        state_changed=True,
        state_entered_ts=1_700_000_000_000,
        entries_blocked_until_ts=1_700_086_400_000,
        entries_blocked=True,
        sudden_event=True,
        transition_path=(RegimeLiteState.STRESSED, RegimeLiteState.EXTREME),
        reason_codes=("RG_EXTREME_BTC_DROP_1H",),
        btc_realized_vol_24h=0.09,
        btc_drop_1h=-0.08,
        intraday_drawdown=0.12,
        engine_return_dispersion=0.07,
    )
    recommendation = build_regime_lite_safing_recommendation(
        assessment,
        source_runtime_mode=RuntimeMode.SHADOW,
        timestamp_ms=1_700_000_000_000,
    )
    path.write_text(recommendation.model_dump_json(indent=2), encoding="utf-8")


def _write_info_stress_assessment(path: Path) -> None:
    assessment = InfoStressAssessment(
        pair="BTCUSDT",
        level=InfoStressLevel.EXTREME,
        alert_count=3,
        reason_codes=(
            "INFO_STRESS_SPREAD_EXPLOSION",
            "INFO_STRESS_DEPTH_RATIO_COLLAPSE",
            "INFO_STRESS_CANCELLATION_SPIKE",
        ),
        entries_blocked=True,
        entries_blocked_until_ts=1_700_086_400,
        detail="info_stress reached EXTREME with 3 active anomaly signal(s)",
    )
    path.write_text(assessment.model_dump_json(indent=2), encoding="utf-8")


def test_shadow_daily_orchestrator_launcher_advances_to_next_dated_export_when_shadow_day_is_recorded():
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

        completed_dates = [record["session_date"] for record in state["completed_runs"]]
        assert completed_dates == ["2026-04-01", "2026-04-02"]
        assert all(record["shadow_day_recorded"] is True for record in state["completed_runs"])
        assert last_run["session_date"] == "2026-04-02"
        assert last_run["shadow_day_recorded"] is True
        assert isinstance(last_run["consecutive_days"], int)
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


def test_shadow_daily_orchestrator_launcher_accepts_execution_runtime_projection_path():
    launcher = _load_launcher_module()
    output_dir = _scratch_dir("launcher_runtime_projection")

    try:
        exports_root = output_dir / "exports_root"
        shadow_output_dir = output_dir / "shadow_session"
        projection_path = output_dir / "local_lab_execution_runtime_projection.json"
        day_one_dir = exports_root / "2026-04-01"
        day_one_dir.mkdir(parents=True, exist_ok=False)
        _write_daily_export(day_one_dir, "2026-04-01", "1")
        _write_execution_runtime_projection(projection_path)

        exit_code = launcher.main(
            [
                "--output-dir",
                str(output_dir),
                "--shadow-output-dir",
                str(shadow_output_dir),
                "--exports-root",
                str(exports_root),
                "--execution-runtime-projection-path",
                str(projection_path),
            ]
        )

        assert exit_code == 0

        last_run = json.loads(
            (output_dir / "shadow_daily_orchestrator.last_run.json").read_text(
                encoding="utf-8"
            )
        )
        assert last_run["execution_runtime_projection_ref"] == str(
            projection_path.resolve()
        )
        assert last_run["execution_runtime_projection_status"] == "ready"
        assert last_run["execution_runtime_projection_ready"] is True
        assert last_run["execution_runtime_projection_consumer_count"] == 3
        assert last_run["execution_runtime_projection_ready_consumer_count"] == 3
        assert last_run["execution_runtime_projection_partial_consumer_count"] == 0
        assert last_run["execution_runtime_projection_blocked_consumer_count"] == 0
        assert last_run["execution_runtime_projection_bridge_status"] == "healthy"
        assert last_run["execution_runtime_projection_bridge_loaded"] is True
        assert last_run["execution_runtime_projection_rate_limit_model_loaded"] is True
        assert last_run["execution_runtime_projection_spread_guard_model_loaded"] is True
        assert last_run["execution_runtime_projection_slippage_model_loaded"] is True
        assert last_run["regime_lite_governance_status"] == "not_configured"
        assert last_run["regime_lite_safing_severity"] == "not_configured"
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_read_regime_lite_governance_summary_projects_ready_shadow_summary():
    launcher = _load_launcher_module()

    summary = launcher._read_regime_lite_governance_summary(
        {
            "regime_lite_governance": {
                "status": "ready",
                "state": "extreme",
                "candidate_state": "extreme",
                "state_changed": True,
                "entries_blocked": True,
                "sudden_event": True,
                "safing_severity": "halt_recommended",
                "should_block_new_entries": True,
                "should_exit_all": True,
                "recommended_operator_action": "set_halted",
                "operator_safing_request_action": "set_halted",
                "operator_safing_request_source_runtime_mode": "shadow",
                "reason_codes": (
                    "RISK_REGIME_EXTREME",
                    "RISK_REGIME_EXTREME_EXIT_ALL",
                ),
                "detail": "EXTREME regime_lite state recommends HALT_RECOMMENDED",
            }
        }
    )

    assert summary["regime_lite_governance_status"] == "ready"
    assert summary["regime_lite_state"] == "extreme"
    assert summary["regime_lite_candidate_state"] == "extreme"
    assert summary["regime_lite_state_changed"] is True
    assert summary["regime_lite_entries_blocked"] is True
    assert summary["regime_lite_sudden_event"] is True
    assert summary["regime_lite_safing_severity"] == "halt_recommended"
    assert summary["regime_lite_safing_should_block_new_entries"] is True
    assert summary["regime_lite_safing_should_exit_all"] is True
    assert summary["regime_lite_safing_recommended_operator_action"] == "set_halted"
    assert summary["regime_lite_safing_operator_safing_request_action"] == "set_halted"
    assert (
        summary["regime_lite_safing_operator_safing_request_source_runtime_mode"]
        == "shadow"
    )
    assert summary["regime_lite_safing_reason_codes"] == (
        "RISK_REGIME_EXTREME",
        "RISK_REGIME_EXTREME_EXIT_ALL",
    )


def test_shadow_daily_orchestrator_launcher_accepts_regime_lite_inputs():
    launcher = _load_launcher_module()
    output_dir = _scratch_dir("launcher_regime_lite")

    try:
        exports_root = output_dir / "exports_root"
        shadow_output_dir = output_dir / "shadow_session"
        assessment_path = output_dir / "regime_lite_assessment.json"
        recommendation_path = output_dir / "regime_lite_safing_recommendation.json"
        day_one_dir = exports_root / "2026-04-01"
        day_one_dir.mkdir(parents=True, exist_ok=False)
        _write_daily_export(day_one_dir, "2026-04-01", "1")
        _write_regime_lite_assessment(assessment_path)
        _write_regime_lite_safing_recommendation(recommendation_path)

        exit_code = launcher.main(
            [
                "--output-dir",
                str(output_dir),
                "--shadow-output-dir",
                str(shadow_output_dir),
                "--exports-root",
                str(exports_root),
                "--regime-lite-assessment-path",
                str(assessment_path),
                "--regime-lite-safing-recommendation-path",
                str(recommendation_path),
            ]
        )

        assert exit_code == 0

        last_run = json.loads(
            (output_dir / "shadow_daily_orchestrator.last_run.json").read_text(
                encoding="utf-8"
            )
        )
        assert last_run["regime_lite_governance_status"] == "ready"
        assert last_run["regime_lite_state"] == "extreme"
        assert last_run["regime_lite_safing_severity"] == "halt_recommended"
        assert last_run["regime_lite_safing_should_exit_all"] is True
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_shadow_daily_orchestrator_launcher_autoloads_regime_lite_inputs_from_shadow_output_dir():
    launcher = _load_launcher_module()
    output_dir = _scratch_dir("launcher_regime_lite_autoload")

    try:
        exports_root = output_dir / "exports_root"
        shadow_output_dir = output_dir / "shadow_session"
        day_one_dir = exports_root / "2026-04-01"
        day_one_dir.mkdir(parents=True, exist_ok=False)
        shadow_output_dir.mkdir(parents=True, exist_ok=False)
        _write_daily_export(day_one_dir, "2026-04-01", "1")
        _write_regime_lite_assessment(
            shadow_output_dir / "regime_lite_assessment.json"
        )
        _write_regime_lite_safing_recommendation(
            shadow_output_dir / "regime_lite_safing_recommendation.json"
        )

        exit_code = launcher.main(
            [
                "--output-dir",
                str(output_dir),
                "--shadow-output-dir",
                str(shadow_output_dir),
                "--exports-root",
                str(exports_root),
            ]
        )

        assert exit_code == 0

        last_run = json.loads(
            (output_dir / "shadow_daily_orchestrator.last_run.json").read_text(
                encoding="utf-8"
            )
        )
        assert last_run["regime_lite_governance_status"] == "ready"
        assert last_run["regime_lite_state"] == "extreme"
        assert last_run["regime_lite_safing_severity"] == "halt_recommended"
        assert last_run["regime_lite_safing_should_exit_all"] is True
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_read_info_stress_governance_summary_projects_shadow_summary():
    launcher = _load_launcher_module()

    summary = launcher._read_info_stress_governance_summary(
        {
            "info_stress_governance": {
                "status": "assessment_only",
                "level": "extreme",
                "alert_count": 3,
                "entries_blocked": True,
                "entries_blocked_until_ts": 1_700_086_400,
                "reason_codes": (
                    "INFO_STRESS_SPREAD_EXPLOSION",
                    "INFO_STRESS_DEPTH_RATIO_COLLAPSE",
                ),
                "detail": "info_stress reached EXTREME with 3 active anomaly signal(s)",
            }
        }
    )

    assert summary["info_stress_governance_status"] == "assessment_only"
    assert summary["info_stress_level"] == "extreme"
    assert summary["info_stress_alert_count"] == 3
    assert summary["info_stress_entries_blocked"] is True
    assert summary["info_stress_entries_blocked_until_ts"] == 1_700_086_400
    assert summary["info_stress_reason_codes"] == (
        "INFO_STRESS_SPREAD_EXPLOSION",
        "INFO_STRESS_DEPTH_RATIO_COLLAPSE",
    )


def test_shadow_daily_orchestrator_launcher_accepts_info_stress_input():
    launcher = _load_launcher_module()
    output_dir = _scratch_dir("launcher_info_stress")

    try:
        exports_root = output_dir / "exports_root"
        shadow_output_dir = output_dir / "shadow_session"
        assessment_path = output_dir / "info_stress_assessment.json"
        day_one_dir = exports_root / "2026-04-01"
        day_one_dir.mkdir(parents=True, exist_ok=False)
        _write_daily_export(day_one_dir, "2026-04-01", "1")
        _write_info_stress_assessment(assessment_path)

        exit_code = launcher.main(
            [
                "--output-dir",
                str(output_dir),
                "--shadow-output-dir",
                str(shadow_output_dir),
                "--exports-root",
                str(exports_root),
                "--info-stress-assessment-path",
                str(assessment_path),
            ]
        )

        assert exit_code == 0

        last_run = json.loads(
            (output_dir / "shadow_daily_orchestrator.last_run.json").read_text(
                encoding="utf-8"
            )
        )
        assert last_run["info_stress_governance_status"] == "assessment_only"
        assert last_run["info_stress_level"] == "extreme"
        assert last_run["info_stress_alert_count"] == 3
        assert last_run["info_stress_entries_blocked"] is True
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_shadow_daily_orchestrator_launcher_autoloads_info_stress_input_from_shadow_output_dir():
    launcher = _load_launcher_module()
    output_dir = _scratch_dir("launcher_info_stress_autoload")

    try:
        exports_root = output_dir / "exports_root"
        shadow_output_dir = output_dir / "shadow_session"
        day_one_dir = exports_root / "2026-04-01"
        day_one_dir.mkdir(parents=True, exist_ok=False)
        shadow_output_dir.mkdir(parents=True, exist_ok=False)
        _write_daily_export(day_one_dir, "2026-04-01", "1")
        _write_info_stress_assessment(shadow_output_dir / "info_stress_assessment.json")

        exit_code = launcher.main(
            [
                "--output-dir",
                str(output_dir),
                "--shadow-output-dir",
                str(shadow_output_dir),
                "--exports-root",
                str(exports_root),
            ]
        )

        assert exit_code == 0

        last_run = json.loads(
            (output_dir / "shadow_daily_orchestrator.last_run.json").read_text(
                encoding="utf-8"
            )
        )
        assert last_run["info_stress_governance_status"] == "assessment_only"
        assert last_run["info_stress_level"] == "extreme"
        assert last_run["info_stress_entries_blocked"] is True
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
