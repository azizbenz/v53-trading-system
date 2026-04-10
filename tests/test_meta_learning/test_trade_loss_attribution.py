from __future__ import annotations

from meta_learning import build_trade_loss_attribution_report
from meta_minimal import build_meta_runtime_result_from_records
from meta_minimal.dtr_core.decision_state_encoder import DecisionState
from meta_minimal.dtr_core.dtr_record_builder import build_dtr


def test_trade_loss_attribution_report_explains_cost_drift_and_ignores_profitable_records():
    records = (
        build_dtr(
            dtr_id="dtr-loss-1",
            pair="BTCUSDT",
            engine_id="engine_a",
            decision_state=DecisionState.EXECUTED,
            expected_cost=0.0010,
            realized_cost=0.0035,
            gross_return=0.0020,
            final_score=0.40,
            ce_expected=0.0010,
            runtime_mode="local_replay",
            input_source="local_replay",
            timestamp=1_700_000_000.0,
        ),
        build_dtr(
            dtr_id="dtr-win-1",
            pair="BTCUSDT",
            engine_id="engine_a",
            decision_state=DecisionState.EXECUTED,
            expected_cost=0.0010,
            realized_cost=0.0008,
            gross_return=0.0040,
            final_score=0.55,
            ce_expected=0.0020,
            runtime_mode="local_replay",
            input_source="local_replay",
            timestamp=1_700_000_060.0,
        ),
        build_dtr(
            dtr_id="dtr-skip-1",
            pair="BTCUSDT",
            engine_id="engine_a",
            decision_state=DecisionState.SELECTED,
            expected_cost=0.0010,
            realized_cost=0.0,
            gross_return=0.0,
            runtime_mode="local_replay",
            input_source="local_replay",
            timestamp=1_700_000_120.0,
        ),
    )
    meta_result = build_meta_runtime_result_from_records(records, total_opportunities=3)

    report = build_trade_loss_attribution_report(
        "corr-loss-1",
        dtr_records=records,
        diagnostics=(),
        dtr_summary=meta_result.dtr_summary,
        cra_report=meta_result.cra_report,
        break_even_report=meta_result.break_even_report,
        edge_report=meta_result.edge_report,
    )

    assert report.correlation_id == "corr-loss-1"
    assert report.total_records == 3
    assert report.executed_records == 2
    assert report.losing_trade_count == 1
    assert report.failure_modes[0].failure_mode == "cost_drift"
    assert report.failure_modes[0].count == 1

    loss = next(item for item in report.attributions if item.dtr_id == "dtr-loss-1")
    win = next(item for item in report.attributions if item.dtr_id == "dtr-win-1")
    skipped = next(item for item in report.attributions if item.dtr_id == "dtr-skip-1")

    assert loss.attribution_status == "loss"
    assert loss.primary_failure_mode == "cost_drift"
    assert loss.recommended_threshold_ids == ("THR-E01", "THR-E02")
    assert "Raise the fee-aware edge gate" in loss.preventive_action
    assert win.attribution_status == "not_loss"
    assert skipped.attribution_status == "not_executed"


def test_trade_loss_attribution_report_falls_back_to_trace_coverage_when_path_is_incomplete():
    records = (
        build_dtr(
            dtr_id="dtr-loss-trace",
            pair="ETHUSDT",
            engine_id="engine_b",
            decision_state=DecisionState.EXECUTED,
            expected_cost=0.0010,
            realized_cost=0.0010,
            gross_return=0.0005,
            final_score=0.60,
            ce_expected=0.0020,
            runtime_mode="local_replay",
            input_source="local_replay",
            path_complete=False,
            path_warnings=("missing_fill_fragment",),
            timestamp=1_700_000_000.0,
        ),
    )
    meta_result = build_meta_runtime_result_from_records(records, total_opportunities=4)

    report = build_trade_loss_attribution_report(
        "corr-trace-loss",
        dtr_records=records,
        diagnostics=(),
        dtr_summary=meta_result.dtr_summary,
        cra_report=meta_result.cra_report,
        break_even_report=meta_result.break_even_report,
        edge_report=meta_result.edge_report,
    )

    loss = report.attributions[0]
    assert loss.primary_failure_mode == "trace_coverage"
    assert "improve trace capture" in loss.preventive_action.lower()
    assert report.losing_trade_count == 1
