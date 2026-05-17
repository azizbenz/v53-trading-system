"""Patch 6 — output-root selector + backtest proof matrix tests.

Covers:
- Output-root form propagation (form -> job_request -> command_preview -> job_status).
- Output-root safety guards (defaulted, inside-raw-root, exists-non-empty).
- Date-guard tightening (DATE_RANGE_REQUIRED_FOR_NON_DRY_RUN).
- Proof matrix builder (READY vs gap classification, no fake metrics).
"""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import threading
from uuid import uuid4

import pytest

from cockpit import action_support as action_support_module
from cockpit.action_support import (
    CockpitBacktestJobKind,
    OUTPUT_ROOT_DEFAULTED,
    OUTPUT_ROOT_EXISTS_NON_EMPTY,
    OUTPUT_ROOT_INSIDE_RAW_ROOT,
    OUTPUT_ROOT_INVALID_PATH,
    OUTPUT_ROOT_NOT_WRITABLE,
    OUTPUT_ROOT_READY,
    launch_backtest_job,
    resolve_output_root,
)
from cockpit.backtest_preflight import build_patch6_preflight_preview
from cockpit.runtime_support import (
    StrategyLadderBacktestSummary,
    _enrich_strategy_ladder_summary_from_artifacts,
)
from cockpit.form_state_support import (
    BacktestFormState,
    read_backtest_form_state,
    write_backtest_form_state,
)
from local_replay_runtime.backtest_proof_matrix import (
    build_backtest_proof_matrix,
    emit_backtest_proof_matrix,
    write_backtest_proof_matrix,
)
from local_replay_runtime.strategy_ladder_data_factory_models import (
    StrategyLadderFirstControlledRunRequest,
)
from local_replay_runtime.strategy_ladder_first_controlled_run import (
    classify_date_guard,
)


def _scratch_dir(label: str) -> Path:
    repo_root = Path(__file__).resolve().parents[2]
    base_dir = repo_root / ".test_tmp"
    base_dir.mkdir(parents=True, exist_ok=True)
    output_dir = base_dir / f"{label}_{uuid4().hex}"
    output_dir.mkdir(parents=True, exist_ok=False)
    return output_dir


# ---------------------------------------------------------------------------
# resolve_output_root unit tests
# ---------------------------------------------------------------------------


def test_resolve_output_root_empty_returns_default_with_defaulted_status() -> None:
    scratch = _scratch_dir("output_root_default")
    try:
        default = scratch / "default_out"
        resolved, status, blocker = resolve_output_root(
            operator_output_root="",
            default_output_root=default,
            raw_roots=(),
        )
        assert resolved == default
        assert status == OUTPUT_ROOT_DEFAULTED
        assert blocker == ""
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_resolve_output_root_custom_path_is_ready() -> None:
    scratch = _scratch_dir("output_root_custom")
    try:
        default = scratch / "default_out"
        custom = scratch / "operator_chosen"
        resolved, status, blocker = resolve_output_root(
            operator_output_root=str(custom),
            default_output_root=default,
            raw_roots=(),
        )
        assert resolved == custom.resolve()
        assert status == OUTPUT_ROOT_READY
        assert blocker == ""
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_resolve_output_root_inside_raw_root_is_blocked() -> None:
    scratch = _scratch_dir("output_root_inside_raw")
    try:
        raw_root = scratch / "raw_data"
        raw_root.mkdir(parents=True, exist_ok=True)
        default = scratch / "default_out"
        custom_inside_raw = raw_root / "would_overwrite_raw"
        resolved, status, blocker = resolve_output_root(
            operator_output_root=str(custom_inside_raw),
            default_output_root=default,
            raw_roots=(raw_root,),
        )
        assert resolved == default
        assert status == OUTPUT_ROOT_INSIDE_RAW_ROOT
        assert blocker == OUTPUT_ROOT_INSIDE_RAW_ROOT
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_resolve_output_root_existing_non_empty_is_blocked() -> None:
    scratch = _scratch_dir("output_root_non_empty")
    try:
        existing = scratch / "existing"
        existing.mkdir(parents=True, exist_ok=True)
        (existing / "stale.txt").write_text("old run", encoding="utf-8")
        default = scratch / "default_out"
        resolved, status, blocker = resolve_output_root(
            operator_output_root=str(existing),
            default_output_root=default,
            raw_roots=(),
        )
        assert status == OUTPUT_ROOT_EXISTS_NON_EMPTY
        assert blocker == OUTPUT_ROOT_EXISTS_NON_EMPTY
        assert resolved == default
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_resolve_output_root_existing_non_empty_passes_with_resume() -> None:
    scratch = _scratch_dir("output_root_resume")
    try:
        existing = scratch / "existing_resume"
        existing.mkdir(parents=True, exist_ok=True)
        (existing / "prior.txt").write_text("resume", encoding="utf-8")
        default = scratch / "default_out"
        resolved, status, blocker = resolve_output_root(
            operator_output_root=str(existing),
            default_output_root=default,
            raw_roots=(),
            allow_resume=True,
        )
        assert status == OUTPUT_ROOT_READY
        assert blocker == ""
        assert resolved == existing.resolve()
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


# ---------------------------------------------------------------------------
# launch_backtest_job — output_root propagation
# ---------------------------------------------------------------------------


def test_launch_backtest_job_propagates_operator_output_root_to_record_and_command() -> None:
    scratch = _scratch_dir("launch_output_root")
    try:
        jobs_root = scratch / "jobs"
        jobs_root.mkdir(parents=True, exist_ok=True)
        export_dir = scratch / "exports"
        export_dir.mkdir(parents=True, exist_ok=True)
        operator_out = scratch / "operator_out"

        record = launch_backtest_job(
            jobs_root=jobs_root,
            job_kind=CockpitBacktestJobKind.STRATEGY_LADDER_DATA_FACTORY,
            export_dir=export_dir,
            action_name="DATA_FACTORY_DRY_RUN",
            raw_roots=(),
            pairs=("BTCUSDT",),
            start="2025-04-29",
            end="2025-04-30",
            operator_output_root=str(operator_out),
            blocked_reason="",
        )

        expected_run_root = operator_out.resolve() / "runs" / record.job_id
        assert record.output_root == str(expected_run_root)
        assert "--output-root" in record.command_preview
        assert str(expected_run_root) in record.command_preview

        # job_request.json + job_status.json must round-trip the operator path.
        job_request = json.loads(Path(record.job_request_path).read_text(encoding="utf-8"))
        job_status = json.loads(Path(record.job_status_path).read_text(encoding="utf-8"))
        assert job_request["output_root"] == str(expected_run_root)
        assert job_status["output_root"] == str(expected_run_root)
        assert "--output-root" in job_request["command_preview"]
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_launch_backtest_job_blocks_output_root_inside_raw_root() -> None:
    scratch = _scratch_dir("launch_blocked_inside_raw")
    try:
        jobs_root = scratch / "jobs"
        jobs_root.mkdir(parents=True, exist_ok=True)
        raw_root = scratch / "raw"
        raw_root.mkdir(parents=True, exist_ok=True)
        operator_out = raw_root / "would_overwrite"

        record = launch_backtest_job(
            jobs_root=jobs_root,
            job_kind=CockpitBacktestJobKind.STRATEGY_LADDER_DATA_FACTORY,
            export_dir=scratch / "exports",
            action_name="DATA_FACTORY_DRY_RUN",
            raw_roots=(raw_root,),
            pairs=("BTCUSDT",),
            operator_output_root=str(operator_out),
        )

        # The job is created but blocked; the executed command is the safe
        # ``blocked --reason`` form rather than the real launcher.
        assert OUTPUT_ROOT_INSIDE_RAW_ROOT in record.blockers
        assert "blocked" in record.command
        assert "--reason" in record.command
        assert OUTPUT_ROOT_INSIDE_RAW_ROOT in record.command
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_launch_backtest_job_allows_phase_a2_rerun_on_existing_phase_root(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scratch = _scratch_dir("launch_phase_a2_rerun")
    try:
        jobs_root = scratch / "jobs"
        jobs_root.mkdir(parents=True, exist_ok=True)
        operator_root = scratch / "operator_out"
        workflow_root = operator_root / "runs" / "strategy_ladder_workflow-demo"
        phase_root = workflow_root / "phase_a2_data_factory"
        phase_root.mkdir(parents=True, exist_ok=True)
        (phase_root / "stale_partial.json").write_text("{}", encoding="utf-8")

        monkeypatch.setattr(threading.Thread, "start", lambda self: None)

        record = launch_backtest_job(
            jobs_root=jobs_root,
            job_kind=CockpitBacktestJobKind.STRATEGY_LADDER_DATA_FACTORY,
            export_dir=scratch / "exports",
            action_name="PHASE_A2_DATA_FACTORY",
            phase_id="PHASE_A2",
            workflow_run_id="strategy_ladder_workflow-demo",
            request_hash="hash-a2-rerun",
            raw_roots=(),
            pairs=("BTCUSDT",),
            start="2025-04-29",
            end="2025-04-29",
            operator_output_root=str(operator_root),
        )

        assert record.status == "JOB_CREATED"
        assert record.output_root == str(phase_root.resolve())
        assert OUTPUT_ROOT_EXISTS_NON_EMPTY not in record.blockers
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_run_backtest_job_surfaces_process_start_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scratch = _scratch_dir("launch_process_start_failure")
    try:
        jobs_root = scratch / "jobs"
        jobs_root.mkdir(parents=True, exist_ok=True)
        export_dir = scratch / "exports"
        export_dir.mkdir(parents=True, exist_ok=True)

        monkeypatch.setattr(threading.Thread, "start", lambda self: None)

        record = launch_backtest_job(
            jobs_root=jobs_root,
            job_kind=CockpitBacktestJobKind.STRATEGY_LADDER_DATA_FACTORY,
            export_dir=export_dir,
            action_name="PHASE_A2_DATA_FACTORY",
            phase_id="PHASE_A2",
            raw_roots=(),
            pairs=("BTCUSDT",),
            start="2025-04-29",
            end="2025-04-29",
            operator_output_root=str(scratch / "operator_out"),
            blocked_reason="",
        )

        def _raise_popen(*args, **kwargs):
            raise OSError("spawn denied for test")

        monkeypatch.setattr(action_support_module.subprocess, "Popen", _raise_popen)

        action_support_module._run_backtest_job(
            record_path=Path(record.record_path),
            record=record,
        )

        job_payload = json.loads(Path(record.record_path).read_text(encoding="utf-8"))
        status_payload = json.loads(Path(record.job_status_path).read_text(encoding="utf-8"))
        stdout_text = Path(record.stdout_log_path).read_text(encoding="utf-8")

        assert job_payload["status"] == "JOB_FAILED"
        assert "JOB_PROCESS_START_FAILED" in job_payload["blockers"]
        assert job_payload["error_summary"] == "process_start_failed:OSError"
        assert status_payload["status"] == "JOB_FAILED"
        assert status_payload["error_code"] == "process_start_failed:OSError"
        assert "JOB_PROCESS_START_FAILED" in stdout_text
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


# ---------------------------------------------------------------------------
# BacktestFormState — round-trip the new field
# ---------------------------------------------------------------------------


def test_backtest_form_state_round_trips_output_root() -> None:
    scratch = _scratch_dir("form_state_output_root")
    try:
        state = BacktestFormState(output_root="J:\\v53\\custom_out")
        write_backtest_form_state(scratch, state)
        loaded = read_backtest_form_state(scratch)
        assert loaded.output_root == "J:\\v53\\custom_out"
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


# ---------------------------------------------------------------------------
# Date guard — DATE_RANGE_REQUIRED_FOR_NON_DRY_RUN
# ---------------------------------------------------------------------------


def _first_run_request(
    *,
    start: str = "",
    end: str = "",
    pairs: tuple[str, ...] = (),
    dry_run: bool = False,
    small_scope: bool = False,
    fixture_mode: bool = False,
    allow_broad_run: bool = False,
) -> StrategyLadderFirstControlledRunRequest:
    scratch = _scratch_dir("first_run_request")
    return StrategyLadderFirstControlledRunRequest(
        run_id="test-run",
        input_root=scratch,
        output_root=scratch / "output",
        silver_root=scratch / "silver",
        gold_root=scratch / "gold",
        pairs=pairs,
        start=start,
        end=end,
        dry_run=dry_run,
        fixture_mode=fixture_mode,
        small_scope=small_scope,
        allow_broad_run=allow_broad_run,
    )


def test_date_guard_blocks_non_dry_run_without_dates() -> None:
    request = _first_run_request(pairs=("BTCUSDT",))
    blockers = classify_date_guard(request)
    assert "DATE_RANGE_REQUIRED_FOR_NON_DRY_RUN" in blockers


def test_date_guard_allows_explicit_window() -> None:
    request = _first_run_request(
        pairs=("BTCUSDT",), start="2025-04-29", end="2025-04-30"
    )
    blockers = classify_date_guard(request)
    assert blockers == ()


def test_date_guard_passes_for_dry_run_without_dates() -> None:
    request = _first_run_request(pairs=("BTCUSDT",), dry_run=True)
    blockers = classify_date_guard(request)
    assert blockers == ()


def test_date_guard_blocks_broad_run_without_explicit_confirmation() -> None:
    request = _first_run_request()  # no pairs, no start, no end, not dry
    blockers = classify_date_guard(request)
    assert "BROAD_RUN_REQUIRES_EXPLICIT_CONFIRMATION" in blockers
    assert "DATE_RANGE_REQUIRED_FOR_NON_DRY_RUN" in blockers


def test_preflight_surfaces_execution_realism_claim_blockers() -> None:
    scratch = _scratch_dir("preflight_execution_realism")
    try:
        preview = build_patch6_preflight_preview(
            selected_form=BacktestFormState(
                action_name="FIRST_CONTROLLED_RUN_SMALL_SCOPE",
                orderbook_path="",
                trades_path="",
                klines_path=str(scratch / "klines"),
                metadata_path="",
            ),
            jobs_root=scratch / "jobs",
        )
        assert preview.execution_realism_claim_status == "REALISM_CLAIM_BLOCKED"
        assert (
            "ORDERBOOK_AND_TRADES_REQUIRED_FOR_EXECUTION_REALISM"
            in preview.execution_realism_claim_blockers
        )
        assert (
            "HISTORICAL_METADATA_REQUIRED_FOR_REALISTIC_EXECUTION_COSTS"
            in preview.execution_realism_claim_blockers
        )
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


# ---------------------------------------------------------------------------
# Proof matrix builder
# ---------------------------------------------------------------------------


def _write_manifest(output_root: Path, payload: dict) -> None:
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "data_factory_manifest.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )


def _write_quality_report(output_root: Path, payload: dict) -> None:
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "data_quality_report.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )


def _ready_data_factory_manifest() -> dict:
    return {
        "schema_version": "v1",
        "run_id": "df-test",
        "data_factory_status": "DATA_FACTORY_READY",
        "raw_source_status": "RAW_SOURCE_READY",
        "pair_universe_status": "PAIR_UNIVERSE_READY",
        "silver_index_status": "SILVER_INDEX_READY",
        "gold_feature_store_status": "FEATURE_STORE_READY",
        "trade_schema_status": "TRADE_SCHEMA_READY",
        "kline_schema_status": "KLINE_SCHEMA_READY",
        "orderbook_schema_status": "ORDERBOOK_SCHEMA_READY",
        "metadata_schema_status": "METADATA_SCHEMA_NOT_PROVEN",
        "compression_status": "COMPRESSION_READY",
        "blocker_codes": [],
    }


def test_proof_matrix_emits_research_only_when_metadata_missing() -> None:
    scratch = _scratch_dir("proof_matrix_research_only")
    try:
        _write_manifest(scratch, _ready_data_factory_manifest())
        matrix = build_backtest_proof_matrix(
            output_root=scratch,
            run_id="df-test",
            pairs=("BTCUSDT",),
            start="2025-04-29",
            end="2025-04-30",
        )
        assert matrix.data_factory_status == "READY"
        assert matrix.metadata_schema_status == "NOT_PROVEN"
        # No metadata => no fees, no capital bucket, no executed-only economics.
        assert matrix.fee_provenance_status == "NOT_PROVEN"
        assert matrix.capital_bucket_status == "NOT_PROVEN"
        assert matrix.executed_only_economics_status == "NOT_PROVEN"
        # Drawdown and impact never auto-promote.
        assert matrix.true_drawdown_status == "NOT_PROVEN"
        assert matrix.impact_provenance_status == "NOT_PROVEN"
        assert matrix.overall_backtest_proof_status == "BACKTEST_PROOF_RESEARCH_ONLY"
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_proof_matrix_reads_bybit_historical_metadata_cache_status() -> None:
    scratch = _scratch_dir("proof_matrix_historical_metadata")
    try:
        manifest = _ready_data_factory_manifest()
        manifest.update(
            {
                "metadata_schema_status": "METADATA_SCHEMA_READY",
                "historical_metadata_status": "BYBIT_HISTORICAL_METADATA_READY",
                "metadata_source_mode": "LOCAL_METADATA_CACHE",
            }
        )
        _write_manifest(scratch, manifest)
        _write_quality_report(
            scratch,
            {
                "metadata_source_mode": "LOCAL_METADATA_CACHE",
                "metadata_cache_path": "K:/v5.3 backtest/metadata/bybit/spot/symbol_metadata.csv",
                "metadata_pairs_covered": ["BTCUSDT"],
                "missing_metadata_pairs": [],
                "metadata_temporal_status": "CURRENT_METADATA_PROXY",
                "metadata_fetched_at_utc": "2026-05-05T00:00:00+00:00",
                "capital_bucket_metadata_status": "CAPITAL_BUCKET_METADATA_READY_REPLAY_NOT_PROVEN",
            },
        )
        (scratch / "silver_index.json").write_text(
            json.dumps(
                {
                    "schema_version": "v1",
                    "status": "SILVER_INDEX_READY",
                    "entries": [
                        {
                            "data_type": "metadata",
                            "row_count": 1,
                            "path": str(scratch / "silver" / "metadata" / "symbol_metadata.jsonl"),
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        matrix = build_backtest_proof_matrix(
            output_root=scratch,
            run_id="df-test",
            pairs=("BTCUSDT",),
        )
        assert matrix.historical_metadata_status == "BYBIT_HISTORICAL_METADATA_READY"
        assert matrix.metadata_source_mode == "LOCAL_METADATA_CACHE"
        assert matrix.metadata_pairs_covered == ("BTCUSDT",)
        assert matrix.missing_metadata_pairs == ()
        assert matrix.metadata_temporal_status == "CURRENT_METADATA_PROXY"
        assert matrix.fee_provenance_status == "CONFIGURED_FEE_PROVENANCE_READY"
        assert (
            matrix.capital_bucket_metadata_status
            == "CAPITAL_BUCKET_METADATA_READY_REPLAY_NOT_PROVEN"
        )
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_proof_matrix_blocked_when_blocker_codes_present() -> None:
    scratch = _scratch_dir("proof_matrix_blocked")
    try:
        manifest = _ready_data_factory_manifest()
        manifest["blocker_codes"] = ["TIMESTAMP_UNIT_AMBIGUOUS"]
        _write_manifest(scratch, manifest)
        matrix = build_backtest_proof_matrix(
            output_root=scratch, run_id="df-test"
        )
        assert "TIMESTAMP_UNIT_AMBIGUOUS" in matrix.blocker_codes
        assert matrix.overall_backtest_proof_status == "BACKTEST_PROOF_BLOCKED"
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_proof_matrix_metric_gaps_have_explicit_reason_codes() -> None:
    scratch = _scratch_dir("proof_matrix_gaps")
    try:
        _write_manifest(scratch, _ready_data_factory_manifest())
        matrix = build_backtest_proof_matrix(
            output_root=scratch, run_id="df-test"
        )
        gap_names = {entry.metric_name for entry in matrix.metric_gaps}
        # These must remain gaps without any source artefact.
        for required_gap in (
            "fee_provenance_status",
            "fill_realism_status",
            "true_drawdown_status",
            "executed_only_economics_status",
            "impact_provenance_status",
            "capital_bucket_status",
        ):
            assert required_gap in gap_names
        # Each gap carries an explicit reason code so the cockpit can show why.
        for entry in matrix.metric_gaps:
            assert entry.reason_codes, f"metric {entry.metric_name} has no reason code"
            assert entry.value is None, "no fake values in gap entries"
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_proof_matrix_ready_metrics_only_for_data_layer() -> None:
    scratch = _scratch_dir("proof_matrix_ready")
    try:
        _write_manifest(scratch, _ready_data_factory_manifest())
        matrix = build_backtest_proof_matrix(
            output_root=scratch, run_id="df-test"
        )
        ready_names = {entry.metric_name for entry in matrix.ready_metrics}
        # Data layer is READY.
        assert "data_factory_status" in ready_names
        assert "silver_index_status" in ready_names
        assert "trade_schema_status" in ready_names
        # Promotion and economics layers must NOT be READY.
        assert "engine_promotion_status" not in ready_names
        assert "executed_only_economics_status" not in ready_names
        assert "fee_provenance_status" not in ready_names
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_proof_matrix_emit_writes_json_and_md_files() -> None:
    scratch = _scratch_dir("proof_matrix_emit")
    try:
        _write_manifest(scratch, _ready_data_factory_manifest())
        matrix, json_path = emit_backtest_proof_matrix(
            output_root=scratch, run_id="df-test", pairs=("BTCUSDT",)
        )
        assert json_path.is_file()
        assert json_path.name == "backtest_proof_matrix.json"
        md_path = scratch / "backtest_proof_matrix.md"
        assert md_path.is_file()
        # JSON round-trip: payload must contain all required fields.
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        for required_field in (
            "data_factory_status",
            "metadata_schema_status",
            "fee_provenance_status",
            "fill_realism_status",
            "true_drawdown_status",
            "capital_bucket_status",
            "execution_label_source",
            "spread_model_source",
            "execution_fidelity_gap_codes",
            "promotion_artifact_status",
            "overall_backtest_proof_status",
            "metric_gaps",
            "ready_metrics",
            "blocker_codes",
        ):
            assert required_field in payload, required_field
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_proof_matrix_carries_execution_fidelity_and_blocks_promotion_ready() -> None:
    scratch = _scratch_dir("proof_matrix_execution_fidelity")
    try:
        _write_manifest(scratch, _ready_data_factory_manifest())
        run_dir = scratch / "backtest_strategy_ladder" / "strategy_ladder_runner-proof"
        reports_dir = run_dir / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        (reports_dir / "strategy_ladder_summary.json").write_text(
            json.dumps(
                {
                    "run_id": "strategy_ladder_runner-proof",
                    "promotion_artifact_status": "PROMOTION_ARTIFACTS_BLOCKED_BY_FIDELITY",
                    "sample_size_survival_status": "SAMPLE_SIZE_READY",
                    "candidate_truth_status": "CANDIDATE_ENGINE_NATIVE_READY",
                    "expected_edge_truth_status": "EXPECTED_EDGE_PROXY_BLOCKED",
                    "engine_native_status": "ENGINE_NATIVE_FULL_PATH_READY",
                    "execution_label_source": "PARTIAL_CANONICAL_EXECUTION",
                    "fee_model_source": "REPLAY_PROXY",
                    "spread_model_source": "CANONICAL_SPREAD_GUARD",
                    "slippage_model_source": "CANONICAL_EXECUTION_BACKBONE",
                    "partial_fill_model_source": "REPLAY_PROXY",
                    "adverse_selection_source": "REPLAY_PROXY",
                    "order_type_selection_source": "REPLAY_PROXY",
                    "venue_constraints_source": "REPLAY_PROXY",
                    "execution_fidelity_gap_codes": [
                        "PARTIAL_FILL_PROXY",
                        "VENUE_CONSTRAINTS_PROXY",
                    ],
                }
            ),
            encoding="utf-8",
        )

        matrix = build_backtest_proof_matrix(
            output_root=scratch,
            run_id="strategy_ladder_runner-proof",
            pairs=("BTCUSDT",),
        )
        assert matrix.promotion_artifact_status == "PROMOTION_ARTIFACTS_BLOCKED_BY_FIDELITY"
        assert matrix.engine_promotion_status == "BLOCKED"
        assert matrix.pair_promotion_status == "BLOCKED"
        assert matrix.execution_label_source == "PARTIAL_CANONICAL_EXECUTION"
        assert matrix.spread_model_source == "CANONICAL_SPREAD_GUARD"
        assert matrix.slippage_model_source == "CANONICAL_EXECUTION_BACKBONE"
        assert matrix.execution_fidelity_gap_codes == (
            "PARTIAL_FILL_PROXY",
            "VENUE_CONSTRAINTS_PROXY",
        )
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_proof_matrix_sequence_gap_blocker_forces_non_ready_substatuses() -> None:
    scratch = _scratch_dir("proof_matrix_sequence_gap_consistency")
    try:
        manifest = _ready_data_factory_manifest()
        manifest["blocker_codes"] = [
            "ORDERBOOK_SEQUENCE_GAP",
            "ORDERBOOK_RECONSTRUCTION_NOT_PROVEN",
        ]
        _write_manifest(scratch, manifest)
        (scratch / "silver_index.json").write_text(
            json.dumps(
                {
                    "schema_version": "v1",
                    "entries": [
                        {
                            "data_type": "orderbook_snapshot",
                            "row_count": 10,
                            "path": str(scratch / "snap.jsonl"),
                            "depth_source_status": "BOOK_DEPTH20_AVAILABLE",
                        },
                        {
                            "data_type": "orderbook_delta",
                            "row_count": 10,
                            "path": str(scratch / "delta.jsonl"),
                            "depth_source_status": "BOOK_DEPTH20_AVAILABLE",
                        },
                    ],
                    "status": "SILVER_INDEX_READY",
                }
            ),
            encoding="utf-8",
        )
        (scratch / "snap.jsonl").write_text("{}\n", encoding="utf-8")
        (scratch / "delta.jsonl").write_text("{}\n", encoding="utf-8")
        matrix = build_backtest_proof_matrix(output_root=scratch, run_id="df-test")
        assert matrix.sequence_gap_status != "BOOK_SEQUENCE_READY"
        assert matrix.orderbook_reconstruction_status != "ORDERBOOK_RECONSTRUCTION_READY"
        assert matrix.depth20_proof_status == "BOOK_DEPTH_NOT_PROVEN"
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_proof_matrix_reads_sequence_gap_report_details() -> None:
    scratch = _scratch_dir("proof_matrix_gap_report")
    try:
        manifest = _ready_data_factory_manifest()
        manifest["blocker_codes"] = ["ORDERBOOK_SEQUENCE_GAP"]
        _write_manifest(scratch, manifest)
        (scratch / "silver_index.json").write_text(
            json.dumps({"schema_version": "v1", "entries": [], "status": "SILVER_INDEX_READY"}),
            encoding="utf-8",
        )
        (scratch / "orderbook_sequence_gap_report.json").write_text(
            json.dumps(
                {
                    "pair": "BNBUSDT",
                    "gap_status": "ORDERBOOK_SEQUENCE_GAP_UNRECOVERED",
                    "gap_count": 1,
                    "gap_files": ["L:/orderbook/BNBUSDT/2025-04-29.data"],
                    "gap_dates": ["2025-04-29"],
                    "first_gap": {
                        "source_file": "L:/orderbook/BNBUSDT/2025-04-29.data",
                        "date": "2025-04-29",
                        "expected_seq": 42,
                        "actual_seq": 45,
                        "previous_seq": 41,
                        "event_timestamp_ms": 1745884800000,
                    },
                    "reconstruction_attempted": True,
                    "reconstruction_success_after_gap": False,
                    "snapshot_used_before_gap": "L:/orderbook/BNBUSDT/2025-04-29.data",
                    "delta_file_used": "L:/orderbook/BNBUSDT/2025-04-29.data",
                    "reason_codes": ["ORDERBOOK_SEQUENCE_GAP_UNRECOVERED"],
                }
            ),
            encoding="utf-8",
        )
        matrix = build_backtest_proof_matrix(output_root=scratch, run_id="df-test")
        assert matrix.sequence_gap_report_path.endswith("orderbook_sequence_gap_report.json")
        assert matrix.gap_count == 1
        assert matrix.gap_dates == ("2025-04-29",)
        assert matrix.first_gap_expected_seq == 42
        assert matrix.first_gap_actual_seq == 45
        assert matrix.gap_recovery_status == "ORDERBOOK_SEQUENCE_GAP_UNRECOVERED"
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_proof_matrix_falls_back_to_partial_phase2_artifacts_and_model_only_replay() -> None:
    scratch = _scratch_dir("proof_matrix_partial_phase2")
    try:
        manifest = _ready_data_factory_manifest()
        manifest.update(
            {
                "metadata_schema_status": "METADATA_SCHEMA_READY",
                "historical_metadata_status": "BYBIT_HISTORICAL_METADATA_READY",
            }
        )
        _write_manifest(scratch, manifest)
        _write_quality_report(
            scratch,
            {
                "metadata_source_mode": "LOCAL_METADATA_CACHE",
                "metadata_cache_path": "K:/v5.3 backtest/metadata/bybit/spot/symbol_metadata.csv",
                "metadata_pairs_covered": ["BTCUSDT"],
                "missing_metadata_pairs": [],
                "metadata_temporal_status": "CURRENT_METADATA_PROXY",
                "metadata_fetched_at_utc": "2026-05-05T00:00:00+00:00",
                "capital_bucket_metadata_status": "CAPITAL_BUCKET_METADATA_READY_REPLAY_NOT_PROVEN",
                "silver_storage_status": "SILVER_STORAGE_READY_COMPRESSED",
            },
        )
        (scratch / "silver_index.json").write_text(
            json.dumps(
                {
                    "schema_version": "v1",
                    "status": "SILVER_INDEX_READY",
                    "entries": [
                        {
                            "data_type": "metadata",
                            "row_count": 1,
                            "path": str(scratch / "silver" / "metadata.jsonl"),
                        },
                        {
                            "data_type": "orderbook_snapshot",
                            "row_count": 5,
                            "path": str(scratch / "snap.jsonl"),
                            "depth_source_status": "BOOK_DEPTH20_AVAILABLE",
                        },
                        {
                            "data_type": "orderbook_delta",
                            "row_count": 10,
                            "path": str(scratch / "delta.jsonl"),
                            "depth_source_status": "BOOK_DEPTH20_AVAILABLE",
                        },
                    ],
                }
            ),
            encoding="utf-8",
        )
        (scratch / "silver" / "metadata.jsonl").parent.mkdir(parents=True, exist_ok=True)
        (scratch / "silver" / "metadata.jsonl").write_text("{}\n", encoding="utf-8")
        (scratch / "snap.jsonl").write_text("{}\n", encoding="utf-8")
        (scratch / "delta.jsonl").write_text("{}\n", encoding="utf-8")
        run_dir = (
            scratch
            / "backtest_strategy_ladder"
            / "strategy_ladder_first_controlled_run-partial"
        )
        (run_dir / "fast_candidates").mkdir(parents=True, exist_ok=True)
        (run_dir / "fast_candidates" / "candidate_summary.json").write_text(
            json.dumps(
                {
                    "candidate_count": 2,
                    "candidate_export_status": "CANDIDATE_EXPORT_READY",
                }
            ),
            encoding="utf-8",
        )
        (run_dir / "raw_windows" / "BTCUSDT" / "cand-1").mkdir(parents=True, exist_ok=True)
        (run_dir / "raw_windows" / "BTCUSDT" / "cand-1" / "window_manifest.json").write_text(
            json.dumps(
                {
                    "candidate_id": "cand-1",
                    "pair": "BTCUSDT",
                    "engine_id": "engine_c",
                    "timestamp_ms": 1745884800000,
                    "window_start_ms": 1745881200000,
                    "window_end_ms": 1745888400000,
                    "window_extraction_status": "RAW_WINDOW_READY",
                    "book_depth_source_status": "BOOK_DEPTH20_AVAILABLE",
                    "source_coverage_status": "RAW_WINDOW_SOURCE_READY",
                }
            ),
            encoding="utf-8",
        )
        (run_dir / "raw_windows" / "BTCUSDT" / "cand-2").mkdir(parents=True, exist_ok=True)
        (run_dir / "raw_windows" / "BTCUSDT" / "cand-2" / "window_manifest.json").write_text(
            json.dumps(
                {
                    "candidate_id": "cand-2",
                    "pair": "BTCUSDT",
                    "engine_id": "engine_d",
                    "timestamp_ms": 1745884860000,
                    "window_start_ms": 1745881260000,
                    "window_end_ms": 1745888460000,
                    "window_extraction_status": "RAW_WINDOW_READY",
                    "book_depth_source_status": "BOOK_DEPTH20_AVAILABLE",
                    "source_coverage_status": "RAW_WINDOW_SOURCE_READY",
                }
            ),
            encoding="utf-8",
        )
        (run_dir / "detailed_replay").mkdir(parents=True, exist_ok=True)
        (run_dir / "detailed_replay" / "cand-1.json").write_text(
            json.dumps(
                {
                    "candidate_id": "cand-1",
                    "pair": "BTCUSDT",
                    "engine_id": "engine_c",
                    "strategy_id": "strategy_ladder",
                    "timestamp_ms": 1745884800000,
                    "detailed_replay_status": "DETAILED_REPLAY_READY",
                    "bucket_results": [
                        {
                            "candidate_id": "cand-1",
                            "pair": "BTCUSDT",
                            "engine_id": "engine_c",
                            "strategy_id": "strategy_ladder",
                            "capital_bucket": 400,
                            "timestamp_ms": 1745884800000,
                            "execution_state": "phantom",
                            "no_fill_flag": True,
                            "expected_ce_net": -0.00023,
                            "executed_only_net_return_status": "EXECUTED_NET_RETURN_INSUFFICIENT_EXECUTIONS",
                            "fee_source_status": "FEE_SOURCE_NOT_PROVEN",
                            "impact_source_status": "IMPACT_SOURCE_DEPTH20_MODEL",
                            "fill_realism_status": "FILL_REALISM_MODEL_ONLY",
                            "cost_parity_status": "REPLAY_LIVE_COST_PARITY_BLOCKED_BY_TELEMETRY",
                            "book_depth_source_status": "BOOK_DEPTH20_AVAILABLE",
                            "reason_codes": ["economically_absurd"],
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        (run_dir / "detailed_replay" / "cand-2.json").write_text(
            json.dumps(
                {
                    "candidate_id": "cand-2",
                    "pair": "BTCUSDT",
                    "engine_id": "engine_d",
                    "strategy_id": "strategy_ladder",
                    "timestamp_ms": 1745884860000,
                    "detailed_replay_status": "DETAILED_REPLAY_READY",
                    "bucket_results": [],
                }
            ),
            encoding="utf-8",
        )
        (run_dir / "reports").mkdir(parents=True, exist_ok=True)
        (run_dir / "reports" / "pair_matrix.json").write_text(
            json.dumps(
                [
                    {
                        "pair": "BTCUSDT",
                        "executed_count": 0,
                        "reduced_count": 0,
                        "no_fill_count": 2,
                        "fee_source_status": "FEE_SOURCE_NOT_PROVEN",
                        "impact_source_status": "IMPACT_SOURCE_DEPTH20_MODEL",
                        "fill_realism_status": "FILL_REALISM_MODEL_ONLY",
                        "cost_parity_status": "REPLAY_LIVE_COST_PARITY_BLOCKED_BY_TELEMETRY",
                        "executed_only_net_return_status": "EXECUTED_NET_RETURN_INSUFFICIENT_EXECUTIONS",
                        "true_net_equity_drawdown_status": "TRUE_NET_EQUITY_DRAWDOWN_INSUFFICIENT_EXECUTIONS",
                    }
                ]
            ),
            encoding="utf-8",
        )

        matrix = build_backtest_proof_matrix(
            output_root=scratch,
            run_id="strategy_ladder_first_controlled_run-partial",
            pairs=("BTCUSDT",),
        )
        assert matrix.candidate_export_status == "READY"
        assert matrix.raw_window_extraction_status == "READY"
        assert matrix.depth_replay_status == "READY"
        assert matrix.candidate_count == 2
        assert matrix.raw_window_count == 2
        assert matrix.detailed_replay_count == 2
        assert matrix.replay_fee_source_status == "FEE_SOURCE_NOT_PROVEN"
        assert matrix.replay_impact_source_status == "IMPACT_SOURCE_DEPTH20_MODEL"
        assert matrix.replay_fill_realism_status == "FILL_REALISM_MODEL_ONLY"
        assert (
            matrix.replay_cost_parity_status
            == "REPLAY_LIVE_COST_PARITY_BLOCKED_BY_TELEMETRY"
        )
        assert matrix.historical_replay_venue == "BYBIT"
        assert matrix.execution_target_venue == "BINANCE"
        assert matrix.overall_backtest_proof_status == "BACKTEST_PROOF_RESEARCH_ONLY"
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_proof_matrix_uses_run_manifest_and_stage_summary_for_detailed_replay() -> None:
    scratch = _scratch_dir("proof_matrix_completed_replay_rollup")
    try:
        manifest = _ready_data_factory_manifest()
        _write_manifest(scratch, manifest)
        (scratch / "silver_index.json").write_text(
            json.dumps(
                {
                    "schema_version": "v1",
                    "status": "SILVER_INDEX_READY",
                    "entries": [
                        {
                            "data_type": "orderbook_snapshot",
                            "row_count": 5,
                            "path": str(scratch / "snap.jsonl"),
                            "depth_source_status": "BOOK_LIMITED_DEPTH_AVAILABLE",
                        },
                        {
                            "data_type": "orderbook_delta",
                            "row_count": 10,
                            "path": str(scratch / "delta.jsonl"),
                            "depth_source_status": "BOOK_LIMITED_DEPTH_AVAILABLE",
                        },
                    ],
                }
            ),
            encoding="utf-8",
        )
        (scratch / "snap.jsonl").write_text("{}\n", encoding="utf-8")
        (scratch / "delta.jsonl").write_text("{}\n", encoding="utf-8")
        (scratch / "first_run_manifest.json").write_text(
            json.dumps(
                {
                    "run_id": "strategy_ladder_first_controlled_run-complete",
                    "first_run_status": "FIRST_RUN_RAN_WITH_PARTIAL_EVIDENCE",
                    "raw_window_status": "RAW_WINDOW_READY",
                    "blocker_codes": [],
                }
            ),
            encoding="utf-8",
        )
        (scratch / "first_run_stage_summary.json").write_text(
            json.dumps(
                {
                    "run_id": "strategy_ladder_first_controlled_run-complete",
                    "stage_statuses": {
                        "candidate_export_status": "CANDIDATE_EXPORT_READY",
                        "raw_window_status": "RAW_WINDOW_READY",
                        "detailed_replay_status": "DETAILED_REPLAY_READY",
                    },
                    "candidate_count": 2,
                    "detailed_replay_count": 8,
                    "capital_profile_count": 4,
                    "blockers": [],
                }
            ),
            encoding="utf-8",
        )
        run_dir = (
            scratch
            / "backtest_strategy_ladder"
            / "strategy_ladder_first_controlled_run-complete"
        )
        (run_dir / "fast_candidates").mkdir(parents=True, exist_ok=True)
        (run_dir / "fast_candidates" / "candidate_summary.json").write_text(
            json.dumps(
                {
                    "candidate_count": 2,
                    "candidate_export_status": "CANDIDATE_EXPORT_READY",
                }
            ),
            encoding="utf-8",
        )
        (run_dir / "run_manifest.json").write_text(
            json.dumps(
                {
                    "run_id": "strategy_ladder_first_controlled_run-complete",
                    "candidate_count": 2,
                    "raw_window_count": 2,
                    "detailed_replay_count": 8,
                    "candidate_export_status": "CANDIDATE_EXPORT_READY",
                    "raw_window_extraction_status": "RAW_WINDOW_READY",
                    "detailed_replay_status": "DETAILED_REPLAY_READY",
                    "blocker_codes": [],
                }
            ),
            encoding="utf-8",
        )

        matrix = build_backtest_proof_matrix(
            output_root=scratch,
            run_id="strategy_ladder_first_controlled_run-complete",
            pairs=("BTCUSDT",),
        )
        assert matrix.candidate_export_status == "READY"
        assert matrix.raw_window_extraction_status == "READY"
        assert matrix.depth_replay_status == "READY"
        assert matrix.phase2_detailed_replay_status == "PHASE2_DETAILED_REPLAY_READY"
        assert matrix.candidate_count == 2
        assert matrix.raw_window_count == 2
        assert matrix.detailed_replay_count == 8
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_proof_matrix_prefers_bloat_warning_from_compression_report() -> None:
    scratch = _scratch_dir("proof_matrix_silver_bloat")
    try:
        _write_manifest(scratch, _ready_data_factory_manifest())
        _write_quality_report(
            scratch,
            {
                "silver_storage_status": "SILVER_STORAGE_READY_COMPRESSED",
            },
        )
        (scratch / "compression_report.json").write_text(
            json.dumps(
                {
                    "raw_size_bytes": 100,
                    "silver_size_bytes": 150,
                    "gold_size_bytes": 10,
                    "silver_storage_format": "jsonl_gz",
                    "silver_storage_status": "SILVER_STORAGE_BLOAT_WARNING",
                    "silver_bloat_ratio": 1.5,
                }
            ),
            encoding="utf-8",
        )
        matrix = build_backtest_proof_matrix(output_root=scratch, run_id="df-test")
        assert matrix.silver_storage_status == "SILVER_STORAGE_BLOAT_WARNING"
        assert matrix.silver_bloat_ratio == 1.5
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_runtime_summary_flags_matrix_count_inflation_and_derives_candidate_semantics() -> None:
    scratch = _scratch_dir("runtime_count_semantics")
    try:
        run_dir = scratch / "backtest_strategy_ladder" / "run-count-semantics"
        (run_dir / "fast_candidates").mkdir(parents=True, exist_ok=True)
        candidate_rows = (
            {
                "candidate_id": "cand-a",
                "timestamp_ms": 1745884800000,
                "pair": "BTCUSDT",
                "timeframe": "5m",
                "engine_id": "engine_a",
                "strategy_id": "strategy_ladder",
                "candidate_source": "COMPAT_FEATURE_DISCOVERY",
            },
            {
                "candidate_id": "cand-b",
                "timestamp_ms": 1745884800000,
                "pair": "BTCUSDT",
                "timeframe": "5m",
                "engine_id": "engine_b",
                "strategy_id": "strategy_ladder",
                "candidate_source": "COMPAT_FEATURE_DISCOVERY",
            },
            {
                "candidate_id": "cand-c",
                "timestamp_ms": 1745885100000,
                "pair": "BTCUSDT",
                "timeframe": "5m",
                "engine_id": "engine_a",
                "strategy_id": "strategy_ladder",
                "candidate_source": "COMPAT_FEATURE_DISCOVERY",
            },
            {
                "candidate_id": "cand-d",
                "timestamp_ms": 1745885100000,
                "pair": "BTCUSDT",
                "timeframe": "5m",
                "engine_id": "engine_b",
                "strategy_id": "strategy_ladder",
                "candidate_source": "COMPAT_FEATURE_DISCOVERY",
            },
        )
        (run_dir / "fast_candidates" / "candidate_events.jsonl").write_text(
            "\n".join(json.dumps(row) for row in candidate_rows) + "\n",
            encoding="utf-8",
        )
        (run_dir / "fast_candidates" / "candidate_summary.json").write_text(
            json.dumps(
                {
                    "candidate_count": 4,
                    "unique_candidate_count": 4,
                    "base_event_count": 2,
                    "per_engine_candidate_count": 2,
                    "engine_native_candidate_count": 0,
                    "candidate_export_status": "CANDIDATE_EXPORT_READY",
                    "candidate_source_status": "CANDIDATE_SOURCE_COMPAT_PROXY_DISCOVERY",
                }
            ),
            encoding="utf-8",
        )
        (run_dir / "run_manifest.json").write_text(
            json.dumps(
                {
                    "run_id": "run-count-semantics",
                    "candidate_count": 4,
                    "unique_candidate_count": 4,
                    "base_event_count": 2,
                    "per_engine_candidate_count": 2,
                    "candidate_engine_native_count": 0,
                    "candidate_proxy_count": 4,
                    "candidate_source_status": "CANDIDATE_SOURCE_COMPAT_PROXY_DISCOVERY",
                    "candidate_export_status": "CANDIDATE_EXPORT_READY",
                    "engine_native_status": "ENGINE_NATIVE_FAILED_NO_RUNNER_INVOCATIONS",
                    "detailed_replay_count": 8,
                    "replay_record_count": 8,
                    "evaluation_record_count": 8,
                    "promotion_record_count": 8,
                    "capital_bucket_record_count": 8,
                    "capital_profile_count": 2,
                    "replay_expansion_axis": "capital_bucket",
                }
            ),
            encoding="utf-8",
        )
        (run_dir / "reports").mkdir(parents=True, exist_ok=True)
        (run_dir / "reports" / "pair_matrix.json").write_text(
            json.dumps(
                [
                    {
                        "pair": "BTCUSDT",
                        "candidate_count": 8,
                        "record_count": 8,
                    }
                ]
            ),
            encoding="utf-8",
        )
        (run_dir / "reports" / "engine_matrix.json").write_text(
            json.dumps(
                [
                    {
                        "engine_id": "engine_a",
                        "candidate_count": 4,
                        "record_count": 4,
                    },
                    {
                        "engine_id": "engine_b",
                        "candidate_count": 4,
                        "record_count": 4,
                    },
                ]
            ),
            encoding="utf-8",
        )

        summary = _enrich_strategy_ladder_summary_from_artifacts(
            StrategyLadderBacktestSummary(
                source_status="artifact",
                run_id="run-count-semantics",
                engine_native_status="ENGINE_NATIVE_FAILED_NO_RUNNER_INVOCATIONS",
            ),
            output_root=scratch,
            jobs=(),
            selected_candidate_id="",
        )

        assert summary.candidate_count == 4
        assert summary.unique_candidate_count == 4
        assert summary.base_event_count == 2
        assert summary.per_engine_candidate_count == 2
        assert summary.replay_record_count == 8
        assert summary.replay_expansion_factor == 2.0
        assert summary.replay_expansion_axis == "capital_bucket"
        assert summary.candidate_source_status == "CANDIDATE_SOURCE_COMPAT_PROXY_DISCOVERY"
        assert summary.candidate_truth_status == "CANDIDATE_TRUTH_PROXY_PRESENT"
        assert summary.matrix_count_inflation_status == "MATRIX_COUNT_INFLATION"
        assert "MATRIX_COUNT_INFLATION" in summary.count_semantics_validator_codes
        assert "SUMMARY_INCONSISTENT" not in summary.count_semantics_validator_codes
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_runtime_summary_keeps_detailed_replay_partial_when_raw_windows_are_partial() -> None:
    scratch = _scratch_dir("runtime_partial_raw_window_linkage")
    try:
        run_dir = scratch / "backtest_strategy_ladder" / "run-raw-window-partial"
        (run_dir / "detailed_replay").mkdir(parents=True, exist_ok=True)
        (run_dir / "detailed_replay" / "cand-1.json").write_text(
            json.dumps({"candidate_id": "cand-1", "bucket_results": []}),
            encoding="utf-8",
        )
        (run_dir / "detailed_replay" / "cand-2.json").write_text(
            json.dumps({"candidate_id": "cand-2", "bucket_results": []}),
            encoding="utf-8",
        )

        summary = _enrich_strategy_ladder_summary_from_artifacts(
            StrategyLadderBacktestSummary(
                source_status="artifact",
                run_id="run-raw-window-partial",
                candidate_count=2,
                raw_window_extraction_status="RAW_WINDOW_PARTIAL",
                detailed_replay_status="DETAILED_REPLAY_NOT_PROVEN",
            ),
            output_root=scratch,
            jobs=(),
            selected_candidate_id="",
        )

        assert summary.detailed_replay_count == 2
        assert summary.detailed_replay_status == "DETAILED_REPLAY_PARTIAL"
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_runtime_summary_surfaces_replay_performance_profile() -> None:
    scratch = _scratch_dir("runtime_replay_performance_profile")
    try:
        run_dir = scratch / "backtest_strategy_ladder" / "run-replay-performance"
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "replay_performance_profile.json").write_text(
            json.dumps(
                {
                    "run_id": "run-replay-performance",
                    "status": "REPLAY_PERFORMANCE_PROFILE_READY",
                    "total_wall_time_s": 120.0,
                    "total_cpu_time_s": 40.0,
                    "total_io_wait_estimate_s": 80.0,
                    "rows_processed": 24000,
                    "files_scanned": 64,
                    "candidate_count": 1000,
                    "replay_record_count": 4000,
                    "parquet_fast_path_status": "PARQUET_REPLAY_NOT_PROVEN",
                    "research_fast_debug_mode_status": (
                        "RESEARCH_FAST_DEBUG_MODE_NOT_REQUESTED"
                    ),
                    "replay_workers_used": 4,
                    "replay_parallelism_ratio": 0.75,
                    "replay_queue_wait_time_s": 1.25,
                    "bottleneck_summary": [
                        "replay_orchestration:70.0s",
                        "raw_window_extraction:25.0s",
                    ],
                    "indexed_lookup_metrics": {
                        "status": "INDEXED_WINDOW_LOOKUP_READY",
                        "indexed_lookup_hit_rate": 0.92,
                        "index_lookup_miss_count": 3,
                        "fallback_scan_count": 1,
                    },
                    "window_cache_metrics": {
                        "status": "WINDOW_CACHE_READY",
                        "cache_hit_count": 240,
                        "cache_miss_count": 60,
                        "cache_reuse_ratio": 0.8,
                    },
                    "phases": [
                        {
                            "phase_name": "raw_window_extraction",
                            "wall_time_s": 25.0,
                        },
                        {
                            "phase_name": "replay_orchestration",
                            "wall_time_s": 70.0,
                        },
                        {
                            "phase_name": "matrix_generation",
                            "wall_time_s": 10.0,
                        },
                        {
                            "phase_name": "dashboard_report_generation",
                            "wall_time_s": 5.0,
                        },
                    ],
                }
            ),
            encoding="utf-8",
        )

        summary = _enrich_strategy_ladder_summary_from_artifacts(
            StrategyLadderBacktestSummary(
                source_status="artifact",
                run_id="run-replay-performance",
            ),
            output_root=scratch,
            jobs=(),
            selected_candidate_id="",
        )

        assert summary.replay_performance_profile_status == (
            "REPLAY_PERFORMANCE_PROFILE_READY"
        )
        assert summary.replay_perf_total_wall_time_s == 120.0
        assert summary.replay_perf_rows_per_s == 200.0
        assert summary.replay_perf_records_per_s == round(4000 / 120.0, 6)
        assert summary.replay_perf_indexed_lookup_status == (
            "INDEXED_WINDOW_LOOKUP_READY"
        )
        assert summary.replay_perf_window_cache_status == "WINDOW_CACHE_READY"
        assert summary.replay_perf_raw_window_wall_time_s == 25.0
        assert summary.replay_perf_replay_wall_time_s == 70.0
        assert summary.replay_perf_bottleneck_summary == (
            "replay_orchestration:70.0s",
            "raw_window_extraction:25.0s",
        )
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_runtime_summary_prefers_b1_candidate_truth_for_b2_semantics() -> None:
    scratch = _scratch_dir("runtime_b1_candidate_truth")
    try:
        run_id = "strategy_ladder_workflow-demo"
        b1_run_dir = (
            scratch
            / "phase_b1_candidate_discovery"
            / "backtest_strategy_ladder"
            / run_id
        )
        b2_run_dir = (
            scratch
            / "phase_b2_detailed_replay"
            / "backtest_strategy_ladder"
            / run_id
        )
        (b1_run_dir / "fast_candidates").mkdir(parents=True, exist_ok=True)
        (b2_run_dir / "fast_candidates").mkdir(parents=True, exist_ok=True)
        b1_candidate_rows = (
            {
                "candidate_id": "cand-a",
                "timestamp_ms": 1745884800000,
                "pair": "BTCUSDT",
                "timeframe": "5m",
                "engine_id": "engine_a",
                "strategy_id": "strategy_ladder",
                "candidate_source": "COMPAT_FEATURE_DISCOVERY",
            },
            {
                "candidate_id": "cand-b",
                "timestamp_ms": 1745884800000,
                "pair": "BTCUSDT",
                "timeframe": "5m",
                "engine_id": "engine_b",
                "strategy_id": "strategy_ladder",
                "candidate_source": "COMPAT_FEATURE_DISCOVERY",
            },
        )
        b2_candidate_rows = (
            {
                "candidate_id": "cand-a",
                "timestamp_ms": 1745884800000,
                "pair": "BTCUSDT",
                "timeframe": "5m",
                "engine_id": "engine_a",
                "strategy_id": "strategy_ladder",
                "candidate_source": "ENGINE_NATIVE_UNAVAILABLE",
            },
            {
                "candidate_id": "cand-b",
                "timestamp_ms": 1745884800000,
                "pair": "BTCUSDT",
                "timeframe": "5m",
                "engine_id": "engine_b",
                "strategy_id": "strategy_ladder",
                "candidate_source": "ENGINE_NATIVE_UNAVAILABLE",
            },
        )
        (b1_run_dir / "fast_candidates" / "candidate_events.jsonl").write_text(
            "\n".join(json.dumps(row) for row in b1_candidate_rows) + "\n",
            encoding="utf-8",
        )
        (b2_run_dir / "fast_candidates" / "candidate_events.jsonl").write_text(
            "\n".join(json.dumps(row) for row in b2_candidate_rows) + "\n",
            encoding="utf-8",
        )
        (b1_run_dir / "fast_candidates" / "candidate_summary.json").write_text(
            json.dumps(
                {
                    "candidate_count": 2,
                    "unique_candidate_count": 2,
                    "base_event_count": 1,
                    "per_engine_candidate_count": 1,
                    "engine_native_candidate_count": 0,
                    "candidate_source_status": "CANDIDATE_SOURCE_COMPAT_PROXY_DISCOVERY",
                    "candidate_export_status": "CANDIDATE_EXPORT_READY",
                    "candidate_discovery_status": "CANDIDATE_DISCOVERY_SAMPLE_CAPPED",
                    "candidate_sample_cap": 400,
                    "effective_engine_native_sample_size": 100,
                    "engine_count": 4,
                    "candidate_cap_formula": "4 engines x 100",
                    "small_scope_enabled": False,
                    "full_scan_enabled": True,
                    "no_full_scan_enabled": False,
                    "candidate_discovery_limited": True,
                    "candidate_discovery_limit_reason": "ENGINE_NATIVE_SAMPLE_CAP_ACTIVE",
                    "candidate_discovery_mode": "FULL_DISCOVERY",
                    "candidate_discovery_cap_status": "CANDIDATE_DISCOVERY_SAMPLE_CAPPED",
                }
            ),
            encoding="utf-8",
        )
        (b2_run_dir / "fast_candidates" / "candidate_summary.json").write_text(
            json.dumps(
                {
                    "candidate_count": 2,
                    "candidate_export_status": "CANDIDATE_EXPORT_READY",
                    "candidate_discovery_status": "CANDIDATE_DISCOVERY_ENGINE_NATIVE_NOT_PROVEN",
                    "candidate_sample_cap": 0,
                    "effective_engine_native_sample_size": 10,
                    "engine_count": 4,
                    "candidate_discovery_mode": "SAMPLE_CAPPED_DEBUG",
                }
            ),
            encoding="utf-8",
        )
        (b2_run_dir / "run_manifest.json").write_text(
            json.dumps(
                {
                    "run_id": run_id,
                    "candidate_count": 2,
                    "detailed_replay_count": 8,
                    "replay_record_count": 8,
                    "capital_profile_count": 4,
                    "engine_native_status": "ENGINE_NATIVE_FAILED_NO_RUNNER_INVOCATIONS",
                }
            ),
            encoding="utf-8",
        )

        summary = _enrich_strategy_ladder_summary_from_artifacts(
            StrategyLadderBacktestSummary(
                source_status="artifact",
                run_id=run_id,
                engine_native_status="ENGINE_NATIVE_FAILED_NO_RUNNER_INVOCATIONS",
            ),
            output_root=scratch / "phase_b2_detailed_replay",
            jobs=(),
            selected_candidate_id="",
        )

        assert summary.base_event_count == 1
        assert summary.per_engine_candidate_count == 1
        assert summary.candidate_sample_cap == 400
        assert summary.effective_engine_native_sample_size == 100
        assert summary.candidate_discovery_mode == "FULL_DISCOVERY"
        assert summary.candidate_source_status == "CANDIDATE_SOURCE_FALLBACK_SYNTHETIC"
        assert summary.candidate_truth_status == "CANDIDATE_TRUTH_NOT_PROVEN"
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
