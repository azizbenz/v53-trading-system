"""Build-9 integration tests — real meta runtime path."""

from __future__ import annotations

import json

from meta_minimal.edge_tracker_prudent_minimal.edge_status_classifier import EdgeStatus
from meta_minimal.dtr_core.decision_state_encoder import DecisionState
from meta_minimal.dtr_core.dtr_record_builder import build_dtr
from meta_minimal.meta_runtime import (
    build_meta_runtime_result_from_records,
    MetaInputSource,
    MetaRuntime,
    MetaRuntimeConfig,
    MetaRuntimeInput,
    MetaRuntimeStatus,
)


def _runtime_input(
    dtr_id: str,
    *,
    pair: str = "BTC/USDT",
    engine_id: str = "engine_a",
    input_source: MetaInputSource = MetaInputSource.REAL_MARKET,
    path_complete: bool = True,
    path_warnings: tuple[str, ...] = (),
    selected: bool = False,
    was_reduced: bool = False,
    is_phantom: bool = False,
    was_executed: bool = False,
    ranking_rejected: bool = False,
    hard_blocked: bool = False,
    candidate_size: float = 100.0,
    final_size: float = 100.0,
    expected_cost: float = 0.01,
    realized_cost: float = 0.01,
    raw_score: float = 0.08,
    final_score: float = 0.08,
    gross_return: float = 0.05,
) -> MetaRuntimeInput:
    return MetaRuntimeInput(
        dtr_id=dtr_id,
        pair=pair,
        engine_id=engine_id,
        runtime_mode="shadow",
        input_source=input_source,
        path_complete=path_complete,
        path_warnings=path_warnings,
        raw_score=raw_score,
        penalized_score=raw_score,
        final_score=final_score,
        ranking_position=1,
        candidate_size=candidate_size,
        final_size=final_size,
        tier="tier_1",
        expected_cost=expected_cost,
        realized_cost=realized_cost,
        gross_return=gross_return,
        score_step="raw=0.08",
        ranking_step="rank=1",
        allocation_step="size=100",
        execution_step="sent_to_execution" if was_executed else "",
        selected=selected,
        was_reduced=was_reduced,
        is_phantom=is_phantom,
        was_executed=was_executed,
        ranking_rejected=ranking_rejected,
        hard_blocked=hard_blocked,
        timestamp=1000.0,
    )


def test_meta_runtime_runs_full_path_and_flushes(repo_tmp_path):
    runtime = MetaRuntime(
        config=MetaRuntimeConfig(flush_dir=repo_tmp_path, flush_to_disk=True)
    )
    result = runtime.evaluate(
        (
            _runtime_input("dtr_exec_1", was_executed=True, selected=True, final_score=0.05, realized_cost=0.01),
            _runtime_input("dtr_exec_2", pair="ETH/USDT", engine_id="engine_b", was_executed=True, selected=True, final_score=0.06, realized_cost=0.01, gross_return=0.06),
            _runtime_input("dtr_rank_reject", pair="SOL/USDT", ranking_rejected=True, candidate_size=0.0, final_size=0.0),
        )
    )

    assert result.status == MetaRuntimeStatus.READY
    assert result.dtr_summary.total_records == 3
    assert result.dtr_summary.dtr_coverage == 1.0
    assert result.cra_report.total_trades == 2
    assert result.break_even_report.views
    assert result.edge_report.total_scopes >= 2
    assert result.flushed_count == 3

    output = repo_tmp_path / "dtr_records.json"
    assert output.exists()
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert len(payload) == 3


def test_meta_runtime_flags_synthetic_inputs_and_excludes_them_from_edge():
    runtime = MetaRuntime()
    result = runtime.evaluate(
        (
            _runtime_input("dtr_real", was_executed=True, selected=True, final_score=0.05),
            _runtime_input(
                "dtr_synth",
                pair="ETH/USDT",
                engine_id="engine_b",
                input_source=MetaInputSource.SYNTHETIC,
                was_executed=True,
                selected=True,
                final_score=0.07,
            ),
        )
    )

    assert result.status == MetaRuntimeStatus.HAS_SYNTHETIC_INPUTS
    assert result.dtr_summary.synthetic_input_count == 1
    assert any("synthetic inputs detected" in warning for warning in result.warnings)
    assert all(classification.scope not in {"engine_b", "ETH/USDT", "engine_b:ETH/USDT"} for classification in result.edge_report.classifications)
    assert result.edge_report.total_scopes >= 1


def test_meta_runtime_marks_incomplete_path_in_dtr_and_status():
    runtime = MetaRuntime()
    result = runtime.evaluate(
        (
            _runtime_input(
                "dtr_incomplete",
                path_complete=False,
                path_warnings=("mocked execution step",),
                selected=True,
                was_reduced=True,
                final_size=40.0,
            ),
        )
    )

    assert result.status == MetaRuntimeStatus.HAS_PATH_WARNINGS
    assert result.dtr_summary.incomplete_path_count == 1
    assert result.records[0].path_complete is False
    assert "mocked execution step" in result.records[0].path_warnings


def test_local_replay_edge_is_not_promoted_to_credible():
    runtime = MetaRuntime()
    result = runtime.evaluate(
        tuple(
            _runtime_input(
                f"dtr_lr_{idx}",
                input_source=MetaInputSource.LOCAL_REPLAY,
                was_executed=True,
                selected=True,
                final_score=0.05 + idx * 0.001,
                realized_cost=0.005,
            )
            for idx in range(35)
        )
    )

    assert result.status == MetaRuntimeStatus.HAS_PATH_WARNINGS
    assert result.dtr_summary.local_replay_input_count == 35
    assert result.edge_report.total_scopes >= 1
    assert all(classification.status != EdgeStatus.CREDIBLE for classification in result.edge_report.classifications)


def test_build_meta_runtime_result_from_records_reconstructs_reports_from_dtr_exports():
    records = (
        build_dtr(
            dtr_id="dtr-1",
            pair="BTCUSDT",
            engine_id="engine_a",
            decision_state=DecisionState.EXECUTED,
            expected_cost=0.001,
            realized_cost=0.0009,
            gross_return=0.004,
            runtime_mode="local_replay",
            input_source="local_replay",
            timestamp=1_700_000_000.0,
        ),
        build_dtr(
            dtr_id="dtr-2",
            pair="BTCUSDT",
            engine_id="engine_a",
            decision_state=DecisionState.EXECUTED,
            expected_cost=0.0011,
            realized_cost=0.0010,
            gross_return=0.0042,
            runtime_mode="local_replay",
            input_source="local_replay",
            timestamp=1_700_000_100.0,
        ),
    )

    result = build_meta_runtime_result_from_records(records)

    assert result.status == MetaRuntimeStatus.HAS_PATH_WARNINGS
    assert result.records == records
    assert result.dtr_summary.total_records == 2
    assert result.dtr_summary.local_replay_input_count == 2
    assert result.cra_report.total_trades == 2
    assert result.break_even_report.views
    assert result.edge_report.total_scopes >= 1
    assert any("local replay inputs detected" in warning for warning in result.warnings)
