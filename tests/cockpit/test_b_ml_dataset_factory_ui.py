from __future__ import annotations

from pathlib import Path

from cockpit import action_support as action_support_module
from cockpit import backtest_preflight as backtest_preflight_module
from cockpit.backtest_preflight import build_patch6_preflight_preview
from cockpit.backtest_state_support import build_patch6_normalized_request
from cockpit.form_state_support import BacktestFormState
from cockpit.strategy_ladder_workflow_support import (
    PHASE_A2,
    PHASE_B_ML,
    ensure_workflow_manifest,
)
from interface_contracts.atomic_io import atomic_write_json


def test_backtest_template_exposes_bml_phase_and_sampler() -> None:
    template = Path("src/cockpit/templates/pages/backtest.html").read_text(
        encoding="utf-8"
    )

    assert "PHASE_B_ML_LABEL_FACTORY" in template
    assert "B_ML Training Label Factory" in template
    assert 'name="bml_candidate_sampler_mode"' in template
    assert "TEMPORAL_STRATIFIED_BACKGROUND_GRID" in template
    assert "REUSE_B1_FAST_CANDIDATES" in template


def test_normalized_request_preserves_bml_phase_and_sampler() -> None:
    request = build_patch6_normalized_request(
        BacktestFormState(
            workflow_phase=PHASE_B_ML,
            bml_candidate_sampler_mode="REUSE_B1_FAST_CANDIDATES",
            pairs=("BTCUSDT",),
            backtest_timeframes=("1m", "5m"),
        )
    )

    assert request.phase_id == PHASE_B_ML
    assert request.action_name == "PHASE_B_ML_LABEL_FACTORY"
    assert request.bml_candidate_sampler_mode == "REUSE_B1_FAST_CANDIDATES"
    assert request.backtest_timeframes == ("1m", "5m")


def test_bml_preview_command_uses_label_factory_script() -> None:
    command_preview = backtest_preflight_module._build_preview_command(
        action_name="PHASE_B_ML_LABEL_FACTORY",
        export_dir="",
        baseline_export_dir="",
        raw_source_manifest_path="",
        orderbook_path="L:\\ordrebookpart1",
        trades_path="L:\\trades",
        klines_path="L:\\klines",
        raw_roots=("L:\\ordrebookpart1", "L:\\trades", "L:\\klines"),
        metadata_path="",
        pairs=("BNBUSDT", "BTCUSDT"),
        backtest_timeframes=("1m", "5m"),
        feature_names="close_return,spread_bps,queue_pressure",
        start="2025-04-29",
        end="2025-05-01",
        ml_mode="ML_MODE_OFF",
        expected_edge_artifact_mode="MONO_PAIR_LEGACY",
        frozen_ml_artifact_path="",
        frozen_ml_artifact_hash="",
        rolling_ml_window_plan_path="",
        ml_artifact_freshness_days=30,
        output_root=(
            "L:\\output backtest\\runs\\strategy_ladder_workflow-test"
            "\\phase_b_ml_training_label_factory"
        ),
        workflow_run_id="strategy_ladder_workflow-test",
        engine_native_sample_size=50,
        candidate_sample_cap=0,
        candidate_discovery_mode="TEMPORAL_STRATIFIED",
        bml_candidate_sampler_mode="REUSE_B1_FAST_CANDIDATES",
        small_scope_enabled=False,
        full_scan_enabled=True,
        no_full_scan_enabled=False,
        allow_broad_run=False,
        silver_storage_mode="jsonl_gz",
    )

    assert "run_strategy_ladder_b_ml_label_factory.py" in command_preview
    assert "--workflow-run-id strategy_ladder_workflow-test" in command_preview
    assert "--a2-run-root" in command_preview
    assert "--pairs BNBUSDT,BTCUSDT" in command_preview
    assert "--timeframes 1m,5m" in command_preview
    assert "--feature-names close_return,spread_bps,queue_pressure" in command_preview
    assert "--candidate-sampler-mode REUSE_B1_FAST_CANDIDATES" in command_preview
    assert "--b1-candidate-events-path" in command_preview
    assert "--ml-mode" not in command_preview


def test_bml_preflight_requires_a2_and_emits_launchable_preview(tmp_path: Path) -> None:
    workflow_run_id = "strategy_ladder_workflow-test"
    output_base = tmp_path / "output"
    workflow_root = output_base / "runs" / workflow_run_id
    a2_root = workflow_root / "phase_a2_data_factory"
    ensure_workflow_manifest(
        workflow_root=workflow_root,
        workflow_run_id=workflow_run_id,
        request_hash="test",
        phase_id=PHASE_A2,
        pairs=("BTCUSDT",),
        start="2025-04-29",
        end="2025-04-29",
        ml_mode="ML_MODE_OFF",
        candidate_discovery_mode="TEMPORAL_STRATIFIED",
        engine_native_sample_size=10,
        engine_count=4,
        allow_broad_run=False,
        small_scope_enabled=True,
        full_scan_enabled=False,
        no_full_scan_enabled=True,
        silver_storage_mode_requested="jsonl_gz",
        silver_storage_mode_effective="jsonl_gz",
    )
    (a2_root / "gold").mkdir(parents=True)
    atomic_write_json(
        a2_root / "data_factory_manifest.json",
        {"data_factory_status": "DATA_FACTORY_READY", "blocker_codes": []},
        indent=2,
    )
    atomic_write_json(a2_root / "silver_index.json", {"entries": []}, indent=2)

    orderbook = tmp_path / "raw" / "orderbook" / "BTCUSDT_2025-04-29.data"
    trades = tmp_path / "raw" / "trades" / "BTCUSDT_2025-04-29.csv"
    klines = tmp_path / "raw" / "klines" / "BTCUSDT_2025-04-29.csv"
    for path in (orderbook, trades, klines):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("placeholder\n", encoding="utf-8")

    preflight = build_patch6_preflight_preview(
        selected_form=BacktestFormState(
            action_name="PHASE_B_ML_LABEL_FACTORY",
            workflow_phase=PHASE_B_ML,
            workflow_run_id=workflow_run_id,
            output_root=str(output_base),
            export_dir=str(tmp_path / "export"),
            orderbook_path=str(orderbook.parent),
            trades_path=str(trades.parent),
            klines_path=str(klines.parent),
            pairs=("BTCUSDT",),
            start="2025-04-29",
            end="2025-04-29",
            backtest_timeframes=("1m",),
            feature_names="close_return,spread_bps",
            bml_candidate_sampler_mode="TEMPORAL_STRATIFIED_BACKGROUND_GRID",
            silver_storage_mode="jsonl_gz",
            small_scope_enabled="true",
        ),
        jobs_root=None,
    )

    assert preflight.phase_id == PHASE_B_ML
    assert preflight.inspection_status == "PHASE_B_ML_LABEL_FACTORY_READY"
    assert preflight.preview_launchable is True
    assert "--a2-run-root" in preflight.command_preview
    assert "phase_a2_data_factory" in preflight.command_preview


def test_bml_launch_command_targets_bml_artifacts(tmp_path: Path) -> None:
    workflow_root = tmp_path / "runs" / "strategy_ladder_workflow-test"
    a2_root = workflow_root / "phase_a2_data_factory"
    b1_events = (
        workflow_root
        / "phase_b1_candidate_discovery"
        / "backtest_strategy_ladder"
        / "strategy_ladder_workflow-test"
        / "fast_candidates"
        / "candidate_events.jsonl"
    )
    output_root = workflow_root / "phase_b_ml_training_label_factory"

    command = action_support_module._build_backtest_command(
        job_id="strategy_ladder_b_ml_label_factory-test",
        job_kind=action_support_module.CockpitBacktestJobKind.STRATEGY_LADDER_B_ML_LABEL_FACTORY,
        export_dir=tmp_path,
        output_root=output_root,
        baseline_export_dir=None,
        signed_by="tester",
        python_executable="python",
        action_name="PHASE_B_ML_LABEL_FACTORY",
        raw_source_manifest_path=None,
        raw_roots=(),
        pairs=("BNBUSDT", "BTCUSDT"),
        start="2025-04-29",
        end="2025-05-01",
        allow_broad_run=False,
        ml_mode_status="ML_MODE_OFF",
        engine_native_mode=False,
        engine_native_sample_size=0,
        feature_store_root=a2_root / "gold",
        candidate_events_path=b1_events,
        workflow_run_id="strategy_ladder_workflow-test",
        backtest_timeframes=("1m", "5m"),
        feature_names_csv="close_return,spread_bps,queue_pressure",
        bml_candidate_sampler_mode="ENGINE_NATIVE_DRY_EVAL_AND_BACKGROUND_GRID",
    )

    assert "run_strategy_ladder_b_ml_label_factory.py" in " ".join(command)
    assert command[command.index("--a2-run-root") + 1] == str(a2_root.resolve())
    assert command[command.index("--output-root") + 1] == str(output_root.resolve())
    assert command[command.index("--pairs") + 1] == "BNBUSDT,BTCUSDT"
    assert command[command.index("--timeframes") + 1] == "1m,5m"
    assert (
        command[command.index("--candidate-sampler-mode") + 1]
        == "ENGINE_NATIVE_DRY_EVAL_AND_BACKGROUND_GRID"
    )
    assert command[command.index("--b1-candidate-events-path") + 1] == str(
        b1_events.resolve()
    )
    assert "--ml-mode" not in command
