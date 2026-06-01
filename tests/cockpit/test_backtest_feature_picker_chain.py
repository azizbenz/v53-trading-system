from __future__ import annotations

import json
from pathlib import Path
import re
from types import SimpleNamespace

from fastapi.testclient import TestClient

from cockpit.action_support import (
    CockpitBacktestJobKind,
    CockpitBacktestJobRecord,
    CockpitBacktestJobStatus,
)
from cockpit.backtest_state_support import (
    BacktestMlChainState,
    Patch6NormalizedRequest,
    read_backtest_ml_chain_state,
    read_launch_request_state,
    write_backtest_ml_chain_state,
)
from cockpit.form_state_support import (
    BacktestFormState,
    read_backtest_form_state,
    write_backtest_form_state,
)
from cockpit.queue_support import initialize_dashboard_command_queue
from cockpit.runtime_support import (
    CockpitRuntimeSurfaces,
    StrategyLadderBacktestSummary,
)
from cockpit.server import create_app
from cockpit.state import CockpitPaths, build_dashboard_view_model
from cockpit.strategy_ladder_workflow_support import PHASE_A2, PHASE_B1, PHASE_B2
from cockpit.strategy_ladder_ml_handoff_support import (
    resolve_backtest_feature_picker_defaults,
)
from local_replay_runtime.expected_edge_feature_promotion_registry import (
    ExpectedEdgeFeatureVerdict,
    FeaturePromotionEntry,
)


def _build_client(tmp_path: Path) -> TestClient:
    service_dir = tmp_path / "service"
    service_dir.mkdir(parents=True, exist_ok=True)
    auto_exports_root = tmp_path / "auto_exports"
    auto_exports_root.mkdir(parents=True, exist_ok=True)
    queue_root = tmp_path / "dashboard_command_queue"
    initialize_dashboard_command_queue(queue_root)
    backtest_jobs_root = tmp_path / "backtest_jobs"
    backtest_jobs_root.mkdir(parents=True, exist_ok=True)
    artifact_ingress_root = tmp_path / "artifact_ingress"
    artifact_ingress_root.mkdir(parents=True, exist_ok=True)
    observability_output_dir = tmp_path / "observability"
    observability_output_dir.mkdir(parents=True, exist_ok=True)
    live_websocket_config = tmp_path / "live_websocket.json"
    live_websocket_config.write_text("{}", encoding="utf-8")
    paths = CockpitPaths(
        service_dir=service_dir,
        pid_file=tmp_path / "cockpit.pid",
        log_file=service_dir / "shadow_service.log",
        auto_exports_root=auto_exports_root,
        live_websocket_config=live_websocket_config,
        calibration_thresholds=tmp_path / "thresholds.yml",
        build_root=tmp_path / "build_root",
        dashboard_command_queue_root=queue_root,
        observability_output_dir=observability_output_dir,
        backtest_jobs_root=backtest_jobs_root,
        artifact_ingress_root=artifact_ingress_root,
    )
    app = create_app(
        paths=paths,
        grafana_url="http://127.0.0.1:3000",
        prometheus_url="http://127.0.0.1:9090",
    )
    return TestClient(app)


def _fixture_orderbook_source() -> Path:
    return (
        Path(__file__).resolve().parents[1]
        / "fixtures"
        / "orderbook"
        / "BTCUSDT"
        / "2025-04-29_BTCUSDT_ob200.data"
    )


def _copy_orderbook_fixture(target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(_fixture_orderbook_source().read_text(encoding="utf-8"), encoding="utf-8")


def _write_trade_fixture(path: Path, *, timestamp_ms: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "id,timestamp,price,volume,side\n"
        f"1,{timestamp_ms},100.0,1.0,buy\n",
        encoding="utf-8",
    )


def _write_kline_fixture(path: Path, *, timestamp_ms: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "startTime,open,high,low,close,volume,turnover\n"
        f"{timestamp_ms},100,101,99,100.5,10,1005\n",
        encoding="utf-8",
    )


def _latest_preview_payload(jobs_root: Path) -> dict[str, object]:
    previews_root = jobs_root / "previews"
    manifests = sorted(
        previews_root.glob("*/source_date_preview_manifest.json"),
        key=lambda path: path.stat().st_mtime,
    )
    assert manifests, "expected at least one preview manifest"
    return json.loads(manifests[-1].read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_ready_phase_a2_artifacts(workflow_root: Path) -> None:
    phase_a2_root = workflow_root / "phase_a2_data_factory"
    (phase_a2_root / "gold").mkdir(parents=True, exist_ok=True)
    _write_json(
        phase_a2_root / "data_factory_manifest.json",
        {
            "data_factory_status": "DATA_FACTORY_READY",
            "raw_source_status": "RAW_SOURCE_READY",
            "pair_universe_status": "PAIR_UNIVERSE_READY",
            "silver_index_status": "SILVER_INDEX_READY",
            "gold_feature_store_status": "GOLD_FEATURE_STORE_READY",
        },
    )
    _write_json(phase_a2_root / "silver_index.json", {"storage_format": "jsonl_gz"})


def _write_ready_phase_b1_artifacts(workflow_root: Path, workflow_run_id: str) -> None:
    phase_b1_run_root = (
        workflow_root
        / "phase_b1_candidate_discovery"
        / "backtest_strategy_ladder"
        / workflow_run_id
    )
    fast_candidate_events = phase_b1_run_root / "fast_candidates" / "candidate_events.jsonl"
    fast_candidate_events.parent.mkdir(parents=True, exist_ok=True)
    fast_candidate_events.write_text(
        json.dumps({"candidate_id": "cand-1"}) + "\n",
        encoding="utf-8",
    )
    (phase_b1_run_root / "reports").mkdir(parents=True, exist_ok=True)
    (phase_b1_run_root / "preselection_candidates.jsonl").write_text(
        json.dumps({"candidate_id": "cand-1"}) + "\n",
        encoding="utf-8",
    )
    _write_json(
        phase_b1_run_root / "reports" / "preselection_summary.json",
        {
            "status": "ENGINE_NATIVE_PRESELECTION_READY",
            "replay_input_mode_status": "PRESELECTED_ONLY",
            "engine_native_preselected_count": 1,
        },
    )


def _checked_feature_names_from_html(html: str) -> tuple[str, ...]:
    checked: list[str] = []
    for match in re.finditer(
        r"<input\b(?=[^>]*\bname=\"selected_features\")[^>]*>",
        html,
    ):
        tag = match.group(0)
        if not re.search(r"\bchecked\b", tag):
            continue
        value_match = re.search(r"\bvalue=\"([^\"]+)\"", tag)
        if value_match:
            checked.append(value_match.group(1))
    return tuple(checked)


def _entry(feature_name: str, verdict: ExpectedEdgeFeatureVerdict) -> FeaturePromotionEntry:
    return FeaturePromotionEntry(
        pair="BTCUSDT",
        timeframe="1m",
        feature_name=feature_name,
        verdict=verdict,
        shap_rank=1,
        ablation_delta_psr=0.07,
        ablation_delta_sharpe=0.03,
        ablation_delta_break_even_bps=1.2,
        talab_quadruple_pass=True,
        min_btl_required=252,
        min_btl_satisfied=True,
        evidence_artifact_ref="E:/artifact.json",
    )


def _post_backtest_form(
    client: TestClient,
    *,
    intent: str,
    action_name: str,
    export_dir: str,
    orderbook_path: str,
    trades_path: str,
    klines_path: str,
    start: str,
    end: str,
    preview_id: str = "",
    request_hash: str = "",
    workflow_run_id: str = "",
    selected_features: tuple[str, ...] = (),
    feature_picker_enabled: str = "1",
    ml_mode: str = "ML_MODE_OFF",
    training_timeframe: str = "1m",
    backtest_timeframes: str = "1m",
) -> object:
    data = {
        "action_name": action_name,
        "intent": intent,
        "preview_id": preview_id,
        "request_hash": request_hash,
        "workflow_run_id": workflow_run_id,
        "export_dir": export_dir,
        "orderbook_path": orderbook_path,
        "trades_path": trades_path,
        "klines_path": klines_path,
        "start": start,
        "end": end,
        "output_root": export_dir,
        "candidate_discovery_mode": "SAMPLE_CAPPED_DEBUG",
        "engine_native_sample_size": "10",
        "b1_5_policy_mode": "conservative_hard_only",
        "preselected_only": "true",
        "silver_storage_mode": "jsonl_gz",
        "ml_mode": ml_mode,
        "training_timeframe": training_timeframe,
        "backtest_timeframes": backtest_timeframes,
        "feature_names": ",".join(selected_features) or "close_return,high_low_range,volume",
        "feature_picker_enabled": feature_picker_enabled,
        "selected_features": list(selected_features),
        "signed_by": "tester",
    }
    return client.post("/backtest/run", data=data, follow_redirects=False)


def _write_minimal_handoff_run(run_root: Path, *, feature_names: tuple[str, ...]) -> None:
    run_root.mkdir(parents=True, exist_ok=True)
    artifact_path = run_root / "bundle.json"
    artifact_path.write_text("{}", encoding="utf-8")
    (run_root / "strategy_ladder_ml_lab_handoff_report.json").write_text(
        json.dumps(
            {
                "status": "HANDOFF_READY",
                "ready": True,
                "pair": "BTCUSDT",
                "timeframe": "1m",
                "feature_names": list(feature_names),
                "train_start": "2025-01-01",
                "train_end": "2025-06-28",
                "requested_backtest_start": "2025-06-29",
                "requested_backtest_end": "2025-06-30",
                "artifact_stale_after": "2025-07-29",
                "max_valid_backtest_end": "2025-07-29",
                "source_artifact_ref": str(artifact_path),
                "transport_artifact_ref": str(artifact_path),
                "anti_leakage_proof_ref": "proof://anti_leakage",
                "artifact_hash": "a" * 64,
                "train_days": 180,
                "validation_days": 30,
                "freshness_days": 30,
                "chunk_days": 30,
            }
        ),
        encoding="utf-8",
    )
    (run_root / "strategy_ladder_backtest_ml_input.json").write_text(
        json.dumps(
            {
                "pair": "BTCUSDT",
                "timeframe": "1m",
                "timeframe_scope": ["1m"],
                "requested_backtest_start": "2025-06-29",
                "requested_backtest_end": "2025-06-30",
                "artifact_stale_after": "2025-07-29",
                "max_valid_backtest_end": "2025-07-29",
                "frozen_ml_artifact_path": str(artifact_path),
                "frozen_ml_artifact_hash": "a" * 64,
                "rolling_ml_window_plan_ref": "",
                "train_days": 180,
                "validation_days": 30,
                "freshness_days": 30,
                "chunk_days": 30,
            }
        ),
        encoding="utf-8",
    )
    (run_root / "strategy_ladder_expected_edge_ml_model_bundle.summary.json").write_text(
        json.dumps(
            {
                "feature_names": list(feature_names),
                "timeframe_scope": ["1m"],
            }
        ),
        encoding="utf-8",
    )


def test_backtest_feature_picker_renders_and_exposes_multiframe_scope(tmp_path: Path) -> None:
    client = _build_client(tmp_path)
    response = client.get("/backtest")
    assert response.status_code == 200
    assert response.text.count('name="selected_features" value="') == 25
    assert 'name="selected_features_csv"' in response.text
    assert 'id="backtest-run-form"' in response.text
    # Patch A (2026-05-31) — the run-form JS moved to the external static bundle
    # (static/backtest_page.js contains document.getElementById("backtest-run-form"));
    # the page wires it via <script src> so the inline string is no longer in the HTML.
    assert '/static/backtest_page.js' in response.text
    assert 'document.querySelector(\'form[action="/backtest/run"]\')' not in response.text
    assert response.text.count('form="backtest-run-form"') >= 28
    assert 'name="backtest_timeframes"' in response.text
    assert 'name="training_timeframe"' in response.text
    assert "Backtest timeframe scope" in response.text
    for timeframe in ("1m", "5m", "10m", "15m"):
        assert f'value="{timeframe}"' in response.text


def test_backtest_explicit_empty_feature_selection_stays_empty() -> None:
    state = BacktestFormState(
        feature_names="close_return,high_low_range,volume",
        selected_features=(),
        feature_picker_enabled="1",
    )
    defaults = resolve_backtest_feature_picker_defaults(
        form_state=state,
        governance_entries=(
            _entry("vpin", ExpectedEdgeFeatureVerdict.PROMOTED),
            _entry("kyle_lambda", ExpectedEdgeFeatureVerdict.PROMOTED),
        ),
        supported_feature_names=("close_return", "high_low_range", "volume", "vpin", "kyle_lambda"),
    )
    assert defaults == ()


def test_backtest_form_state_uses_csv_mirror_when_checkbox_payload_is_missing() -> None:
    from cockpit.server import _build_backtest_form_state

    built = _build_backtest_form_state(
        current_form=BacktestFormState(),
        job_kind="",
        selected_action_name="PHASE_B1_CANDIDATE_DISCOVERY",
        resolved_phase_id="PHASE_B1",
        workflow_phase="PHASE_B1",
        workflow_run_id="",
        export_dir="",
        baseline_export_dir="",
        raw_source_manifest_path="",
        raw_roots="",
        pairs="BTCUSDT",
        start="2025-04-29",
        end="2025-04-30",
        ml_mode="ML_MODE_OFF",
        training_timeframe="5m",
        feature_names="close_return,high_low_range,volume",
        selected_features=[],
        feature_picker_enabled="1",
        backtest_timeframes="5m,15m",
        expected_edge_artifact_mode="MONO_PAIR_LEGACY",
        ml_handoff_run_root="",
        frozen_ml_artifact_path="",
        frozen_ml_artifact_hash="",
        rolling_ml_window_plan_path="",
        ml_artifact_freshness_days=30,
        allow_broad_run="",
        confirm_broad_run="",
        candidate_discovery_mode="SAMPLE_CAPPED_DEBUG",
        engine_native_sample_size=10,
        b1_5_policy_mode="conservative_hard_only",
        preselected_only="true",
        diagnostic_full_replay="",
        small_scope_enabled="",
        full_scan_enabled="",
        silver_storage_mode="jsonl_debug",
        debug_storage_override="",
        signed_by="tester",
        orderbook_path="",
        klines_path="",
        trades_path="",
        metadata_path="",
        output_root="",
        selected_features_csv="vpin,kyle_lambda",
    )
    assert built.selected_features == ("vpin", "kyle_lambda")
    assert built.feature_names == "vpin,kyle_lambda"
    assert built.backtest_timeframes == ("5m", "15m")


def test_backtest_form_state_uses_non_default_feature_names_when_mirrors_are_missing() -> None:
    from cockpit.server import _build_backtest_form_state

    built = _build_backtest_form_state(
        current_form=BacktestFormState(),
        job_kind="",
        selected_action_name="PHASE_A1_PREVIEW",
        resolved_phase_id="PHASE_A1",
        workflow_phase="PHASE_A1",
        workflow_run_id="",
        export_dir="",
        baseline_export_dir="",
        raw_source_manifest_path="",
        raw_roots=(),
        pairs=("BTCUSDT",),
        start="2025-04-29",
        end="2025-04-30",
        ml_mode="ML_MODE_OFF",
        training_timeframe="1m",
        backtest_timeframes="1m",
        feature_names="vpin,kyle_lambda",
        selected_features=[],
        feature_picker_enabled="1",
        expected_edge_artifact_mode="MONO_PAIR_LEGACY",
        ml_handoff_run_root="",
        frozen_ml_artifact_path="",
        frozen_ml_artifact_hash="",
        rolling_ml_window_plan_path="",
        ml_artifact_freshness_days=30,
        allow_broad_run="",
        confirm_broad_run="",
        candidate_discovery_mode="SAMPLE_CAPPED_DEBUG",
        engine_native_sample_size=10,
        b1_5_policy_mode="conservative_hard_only",
        preselected_only="true",
        diagnostic_full_replay="",
        small_scope_enabled="",
        full_scan_enabled="",
        silver_storage_mode="jsonl_debug",
        debug_storage_override="",
        signed_by="tester",
        orderbook_path="",
        klines_path="",
        trades_path="",
        metadata_path="",
        output_root="",
        selected_features_csv="",
    )

    assert built.selected_features == ("vpin", "kyle_lambda")
    assert built.feature_names == "vpin,kyle_lambda"


def test_backtest_form_state_does_not_treat_default_csv_as_picker_selection() -> None:
    from cockpit.server import _build_backtest_form_state

    built = _build_backtest_form_state(
        current_form=BacktestFormState(),
        job_kind="",
        selected_action_name="PHASE_A1_PREVIEW",
        resolved_phase_id="PHASE_A1",
        workflow_phase="PHASE_A1",
        workflow_run_id="",
        export_dir="",
        baseline_export_dir="",
        raw_source_manifest_path="",
        raw_roots=(),
        pairs=("BTCUSDT",),
        start="2025-04-29",
        end="2025-04-30",
        ml_mode="ML_MODE_OFF",
        training_timeframe="1m",
        backtest_timeframes="1m",
        feature_names="close_return,high_low_range,volume",
        selected_features=[],
        feature_picker_enabled="1",
        expected_edge_artifact_mode="MONO_PAIR_LEGACY",
        ml_handoff_run_root="",
        frozen_ml_artifact_path="",
        frozen_ml_artifact_hash="",
        rolling_ml_window_plan_path="",
        ml_artifact_freshness_days=30,
        allow_broad_run="",
        confirm_broad_run="",
        candidate_discovery_mode="SAMPLE_CAPPED_DEBUG",
        engine_native_sample_size=10,
        b1_5_policy_mode="conservative_hard_only",
        preselected_only="true",
        diagnostic_full_replay="",
        small_scope_enabled="",
        full_scan_enabled="",
        silver_storage_mode="jsonl_debug",
        debug_storage_override="",
        signed_by="tester",
        orderbook_path="",
        klines_path="",
        trades_path="",
        metadata_path="",
        output_root="",
        selected_features_csv="",
    )

    assert built.selected_features == ()
    assert built.feature_names == ""


def test_backtest_a1_preview_keeps_selected_features_from_csv_mirror(
    tmp_path: Path,
) -> None:
    client = _build_client(tmp_path)
    jobs_root = tmp_path / "backtest_jobs"
    raw_root = tmp_path / "raw"
    (raw_root / "orderbook" / "BTCUSDT").mkdir(parents=True)
    (raw_root / "trades" / "BTCUSDT").mkdir(parents=True)
    (raw_root / "klines" / "BTCUSDT" / "1").mkdir(parents=True)

    response = client.post(
        "/backtest/run",
        data={
            "action_name": "PHASE_A1_PREVIEW",
            "intent": "preview",
            "export_dir": str(tmp_path / "export"),
            "output_root": str(tmp_path / "export"),
            "orderbook_path": str(raw_root / "orderbook" / "BTCUSDT"),
            "trades_path": str(raw_root / "trades" / "BTCUSDT"),
            "klines_path": str(raw_root / "klines" / "BTCUSDT" / "1"),
            "pairs": "BTCUSDT",
            "start": "2025-04-29",
            "end": "2025-04-30",
            "ml_mode": "ML_MODE_OFF",
            "training_timeframe": "1m",
            "backtest_timeframes": "1m",
            "feature_picker_enabled": "1",
            "feature_names": "close_return,high_low_range,volume",
            "selected_features_csv": "vpin,kyle_lambda",
            "signed_by": "tester",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    state = read_backtest_form_state(jobs_root)
    assert state.selected_features == ("vpin", "kyle_lambda")
    assert state.feature_names == "vpin,kyle_lambda"
    page = client.get("/backtest")
    assert page.status_code == 200
    assert _checked_feature_names_from_html(page.text) == ("vpin", "kyle_lambda")
    assert "Source:</strong> <code>FORM_SELECTED</code>" in page.text


def test_backtest_feature_scope_survives_preview_a1_to_b2_launches(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _build_client(tmp_path)
    jobs_root = tmp_path / "backtest_jobs"
    export_root = tmp_path / "export"
    selected_features = ("vpin", "kyle_lambda")
    orderbook_root = tmp_path / "raw" / "orderbook" / "BTCUSDT"
    trades_root = tmp_path / "raw" / "trades" / "BTCUSDT"
    klines_root = tmp_path / "raw" / "klines" / "BTCUSDT" / "1"
    _copy_orderbook_fixture(orderbook_root / "2025-04-29_BTCUSDT_ob200.data")
    _write_trade_fixture(
        trades_root / "BTCUSDT_2025-04-29.csv",
        timestamp_ms=1_745_884_800_000,
    )
    _write_kline_fixture(
        klines_root / "BTCUSDT_1_2025-04-29.csv",
        timestamp_ms=1_745_884_800_000,
    )

    captured: list[dict[str, object]] = []

    def _fake_launch_backtest_job(**kwargs):
        captured.append(dict(kwargs))
        return SimpleNamespace(
            status=CockpitBacktestJobStatus.JOB_CREATED,
            blockers=(),
            job_id=f"job-{len(captured)}",
            output_root=str(export_root / f"job-{len(captured)}"),
        )

    monkeypatch.setattr("cockpit.server.launch_backtest_job", _fake_launch_backtest_job)

    a1_response = _post_backtest_form(
        client,
        intent="preview",
        action_name="PHASE_A1_PREVIEW",
        export_dir=str(export_root),
        orderbook_path=str(orderbook_root),
        trades_path=str(trades_root),
        klines_path=str(klines_root),
        start="2025-04-29",
        end="2025-04-30",
        selected_features=selected_features,
        ml_mode="ML_MODE_OFF",
        training_timeframe="5m",
        backtest_timeframes="1m,5m",
    )
    assert a1_response.status_code == 303
    a1_preview = _latest_preview_payload(jobs_root)
    workflow_run_id = str(a1_preview["workflow_run_id"])
    workflow_root = export_root / "runs" / workflow_run_id
    state = read_backtest_form_state(jobs_root)
    assert state.selected_features == selected_features
    assert state.feature_names == "vpin,kyle_lambda"

    phase_specs = (
        ("PHASE_A2_DATA_FACTORY", PHASE_A2),
        ("PHASE_B1_CANDIDATE_DISCOVERY", PHASE_B1),
        ("PHASE_B2_DETAILED_REPLAY", PHASE_B2),
    )
    for action_name, expected_phase in phase_specs:
        if action_name == "PHASE_B1_CANDIDATE_DISCOVERY":
            _write_ready_phase_a2_artifacts(workflow_root)
        if action_name == "PHASE_B2_DETAILED_REPLAY":
            _write_ready_phase_a2_artifacts(workflow_root)
            _write_ready_phase_b1_artifacts(workflow_root, workflow_run_id)
        preview_response = _post_backtest_form(
            client,
            intent="preview",
            action_name=action_name,
            workflow_run_id=workflow_run_id,
            export_dir=str(export_root),
            orderbook_path=str(orderbook_root),
            trades_path=str(trades_root),
            klines_path=str(klines_root),
            start="2025-04-29",
            end="2025-04-30",
            selected_features=selected_features,
            ml_mode="ML_MODE_OFF",
            training_timeframe="5m",
            backtest_timeframes="1m,5m",
        )
        assert preview_response.status_code == 303
        preview_payload = _latest_preview_payload(jobs_root)
        state = read_backtest_form_state(jobs_root)
        assert state.selected_features == selected_features
        assert state.feature_names == "vpin,kyle_lambda"
        assert state.ml_mode == "ML_MODE_OFF"

        launch_response = _post_backtest_form(
            client,
            intent="launch",
            action_name=action_name,
            preview_id=str(preview_payload["preview_id"]),
            request_hash=str(preview_payload["request_hash"]),
            workflow_run_id=workflow_run_id,
            export_dir=str(export_root),
            orderbook_path=str(orderbook_root),
            trades_path=str(trades_root),
            klines_path=str(klines_root),
            start="2025-04-29",
            end="2025-04-30",
            selected_features=selected_features,
            ml_mode="ML_MODE_OFF",
            training_timeframe="5m",
            backtest_timeframes="1m,5m",
        )
        assert launch_response.status_code == 303
        assert captured[-1]["phase_id"] == expected_phase
        assert captured[-1]["ml_mode_status"] == "ML_MODE_OFF"
        assert captured[-1]["feature_names_csv"] == "vpin,kyle_lambda"
        assert captured[-1].get("blocked_reason", "") == ""
        state = read_backtest_form_state(jobs_root)
        assert state.selected_features == selected_features
        assert state.feature_names == "vpin,kyle_lambda"


def test_backtest_page_marks_picker_read_only_when_frozen_artifact_is_authoritative(
    tmp_path: Path,
) -> None:
    client = _build_client(tmp_path)
    jobs_root = tmp_path / "backtest_jobs"
    run_root = tmp_path / "ml_handoff" / "strategy_ladder_ml_lab_handoff-test"
    _write_minimal_handoff_run(run_root, feature_names=("vpin", "kyle_lambda"))
    write_backtest_form_state(
        jobs_root,
        BacktestFormState(
            ml_mode="ML_MODE_OVERLAY_FROZEN",
            ml_handoff_run_root=str(run_root),
            feature_names="vpin,kyle_lambda",
        ),
    )
    response = client.get("/backtest")
    assert response.status_code == 200
    assert "Artifact authoritative:" in response.text
    assert 'name="backtest_timeframes"' in response.text
    assert "Frozen artifact feature list is authoritative for replay scoring." in response.text


def test_backtest_page_ml_off_does_not_render_artifact_features_as_selected(
    tmp_path: Path,
) -> None:
    client = _build_client(tmp_path)
    jobs_root = tmp_path / "backtest_jobs"
    run_root = tmp_path / "ml_handoff" / "strategy_ladder_ml_lab_handoff-test"
    _write_minimal_handoff_run(
        run_root,
        feature_names=("close_return", "high_low_range", "volume"),
    )
    write_backtest_form_state(
        jobs_root,
        BacktestFormState(
            ml_mode="ML_MODE_OFF",
            ml_handoff_run_root=str(run_root),
            feature_names="close_return,high_low_range,volume,vpin,kyle_lambda",
            selected_features=(
                "close_return",
                "high_low_range",
                "volume",
                "vpin",
                "kyle_lambda",
            ),
            feature_picker_enabled="1",
        ),
    )

    response = client.get("/backtest")

    assert response.status_code == 200
    assert _checked_feature_names_from_html(response.text) == (
        "close_return",
        "high_low_range",
        "volume",
        "vpin",
        "kyle_lambda",
    )
    assert "Source:</strong> <code>FORM_SELECTED</code>" in response.text
    assert "Artifact authoritative:" not in response.text


def test_backtest_launch_with_selected_features_requires_frozen_ia_lab_artifact(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _build_client(tmp_path)
    jobs_root = tmp_path / "backtest_jobs"
    orderbook_root = tmp_path / "raw" / "orderbook" / "BTCUSDT"
    trades_root = tmp_path / "raw" / "trades" / "BTCUSDT"
    klines_root = tmp_path / "raw" / "klines" / "BTCUSDT" / "1"
    _copy_orderbook_fixture(orderbook_root / "2025-04-29_BTCUSDT_ob200.data")
    _write_trade_fixture(
        trades_root / "BTCUSDT_2025-04-29.csv",
        timestamp_ms=1_745_884_800_000,
    )
    _write_kline_fixture(
        klines_root / "BTCUSDT_1_2025-04-29.csv",
        timestamp_ms=1_745_884_800_000,
    )

    captured: dict[str, object] = {}

    def _fake_launch_backtest_job(**kwargs):
        captured.update(kwargs)
        raise AssertionError("Backtest must not launch an ML handoff implicitly")

    monkeypatch.setattr("cockpit.server.launch_backtest_job", _fake_launch_backtest_job)

    preview_response = _post_backtest_form(
        client,
        intent="preview",
        action_name="PHASE_B1_CANDIDATE_DISCOVERY",
        export_dir=str(tmp_path / "export"),
        orderbook_path=str(orderbook_root),
        trades_path=str(trades_root),
        klines_path=str(klines_root),
        start="2025-04-29",
        end="2025-04-30",
        selected_features=("close_return", "high_low_range", "volume"),
        ml_mode="ML_MODE_OVERLAY_FROZEN",
        training_timeframe="5m",
    )
    assert preview_response.status_code == 303
    preview_payload = _latest_preview_payload(jobs_root)
    workflow_run_id = str(preview_payload["workflow_run_id"])
    phase_a2_root = (
        tmp_path / "export" / "runs" / workflow_run_id / "phase_a2_data_factory"
    )
    phase_a2_root.mkdir(parents=True, exist_ok=True)
    (phase_a2_root / "gold").mkdir(parents=True, exist_ok=True)
    (phase_a2_root / "data_factory_manifest.json").write_text(
        json.dumps(
            {
                "data_factory_status": "DATA_FACTORY_READY",
                "raw_source_status": "RAW_SOURCE_READY",
                "pair_universe_status": "PAIR_UNIVERSE_READY",
                "silver_index_status": "SILVER_INDEX_READY",
                "gold_feature_store_status": "GOLD_FEATURE_STORE_READY",
            }
        ),
        encoding="utf-8",
    )
    (phase_a2_root / "silver_index.json").write_text(
        json.dumps({"storage_format": "jsonl_gz"}),
        encoding="utf-8",
    )

    response = _post_backtest_form(
        client,
        intent="launch",
        action_name="PHASE_B1_CANDIDATE_DISCOVERY",
        export_dir=str(tmp_path / "export"),
        orderbook_path=str(orderbook_root),
        trades_path=str(trades_root),
        klines_path=str(klines_root),
        start="2025-04-29",
        end="2025-04-30",
        preview_id=str(preview_payload["preview_id"]),
        request_hash=str(preview_payload["request_hash"]),
        workflow_run_id=workflow_run_id,
        selected_features=("close_return", "high_low_range", "volume"),
        ml_mode="ML_MODE_OVERLAY_FROZEN",
        training_timeframe="5m",
    )
    assert response.status_code == 303
    assert captured == {}
    assert "ML_OVERLAY_FROZEN_REQUIRES_ARTIFACT_PATH_AND_HASH" in response.headers["location"]
    launch_state = read_launch_request_state(jobs_root)
    assert launch_state is not None
    assert launch_state.status == "CHAIN_BLOCKED"
    assert launch_state.blockers == ("ML_OVERLAY_FROZEN_REQUIRES_ARTIFACT_PATH_AND_HASH",)
    assert read_backtest_ml_chain_state(jobs_root) is None


def test_backtest_launch_with_ml_off_selected_features_stays_native(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _build_client(tmp_path)
    jobs_root = tmp_path / "backtest_jobs"
    orderbook_root = tmp_path / "raw" / "orderbook" / "BTCUSDT"
    trades_root = tmp_path / "raw" / "trades" / "BTCUSDT"
    klines_root = tmp_path / "raw" / "klines" / "BTCUSDT" / "1"
    _copy_orderbook_fixture(orderbook_root / "2025-04-29_BTCUSDT_ob200.data")
    _write_trade_fixture(
        trades_root / "BTCUSDT_2025-04-29.csv",
        timestamp_ms=1_745_884_800_000,
    )
    _write_kline_fixture(
        klines_root / "BTCUSDT_1_2025-04-29.csv",
        timestamp_ms=1_745_884_800_000,
    )

    captured: dict[str, object] = {}

    def _fake_launch_backtest_job(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(
            status=CockpitBacktestJobStatus.JOB_CREATED,
            blockers=(),
            job_id="native-runner-001",
            output_root=str(tmp_path / "native_runner_out"),
        )

    monkeypatch.setattr("cockpit.server.launch_backtest_job", _fake_launch_backtest_job)

    preview_response = _post_backtest_form(
        client,
        intent="preview",
        action_name="PHASE_B1_CANDIDATE_DISCOVERY",
        export_dir=str(tmp_path / "export"),
        orderbook_path=str(orderbook_root),
        trades_path=str(trades_root),
        klines_path=str(klines_root),
        start="2025-04-29",
        end="2025-04-30",
        selected_features=("vpin", "kyle_lambda"),
        ml_mode="ML_MODE_OFF",
        training_timeframe="5m",
    )
    assert preview_response.status_code == 303
    preview_payload = _latest_preview_payload(jobs_root)
    workflow_run_id = str(preview_payload["workflow_run_id"])
    phase_a2_root = (
        tmp_path / "export" / "runs" / workflow_run_id / "phase_a2_data_factory"
    )
    phase_a2_root.mkdir(parents=True, exist_ok=True)
    (phase_a2_root / "gold").mkdir(parents=True, exist_ok=True)
    (phase_a2_root / "data_factory_manifest.json").write_text(
        json.dumps(
            {
                "data_factory_status": "DATA_FACTORY_READY",
                "raw_source_status": "RAW_SOURCE_READY",
                "pair_universe_status": "PAIR_UNIVERSE_READY",
                "silver_index_status": "SILVER_INDEX_READY",
                "gold_feature_store_status": "GOLD_FEATURE_STORE_READY",
            }
        ),
        encoding="utf-8",
    )
    (phase_a2_root / "silver_index.json").write_text(
        json.dumps({"storage_format": "jsonl_gz"}),
        encoding="utf-8",
    )

    response = _post_backtest_form(
        client,
        intent="launch",
        action_name="PHASE_B1_CANDIDATE_DISCOVERY",
        export_dir=str(tmp_path / "export"),
        orderbook_path=str(orderbook_root),
        trades_path=str(trades_root),
        klines_path=str(klines_root),
        start="2025-04-29",
        end="2025-04-30",
        preview_id=str(preview_payload["preview_id"]),
        request_hash=str(preview_payload["request_hash"]),
        workflow_run_id=workflow_run_id,
        selected_features=("vpin", "kyle_lambda"),
        ml_mode="ML_MODE_OFF",
        training_timeframe="5m",
    )
    assert response.status_code == 303
    assert "Backtest+feature+selection+requires+a+frozen+IA+Lab+artifact" not in response.headers["location"]
    assert captured["ml_mode_status"] == "ML_MODE_OFF"
    assert captured["feature_names_csv"] == "vpin,kyle_lambda"
    chain_state = read_backtest_ml_chain_state(jobs_root)
    assert chain_state is not None
    assert chain_state.status == "CHAIN_NOT_REQUESTED"


def test_backtest_chain_blocks_non_legacy_features_without_phase_b2_root(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _build_client(tmp_path)
    jobs_root = tmp_path / "backtest_jobs"
    orderbook_root = tmp_path / "raw" / "orderbook" / "BTCUSDT"
    trades_root = tmp_path / "raw" / "trades" / "BTCUSDT"
    klines_root = tmp_path / "raw" / "klines" / "BTCUSDT" / "1"
    _copy_orderbook_fixture(orderbook_root / "2025-04-29_BTCUSDT_ob200.data")
    _write_trade_fixture(
        trades_root / "BTCUSDT_2025-04-29.csv",
        timestamp_ms=1_745_884_800_000,
    )
    _write_kline_fixture(
        klines_root / "BTCUSDT_1_2025-04-29.csv",
        timestamp_ms=1_745_884_800_000,
    )

    def _unexpected_launch_backtest_job(**kwargs):
        raise AssertionError("launch_backtest_job must not be called")

    monkeypatch.setattr("cockpit.server.launch_backtest_job", _unexpected_launch_backtest_job)

    preview_response = _post_backtest_form(
        client,
        intent="preview",
        action_name="PHASE_B1_CANDIDATE_DISCOVERY",
        export_dir=str(tmp_path / "export"),
        orderbook_path=str(orderbook_root),
        trades_path=str(trades_root),
        klines_path=str(klines_root),
        start="2025-04-29",
        end="2025-04-30",
        selected_features=("vpin", "kyle_lambda"),
        ml_mode="ML_MODE_OVERLAY_FROZEN",
        training_timeframe="5m",
    )
    assert preview_response.status_code == 303
    preview_payload = _latest_preview_payload(jobs_root)
    workflow_run_id = str(preview_payload["workflow_run_id"])
    phase_a2_root = (
        tmp_path / "export" / "runs" / workflow_run_id / "phase_a2_data_factory"
    )
    phase_a2_root.mkdir(parents=True, exist_ok=True)
    (phase_a2_root / "gold").mkdir(parents=True, exist_ok=True)
    (phase_a2_root / "data_factory_manifest.json").write_text(
        json.dumps(
            {
                "data_factory_status": "DATA_FACTORY_READY",
                "raw_source_status": "RAW_SOURCE_READY",
                "pair_universe_status": "PAIR_UNIVERSE_READY",
                "silver_index_status": "SILVER_INDEX_READY",
                "gold_feature_store_status": "GOLD_FEATURE_STORE_READY",
            }
        ),
        encoding="utf-8",
    )
    (phase_a2_root / "silver_index.json").write_text(
        json.dumps({"storage_format": "jsonl_gz"}),
        encoding="utf-8",
    )

    response = _post_backtest_form(
        client,
        intent="launch",
        action_name="PHASE_B1_CANDIDATE_DISCOVERY",
        export_dir=str(tmp_path / "export"),
        orderbook_path=str(orderbook_root),
        trades_path=str(trades_root),
        klines_path=str(klines_root),
        start="2025-04-29",
        end="2025-04-30",
        preview_id=str(preview_payload["preview_id"]),
        request_hash=str(preview_payload["request_hash"]),
        workflow_run_id=workflow_run_id,
        selected_features=("vpin", "kyle_lambda"),
        ml_mode="ML_MODE_OVERLAY_FROZEN",
        training_timeframe="5m",
    )
    assert response.status_code == 303
    assert "ML_OVERLAY_FROZEN_REQUIRES_ARTIFACT_PATH_AND_HASH" in response.headers["location"]
    launch_state = read_launch_request_state(jobs_root)
    assert launch_state is not None
    assert launch_state.status == "CHAIN_BLOCKED"
    assert launch_state.blockers == ("ML_OVERLAY_FROZEN_REQUIRES_ARTIFACT_PATH_AND_HASH",)
    assert read_backtest_ml_chain_state(jobs_root) is None


def test_candidate_feature_table_endpoint_returns_dynamic_feature_columns(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _build_client(tmp_path)
    jobs_root = tmp_path / "backtest_jobs"
    write_backtest_form_state(
        jobs_root,
        BacktestFormState(
            feature_names="vpin,kyle_lambda",
            selected_features=("vpin", "kyle_lambda"),
            feature_picker_enabled="1",
            training_timeframe="1m",
        ),
    )

    def _fake_runtime_surfaces(**kwargs):
        assert kwargs["active_feature_names"] == ("vpin", "kyle_lambda")
        summary = SimpleNamespace(
            run_id="strategy_ladder_run-001",
            workflow_run_id="strategy_ladder_workflow-001",
            candidate_feature_table_status="CANDIDATE_FEATURE_TABLE_READY",
            active_feature_names=("vpin", "kyle_lambda"),
            candidate_feature_columns=("vpin", "kyle_lambda"),
            candidate_feature_rows=(
                {
                    "candidate_id": "cand-1",
                    "pair": "BTCUSDT",
                    "engine_id": "ENGINE_B",
                    "timeframe": "1m",
                    "outcome_status": "executed",
                    "accepted_or_refused": "ACCEPTED",
                    "reason_codes": ("EXPECTED_EDGE_OK",),
                    "vpin": 0.42,
                    "kyle_lambda": 0.08,
                },
            ),
            feature_engine_ml_wiring_status="FEATURE_ENGINE_ML_WIRING_READY",
            feature_engine_ml_wiring_report_path="E:/report.json",
            feature_engine_ml_wiring_rows=(
                {
                    "feature_name": "vpin",
                    "training_selected": True,
                    "artifact_selected": False,
                    "runtime_payload_available": True,
                    "native_engine_origin": "bridge_microstructure_capture",
                    "native_engine_consumption_status": "CAPTURED_NATIVE_CONTEXT_NOT_DIRECT_ENGINE_GATE",
                    "ml_runtime_wired": True,
                    "ml_block_reason": "",
                },
            ),
        )
        return SimpleNamespace(strategy_ladder_summary=summary)

    monkeypatch.setattr("cockpit.server.read_runtime_surfaces", _fake_runtime_surfaces)

    response = client.get("/backtest/candidate-feature-table.json")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "CANDIDATE_FEATURE_TABLE_READY"
    assert payload["columns"][-2:] == ["vpin", "kyle_lambda"]
    assert payload["rows"][0]["candidate_id"] == "cand-1"
    assert payload["rows"][0]["vpin"] == 0.42
    assert payload["wiring_status"] == "FEATURE_ENGINE_ML_WIRING_READY"


def test_backtest_view_model_defers_candidate_feature_audits(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _build_client(tmp_path)
    captured: dict[str, object] = {}

    def _fake_runtime_surfaces(**kwargs):
        captured.update(kwargs)
        return CockpitRuntimeSurfaces()

    monkeypatch.setattr("cockpit.state.read_runtime_surfaces", _fake_runtime_surfaces)

    build_dashboard_view_model(
        paths=client.app.state.paths,
        welcome_message="Welcome",
        grafana_url="http://127.0.0.1:3000",
        prometheus_url="http://127.0.0.1:9090",
        current_page="backtest",
    )

    assert captured["include_candidate_feature_audits"] is False


def test_backtest_page_lazy_loads_candidate_feature_audits(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _build_client(tmp_path)
    jobs_root = tmp_path / "backtest_jobs"
    write_backtest_form_state(
        jobs_root,
        BacktestFormState(
            feature_names="vpin,kyle_lambda",
            selected_features=("vpin", "kyle_lambda"),
            feature_picker_enabled="1",
            training_timeframe="1m",
        ),
    )

    def _fake_runtime_surfaces(**kwargs):
        summary = StrategyLadderBacktestSummary(
            run_id="strategy_ladder_run-001",
            workflow_run_id="strategy_ladder_workflow-001",
            candidate_feature_table_status="CANDIDATE_FEATURE_TABLE_DEFERRED",
            active_feature_names=("vpin", "kyle_lambda"),
            candidate_feature_columns=("vpin", "kyle_lambda"),
            candidate_feature_rows=(),
            feature_engine_ml_wiring_status="FEATURE_ENGINE_ML_WIRING_DEFERRED",
            feature_engine_ml_wiring_report_path="",
            feature_engine_ml_wiring_rows=(),
            candidate_rows=(
                {
                    "candidate_id": "cand-1",
                    "pair": "BTCUSDT",
                    "engine_id": "ENGINE_B",
                    "timeframe": "1m",
                    "score_final": 0.42,
                    "replay_status": "DETAILED_REPLAY_READY",
                    "outcome_status": "executed",
                    "net_result": "12.0",
                },
            ),
            selected_candidate_id="",
            selected_candidate_detail={},
            selected_candidate_replay={},
            selected_candidate_window={},
            current_job_status="JOB_COMPLETED",
            current_phase_status="PHASE_B2_DETAILED_REPLAY_READY",
            phase_id="PHASE_B2",
            source_status="ok",
            output_root=str(tmp_path / "export"),
        )
        return CockpitRuntimeSurfaces(strategy_ladder_summary=summary)

    monkeypatch.setattr("cockpit.state.read_runtime_surfaces", _fake_runtime_surfaces)
    # Patch A (2026-05-31) — candidate feature / wiring audit panels MOVED to
    # /backtest/replay (drill-down). The lazy-load placeholders now render there.
    response = client.get("/backtest/replay")

    assert response.status_code == 200
    assert "Loading feature metrics asynchronously to reduce first-paint cost." in response.text
    assert "Loading wiring audit asynchronously to reduce first-paint cost." in response.text
    assert "/backtest/candidate-feature-table.json" in response.text


def test_backtest_status_reconcile_launches_replay_once_after_handoff_success(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client = _build_client(tmp_path)
    jobs_root = tmp_path / "backtest_jobs"
    frozen_form = BacktestFormState(
        action_name="PHASE_B1_CANDIDATE_DISCOVERY",
        phase_id=PHASE_B1,
        workflow_phase=PHASE_B1,
        workflow_run_id="strategy_ladder_workflow-001",
        export_dir=str(tmp_path / "export"),
        output_root=str(tmp_path / "export"),
        start="2025-04-29",
        end="2025-04-30",
        pairs=("BTCUSDT",),
        klines_path=str(tmp_path / "raw" / "klines"),
        feature_names="vpin,kyle_lambda",
        selected_features=("vpin", "kyle_lambda"),
        feature_picker_enabled="1",
        training_timeframe="1m",
    )
    write_backtest_form_state(jobs_root, frozen_form)
    write_backtest_ml_chain_state(
        jobs_root,
        BacktestMlChainState(
            status="CHAIN_HANDOFF_PENDING",
            created_at="2026-05-23T09:00:00+00:00",
            updated_at="2026-05-23T09:00:00+00:00",
            action_name="PHASE_B1_CANDIDATE_DISCOVERY",
            phase_id=PHASE_B1,
            workflow_run_id="strategy_ladder_workflow-001",
            preview_id="preview-001",
            request_hash="request-hash-001",
            selected_features=("vpin", "kyle_lambda"),
            training_timeframe="1m",
            feature_selection_source="FORM_SELECTED",
            handoff_job_id="handoff-001",
            handoff_output_root=str(tmp_path / "ml_handoff_ready"),
            frozen_form=frozen_form,
        ),
    )

    handoff_job = CockpitBacktestJobRecord(
        job_id="handoff-001",
        correlation_id="corr-handoff",
        job_kind=CockpitBacktestJobKind.STRATEGY_LADDER_ML_LAB_HANDOFF,
        status=CockpitBacktestJobStatus.JOB_COMPLETED,
        requested_at_iso="2026-05-23T09:00:00+00:00",
        output_root=str(tmp_path / "ml_handoff_ready"),
        record_path=str(tmp_path / "jobs" / "handoff" / "job.json"),
        stdout_log_path=str(tmp_path / "jobs" / "handoff" / "stdout.log"),
        command=("python", "stub.py"),
        action_name="STRATEGY_LADDER_ML_LAB_HANDOFF",
        phase_id=PHASE_B1,
        workflow_run_id="strategy_ladder_workflow-001",
        phase_run_id="phase-handoff-001",
        preview_id="preview-001",
        request_hash="request-hash-001",
    )
    replay_job = CockpitBacktestJobRecord(
        job_id="replay-001",
        correlation_id="corr-replay",
        job_kind=CockpitBacktestJobKind.STRATEGY_LADDER_RUNNER,
        status=CockpitBacktestJobStatus.JOB_RUNNING,
        requested_at_iso="2026-05-23T09:05:00+00:00",
        output_root=str(tmp_path / "replay_out"),
        record_path=str(tmp_path / "jobs" / "replay" / "job.json"),
        stdout_log_path=str(tmp_path / "jobs" / "replay" / "stdout.log"),
        command=("python", "stub.py"),
        action_name="PHASE_B1_CANDIDATE_DISCOVERY",
        phase_id=PHASE_B1,
        workflow_run_id="strategy_ladder_workflow-001",
        phase_run_id="phase-b1-001",
        preview_id="preview-001",
        request_hash="request-hash-001",
    )
    load_phase = {"value": 0}

    def _fake_load_backtest_job_records(_jobs_root: Path, limit: int = 64):
        if load_phase["value"] == 0:
            return (handoff_job,)
        return (replay_job, handoff_job)

    launched: list[dict[str, object]] = []

    def _fake_launch_backtest_job(**kwargs):
        launched.append(kwargs)
        load_phase["value"] = 1
        return replay_job

    frozen_artifact = tmp_path / "ml_handoff_ready" / "bundle.json"
    frozen_artifact.parent.mkdir(parents=True, exist_ok=True)
    frozen_artifact.write_text("{}", encoding="utf-8")

    preflight = SimpleNamespace(
        workflow_run_id="strategy_ladder_workflow-001",
        preview_id="preview-001",
        request_hash="request-hash-001",
        action_name="PHASE_B1_CANDIDATE_DISCOVERY",
        phase_id=PHASE_B1,
        detected_pairs=("BTCUSDT",),
        active_pairs_after_pruning=("BTCUSDT",),
        preview_launchable=True,
        blockers=(),
        output_root_selected=str(tmp_path / "export"),
        effective_engine_native_sample_size=10,
        candidate_discovery_mode="SAMPLE_CAPPED_DEBUG",
        small_scope_enabled=True,
        full_scan_enabled=False,
        no_full_scan_enabled=True,
        silver_storage_mode_effective="jsonl_gz",
        command_preview="python stub.py",
        ml_overlay_intake=SimpleNamespace(
            ready=True,
            frozen_ml_artifact_path=str(frozen_artifact),
            frozen_ml_artifact_hash="a" * 64,
            feature_names=("vpin", "kyle_lambda"),
            blocker_codes=(),
        ),
        normalized_request=Patch6NormalizedRequest(
            phase_id=PHASE_B1,
            phase_label="Phase B1 Candidate Discovery",
            action_name="PHASE_B1_CANDIDATE_DISCOVERY",
            workflow_run_id="strategy_ladder_workflow-001",
            ml_mode="ML_MODE_OVERLAY_FROZEN",
            dry_run=False,
            pair_subset=("BTCUSDT",),
            start="2025-04-29",
            end="2025-04-30",
            orderbook_root="",
            trades_root="",
            klines_root=str(tmp_path / "raw" / "klines"),
            output_root_selected=str(tmp_path / "export"),
            expected_edge_artifact_mode="MONO_PAIR_LEGACY",
            frozen_ml_artifact_path=str(frozen_artifact),
            frozen_ml_artifact_hash="a" * 64,
            rolling_ml_window_plan_path="",
            ml_artifact_freshness_days=30,
            historical_metadata_root="",
            candidate_discovery_mode="SAMPLE_CAPPED_DEBUG",
            engine_native_sample_size=10,
            allow_broad_run=False,
            small_scope_enabled=True,
            full_scan_enabled=False,
            no_full_scan_enabled=True,
            silver_storage_mode="jsonl_gz",
            preselected_only=True,
            diagnostic_full_replay=False,
            b1_5_policy_mode="conservative_hard_only",
            debug_storage_override=False,
        ),
    )

    monkeypatch.setattr("cockpit.server.load_backtest_job_records", _fake_load_backtest_job_records)
    monkeypatch.setattr("cockpit.server.launch_backtest_job", _fake_launch_backtest_job)
    monkeypatch.setattr("cockpit.server.build_patch6_preflight_preview", lambda **kwargs: preflight)

    first = client.get("/backtest/status.json")
    assert first.status_code == 200
    second = client.get("/backtest/status.json")
    assert second.status_code == 200
    assert len(launched) == 1
    assert launched[0]["job_kind"] == CockpitBacktestJobKind.STRATEGY_LADDER_RUNNER
    chain_state = read_backtest_ml_chain_state(jobs_root)
    assert chain_state is not None
    assert chain_state.status == "CHAIN_REPLAY_LAUNCHED"
    assert chain_state.replay_job_id == "replay-001"
