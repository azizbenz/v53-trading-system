"""Tests for the local technical dashboard launcher."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import pytest
import shutil
import sys
from uuid import uuid4

from interface_contracts import ProfileId, RuntimeMode
from monitoring import MonitoringRuntime
from ui import LightUIRuntime, OperatorActionRequest, OperatorActionType


def _load_launcher_module():
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "scripts" / "run_technical_dashboard.py"
    module_name = "test_run_technical_dashboard_launcher"
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _scratch_dir(label: str) -> Path:
    repo_root = Path(__file__).resolve().parents[2]
    base_dir = repo_root / "build" / "technical_dashboard_launcher_tests"
    base_dir.mkdir(parents=True, exist_ok=True)
    output_dir = base_dir / f"{label}_{uuid4().hex}"
    output_dir.mkdir(parents=True, exist_ok=False)
    return output_dir


def test_export_technical_dashboard_writes_availability_view():
    launcher = _load_launcher_module()
    output_dir = _scratch_dir("availability")

    try:
        artifacts = launcher.export_technical_dashboard(
            output_dir,
            prefer_local_runtime_artifacts=False,
        )

        assert artifacts.html_path.exists()
        html = artifacts.html_path.read_text(encoding="utf-8")
        assert "availability_only" in html
        assert "No monitoring snapshot loaded" in html
        assert "Live Market Lab" in html
        assert "BTCUSDT" in html
        assert "ETHUSDT" in html
        assert "1m" in html
        assert "15m" in html
        assert "1h" in html
        assert "4h" in html
        assert "1d" in html
        assert "Candles" in html
        assert "Line" in html
        assert "LIVE_PAIRS = [\"BTCUSDT\", \"ETHUSDT\"]" in html
        assert "data-section-key='pairs'" in html
        assert "data-section-key='data-infra'" in html
        assert "data-section-key='alerts'" in html
        assert "Account / User Data" in html
        assert "data-card-key='pairs_empty'" in html
        assert "bookTicker" in html
        assert "@depth" in html
        assert "No liquidity data loaded yet." in html
        assert "stream.binance.com:9443/stream?streams=" in html
        assert "Build-10" in html
        assert "Build-11 Shadow" in html
        assert "Build-12 Micro-live" in html
        assert "Build-13 Live" in html
        assert "Build-14 Enablers" in html
        assert "7 available" in html
        assert "Governance &amp; Readiness" in html
        assert artifacts.payload_json_path is None
        assert artifacts.view_json_path is None
        assert artifacts.observability_text_path is None
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_export_technical_dashboard_writes_demo_sidecars():
    launcher = _load_launcher_module()
    output_dir = _scratch_dir("demo")

    try:
        artifacts = launcher.export_technical_dashboard(output_dir, demo=True)

        assert artifacts.html_path.exists()
        assert artifacts.payload_json_path is not None and artifacts.payload_json_path.exists()
        assert artifacts.view_json_path is not None and artifacts.view_json_path.exists()
        assert artifacts.observability_text_path is not None and artifacts.observability_text_path.exists()
        assert (
            artifacts.local_replay_evidence_json_path is not None
            and artifacts.local_replay_evidence_json_path.exists()
        )
        assert artifacts.upload_request_json_path is not None and artifacts.upload_request_json_path.exists()
        assert artifacts.upload_decision_json_path is not None and artifacts.upload_decision_json_path.exists()
        assert (
            artifacts.shadow_runtime_evidence_json_path is not None
            and artifacts.shadow_runtime_evidence_json_path.exists()
        )

        html = artifacts.html_path.read_text(encoding="utf-8")
        payload_json = artifacts.payload_json_path.read_text(encoding="utf-8")
        payload = json.loads(payload_json)
        observability_text = artifacts.observability_text_path.read_text(encoding="utf-8")
        upload_request = json.loads(
            artifacts.upload_request_json_path.read_text(encoding="utf-8")
        )
        upload_decision = json.loads(
            artifacts.upload_decision_json_path.read_text(encoding="utf-8")
        )
        local_replay_evidence = json.loads(
            artifacts.local_replay_evidence_json_path.read_text(encoding="utf-8")
        )
        shadow_runtime_evidence = json.loads(
            artifacts.shadow_runtime_evidence_json_path.read_text(encoding="utf-8")
        )

        assert "demo payload" in html.lower()
        assert "Live Market Lab" in html
        assert "1m" in html
        assert "LIVE_PAIRS = [\"BTCUSDT\", \"ETHUSDT\"]" in html
        assert "data-card-key='pair_ethusdt'" in html
        assert "api.binance.com/api/v3/klines" in html
        assert "bookTicker" in html
        assert "@depth" in html
        assert "Build-10" in html
        assert "Build-11 Shadow" in html
        assert "Build-12 Micro-live" in html
        assert "Build-13 Live" in html
        assert "Engine Judgement" in html
        assert "promotable" in html
        assert "dormant" in html
        assert "Strategy Onboarding" in html
        assert "Account / User Data" in html
        assert "Build-14 Enablers" in html
        assert "Observability Export" in html
        assert '"correlation_id": "corr-tech-demo"' in payload_json
        assert '"engine_judgment"' in payload_json
        assert '"shadow"' in payload_json
        assert '"micro_live"' in payload_json
        assert '"live_light"' in payload_json
        assert '"build14"' in payload_json
        assert '"reader_projections"' in payload_json
        assert "v53_system_headline_status" in observability_text
        assert "v53_shadow_run_state" in observability_text
        assert "v53_micro_live_run_state" in observability_text
        assert "v53_live_light_run_state" in observability_text
        assert "v53_build14_status" in observability_text
        assert "v53_build14_reader_value" in observability_text
        assert 'reader="market_toxicity_snapshot"' in observability_text
        assert '"validation_status": "accepted"' in payload_json
        assert '"feature_lineage_status": "ok"' in payload_json
        assert '"transform_whitelist_status": "ok"' in payload_json
        assert '"signature_check_status": "verified"' in payload_json
        assert '"run_state": "completed"' in payload_json
        assert upload_request["upload_context"] == "LOCAL_LAB"
        assert upload_request["dry_run"] is True
        assert upload_decision["accepted"] is True
        assert upload_decision["status"] == "DRY_RUN_OK"
        assert payload["engine_judgment"]["source_shadow_days_completed"] == 30
        assert payload["engine_judgment"]["source_shadow_required_days"] == 30
        assert payload["engine_judgment"]["cards"][0]["judgment_verdict"] == "promotable"
        assert payload["engine_judgment"]["cards"][2]["judgment_verdict"] == "dormant"
        assert local_replay_evidence["data_source"] == "recorded_replay"
        assert local_replay_evidence["replay_useful_ready"] is True
        assert shadow_runtime_evidence["data_source"] == "recorded_replay"
        assert shadow_runtime_evidence["event_loop_ready"] is True
        assert shadow_runtime_evidence["config_loaded"] is True
        assert shadow_runtime_evidence["shadow_dtr_persisted"] is True
        assert shadow_runtime_evidence["continuous_hours"] >= 24.0
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_load_artifact_import_summary_backfills_legacy_source_profile():
    launcher = _load_launcher_module()
    output_dir = _scratch_dir("legacy_import_summary")

    try:
        summary_path = output_dir / "legacy.import_summary.json"
        summary_path.write_text(
            json.dumps(
                {
                    "artifact_id": "artifact-legacy-1",
                    "correlation_id": "corr-legacy-1",
                    "artifact_kind": "review_packet",
                    "strategy_classification": "a_variant",
                    "lineage_version": "a.v1.0.r1",
                    "exported_from": "local",
                    "payload_ref_count": 5,
                    "accepted": True,
                    "validation_status": "accepted",
                    "normalized_promotion_state": "shadow_candidate",
                    "review_state": "pending",
                    "rejection_reasons": [],
                }
            ),
            encoding="utf-8",
        )

        summary = launcher._load_artifact_import_summary(
            summary_path,
            fallback_source_profile=ProfileId.COMPLETE,
        )

        assert summary.source_profile == ProfileId.COMPLETE
        assert summary.exported_from == "local"
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_launcher_main_accepts_demo_output_dir():
    launcher = _load_launcher_module()
    output_dir = _scratch_dir("cli")

    try:
        exit_code = launcher.main(["--demo", "--output-dir", str(output_dir)])

        assert exit_code == 0
        assert (output_dir / "technical_dashboard.html").exists()
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_export_technical_dashboard_prefers_local_runtime_artifacts_when_available():
    launcher = _load_launcher_module()
    repo_root = Path(__file__).resolve().parents[2]
    artifact_root = repo_root / "build" / "build11_live_websocket_campaign"
    candidate_payload = artifact_root / "shadow_session" / "local_replay_shadow.candidate_payload.json"
    shadow_summary = artifact_root / "shadow_session" / "local_replay_shadow.shadow_summary.json"
    campaign_summary = artifact_root / "service" / "shadow_vps_service.campaign_summary.json"
    if not (candidate_payload.exists() and shadow_summary.exists() and campaign_summary.exists()):
        pytest.skip("local runtime artifact campaign not present in workspace")

    output_dir = _scratch_dir("live_artifacts")
    try:
        artifacts = launcher.export_technical_dashboard(
            output_dir,
            local_runtime_root=artifact_root,
        )

        assert artifacts.payload_json_path is not None and artifacts.payload_json_path.exists()
        assert artifacts.view_json_path is not None and artifacts.view_json_path.exists()
        assert artifacts.observability_text_path is not None and artifacts.observability_text_path.exists()

        html = artifacts.html_path.read_text(encoding="utf-8")
        payload = json.loads(artifacts.payload_json_path.read_text(encoding="utf-8"))

        assert "local_runtime_artifacts" in html
        assert "engine_a" in html
        assert "engine_b" in html
        assert "engine_c" in html
        assert "engine_d" in html
        assert "Engine Judgement" in html
        assert "shadow-only" in html
        assert "Build-11 Shadow" in html
        assert "Build-12 Micro-live" in html
        assert "Build-13 Live" in html
        assert "Build-14 Enablers" in html
        assert "Account / User Data" in html
        assert "technical_supervision" in html
        assert "observability_export" in html
        assert payload["profile"] == "complete"
        assert payload["shadow"]["shadow_days_completed"] == 1
        assert payload["shadow"]["shadow_required_days"] == 30
        assert payload["engine_judgment"]["source_shadow_days_completed"] == 1
        assert payload["engine_judgment"]["cards"][0]["judgment_verdict"] == "shadow-only"
        assert payload["micro_live"]["verdict"] == "blocked"
        assert payload["live_light"]["verdict"] == "blocked"
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_export_technical_dashboard_projects_authenticated_user_data_when_runtime_root_has_it():
    launcher = _load_launcher_module()
    repo_root = Path(__file__).resolve().parents[2]
    runtime_root = repo_root / "build" / "binance_user_data_smoke_fresh"
    campaign_summary = runtime_root / "service" / "shadow_vps_service.campaign_summary.json"
    if not campaign_summary.exists():
        pytest.skip("binance_user_data_smoke_fresh runtime artifacts not present in workspace")

    output_dir = _scratch_dir("user_data_runtime")
    try:
        artifacts = launcher.export_technical_dashboard(
            output_dir,
            local_runtime_root=runtime_root,
        )

        assert artifacts.payload_json_path is not None and artifacts.payload_json_path.exists()
        html = artifacts.html_path.read_text(encoding="utf-8")
        payload = json.loads(artifacts.payload_json_path.read_text(encoding="utf-8"))

        assert "Account / User Data" in html
        assert payload["account_user_data"]["authenticated"] is True
        assert payload["account_user_data"]["subscription_id"] == 0
        assert payload["account_user_data"]["pair_scope"] == ["BTCUSDT", "ETHUSDT"]
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_export_technical_dashboard_propagates_micro_live_safing_request():
    launcher = _load_launcher_module()
    output_dir = _scratch_dir("demo_micro_live_safing")
    light_ui_runtime = LightUIRuntime()
    light_ui_runtime.submit_action(
        OperatorActionRequest(
            timestamp_ms=1_700_000_000_250,
            correlation_id="corr-tech-demo",
            profile=ProfileId.LIGHT,
            runtime_mode=RuntimeMode.MICRO_LIVE,
            action=OperatorActionType.DOWNGRADE_TO_SHADOW,
            reason="manual requalification requested",
        )
    )
    monitoring_runtime = MonitoringRuntime(light_ui_runtime=light_ui_runtime)

    try:
        artifacts = launcher.export_technical_dashboard(
            output_dir,
            demo=True,
            monitoring_runtime=monitoring_runtime,
        )

        assert artifacts.payload_json_path is not None
        payload = json.loads(artifacts.payload_json_path.read_text(encoding="utf-8"))
        assert payload["micro_live"]["operator_safing_action"] == "downgrade_to_shadow"
        assert payload["micro_live"]["operator_safing_target_runtime_mode"] == "shadow"
        assert payload["micro_live"]["operator_safing_reason"] == "manual requalification requested"
        assert payload["micro_live"]["run_state"] == "blocked"
        assert payload["micro_live"]["verdict"] == "blocked"
        assert any(
            "operator safing request: downgrade_to_shadow (micro_live -> shadow) reason=manual requalification requested"
            in reason
            for reason in payload["micro_live"]["blocking_reasons"]
        )
        assert payload["live_light"]["operator_safing_action"] == ""
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_export_technical_dashboard_propagates_live_safing_request():
    launcher = _load_launcher_module()
    output_dir = _scratch_dir("demo_live_safing")
    light_ui_runtime = LightUIRuntime()
    light_ui_runtime.submit_action(
        OperatorActionRequest(
            timestamp_ms=1_700_000_000_260,
            correlation_id="corr-tech-demo",
            profile=ProfileId.LIGHT,
            runtime_mode=RuntimeMode.LIVE,
            action=OperatorActionType.DOWNGRADE_TO_MICRO_LIVE,
            reason="execution drift requires step-down",
        )
    )
    monitoring_runtime = MonitoringRuntime(light_ui_runtime=light_ui_runtime)

    try:
        artifacts = launcher.export_technical_dashboard(
            output_dir,
            demo=True,
            monitoring_runtime=monitoring_runtime,
        )

        assert artifacts.payload_json_path is not None
        payload = json.loads(artifacts.payload_json_path.read_text(encoding="utf-8"))
        assert payload["live_light"]["operator_safing_action"] == "downgrade_to_micro_live"
        assert payload["live_light"]["operator_safing_target_runtime_mode"] == "micro_live"
        assert payload["live_light"]["operator_safing_reason"] == "execution drift requires step-down"
        assert payload["live_light"]["run_state"] == "blocked"
        assert payload["live_light"]["verdict"] == "blocked"
        assert any(
            "operator safing request: downgrade_to_micro_live (live -> micro_live) reason=execution drift requires step-down"
            in reason
            for reason in payload["live_light"]["blocking_reasons"]
        )
        assert payload["micro_live"]["operator_safing_action"] == ""
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
