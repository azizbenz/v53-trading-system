from __future__ import annotations

import ast
from collections import Counter
import json
from datetime import UTC, datetime
import gzip
import inspect
from pathlib import Path
import shutil
from uuid import uuid4

import pytest

import local_replay_runtime.strategy_ladder_runner as strategy_ladder_runner_module
from local_replay_runtime.strategy_ladder_candidate_discovery import (
    apply_strategy_ladder_candidate_budget,
    discover_strategy_ladder_candidates,
)
from local_replay_runtime.strategy_ladder_complete_enabler_support import (
    apply_build14_shadow_context,
)
from local_replay_runtime.strategy_ladder_detailed_replay import (
    StrategyLadderDetailedReplayStageResult,
    load_strategy_ladder_detailed_replay_artifact,
    run_strategy_ladder_detailed_replay,
)
from local_replay_runtime.strategy_ladder_edge_model_provider import (
    EdgeEstimate,
    GovernedExpectedEdgeModelLoadResult,
)
from local_replay_runtime.strategy_ladder_economic_provenance import EconomicProvenance
from local_replay_runtime.strategy_ladder_engine_native_preselection import (
    StrategyLadderEngineNativePreselectionBuildResult,
)
from local_replay_runtime.strategy_ladder_feature_store import (
    load_strategy_ladder_feature_store,
    parse_time_boundary_to_ms,
)
from local_replay_runtime.strategy_ladder_models import (
    StrategyLadderBucketReplayResult,
    StrategyLadderCandidateEvent,
    StrategyLadderDetailedReplayArtifact,
    StrategyLadderFeatureRow,
    StrategyLadderRawWindowManifest,
    StrategyLadderReportSummary,
    StrategyLadderRequest,
    StrategyLadderRunManifest,
)
from local_replay_runtime.strategy_ladder_raw_window_extractor import (
    StrategyLadderRawWindowExtractionResult,
    extract_strategy_ladder_raw_windows,
)
from local_replay_runtime.strategy_ladder_window_cache import (
    StrategyLadderWindowCacheMetrics,
)
from local_replay_runtime.strategy_ladder_window_index import (
    StrategyLadderWindowLookupMetrics,
)
from local_replay_runtime.strategy_ladder_runner import (
    _count_executed_trades,
    _compute_statistical_validation_result,
    _build_report_summary,
    _promotion_fidelity_blockers,
    _stage_final_status,
    _build_engine_ab_direction_cost_diagnosis,
    _build_cost_parity,
    _build_engine_c_diagnosis,
    _build_engine_d_diagnosis,
    _build_engine_no_trade_diagnosis_payload,
    _build_profitability_truth_verdict,
    _materialize_native_candidate_event,
    _expected_edge_model_feature_maps,
    _expected_edge_model_reference_at,
    _effective_candidate_sample_cap,
    _candidate_sample_cap_total,
    _candidate_cap_formula,
    _engine_input_expected_gain_from_provenance,
    _engine_input_expected_gain_source_status,
    _blocker_assessment,
    _select_engine_specific_reason_counts,
    _summarize_raw_window_linkage,
    _resolve_run_raw_source_manifest_path,
    _persist_progress_run_manifest,
    _raw_window_refs_only_linkage_counts,
    _should_materialize_raw_windows,
    run_backtest_strategy_ladder,
)
from interface_contracts.strategy_ladder_workflow_support import (
    PHASE_B1,
    PHASE_B2,
    PHASE_STATUS_DISCOVERY_BLOCKED,
    PHASE_STATUS_PROOF_BLOCKED,
    ensure_workflow_manifest,
    read_workflow_manifest,
    upsert_workflow_phase,
)
from tests.support_paths import repo_build_path


def _scratch_dir(name: str) -> Path:
    return repo_build_path("strategy_ladder_runner_tests", f"{name}_{uuid4().hex}")


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(row) for row in rows) + ("\n" if rows else ""),
        encoding="utf-8",
    )


def _write_jsonl_gz(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row))
            handle.write("\n")


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _read_jsonl_any(path: Path) -> list[dict[str, object]]:
    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8-sig") as handle:
            return [json.loads(line) for line in handle if line.strip()]
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8-sig").splitlines()
        if line.strip()
    ]


def test_resolve_run_raw_source_manifest_path_falls_back_to_a2_manifest() -> None:
    scratch = _scratch_dir("resolve_raw_source_manifest_path")
    try:
        phase_a2_root = scratch / "phase_a2_data_factory"
        manifest_path = phase_a2_root / "raw_source_manifest.json"
        silver_index_path = phase_a2_root / "silver_index.json"
        _write_json(manifest_path, {"schema_version": "v1"})
        _write_json(
            phase_a2_root / "data_factory_manifest.json",
            {
                "schema_version": "v1",
                "raw_source_manifest_path": str(manifest_path.resolve()),
            },
        )
        _write_json(silver_index_path, {"schema_version": "v1", "entries": []})

        request = StrategyLadderRequest(
            run_id="run-raw-source-fallback",
            input_root=scratch,
            feature_store_root=scratch,
            raw_root=scratch,
            output_root=scratch / "output",
            pairs=("BTCUSDT",),
            engines=("engine_a",),
            timeframes=("5m",),
            start="2025-07-21",
            end="2025-07-22",
        )

        resolved = _resolve_run_raw_source_manifest_path(
            request=request,
            silver_index_path=silver_index_path,
            data_factory_base_root=phase_a2_root,
        )

        assert resolved == str(manifest_path.resolve())
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def _write_csv(path: Path, header: str, rows: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join([header, *rows]) + "\n", encoding="utf-8")


def _feature_row(
    *,
    pair: str = "BTCUSDT",
    engine_id: str = "engine_a",
    timestamp_ms: int = 1_714_000_000_000,
    timeframe: str = "5m",
    allocation_fraction: float | None = 0.2,
    min_notional: float | None = 50.0,
    fill_ratio: float = 1.0,
    book_depth_levels: int | None = 20,
    book_depth_source_status: str = "BOOK_DEPTH20_AVAILABLE",
    gross_return_bps: float = 40.0,
    expected_edge_bps: float = 20.0,
) -> dict[str, object]:
    return {
        "timestamp_ms": timestamp_ms,
        "pair": pair,
        "timeframe": timeframe,
        "engine_id": engine_id,
        "feature_values": {"edge_score": expected_edge_bps / 10.0},
        "feature_version": "fs.v1",
        "input_data_hash": f"hash-{pair}-{engine_id}",
        "method_version_hash": "method.v1",
        "source_ref": f"{pair}-{engine_id}.jsonl",
        "available_at_timestamp_ms": timestamp_ms,
        "raw_score": 0.72,
        "penalized_score": 0.71,
        "final_score": 0.70,
        "expected_edge_bps": expected_edge_bps,
        "spread_bps": 4.0,
        "slippage_bps": 3.0,
        "latency_penalty_bps": 1.0,
        "fill_ratio": fill_ratio,
        "book_depth_levels": book_depth_levels,
        "book_depth_source_status": book_depth_source_status,
        "book_depth_snapshot_count": 5,
        "book_depth_event_count": 5,
        "book_depth_missing_count": 0,
        "book_depth_staleness_status": book_depth_source_status,
        "candidate_size": 100.0,
        "final_size": 100.0,
        "gross_return_bps": gross_return_bps,
        "allocation_fraction": allocation_fraction,
        "min_notional": min_notional,
    }


def _book_depth20_row(timestamp_ms: int) -> dict[str, object]:
    bids = [[str(100.0 - index * 0.01), "10.0"] for index in range(20)]
    asks = [[str(100.1 + index * 0.01), "10.0"] for index in range(20)]
    return {
        "timestamp_ms": timestamp_ms,
        "pair": "BTCUSDT",
        "bids": bids,
        "asks": asks,
    }


def test_temporal_stratified_candidate_budget_covers_multiple_days() -> None:
    rows = tuple(
        StrategyLadderFeatureRow.model_validate(
            _feature_row(
                engine_id="engine_a",
                timestamp_ms=timestamp_ms,
            )
        )
        for timestamp_ms in (
            1_714_000_000_000,
            1_714_000_300_000,
            1_714_000_600_000,
            1_714_000_900_000,
            1_714_086_400_000,
            1_714_086_700_000,
            1_714_087_000_000,
            1_714_087_300_000,
        )
    )
    _, discovered = discover_strategy_ladder_candidates(
        run_id="run-temporal-stratified",
        rows=rows,
    )

    result = apply_strategy_ladder_candidate_budget(
        discovered,
        sample_cap_per_engine=2,
        candidate_discovery_mode="TEMPORAL_STRATIFIED",
    )

    assert result.limited is True
    assert len(result.candidates) == 2
    assert result.limit_reason == "TEMPORAL_STRATIFIED_SAMPLE_BUDGET_ACTIVE"
    assert result.temporal_bucket_granularity == "day"
    assert result.temporal_bucket_count_available == 2
    assert result.temporal_bucket_count_selected == 2
    assert result.temporal_bucket_coverage_ratio == pytest.approx(1.0)
    selected_days = {
        datetime.fromtimestamp(event.resolved_timestamp_ms / 1000.0, tz=UTC).date().isoformat()
        for event in result.candidates
    }
    assert len(selected_days) == 2


def test_temporal_stratified_candidate_budget_is_pair_engine_aware() -> None:
    rows = tuple(
        StrategyLadderFeatureRow.model_validate(
            _feature_row(
                pair=pair,
                engine_id="engine_a",
                timestamp_ms=1_714_000_000_000 + index * 60_000,
            )
        )
        for pair in ("BNBUSDT", "BTCUSDT")
        for index in range(3)
    )
    _, discovered = discover_strategy_ladder_candidates(
        run_id="run-temporal-pair-aware",
        rows=rows,
    )

    result = apply_strategy_ladder_candidate_budget(
        discovered,
        sample_cap_per_engine=1,
        candidate_discovery_mode="TEMPORAL_STRATIFIED",
    )

    assert result.limited is True
    assert len(result.candidates) == 2
    assert {event.pair for event in result.candidates} == {"BNBUSDT", "BTCUSDT"}


def test_full_discovery_explicit_zero_cap_is_uncapped() -> None:
    request = StrategyLadderRequest(
        run_id="full-discovery-uncapped",
        input_root=Path("input"),
        feature_store_root=Path("feature"),
        raw_root=Path("raw"),
        output_root=Path("output"),
        pairs=("BNBUSDT", "BTCUSDT"),
        engines=("engine_a", "engine_b", "engine_c", "engine_d"),
        candidate_discovery_mode="FULL_DISCOVERY",
        candidate_sample_cap=0,
        engine_native_sample_size=10,
        full_scan_enabled=True,
        small_scope_enabled=False,
    )

    effective_cap = _effective_candidate_sample_cap(request)

    assert effective_cap == 0
    assert (
        _candidate_sample_cap_total(
            effective_sample_cap=effective_cap,
            engine_count=4,
            pair_count=2,
            candidate_discovery_mode=request.candidate_discovery_mode,
        )
        == 0
    )
    assert (
        _candidate_cap_formula(
            effective_sample_cap=effective_cap,
            engine_count=4,
            pair_count=2,
            candidate_discovery_mode=request.candidate_discovery_mode,
        )
        == "uncapped"
    )


def test_refs_only_raw_window_mode_skips_b1_materialization() -> None:
    scratch = _scratch_dir("refs_only_raw_window_mode")
    try:
        request = StrategyLadderRequest(
            run_id="run-refs-only",
            input_root=scratch,
            feature_store_root=scratch,
            raw_root=scratch,
            output_root=scratch / "output",
            pairs=("BTCUSDT",),
            engines=("engine_a",),
            timeframes=("5m",),
            start="2025-07-21",
            end="2025-07-22",
            fast_only=True,
            engine_native_mode=True,
            raw_window_materialization_mode="refs-only",
        )
        candidate = StrategyLadderCandidateEvent(
            run_id="run-refs-only",
            candidate_id="cand-refs-only",
            timestamp_ms=1_714_000_000_000,
            pair="BTCUSDT",
            timeframe="5m",
            engine_id="engine_a",
            strategy_id="engine_a",
            candidate_source="COMPAT_FEATURE_DISCOVERY",
            input_data_hash="hash-cand",
            method_version_hash="method.v1",
        )

        assert request.raw_window_materialization_mode == "REFS_ONLY"
        assert not _should_materialize_raw_windows(
            request=request,
            candidate_events=(candidate,),
        )
        assert _raw_window_refs_only_linkage_counts((candidate,)) == {
            "raw_windows_total": 1,
            "trade_windows_found": 0,
            "trade_windows_missing": 0,
            "book_windows_found": 0,
            "book_windows_missing": 0,
            "ohlcv_windows_found": 0,
            "ohlcv_windows_missing": 0,
            "depth20_found": 0,
            "depth20_missing": 0,
        }
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_refs_only_raw_window_mode_persists_final_manifest() -> None:
    scratch = _scratch_dir("refs_only_raw_window_manifest")
    shutil.rmtree(scratch, ignore_errors=True)
    try:
        input_root = scratch / "input"
        feature_root = input_root / "feature_store"
        raw_root = input_root / "raw"
        (raw_root / "BTCUSDT").mkdir(parents=True, exist_ok=True)
        _write_json(
            input_root / "data_factory_manifest.json",
            {
                "data_factory_status": "DATA_FACTORY_READY",
                "raw_source_status": "RAW_SOURCE_READY",
                "pair_universe_status": "PAIR_UNIVERSE_READY",
                "silver_index_status": "SILVER_INDEX_READY",
                "gold_feature_store_status": "FEATURE_STORE_READY",
            },
        )
        _write_json(input_root / "raw_source_report.json", {"raw_source_status": "RAW_SOURCE_READY"})
        _write_json(
            input_root / "pair_universe_report.json",
            {
                "pair_universe_status": "PAIR_UNIVERSE_READY",
                "requested_pairs": ["BTCUSDT"],
                "available_pairs": ["BTCUSDT"],
                "missing_pairs": [],
            },
        )
        _write_json(
            input_root / "gold_feature_manifest.json",
            {
                "gold_feature_store_status": "FEATURE_STORE_READY",
                "feature_row_count": 1,
            },
        )
        _write_json(input_root / "silver_index.json", {"status": "SILVER_INDEX_READY"})
        _write_jsonl(feature_root / "features.jsonl", [_feature_row(pair="BTCUSDT")])

        result = run_backtest_strategy_ladder(
            StrategyLadderRequest(
                run_id="run-refs-only-final-manifest",
                input_root=input_root,
                feature_store_root=feature_root,
                raw_root=raw_root,
                output_root=scratch / "output",
                pairs=("BTCUSDT",),
                engines=("engine_a",),
                capital_buckets=(400,),
                timeframes=("5m",),
                fast_only=True,
                raw_window_materialization_mode="refs-only",
            )
        )

        run_dir = (
            scratch
            / "output"
            / "backtest_strategy_ladder"
            / "run-refs-only-final-manifest"
        )
        disk_manifest = json.loads(
            (run_dir / "run_manifest.json").read_text(encoding="utf-8")
        )
        disk_summary = json.loads(
            (run_dir / "reports" / "strategy_ladder_summary.json").read_text(
                encoding="utf-8"
            )
        )

        assert result.run_manifest.raw_window_extraction_status == "RAW_WINDOW_REFS_ONLY"
        assert result.run_manifest.raw_window_materialization_mode == "REFS_ONLY"
        assert result.report_summary.raw_window_materialization_mode == "REFS_ONLY"
        assert disk_manifest["raw_window_materialization_mode"] == "REFS_ONLY"
        assert disk_summary["raw_window_materialization_mode"] == "REFS_ONLY"
        tabular_manifest = json.loads(
            (
                run_dir
                / "fast_candidates"
                / "candidate_events.tabular_manifest.json"
            ).read_text(encoding="utf-8")
        )
        assert tabular_manifest["artifact_name"] == "candidate_events"
        assert tabular_manifest["audit_jsonl_preserved"] is True
        assert tabular_manifest["status"] in {
            "TABULAR_MIRROR_PARQUET_READY",
            "TABULAR_MIRROR_COLUMNAR_JSON_READY",
        }
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_b2_detailed_replay_keeps_raw_window_materialization_by_default() -> None:
    scratch = _scratch_dir("b2_materialize_default")
    try:
        request = StrategyLadderRequest(
            run_id="run-b2-materialize",
            input_root=scratch,
            feature_store_root=scratch,
            raw_root=scratch,
            output_root=scratch / "output",
            pairs=("BTCUSDT",),
            engines=("engine_a",),
            timeframes=("5m",),
            start="2025-07-21",
            end="2025-07-22",
            engine_native_mode=True,
        )
        candidate = StrategyLadderCandidateEvent(
            run_id="run-b2-materialize",
            candidate_id="cand-b2-materialize",
            timestamp_ms=1_714_000_000_000,
            pair="BTCUSDT",
            timeframe="5m",
            engine_id="engine_a",
            strategy_id="engine_a",
            candidate_source="COMPAT_FEATURE_DISCOVERY",
            input_data_hash="hash-cand",
            method_version_hash="method.v1",
        )

        assert request.raw_window_materialization_mode == "MATERIALIZE"
        assert _should_materialize_raw_windows(
            request=request,
            candidate_events=(candidate,),
        )
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_ml_off_expected_edge_proxy_is_readiness_blocker_not_hard_selection_blocker() -> None:
    candidate = StrategyLadderCandidateEvent(
        run_id="run-ml-off",
        candidate_id="cand-ml-off",
        timestamp_ms=1_714_000_000_000,
        pair="BTCUSDT",
        timeframe="5m",
        engine_id="engine_a",
        strategy_id="engine_a",
        candidate_source="COMPAT_FEATURE_DISCOVERY",
        input_data_hash="hash-cand",
        method_version_hash="method.v1",
    )
    provenance = EconomicProvenance(
        expected_edge_bps=0.0,
        expected_edge_provenance="PROXY_FORWARD_RETURN_MEDIAN_TO_CALIBRATE",
        spread_bps=1.0,
        spread_provenance="MEASURED_FROM_BOOK_RECONSTRUCTION",
        slippage_bps=1.0,
        slippage_provenance="MEASURED_FROM_DEPTH20_BOOK_WALK",
        latency_penalty_bps=0.0,
        latency_provenance="MEASURED_FROM_VENUE_MODEL",
        fee_bps=1.0,
        fee_provenance="MEASURED_FROM_VENUE_METADATA",
        measured_cost_governance={
            "cost_source_used_for_break_even": "measured",
            "expected_cost_truth_status": "FULLY_MEASURED_COST",
            "expected_cost_block_reason": "",
        },
    )

    materialized = _materialize_native_candidate_event(
        candidate=candidate,
        window=None,
        economic_provenance=provenance,
        builder_status="ENGINE_NATIVE_INPUT_BUILDER_FAILED_NO_RAW_WINDOW",
        builder_warnings=("RAW_WINDOW_NOT_AVAILABLE",),
        builder_provenance="ENGINE_NATIVE_INPUT_PROVENANCE_NOT_PROVEN",
        engine_output=None,
        engine_input_payload={},
        build14_application=None,
        records_built=0,
        runner_invoked=False,
        ml_mode="ML_MODE_OFF",
    )

    payload = dict(materialized.compatibility_payload or {})
    assert "EXPECTED_EDGE_PROXY_BLOCKED" not in payload["hard_block_reasons"]
    assert "EXPECTED_EDGE_PROXY_BLOCKED" in payload["profitability_blocker_reasons"]
    assert (
        payload["expected_edge_selection_gate_status"]
        == "EXPECTED_EDGE_SELECTION_GATE_DISABLED_IN_ML_OFF"
    )


def test_ml_off_uses_causal_edge_proxy_for_engine_input_only() -> None:
    provenance = EconomicProvenance(
        expected_edge_bps=12.5,
        expected_edge_provenance="PROXY_FORWARD_RETURN_MEDIAN_TO_CALIBRATE",
        spread_bps=1.0,
        spread_provenance="MEASURED_FROM_BOOK_RECONSTRUCTION",
        slippage_bps=1.0,
        slippage_provenance="MEASURED_FROM_DEPTH20_BOOK_WALK",
        latency_penalty_bps=0.0,
        latency_provenance="MEASURED_FROM_VENUE_MODEL",
        fee_bps=1.0,
        fee_provenance="MEASURED_FROM_VENUE_METADATA",
    )

    assert _engine_input_expected_gain_from_provenance(
        provenance,
        ml_mode="ML_MODE_OFF",
    ) == pytest.approx(0.00125)
    assert _engine_input_expected_gain_source_status(
        provenance,
        ml_mode="ML_MODE_OFF",
    ) == "ENGINE_INPUT_EDGE_CAUSAL_PROXY_DIAGNOSTIC_ML_OFF"


def test_overlay_zeroes_non_governed_engine_input_edge() -> None:
    provenance = EconomicProvenance(
        expected_edge_bps=12.5,
        expected_edge_provenance="PROXY_FORWARD_RETURN_MEDIAN_TO_CALIBRATE",
        spread_bps=1.0,
        spread_provenance="MEASURED_FROM_BOOK_RECONSTRUCTION",
        slippage_bps=1.0,
        slippage_provenance="MEASURED_FROM_DEPTH20_BOOK_WALK",
        latency_penalty_bps=0.0,
        latency_provenance="MEASURED_FROM_VENUE_MODEL",
        fee_bps=1.0,
        fee_provenance="MEASURED_FROM_VENUE_METADATA",
    )

    assert _engine_input_expected_gain_from_provenance(
        provenance,
        ml_mode="ML_MODE_OVERLAY_FROZEN",
    ) == 0.0
    assert _engine_input_expected_gain_source_status(
        provenance,
        ml_mode="ML_MODE_OVERLAY_FROZEN",
    ) == "ENGINE_INPUT_EDGE_ZEROED_EXPECTED_EDGE_NOT_GOVERNED"


def test_count_executed_trades_accepts_lowercase_replay_states() -> None:
    rows = (
        StrategyLadderBucketReplayResult(
            candidate_id="c1",
            pair="BTCUSDT",
            engine_id="engine_a",
            strategy_id="engine_a",
            capital_bucket=400,
            timestamp_ms=1,
            execution_state="executed",
            executed_notional=100.0,
        ),
        StrategyLadderBucketReplayResult(
            candidate_id="c2",
            pair="BTCUSDT",
            engine_id="engine_a",
            strategy_id="engine_a",
            capital_bucket=400,
            timestamp_ms=2,
            execution_state="reduced",
            reduced_notional=50.0,
        ),
        StrategyLadderBucketReplayResult(
            candidate_id="c3",
            pair="BTCUSDT",
            engine_id="engine_a",
            strategy_id="engine_a",
            capital_bucket=400,
            timestamp_ms=3,
            execution_state="no_fill",
        ),
    )

    assert _count_executed_trades(rows) == 2


def test_compute_statistical_validation_result_uses_proven_executed_returns() -> None:
    request = StrategyLadderRequest(
        run_id="stat-validation",
        input_root=Path("input"),
        feature_store_root=Path("feature"),
        raw_root=Path("raw"),
        output_root=Path("output"),
        timeframes=("5m",),
    )
    rows = (
        StrategyLadderBucketReplayResult(
            candidate_id="c1",
            pair="BTCUSDT",
            engine_id="engine_a",
            strategy_id="engine_a.long",
            capital_bucket=400,
            timestamp_ms=1,
            execution_state="executed",
            executed_notional=100.0,
            executed_only_net_return=0.010,
            executed_only_net_return_status="EXECUTED_NET_RETURN_PROVEN",
        ),
        StrategyLadderBucketReplayResult(
            candidate_id="c2",
            pair="BTCUSDT",
            engine_id="engine_a",
            strategy_id="engine_a.long",
            capital_bucket=400,
            timestamp_ms=2,
            execution_state="executed",
            executed_notional=100.0,
            executed_only_net_return=0.020,
            executed_only_net_return_status="EXECUTED_NET_RETURN_PROVEN",
        ),
    )

    result = _compute_statistical_validation_result(
        request=request,
        bucket_results=rows,
    )

    assert result.status == "STATISTICAL_VALIDATION_INSUFFICIENT_EXECUTIONS"
    assert result.observation_count == 2
    assert result.blocker_codes == ("STATISTICAL_VALIDATION_INSUFFICIENT_EXECUTIONS",)


def test_compute_statistical_validation_result_emits_psr_and_dsr() -> None:
    request = StrategyLadderRequest(
        run_id="stat-validation-ready",
        input_root=Path("input"),
        feature_store_root=Path("feature"),
        raw_root=Path("raw"),
        output_root=Path("output"),
        timeframes=("5m",),
    )
    rows = tuple(
        StrategyLadderBucketReplayResult(
            candidate_id=f"c{index}",
            pair="BTCUSDT",
            engine_id="engine_a",
            strategy_id="engine_a.long",
            capital_bucket=400,
            timestamp_ms=index,
            execution_state="executed",
            executed_notional=100.0,
            executed_only_net_return=net_return,
            executed_only_net_return_status="EXECUTED_NET_RETURN_PROVEN",
        )
        for index, net_return in enumerate((0.010, 0.018, 0.014, 0.021, 0.017), start=1)
    )

    result = _compute_statistical_validation_result(
        request=request,
        bucket_results=rows,
    )

    assert result.status == "STATISTICAL_VALIDATION_READY"
    assert result.observation_count == 5
    assert result.trial_count == 1
    assert result.stationary_block_length >= 1
    assert result.effective_sample_size is not None
    assert result.min_trl_required is not None
    assert result.min_trl_satisfied is True
    assert result.sample_sharpe is not None
    assert result.psr is not None and result.psr >= 0.95
    assert result.dsr is not None and result.dsr >= 0.95
    assert result.blocker_codes == ()


def test_build_report_summary_carries_statistical_validation_fields() -> None:
    request = StrategyLadderRequest(
        run_id="stat-summary",
        input_root=Path("input"),
        feature_store_root=Path("feature"),
        raw_root=Path("raw"),
        output_root=Path("output"),
    )
    run_manifest = StrategyLadderRunManifest(
        run_id="stat-summary",
        statistical_validation_status="STATISTICAL_VALIDATION_READY",
        statistical_validation_observation_count=7,
        statistical_validation_trial_count=3,
        statistical_validation_benchmark_sharpe=0.0,
        statistical_validation_acceptance_floor=0.95,
        statistical_validation_sample_sharpe=1.23,
        statistical_validation_psr=0.98,
        statistical_validation_dsr=0.96,
        statistical_validation_stationary_block_length=2,
        statistical_validation_effective_sample_size=5.0,
        statistical_validation_min_trl_required=4.1,
        statistical_validation_min_trl_satisfied=True,
        statistical_validation_psr_passes_floor=True,
        statistical_validation_dsr_passes_floor=True,
        statistical_validation_blocker_codes=(),
        executed_trade_count=7,
    )

    summary = _build_report_summary(
        request=request,
        run_manifest=run_manifest,
        capital_profiles=(),
        engine_artifacts=(),
        pair_artifacts=(),
        strategy_artifacts=(),
        sample_artifacts=(),
        bucket_results=(),
        evidence_projection={},
    )

    assert summary.executed_trade_count == 7
    assert summary.statistical_validation_status == "STATISTICAL_VALIDATION_READY"
    assert summary.statistical_validation_observation_count == 7
    assert summary.statistical_validation_trial_count == 3
    assert summary.statistical_validation_psr == pytest.approx(0.98)
    assert summary.statistical_validation_dsr == pytest.approx(0.96)
    assert summary.statistical_validation_stationary_block_length == 2
    assert summary.statistical_validation_effective_sample_size == pytest.approx(5.0)
    assert summary.statistical_validation_min_trl_required == pytest.approx(4.1)
    assert summary.statistical_validation_min_trl_satisfied is True


def test_compute_statistical_validation_result_blocks_when_min_trl_not_satisfied(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        strategy_ladder_runner_module,
        "infer_stationary_block_length",
        lambda _values: 12,
    )
    request = StrategyLadderRequest(
        run_id="stat-validation-mintrl",
        input_root=Path("input"),
        feature_store_root=Path("feature"),
        raw_root=Path("raw"),
        output_root=Path("output"),
        timeframes=("5m",),
    )
    rows = tuple(
        StrategyLadderBucketReplayResult(
            candidate_id=f"c{index}",
            pair="BTCUSDT",
            engine_id="engine_a",
            strategy_id="engine_a.long",
            capital_bucket=400,
            timestamp_ms=index,
            execution_state="executed",
            executed_notional=100.0,
            executed_only_net_return=net_return,
            executed_only_net_return_status="EXECUTED_NET_RETURN_PROVEN",
        )
        for index, net_return in enumerate((0.010, 0.018, 0.014, 0.021, 0.017), start=1)
    )

    result = _compute_statistical_validation_result(
        request=request,
        bucket_results=rows,
    )

    assert result.status == "STATISTICAL_VALIDATION_MINTRL_NOT_SATISFIED"
    assert result.effective_sample_size == pytest.approx(5.0 / 12.0)
    assert result.min_trl_required is not None
    assert result.min_trl_satisfied is False
    assert "STATISTICAL_VALIDATION_MINTRL_NOT_SATISFIED" in result.blocker_codes


def test_promotion_fidelity_blockers_include_statistical_validation_failures() -> None:
    blockers = _promotion_fidelity_blockers(
        candidate_truth_status="CANDIDATE_ENGINE_NATIVE_READY",
        expected_edge_truth_status="EXPECTED_EDGE_GOVERNED_BACKTEST_TRUTH",
        economic_constants_provenance="FULLY_MEASURED",
        execution_fidelity_gap_codes=(),
        statistical_validation_status="STATISTICAL_VALIDATION_BELOW_FLOOR",
        statistical_validation_blocker_codes=("STATISTICAL_VALIDATION_PSR_BELOW_FLOOR",),
    )

    assert "STATISTICAL_VALIDATION_BELOW_FLOOR" in blockers
    assert "STATISTICAL_VALIDATION_PSR_BELOW_FLOOR" in blockers


def test_stage_final_status_blocks_when_statistical_validation_is_not_ready() -> None:
    request = StrategyLadderRequest(
        run_id="stat-final-status",
        input_root=Path("input"),
        feature_store_root=Path("feature"),
        raw_root=Path("raw"),
        output_root=Path("output"),
    )

    status = _stage_final_status(
        request=request,
        feature_store_status="FEATURE_STORE_READY",
        candidate_export_status="CANDIDATE_EXPORT_READY",
        raw_window_status="RAW_WINDOW_READY",
        detailed_replay_status="DETAILED_REPLAY_READY",
        capital_profile_count=1,
        promotion_artifact_count=3,
        executed_trade_count=5,
        detailed_replay_record_count=10,
        statistical_validation_status="STATISTICAL_VALIDATION_BELOW_FLOOR",
    )

    assert status == "STRATEGY_LADDER_BLOCKED_BY_STATISTICAL_VALIDATION"


def test_expected_edge_model_feature_maps_promote_microstructure_payload_fields() -> None:
    discovery_status, candidate_events = discover_strategy_ladder_candidates(
        run_id="fixture-run",
        rows=(StrategyLadderFeatureRow.model_validate(_feature_row()),),
    )

    assert discovery_status == "CANDIDATE_DISCOVERY_READY"
    assert len(candidate_events) == 1

    feature_values, route_features = _expected_edge_model_feature_maps(candidate_events[0])

    assert feature_values["spread_bps"] == 4.0
    assert feature_values["slippage_bps"] == 3.0
    assert feature_values["book_depth_levels"] == 20
    assert route_features["route_spread_bps"] == 4.0
    assert route_features["route_slippage_bps"] == 3.0


def test_expected_edge_model_feature_maps_promote_f16_augmented_payload_fields() -> None:
    candidate = StrategyLadderCandidateEvent(
        run_id="fixture-run-f16",
        candidate_id="cand-f16",
        timestamp_ms=1_714_000_000_000,
        pair="BTCUSDT",
        timeframe="5m",
        engine_id="engine_d",
        strategy_id="engine_d",
        compatibility_payload={
            "feature_values": {"edge_score": 2.0},
            "kyle_lambda": 0.0023,
            "realized_vol_current": 0.013,
            "realized_vol_at_break": 0.021,
            "micro_edge_exit_governor_observed": 0.44,
            "micro_edge_entry_timing_observed": 0.57,
            "history_score": 0.61,
            "marginal_value_score": 0.64,
            "reentry_lateness": 0.15,
            "concentration_headroom": 0.22,
            "anti_revenge_state__active": False,
            "anti_revenge_state__cooling": True,
            "anti_revenge_state__idle": False,
        },
    )

    feature_values, _route_features = _expected_edge_model_feature_maps(candidate)

    assert feature_values["kyle_lambda"] == 0.0023
    assert feature_values["realized_vol_current"] == 0.013
    assert feature_values["realized_vol_at_break"] == 0.021
    assert feature_values["micro_edge_exit_governor_observed"] == 0.44
    assert feature_values["micro_edge_entry_timing_observed"] == 0.57
    assert feature_values["history_score"] == 0.61
    assert feature_values["marginal_value_score"] == 0.64
    assert feature_values["reentry_lateness"] == 0.15
    assert feature_values["concentration_headroom"] == 0.22
    assert feature_values["anti_revenge_state__active"] is False
    assert feature_values["anti_revenge_state__cooling"] is True
    assert feature_values["anti_revenge_state__idle"] is False


def test_feature_store_loader_supports_jsonl_and_rejects_future_leak() -> None:
    scratch = _scratch_dir("feature_store_loader")
    shutil.rmtree(scratch, ignore_errors=True)
    try:
        feature_root = scratch / "feature_store"
        _write_jsonl(
            feature_root / "features.jsonl",
            [
                _feature_row(pair="BTCUSDT"),
                {
                    **_feature_row(pair="ETHUSDT", timestamp_ms=1_714_000_060_000),
                    "available_at_timestamp_ms": 1_714_000_120_000,
                },
            ],
        )

        result = load_strategy_ladder_feature_store(feature_root)

        assert result.feature_store_status == "FEATURE_STORE_PARTIAL"
        assert result.row_count == 1
        assert result.rejected_future_leak_count == 1
        assert result.rows[0].pair == "BTCUSDT"
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_feature_store_date_only_end_boundary_includes_full_day() -> None:
    scratch = _scratch_dir("feature_store_date_end_boundary")
    shutil.rmtree(scratch, ignore_errors=True)
    try:
        feature_root = scratch / "feature_store"
        noon_utc = 1746100800000
        _write_jsonl(feature_root / "features.jsonl", [_feature_row(timestamp_ms=noon_utc)])

        result = load_strategy_ladder_feature_store(
            feature_root,
            start_ms=parse_time_boundary_to_ms("2025-05-01"),
            end_ms=parse_time_boundary_to_ms("2025-05-01", end_of_day=True),
        )

        assert result.row_count == 1
        assert result.rows[0].resolved_timestamp_ms == noon_utc
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_strategy_ladder_runner_preselected_only_replays_only_b15_subset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scratch = _scratch_dir("engine_native_preselected_only")
    shutil.rmtree(scratch, ignore_errors=True)
    try:
        input_root = scratch / "input"
        feature_root = input_root / "feature_store"
        raw_root = input_root / "raw"
        (raw_root / "BTCUSDT").mkdir(parents=True, exist_ok=True)
        _write_json(
            input_root / "data_factory_manifest.json",
            {
                "data_factory_status": "DATA_FACTORY_READY",
                "raw_source_status": "RAW_SOURCE_READY",
                "pair_universe_status": "PAIR_UNIVERSE_READY",
                "silver_index_status": "SILVER_INDEX_READY",
                "gold_feature_store_status": "FEATURE_STORE_READY",
            },
        )
        _write_json(
            input_root / "raw_source_report.json",
            {"raw_source_status": "RAW_SOURCE_READY"},
        )
        _write_json(
            input_root / "pair_universe_report.json",
            {
                "pair_universe_status": "PAIR_UNIVERSE_READY",
                "requested_pairs": ["BTCUSDT"],
                "available_pairs": ["BTCUSDT"],
                "missing_pairs": [],
            },
        )
        _write_json(
            input_root / "gold_feature_manifest.json",
            {
                "gold_feature_store_status": "FEATURE_STORE_READY",
                "feature_row_count": 2,
            },
        )
        _write_json(input_root / "silver_index.json", {"status": "SILVER_INDEX_READY"})
        _write_jsonl(
            feature_root / "features.jsonl",
            [
                _feature_row(
                    pair="BTCUSDT",
                    engine_id="engine_a",
                    timestamp_ms=1_714_000_000_000,
                ),
                _feature_row(
                    pair="BTCUSDT",
                    engine_id="engine_a",
                    timestamp_ms=1_714_000_060_000,
                ),
            ],
        )

        def _fake_extract(output_dir, *, candidate_events, **kwargs):
            manifests = tuple(
                StrategyLadderRawWindowManifest(
                    candidate_id=event.candidate_id,
                    pair=event.pair,
                    engine_id=event.engine_id,
                    timestamp_ms=event.resolved_timestamp_ms,
                    window_start_ms=event.resolved_timestamp_ms - 60_000,
                    window_end_ms=event.resolved_timestamp_ms + 60_000,
                    window_extraction_status="RAW_WINDOW_READY",
                    source_coverage_status="RAW_WINDOW_SOURCE_READY",
                )
                for event in candidate_events
            )
            return StrategyLadderRawWindowExtractionResult(
                status="RAW_WINDOW_READY",
                manifests=manifests,
                indexed_lookup_metrics=StrategyLadderWindowLookupMetrics(
                    status="INDEXED_WINDOW_LOOKUP_READY"
                ),
                window_cache_metrics=StrategyLadderWindowCacheMetrics(
                    status="WINDOW_CACHE_READY"
                ),
            )

        def _fake_materialize(*, candidate_events, **kwargs):
            materialized_events = []
            for index, event in enumerate(candidate_events):
                reason_codes = (
                    ("engine_internal.engine_a.direction.non_long",)
                    if index == 0
                    else ("EXPECTED_EDGE_PROXY_BLOCKED",)
                )
                materialized_events.append(
                    event.model_copy(
                        update={
                            "candidate_source": "ENGINE_NATIVE",
                            "compatibility_payload": {
                                "candidate_source": "ENGINE_NATIVE",
                                "engine_native_decision": "no_trade",
                                "engine_native_reason_codes": reason_codes,
                            },
                        }
                    )
                )
            return strategy_ladder_runner_module._EngineNativeCandidateMaterialization(
                candidate_events=tuple(materialized_events),
                candidate_discovery_status="CANDIDATE_DISCOVERY_ENGINE_NATIVE_READY",
                engine_native_status="ENGINE_NATIVE_FULL_PATH_READY",
                engine_native_records_built=2,
                engine_native_runner_invocation_count=2,
                expected_edge_proxy_count=2,
                expected_edge_governed_count=0,
            )

        captured: dict[str, tuple[str, ...]] = {}

        def _fake_detailed_replay(output_dir, *, candidate_events, capital_buckets, **kwargs):
            captured["candidate_ids"] = tuple(
                event.candidate_id for event in candidate_events
            )
            return StrategyLadderDetailedReplayStageResult(
                detailed_replay_status="DETAILED_REPLAY_READY",
                candidate_artifacts=(),
                bucket_results_by_bucket={bucket: () for bucket in capital_buckets},
                bucket_dtr_records={bucket: () for bucket in capital_buckets},
            )

        monkeypatch.setattr(
            "local_replay_runtime.strategy_ladder_runner.extract_strategy_ladder_raw_windows",
            _fake_extract,
        )
        monkeypatch.setattr(
            "local_replay_runtime.strategy_ladder_runner._materialize_engine_native_candidates",
            _fake_materialize,
        )
        monkeypatch.setattr(
            "local_replay_runtime.strategy_ladder_runner.run_strategy_ladder_detailed_replay",
            _fake_detailed_replay,
        )

        result = run_backtest_strategy_ladder(
            StrategyLadderRequest(
                run_id="run-preselected-only",
                input_root=input_root,
                feature_store_root=feature_root,
                raw_root=raw_root,
                output_root=scratch / "output",
                pairs=("BTCUSDT",),
                engines=("engine_a",),
                capital_buckets=(400,),
                engine_native_mode=True,
                preselected_only=True,
            )
        )

        run_dir = scratch / "output" / "backtest_strategy_ladder" / "run-preselected-only"
        preselected_rows = [
            json.loads(line)
            for line in (run_dir / "preselection_candidates.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
            if line
        ]
        assert result.run_manifest.preselection_status == "ENGINE_NATIVE_PRESELECTION_READY"
        assert result.run_manifest.replay_input_mode_status == "PRESELECTED_ONLY"
        assert result.run_manifest.b1_5_policy_mode == "conservative_hard_only"
        assert result.run_manifest.discovery_pre_candidate_count == 2
        assert result.run_manifest.engine_native_preselected_count == 1
        assert result.run_manifest.preselection_hard_rejected_count == 1
        assert result.run_manifest.preselection_soft_flagged_count == 1
        assert result.run_manifest.preselection_passed_count == 1
        assert result.run_manifest.b2_replay_candidate_count == 1
        assert result.run_manifest.preselection_rejection_count == 1
        assert result.run_manifest.replay_savings_estimate_count == 1
        assert result.run_manifest.executed_trade_count == 0
        assert len(preselected_rows) == 1
        assert captured["candidate_ids"] == (preselected_rows[0]["candidate_id"],)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_strategy_ladder_runner_diagnostic_full_replay_preserves_full_b1_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scratch = _scratch_dir("engine_native_diagnostic_full_replay")
    shutil.rmtree(scratch, ignore_errors=True)
    try:
        input_root = scratch / "input"
        feature_root = input_root / "feature_store"
        raw_root = input_root / "raw"
        (raw_root / "BTCUSDT").mkdir(parents=True, exist_ok=True)
        _write_json(
            input_root / "data_factory_manifest.json",
            {
                "data_factory_status": "DATA_FACTORY_READY",
                "raw_source_status": "RAW_SOURCE_READY",
                "pair_universe_status": "PAIR_UNIVERSE_READY",
                "silver_index_status": "SILVER_INDEX_READY",
                "gold_feature_store_status": "FEATURE_STORE_READY",
            },
        )
        _write_json(
            input_root / "raw_source_report.json",
            {"raw_source_status": "RAW_SOURCE_READY"},
        )
        _write_json(
            input_root / "pair_universe_report.json",
            {
                "pair_universe_status": "PAIR_UNIVERSE_READY",
                "requested_pairs": ["BTCUSDT"],
                "available_pairs": ["BTCUSDT"],
                "missing_pairs": [],
            },
        )
        _write_json(
            input_root / "gold_feature_manifest.json",
            {
                "gold_feature_store_status": "FEATURE_STORE_READY",
                "feature_row_count": 2,
            },
        )
        _write_json(input_root / "silver_index.json", {"status": "SILVER_INDEX_READY"})
        _write_jsonl(
            feature_root / "features.jsonl",
            [
                _feature_row(
                    pair="BTCUSDT",
                    engine_id="engine_a",
                    timestamp_ms=1_714_000_000_000,
                ),
                _feature_row(
                    pair="BTCUSDT",
                    engine_id="engine_a",
                    timestamp_ms=1_714_000_060_000,
                ),
            ],
        )

        def _fake_extract(output_dir, *, candidate_events, **kwargs):
            manifests = tuple(
                StrategyLadderRawWindowManifest(
                    candidate_id=event.candidate_id,
                    pair=event.pair,
                    engine_id=event.engine_id,
                    timestamp_ms=event.resolved_timestamp_ms,
                    window_start_ms=event.resolved_timestamp_ms - 60_000,
                    window_end_ms=event.resolved_timestamp_ms + 60_000,
                    window_extraction_status="RAW_WINDOW_READY",
                    source_coverage_status="RAW_WINDOW_SOURCE_READY",
                )
                for event in candidate_events
            )
            return StrategyLadderRawWindowExtractionResult(
                status="RAW_WINDOW_READY",
                manifests=manifests,
                indexed_lookup_metrics=StrategyLadderWindowLookupMetrics(
                    status="INDEXED_WINDOW_LOOKUP_READY"
                ),
                window_cache_metrics=StrategyLadderWindowCacheMetrics(
                    status="WINDOW_CACHE_READY"
                ),
            )

        def _fake_materialize(*, candidate_events, **kwargs):
            materialized_events = tuple(
                event.model_copy(
                    update={
                        "candidate_source": "ENGINE_NATIVE",
                        "compatibility_payload": {
                            "candidate_source": "ENGINE_NATIVE",
                            "engine_native_decision": "no_trade",
                            "engine_native_reason_codes": (
                                ("engine_internal.engine_a.direction.non_long",)
                                if index == 0
                                else ("EXPECTED_EDGE_PROXY_BLOCKED",)
                            ),
                        },
                    }
                )
                for index, event in enumerate(candidate_events)
            )
            return strategy_ladder_runner_module._EngineNativeCandidateMaterialization(
                candidate_events=materialized_events,
                candidate_discovery_status="CANDIDATE_DISCOVERY_ENGINE_NATIVE_READY",
                engine_native_status="ENGINE_NATIVE_FULL_PATH_READY",
                engine_native_records_built=2,
                engine_native_runner_invocation_count=2,
                expected_edge_proxy_count=2,
                expected_edge_governed_count=0,
            )

        captured: dict[str, tuple[str, ...]] = {}

        def _fake_detailed_replay(output_dir, *, candidate_events, capital_buckets, **kwargs):
            captured["candidate_ids"] = tuple(
                event.candidate_id for event in candidate_events
            )
            return StrategyLadderDetailedReplayStageResult(
                detailed_replay_status="DETAILED_REPLAY_READY",
                candidate_artifacts=(),
                bucket_results_by_bucket={bucket: () for bucket in capital_buckets},
                bucket_dtr_records={bucket: () for bucket in capital_buckets},
            )

        monkeypatch.setattr(
            "local_replay_runtime.strategy_ladder_runner.extract_strategy_ladder_raw_windows",
            _fake_extract,
        )
        monkeypatch.setattr(
            "local_replay_runtime.strategy_ladder_runner._materialize_engine_native_candidates",
            _fake_materialize,
        )
        monkeypatch.setattr(
            "local_replay_runtime.strategy_ladder_runner.run_strategy_ladder_detailed_replay",
            _fake_detailed_replay,
        )

        result = run_backtest_strategy_ladder(
            StrategyLadderRequest(
                run_id="run-diagnostic-full-replay",
                input_root=input_root,
                feature_store_root=feature_root,
                raw_root=raw_root,
                output_root=scratch / "output",
                pairs=("BTCUSDT",),
                engines=("engine_a",),
                capital_buckets=(400,),
                engine_native_mode=True,
                preselected_only=False,
                diagnostic_full_replay=True,
            )
        )

        run_dir = (
            scratch / "output" / "backtest_strategy_ladder" / "run-diagnostic-full-replay"
        )
        preselected_rows = [
            json.loads(line)
            for line in (run_dir / "preselection_candidates.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
            if line
        ]
        assert result.run_manifest.replay_input_mode_status == "DIAGNOSTIC_FULL_REPLAY"
        assert result.run_manifest.preselected_only is False
        assert result.run_manifest.diagnostic_full_replay is True
        assert result.run_manifest.b1_5_policy_mode == "diagnostic_full_replay"
        assert result.run_manifest.discovery_pre_candidate_count == 2
        assert result.run_manifest.engine_native_preselected_count == 1
        assert result.run_manifest.preselection_hard_rejected_count == 1
        assert result.run_manifest.preselection_soft_flagged_count == 1
        assert result.run_manifest.preselection_passed_count == 1
        assert result.run_manifest.b2_replay_candidate_count == 2
        assert result.run_manifest.preselection_rejection_count == 0
        assert result.run_manifest.executed_trade_count == 0
        assert len(preselected_rows) == 1
        assert len(captured["candidate_ids"]) == 2
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_strategy_ladder_runner_empty_preselection_preserves_engine_native_truth(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scratch = _scratch_dir("engine_native_preselection_empty_truth")
    shutil.rmtree(scratch, ignore_errors=True)
    try:
        input_root = scratch / "input"
        feature_root = input_root / "feature_store"
        raw_root = input_root / "raw"
        (raw_root / "BTCUSDT").mkdir(parents=True, exist_ok=True)
        _write_json(
            input_root / "data_factory_manifest.json",
            {
                "data_factory_status": "DATA_FACTORY_READY",
                "raw_source_status": "RAW_SOURCE_READY",
                "pair_universe_status": "PAIR_UNIVERSE_READY",
                "silver_index_status": "SILVER_INDEX_READY",
                "gold_feature_store_status": "FEATURE_STORE_READY",
            },
        )
        _write_json(
            input_root / "raw_source_report.json",
            {"raw_source_status": "RAW_SOURCE_READY"},
        )
        _write_json(
            input_root / "pair_universe_report.json",
            {
                "pair_universe_status": "PAIR_UNIVERSE_READY",
                "requested_pairs": ["BTCUSDT"],
                "available_pairs": ["BTCUSDT"],
                "missing_pairs": [],
            },
        )
        _write_json(
            input_root / "gold_feature_manifest.json",
            {
                "gold_feature_store_status": "FEATURE_STORE_READY",
                "feature_row_count": 2,
            },
        )
        _write_json(input_root / "silver_index.json", {"status": "SILVER_INDEX_READY"})
        _write_jsonl(
            feature_root / "features.jsonl",
            [
                _feature_row(
                    pair="BTCUSDT",
                    engine_id="engine_a",
                    timestamp_ms=1_714_000_000_000,
                ),
                _feature_row(
                    pair="BTCUSDT",
                    engine_id="engine_b",
                    timestamp_ms=1_714_000_060_000,
                ),
            ],
        )

        def _fake_extract(output_dir, *, candidate_events, **kwargs):
            manifests = tuple(
                StrategyLadderRawWindowManifest(
                    candidate_id=event.candidate_id,
                    pair=event.pair,
                    engine_id=event.engine_id,
                    timestamp_ms=event.resolved_timestamp_ms,
                    window_start_ms=event.resolved_timestamp_ms - 60_000,
                    window_end_ms=event.resolved_timestamp_ms + 60_000,
                    window_extraction_status="RAW_WINDOW_READY",
                    source_coverage_status="RAW_WINDOW_SOURCE_READY",
                )
                for event in candidate_events
            )
            return StrategyLadderRawWindowExtractionResult(
                status="RAW_WINDOW_READY",
                manifests=manifests,
                indexed_lookup_metrics=StrategyLadderWindowLookupMetrics(
                    status="INDEXED_WINDOW_LOOKUP_READY"
                ),
                window_cache_metrics=StrategyLadderWindowCacheMetrics(
                    status="WINDOW_CACHE_READY"
                ),
            )

        def _fake_materialize(*, candidate_events, **kwargs):
            materialized_events = tuple(
                event.model_copy(
                    update={
                        "candidate_source": "ENGINE_NATIVE",
                        "compatibility_payload": {
                            "candidate_source": "ENGINE_NATIVE",
                            "engine_native_decision": "no_trade",
                            "engine_native_reason_codes": (
                                ("engine_internal.engine_a.direction.non_long",)
                                if index == 0
                                else ("EXPECTED_EDGE_PROXY_BLOCKED",)
                            ),
                            "expected_edge_provenance": (
                                "PROXY_FORWARD_RETURN_MEDIAN_TO_CALIBRATE"
                            ),
                            "economic_provenance": "PARTIALLY_MEASURED",
                        },
                    }
                )
                for index, event in enumerate(candidate_events)
            )
            return strategy_ladder_runner_module._EngineNativeCandidateMaterialization(
                candidate_events=materialized_events,
                candidate_discovery_status="CANDIDATE_DISCOVERY_ENGINE_NATIVE_READY",
                engine_native_status="ENGINE_NATIVE_FULL_PATH_READY",
                engine_native_records_built=2,
                engine_native_runner_invocation_count=2,
                expected_edge_proxy_count=2,
                expected_edge_governed_count=0,
            )

        def _unexpected_replay(*args, **kwargs):
            raise AssertionError("detailed replay must not run when preselection is empty")

        monkeypatch.setattr(
            "local_replay_runtime.strategy_ladder_runner.extract_strategy_ladder_raw_windows",
            _fake_extract,
        )
        monkeypatch.setattr(
            "local_replay_runtime.strategy_ladder_runner._materialize_engine_native_candidates",
            _fake_materialize,
        )
        monkeypatch.setattr(
            "local_replay_runtime.strategy_ladder_runner.run_strategy_ladder_detailed_replay",
            _unexpected_replay,
        )

        result = run_backtest_strategy_ladder(
            StrategyLadderRequest(
                run_id="run-preselection-empty",
                input_root=input_root,
                feature_store_root=feature_root,
                raw_root=raw_root,
                output_root=scratch / "output",
                pairs=("BTCUSDT",),
                engines=("engine_a", "engine_b"),
                capital_buckets=(400,),
                engine_native_mode=True,
                b1_5_policy_mode="strict_fail_closed",
            )
        )

        assert result.run_manifest.preselection_status == "ENGINE_NATIVE_PRESELECTION_EMPTY"
        assert result.run_manifest.b1_5_policy_mode == "strict_fail_closed"
        assert result.run_manifest.engine_native_preselected_count == 0
        assert result.run_manifest.preselection_hard_rejected_count == 1
        assert result.run_manifest.preselection_soft_flagged_count == 1
        assert result.run_manifest.preselection_passed_count == 0
        assert result.run_manifest.b2_replay_candidate_count == 0
        assert result.run_manifest.candidate_truth_status == "CANDIDATE_ENGINE_NATIVE_READY"
        assert result.run_manifest.expected_edge_truth_status == "EXPECTED_EDGE_PROXY_BLOCKED"
        assert result.run_manifest.executed_trade_count == 0
        assert result.run_manifest.detailed_replay_count == 0
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_strategy_ladder_runner_materializes_native_candidates_and_blocks_proxy_edge() -> None:
    scratch = _scratch_dir("engine_native_deproxy_phase_a")
    shutil.rmtree(scratch, ignore_errors=True)
    try:
        input_root = scratch / "input"
        feature_root = input_root / "feature_store"
        raw_root = input_root / "raw"
        ts = 1_714_000_000_000
        trade_path = raw_root / "BTCUSDT" / "trades.jsonl"
        snapshot_path = raw_root / "BTCUSDT" / "book_depth20.jsonl"
        delta_path = raw_root / "BTCUSDT" / "book_delta.jsonl"
        ohlcv_path = raw_root / "BTCUSDT" / "ohlcv.jsonl"
        metadata_path = raw_root / "BTCUSDT" / "metadata.csv"
        _write_jsonl(
            feature_root / "features.jsonl",
            [
                _feature_row(
                    pair="BTCUSDT",
                    engine_id="engine_b",
                    timestamp_ms=ts,
                    expected_edge_bps=20.0,
                )
            ],
        )
        _write_jsonl(
            trade_path,
            [
                {"timestamp_ms": ts - 120_000, "price": 100.0, "qty": 1.0, "side": "buy"},
                {"timestamp_ms": ts - 60_000, "price": 99.5, "qty": 1.2, "side": "sell"},
                {"timestamp_ms": ts, "price": 99.0, "qty": 1.1, "side": "sell"},
            ],
        )
        _write_jsonl(snapshot_path, [_book_depth20_row(ts)])
        _write_jsonl(
            delta_path,
            [
                {
                    "timestamp_ms": ts,
                    "pair": "BTCUSDT",
                    "bids": [["100.00", "9.0"]],
                    "asks": [["100.10", "11.0"]],
                }
            ],
        )
        _write_jsonl(
            ohlcv_path,
            [
                {
                    "timestamp_ms": ts - (5 - index) * 60_000,
                    "open": 100.0 + index,
                    "high": 100.5 + index,
                    "low": 99.5 + index,
                    "close": 100.0 + index,
                    "volume": 10.0 + index,
                }
                for index in range(6)
            ],
        )
        _write_csv(
            metadata_path,
            "pair,min_notional,tick_size,step_size,maker_fee,taker_fee",
            ["BTCUSDT,10,0.01,0.0001,0.001,0.0015"],
        )
        _write_json(
            input_root / "silver_index.json",
            {
                "status": "SILVER_INDEX_READY",
                "entries": [
                    {
                        "source_id": "phase-b-fixture",
                        "source_root": str(raw_root.resolve()),
                        "source_priority": 10,
                        "exchange": "binance",
                        "market_type": "spot",
                        "data_type": data_type,
                        "pair": "BTCUSDT",
                        "timeframe": timeframe,
                        "path": str(path.resolve()),
                        "storage_format": storage_format,
                        "min_timestamp_ms": ts - 300_000,
                        "max_timestamp_ms": ts,
                        "row_count": row_count,
                        "depth_source_status": depth_status,
                        "schema_status": "SCHEMA_READY",
                    }
                    for data_type, timeframe, path, storage_format, row_count, depth_status in (
                        ("trades", "", trade_path, "jsonl", 3, "BOOK_DEPTH_NOT_PROVEN"),
                        (
                            "orderbook_snapshot",
                            "",
                            snapshot_path,
                            "jsonl",
                            1,
                            "BOOK_DEPTH20_AVAILABLE",
                        ),
                        (
                            "orderbook_delta",
                            "",
                            delta_path,
                            "jsonl",
                            1,
                            "BOOK_DEPTH20_AVAILABLE",
                        ),
                        ("ohlcv", "5m", ohlcv_path, "jsonl", 6, "BOOK_DEPTH_NOT_PROVEN"),
                        ("metadata", "", metadata_path, "csv", 1, "BOOK_DEPTH_NOT_PROVEN"),
                    )
                ],
            },
        )

        progress_manifests = []
        result = run_backtest_strategy_ladder(
            StrategyLadderRequest(
                run_id="run-engine-native-deproxy-1",
                input_root=input_root,
                feature_store_root=feature_root,
                raw_root=raw_root,
                output_root=scratch / "output",
                engines=("engine_b",),
                capital_buckets=(400,),
                engine_native_mode=True,
            ),
            progress_callback=progress_manifests.append,
        )

        manifest = result.run_manifest
        assert manifest.candidate_engine_native_count == 1
        assert manifest.candidate_proxy_count == 0
        assert manifest.candidate_truth_status == "CANDIDATE_ENGINE_NATIVE_READY"
        assert manifest.engine_native_status == "ENGINE_NATIVE_FULL_PATH_READY"
        assert manifest.expected_edge_truth_status == "EXPECTED_EDGE_PROXY_BLOCKED"
        assert manifest.expected_edge_proxy_count == 1
        assert manifest.expected_edge_governed_count == 0
        assert manifest.expected_edge_label_fidelity == "EXPECTED_EDGE_PROXY_DISCOVERY_ONLY"
        assert (
            manifest.expected_edge_anti_leakage_status
            == "EXPECTED_EDGE_ANTI_LEAKAGE_NOT_PROVEN"
        )
        assert "EXPECTED_EDGE_PROXY_BLOCKED" in manifest.expected_edge_blocker_codes
        assert "EXPECTED_EDGE_PROXY_NOT_BACKTEST_TRUTH" in manifest.blocker_codes
        assert manifest.raw_window_extraction_status == "RAW_WINDOW_READY"
        assert manifest.detailed_replay_status == "DETAILED_REPLAY_READY"
        assert manifest.detailed_replay_count == 1
        assert manifest.capital_profile_generation_status == "CAPITAL_PROFILE_GENERATION_READY"
        assert manifest.capital_profile_count == 1
        assert manifest.promotion_artifact_status == "PROMOTION_ARTIFACTS_BLOCKED_BY_FIDELITY"
        assert manifest.execution_label_source == "PARTIAL_CANONICAL_EXECUTION"
        assert manifest.execution_fidelity_gap_codes
        assert "EXPECTED_EDGE_PROXY_BLOCKED" in manifest.blocker_codes
        assert manifest.engine_promotion_count == 1
        assert manifest.pair_promotion_count == 1
        assert manifest.strategy_promotion_count == 1
        assert manifest.final_status == "STRATEGY_LADDER_BLOCKED_BY_NO_EXECUTED_TRADES"
        assert "NO_EXECUTED_TRADES" in manifest.blocker_codes
        assert result.report_summary.candidate_truth_status == "CANDIDATE_ENGINE_NATIVE_READY"
        assert result.report_summary.expected_edge_truth_status == "EXPECTED_EDGE_PROXY_BLOCKED"
        assert result.report_summary.engine_native_status == "ENGINE_NATIVE_FULL_PATH_READY"
        assert result.report_summary.execution_label_source == "PARTIAL_CANONICAL_EXECUTION"
        assert result.report_summary.execution_fidelity_gap_codes
        assert any(
            item.engine_native_status == "ENGINE_NATIVE_MATERIALIZING"
            for item in progress_manifests
        )

        run_dir = scratch / "output" / "backtest_strategy_ladder" / "run-engine-native-deproxy-1"
        assert (run_dir / "run_manifest.json").is_file()
        assert (run_dir / "capital_profiles" / "400.json").is_file()
        assert (
            run_dir / "engine_promotion" / "engine_b" / "run-engine-native-deproxy-1.json"
        ).is_file()
        assert (
            run_dir / "pair_promotion" / "BTCUSDT" / "run-engine-native-deproxy-1.json"
        ).is_file()
        assert (
            run_dir / "strategy_promotion" / "engine_b" / "run-engine-native-deproxy-1.json"
        ).is_file()
        assert (run_dir / "reports" / "strategy_ladder_report.md").is_file()
        assert (run_dir / "reports" / "strategy_ladder_summary.json").is_file()
        assert (run_dir / "reports" / "post_b2_refusal_audit.json").is_file()
        assert (run_dir / "reports" / "post_b2_refusal_audit.md").is_file()
        assert (run_dir / "reports" / "governed_audit_evidence_index.json").is_file()
        assert (run_dir / "reports" / "timeframe_matrix.json").is_file()
        event = json.loads(
            (run_dir / "fast_candidates" / "candidate_events.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()[0]
        )
        payload = event["compatibility_payload"]
        assert event["candidate_source"] == "ENGINE_NATIVE"
        assert payload["candidate_source"] == "ENGINE_NATIVE"
        assert payload["expected_edge_provenance"] == "PROXY_FORWARD_RETURN_MEDIAN_TO_CALIBRATE"
        assert payload["expected_edge_truth_status"] == "EXPECTED_EDGE_PROXY_BLOCKED"
        assert payload["engine_native_decision"] == "no_trade"
        assert payload["production_decision_state"] == "hard_blocked"
        assert payload["target_decision_state"] == "hard_blocked"
        assert "EXPECTED_EDGE_NOT_GOVERNED_FOR_BACKTEST_TRUTH" not in payload["hard_block_reasons"]
        assert "FEE_AWARE_EDGE_PROXY_BLOCKED" not in payload["hard_block_reasons"]
        assert "BREAK_EVEN_PROXY_BLOCKED" not in payload["hard_block_reasons"]
        assert "EXPECTED_EDGE_NOT_GOVERNED_FOR_BACKTEST_TRUTH" in payload["profitability_blocker_reasons"]
        assert "FEE_AWARE_EDGE_PROXY_BLOCKED" in payload["profitability_blocker_reasons"]
        assert "BREAK_EVEN_PROXY_BLOCKED" in payload["profitability_blocker_reasons"]
        candidate_id = event["candidate_id"]
        replay_payload = json.loads(
            (run_dir / "detailed_replay" / "by_bucket" / "400" / f"{candidate_id}.json")
            .read_text(encoding="utf-8")
        )
        assert replay_payload["execution_state"] == "hard_blocked"
        assert "EXPECTED_EDGE_NOT_GOVERNED_FOR_BACKTEST_TRUTH" not in replay_payload["reason_codes"]
        assert (
            "EXPECTED_EDGE_NOT_GOVERNED_FOR_BACKTEST_TRUTH"
            not in replay_payload["dtr_record"]["cause_chain"]
        )
        refusal_rows = [
            json.loads(line)
            for line in (run_dir / "refusal_ledger.jsonl").read_text(encoding="utf-8").splitlines()
            if line and not bool(json.loads(line).get("artifact_header"))
        ]
        assert refusal_rows
        assert refusal_rows[0]["execution_state"] == "hard_blocked"
        assert "EXPECTED_EDGE_NOT_GOVERNED_FOR_BACKTEST_TRUTH" not in refusal_rows[0]["reason_codes"]
        summary_payload = json.loads(
            (run_dir / "reports" / "strategy_ladder_summary.json").read_text(encoding="utf-8")
        )
        assert summary_payload["candidate_truth_status"] == "CANDIDATE_ENGINE_NATIVE_READY"
        assert summary_payload["expected_edge_truth_status"] == "EXPECTED_EDGE_PROXY_BLOCKED"
        assert summary_payload["expected_edge_label_fidelity"] == "EXPECTED_EDGE_PROXY_DISCOVERY_ONLY"
        assert summary_payload["expected_edge_anti_leakage_status"] == "EXPECTED_EDGE_ANTI_LEAKAGE_NOT_PROVEN"
        assert summary_payload["promotion_artifact_status"] == "PROMOTION_ARTIFACTS_BLOCKED_BY_FIDELITY"
        assert summary_payload["candidate_engine_native_count"] == 1
        assert summary_payload["candidate_proxy_count"] == 0
        assert summary_payload["execution_label_source"] == "PARTIAL_CANONICAL_EXECUTION"
        assert summary_payload["execution_fidelity_gap_codes"]
        assert summary_payload["governed_evidence_status"] == "EVIDENCE_AUDIT_NOT_CONFIRMED"
        assert summary_payload["audited_evidence_count"] == 0
        assert summary_payload["scratch_only_evidence_count"] > 0
        assert summary_payload["promotion_grade_evidence_count"] == 0
        assert summary_payload["run_manifest_evidence_class"] == "SCRATCH_ONLY"
        assert summary_payload["capital_profiles_evidence_class"] == "SCRATCH_ONLY"
        assert summary_payload["engine_promotion_evidence_class"] == "SCRATCH_ONLY"
        assert summary_payload["pair_promotion_evidence_class"] == "SCRATCH_ONLY"
        assert summary_payload["strategy_promotion_evidence_class"] == "SCRATCH_ONLY"
        assert summary_payload["sample_size_survival_evidence_class"] == "SCRATCH_ONLY"
        assert summary_payload["trade_detail_ledger_evidence_class"] == "SCRATCH_ONLY"
        assert summary_payload["refusal_ledger_evidence_class"] == "SCRATCH_ONLY"
        assert summary_payload["loss_analysis_ledger_evidence_class"] == "SCRATCH_ONLY"
        assert "EVIDENCE_AUDIT_NOT_CONFIRMED" in summary_payload["evidence_audit_blocker_codes"]
        assert "EVIDENCE_AUDIT_NOT_CONFIRMED" in summary_payload["promotion_blockers"]
        report_markdown = (run_dir / "reports" / "strategy_ladder_report.md").read_text(
            encoding="utf-8"
        )
        refusal_audit_payload = json.loads(
            (run_dir / "reports" / "post_b2_refusal_audit.json").read_text(
                encoding="utf-8"
            )
        )
        refusal_audit_markdown = (run_dir / "reports" / "post_b2_refusal_audit.md").read_text(
            encoding="utf-8"
        )
        evidence_index_payload = json.loads(
            (run_dir / "reports" / "governed_audit_evidence_index.json").read_text(
                encoding="utf-8"
            )
        )
        assert "candidate_truth_status: CANDIDATE_ENGINE_NATIVE_READY" in report_markdown
        assert "expected_edge_truth_status: EXPECTED_EDGE_PROXY_BLOCKED" in report_markdown
        assert "promotion_artifact_status: PROMOTION_ARTIFACTS_BLOCKED_BY_FIDELITY" in report_markdown
        assert "execution_label_source: PARTIAL_CANONICAL_EXECUTION" in report_markdown
        assert "## Proxy & Fidelity Surface" in report_markdown
        assert "feature_row_sample_status: NOT_PROVEN_SMALL_SAMPLE" in report_markdown
        assert "expected_edge_governance_status: EXPECTED_EDGE_NOT_GOVERNED" in report_markdown
        assert "expected_edge_label_fidelity: EXPECTED_EDGE_PROXY_DISCOVERY_ONLY" in report_markdown
        assert "expected_edge_anti_leakage_status: EXPECTED_EDGE_ANTI_LEAKAGE_NOT_PROVEN" in report_markdown
        assert "threshold_calibration_status:" in report_markdown
        assert "threshold_counts: default=" in report_markdown
        assert "venue_transfer_status: BINANCE_SHADOW_REQUIRED" in report_markdown
        assert "## Governed Audit Evidence" in report_markdown
        assert "governed_evidence_status: EVIDENCE_AUDIT_NOT_CONFIRMED" in report_markdown
        assert "run_manifest_evidence_class: SCRATCH_ONLY" in report_markdown
        assert "trade_detail_ledger_evidence_class: SCRATCH_ONLY" in report_markdown
        assert refusal_audit_payload["candidate_funnel"]["selected_count"] == 0
        assert refusal_audit_payload["profitability_claim_allowed"] is False
        assert (
            refusal_audit_payload["profitability_claim_blocker"]
            == "SELECTED_COUNT_ZERO_NO_PROFITABILITY_CLAIM"
        )
        assert (
            refusal_audit_payload["evidence"]["refusal_ledger_evidence_class"]
            == "SCRATCH_ONLY"
        )
        assert refusal_audit_payload["common_blockers"]
        assert "ENGINE_NATIVE_NO_TRADE" in {
            item["reason_code"] for item in refusal_audit_payload["common_blockers"]
        }
        assert "## Candidate Funnel" in refusal_audit_markdown
        assert "profitability_claim_allowed: False" in refusal_audit_markdown
        assert "refusal_ledger_evidence_class: SCRATCH_ONLY" in refusal_audit_markdown
        assert evidence_index_payload["entries"]
        assert {
            item["evidence_class"] for item in evidence_index_payload["entries"]
        } == {"SCRATCH_ONLY"}
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


class _RunnerStaticGovernedExpectedEdgeModel:
    artifact_hash = "a" * 64
    feature_hash = "b" * 64

    def estimate_expected_edge_bps(self, **kwargs: object) -> EdgeEstimate:
        feature_values = kwargs["feature_values"]
        assert isinstance(feature_values, dict)
        assert feature_values["edge_score"] == 2.0
        return EdgeEstimate(
            edge_bps=12.5,
            provenance="GOVERNED_ML_ARTIFACT_BACKTEST_TRUTH",
            n_lookback_bars_used=0,
            median_abs_forward_return=0.0,
            detector_status="GOVERNED_EDGE_MODEL_READY",
            artifact_hash=self.artifact_hash,
            feature_hash=self.feature_hash,
            model_status="GOVERNED_EDGE_MODEL_READY",
        )


def test_strategy_ladder_runner_uses_frozen_ml_artifact_for_governed_edge(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scratch = _scratch_dir("engine_native_governed_edge")
    shutil.rmtree(scratch, ignore_errors=True)
    try:
        input_root = scratch / "input"
        feature_root = input_root / "feature_store"
        raw_root = input_root / "raw"
        ts = 1_714_000_000_000
        trade_path = raw_root / "BTCUSDT" / "trades.jsonl"
        snapshot_path = raw_root / "BTCUSDT" / "book_depth20.jsonl"
        delta_path = raw_root / "BTCUSDT" / "book_delta.jsonl"
        ohlcv_path = raw_root / "BTCUSDT" / "ohlcv.jsonl"
        metadata_path = raw_root / "BTCUSDT" / "metadata.csv"
        artifact_path = scratch / "edge_artifact.json"
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        artifact_path.write_text("{}", encoding="utf-8")
        _write_jsonl(
            feature_root / "features.jsonl",
            [
                _feature_row(
                    pair="BTCUSDT",
                    engine_id="engine_b",
                    timestamp_ms=ts,
                    expected_edge_bps=20.0,
                )
            ],
        )
        _write_jsonl(
            trade_path,
            [
                {"timestamp_ms": ts - 120_000, "price": 100.0, "qty": 1.0, "side": "buy"},
                {"timestamp_ms": ts - 60_000, "price": 99.5, "qty": 1.2, "side": "sell"},
                {"timestamp_ms": ts, "price": 99.0, "qty": 1.1, "side": "sell"},
            ],
        )
        _write_jsonl(snapshot_path, [_book_depth20_row(ts)])
        _write_jsonl(
            delta_path,
            [
                {
                    "timestamp_ms": ts,
                    "pair": "BTCUSDT",
                    "bids": [["100.00", "9.0"]],
                    "asks": [["100.10", "11.0"]],
                }
            ],
        )
        _write_jsonl(
            ohlcv_path,
            [
                {
                    "timestamp_ms": ts - (5 - index) * 60_000,
                    "open": 100.0 + index,
                    "high": 100.5 + index,
                    "low": 99.5 + index,
                    "close": 100.0 + index,
                    "volume": 10.0 + index,
                }
                for index in range(6)
            ],
        )
        _write_csv(
            metadata_path,
            "pair,min_notional,tick_size,step_size,maker_fee,taker_fee",
            ["BTCUSDT,10,0.01,0.0001,0.001,0.0015"],
        )
        _write_json(
            input_root / "silver_index.json",
            {
                "status": "SILVER_INDEX_READY",
                "entries": [
                    {
                        "source_id": "governed-edge-fixture",
                        "source_root": str(raw_root.resolve()),
                        "source_priority": 10,
                        "exchange": "binance",
                        "market_type": "spot",
                        "data_type": data_type,
                        "pair": "BTCUSDT",
                        "timeframe": timeframe,
                        "path": str(path.resolve()),
                        "storage_format": storage_format,
                        "min_timestamp_ms": ts - 300_000,
                        "max_timestamp_ms": ts,
                        "row_count": row_count,
                        "depth_source_status": depth_status,
                        "schema_status": "SCHEMA_READY",
                    }
                    for data_type, timeframe, path, storage_format, row_count, depth_status in (
                        ("trades", "", trade_path, "jsonl", 3, "BOOK_DEPTH_NOT_PROVEN"),
                        (
                            "orderbook_snapshot",
                            "",
                            snapshot_path,
                            "jsonl",
                            1,
                            "BOOK_DEPTH20_AVAILABLE",
                        ),
                        (
                            "orderbook_delta",
                            "",
                            delta_path,
                            "jsonl",
                            1,
                            "BOOK_DEPTH20_AVAILABLE",
                        ),
                        ("ohlcv", "5m", ohlcv_path, "jsonl", 6, "BOOK_DEPTH_NOT_PROVEN"),
                        ("metadata", "", metadata_path, "csv", 1, "BOOK_DEPTH_NOT_PROVEN"),
                    )
                ],
            },
        )

        def _fake_load(*args: object, **kwargs: object) -> GovernedExpectedEdgeModelLoadResult:
            assert kwargs["expected_artifact_hash"] == "a" * 64
            return GovernedExpectedEdgeModelLoadResult(
                model=_RunnerStaticGovernedExpectedEdgeModel(),
                status="EXPECTED_EDGE_GOVERNED_BACKTEST_LABELS_READY",
                training_artifact_ref=str(artifact_path.resolve()),
                artifact_hash="a" * 64,
                feature_hash="b" * 64,
                label_source="strategy_ladder_forward_return_label",
                label_fidelity="EXPECTED_EDGE_GOVERNED_BACKTEST_LABELS_READY",
                anti_leakage_status="EXPECTED_EDGE_ANTI_LEAKAGE_PROVEN",
                walkforward_status="EXPECTED_EDGE_WALKFORWARD_DECLARED",
                horizon_minutes=5,
                purge_window_minutes=30,
                embargo_window_minutes=30,
                blocker_codes=(
                    "EXPECTED_EDGE_GOVERNED_SHADOW_REQUIRED",
                    "EXPECTED_EDGE_NOT_PROMOTION_GRADE",
                ),
            )

        monkeypatch.setattr(
            "local_replay_runtime.strategy_ladder_runner.load_governed_expected_edge_model_artifact",
            _fake_load,
        )

        result = run_backtest_strategy_ladder(
            StrategyLadderRequest(
                run_id="run-engine-native-governed-edge-1",
                input_root=input_root,
                feature_store_root=feature_root,
                raw_root=raw_root,
                output_root=scratch / "output",
                engines=("engine_b",),
                capital_buckets=(400,),
                engine_native_mode=True,
                ml_mode="ML_MODE_OVERLAY_FROZEN",
                frozen_ml_artifact_path=artifact_path,
                frozen_ml_artifact_hash="a" * 64,
            )
        )

        manifest = result.run_manifest
        assert manifest.ml_mode_status == "ML_MODE_OVERLAY_FROZEN"
        assert manifest.expected_edge_truth_status == "EXPECTED_EDGE_GOVERNED_BACKTEST_TRUTH"
        assert manifest.expected_edge_proxy_count == 0
        assert manifest.expected_edge_governed_count == 1
        assert manifest.expected_edge_model_status == "GOVERNED_EDGE_MODEL_READY"
        assert manifest.expected_edge_model_artifact_hash == "a" * 64
        assert manifest.expected_edge_training_artifact_ref == str(artifact_path.resolve())
        assert manifest.expected_edge_label_source == "strategy_ladder_forward_return_label"
        assert (
            manifest.expected_edge_label_fidelity
            == "EXPECTED_EDGE_GOVERNED_BACKTEST_LABELS_READY"
        )
        assert (
            manifest.expected_edge_anti_leakage_status
            == "EXPECTED_EDGE_ANTI_LEAKAGE_PROVEN"
        )
        assert manifest.expected_edge_horizon == 5
        assert "EXPECTED_EDGE_PROXY_NOT_BACKTEST_TRUTH" not in manifest.blocker_codes
        assert "EXPECTED_EDGE_MODEL_NOT_BACKTEST_TRUTH" not in manifest.blocker_codes
        assert "EXPECTED_EDGE_NOT_PROMOTION_GRADE" in manifest.expected_edge_blocker_codes

        run_dir = (
            scratch
            / "output"
            / "backtest_strategy_ladder"
            / "run-engine-native-governed-edge-1"
        )
        event = json.loads(
            (run_dir / "fast_candidates" / "candidate_events.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()[0]
        )
        payload = event["compatibility_payload"]
        assert payload["expected_edge_provenance"] == "GOVERNED_ML_ARTIFACT_BACKTEST_TRUTH"
        assert payload["expected_edge_truth_status"] == "EXPECTED_EDGE_GOVERNED_BACKTEST_TRUTH"
        assert payload["expected_edge_model_status"] == "GOVERNED_EDGE_MODEL_READY"
        assert payload["expected_edge_model_artifact_hash"] == "a" * 64
        assert "EXPECTED_EDGE_NOT_GOVERNED_FOR_BACKTEST_TRUTH" not in payload["hard_block_reasons"]
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_strategy_ladder_request_ml_mode_off_allows_long_backtest_without_plan() -> None:
    scratch = _scratch_dir("ml_mode_off_long_backtest")
    request = StrategyLadderRequest(
        run_id="long-baseline-1",
        input_root=scratch / "input",
        feature_store_root=scratch / "features",
        raw_root=scratch / "raw",
        output_root=scratch / "output",
        start="2025-05-01",
        end="2025-09-07",
        ml_mode="ML_MODE_OFF",
    )

    assert request.ml_mode == "ML_MODE_OFF"
    assert request.rolling_ml_window_plan_path is None


def test_strategy_ladder_request_frozen_ml_long_backtest_requires_plan() -> None:
    scratch = _scratch_dir("frozen_ml_long_backtest_requires_plan")

    with pytest.raises(
        ValueError,
        match="rolling_ml_window_plan_path",
    ):
        StrategyLadderRequest(
            run_id="long-frozen-1",
            input_root=scratch / "input",
            feature_store_root=scratch / "features",
            raw_root=scratch / "raw",
            output_root=scratch / "output",
            start="2025-05-01",
            end="2025-09-07",
            ml_mode="ML_MODE_OVERLAY_FROZEN",
            frozen_ml_artifact_path=scratch / "artifact.json",
            frozen_ml_artifact_hash="a" * 64,
        )


def test_strategy_ladder_runner_hydrates_b2_from_consumed_a2_and_b1_artifacts() -> None:
    scratch = _scratch_dir("b2_hydration_from_a2_b1")
    shutil.rmtree(scratch, ignore_errors=True)
    try:
        workflow_root = scratch / "workflow"
        a2_root = workflow_root / "phase_a2_data_factory"
        b1_root = workflow_root / "phase_b1_candidate_discovery" / "backtest_strategy_ladder" / "run-b2-hydration"
        b2_root = workflow_root / "phase_b2_detailed_replay"
        raw_root = scratch / "raw"
        ts = 1_714_000_000_000
        trade_path = raw_root / "BTCUSDT" / "trades.jsonl"
        snapshot_path = raw_root / "BTCUSDT" / "book_depth20.jsonl"
        delta_path = raw_root / "BTCUSDT" / "book_delta.jsonl"
        ohlcv_path = raw_root / "BTCUSDT" / "ohlcv.jsonl"
        metadata_path = raw_root / "BTCUSDT" / "metadata.csv"
        _write_jsonl(
            trade_path,
            [
                {"timestamp_ms": ts - 120_000, "price": 100.0, "qty": 1.0, "side": "buy"},
                {"timestamp_ms": ts - 60_000, "price": 99.5, "qty": 1.2, "side": "sell"},
                {"timestamp_ms": ts, "price": 99.0, "qty": 1.1, "side": "sell"},
            ],
        )
        _write_jsonl(snapshot_path, [_book_depth20_row(ts)])
        _write_jsonl(
            delta_path,
            [
                {
                    "timestamp_ms": ts,
                    "pair": "BTCUSDT",
                    "bids": [["100.00", "9.0"]],
                    "asks": [["100.10", "11.0"]],
                }
            ],
        )
        _write_jsonl(
            ohlcv_path,
            [
                {
                    "timestamp_ms": ts - (5 - index) * 60_000,
                    "open": 100.0 + index,
                    "high": 100.5 + index,
                    "low": 99.5 + index,
                    "close": 100.0 + index,
                    "volume": 10.0 + index,
                }
                for index in range(6)
            ],
        )
        _write_csv(
            metadata_path,
            "pair,min_notional,tick_size,step_size,maker_fee,taker_fee",
            ["BTCUSDT,10,0.01,0.0001,0.001,0.0015"],
        )

        row = StrategyLadderFeatureRow.model_validate(
            _feature_row(pair="BTCUSDT", engine_id="engine_b", timestamp_ms=ts)
        )
        _, discovered = discover_strategy_ladder_candidates(
            run_id="run-b2-hydration",
            rows=(row,),
        )
        candidate = discovered[0]
        _write_jsonl(
            b1_root / "fast_candidates" / "candidate_events.jsonl",
            [candidate.model_dump(mode="json")],
        )
        _write_json(
            b1_root / "fast_candidates" / "candidate_summary.json",
            {
                "run_id": "run-b2-hydration",
                "candidate_count": 1,
                "unique_candidate_count": 1,
                "base_event_count": 1,
                "per_engine_candidate_count": 1,
                "engine_native_candidate_count": 0,
                "candidate_source_status": "CANDIDATE_SOURCE_COMPAT_PROXY_DISCOVERY",
                "candidate_export_status": "CANDIDATE_EXPORT_READY",
                "candidate_discovery_status": "CANDIDATE_DISCOVERY_SAMPLE_CAPPED",
                "candidate_sample_cap": 50,
                "effective_engine_native_sample_size": 50,
                "engine_count": 1,
                "candidate_cap_formula": "1 engines x 50",
                "small_scope_enabled": False,
                "full_scan_enabled": True,
                "no_full_scan_enabled": False,
                "candidate_discovery_limited": True,
                "candidate_discovery_limit_reason": "ENGINE_NATIVE_SAMPLE_CAP_ACTIVE",
                "candidate_discovery_mode": "FULL_DISCOVERY",
                "candidate_discovery_cap_status": "CANDIDATE_DISCOVERY_SAMPLE_CAPPED",
            },
        )
        _write_json(
            a2_root / "data_factory_manifest.json",
            {
                "data_factory_status": "DATA_FACTORY_READY",
                "raw_source_status": "RAW_SOURCE_READY",
                "pair_universe_status": "PAIR_UNIVERSE_READY",
                "silver_index_status": "SILVER_INDEX_READY",
                "gold_feature_store_status": "FEATURE_STORE_READY",
            },
        )
        _write_json(
            a2_root / "raw_source_report.json",
            {"raw_source_status": "RAW_SOURCE_READY"},
        )
        _write_json(
            a2_root / "pair_universe_report.json",
            {"pair_universe_status": "PAIR_UNIVERSE_READY"},
        )
        _write_json(
            a2_root / "data_quality_report.json",
            {"orderbook_schema_status": "ORDERBOOK_DATA_SCHEMA_INVALID"},
        )
        _write_json(
            a2_root / "gold_feature_manifest.json",
            {
                "gold_feature_store_status": "FEATURE_STORE_READY",
                "feature_row_count": 1,
            },
        )
        _write_json(
            a2_root / "silver_index.json",
            {
                "status": "SILVER_INDEX_READY",
                "entries": [
                    {
                        "source_id": "b2-hydration-fixture",
                        "source_root": str(raw_root.resolve()),
                        "source_priority": 10,
                        "exchange": "binance",
                        "market_type": "spot",
                        "data_type": data_type,
                        "pair": "BTCUSDT",
                        "timeframe": timeframe,
                        "path": str(path.resolve()),
                        "storage_format": storage_format,
                        "min_timestamp_ms": ts - 300_000,
                        "max_timestamp_ms": ts,
                        "row_count": row_count,
                        "depth_source_status": depth_status,
                        "schema_status": "SCHEMA_READY",
                    }
                    for data_type, timeframe, path, storage_format, row_count, depth_status in (
                        ("trades", "", trade_path, "jsonl", 3, "BOOK_DEPTH_NOT_PROVEN"),
                        ("orderbook_snapshot", "", snapshot_path, "jsonl", 1, "BOOK_DEPTH20_AVAILABLE"),
                        ("orderbook_delta", "", delta_path, "jsonl", 1, "BOOK_DEPTH20_AVAILABLE"),
                        ("ohlcv", "5m", ohlcv_path, "jsonl", 6, "BOOK_DEPTH_NOT_PROVEN"),
                        ("metadata", "", metadata_path, "csv", 1, "BOOK_DEPTH_NOT_PROVEN"),
                    )
                ],
            },
        )

        workflow_manifest_path = workflow_root / "workflow_manifest.json"
        ensure_workflow_manifest(
            workflow_root=workflow_root,
            workflow_run_id="workflow-demo",
            request_hash="workflow-demo-request-hash",
            phase_id=PHASE_B2,
            pairs=("BTCUSDT",),
            start="2025-05-08",
            end="2025-05-08",
            ml_mode="ML_MODE_OFF",
            candidate_discovery_mode="FULL_DISCOVERY",
            engine_native_sample_size=50,
            engine_count=4,
            allow_broad_run=False,
            small_scope_enabled=False,
            full_scan_enabled=True,
            no_full_scan_enabled=False,
            silver_storage_mode_requested="jsonl_gz",
            silver_storage_mode_effective="jsonl_gz",
        )
        upsert_workflow_phase(
            workflow_root=workflow_root,
            workflow_run_id="workflow-demo",
            phase_id=PHASE_B2,
            phase_run_id="phase_b2-stale",
            phase_output_root=scratch / "stale_b2_output",
            parent_workflow_ref=str(workflow_manifest_path.resolve()),
            job_id="strategy_ladder_runner-old",
            request_hash="workflow-demo-request-hash",
            phase_status=PHASE_STATUS_PROOF_BLOCKED,
            blocker_codes=("OUTPUT_ROOT_EXISTS_NON_EMPTY",),
            error_code="OUTPUT_ROOT_EXISTS_NON_EMPTY",
            stderr_ref="stale_b2_stdout.log",
        )

        result = run_backtest_strategy_ladder(
            StrategyLadderRequest(
                run_id="run-b2-hydration",
                input_root=b2_root,
                feature_store_root=a2_root / "gold",
                raw_root=raw_root,
                output_root=b2_root,
                pairs=("BTCUSDT",),
                capital_buckets=(400,),
                detailed_only=True,
                resume=True,
                workflow_run_id="workflow-demo",
                phase_run_id="phase_b2-demo",
                parent_workflow_ref=str(workflow_manifest_path),
                engine_native_mode=True,
                engine_native_sample_size=50,
                candidate_discovery_mode="FULL_DISCOVERY",
                candidate_events_path=b1_root / "fast_candidates" / "candidate_events.jsonl",
                silver_index_path=a2_root / "silver_index.json",
                full_scan_enabled=True,
            )
        )

        manifest = result.run_manifest
        assert manifest.workflow_run_id == "workflow-demo"
        assert manifest.phase_run_id == "phase_b2-demo"
        assert manifest.parent_workflow_ref == str(workflow_manifest_path.resolve())
        assert manifest.data_factory_status == "DATA_FACTORY_READY"
        assert manifest.raw_source_status == "RAW_SOURCE_READY"
        assert manifest.pair_universe_status == "PAIR_UNIVERSE_READY"
        assert manifest.silver_index_status == "SILVER_INDEX_READY"
        assert manifest.gold_feature_store_status == "FEATURE_STORE_READY"
        assert manifest.silver_index_path == str((a2_root / "silver_index.json").resolve())
        assert manifest.candidate_sample_cap == 50
        assert manifest.effective_engine_native_sample_size == 50
        assert manifest.full_scan_enabled is True
        assert manifest.small_scope_enabled is False
        assert manifest.engine_native_status != "ENGINE_NATIVE_FAILED_NO_RUNNER_INVOCATIONS"
        assert manifest.blocker_codes.count("SUMMARY_INCONSISTENT") == 0

        summary_payload = json.loads(
            (
                b2_root
                / "backtest_strategy_ladder"
                / "run-b2-hydration"
                / "reports"
                / "strategy_ladder_summary.json"
            ).read_text(encoding="utf-8")
        )
        assert summary_payload["workflow_run_id"] == "workflow-demo"
        assert summary_payload["phase_run_id"] == "phase_b2-demo"
        assert summary_payload["parent_workflow_ref"] == str(workflow_manifest_path.resolve())
        assert summary_payload["candidate_sample_cap"] == 50
        assert summary_payload["silver_index_path"] == str((a2_root / "silver_index.json").resolve())
        assert summary_payload["silver_index_status"] == "SILVER_INDEX_READY"
        assert summary_payload["data_factory_status"] == "DATA_FACTORY_READY"
        assert summary_payload["blocker_codes"].count("SUMMARY_INCONSISTENT") == 0
        workflow_manifest = read_workflow_manifest(workflow_root)
        assert workflow_manifest is not None
        phase_b2 = workflow_manifest.phases[PHASE_B2]
        assert phase_b2.phase_run_id == "phase_b2-demo"
        assert phase_b2.job_id == "phase_b2-demo"
        assert phase_b2.error_code == ""
        assert phase_b2.stderr_ref == ""
        assert "OUTPUT_ROOT_EXISTS_NON_EMPTY" not in phase_b2.blocker_codes
        assert phase_b2.phase_output_root == str(b2_root.resolve())
        assert phase_b2.produced_artifact_refs["run_manifest.json"].endswith("run_manifest.json")
        assert not (
            b2_root / "backtest_strategy_ladder" / "run-b2-hydration" / "run_manifest.progress.json"
        ).exists()
        assert phase_b2.produced_artifact_refs["strategy_ladder_summary.json"].endswith(
            "strategy_ladder_summary.json"
        )
        assert phase_b2.consumed_artifact_refs["phase_b1_candidate_events"].endswith(
            "candidate_events.jsonl"
        )
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_b1_successful_rerun_replaces_stale_parent_workflow_phase_record() -> None:
    scratch = _scratch_dir("b1_parent_workflow_phase_sync")
    shutil.rmtree(scratch, ignore_errors=True)
    try:
        workflow_root = scratch / "workflow_root"
        a2_root = workflow_root / "phase_a2_data_factory"
        feature_root = a2_root / "gold"
        raw_root = scratch / "raw_root"
        b1_root = workflow_root / "phase_b1_candidate_discovery"

        _write_json(
            a2_root / "data_factory_manifest.json",
            {
                "data_factory_status": "DATA_FACTORY_READY",
                "raw_source_status": "RAW_SOURCE_READY",
                "pair_universe_status": "PAIR_UNIVERSE_READY",
                "silver_index_status": "SILVER_INDEX_READY",
                "gold_feature_store_status": "FEATURE_STORE_READY",
            },
        )
        _write_json(a2_root / "raw_source_report.json", {"raw_source_status": "RAW_SOURCE_READY"})
        _write_json(a2_root / "pair_universe_report.json", {"pair_universe_status": "PAIR_UNIVERSE_READY"})
        _write_json(
            a2_root / "data_quality_report.json",
            {"orderbook_schema_status": "ORDERBOOK_DATA_SCHEMA_INVALID"},
        )
        _write_json(
            a2_root / "gold_feature_manifest.json",
            {"gold_feature_store_status": "FEATURE_STORE_READY", "feature_row_count": 1},
        )
        _write_jsonl(
            feature_root / "features.jsonl",
            [_feature_row(pair="BTCUSDT", engine_id="engine_a", timeframe="5m")],
        )
        _write_json(
            a2_root / "silver_index.json",
            {
                "status": "SILVER_INDEX_READY",
                "entries": [
                    {
                        "source_id": "b1-fixture",
                        "source_root": str(raw_root.resolve()),
                        "source_priority": 10,
                        "exchange": "binance",
                        "market_type": "spot",
                        "data_type": "trades",
                        "pair": "BTCUSDT",
                        "timeframe": "",
                        "path": str((raw_root / "trades.jsonl").resolve()),
                        "storage_format": "jsonl_gz",
                        "min_timestamp_ms": 1_714_000_000_000,
                        "max_timestamp_ms": 1_714_000_300_000,
                        "row_count": 1,
                        "depth_source_status": "BOOK_DEPTH_NOT_PROVEN",
                        "schema_status": "SCHEMA_READY",
                    }
                ],
            },
        )

        workflow_manifest_path = workflow_root / "workflow_manifest.json"
        ensure_workflow_manifest(
            workflow_root=workflow_root,
            workflow_run_id="workflow-b1-demo",
            request_hash="workflow-b1-request-hash",
            phase_id=PHASE_B1,
            pairs=("BTCUSDT",),
            start="2025-05-08",
            end="2025-05-08",
            ml_mode="ML_MODE_OFF",
            candidate_discovery_mode="FULL_DISCOVERY",
            engine_native_sample_size=25,
            engine_count=4,
            allow_broad_run=False,
            small_scope_enabled=False,
            full_scan_enabled=True,
            no_full_scan_enabled=False,
            silver_storage_mode_requested="jsonl_gz",
            silver_storage_mode_effective="jsonl_gz",
        )
        upsert_workflow_phase(
            workflow_root=workflow_root,
            workflow_run_id="workflow-b1-demo",
            phase_id=PHASE_B1,
            phase_run_id="phase_b1-stale",
            phase_output_root=scratch / "stale_b1_output",
            parent_workflow_ref=str(workflow_manifest_path.resolve()),
            job_id="strategy_ladder_runner-old",
            request_hash="workflow-b1-request-hash",
            phase_status=PHASE_STATUS_DISCOVERY_BLOCKED,
            blocker_codes=("OUTPUT_ROOT_EXISTS_NON_EMPTY",),
            error_code="OUTPUT_ROOT_EXISTS_NON_EMPTY",
            stderr_ref="stale_b1_stdout.log",
        )

        result = run_backtest_strategy_ladder(
            StrategyLadderRequest(
                run_id="run-b1-ledger-sync",
                input_root=b1_root,
                feature_store_root=feature_root,
                raw_root=raw_root,
                output_root=b1_root,
                pairs=("BTCUSDT",),
                engines=("engine_a",),
                capital_buckets=(400,),
                fast_only=True,
                resume=False,
                workflow_run_id="workflow-b1-demo",
                phase_run_id="phase_b1-demo",
                parent_workflow_ref=str(workflow_manifest_path),
                engine_native_sample_size=25,
                candidate_discovery_mode="FULL_DISCOVERY",
                silver_index_path=a2_root / "silver_index.json",
                small_scope_enabled=False,
                full_scan_enabled=True,
                no_full_scan_enabled=False,
            )
        )

        assert result.run_manifest.candidate_export_status == "CANDIDATE_EXPORT_READY"
        workflow_manifest = read_workflow_manifest(workflow_root)
        assert workflow_manifest is not None
        phase_b1 = workflow_manifest.phases[PHASE_B1]
        assert phase_b1.phase_run_id == "phase_b1-demo"
        assert phase_b1.job_id == "phase_b1-demo"
        assert phase_b1.error_code == ""
        assert phase_b1.stderr_ref == ""
        assert "OUTPUT_ROOT_EXISTS_NON_EMPTY" not in phase_b1.blocker_codes
        assert phase_b1.phase_status == "PHASE_B1_CANDIDATE_DISCOVERY_READY"
        assert phase_b1.phase_output_root == str(b1_root.resolve())
        assert phase_b1.produced_artifact_refs["candidate_events.jsonl"].endswith(
            "candidate_events.jsonl"
        )
        assert phase_b1.produced_artifact_refs["candidate_summary.json"].endswith(
            "candidate_summary.json"
        )
        assert phase_b1.consumed_artifact_refs["phase_a2_silver_index"].endswith(
            "silver_index.json"
        )
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_progress_run_manifest_does_not_overwrite_canonical_run_manifest() -> None:
    scratch = _scratch_dir("progress_run_manifest_separation")
    shutil.rmtree(scratch, ignore_errors=True)
    try:
        run_dir = scratch / "run"
        run_dir.mkdir(parents=True, exist_ok=True)
        canonical_manifest = StrategyLadderRunManifest(
            run_id="canonical-run",
            workflow_run_id="workflow-demo",
            phase_run_id="phase_b2-final",
            output_root=str(run_dir.resolve()),
            final_status="STRATEGY_LADDER_BLOCKED_BY_NO_EXECUTED_TRADES",
            raw_window_extraction_status="RAW_WINDOW_READY",
            detailed_replay_status="DETAILED_REPLAY_READY",
        )
        (run_dir / "run_manifest.json").write_text(
            json.dumps(canonical_manifest.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )

        progress_manifest = StrategyLadderRunManifest(
            run_id="canonical-run",
            workflow_run_id="workflow-demo",
            phase_run_id="phase_b2-progress",
            output_root=str(run_dir.resolve()),
            final_status="STRATEGY_LADDER_BLOCKED_BY_RAW_WINDOWS",
            raw_window_extraction_status="RAW_WINDOW_NOT_PROVEN",
            detailed_replay_status="DETAILED_REPLAY_NOT_PROVEN",
        )
        _persist_progress_run_manifest(run_dir, progress_manifest)

        canonical_payload = json.loads(
            (run_dir / "run_manifest.json").read_text(encoding="utf-8")
        )
        progress_payload = json.loads(
            (run_dir / "run_manifest.progress.json").read_text(encoding="utf-8")
        )

        assert canonical_payload["phase_run_id"] == "phase_b2-final"
        assert canonical_payload["final_status"] == "STRATEGY_LADDER_BLOCKED_BY_NO_EXECUTED_TRADES"
        assert progress_payload["phase_run_id"] == "phase_b2-progress"
        assert progress_payload["final_status"] == "STRATEGY_LADDER_BLOCKED_BY_RAW_WINDOWS"
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_fast_only_b1_with_engine_native_mode_runs_native_materialization_and_preselection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scratch = _scratch_dir("b1_fast_only_engine_native")
    shutil.rmtree(scratch, ignore_errors=True)
    try:
        workflow_root = scratch / "workflow_root"
        a2_root = workflow_root / "phase_a2_data_factory"
        feature_root = a2_root / "gold"
        raw_root = scratch / "raw_root"
        b1_root = workflow_root / "phase_b1_candidate_discovery"
        workflow_manifest_path = workflow_root / "workflow_manifest.json"
        timestamp_ms = 1_711_929_600_000

        _write_json(
            a2_root / "data_factory_manifest.json",
            {
                "data_factory_status": "DATA_FACTORY_READY",
                "raw_source_status": "RAW_SOURCE_READY",
                "pair_universe_status": "PAIR_UNIVERSE_READY",
                "silver_index_status": "SILVER_INDEX_READY",
                "gold_feature_store_status": "FEATURE_STORE_READY",
            },
        )
        _write_json(a2_root / "raw_source_report.json", {"raw_source_status": "RAW_SOURCE_READY"})
        _write_json(a2_root / "pair_universe_report.json", {"pair_universe_status": "PAIR_UNIVERSE_READY"})
        _write_json(
            a2_root / "data_quality_report.json",
            {"orderbook_schema_status": "ORDERBOOK_SCHEMA_READY"},
        )
        _write_json(
            a2_root / "gold_feature_manifest.json",
            {"gold_feature_store_status": "FEATURE_STORE_READY", "feature_row_count": 1},
        )
        _write_jsonl(
            feature_root / "features.jsonl",
            [_feature_row(pair="BTCUSDT", engine_id="engine_a", timeframe="5m", timestamp_ms=timestamp_ms)],
        )
        _write_json(a2_root / "silver_index.json", {"status": "SILVER_INDEX_READY", "entries": []})
        raw_root.mkdir(parents=True, exist_ok=True)

        ensure_workflow_manifest(
            workflow_root=workflow_root,
            workflow_run_id="workflow-b1-fast-native",
            request_hash="workflow-b1-fast-native-hash",
            phase_id=PHASE_B1,
            pairs=("BTCUSDT",),
            start="2024-04-01",
            end="2024-04-01",
            ml_mode="ML_MODE_OFF",
            candidate_discovery_mode="FULL_DISCOVERY",
            engine_native_sample_size=25,
            engine_count=4,
            allow_broad_run=False,
            small_scope_enabled=False,
            full_scan_enabled=True,
            no_full_scan_enabled=False,
            silver_storage_mode_requested="jsonl_gz",
            silver_storage_mode_effective="jsonl_gz",
        )

        calls = {"extract": 0, "materialize": 0, "preselect": 0}

        def _fake_extract(*args: object, **kwargs: object) -> StrategyLadderRawWindowExtractionResult:
            calls["extract"] += 1
            manifest = StrategyLadderRawWindowManifest(
                candidate_id="candidate-engine-a",
                pair="BTCUSDT",
                engine_id="engine_a",
                strategy_id="engine_a",
                timestamp_ms=timestamp_ms,
                window_start_ms=timestamp_ms - 300_000,
                window_end_ms=timestamp_ms + 300_000,
                raw_trade_path=str((scratch / "raw_windows" / "trade.jsonl").resolve()),
                raw_book_path=str((scratch / "raw_windows" / "book.jsonl").resolve()),
                raw_book_delta_path=str((scratch / "raw_windows" / "book_delta.jsonl").resolve()),
                raw_ohlcv_path=str((scratch / "raw_windows" / "ohlcv.jsonl").resolve()),
                raw_metadata_path="",
                raw_sources_used=("raw_root_01",),
                book_depth_levels_available=20,
                book_depth_source_status="BOOK_DEPTH20_AVAILABLE",
                source_coverage_status="RAW_WINDOW_SOURCE_COVERAGE_COMPLETE",
                window_extraction_status="RAW_WINDOW_READY",
                input_data_hash="raw-window-hash",
                method_version_hash="strategy_ladder.gold.v1",
                artifact_hash="raw-window-artifact-hash",
            )
            return StrategyLadderRawWindowExtractionResult(
                status="RAW_WINDOW_READY",
                manifests=(manifest,),
                indexed_lookup_metrics=StrategyLadderWindowLookupMetrics(),
                window_cache_metrics=StrategyLadderWindowCacheMetrics(),
            )

        def _fake_materialize(
            *,
            candidate_events: tuple[StrategyLadderCandidateEvent, ...],
            **kwargs: object,
        ) -> strategy_ladder_runner_module._EngineNativeCandidateMaterialization:
            calls["materialize"] += 1
            source_event = candidate_events[0]
            payload = dict(source_event.compatibility_payload or {})
            payload.update(
                {
                    "engine_native_builder_status": "ENGINE_A_INPUT_BUILDER_READY",
                    "engine_native_decision": "emit",
                    "engine_native_reason_codes": [],
                    "engine_native_no_trade_reasons": [],
                    "expected_edge_provenance": "GOVERNED_ML_ARTIFACT_BACKTEST_TRUTH",
                    "hard_block_reasons": [],
                }
            )
            materialized = source_event.model_copy(
                update={
                    "candidate_source": "ENGINE_NATIVE",
                    "compatibility_payload": payload,
                    "preliminary_reason_codes": ("ENGINE_NATIVE_RUNNER_INVOKED",),
                }
            )
            return strategy_ladder_runner_module._EngineNativeCandidateMaterialization(
                candidate_events=(materialized,),
                candidate_discovery_status="CANDIDATE_DISCOVERY_ENGINE_NATIVE_READY",
                engine_native_status="ENGINE_NATIVE_FULL_PATH_READY",
                engine_native_records_built=12,
                engine_native_runner_invocation_count=1,
                expected_edge_proxy_count=0,
                expected_edge_governed_count=1,
                blocker_codes=(),
            )

        def _fake_preselect(
            *,
            run_dir: Path,
            materialized_candidate_events: tuple[StrategyLadderCandidateEvent, ...],
            **kwargs: object,
        ) -> StrategyLadderEngineNativePreselectionBuildResult:
            calls["preselect"] += 1
            preselection_candidates_path = run_dir / "preselection_candidates.jsonl"
            _write_jsonl(
                preselection_candidates_path,
                [json.loads(event.model_dump_json()) for event in materialized_candidate_events],
            )
            _write_json(
                run_dir / "reports" / "preselection_summary.json",
                {"status": "ENGINE_NATIVE_PRESELECTION_READY"},
            )
            _write_jsonl(run_dir / "preselection_rejection_ledger.jsonl", [])
            return StrategyLadderEngineNativePreselectionBuildResult(
                status="ENGINE_NATIVE_PRESELECTION_READY",
                preselection_candidates_path=str(preselection_candidates_path.resolve()),
                preselection_summary_path=str((run_dir / "reports" / "preselection_summary.json").resolve()),
                preselection_rejection_ledger_path=str((run_dir / "preselection_rejection_ledger.jsonl").resolve()),
                discovery_pre_candidate_count=1,
                engine_native_preselected_count=1,
                preselection_hard_rejected_count=0,
                preselection_soft_flagged_count=0,
                preselection_passed_count=1,
                b2_replay_candidate_count=1,
                preselection_rejection_count=0,
                replay_savings_estimate_count=0,
            )

        monkeypatch.setattr(strategy_ladder_runner_module, "extract_strategy_ladder_raw_windows", _fake_extract)
        monkeypatch.setattr(strategy_ladder_runner_module, "_materialize_engine_native_candidates", _fake_materialize)
        monkeypatch.setattr(
            strategy_ladder_runner_module,
            "build_strategy_ladder_engine_native_preselection",
            _fake_preselect,
        )

        result = run_backtest_strategy_ladder(
            StrategyLadderRequest(
                run_id="run-b1-fast-native",
                input_root=b1_root,
                feature_store_root=feature_root,
                raw_root=raw_root,
                output_root=b1_root,
                pairs=("BTCUSDT",),
                engines=("engine_a",),
                capital_buckets=(400,),
                timeframes=("5m",),
                start="2024-04-01",
                end="2024-04-01",
                fast_only=True,
                engine_native_mode=True,
                preselected_only=True,
                resume=False,
                workflow_run_id="workflow-b1-fast-native",
                phase_run_id="phase_b1-fast-native",
                parent_workflow_ref=str(workflow_manifest_path),
                engine_native_sample_size=25,
                candidate_discovery_mode="FULL_DISCOVERY",
                silver_index_path=a2_root / "silver_index.json",
                small_scope_enabled=False,
                full_scan_enabled=True,
                no_full_scan_enabled=False,
            )
        )

        assert calls == {"extract": 1, "materialize": 1, "preselect": 1}
        assert result.run_manifest.fast_only is True
        assert result.run_manifest.raw_window_extraction_status == "RAW_WINDOW_READY"
        assert result.run_manifest.engine_native_status == "ENGINE_NATIVE_FULL_PATH_READY"
        assert result.run_manifest.preselection_status == "ENGINE_NATIVE_PRESELECTION_READY"
        assert result.run_manifest.candidate_engine_native_count == 1
        assert result.run_manifest.engine_native_preselected_count == 1
        assert result.run_manifest.candidate_truth_status == "CANDIDATE_ENGINE_NATIVE_READY"
        assert result.run_manifest.replay_input_mode_status == "PRESELECTED_ONLY"
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_expected_edge_model_freshness_uses_replay_boundary() -> None:
    created_at = datetime(2026, 5, 8, tzinfo=UTC)
    replay_end = datetime(2025, 5, 8, tzinfo=UTC)

    assert _expected_edge_model_reference_at(
        created_at=created_at,
        end_ms=int(replay_end.timestamp() * 1000),
    ) == replay_end
    assert _expected_edge_model_reference_at(
        created_at=created_at,
        end_ms=None,
    ) == created_at


def test_candidate_discovery_ids_are_deterministic_and_compat_labeled() -> None:
    row = StrategyLadderFeatureRow.model_validate(_feature_row(pair="BTCUSDT", engine_id="engine_c"))

    status_a, candidates_a = discover_strategy_ladder_candidates(
        run_id="run-candidate-1",
        rows=(row,),
    )
    status_b, candidates_b = discover_strategy_ladder_candidates(
        run_id="run-candidate-1",
        rows=(row,),
    )

    assert status_a == "CANDIDATE_DISCOVERY_READY"
    assert status_b == "CANDIDATE_DISCOVERY_READY"
    assert candidates_a[0].candidate_id == candidates_b[0].candidate_id
    assert candidates_a[0].candidate_source == "COMPAT_FEATURE_DISCOVERY"
    assert "NOT_LIVE_ENGINE_PARITY" in candidates_a[0].preliminary_reason_codes
    assert candidates_a[0].strategy_id == "engine_c"


def test_candidate_discovery_ids_distinguish_timeframes_for_same_timestamp() -> None:
    row_1m = StrategyLadderFeatureRow.model_validate(
        _feature_row(
            pair="BTCUSDT",
            engine_id="engine_a",
            timeframe="1m",
            timestamp_ms=1_748_157_600_000,
        )
    )
    row_5m = StrategyLadderFeatureRow.model_validate(
        _feature_row(
            pair="BTCUSDT",
            engine_id="engine_a",
            timeframe="5m",
            timestamp_ms=1_748_157_600_000,
        )
    )

    status, candidates = discover_strategy_ladder_candidates(
        run_id="run-candidate-timeframe-split",
        rows=(row_1m, row_5m),
    )

    assert status == "CANDIDATE_DISCOVERY_READY"
    assert len(candidates) == 2
    assert candidates[0].candidate_id != candidates[1].candidate_id
    assert {candidate.timeframe for candidate in candidates} == {"1m", "5m"}


def test_raw_window_extraction_marks_limited_depth_and_missing_book_explicitly() -> None:
    scratch = _scratch_dir("raw_window_extraction")
    shutil.rmtree(scratch, ignore_errors=True)
    try:
        raw_root = scratch / "raw"
        _write_json(raw_root / "BTCUSDT" / "book_depth10.json", {"depth_levels": 10})
        _write_jsonl(raw_root / "BTCUSDT" / "trades.jsonl", [{"price": 1.0}])
        _write_csv(raw_root / "BTCUSDT" / "ohlcv.csv", "timestamp,open,high,low,close,volume", ["1,1,1,1,1,1"])
        _write_jsonl(raw_root / "ETHUSDT" / "trades.jsonl", [{"price": 1.0}])
        _write_csv(raw_root / "ETHUSDT" / "ohlcv.csv", "timestamp,open,high,low,close,volume", ["1,1,1,1,1,1"])

        candidates = (
            StrategyLadderCandidateEvent(
                run_id="run-raw-1",
                candidate_id="cand-btc",
                timestamp_ms=1_714_000_000_000,
                pair="BTCUSDT",
                timeframe="5m",
                engine_id="engine_a",
                strategy_id="engine_a",
            ),
            StrategyLadderCandidateEvent(
                run_id="run-raw-1",
                candidate_id="cand-eth",
                timestamp_ms=1_714_000_060_000,
                pair="ETHUSDT",
                timeframe="5m",
                engine_id="engine_b",
                strategy_id="engine_b",
            ),
        )

        status, manifests = extract_strategy_ladder_raw_windows(
            scratch / "raw_windows",
            candidate_events=candidates,
            raw_root=raw_root,
        )

        btc = {item.candidate_id: item for item in manifests}["cand-btc"]
        eth = {item.candidate_id: item for item in manifests}["cand-eth"]
        assert status == "RAW_WINDOW_PARTIAL"
        assert btc.book_depth_source_status == "BOOK_LIMITED_DEPTH_AVAILABLE"
        assert btc.window_extraction_status == "RAW_WINDOW_PARTIAL"
        assert eth.book_depth_source_status == "BOOK_DEPTH_MISSING"
        assert eth.window_extraction_status == "RAW_WINDOW_MISSING_BOOK"
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_raw_window_fallback_never_auto_proves_depth20() -> None:
    scratch = _scratch_dir("raw_window_fallback_no_depth20")
    shutil.rmtree(scratch, ignore_errors=True)
    try:
        raw_root = scratch / "raw"
        _write_json(raw_root / "BTCUSDT" / "book_depth20.json", {"depth_levels": 20})
        _write_jsonl(raw_root / "BTCUSDT" / "trades.jsonl", [{"price": 1.0}])
        _write_csv(
            raw_root / "BTCUSDT" / "ohlcv.csv",
            "timestamp,open,high,low,close,volume",
            ["1,1,1,1,1,1"],
        )

        candidate = StrategyLadderCandidateEvent(
            run_id="run-raw-fallback-1",
            candidate_id="cand-btc",
            timestamp_ms=1_714_000_000_000,
            pair="BTCUSDT",
            timeframe="5m",
            engine_id="engine_a",
            strategy_id="engine_a",
        )

        status, manifests = extract_strategy_ladder_raw_windows(
            scratch / "raw_windows",
            candidate_events=(candidate,),
            raw_root=raw_root,
        )

        manifest = manifests[0]
        assert status == "RAW_WINDOW_PARTIAL"
        assert manifest.book_depth_source_status == "BOOK_LIMITED_DEPTH_AVAILABLE"
        assert manifest.window_extraction_status == "RAW_WINDOW_PARTIAL"
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_raw_window_extraction_uses_silver_index_and_preserves_multi_source_lineage() -> None:
    scratch = _scratch_dir("raw_window_silver_index")
    shutil.rmtree(scratch, ignore_errors=True)
    try:
        silver_root = scratch / "silver"
        trades_path = silver_root / "bybit" / "spot" / "trades" / "BTCUSDT" / "2023" / "01" / "01.jsonl.gz"
        book_snapshot_path = silver_root / "bybit" / "spot" / "orderbook_snapshot" / "BTCUSDT" / "2023" / "01" / "01.jsonl.gz"
        book_delta_path = silver_root / "bybit" / "spot" / "orderbook_delta" / "BTCUSDT" / "2023" / "01" / "01.jsonl.gz"
        ohlcv_path = silver_root / "bybit" / "spot" / "ohlcv" / "5m" / "BTCUSDT" / "2023" / "01" / "01.jsonl.gz"
        metadata_path = silver_root / "metadata" / "symbol_filters.jsonl"
        _write_jsonl_gz(trades_path, [{"timestamp_ms": 1_714_000_000_000, "price": 1.0}])
        _write_jsonl_gz(book_snapshot_path, [{"timestamp_ms": 1_714_000_000_000, "depth_levels": 20}])
        _write_jsonl_gz(book_delta_path, [{"timestamp_ms": 1_714_000_010_000, "u": 2}])
        _write_jsonl_gz(ohlcv_path, [{"timestamp_ms": 1_714_000_000_000, "open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0}])
        _write_jsonl(metadata_path, [{"pair": "BTCUSDT", "min_notional": 10.0}])
        silver_index_path = scratch / "silver_index.json"
        _write_json(
            silver_index_path,
            {
                "schema_version": "v1",
                "entries": [
                    {
                        "source_id": "source_a",
                        "source_root": str((scratch / "raw_a").resolve()),
                        "source_priority": 10,
                        "exchange": "bybit",
                        "market_type": "spot",
                        "data_type": "trades",
                        "pair": "BTCUSDT",
                        "timeframe": "",
                        "date": "2023-01-01",
                        "path": str(trades_path.resolve()),
                        "storage_format": "jsonl_gz",
                        "min_timestamp_ms": 1_714_000_000_000,
                        "max_timestamp_ms": 1_714_000_060_000,
                        "row_count": 1,
                        "file_hash": "hash-trades",
                        "depth_source_status": "BOOK_DEPTH_NOT_PROVEN",
                        "schema_status": "TRADE_SCHEMA_READY",
                    },
                    {
                        "source_id": "source_b",
                        "source_root": str((scratch / "raw_b").resolve()),
                        "source_priority": 20,
                        "exchange": "bybit",
                        "market_type": "spot",
                        "data_type": "orderbook_snapshot",
                        "pair": "BTCUSDT",
                        "timeframe": "",
                        "date": "2023-01-01",
                        "path": str(book_snapshot_path.resolve()),
                        "storage_format": "jsonl_gz",
                        "min_timestamp_ms": 1_714_000_000_000,
                        "max_timestamp_ms": 1_714_000_060_000,
                        "row_count": 1,
                        "file_hash": "hash-book-snapshot",
                        "depth_source_status": "BOOK_DEPTH20_AVAILABLE",
                        "schema_status": "ORDERBOOK_SCHEMA_READY",
                    },
                    {
                        "source_id": "source_b",
                        "source_root": str((scratch / "raw_b").resolve()),
                        "source_priority": 20,
                        "exchange": "bybit",
                        "market_type": "spot",
                        "data_type": "orderbook_delta",
                        "pair": "BTCUSDT",
                        "timeframe": "",
                        "date": "2023-01-01",
                        "path": str(book_delta_path.resolve()),
                        "storage_format": "jsonl_gz",
                        "min_timestamp_ms": 1_714_000_000_000,
                        "max_timestamp_ms": 1_714_000_060_000,
                        "row_count": 1,
                        "file_hash": "hash-book-delta",
                        "depth_source_status": "BOOK_DEPTH20_AVAILABLE",
                        "schema_status": "ORDERBOOK_SCHEMA_READY",
                    },
                    {
                        "source_id": "source_a",
                        "source_root": str((scratch / "raw_a").resolve()),
                        "source_priority": 10,
                        "exchange": "bybit",
                        "market_type": "spot",
                        "data_type": "ohlcv",
                        "pair": "BTCUSDT",
                        "timeframe": "5m",
                        "date": "2023-01-01",
                        "path": str(ohlcv_path.resolve()),
                        "storage_format": "jsonl_gz",
                        "min_timestamp_ms": 1_714_000_000_000,
                        "max_timestamp_ms": 1_714_000_060_000,
                        "row_count": 1,
                        "file_hash": "hash-ohlcv",
                        "depth_source_status": "BOOK_DEPTH_NOT_PROVEN",
                        "schema_status": "KLINE_SCHEMA_READY",
                    },
                    {
                        "source_id": "source_meta",
                        "source_root": str((scratch / "raw_meta").resolve()),
                        "source_priority": 5,
                        "exchange": "bybit",
                        "market_type": "spot",
                        "data_type": "metadata",
                        "pair": "BTCUSDT",
                        "timeframe": "",
                        "date": "2023-01-01",
                        "path": str(metadata_path.resolve()),
                        "storage_format": "jsonl",
                        "min_timestamp_ms": 1_714_000_000_000,
                        "max_timestamp_ms": 1_714_000_060_000,
                        "row_count": 1,
                        "file_hash": "hash-meta",
                        "depth_source_status": "BOOK_DEPTH_NOT_PROVEN",
                        "schema_status": "METADATA_SCHEMA_READY",
                    },
                ],
            },
        )

        candidate = StrategyLadderCandidateEvent(
            run_id="run-indexed-1",
            candidate_id="cand-indexed",
            timestamp_ms=1_714_000_010_000,
            pair="BTCUSDT",
            timeframe="5m",
            engine_id="engine_a",
            strategy_id="engine_a",
        )

        status, manifests = extract_strategy_ladder_raw_windows(
            scratch / "raw_windows",
            candidate_events=(candidate,),
            silver_index_path=silver_index_path,
        )

        manifest = manifests[0]
        assert status == "RAW_WINDOW_READY"
        assert manifest.source_coverage_status == "RAW_WINDOW_SOURCE_COVERAGE_COMPLETE"
        assert manifest.trade_source_id == "source_a"
        assert manifest.book_snapshot_source_id == "source_b"
        assert manifest.book_delta_source_id == "source_b"
        assert manifest.metadata_source_id == "source_meta"
        assert manifest.raw_sources_used == ("source_a", "source_b", "source_meta")
        assert manifest.raw_trade_path is not None
        assert manifest.raw_book_path is not None
        assert manifest.raw_book_delta_path is not None
        assert manifest.raw_ohlcv_path is not None
        assert Path(manifest.raw_trade_path).name == "trades.jsonl"
        assert Path(manifest.raw_book_path).name == "orderbook_snapshot.jsonl"
        assert Path(manifest.raw_book_delta_path).suffix in {".jsonl", ".gz"}
        assert Path(manifest.raw_ohlcv_path).name == "ohlcv.jsonl"
        assert Path(manifest.raw_trade_path).read_text(encoding="utf-8").strip()
        assert Path(manifest.raw_book_path).read_text(encoding="utf-8").strip()
        assert _read_jsonl_any(Path(manifest.raw_book_delta_path))
        assert Path(manifest.raw_ohlcv_path).read_text(encoding="utf-8").strip()
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_raw_window_extraction_keeps_pre_window_snapshot_anchor_for_delta_replay() -> None:
    scratch = _scratch_dir("raw_window_snapshot_anchor")
    shutil.rmtree(scratch, ignore_errors=True)
    try:
        silver_root = scratch / "silver"
        trades_path = silver_root / "bybit" / "spot" / "trades" / "BTCUSDT" / "2023" / "01" / "01.jsonl.gz"
        book_snapshot_path = silver_root / "bybit" / "spot" / "orderbook_snapshot" / "BTCUSDT" / "2023" / "01" / "01.jsonl.gz"
        book_delta_path = silver_root / "bybit" / "spot" / "orderbook_delta" / "BTCUSDT" / "2023" / "01" / "01.jsonl.gz"
        ohlcv_path = silver_root / "bybit" / "spot" / "ohlcv" / "5m" / "BTCUSDT" / "2023" / "01" / "01.jsonl.gz"
        candidate_ts = 1_714_000_010_000
        _write_jsonl_gz(trades_path, [{"timestamp_ms": candidate_ts, "price": 1.0}])
        _write_jsonl_gz(
            book_snapshot_path,
            [{"timestamp_ms": candidate_ts - 120_000, "depth_levels": 20}],
        )
        _write_jsonl_gz(book_delta_path, [{"timestamp_ms": candidate_ts, "u": 2}])
        _write_jsonl_gz(ohlcv_path, [{"timestamp_ms": candidate_ts, "open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0}])

        silver_index_path = scratch / "silver_index.json"
        _write_json(
            silver_index_path,
            {
                "schema_version": "v1",
                "entries": [
                    {
                        "source_id": "source_trades",
                        "source_root": str((scratch / "raw_a").resolve()),
                        "source_priority": 10,
                        "exchange": "bybit",
                        "market_type": "spot",
                        "data_type": "trades",
                        "pair": "BTCUSDT",
                        "timeframe": "",
                        "date": "2023-01-01",
                        "path": str(trades_path.resolve()),
                        "storage_format": "jsonl_gz",
                        "min_timestamp_ms": candidate_ts,
                        "max_timestamp_ms": candidate_ts,
                        "row_count": 1,
                        "file_hash": "hash-trades",
                        "depth_source_status": "BOOK_DEPTH_NOT_PROVEN",
                        "schema_status": "TRADE_SCHEMA_READY",
                    },
                    {
                        "source_id": "source_book",
                        "source_root": str((scratch / "raw_b").resolve()),
                        "source_priority": 20,
                        "exchange": "bybit",
                        "market_type": "spot",
                        "data_type": "orderbook_snapshot",
                        "pair": "BTCUSDT",
                        "timeframe": "",
                        "date": "2023-01-01",
                        "path": str(book_snapshot_path.resolve()),
                        "storage_format": "jsonl_gz",
                        "min_timestamp_ms": candidate_ts - 120_000,
                        "max_timestamp_ms": candidate_ts + 60_000,
                        "row_count": 1,
                        "file_hash": "hash-book-snapshot",
                        "depth_source_status": "BOOK_DEPTH20_AVAILABLE",
                        "schema_status": "ORDERBOOK_SCHEMA_READY",
                    },
                    {
                        "source_id": "source_book",
                        "source_root": str((scratch / "raw_b").resolve()),
                        "source_priority": 20,
                        "exchange": "bybit",
                        "market_type": "spot",
                        "data_type": "orderbook_delta",
                        "pair": "BTCUSDT",
                        "timeframe": "",
                        "date": "2023-01-01",
                        "path": str(book_delta_path.resolve()),
                        "storage_format": "jsonl_gz",
                        "min_timestamp_ms": candidate_ts,
                        "max_timestamp_ms": candidate_ts,
                        "row_count": 1,
                        "file_hash": "hash-book-delta",
                        "depth_source_status": "BOOK_DEPTH20_AVAILABLE",
                        "schema_status": "ORDERBOOK_SCHEMA_READY",
                    },
                    {
                        "source_id": "source_ohlcv",
                        "source_root": str((scratch / "raw_c").resolve()),
                        "source_priority": 10,
                        "exchange": "bybit",
                        "market_type": "spot",
                        "data_type": "ohlcv",
                        "pair": "BTCUSDT",
                        "timeframe": "5m",
                        "date": "2023-01-01",
                        "path": str(ohlcv_path.resolve()),
                        "storage_format": "jsonl_gz",
                        "min_timestamp_ms": candidate_ts,
                        "max_timestamp_ms": candidate_ts,
                        "row_count": 1,
                        "file_hash": "hash-ohlcv",
                        "depth_source_status": "BOOK_DEPTH_NOT_PROVEN",
                        "schema_status": "KLINE_SCHEMA_READY",
                    },
                ],
            },
        )

        candidate = StrategyLadderCandidateEvent(
            run_id="run-anchor",
            candidate_id="cand-anchor",
            timestamp_ms=candidate_ts,
            pair="BTCUSDT",
            timeframe="5m",
            engine_id="engine_a",
            strategy_id="engine_a",
        )

        status, manifests = extract_strategy_ladder_raw_windows(
            scratch / "raw_windows",
            candidate_events=(candidate,),
            silver_index_path=silver_index_path,
        )

        manifest = manifests[0]
        assert status == "RAW_WINDOW_READY"
        assert manifest.raw_book_path is not None
        assert manifest.raw_book_delta_path is not None
        snapshot_rows = Path(manifest.raw_book_path).read_text(encoding="utf-8").strip().splitlines()
        delta_rows = [
            json.dumps(row)
            for row in _read_jsonl_any(Path(manifest.raw_book_delta_path))
        ]
        assert len(snapshot_rows) == 1
        assert len(delta_rows) == 1
        assert json.loads(snapshot_rows[0])["timestamp_ms"] == candidate_ts - 120_000
        assert json.loads(delta_rows[0])["timestamp_ms"] == candidate_ts
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_raw_window_linkage_summary_counts_missing_sources_explicitly() -> None:
    scratch = _scratch_dir("raw_window_linkage_summary")
    shutil.rmtree(scratch, ignore_errors=True)
    try:
        trade_path = scratch / "cand-a-trades.jsonl"
        book_path = scratch / "cand-a-book.jsonl"
        ohlcv_path = scratch / "cand-a-ohlcv.jsonl"
        _write_jsonl(trade_path, [{"timestamp_ms": 1_714_000_000_000, "price": 1.0}])
        _write_jsonl(book_path, [{"timestamp_ms": 1_714_000_000_000, "depth_levels": 20}])
        _write_jsonl(ohlcv_path, [{"timestamp_ms": 1_714_000_000_000, "open": 1.0}])
        candidates = (
            StrategyLadderCandidateEvent(
                run_id="run-linkage",
                candidate_id="cand-a",
                timestamp_ms=1_714_000_000_000,
                pair="BTCUSDT",
                timeframe="5m",
                engine_id="engine_a",
                strategy_id="engine_a",
            ),
            StrategyLadderCandidateEvent(
                run_id="run-linkage",
                candidate_id="cand-b",
                timestamp_ms=1_714_000_060_000,
                pair="BTCUSDT",
                timeframe="5m",
                engine_id="engine_b",
                strategy_id="engine_b",
            ),
        )
        manifests = (
            StrategyLadderRawWindowManifest(
                candidate_id="cand-a",
                pair="BTCUSDT",
                engine_id="engine_a",
                timestamp_ms=1_714_000_000_000,
                window_start_ms=1_714_000_000_000,
                window_end_ms=1_714_000_060_000,
                raw_trade_path=str(trade_path.resolve()),
                raw_book_path=str(book_path.resolve()),
                raw_ohlcv_path=str(ohlcv_path.resolve()),
                book_depth_levels_available=20,
                book_depth_source_status="BOOK_DEPTH20_AVAILABLE",
                window_extraction_status="RAW_WINDOW_READY",
                source_coverage_status="RAW_WINDOW_SOURCE_COVERAGE_COMPLETE",
            ),
            StrategyLadderRawWindowManifest(
                candidate_id="cand-b",
                pair="BTCUSDT",
                engine_id="engine_b",
                timestamp_ms=1_714_000_060_000,
                window_start_ms=1_714_000_030_000,
                window_end_ms=1_714_000_090_000,
                raw_trade_path=None,
                raw_book_path=None,
                raw_ohlcv_path=None,
                book_depth_levels_available=None,
                book_depth_source_status="BOOK_DEPTH_MISSING",
                window_extraction_status="RAW_WINDOW_NOT_PROVEN",
                source_coverage_status="RAW_WINDOW_SOURCE_NOT_PROVEN",
            ),
        )

        summary = _summarize_raw_window_linkage(
            candidate_events=candidates,
            raw_window_manifests=manifests,
        )

        assert summary == {
            "raw_windows_total": 2,
            "trade_windows_found": 1,
            "trade_windows_missing": 1,
            "book_windows_found": 1,
            "book_windows_missing": 1,
            "ohlcv_windows_found": 1,
            "ohlcv_windows_missing": 1,
            "depth20_found": 1,
            "depth20_missing": 1,
        }
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_strategy_ladder_request_rejects_training_mode() -> None:
    with pytest.raises(ValueError, match="forbids ML_MODE_TRAINING_LAB_ONLY"):
        StrategyLadderRequest(
            run_id="run-training-blocked",
            input_root=Path("input"),
            feature_store_root=Path("feature_store"),
            raw_root=Path("raw"),
            output_root=Path("output"),
            ml_mode="ML_MODE_TRAINING_LAB_ONLY",
        )


def test_detailed_replay_preserves_partial_fill_and_no_fill_without_zero_impact() -> None:
    scratch = _scratch_dir("detailed_replay")
    shutil.rmtree(scratch, ignore_errors=True)
    try:
        partial_candidate = StrategyLadderCandidateEvent(
            run_id="run-detailed-1",
            candidate_id="cand-partial",
            timestamp_ms=1_714_000_000_000,
            pair="BTCUSDT",
            timeframe="5m",
            engine_id="engine_c",
            strategy_id="engine_c",
            compatibility_payload=_feature_row(
                pair="BTCUSDT",
                engine_id="engine_c",
                fill_ratio=0.5,
                book_depth_levels=10,
                book_depth_source_status="BOOK_LIMITED_DEPTH_AVAILABLE",
            ),
        )
        no_fill_candidate = StrategyLadderCandidateEvent(
            run_id="run-detailed-1",
            candidate_id="cand-nofill",
            timestamp_ms=1_714_000_060_000,
            pair="ETHUSDT",
            timeframe="5m",
            engine_id="engine_d",
            strategy_id="engine_d",
            compatibility_payload=_feature_row(
                pair="ETHUSDT",
                engine_id="engine_d",
                fill_ratio=0.0,
                book_depth_levels=0,
                book_depth_source_status="BOOK_DEPTH_MISSING",
            ),
        )

        stage = run_strategy_ladder_detailed_replay(
            scratch / "detailed_replay",
            candidate_events=(partial_candidate, no_fill_candidate),
            raw_window_manifests=(),
            capital_buckets=(400,),
        )

        results = {
            item.candidate_id: item
            for item in stage.bucket_results_by_bucket[400]
        }
        assert stage.detailed_replay_status == "DETAILED_REPLAY_PARTIAL"
        assert results["cand-partial"].partial_fill_flag is True
        assert results["cand-partial"].book_depth_source_status == "BOOK_LIMITED_DEPTH_AVAILABLE"
        assert results["cand-nofill"].no_fill_flag is True
        assert results["cand-nofill"].impact_source_status == "IMPACT_SOURCE_MISSING"
        assert results["cand-nofill"].executed_only_net_return is None
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_strategy_ladder_dry_run_does_not_emit_fake_measured_artifacts() -> None:
    scratch = _scratch_dir("dry_run")
    shutil.rmtree(scratch, ignore_errors=True)
    try:
        input_root = scratch / "input"
        feature_root = input_root / "feature_store"
        _write_jsonl(feature_root / "features.jsonl", [_feature_row()])

        result = run_backtest_strategy_ladder(
            StrategyLadderRequest(
                run_id="run-dry-1",
                input_root=input_root,
                feature_store_root=feature_root,
                raw_root=input_root / "raw",
                output_root=scratch / "output",
                dry_run=True,
            )
        )

        run_dir = scratch / "output" / "backtest_strategy_ladder" / "run-dry-1"
        assert result.run_manifest.final_status == "STRATEGY_LADDER_READY_TO_RUN"
        assert (run_dir / "run_manifest.json").exists()
        assert not (run_dir / "fast_candidates" / "candidate_events.jsonl").exists()
        assert not (run_dir / "capital_profiles").exists()
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_strategy_ladder_detailed_replay_writes_compact_wrapper_and_loader_hydrates() -> None:
    scratch = _scratch_dir("compact_wrapper")
    shutil.rmtree(scratch, ignore_errors=True)
    try:
        detailed_root = scratch / "detailed_replay"
        raw_root = scratch / "raw"
        snapshot_path = raw_root / "orderbook_snapshot.jsonl"
        delta_path = raw_root / "orderbook_delta.jsonl"
        ohlcv_path = raw_root / "ohlcv.jsonl"
        _write_jsonl(
            snapshot_path,
            [
                {
                    "timestamp_ms": 1_713_999_999_000,
                    "update_id": 10,
                    "bids": [[99.9, 2.0], [99.8, 3.0]],
                    "asks": [[100.1, 2.0], [100.2, 3.0]],
                }
            ],
        )
        _write_jsonl(
            delta_path,
            [
                {
                    "timestamp_ms": 1_714_000_000_000,
                    "update_id": 11,
                    "bids": [[100.0, 2.0]],
                    "asks": [[100.1, 2.0]],
                }
            ],
        )
        _write_jsonl(
            ohlcv_path,
            [
                {
                    "timestamp_ms": 1_714_000_060_000,
                    "open": 100.0,
                    "high": 101.2,
                    "low": 99.7,
                    "close": 100.8,
                },
                {
                    "timestamp_ms": 1_714_000_120_000,
                    "open": 100.8,
                    "high": 101.8,
                    "low": 100.1,
                    "close": 101.1,
                },
            ],
        )
        candidate_payload = _feature_row()
        candidate_payload.update(
            {
                "side": "buy",
                "close_price": 100.0,
                "entry_price": 100.0,
            }
        )
        candidate = StrategyLadderCandidateEvent(
            run_id="run-compact",
            candidate_id="cand-compact",
            timestamp_ms=1_714_000_000_000,
            pair="BTCUSDT",
            timeframe="5m",
            engine_id="engine_a",
            strategy_id="engine_a",
            compatibility_payload=candidate_payload,
        )
        window_manifest = StrategyLadderRawWindowManifest(
            candidate_id="cand-compact",
            pair="BTCUSDT",
            engine_id="engine_a",
            timestamp_ms=1_714_000_000_000,
            window_start_ms=1_713_999_940_000,
            window_end_ms=1_714_000_600_000,
            raw_trade_path="",
            raw_book_path=str(snapshot_path),
            raw_book_delta_path=str(delta_path),
            raw_ohlcv_path=str(ohlcv_path),
        )

        stage = run_strategy_ladder_detailed_replay(
            detailed_root,
            candidate_events=(candidate,),
            raw_window_manifests=(window_manifest,),
            capital_buckets=(400, 500),
        )

        wrapper_path = detailed_root / "cand-compact.json"
        wrapper_payload = json.loads(wrapper_path.read_text(encoding="utf-8"))
        assert wrapper_payload["bucket_results"] == []
        assert len(wrapper_payload["bucket_result_summary"]) == 2
        assert wrapper_payload["shared_payload_ref"]
        assert stage.performance_metrics.cache_hits_book_state >= 3
        assert stage.performance_metrics.cache_hits_ohlcv >= 1

        hydrated = load_strategy_ladder_detailed_replay_artifact(wrapper_path)
        assert len(hydrated.bucket_results) == 2
        for result in hydrated.bucket_results:
            assert result.parity_payload["measured_spread_report"]["status"] == (
                "SPREAD_MEASURED_FROM_BOOK"
            )
            assert result.parity_payload["replay_outcome_report"]["status"] == (
                "REPLAY_OUTCOME_RESEARCH_ONLY"
            )
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_strategy_ladder_detailed_replay_loader_supports_legacy_embedded_bucket_results() -> None:
    scratch = _scratch_dir("legacy_wrapper_loader")
    shutil.rmtree(scratch, ignore_errors=True)
    try:
        replay_root = scratch / "detailed_replay"
        replay_root.mkdir(parents=True, exist_ok=True)
        result = StrategyLadderBucketReplayResult(
            candidate_id="cand-legacy",
            pair="BTCUSDT",
            engine_id="engine_a",
            strategy_id="engine_a",
            capital_bucket=400,
            timestamp_ms=1_714_000_000_000,
            execution_state="executed",
            expected_ce_net=0.001,
            parity_payload={"legacy_field": "kept"},
        )
        artifact = StrategyLadderDetailedReplayArtifact(
            candidate_id="cand-legacy",
            pair="BTCUSDT",
            engine_id="engine_a",
            strategy_id="engine_a",
            timestamp_ms=1_714_000_000_000,
            detailed_replay_status="DETAILED_REPLAY_READY",
            bucket_results=(result,),
            bucket_result_refs=(),
        )
        path = replay_root / "cand-legacy.json"
        path.write_text(artifact.model_dump_json(indent=2), encoding="utf-8")

        loaded = load_strategy_ladder_detailed_replay_artifact(path)
        assert len(loaded.bucket_results) == 1
        assert loaded.bucket_results[0].parity_payload["legacy_field"] == "kept"
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_strategy_ladder_missing_feature_store_blocks_run() -> None:
    scratch = _scratch_dir("missing_feature_store")
    shutil.rmtree(scratch, ignore_errors=True)
    try:
        input_root = scratch / "input"

        result = run_backtest_strategy_ladder(
            StrategyLadderRequest(
                run_id="run-missing-fs",
                input_root=input_root,
                feature_store_root=input_root / "feature_store",
                raw_root=input_root / "raw",
                output_root=scratch / "output",
            )
        )

        assert result.run_manifest.feature_store_status == "FEATURE_STORE_MISSING"
        assert result.run_manifest.final_status == "STRATEGY_LADDER_BLOCKED_BY_FEATURE_STORE"
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_strategy_ladder_runner_builds_bucket_profiles_without_small_bucket_universe_inheritance() -> None:
    scratch = _scratch_dir("bucket_profiles")
    shutil.rmtree(scratch, ignore_errors=True)
    try:
        input_root = scratch / "input"
        feature_root = input_root / "feature_store"
        raw_root = input_root / "raw"
        _write_jsonl(
            feature_root / "features.jsonl",
            [
                _feature_row(pair="BTCUSDT", allocation_fraction=0.20, min_notional=50.0),
                _feature_row(
                    pair="ETHUSDT",
                    timestamp_ms=1_714_000_060_000,
                    engine_id="engine_b",
                    allocation_fraction=0.90,
                    min_notional=500.0,
                ),
            ],
        )
        _write_json(raw_root / "BTCUSDT" / "book_depth20.json", {"depth_levels": 20})
        _write_json(raw_root / "ETHUSDT" / "book_depth20.json", {"depth_levels": 20})
        _write_jsonl(raw_root / "BTCUSDT" / "trades.jsonl", [{"price": 1.0}])
        _write_jsonl(raw_root / "ETHUSDT" / "trades.jsonl", [{"price": 1.0}])
        _write_csv(raw_root / "BTCUSDT" / "ohlcv.csv", "timestamp,open,high,low,close,volume", ["1,1,1,1,1,1"])
        _write_csv(raw_root / "ETHUSDT" / "ohlcv.csv", "timestamp,open,high,low,close,volume", ["1,1,1,1,1,1"])

        result = run_backtest_strategy_ladder(
            StrategyLadderRequest(
                run_id="run-buckets-1",
                input_root=input_root,
                feature_store_root=feature_root,
                raw_root=raw_root,
                output_root=scratch / "output",
                capital_buckets=(400, 500, 1500, 4000),
            )
        )

        profiles = {item.capital_bucket: item for item in result.capital_profiles}
        assert profiles[400].pair_universe == ("BTCUSDT",)
        assert set(profiles[4000].pair_universe) == {"BTCUSDT", "ETHUSDT"}
        assert profiles[400].allowed_pairs == ()
        assert profiles[400].promotion_status != "CAPITAL_BUCKET_READY"
        assert profiles[400].run_id == "run-buckets-1"
        assert profiles[400].strategy_ladder_manifest_ref
        assert profiles[400].expires_at is not None
        assert profiles[4000].executed_only_net_return_status in {
            "EXECUTED_NET_RETURN_NOT_PROVEN",
            "EXECUTED_NET_RETURN_PROVEN",
        }
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_post_b2_refusal_audit_prefers_engine_specific_non_build14_reasons() -> None:
    common_reason_codes = {
        "BREAK_EVEN_PROXY_BLOCKED",
        "ENGINE_NATIVE_NO_TRADE",
        "EXPECTED_EDGE_NOT_GOVERNED_FOR_BACKTEST_TRUTH",
        "EXPECTED_EDGE_PROXY_BLOCKED",
        "FEE_AWARE_EDGE_PROXY_BLOCKED",
    }

    engine_c_reason_counts = _select_engine_specific_reason_counts(
        reason_counter=Counter(
            {
                "BREAK_EVEN_PROXY_BLOCKED": 1000,
                "BUILD14_APPLIED:DATA_FRESHNESS": 1000,
                "BUILD14_READER:execution_fragility_score:ELEVATED": 1000,
                "engine_c.microstructure.not_applied": 1000,
                "engine_c.breakout.structured_breakout": 1000,
                "engine_c.continuation.fresh_breakout": 1000,
            }
        ),
        common_reason_codes=common_reason_codes,
    )
    engine_c_codes = tuple(code for code, _ in engine_c_reason_counts[:4])
    assert "engine_c.microstructure.not_applied" in engine_c_codes
    assert "BREAK_EVEN_PROXY_BLOCKED" not in engine_c_codes
    assert "BUILD14_APPLIED:DATA_FRESHNESS" not in engine_c_codes
    engine_c_assessment = _blocker_assessment(engine_c_codes)
    assert engine_c_assessment["assessment"] == "SUSPECTED_WIRING_ISSUE"
    assert engine_c_assessment["classification"] == "microstructure"

    engine_d_reason_counts = _select_engine_specific_reason_counts(
        reason_counter=Counter(
            {
                "BREAK_EVEN_PROXY_BLOCKED": 1000,
                "BUILD14_APPLIED:DATA_FRESHNESS": 1000,
                "ENGINE_D_HISTORY_BLOCKED_BY_MISSING_CLOSED_EPISODE_JOURNAL": 1000,
                "engine_d.no_trade.history_weak": 1000,
                "history_weak": 1000,
            }
        ),
        common_reason_codes=common_reason_codes,
    )
    engine_d_codes = tuple(code for code, _ in engine_d_reason_counts[:4])
    assert "ENGINE_D_HISTORY_BLOCKED_BY_MISSING_CLOSED_EPISODE_JOURNAL" in engine_d_codes
    assert "BREAK_EVEN_PROXY_BLOCKED" not in engine_d_codes
    engine_d_assessment = _blocker_assessment(engine_d_codes)
    assert engine_d_assessment["assessment"] == "SUSPECTED_WIRING_ISSUE"
    assert engine_d_assessment["classification"] == "history"
    cold_start_assessment = _blocker_assessment(
        ("ENGINE_D_COLD_START_NO_CLOSED_EPISODE_SOURCE",)
    )
    assert cold_start_assessment["assessment"] == "HEALTHY_ENGINE_D_COLD_START_BLOCKER"
    assert cold_start_assessment["classification"] == "history"


def test_engine_d_missing_closed_episode_journal_is_classified_explicitly() -> None:
    scratch = _scratch_dir("engine_d_no_trade_diagnosis")
    try:
        diagnosis = _build_engine_d_diagnosis(
            candidate_rows=[
                {
                    "engine_id": "engine_d",
                    "candidate_id": "cand-d",
                    "timestamp_ms": 1,
                    "pair": "BTCUSDT",
                    "timeframe": "5m",
                    "compatibility_payload": {
                        "engine_native_builder_status": "ENGINE_D_INPUT_BUILDER_READY_NO_FIRST_EPISODE",
                        "engine_native_input_provenance": "BUILDER_NO_FIRST_EPISODE_DEFAULTS",
                    },
                }
            ],
            reason_counter=Counter(
                {
                    "ENGINE_D_HISTORY_BLOCKED_BY_MISSING_CLOSED_EPISODE_JOURNAL": 1,
                    "engine_d.no_trade.history_weak": 1,
                }
            ),
            common_reason_codes={
                "ENGINE_NATIVE_NO_TRADE",
                "EXPECTED_EDGE_PROXY_BLOCKED",
            },
            workflow_root=scratch,
        )

        assert diagnosis["closed_episode_journal_status"] == "CLOSED_EPISODE_JOURNAL_NOT_GENERATED"
        assert diagnosis["engine_d_history_input_status"] == "REQUIRED_FOR_ENGINE_D_BUT_NOT_AVAILABLE_IN_B2"
        assert diagnosis["first_episode_ref_status"] == "FIRST_EPISODE_REF_MISSING"
        assert diagnosis["closed_episode_source_status"] == "REQUIRED_FOR_ENGINE_D_BUT_NO_VALID_EPISODE_SOURCE"
        assert diagnosis["reentry_age_status"] == "REENTRY_AGE_BLOCKED_BY_MISSING_FIRST_EPISODE"
        assert "ENGINE_D_COLD_START_NO_CLOSED_EPISODE_SOURCE" in diagnosis["suspected_wiring_gaps"]
        assert diagnosis["recommended_next_action"] == "PROVIDE_REAL_CLOSED_EPISODE_SOURCE_FOR_ENGINE_D"
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_engine_d_empty_closed_episode_journal_is_not_classified_as_missing_journal() -> None:
    scratch = _scratch_dir("engine_d_empty_closed_episode_journal")
    try:
        scratch.mkdir(parents=True, exist_ok=True)
        manifest_path = scratch / "closed_episode_manifest.json"
        manifest_path.write_text(
            json.dumps(
                {
                    "status": "CLOSED_EPISODE_JOURNAL_EMPTY_NO_VALID_EPISODES",
                    "path": str((scratch / "closed_episodes.jsonl").resolve()),
                    "record_count": 0,
                    "source_status": "REQUIRED_FOR_ENGINE_D_BUT_NO_VALID_EPISODE_SOURCE",
                },
                indent=2,
            ),
            encoding="utf-8",
        )

        diagnosis = _build_engine_d_diagnosis(
            candidate_rows=[
                {
                    "engine_id": "engine_d",
                    "candidate_id": "cand-d-empty",
                    "timestamp_ms": 1,
                    "pair": "BTCUSDT",
                    "timeframe": "5m",
                    "compatibility_payload": {
                        "engine_native_builder_status": "ENGINE_D_INPUT_BUILDER_READY_NO_FIRST_EPISODE",
                    },
                }
            ],
            reason_counter=Counter(
                {
                    "ENGINE_D_HISTORY_BLOCKED_BY_MISSING_CLOSED_EPISODE_JOURNAL": 1,
                    "engine_d.no_trade.history_weak": 1,
                }
            ),
            common_reason_codes={
                "ENGINE_NATIVE_NO_TRADE",
                "EXPECTED_EDGE_PROXY_BLOCKED",
            },
            workflow_root=scratch,
        )

        assert diagnosis["closed_episode_journal_status"] == "CLOSED_EPISODE_JOURNAL_EMPTY_NO_VALID_EPISODES"
        assert diagnosis["engine_d_history_input_status"] == "REQUIRED_FOR_ENGINE_D_BUT_NO_VALID_EPISODE_SOURCE"
        assert diagnosis["recommended_next_action"] == "PRODUCE_VALID_CLOSED_EPISODES_BEFORE_EVALUATING_ENGINE_D"
        assert "ENGINE_D_HISTORY_BLOCKED_BY_MISSING_CLOSED_EPISODE_JOURNAL" not in diagnosis["suspected_wiring_gaps"]
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_engine_c_feature_present_but_not_consumed_is_distinguished_from_missing() -> None:
    common_reason_codes = {
        "ENGINE_NATIVE_NO_TRADE",
        "EXPECTED_EDGE_PROXY_BLOCKED",
    }
    gold_manifest_payload = {
        "feature_groups_ready": ["ofi_features", "queue_pressure", "vpin_features", "spread_features", "depth_features"]
    }

    present_not_consumed = _build_engine_c_diagnosis(
        candidate_rows=[
            {
                "engine_id": "engine_c",
                "candidate_id": "cand-c-present",
                "timestamp_ms": 1,
                "pair": "BTCUSDT",
                "timeframe": "5m",
                "compatibility_payload": {
                    "cumulative_ofi": 1.2,
                    "queue_pressure": 0.4,
                    "vpin": 0.22,
                    "spread_bps": 0.5,
                    "book_depth_levels": 20,
                    "build14_shadow_activation_status": "BUILD14_SHADOW_ENABLED_ACTIVE",
                    "build14_shadow_reason_codes": [
                        "BUILD14_READER:execution_fragility_score:ELEVATED",
                        "BUILD14_READER:false_breakout_model:ELEVATED",
                    ],
                },
            }
        ],
        reason_counter=Counter(
            {
                "engine_c.microstructure.not_applied": 1,
                "engine_c.breakout.structured_breakout": 1,
            }
        ),
        common_reason_codes=common_reason_codes,
        gold_manifest_payload=gold_manifest_payload,
    )
    assert present_not_consumed["engine_c_microstructure_consumption_status"] == "ENGINE_C_MICROSTRUCTURE_PRESENT_BUT_NOT_CONSUMED"
    assert present_not_consumed["vpin_context_status"] == "VPIN_PRESENT_IN_REPLAY_PAYLOAD"
    assert present_not_consumed["fragility_context_status"] == "FRAGILITY_PRESENT_IN_REPLAY_PAYLOAD"
    assert present_not_consumed["fragility_block_status"] == "FRAGILITY_NOT_PROVEN"

    missing_from_payload = _build_engine_c_diagnosis(
        candidate_rows=[
            {
                "engine_id": "engine_c",
                "candidate_id": "cand-c-missing",
                "timestamp_ms": 1,
                "pair": "BTCUSDT",
                "timeframe": "5m",
                "compatibility_payload": {
                    "spread_bps": 0.5,
                    "book_depth_levels": 20,
                    "build14_shadow_activation_status": "BUILD14_SHADOW_ENABLED_ACTIVE",
                },
            }
        ],
        reason_counter=Counter(
            {
                "engine_c.microstructure.not_applied": 1,
                "engine_c.breakout.structured_breakout": 1,
            }
        ),
        common_reason_codes=common_reason_codes,
        gold_manifest_payload=gold_manifest_payload,
    )
    assert missing_from_payload["engine_c_microstructure_consumption_status"] == "ENGINE_C_MICROSTRUCTURE_MISSING_FROM_REPLAY_PAYLOAD"
    assert missing_from_payload["vpin_context_status"] == "VPIN_GROUP_READY_BUT_MISSING_FROM_REPLAY_PAYLOAD"

    consumed_but_fragile = _build_engine_c_diagnosis(
        candidate_rows=[
            {
                "engine_id": "engine_c",
                "candidate_id": "cand-c-fragile",
                "timestamp_ms": 1,
                "pair": "BTCUSDT",
                "timeframe": "5m",
                "compatibility_payload": {
                    "cumulative_ofi": 1.2,
                    "queue_pressure": 0.4,
                    "vpin": 0.22,
                    "spread_bps": 0.5,
                    "book_depth_levels": 20,
                    "build14_shadow_reason_codes": [
                        "BUILD14_READER:execution_fragility_score:ELEVATED",
                    ],
                },
            }
        ],
        reason_counter=Counter(
            {
                "engine_c.breakout.structured_breakout": 1,
            }
        ),
        common_reason_codes=common_reason_codes,
        gold_manifest_payload=gold_manifest_payload,
    )
    assert consumed_but_fragile["engine_c_microstructure_consumption_status"] == "ENGINE_C_MICROSTRUCTURE_CONSUMED_BUT_BLOCKED_BY_FRAGILITY"


def test_engine_c_with_no_b2_candidates_is_classified_as_upstream_preselection() -> None:
    diagnosis = _build_engine_c_diagnosis(
        candidate_rows=[],
        reason_counter=Counter(),
        common_reason_codes={
            "ENGINE_NATIVE_NO_TRADE",
            "EXPECTED_EDGE_PROXY_BLOCKED",
        },
        gold_manifest_payload={
            "feature_groups_ready": [
                "ofi_features",
                "queue_pressure",
                "vpin_features",
                "spread_features",
                "depth_features",
            ]
        },
    )

    assert diagnosis["engine_c_microstructure_input_status"] == "ENGINE_C_NOT_PRESENT_IN_B2"
    assert diagnosis["first_blocking_layer"] == "upstream_preselection"
    assert diagnosis["suspected_wiring_gaps"] == ()
    assert diagnosis["recommended_next_action"] == "AUDIT_ENGINE_C_B1_BREAKOUT_ELIGIBILITY"


def test_engine_ab_direction_cost_diagnosis_counts_non_long_without_forcing_trade() -> None:
    diagnosis = _build_engine_ab_direction_cost_diagnosis(
        engine_id="engine_a",
        candidate_rows=[
            {
                "engine_id": "engine_a",
                "candidate_id": "cand-a",
                "timestamp_ms": 1,
                "pair": "BTCUSDT",
                "timeframe": "5m",
                "compatibility_payload": {
                    "engine_native_reason_codes": [
                        "engine_internal.engine_a.direction.non_long",
                        "engine_a.input.non_long_direction",
                    ]
                },
            }
        ],
        refusal_rows=[
            {
                "reason_codes": [
                    "engine_internal.engine_a.direction.non_long",
                    "engine_a.input.non_long_direction",
                    "non_long_direction",
                ]
            },
            {
                "reason_codes": [
                    "cost_infeasible",
                    "engine_a.cost.break_even_not_cleared",
                ]
            },
            {
                "reason_codes": [
                    "engine_a.structure.unfavorable",
                ]
            },
        ],
        reason_counter=Counter(
            {
                "engine_internal.engine_a.direction.non_long": 5,
                "engine_a.input.non_long_direction": 5,
                "non_long_direction": 5,
                "cost_infeasible": 3,
                "engine_a.cost.break_even_not_cleared": 3,
                "engine_a.structure.unfavorable": 2,
            }
        ),
        common_reason_codes={
            "ENGINE_NATIVE_NO_TRADE",
            "EXPECTED_EDGE_PROXY_BLOCKED",
            "BREAK_EVEN_PROXY_BLOCKED",
            "FEE_AWARE_EDGE_PROXY_BLOCKED",
        },
    )

    aggregated = diagnosis["aggregated_blocker_counts"]
    assert aggregated["non_long_direction"] == 1
    assert aggregated["cost_infeasible"] == 1
    assert aggregated["break_even_not_cleared"] == 1
    assert aggregated["structure_unfavorable"] == 1
    assert diagnosis["long_only_filter_status"] == "LONG_ONLY_GOVERNANCE_BLOCKED_NON_LONG_CONTEXT"
    assert diagnosis["direction_mapping_status"] != "ENGINE_A_B_DIRECTION_MAPPING_NOT_PROVEN"
    assert diagnosis["suspected_wiring_gaps"] == ()


def test_engine_no_trade_diagnosis_payload_blocks_profitability_claim() -> None:
    scratch = _scratch_dir("engine_no_trade_payload")
    try:
        run_dir = scratch / "run"
        _write_jsonl(
            run_dir / "fast_candidates" / "candidate_events.jsonl",
            [
                {
                    "candidate_id": "cand-a",
                    "timestamp_ms": 1,
                    "pair": "BTCUSDT",
                    "timeframe": "5m",
                    "engine_id": "engine_a",
                    "compatibility_payload": {
                        "engine_native_reason_codes": [
                            "engine_internal.engine_a.direction.non_long"
                        ]
                    },
                }
            ],
        )
        _write_jsonl(
            run_dir / "refusal_ledger.jsonl",
            [
                {
                    "candidate_id": "cand-a",
                    "engine_id": "engine_a",
                    "capital_bucket": 400,
                    "execution_state": "hard_blocked",
                    "reason_codes": [
                        "ENGINE_NATIVE_NO_TRADE",
                        "EXPECTED_EDGE_PROXY_BLOCKED",
                        "FEE_AWARE_EDGE_PROXY_BLOCKED",
                        "BREAK_EVEN_PROXY_BLOCKED",
                        "engine_internal.engine_a.direction.non_long",
                        "non_long_direction",
                    ],
                }
            ],
        )
        _write_json(
            run_dir / "reports" / "engine_matrix.json",
            [
                {
                    "engine_id": "engine_a",
                    "record_count": 1,
                    "selected_count": 0,
                    "hard_blocked_count": 1,
                }
            ],
        )

        payload = _build_engine_no_trade_diagnosis_payload(
            summary=StrategyLadderReportSummary(
                run_id="run-diagnosis",
                workflow_run_id="run-diagnosis",
                phase_run_id="phase-b2",
                final_status="STRATEGY_LADDER_BLOCKED_BY_NO_EXECUTED_TRADES",
                candidate_count=1,
                engine_native_candidate_count=1,
                replay_record_count=1,
                executed_count=0,
                governed_evidence_status="EVIDENCE_AUDIT_NOT_CONFIRMED",
                run_manifest_evidence_class="SCRATCH_ONLY",
                refusal_ledger_evidence_class="SCRATCH_ONLY",
                sample_size_survival_evidence_class="SCRATCH_ONLY",
            ),
            run_manifest=StrategyLadderRunManifest(
                run_id="run-diagnosis",
                start="2025-05-03",
                end="2025-05-04",
                pairs=("BTCUSDT",),
            ),
            run_dir=run_dir,
            operator_artifact_refs={
                "refusal_ledger": str((run_dir / "refusal_ledger.jsonl").resolve())
            },
            gold_manifest_payload={},
        )

        assert payload["profitability_claim_allowed"] is False
        assert payload["profitability_claim_blocker"] == "SELECTED_COUNT_ZERO_NO_PROFITABILITY_CLAIM"
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_profitability_truth_verdict_requires_executions_and_proxy_free_path() -> None:
    blocked = _build_profitability_truth_verdict(
        summary=StrategyLadderReportSummary(
            run_id="run-profit-blocked",
            expected_edge_truth_status="EXPECTED_EDGE_PROXY_BLOCKED",
            expected_edge_proxy_count=1,
            executed_trade_count=0,
            execution_label_source="REPLAY_PROXY_EXECUTION",
            slippage_model_source="REPLAY_PROXY",
            blocker_codes=("NO_EXECUTED_TRADES",),
        ),
        run_manifest=StrategyLadderRunManifest(
            run_id="run-profit-blocked",
            blocker_codes=("NO_EXECUTED_TRADES",),
            executed_trade_count=0,
        ),
    )
    assert blocked["status"] == "PROFITABILITY_VERDICT_BLOCKED_NO_EXECUTED_TRADES"
    assert blocked["profitability_claim_allowed"] is False

    diagnostic = _build_profitability_truth_verdict(
        summary=StrategyLadderReportSummary(
            run_id="run-profit-diagnostic",
            expected_edge_truth_status="EXPECTED_EDGE_GOVERNED_BACKTEST_TRUTH",
            expected_edge_proxy_count=0,
            expected_edge_governed_count=80,
            executed_trade_count=80,
            execution_label_source="FULL_CANONICAL_EXECUTION",
            fee_model_source="CANONICAL",
            spread_model_source="CANONICAL",
            slippage_model_source="CANONICAL",
            partial_fill_model_source="CANONICAL",
            adverse_selection_source="CANONICAL",
        ),
        run_manifest=StrategyLadderRunManifest(
            run_id="run-profit-diagnostic",
            executed_trade_count=80,
        ),
    )
    assert diagnostic["status"] == "PROFITABILITY_VERDICT_DIAGNOSTIC_FRAGILE"
    assert diagnostic["proxy_blockers_present"] is False

    prod_candidate = _build_profitability_truth_verdict(
        summary=StrategyLadderReportSummary(
            run_id="run-profit-prod",
            expected_edge_truth_status="EXPECTED_EDGE_GOVERNED_BACKTEST_TRUTH",
            expected_edge_proxy_count=0,
            expected_edge_governed_count=120,
            executed_trade_count=120,
            execution_label_source="FULL_CANONICAL_EXECUTION",
            fee_model_source="CANONICAL",
            spread_model_source="CANONICAL",
            slippage_model_source="CANONICAL",
            partial_fill_model_source="CANONICAL",
            adverse_selection_source="CANONICAL",
        ),
        run_manifest=StrategyLadderRunManifest(
            run_id="run-profit-prod",
            executed_trade_count=120,
        ),
    )
    assert prod_candidate["status"] == "PROFITABILITY_VERDICT_PROD_CANDIDATE"
    assert prod_candidate["profitability_claim_allowed"] is True


def test_engine_no_trade_diagnosis_payload_uses_engine_specific_next_actions() -> None:
    scratch = _scratch_dir("engine_no_trade_payload_next_actions")
    try:
        run_dir = scratch / "run"
        _write_jsonl(
            run_dir / "fast_candidates" / "candidate_events.jsonl",
            [
                {
                    "candidate_id": "cand-d",
                    "timestamp_ms": 1,
                    "pair": "BTCUSDT",
                    "timeframe": "5m",
                    "engine_id": "engine_d",
                    "compatibility_payload": {
                        "engine_native_builder_status": "ENGINE_D_INPUT_BUILDER_READY_NO_FIRST_EPISODE",
                    },
                }
            ],
        )
        _write_jsonl(
            run_dir / "refusal_ledger.jsonl",
            [
                {
                    "candidate_id": "cand-d",
                    "engine_id": "engine_d",
                    "capital_bucket": 400,
                    "execution_state": "hard_blocked",
                    "reason_codes": [
                        "ENGINE_NATIVE_NO_TRADE",
                        "EXPECTED_EDGE_PROXY_BLOCKED",
                        "FEE_AWARE_EDGE_PROXY_BLOCKED",
                        "BREAK_EVEN_PROXY_BLOCKED",
                        "ENGINE_D_HISTORY_BLOCKED_BY_MISSING_CLOSED_EPISODE_JOURNAL",
                        "engine_d.no_trade.history_weak",
                    ],
                }
            ],
        )
        _write_json(
            run_dir / "reports" / "engine_matrix.json",
            [
                {
                    "engine_id": "engine_c",
                    "record_count": 0,
                    "selected_count": 0,
                    "hard_blocked_count": 0,
                },
                {
                    "engine_id": "engine_d",
                    "record_count": 1,
                    "selected_count": 0,
                    "hard_blocked_count": 1,
                },
            ],
        )
        _write_json(
            run_dir / "closed_episode_manifest.json",
            {
                "status": "CLOSED_EPISODE_JOURNAL_EMPTY_NO_VALID_EPISODES",
                "path": str((run_dir / "closed_episodes.jsonl").resolve()),
                "record_count": 0,
                "source_status": "REQUIRED_FOR_ENGINE_D_BUT_NO_VALID_EPISODE_SOURCE",
            },
        )

        payload = _build_engine_no_trade_diagnosis_payload(
            summary=StrategyLadderReportSummary(
                run_id="run-diagnosis-next-actions",
                workflow_run_id="run-diagnosis-next-actions",
                phase_run_id="phase-b2",
                final_status="STRATEGY_LADDER_BLOCKED_BY_NO_EXECUTED_TRADES",
                candidate_count=1,
                engine_native_candidate_count=1,
                replay_record_count=1,
                executed_count=0,
                governed_evidence_status="EVIDENCE_AUDIT_NOT_CONFIRMED",
                run_manifest_evidence_class="SCRATCH_ONLY",
                refusal_ledger_evidence_class="SCRATCH_ONLY",
                sample_size_survival_evidence_class="SCRATCH_ONLY",
            ),
            run_manifest=StrategyLadderRunManifest(
                run_id="run-diagnosis-next-actions",
                start="2025-05-03",
                end="2025-05-04",
                pairs=("BTCUSDT",),
            ),
            run_dir=run_dir,
            operator_artifact_refs={
                "refusal_ledger": str((run_dir / "refusal_ledger.jsonl").resolve())
            },
            gold_manifest_payload={
                "feature_groups_ready": [
                    "ofi_features",
                    "queue_pressure",
                    "vpin_features",
                    "spread_features",
                    "depth_features",
                ]
            },
        )

        ranking = {row["rank"]: row for row in payload["next_action_ranking"]}
        assert ranking["B"]["action"] == "PRODUCE_VALID_CLOSED_EPISODES_BEFORE_EVALUATING_ENGINE_D"
        assert ranking["C"]["action"] == "AUDIT_ENGINE_C_B1_BREAKOUT_ELIGIBILITY"
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_strategy_ladder_runner_feeds_engine_cd_promotion_artifacts() -> None:
    scratch = _scratch_dir("engine_cd")
    shutil.rmtree(scratch, ignore_errors=True)
    try:
        input_root = scratch / "input"
        feature_root = input_root / "feature_store"
        raw_root = input_root / "raw"
        _write_jsonl(
            feature_root / "features.jsonl",
            [
                _feature_row(pair="BTCUSDT", engine_id="engine_c"),
                _feature_row(
                    pair="ETHUSDT",
                    engine_id="engine_d",
                    timestamp_ms=1_714_000_060_000,
                    fill_ratio=0.5,
                    book_depth_levels=10,
                    book_depth_source_status="BOOK_LIMITED_DEPTH_AVAILABLE",
                ),
            ],
        )
        for pair in ("BTCUSDT", "ETHUSDT"):
            _write_json(raw_root / pair / "book_depth20.json", {"depth_levels": 20 if pair == "BTCUSDT" else 10})
            _write_jsonl(raw_root / pair / "trades.jsonl", [{"price": 1.0}])
            _write_csv(raw_root / pair / "ohlcv.csv", "timestamp,open,high,low,close,volume", ["1,1,1,1,1,1"])

        result = run_backtest_strategy_ladder(
            StrategyLadderRequest(
                run_id="run-engine-cd-1",
                input_root=input_root,
                feature_store_root=feature_root,
                raw_root=raw_root,
                output_root=scratch / "output",
                engines=("engine_c", "engine_d"),
                capital_buckets=(400,),
            )
        )

        engines = {item.engine_id: item for item in result.engine_promotion_artifacts}
        assert engines["engine_c"].shared_physics_mapping_status == "PARTIAL_BY_DESIGN"
        assert engines["engine_d"].shared_physics_mapping_status == "PARTIAL_BY_DESIGN"
        assert engines["engine_c"].engine_c is not None
        assert engines["engine_d"].engine_d is not None
        # Audit 2026-05-06 — la gate _stage_final_status bloque desormais
        # un run dont detailed_replay_count > 0 mais executed_trade_count
        # == 0 (cas typique de la fixture COMPAT_FEATURE_DISCOVERY qui ne
        # produit jamais de trades reels). BLOCKED_BY_NO_EXECUTED_TRADES
        # est donc un statut attendu tant que le rail proxy reste actif.
        assert result.report_summary.final_status in {
            "STRATEGY_LADDER_RAN_WITH_PARTIAL_EVIDENCE",
            "STRATEGY_LADDER_MEASURED_ARTIFACTS_PRODUCED",
            "STRATEGY_LADDER_BLOCKED_BY_NO_EXECUTED_TRADES",
            "STRATEGY_LADDER_BLOCKED_BY_STATISTICAL_VALIDATION",
        }
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_strategy_ladder_build14_shadow_provenance_is_carried_into_detailed_replay() -> None:
    scratch = _scratch_dir("engine_cd_build14")
    shutil.rmtree(scratch, ignore_errors=True)
    try:
        build14_observation = {
            "cra_sterilization_rate": 0.8,
            "cra_alert_count": 2,
            "break_even_drift_alert": True,
            "edge_degraded_count": 2,
            "queue_backlog": 90,
            "stale_pair_count": 1,
            "ce_net": -0.001,
            "breakout_failure_rate": 0.9,
            "volume_support_ratio": 0.1,
            "vwa_absorption_ratio": 0.1,
            "ghost_liquidity_ratio": 0.8,
            "adverse_obi_pressure": 0.9,
            "hurst_exponent": 0.9,
            "competition_density": 0.8,
        }
        engine_c_candidate_payload = _feature_row(pair="BTCUSDT", engine_id="engine_c")
        for key, value in build14_observation.items():
            engine_c_candidate_payload["feature_values"][f"build14_{key}"] = value
        engine_c_application = apply_build14_shadow_context(
            engine_id="engine_c",
            candidate_id="cand-build14-c",
            pair="BTCUSDT",
            candidate_payload=engine_c_candidate_payload,
            engine_input_payload={
                "expected_gain": 0.002,
                "expected_cost": 0.0008,
                "regime_favorability": 0.8,
                "pair_health": 0.8,
                "data_freshness": 0.8,
                "flow_coherence": 0.8,
                "queue_pressure": -0.4,
                "volume_confirmation": 0.9,
                "retrace_risk": 0.2,
            },
        )
        assert engine_c_application.activation_status == "BUILD14_SHADOW_ENABLED_ACTIVE"
        assert engine_c_application.shadow_report.signal.influence_mode == "shadow_enabled"
        assert "expected_gain" in engine_c_application.applied_fields
        assert "flow_coherence" in engine_c_application.applied_fields

        engine_d_candidate_payload = _feature_row(
            pair="ETHUSDT",
            engine_id="engine_d",
            timestamp_ms=1_714_000_060_000,
            fill_ratio=0.5,
            book_depth_levels=10,
            book_depth_source_status="BOOK_LIMITED_DEPTH_AVAILABLE",
        )
        for key, value in build14_observation.items():
            engine_d_candidate_payload["feature_values"][f"build14_{key}"] = value
        engine_d_application = apply_build14_shadow_context(
            engine_id="engine_d",
            candidate_id="cand-build14-d",
            pair="ETHUSDT",
            candidate_payload=engine_d_candidate_payload,
            engine_input_payload={
                "expected_gain": 0.0018,
                "expected_cost": 0.0009,
                "regime_favorability": 0.7,
                "pair_health": 0.75,
                "data_freshness": 0.8,
                "flow_coherence": 0.7,
                "reformation_quality": 0.8,
            },
        )
        assert engine_d_application.shadow_report.signal.influence_mode == "shadow_enabled"
        assert engine_d_application.applied_fields

        engine_c_candidate_payload.update(
            {
                "build14_shadow_activation_status": engine_c_application.activation_status,
                "build14_shadow_observation": engine_c_application.observation_input.model_dump(
                    mode="json"
                ),
                "build14_shadow_report": engine_c_application.shadow_report.model_dump(
                    mode="json"
                ),
                "build14_shadow_applied_fields": engine_c_application.applied_fields,
                "build14_shadow_adjustment_factors": engine_c_application.adjustment_factors,
                "build14_shadow_reason_codes": engine_c_application.reason_codes,
            }
        )
        engine_d_candidate_payload.update(
            {
                "build14_shadow_activation_status": engine_d_application.activation_status,
                "build14_shadow_observation": engine_d_application.observation_input.model_dump(
                    mode="json"
                ),
                "build14_shadow_report": engine_d_application.shadow_report.model_dump(
                    mode="json"
                ),
                "build14_shadow_applied_fields": engine_d_application.applied_fields,
                "build14_shadow_adjustment_factors": engine_d_application.adjustment_factors,
                "build14_shadow_reason_codes": engine_d_application.reason_codes,
            }
        )
        stage = run_strategy_ladder_detailed_replay(
            scratch / "detailed_replay",
            candidate_events=(
                StrategyLadderCandidateEvent(
                    run_id="run-build14",
                    candidate_id="cand-build14-c",
                    timestamp_ms=1_714_000_000_000,
                    pair="BTCUSDT",
                    timeframe="5m",
                    engine_id="engine_c",
                    strategy_id="engine_c",
                    compatibility_payload=engine_c_candidate_payload,
                ),
                StrategyLadderCandidateEvent(
                    run_id="run-build14",
                    candidate_id="cand-build14-d",
                    timestamp_ms=1_714_000_060_000,
                    pair="ETHUSDT",
                    timeframe="5m",
                    engine_id="engine_d",
                    strategy_id="engine_d",
                    compatibility_payload=engine_d_candidate_payload,
                ),
            ),
            raw_window_manifests=(),
            capital_buckets=(400,),
        )

        assert stage.bucket_results_by_bucket[400]
        for result in stage.bucket_results_by_bucket[400]:
            assert result.parity_payload["build14_shadow_activation_status"] == (
                "BUILD14_SHADOW_ENABLED_ACTIVE"
            )
            assert result.parity_payload["build14_shadow_report"]["signal"]["influence_mode"] == (
                "shadow_enabled"
            )
            assert result.parity_payload["build14_shadow_applied_fields"]
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_strategy_ladder_detailed_replay_cannot_import_shadow_execution_simulator_directly() -> None:
    import local_replay_runtime.strategy_ladder_detailed_replay as detailed_replay_module

    source = inspect.getsource(detailed_replay_module)
    module_ast = ast.parse(source)
    direct_shadow_imports = []
    direct_shadow_calls = []
    evaluate_calls = 0

    for node in ast.walk(module_ast):
        if isinstance(node, ast.ImportFrom) and node.module == "local_replay_runtime.shadow_execution_simulator":
            direct_shadow_imports.append(node.module)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "local_replay_runtime.shadow_execution_simulator":
                    direct_shadow_imports.append(alias.name)
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id == "simulate_shadow_compatible_dtrs":
                direct_shadow_calls.append(func.id)
            elif isinstance(func, ast.Attribute) and func.attr == "simulate_shadow_compatible_dtrs":
                direct_shadow_calls.append(func.attr)
            elif isinstance(func, ast.Name) and func.id == "evaluate_replay_execution":
                evaluate_calls += 1

    assert direct_shadow_imports == []
    assert direct_shadow_calls == []
    assert evaluate_calls >= 1


def test_strategy_ladder_cost_parity_carries_partial_canonical_execution_sources() -> None:
    result = StrategyLadderBucketReplayResult(
        candidate_id="cand-parity",
        pair="BTCUSDT",
        engine_id="engine_c",
        strategy_id="engine_c",
        capital_bucket=400,
        timestamp_ms=1_714_000_000_000,
        cost_parity_status="REPLAY_LIVE_COST_PARITY_NOT_PROVEN",
        parity_payload={
            "execution_label_source": "PARTIAL_CANONICAL_EXECUTION",
            "fee_model_source": "REPLAY_PROXY",
            "spread_model_source": "CANONICAL_SPREAD_GUARD",
            "slippage_model_source": "CANONICAL_EXECUTION_BACKBONE",
            "partial_fill_model_source": "REPLAY_PROXY",
            "adverse_selection_source": "REPLAY_PROXY",
            "order_type_selection_source": "REPLAY_PROXY",
            "venue_constraints_source": "REPLAY_PROXY",
            "execution_fidelity_gap_codes": (
                "FEE_MODEL_PROXY",
                "PARTIAL_FILL_MODEL_PROXY",
                "ADVERSE_SELECTION_PROXY",
            ),
        },
    )

    parity = _build_cost_parity((result,))

    assert parity.execution_label_source == "PARTIAL_CANONICAL_EXECUTION"
    assert parity.spread_model_source == "CANONICAL_SPREAD_GUARD"
    assert parity.slippage_model_source == "CANONICAL_EXECUTION_BACKBONE"
    assert parity.fee_model_source == "REPLAY_PROXY"
    assert "PARTIAL_FILL_MODEL_PROXY" in parity.execution_fidelity_gap_codes


def test_strategy_ladder_runner_persists_raw_window_failure_report_on_partial_crash(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scratch = _scratch_dir("raw_window_failure_report")
    shutil.rmtree(scratch, ignore_errors=True)
    try:
        input_root = scratch / "input"
        feature_root = input_root / "feature_store"
        raw_root = input_root / "raw"
        _write_jsonl(feature_root / "features.jsonl", [_feature_row(pair="BTCUSDT")])
        _write_json(raw_root / "BTCUSDT" / "book_depth20.json", {"depth_levels": 20})
        _write_jsonl(raw_root / "BTCUSDT" / "trades.jsonl", [{"price": 1.0}])
        _write_csv(raw_root / "BTCUSDT" / "ohlcv.csv", "timestamp,open,high,low,close,volume", ["1,1,1,1,1,1"])

        def _crashing_extract(output_dir, **kwargs):
            extract_strategy_ladder_raw_windows(output_dir, **kwargs)
            raise RuntimeError("synthetic raw-window crash")

        def _unexpected_detailed(*args, **kwargs):
            raise AssertionError("detailed replay should be skipped after raw-window crash")

        monkeypatch.setattr(
            "local_replay_runtime.strategy_ladder_runner.extract_strategy_ladder_raw_windows",
            _crashing_extract,
        )
        monkeypatch.setattr(
            "local_replay_runtime.strategy_ladder_runner.run_strategy_ladder_detailed_replay",
            _unexpected_detailed,
        )

        result = run_backtest_strategy_ladder(
            StrategyLadderRequest(
                run_id="run-raw-window-crash-1",
                input_root=input_root,
                feature_store_root=feature_root,
                raw_root=raw_root,
                output_root=scratch / "output",
                capital_buckets=(400,),
            )
        )

        run_dir = scratch / "output" / "backtest_strategy_ladder" / "run-raw-window-crash-1"
        failure_report = json.loads(
            (run_dir / "raw_window_failure_report.json").read_text(encoding="utf-8")
        )
        assert failure_report["error_type"] == "RuntimeError"
        assert failure_report["raw_window_status"] == "RAW_WINDOW_PARTIAL"
        assert failure_report["raw_window_count"] == 1
        assert failure_report["raw_windows_total"] == 1
        assert failure_report["trade_windows_found"] == 1
        assert failure_report["trade_windows_missing"] == 0
        assert "RAW_WINDOW_EXTRACTION_FAILED" in failure_report["blocker_codes"]
        assert result.run_manifest.raw_window_extraction_status == "RAW_WINDOW_PARTIAL"
        assert result.run_manifest.detailed_replay_status == "DETAILED_REPLAY_NOT_PROVEN"
        assert "RAW_WINDOW_EXTRACTION_FAILED" in result.run_manifest.blocker_codes
        assert result.run_manifest.raw_window_count == 1
        assert result.run_manifest.raw_windows_total == 1
        assert result.run_manifest.trade_windows_found == 1
        assert result.run_manifest.book_windows_missing == 0
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
