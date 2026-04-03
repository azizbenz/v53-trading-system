"""Tests for the autonomous VPS Shadow service launcher."""

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
from protocols import (
    BinanceSpotLiveWebSocketAdapter,
    ShadowLiveWebSocketConfig,
    capture_live_websocket_snapshot_batch,
)


def _load_service_module():
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "scripts" / "run_shadow_vps_service.py"
    module_name = "test_run_shadow_vps_service"
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _scratch_dir(label: str) -> Path:
    repo_root = Path(__file__).resolve().parents[2]
    base_dir = repo_root / "build" / "shadow_vps_service_tests"
    base_dir.mkdir(parents=True, exist_ok=True)
    output_dir = base_dir / f"{label}_{uuid4().hex}"
    output_dir.mkdir(parents=True, exist_ok=False)
    return output_dir


def _read_runtime_evidence_bundle(service_dir: Path, session_date: str) -> dict:
    return json.loads(
        (
            service_dir
            / "runtime_evidence"
            / f"{session_date}.shadow_vps_runtime_evidence.json"
        ).read_text(encoding="utf-8")
    )


def _write_daily_export(export_dir: Path, session_date: str, run_suffix: str) -> None:
    execute_local_replay_export(
        export_dir,
        ReplayExecutionInput(
            run_manifest=ReplayRunManifest(
                run_id=f"run-shadow-vps-{run_suffix}",
                strategy_id=f"strategy-shadow-vps-{run_suffix}",
                strategy_version="a.v3.1",
                strategy_classification=StrategyClassification.A_VARIANT,
                lineage_version=f"a.v3.1.r{run_suffix}",
                profile_scope=ProfileId.LIGHT,
                engine_scope=("engine_a", "engine_b"),
                tested_pairs=("BTCUSDT", "ETHUSDT"),
                dataset_manifest_id=f"dataset-shadow-vps-{session_date}",
                timeframe_scope=f"{session_date}/{session_date}",
                feature_set_version="feature.v3",
                formula_set_version="formula.v3",
                scoring_version="score.v3",
                regime_version="regime.v3",
                risk_policy_version="risk.v3",
                cost_model_version="cost.v3",
                performance_mode="research_fast_mode",
                artifact_schema_version="artifact.v3",
                artifact_hash=f"artifact-shadow-vps-{run_suffix}",
                clock_id=f"clock-shadow-vps-{run_suffix}",
                start_timestamp_ms=1_700_000_000_000,
                end_timestamp_ms=1_700_003_600_000,
                tick_count=360,
                record_count=1024,
            ),
            total_opportunities=2,
            dtr_records=(
                build_dtr(
                    dtr_id=f"run-shadow-vps-{run_suffix}:dtr:1",
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
            review_notes=(f"vps service export {session_date}",),
        ),
    )


def _write_raw_dataset_input(raw_input_dir: Path, session_date: str) -> None:
    payload = [
        {
            "opportunity_id": f"raw-{session_date}-1",
            "timestamp_ms": 1_700_000_000_000,
            "pair": "BTCUSDT",
            "engine_id": "engine_a",
            "close_price": 43250.0,
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
            "gross_return_bps": 21.0,
            "feature_values": {"spread_bps": 3.0},
        },
        {
            "opportunity_id": f"raw-{session_date}-2",
            "timestamp_ms": 1_700_000_060_000,
            "pair": "ETHUSDT",
            "engine_id": "engine_b",
            "close_price": 2280.0,
            "raw_score": 0.81,
            "penalized_score": 0.79,
            "final_score": 0.76,
            "expected_edge_bps": 7.0,
            "spread_bps": 5.0,
            "slippage_bps": 3.0,
            "latency_penalty_bps": 1.0,
            "fill_ratio": 0.0,
            "target_decision_state": "rejected_ranking",
            "production_decision_state": "rejected_ranking",
            "production_final_score": 0.76,
            "production_expected_cost": 0.00094,
            "ranking_position": 3,
            "gross_return_bps": -4.0,
            "primary_reason": "rank_cutoff",
            "feature_values": {"spread_bps": 5.0},
        },
    ]
    (raw_input_dir / "replay_dataset.json").write_text(
        json.dumps(payload, indent=2),
        encoding="utf-8",
    )
    (raw_input_dir / "shadow_input_config.json").write_text(
        json.dumps(
            {
                "strategy_id": "strategy-shadow-vps-native",
                "strategy_version": "a.v4.0",
                "lineage_version": "a.v4.0.r1",
                "strategy_classification": "a_variant",
                "performance_mode": "research_fast_mode",
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def _write_websocket_stream_input(websocket_input_dir: Path, session_date: str) -> None:
    websocket_input_dir.joinpath("websocket_stream.jsonl").write_text(
        "\n".join(
            (
                json.dumps(
                    {
                        "endpoint": "wss://shadow.injected",
                        "pair": "BTCUSDT",
                        "stream_type": "snapshot",
                        "payload": {
                            "snapshot_type": "ticker",
                            "last_price": 43250.0,
                            "bid": 43249.5,
                            "ask": 43250.5,
                            "volume_24h": 125000.0,
                        },
                        "recv_time": 1700000000.0,
                        "source": "binance",
                        "route_hint": {
                            "route_id": f"btc-ws-{session_date}",
                            "engine_id": "engine_a",
                            "raw_score": 0.91,
                            "penalized_score": 0.88,
                            "final_score": 0.86,
                            "expected_edge_bps": 17.0,
                            "target_decision_state": "executed",
                            "production_decision_state": "executed",
                            "production_final_score": 0.86,
                            "production_expected_cost": 0.00086,
                            "candidate_size": 1.0,
                            "final_size": 1.0,
                            "gross_return_bps": 21.0,
                            "feature_values": {"spread_bps": 3.0},
                        },
                    }
                ),
                json.dumps(
                    {
                        "endpoint": "wss://shadow.injected",
                        "pair": "ETHUSDT",
                        "stream_type": "snapshot",
                        "payload": {
                            "snapshot_type": "ticker",
                            "last_price": 2280.0,
                            "bid": 2279.8,
                            "ask": 2280.2,
                            "volume_24h": 98000.0,
                        },
                        "recv_time": 1700000060.0,
                        "source": "binance",
                        "route_hint": {
                            "route_id": f"eth-ws-{session_date}",
                            "engine_id": "engine_b",
                            "raw_score": 0.81,
                            "penalized_score": 0.79,
                            "final_score": 0.76,
                            "expected_edge_bps": 7.0,
                            "ranking_position": 3,
                            "target_decision_state": "rejected_ranking",
                            "production_decision_state": "rejected_ranking",
                            "production_final_score": 0.76,
                            "production_expected_cost": 0.00094,
                            "primary_reason": "rank_cutoff",
                            "gross_return_bps": -4.0,
                            "feature_values": {"spread_bps": 5.0},
                        },
                    }
                ),
            )
        ),
        encoding="utf-8",
    )
    websocket_input_dir.joinpath("shadow_input_config.json").write_text(
        json.dumps(
            {
                "strategy_id": "strategy-shadow-vps-websocket",
                "strategy_version": "a.v4.1",
                "lineage_version": "a.v4.1.r1",
                "strategy_classification": "a_variant",
                "performance_mode": "research_fast_mode",
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def _write_live_websocket_config(config_path: Path, session_date: str) -> None:
    config_path.write_text(
        json.dumps(
            {
                "endpoint": "wss://stream.binance.com:9443/ws",
                "pairs": ["BTCUSDT"],
                "stream_types": ["trade", "ticker"],
                "capture_frame_limit": 2,
                "idle_poll_limit": 3,
                "capture_timeout_s": 5.0,
                "session_date_override": session_date,
                "route_hints_by_pair": {
                    "BTCUSDT": {
                        "route_id": f"btc-live-{session_date}",
                        "engine_id": "engine_a",
                        "raw_score": 0.91,
                        "penalized_score": 0.88,
                        "final_score": 0.86,
                        "expected_edge_bps": 17.0,
                        "target_decision_state": "executed",
                        "production_decision_state": "executed",
                        "production_final_score": 0.86,
                        "production_expected_cost": 0.00086,
                        "candidate_size": 1.0,
                        "final_size": 1.0,
                        "gross_return_bps": 21.0,
                        "feature_values": {"spread_bps": 3.0},
                    }
                },
                "config": {
                    "strategy_id": "strategy-shadow-vps-live",
                    "strategy_version": "a.v4.2",
                    "lineage_version": "a.v4.2.r1",
                    "strategy_classification": "a_variant",
                    "performance_mode": "research_fast_mode",
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def test_shadow_vps_service_processes_multiple_days_and_persists_logs():
    service = _load_service_module()
    output_dir = _scratch_dir("multi_day")

    try:
        service_dir = output_dir / "service"
        orchestrator_dir = output_dir / "orchestrator"
        shadow_output_dir = output_dir / "shadow_session"
        exports_root = output_dir / "exports_root"
        (exports_root / "2026-04-01").mkdir(parents=True, exist_ok=False)
        (exports_root / "2026-04-02").mkdir(parents=True, exist_ok=False)
        _write_daily_export(exports_root / "2026-04-01", "2026-04-01", "1")
        _write_daily_export(exports_root / "2026-04-02", "2026-04-02", "2")

        exit_code = service.main(
            [
                "--service-dir",
                str(service_dir),
                "--orchestrator-output-dir",
                str(orchestrator_dir),
                "--shadow-output-dir",
                str(shadow_output_dir),
                "--exports-root",
                str(exports_root),
                "--max-cycles",
                "2",
                "--poll-interval-s",
                "0",
            ]
        )

        assert exit_code == 0

        state = json.loads(
            (service_dir / "shadow_vps_service.state.json").read_text(
                encoding="utf-8"
            )
        )
        events = [
            json.loads(line)
            for line in (service_dir / "shadow_vps_service.events.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip()
        ]
        shadow_session_summary = json.loads(
            (shadow_output_dir / "local_replay_shadow.shadow_session_summary.json").read_text(
                encoding="utf-8"
            )
        )
        runtime_bundle = _read_runtime_evidence_bundle(service_dir, "2026-04-02")

        assert state["service_status"] == "stopped"
        assert state["loop_count"] == 2
        assert state["success_count"] == 2
        assert state["failure_count"] == 0
        assert state["last_completed_session_date"] == "2026-04-02"
        assert state["last_local_replay_evidence_ref"].endswith(
            "local_replay_shadow.local_replay_evidence.json"
        )
        assert state["last_shadow_runtime_evidence_ref"].endswith(
            "local_replay_shadow.shadow_runtime_evidence.json"
        )
        assert state["last_runtime_evidence_bundle_ref"].endswith(
            "runtime_evidence\\2026-04-02.shadow_vps_runtime_evidence.json"
        )
        assert shadow_session_summary["consecutive_days"] == 2
        assert runtime_bundle["acquisition_mode"] == "dated_export"
        assert runtime_bundle["runtime_data_source"] == "recorded_replay"
        assert runtime_bundle["accepted"] is False
        assert runtime_bundle["consecutive_days"] == 2

        event_types = [event["event_type"] for event in events]
        assert event_types[0] == "service_started"
        assert event_types.count("runtime_evidence_bundle_written") == 2
        assert event_types.count("shadow_day_completed") == 2
        assert event_types[-1] == "service_stopped"
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_shadow_vps_service_resumes_after_restart_and_consumes_next_day():
    service = _load_service_module()
    output_dir = _scratch_dir("resume")

    try:
        service_dir = output_dir / "service"
        orchestrator_dir = output_dir / "orchestrator"
        shadow_output_dir = output_dir / "shadow_session"
        exports_root = output_dir / "exports_root"
        (exports_root / "2026-04-01").mkdir(parents=True, exist_ok=False)
        _write_daily_export(exports_root / "2026-04-01", "2026-04-01", "1")

        first_exit = service.main(
            [
                "--service-dir",
                str(service_dir),
                "--orchestrator-output-dir",
                str(orchestrator_dir),
                "--shadow-output-dir",
                str(shadow_output_dir),
                "--exports-root",
                str(exports_root),
                "--max-cycles",
                "1",
                "--poll-interval-s",
                "0",
            ]
        )
        (exports_root / "2026-04-02").mkdir(parents=True, exist_ok=False)
        _write_daily_export(exports_root / "2026-04-02", "2026-04-02", "2")
        second_exit = service.main(
            [
                "--service-dir",
                str(service_dir),
                "--orchestrator-output-dir",
                str(orchestrator_dir),
                "--shadow-output-dir",
                str(shadow_output_dir),
                "--exports-root",
                str(exports_root),
                "--max-cycles",
                "1",
                "--poll-interval-s",
                "0",
            ]
        )

        assert first_exit == 0
        assert second_exit == 0

        state = json.loads(
            (service_dir / "shadow_vps_service.state.json").read_text(
                encoding="utf-8"
            )
        )
        events = [
            json.loads(line)
            for line in (service_dir / "shadow_vps_service.events.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip()
        ]

        assert state["resumed"] is True
        assert state["loop_count"] == 2
        assert state["success_count"] == 2
        assert state["last_completed_session_date"] == "2026-04-02"
        assert any(
            event["event_type"] == "service_started"
            and event["message"] == "Shadow VPS service resumed"
            for event in events
        )
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_shadow_vps_service_auto_exports_raw_inputs_then_runs_shadow():
    service = _load_service_module()
    output_dir = _scratch_dir("raw_inputs")

    try:
        service_dir = output_dir / "service"
        orchestrator_dir = output_dir / "orchestrator"
        shadow_output_dir = output_dir / "shadow_session"
        auto_exports_root = output_dir / "auto_exports"
        raw_inputs_root = output_dir / "raw_inputs_root"
        day_one_dir = raw_inputs_root / "2026-04-01"
        day_two_dir = raw_inputs_root / "2026-04-02"
        day_one_dir.mkdir(parents=True, exist_ok=False)
        day_two_dir.mkdir(parents=True, exist_ok=False)
        _write_raw_dataset_input(day_one_dir, "2026-04-01")
        _write_raw_dataset_input(day_two_dir, "2026-04-02")

        exit_code = service.main(
            [
                "--service-dir",
                str(service_dir),
                "--orchestrator-output-dir",
                str(orchestrator_dir),
                "--shadow-output-dir",
                str(shadow_output_dir),
                "--raw-inputs-root",
                str(raw_inputs_root),
                "--auto-exports-root",
                str(auto_exports_root),
                "--max-cycles",
                "2",
                "--poll-interval-s",
                "0",
            ]
        )

        assert exit_code == 0

        state = json.loads(
            (service_dir / "shadow_vps_service.state.json").read_text(
                encoding="utf-8"
            )
        )
        events = [
            json.loads(line)
            for line in (service_dir / "shadow_vps_service.events.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip()
        ]
        auto_manifest = json.loads(
            (auto_exports_root / "2026-04-02" / "replay_run_manifest.json").read_text(
                encoding="utf-8"
            )
        )
        runtime_bundle = _read_runtime_evidence_bundle(service_dir, "2026-04-02")

        assert state["success_count"] == 2
        assert state["last_completed_session_date"] == "2026-04-02"
        assert state["last_raw_input_dir_ref"].endswith("raw_inputs_root\\2026-04-02")
        assert state["last_auto_export_dir_ref"].endswith("auto_exports\\2026-04-02")
        assert state["last_runtime_evidence_bundle_ref"].endswith(
            "runtime_evidence\\2026-04-02.shadow_vps_runtime_evidence.json"
        )
        assert auto_manifest["strategy_id"] == "strategy-shadow-vps-native"
        assert runtime_bundle["acquisition_mode"] == "raw_input_auto_export"
        assert runtime_bundle["raw_input_dir_ref"].endswith("raw_inputs_root\\2026-04-02")
        assert runtime_bundle["auto_export_dir_ref"].endswith("auto_exports\\2026-04-02")
        assert runtime_bundle["runtime_data_source"] == "recorded_replay"
        assert any(
            event["event_type"] == "auto_export_completed"
            and event["session_date"] == "2026-04-01"
            for event in events
        )
        assert any(
            event["event_type"] == "auto_export_completed"
            and event["session_date"] == "2026-04-02"
            for event in events
        )
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_shadow_vps_service_auto_builds_snapshots_from_websocket_streams():
    service = _load_service_module()
    output_dir = _scratch_dir("websocket_inputs")

    try:
        service_dir = output_dir / "service"
        orchestrator_dir = output_dir / "orchestrator"
        shadow_output_dir = output_dir / "shadow_session"
        auto_snapshots_root = output_dir / "auto_snapshots"
        auto_exports_root = output_dir / "auto_exports"
        websocket_streams_root = output_dir / "websocket_streams_root"
        day_one_dir = websocket_streams_root / "2026-04-01"
        day_two_dir = websocket_streams_root / "2026-04-02"
        day_one_dir.mkdir(parents=True, exist_ok=False)
        day_two_dir.mkdir(parents=True, exist_ok=False)
        _write_websocket_stream_input(day_one_dir, "2026-04-01")
        _write_websocket_stream_input(day_two_dir, "2026-04-02")

        exit_code = service.main(
            [
                "--service-dir",
                str(service_dir),
                "--orchestrator-output-dir",
                str(orchestrator_dir),
                "--shadow-output-dir",
                str(shadow_output_dir),
                "--websocket-streams-root",
                str(websocket_streams_root),
                "--auto-snapshots-root",
                str(auto_snapshots_root),
                "--auto-exports-root",
                str(auto_exports_root),
                "--max-cycles",
                "2",
                "--poll-interval-s",
                "0",
            ]
        )

        assert exit_code == 0

        state = json.loads(
            (service_dir / "shadow_vps_service.state.json").read_text(
                encoding="utf-8"
            )
        )
        events = [
            json.loads(line)
            for line in (service_dir / "shadow_vps_service.events.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip()
        ]
        snapshot_summary = json.loads(
            (auto_snapshots_root / "2026-04-02" / "websocket_snapshot_ingest.json").read_text(
                encoding="utf-8"
            )
        )
        auto_manifest = json.loads(
            (auto_exports_root / "2026-04-02" / "replay_run_manifest.json").read_text(
                encoding="utf-8"
            )
        )
        runtime_bundle = _read_runtime_evidence_bundle(service_dir, "2026-04-02")

        assert state["success_count"] == 2
        assert state["last_completed_session_date"] == "2026-04-02"
        assert state["last_websocket_input_dir_ref"].endswith(
            "websocket_streams_root\\2026-04-02"
        )
        assert state["last_auto_snapshot_dir_ref"].endswith("auto_snapshots\\2026-04-02")
        assert state["last_auto_export_dir_ref"].endswith("auto_exports\\2026-04-02")
        assert state["last_runtime_evidence_bundle_ref"].endswith(
            "runtime_evidence\\2026-04-02.shadow_vps_runtime_evidence.json"
        )
        assert snapshot_summary["accepted_message_count"] == 2
        assert snapshot_summary["event_types"] == ["snapshot"]
        assert auto_manifest["strategy_id"] == "strategy-shadow-vps-websocket"
        assert runtime_bundle["acquisition_mode"] == "websocket_stream_auto_export"
        assert runtime_bundle["websocket_input_dir_ref"].endswith(
            "websocket_streams_root\\2026-04-02"
        )
        assert runtime_bundle["auto_snapshot_dir_ref"].endswith("auto_snapshots\\2026-04-02")
        assert runtime_bundle["auto_export_dir_ref"].endswith("auto_exports\\2026-04-02")
        assert runtime_bundle["runtime_data_source"] == "recorded_replay"
        assert any(
            event["event_type"] == "auto_snapshot_completed"
            and event["session_date"] == "2026-04-01"
            for event in events
        )
        assert any(
            event["event_type"] == "auto_export_completed"
            and event["session_date"] == "2026-04-02"
            for event in events
        )
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_shadow_vps_service_captures_native_live_websocket_then_runs_shadow(monkeypatch):
    service = _load_service_module()
    output_dir = _scratch_dir("live_websocket")

    try:
        service_dir = output_dir / "service"
        orchestrator_dir = output_dir / "orchestrator"
        shadow_output_dir = output_dir / "shadow_session"
        live_captures_root = output_dir / "live_captures"
        auto_exports_root = output_dir / "auto_exports"
        live_config_path = output_dir / "live_websocket_config.json"
        _write_live_websocket_config(live_config_path, "2026-04-02")

        class _FakeSocket:
            def __init__(self) -> None:
                self.payloads = [
                    json.dumps({"result": None, "id": 1}),
                    json.dumps(
                        {
                            "stream": "btcusdt@trade",
                            "data": {
                                "e": "trade",
                                "s": "BTCUSDT",
                                "t": 101,
                                "p": "43250.1",
                                "q": "0.250",
                                "m": False,
                            },
                        }
                    ),
                    json.dumps(
                        {
                            "stream": "btcusdt@ticker",
                            "data": {
                                "e": "24hrTicker",
                                "s": "BTCUSDT",
                                "c": "43255.0",
                                "b": "43254.5",
                                "a": "43255.5",
                                "v": "125000.0",
                                "h": "44000.0",
                                "l": "42000.0",
                            },
                        }
                    ),
                ]

            def settimeout(self, timeout: float) -> None:
                return None

            def send(self, payload: str) -> None:
                return None

            def recv(self) -> str | bytes | None:
                if not self.payloads:
                    raise TimeoutError("done")
                return self.payloads.pop(0)

            def close(self) -> None:
                return None

        def _fake_live_capture(config: ShadowLiveWebSocketConfig, *, output_dir: Path):
            return capture_live_websocket_snapshot_batch(
                config,
                output_dir=output_dir,
                adapter_factory=lambda cfg: BinanceSpotLiveWebSocketAdapter(
                    cfg,
                    socket_factory=lambda endpoint, connect_timeout_s, recv_timeout_s: _FakeSocket(),
                    clock=lambda: 1_700_000_000.0,
                ),
                clock=lambda: 1_700_000_000.0,
            )

        monkeypatch.setattr(service, "capture_live_websocket_snapshot_batch", _fake_live_capture)

        exit_code = service.main(
            [
                "--service-dir",
                str(service_dir),
                "--orchestrator-output-dir",
                str(orchestrator_dir),
                "--shadow-output-dir",
                str(shadow_output_dir),
                "--live-websocket-config",
                str(live_config_path),
                "--live-captures-root",
                str(live_captures_root),
                "--auto-exports-root",
                str(auto_exports_root),
                "--max-cycles",
                "1",
                "--poll-interval-s",
                "0",
            ]
        )

        assert exit_code == 0

        state = json.loads(
            (service_dir / "shadow_vps_service.state.json").read_text(
                encoding="utf-8"
            )
        )
        events = [
            json.loads(line)
            for line in (service_dir / "shadow_vps_service.events.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip()
        ]
        auto_manifest = json.loads(
            (auto_exports_root / "2026-04-02" / "replay_run_manifest.json").read_text(
                encoding="utf-8"
            )
        )
        runtime_bundle = _read_runtime_evidence_bundle(service_dir, "2026-04-02")

        assert state["success_count"] == 1
        assert state["last_completed_session_date"] == "2026-04-02"
        assert state["last_live_capture_dir_ref"].endswith("live_captures\\2026-04-02")
        assert state["last_auto_export_dir_ref"].endswith("auto_exports\\2026-04-02")
        assert state["last_shadow_runtime_evidence_ref"].endswith(
            "local_replay_shadow.shadow_runtime_evidence.json"
        )
        assert state["last_runtime_evidence_bundle_ref"].endswith(
            "runtime_evidence\\2026-04-02.shadow_vps_runtime_evidence.json"
        )
        assert auto_manifest["strategy_id"] == "strategy-shadow-vps-live"
        assert runtime_bundle["acquisition_mode"] == "native_live_websocket_auto_export"
        assert runtime_bundle["live_capture_dir_ref"].endswith("live_captures\\2026-04-02")
        assert runtime_bundle["auto_export_dir_ref"].endswith("auto_exports\\2026-04-02")
        assert runtime_bundle["runtime_data_source"] == "recorded_replay"
        assert runtime_bundle["accepted"] is False
        assert runtime_bundle["consecutive_days"] == 1
        assert any(event["event_type"] == "live_capture_completed" for event in events)
        assert any(
            event["event_type"] == "runtime_evidence_bundle_written" for event in events
        )
        assert any(event["event_type"] == "shadow_day_completed" for event in events)
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
