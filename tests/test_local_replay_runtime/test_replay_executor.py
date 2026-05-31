"""Tests for the governed LOCAL_REPLAY session executor."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
from uuid import uuid4

import pytest

from backtest_artifact_import import (
    CapitalProfileBuildInput,
    build_capital_bucket_profile,
)
from interface_contracts import ProfileId, StrategyClassification
from local_replay_runtime import (
    ReplayBookDepthAvailability,
    ReplayCostParityEvidence,
    ReplayExecutionInput,
    ReplayFeeProvenance,
    ReplayFillRealismEvidence,
    ReplayImpactProvenance,
    ReplayRunManifest,
    build_replay_metrics_summary,
    execute_local_replay_export,
)
from meta_minimal.dtr_core.decision_state_encoder import DecisionState
from meta_minimal.dtr_core.dtr_record_builder import build_dtr
from tests.support_paths import repo_build_path


def _scratch_dir(name: str) -> Path:
    return repo_build_path("local_replay_executor_tests", f"{name}_{uuid4().hex}")


def _records():
    return (
        build_dtr(
            dtr_id="dtr-1",
            pair="BTCUSDT",
            engine_id="engine_a",
            decision_state=DecisionState.SELECTED,
            expected_cost=0.0010,
            realized_cost=0.0011,
            gross_return=0.0022,
            ce_expected=0.0006,
            runtime_mode="local_replay",
            input_source="local_replay",
            timestamp=1_700_000_000.0,
        ),
        build_dtr(
            dtr_id="dtr-2",
            pair="ETHUSDT",
            engine_id="engine_b",
            decision_state=DecisionState.HARD_BLOCKED,
            expected_cost=0.0014,
            realized_cost=0.0,
            gross_return=-0.0005,
            ce_expected=-0.0001,
            runtime_mode="local_replay",
            input_source="local_replay",
            timestamp=1_700_000_060.0,
        ),
    )


def test_build_replay_metrics_summary_aggregates_pairs_engines_and_drawdown():
    summary = build_replay_metrics_summary(_records(), total_opportunities=4)

    assert summary.total_records == 2
    assert summary.dtr_coverage == 0.5
    assert summary.selected_count == 1
    assert summary.executed_count == 0
    assert summary.hard_blocked_count == 1
    assert summary.ce_net == 0.0005
    assert summary.drawdown_proxy >= 0.0
    assert summary.fee_source_status == "FEE_SOURCE_NOT_PROVEN"
    assert summary.impact_source_status == "IMPACT_SOURCE_NOT_PROVEN"
    assert summary.cost_model_completeness_status == "COST_MODEL_PARTIAL_FEE_MISSING"
    assert "FEE_SOURCE_NOT_PROVEN" in summary.cost_readiness_reason_codes
    assert "IMPACT_SOURCE_NOT_PROVEN" in summary.cost_readiness_reason_codes
    assert summary.executed_only_net_return is None
    assert summary.executed_only_net_return_status == "EXECUTED_NET_RETURN_INSUFFICIENT_EXECUTIONS"
    assert summary.true_net_equity_max_drawdown is None
    assert summary.true_net_equity_drawdown_status == "TRUE_NET_EQUITY_DRAWDOWN_MISSING_CAPITAL"
    assert summary.replay_expected_cost_model_mean == summary.expected_cost_mean
    assert summary.pair_aggregates[0].pair == "BTCUSDT"
    assert summary.engine_aggregates[0].engine_id == "engine_a"
    assert summary.engine_aggregates[0].shared_physics_mapping_status == "NOT_APPLICABLE"
    assert summary.engine_aggregates[0].executed_count == 0
    assert summary.engine_aggregates[0].reduced_count == 0
    assert summary.engine_aggregates[0].rejected_count == 0
    assert summary.engine_aggregates[0].engine_executed_only_net_return is None
    assert summary.engine_aggregates[0].executed_only_net_return_status == "EXECUTED_NET_RETURN_INSUFFICIENT_EXECUTIONS"
    assert summary.engine_aggregates[0].engine_true_net_equity_max_drawdown is None
    assert summary.engine_aggregates[0].true_net_equity_drawdown_status == "TRUE_NET_EQUITY_DRAWDOWN_MISSING_CAPITAL"
    assert summary.engine_aggregates[0].promotion_status == "NOT_SHADOW_READY"
    assert sum(item.record_count for item in summary.pair_aggregates) == summary.total_records
    assert sum(item.record_count for item in summary.engine_aggregates) == summary.total_records
    assert sum(item.ce_net for item in summary.pair_aggregates) == pytest.approx(summary.ce_net)
    assert sum(item.ce_net for item in summary.engine_aggregates) == pytest.approx(summary.ce_net)
    assert summary.executed_count <= summary.selected_count <= summary.total_records
    assert summary.non_execution_rate == pytest.approx(1.0)


def test_executed_distinct_candidate_count_separates_buckets_from_candidates() -> None:
    """P0 #3 — ``executed_count`` counts BUCKET records (1 candidate × N capital
    buckets). ``executed_distinct_candidate_count`` keys on (pair, engine_id,
    timestamp), stable across buckets. 8 executed records = 2 candidates × 4 buckets."""
    records = tuple(
        build_dtr(
            dtr_id=f"dtr-{candidate_idx}-{bucket}",
            pair="BTCUSDT",
            engine_id="engine_a",
            decision_state=DecisionState.EXECUTED,
            expected_cost=0.0010,
            realized_cost=0.0011,
            gross_return=0.0022,
            ce_expected=0.0006,
            runtime_mode="local_replay",
            input_source="local_replay",
            timestamp=candidate_ts,
        )
        for candidate_idx, candidate_ts in enumerate((1_700_000_000.0, 1_700_000_900.0))
        for bucket in (400, 500, 1000, 2000)
    )

    summary = build_replay_metrics_summary(records, total_opportunities=8)

    assert summary.executed_count == 8
    assert summary.executed_distinct_candidate_count == 2


def test_build_replay_metrics_summary_adds_cd_engine_doctrine_and_non_green_statuses() -> None:
    records = (
        build_dtr(
            dtr_id="dtr-c-executed",
            pair="BTCUSDT",
            engine_id="engine_c",
            decision_state=DecisionState.EXECUTED,
            expected_cost=0.0012,
            realized_cost=0.0013,
            gross_return=0.0025,
            ce_expected=0.0007,
            runtime_mode="local_replay",
            input_source="local_replay",
            timestamp=1_700_000_000.0,
        ),
        build_dtr(
            dtr_id="dtr-d-rejected",
            pair="ETHUSDT",
            engine_id="engine_d",
            decision_state=DecisionState.REJECTED_RANKING,
            expected_cost=0.0014,
            realized_cost=0.0,
            gross_return=0.0,
            ce_expected=-0.0002,
            runtime_mode="local_replay",
            input_source="local_replay",
            timestamp=1_700_000_060.0,
        ),
    )

    summary = build_replay_metrics_summary(records, total_opportunities=2)
    engines = {item.engine_id: item for item in summary.engine_aggregates}

    assert engines["engine_c"].engine_role == (
        "Breakout / continuation engine with fake-breakout protection and toxic-flow veto/context."
    )
    assert engines["engine_c"].shared_physics_mapping_status == "PARTIAL_BY_DESIGN"
    assert engines["engine_c"].executed_count == 1
    assert engines["engine_c"].rejected_count == 0
    assert engines["engine_c"].execution_rate == pytest.approx(1.0)
    assert engines["engine_c"].engine_executed_only_net_return == pytest.approx(0.0012)
    assert engines["engine_c"].executed_only_net_return_status == "EXECUTED_NET_RETURN_NOT_PROVEN"
    assert engines["engine_c"].true_net_equity_drawdown_status == "TRUE_NET_EQUITY_DRAWDOWN_MISSING_CAPITAL"
    assert engines["engine_c"].shadow_confirmation_status == "NOT_PROVEN"
    assert engines["engine_c"].promotion_status == "NOT_SHADOW_READY"
    assert engines["engine_c"].cost_model_completeness_status == "COST_MODEL_PARTIAL_FEE_MISSING"
    assert engines["engine_d"].engine_role == (
        "Re-entry / second-chance engine with first-episode linkage, anti-revenge, reformation, and realized-vol context."
    )
    assert engines["engine_d"].shared_physics_mapping_status == "PARTIAL_BY_DESIGN"
    assert engines["engine_d"].executed_count == 0
    assert engines["engine_d"].rejected_count == 1
    assert engines["engine_d"].execution_rate == pytest.approx(0.0)
    assert engines["engine_d"].executed_only_net_return_status == "EXECUTED_NET_RETURN_INSUFFICIENT_EXECUTIONS"
    assert engines["engine_d"].true_net_equity_drawdown_status == "TRUE_NET_EQUITY_DRAWDOWN_MISSING_CAPITAL"
    assert engines["engine_d"].fill_realism_status == "FILL_REALISM_MODEL_ONLY"
    assert engines["engine_d"].promotion_status == "NOT_SHADOW_READY"


def test_build_replay_metrics_summary_keeps_state_counts_mutually_exclusive() -> None:
    records = (
        build_dtr(
            dtr_id="dtr-executed",
            pair="BTCUSDT",
            engine_id="engine_a",
            decision_state=DecisionState.EXECUTED,
            ce_expected=0.0004,
            runtime_mode="local_replay",
            input_source="local_replay",
            timestamp=1_700_000_000.0,
        ),
        build_dtr(
            dtr_id="dtr-phantom",
            pair="BTCUSDT",
            engine_id="engine_a",
            decision_state=DecisionState.PHANTOM,
            ce_expected=0.0002,
            runtime_mode="local_replay",
            input_source="local_replay",
            timestamp=1_700_000_060.0,
        ),
        build_dtr(
            dtr_id="dtr-hard-blocked",
            pair="ETHUSDT",
            engine_id="engine_b",
            decision_state=DecisionState.HARD_BLOCKED,
            ce_expected=-0.0001,
            runtime_mode="local_replay",
            input_source="local_replay",
            timestamp=1_700_000_120.0,
        ),
        build_dtr(
            dtr_id="dtr-rejected",
            pair="ETHUSDT",
            engine_id="engine_b",
            decision_state=DecisionState.REJECTED_RANKING,
            ce_expected=-0.0002,
            runtime_mode="local_replay",
            input_source="local_replay",
            timestamp=1_700_000_180.0,
        ),
    )

    summary = build_replay_metrics_summary(records, total_opportunities=4)

    assert summary.total_records == 4
    assert summary.selected_count == 2
    assert summary.executed_count == 1
    assert summary.hard_blocked_count == 1
    assert summary.rejected_ranking_count == 1
    assert summary.phantom_count == 1
    assert summary.executed_count <= summary.selected_count <= summary.total_records
    assert summary.hard_blocked_count + summary.rejected_ranking_count + summary.phantom_count + summary.executed_count == summary.total_records


def test_build_replay_metrics_summary_executed_only_return_excludes_non_executed_states_and_builds_true_drawdown() -> None:
    records = (
        build_dtr(
            dtr_id="dtr-executed-1",
            pair="BTCUSDT",
            engine_id="engine_c",
            decision_state=DecisionState.EXECUTED,
            expected_cost=0.0010,
            realized_cost=0.0010,
            gross_return=0.0040,
            ce_expected=0.0006,
            runtime_mode="local_replay",
            input_source="local_replay",
            timestamp=1_700_000_000.0,
        ),
        build_dtr(
            dtr_id="dtr-reduced-1",
            pair="BTCUSDT",
            engine_id="engine_c",
            decision_state=DecisionState.REDUCED,
            expected_cost=0.0006,
            realized_cost=0.0005,
            gross_return=-0.0010,
            ce_expected=0.0001,
            runtime_mode="local_replay",
            input_source="local_replay",
            timestamp=1_700_000_060.0,
        ),
        build_dtr(
            dtr_id="dtr-blocked-1",
            pair="ETHUSDT",
            engine_id="engine_d",
            decision_state=DecisionState.HARD_BLOCKED,
            expected_cost=0.0040,
            realized_cost=0.0,
            gross_return=0.1200,
            ce_expected=-0.0002,
            runtime_mode="local_replay",
            input_source="local_replay",
            timestamp=1_700_000_120.0,
        ),
        build_dtr(
            dtr_id="dtr-rejected-1",
            pair="ETHUSDT",
            engine_id="engine_d",
            decision_state=DecisionState.REJECTED_RANKING,
            expected_cost=0.0030,
            realized_cost=0.0,
            gross_return=0.0800,
            ce_expected=-0.0001,
            runtime_mode="local_replay",
            input_source="local_replay",
            timestamp=1_700_000_180.0,
        ),
        build_dtr(
            dtr_id="dtr-phantom-1",
            pair="SOLUSDT",
            engine_id="engine_a",
            decision_state=DecisionState.PHANTOM,
            expected_cost=0.0020,
            realized_cost=0.0,
            gross_return=0.0700,
            ce_expected=-0.0003,
            runtime_mode="local_replay",
            input_source="local_replay",
            timestamp=1_700_000_240.0,
        ),
    )

    summary = build_replay_metrics_summary(
        records,
        total_opportunities=5,
        initial_capital=1.0,
    )

    assert summary.executed_count == 1
    assert summary.reduced_count == 1
    assert summary.hard_blocked_count == 1
    assert summary.rejected_count == 1
    assert summary.phantom_count == 1
    assert summary.missing_realized_cost_count == 0
    assert summary.executed_only_net_return == pytest.approx(0.0015)
    assert summary.executed_only_net_return_status == "EXECUTED_NET_RETURN_NOT_PROVEN"
    assert summary.ce_net == pytest.approx(0.0001)
    assert summary.executed_only_net_return != summary.ce_net
    assert summary.true_net_equity_curve == ()
    assert summary.true_net_equity_max_drawdown is None
    assert summary.true_net_equity_drawdown_status == "TRUE_NET_EQUITY_DRAWDOWN_MISSING_EXECUTED_PNL"


def test_build_replay_metrics_summary_missing_realized_cost_blocks_true_economics() -> None:
    records = (
        build_dtr(
            dtr_id="dtr-executed-missing-cost",
            pair="BTCUSDT",
            engine_id="engine_c",
            decision_state=DecisionState.EXECUTED,
            expected_cost=0.0010,
            realized_cost=0.0,
            gross_return=0.0040,
            ce_expected=0.0005,
            runtime_mode="local_replay",
            input_source="local_replay",
            timestamp=1_700_000_000.0,
        ),
    )

    summary = build_replay_metrics_summary(
        records,
        total_opportunities=1,
        initial_capital=1.0,
    )

    assert summary.executed_only_net_return is None
    assert summary.executed_only_net_return_status == "EXECUTED_NET_RETURN_MISSING_REALIZED_COST"
    assert summary.missing_realized_cost_count == 1
    assert summary.true_net_equity_curve == ()
    assert summary.true_net_equity_max_drawdown is None
    assert summary.true_net_equity_drawdown_status == "TRUE_NET_EQUITY_DRAWDOWN_MISSING_EXECUTED_PNL"


def test_build_replay_metrics_summary_missing_capital_keeps_true_drawdown_not_proven() -> None:
    records = (
        build_dtr(
            dtr_id="dtr-executed-no-capital",
            pair="BTCUSDT",
            engine_id="engine_c",
            decision_state=DecisionState.EXECUTED,
            expected_cost=0.0010,
            realized_cost=0.0010,
            gross_return=0.0040,
            ce_expected=0.0005,
            runtime_mode="local_replay",
            input_source="local_replay",
            timestamp=1_700_000_000.0,
        ),
    )

    summary = build_replay_metrics_summary(records, total_opportunities=1)

    assert summary.executed_only_net_return_status == "EXECUTED_NET_RETURN_NOT_PROVEN"
    assert summary.true_net_equity_max_drawdown is None
    assert summary.true_net_equity_drawdown_status == "TRUE_NET_EQUITY_DRAWDOWN_MISSING_CAPITAL"


def test_build_replay_metrics_summary_carries_configured_fee_and_depth20_impact_provenance() -> None:
    records = (
        build_dtr(
            dtr_id="dtr-executed-provenance",
            pair="BTCUSDT",
            engine_id="engine_a",
            decision_state=DecisionState.EXECUTED,
            expected_cost=0.0012,
            realized_cost=0.0011,
            gross_return=0.0040,
            ce_expected=0.0009,
            runtime_mode="local_replay",
            input_source="local_replay",
            timestamp=1_700_000_000.0,
        ),
    )

    summary = build_replay_metrics_summary(
        records,
        total_opportunities=1,
        initial_capital=1.0,
        fee_provenance=ReplayFeeProvenance(
            fee_source_status="FEE_SOURCE_CONFIGURED",
            fee_model_name="binance_spot_fee_schedule",
            fee_rate_maker_bps=7.5,
            fee_rate_taker_bps=10.0,
            fee_currency="USDT",
            fee_bps=10.0,
            fee_provenance_ref="config/fees/binance_spot.json",
            fee_input_hash="fee-hash-1",
            fee_policy_version="fee.v1",
        ),
        impact_provenance=ReplayImpactProvenance(
            impact_source_status="IMPACT_SOURCE_DEPTH20_MODEL",
            impact_model_name="depth20_prudent_v1",
            impact_bps=2.4,
            impact_notional=125.0,
            impact_depth_ref="depth20://BTCUSDT/2026-03-01T00:00:00Z",
            impact_depth_level=20,
            impact_provenance_ref="depth20_model://prudent_v1",
            impact_input_hash="impact-hash-1",
            impact_policy_version="impact.v1",
        ),
        book_depth_availability=ReplayBookDepthAvailability(
            book_depth_levels=20,
            book_depth_source_status="BOOK_DEPTH20_AVAILABLE",
            impact_depth_level_used=20,
        ),
        fill_realism=ReplayFillRealismEvidence(
            fill_realism_status="FILL_REALISM_SHADOW_MEASURED",
            fill_source_status="FILL_SOURCE_SHADOW_TELEMETRY",
            measured_fill_flag=True,
            fill_ratio_observed=1.0,
        ),
        cost_parity=ReplayCostParityEvidence(
            cost_parity_status="REPLAY_LIVE_COST_PARITY_BLOCKED_BY_TELEMETRY",
        ),
    )

    assert summary.fee_source_status == "FEE_SOURCE_CONFIGURED"
    assert summary.fee_model_name == "binance_spot_fee_schedule"
    assert summary.fee_rate_maker_bps == pytest.approx(7.5)
    assert summary.fee_rate_taker_bps == pytest.approx(10.0)
    assert summary.fee_bps == pytest.approx(10.0)
    assert summary.impact_source_status == "IMPACT_SOURCE_DEPTH20_MODEL"
    assert summary.impact_model_name == "depth20_prudent_v1"
    assert summary.impact_bps == pytest.approx(2.4)
    assert summary.impact_depth_level == 20
    assert summary.book_depth_source_status == "BOOK_DEPTH20_AVAILABLE"
    assert summary.impact_depth_readiness_status == "DEPTH20_AVAILABLE"
    assert summary.shadow_extension_required is False
    assert summary.fill_realism_status == "FILL_REALISM_SHADOW_MEASURED"
    assert summary.cost_model_completeness_status == "COST_MODEL_PARTIAL_REPLAY_LIVE_PARITY_MISSING"
    assert "REPLAY_LIVE_COST_PARITY_NOT_PROVEN" in summary.cost_readiness_reason_codes


def test_execute_local_replay_export_keeps_cost_provenance_fields_in_artifact() -> None:
    output_dir = _scratch_dir("export_cost_provenance")
    shutil.rmtree(output_dir, ignore_errors=True)
    try:
        result = execute_local_replay_export(
            output_dir,
            ReplayExecutionInput(
                run_manifest=ReplayRunManifest(
                    run_id="run-executor-cost-prov-1",
                    strategy_id="strategy-executor-a",
                    strategy_version="a.v4.0",
                    strategy_classification=StrategyClassification.A_VARIANT,
                    lineage_version="a.v4.0.r1",
                    profile_scope=ProfileId.LIGHT,
                    engine_scope=("engine_a",),
                    tested_pairs=("BTCUSDT",),
                    dataset_manifest_id="dataset-executor-cost-prov-1",
                    timeframe_scope="2026-03-01/2026-03-31",
                    feature_set_version="4.0.0",
                    transform_set_version="4.0.0",
                    formula_set_version="formula.v4",
                    scoring_version="score.v4",
                    regime_version="regime.v4",
                    risk_policy_version="risk.v4",
                    cost_model_version="cost.v4",
                    performance_mode="research_fast_mode",
                    artifact_schema_version="4.0.0",
                    artifact_hash="artifact-executor-cost-prov-1",
                    clock_id="clock-executor-cost-prov-1",
                    start_timestamp_ms=1_700_000_000_000,
                    end_timestamp_ms=1_700_000_600_000,
                    tick_count=600,
                    record_count=1,
                ),
                total_opportunities=1,
                dtr_records=(
                    build_dtr(
                        dtr_id="dtr-cost-prov-1",
                        pair="BTCUSDT",
                        engine_id="engine_a",
                        decision_state=DecisionState.EXECUTED,
                        expected_cost=0.0010,
                        realized_cost=0.0011,
                        gross_return=0.0022,
                        ce_expected=0.0006,
                        runtime_mode="local_replay",
                        input_source="local_replay",
                        timestamp=1_700_000_000.0,
                    ),
                ),
                initial_capital=400.0,
                fee_provenance=ReplayFeeProvenance(
                    fee_source_status="FEE_SOURCE_CONFIGURED",
                    fee_model_name="binance_spot_fee_schedule",
                    fee_rate_maker_bps=7.5,
                    fee_rate_taker_bps=10.0,
                    fee_currency="USDT",
                    fee_bps=10.0,
                    fee_provenance_ref="config/fees/binance_spot.json",
                    fee_input_hash="fee-hash-1",
                    fee_policy_version="fee.v1",
                ),
                impact_provenance=ReplayImpactProvenance(
                    impact_source_status="IMPACT_SOURCE_DEPTH20_MODEL",
                    impact_model_name="depth20_prudent_v1",
                    impact_bps=2.4,
                    impact_notional=125.0,
                    impact_depth_ref="depth20://BTCUSDT/2026-03-01T00:00:00Z",
                    impact_depth_level=20,
                    impact_provenance_ref="depth20_model://prudent_v1",
                    impact_input_hash="impact-hash-1",
                    impact_policy_version="impact.v1",
                ),
                feature_bridge_payload={
                    "bridge_status": "ok",
                    "dataset_id": "dataset-executor-cost-prov-1",
                    "feature_set_version": "4.0.0",
                    "transform_set_version": "4.0.0",
                    "pairs": ["BTCUSDT"],
                    "engines": ["engine_a"],
                },
                parity_diagnostics_payload={
                    "parity_status": "ok",
                    "dataset_id": "dataset-executor-cost-prov-1",
                    "decision_match_rate": 1.0,
                    "book_depth_levels": 20,
                    "book_depth_source_status": "BOOK_DEPTH20_AVAILABLE",
                    "impact_depth_level_used": 20,
                    "impact_depth_readiness_status": "DEPTH20_AVAILABLE",
                    "shadow_extension_required": False,
                    "shadow_extension_reason": "SHADOW_STANDARD_30D",
                    "minimum_shadow_days_required": 30,
                    "shadow_extension_status": "SHADOW_STANDARD_30D",
                    "fill_realism_status": "FILL_REALISM_SHADOW_MEASURED",
                    "fill_source_status": "FILL_SOURCE_SHADOW_TELEMETRY",
                    "measured_fill_flag": True,
                    "fill_ratio_observed": 1.0,
                    "cost_parity_status": "REPLAY_LIVE_COST_PARITY_BLOCKED_BY_TELEMETRY",
                    "cost_alignment": "NOT_PROVEN",
                },
                review_notes=("executor cost provenance smoke",),
            ),
        )

        metrics_payload = json.loads(
            result.export_result.replay_metrics_path.read_text(encoding="utf-8")
        )

        assert metrics_payload["fee_source_status"] == "FEE_SOURCE_CONFIGURED"
        assert metrics_payload["fee_model_name"] == "binance_spot_fee_schedule"
        assert metrics_payload["fee_rate_taker_bps"] == pytest.approx(10.0)
        assert metrics_payload["impact_source_status"] == "IMPACT_SOURCE_DEPTH20_MODEL"
        assert metrics_payload["impact_model_name"] == "depth20_prudent_v1"
        assert metrics_payload["impact_depth_level"] == 20
        assert metrics_payload["book_depth_source_status"] == "BOOK_DEPTH20_AVAILABLE"
        assert metrics_payload["fill_realism_status"] == "FILL_REALISM_SHADOW_MEASURED"
        assert metrics_payload["cost_parity_status"] == "REPLAY_LIVE_COST_PARITY_BLOCKED_BY_TELEMETRY"
        assert metrics_payload["cost_model_completeness_status"] == "COST_MODEL_PARTIAL_REPLAY_LIVE_PARITY_MISSING"
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_execute_local_replay_export_persists_capital_profile_artifacts_and_non_green_statuses() -> None:
    output_dir = _scratch_dir("export_capital_profiles")
    shutil.rmtree(output_dir, ignore_errors=True)
    try:
        capital_profiles = (
            build_capital_bucket_profile(
                CapitalProfileBuildInput(
                    capital_bucket=400,
                    pair_universe=("BTCUSDT", "ETHUSDT"),
                    max_active_pairs=1,
                )
            ),
            build_capital_bucket_profile(
                CapitalProfileBuildInput(
                    capital_bucket=500,
                    pair_universe=("BTCUSDT", "ETHUSDT"),
                    max_active_pairs=1,
                )
            ),
            build_capital_bucket_profile(
                CapitalProfileBuildInput(
                    capital_bucket=1500,
                    pair_universe=("BTCUSDT", "ETHUSDT", "SOLUSDT"),
                    max_active_pairs=2,
                )
            ),
            build_capital_bucket_profile(
                CapitalProfileBuildInput(
                    capital_bucket=4000,
                    pair_universe=("BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"),
                    max_active_pairs=3,
                )
            ),
        )
        result = execute_local_replay_export(
            output_dir,
            ReplayExecutionInput(
                run_manifest=ReplayRunManifest(
                    run_id="run-executor-capital-profiles-1",
                    strategy_id="strategy-executor-a",
                    strategy_version="a.v4.0",
                    strategy_classification=StrategyClassification.A_VARIANT,
                    lineage_version="a.v4.0.r1",
                    profile_scope=ProfileId.COMPLETE,
                    engine_scope=("engine_a",),
                    tested_pairs=("BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"),
                    dataset_manifest_id="dataset-executor-capital-profiles-1",
                    timeframe_scope="2026-03-01/2026-03-31",
                    feature_set_version="4.0.0",
                    transform_set_version="4.0.0",
                    formula_set_version="formula.v4",
                    scoring_version="score.v4",
                    regime_version="regime.v4",
                    risk_policy_version="risk.v4",
                    cost_model_version="cost.v4",
                    performance_mode="research_fast_mode",
                    artifact_schema_version="4.0.0",
                    artifact_hash="artifact-executor-capital-profiles-1",
                    clock_id="clock-executor-capital-profiles-1",
                    start_timestamp_ms=1_700_000_000_000,
                    end_timestamp_ms=1_700_000_600_000,
                    tick_count=600,
                    record_count=1,
                ),
                total_opportunities=1,
                dtr_records=(
                    build_dtr(
                        dtr_id="dtr-capital-profile-1",
                        pair="BTCUSDT",
                        engine_id="engine_a",
                        decision_state=DecisionState.EXECUTED,
                        expected_cost=0.0010,
                        realized_cost=0.0011,
                        gross_return=0.0022,
                        ce_expected=0.0006,
                        runtime_mode="local_replay",
                        input_source="local_replay",
                        timestamp=1_700_000_000.0,
                    ),
                ),
                initial_capital=400.0,
                capital_bucket_profiles=capital_profiles,
                feature_bridge_payload={
                    "bridge_status": "ok",
                    "dataset_id": "dataset-executor-capital-profiles-1",
                    "feature_set_version": "4.0.0",
                    "transform_set_version": "4.0.0",
                    "pairs": ["BTCUSDT"],
                    "engines": ["engine_a"],
                },
                parity_diagnostics_payload={
                    "parity_status": "ok",
                    "dataset_id": "dataset-executor-capital-profiles-1",
                    "decision_match_rate": 1.0,
                },
                review_notes=("capital profile export",),
            ),
        )

        metrics_payload = json.loads(
            result.export_result.replay_metrics_path.read_text(encoding="utf-8")
        )
        assert len(result.export_result.capital_profile_paths) == 4
        assert metrics_payload["small_capital_viability_status"] == "NOT_PROVEN"
        assert metrics_payload["min_notional_viability_status"] == "MIN_NOTIONAL_NOT_PROVEN"
        assert metrics_payload["capital_fragmentation_status"] == "NOT_PROVEN"
        assert len(metrics_payload["capital_bucket_profiles"]) == 4
        assert (result.export_result.export_dir / "capital_profiles" / "400.json").exists()
        assert metrics_payload["capital_bucket_profiles"][0]["capital_bucket"] == 400
        assert metrics_payload["capital_bucket_profiles"][0]["allowed_pairs"] == []
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_execute_local_replay_export_builds_artifact_from_dtr_session():
    output_dir = _scratch_dir("export")
    shutil.rmtree(output_dir, ignore_errors=True)
    try:
        result = execute_local_replay_export(
            output_dir,
            ReplayExecutionInput(
                run_manifest=ReplayRunManifest(
                    run_id="run-executor-1",
                    strategy_id="strategy-executor-a",
                    strategy_version="a.v4.0",
                    strategy_classification=StrategyClassification.A_VARIANT,
                    lineage_version="a.v4.0.r1",
                    profile_scope=ProfileId.LIGHT,
                    engine_scope=("engine_a", "engine_b"),
                    tested_pairs=("BTCUSDT", "ETHUSDT"),
                    dataset_manifest_id="dataset-executor-1",
                    timeframe_scope="2026-03-01/2026-03-31",
        feature_set_version="4.0.0",
        transform_set_version="4.0.0",
        formula_set_version="formula.v4",
                    scoring_version="score.v4",
                    regime_version="regime.v4",
                    risk_policy_version="risk.v4",
                    cost_model_version="cost.v4",
                    performance_mode="research_fast_mode",
        artifact_schema_version="4.0.0",
                    artifact_hash="artifact-executor-1",
                    clock_id="clock-executor-1",
                    start_timestamp_ms=1_700_000_000_000,
                    end_timestamp_ms=1_700_000_600_000,
                    tick_count=600,
                    record_count=2,
                ),
                total_opportunities=4,
                dtr_records=_records(),
                initial_capital=400.0,
                feature_bridge_payload={
                    "bridge_status": "ok",
                    "dataset_id": "dataset-executor-1",
                    "feature_set_version": "4.0.0",
                    "transform_set_version": "4.0.0",
                    "pairs": ["BTCUSDT", "ETHUSDT"],
                    "engines": ["engine_a", "engine_b"],
                },
        parity_diagnostics_payload={
            "parity_status": "ok",
            "dataset_id": "dataset-executor-1",
            "decision_match_rate": 1.0,
        },
                review_notes=("executor smoke",),
            ),
        )

        metrics_payload = json.loads(
            result.export_result.replay_metrics_path.read_text(encoding="utf-8")
        )
        review_markdown = result.export_result.review_export_path.read_text(encoding="utf-8")
        replay_dtr_lines = result.export_result.replay_dtr_path.read_text(encoding="utf-8").strip().splitlines()

        assert result.metrics_summary.total_records == 2
        assert metrics_payload["dtr_coverage"] == 0.5
        assert metrics_payload["selected_count"] == 1
        assert "expected_ce_net:" in review_markdown
        assert "executed_only_net_return_status: EXECUTED_NET_RETURN_INSUFFICIENT_EXECUTIONS" in review_markdown
        assert "exec_rate_semantics: executed_count / total_records" in review_markdown
        assert "drawdown_proxy_semantics: gross_return_proxy_not_net_equity_max_drawdown" in review_markdown
        assert "true_net_equity_drawdown_status: TRUE_NET_EQUITY_DRAWDOWN_INSUFFICIENT_EXECUTIONS" in review_markdown
        assert "cost_model_completeness_status: COST_MODEL_PARTIAL_FEE_MISSING" in review_markdown
        assert "fee_source_status: FEE_SOURCE_NOT_PROVEN" in review_markdown
        assert "run-executor-1" in review_markdown
        assert "dtr_coverage: 0.500" in review_markdown
        assert len(replay_dtr_lines) == 2
        assert len(metrics_payload["engine_promotion_artifacts"]) == 2
        assert len(metrics_payload["pair_promotion_artifacts"]) == 2
        assert len(metrics_payload["strategy_promotion_artifacts"]) == 1
        assert len(metrics_payload["sample_size_survival_artifacts"]) >= 6
        assert result.promotion_artifacts.engine_promotion_artifacts[0].promotion_status != "ENGINE_PROMOTION_READY"
        assert (result.export_result.export_dir / "engine_promotion" / "engine_a" / "run-executor-1.json").exists()
        assert (result.export_result.export_dir / "pair_promotion" / "BTCUSDT" / "run-executor-1.json").exists()
        assert (result.export_result.export_dir / "strategy_promotion" / "strategy-executor-a" / "run-executor-1.json").exists()
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
