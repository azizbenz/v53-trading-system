from __future__ import annotations

import json
from pathlib import Path
import shutil
from types import SimpleNamespace

import pytest

from local_replay_runtime.strategy_ladder_data_factory_models import (
    StrategyLadderFirstControlledRunRequest,
)
from local_replay_runtime import strategy_ladder_first_controlled_run as first_run_module
from local_replay_runtime.strategy_ladder_first_controlled_run import (
    run_strategy_ladder_first_controlled_run,
)
from tests.support_paths import make_repo_scratch_dir


def _write_csv(path: Path, header: str, rows: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join([header, *rows]) + "\n", encoding="utf-8")


def _scratch_dir(label: str) -> Path:
    return make_repo_scratch_dir("strategy_ladder_first_run_tests", label)


def test_first_controlled_run_refuses_broad_scan_without_allow_flag() -> None:
    scratch = _scratch_dir("first_run_blocked")
    shutil.rmtree(scratch, ignore_errors=True)
    try:
        result = run_strategy_ladder_first_controlled_run(
            StrategyLadderFirstControlledRunRequest(
                run_id="first-run-blocked",
                input_root=scratch / "input",
                output_root=scratch / "output",
                silver_root=scratch / "output" / "silver",
                gold_root=scratch / "output" / "gold",
            )
        )

        assert result.manifest.first_run_status == "FIRST_RUN_BLOCKED_BY_DATA_FACTORY"
        assert "BROAD_RUN_REQUIRES_ALLOW_BROAD_RUN" in result.manifest.blocker_codes
        assert (scratch / "output" / "first_run_stage_summary.json").exists()
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_first_controlled_run_dry_run_emits_reports_not_measured_artifacts() -> None:
    scratch = _scratch_dir("first_run_dry")
    shutil.rmtree(scratch, ignore_errors=True)
    try:
        raw_root = scratch / "raw"
        _write_csv(
            raw_root / "trades" / "ADAUSDT_2023-01-01.csv",
            "id,timestamp,price,volume,side",
            ["1,1672531200000,1,1,buy"],
        )
        _write_csv(
            raw_root / "klines" / "ADAUSDT_1_2023-01-01.csv",
            "startTime,open,high,low,close,volume,turnover",
            ["1672531200000,1,1,1,1,1,1"],
        )

        output_root = scratch / "first_run"
        result = run_strategy_ladder_first_controlled_run(
            StrategyLadderFirstControlledRunRequest(
                run_id="first-run-dry",
                input_root=scratch / "input",
                raw_roots=(raw_root,),
                output_root=output_root,
                silver_root=output_root / "silver",
                gold_root=output_root / "gold",
                pairs=("ADAUSDT",),
                dry_run=True,
                small_scope=True,
            )
        )

        blockers_payload = json.loads((output_root / "first_run_blockers.json").read_text(encoding="utf-8"))
        assert result.manifest.first_run_status == "FIRST_RUN_READY_TO_EXECUTE"
        assert result.manifest.capital_profile_status == "CAPITAL_PROFILE_NOT_PROVEN"
        assert not (output_root / "backtest_strategy_ladder").exists()
        assert isinstance(blockers_payload["blockers"], list)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_first_controlled_run_rejects_training_mode() -> None:
    scratch = _scratch_dir("first_run_ml_blocked")
    shutil.rmtree(scratch, ignore_errors=True)
    try:
        with pytest.raises(ValueError, match="forbids ML_MODE_TRAINING_LAB_ONLY"):
            run_strategy_ladder_first_controlled_run(
                StrategyLadderFirstControlledRunRequest(
                    run_id="first-run-ml-blocked",
                    input_root=scratch / "input",
                    output_root=scratch / "output",
                    silver_root=scratch / "output" / "silver",
                    gold_root=scratch / "output" / "gold",
                    ml_mode="ML_MODE_TRAINING_LAB_ONLY",
                    small_scope=True,
                )
            )
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_first_controlled_run_wires_engine_native_bridge_into_runner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scratch = _scratch_dir("first_run_engine_native_wire")
    shutil.rmtree(scratch, ignore_errors=True)
    try:
        captured: dict[str, object] = {}

        def _fake_data_factory(request):
            captured["data_factory_request"] = request
            return SimpleNamespace(
                manifest=SimpleNamespace(
                    blocker_codes=(),
                    data_factory_status="DATA_FACTORY_READY",
                    raw_source_status="RAW_SOURCE_READY",
                    pair_universe_status="PAIR_UNIVERSE_READY",
                    silver_index_status="SILVER_INDEX_READY",
                    gold_feature_store_status="FEATURE_STORE_READY",
                    trade_schema_status="TRADE_SCHEMA_READY",
                    kline_schema_status="KLINE_SCHEMA_READY",
                    orderbook_schema_status="ORDERBOOK_SCHEMA_READY",
                    files_processed=1,
                    files_skipped=0,
                ),
                pair_universe_report=SimpleNamespace(available_pairs=("BTCUSDT",)),
                gold_feature_manifest=SimpleNamespace(
                    gold_feature_store_status="FEATURE_STORE_READY"
                ),
            )

        fake_run_manifest = SimpleNamespace(
            feature_store_status="FEATURE_STORE_READY",
            candidate_export_status="CANDIDATE_EXPORT_READY",
            raw_window_extraction_status="RAW_WINDOW_READY",
            detailed_replay_status="DETAILED_REPLAY_READY",
            capital_profile_generation_status="CAPITAL_PROFILE_GENERATION_READY",
            promotion_artifact_status="PROMOTION_ARTIFACTS_READY",
            sample_size_survival_status="SAMPLE_SIZE_NOT_PROVEN",
            blocker_codes=(),
            final_status="STRATEGY_LADDER_BLOCKED_BY_NO_EXECUTED_TRADES",
            candidate_count=1,
            detailed_replay_count=1,
            capital_profile_count=1,
        )

        def _fake_backtest_runner(request, progress_callback=None):
            captured["ladder_request"] = request
            return SimpleNamespace(run_manifest=fake_run_manifest)

        monkeypatch.setattr(
            first_run_module,
            "run_strategy_ladder_data_factory",
            _fake_data_factory,
        )
        monkeypatch.setattr(
            first_run_module,
            "run_backtest_strategy_ladder",
            _fake_backtest_runner,
        )
        monkeypatch.setattr(
            first_run_module,
            "_write_first_run_payloads",
            lambda *args, **kwargs: None,
        )

        run_strategy_ladder_first_controlled_run(
            StrategyLadderFirstControlledRunRequest(
                run_id="first-run-engine-native",
                input_root=scratch / "input",
                raw_roots=(scratch / "raw",),
                output_root=scratch / "output",
                silver_root=scratch / "output" / "silver",
                gold_root=scratch / "output" / "gold",
                pairs=("BTCUSDT",),
                start="2025-07-22",
                end="2025-07-22",
                small_scope=True,
                engine_native_mode=True,
                engine_native_sample_size=7,
            )
        )

        data_factory_request = captured["data_factory_request"]
        ladder_request = captured["ladder_request"]
        assert data_factory_request.use_measured_economic_provenance is True
        assert data_factory_request.small_scope is True
        assert data_factory_request.max_gold_feature_rows == 7
        assert ladder_request.engine_native_mode is True
        assert ladder_request.engine_native_sample_size == 7
        assert ladder_request.candidate_sample_cap == 7
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
