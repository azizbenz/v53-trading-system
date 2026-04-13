from __future__ import annotations

from meta_minimal.dtr_core.decision_state_encoder import DecisionState
from meta_minimal.dtr_core.dtr_record_builder import build_dtr

from local_replay_runtime import build_local_lab_loss_surrogate_report


def _records() -> tuple:
    return (
        build_dtr(
            dtr_id="btc-1",
            pair="BTCUSDT",
            engine_id="engine_a",
            decision_state=DecisionState.EXECUTED,
            raw_score=0.10,
            penalized_score=0.09,
            final_score=0.08,
            expected_cost=0.0018,
            realized_cost=0.0020,
            gross_return=0.0010,
            ce_expected=0.0010,
            candidate_size=1.0,
            final_size=1.0,
            ranking_position=1,
            runtime_mode="local_replay",
            input_source="local_replay",
            timestamp=1_700_000_000.0,
        ),
        build_dtr(
            dtr_id="btc-2",
            pair="BTCUSDT",
            engine_id="engine_a",
            decision_state=DecisionState.EXECUTED,
            raw_score=0.11,
            penalized_score=0.10,
            final_score=0.09,
            expected_cost=0.0017,
            realized_cost=0.0019,
            gross_return=0.0012,
            ce_expected=0.0011,
            candidate_size=1.0,
            final_size=0.9,
            ranking_position=2,
            runtime_mode="local_replay",
            input_source="local_replay",
            timestamp=1_700_000_060.0,
        ),
        build_dtr(
            dtr_id="eth-1",
            pair="ETHUSDT",
            engine_id="engine_b",
            decision_state=DecisionState.EXECUTED,
            raw_score=0.35,
            penalized_score=0.32,
            final_score=0.30,
            expected_cost=0.0008,
            realized_cost=0.0007,
            gross_return=0.0060,
            ce_expected=0.0030,
            candidate_size=1.0,
            final_size=1.0,
            ranking_position=1,
            runtime_mode="local_replay",
            input_source="local_replay",
            timestamp=1_700_000_120.0,
        ),
        build_dtr(
            dtr_id="eth-2",
            pair="ETHUSDT",
            engine_id="engine_b",
            decision_state=DecisionState.EXECUTED,
            raw_score=0.33,
            penalized_score=0.31,
            final_score=0.29,
            expected_cost=0.0009,
            realized_cost=0.0008,
            gross_return=0.0055,
            ce_expected=0.0028,
            candidate_size=1.0,
            final_size=1.0,
            ranking_position=2,
            runtime_mode="local_replay",
            input_source="local_replay",
            timestamp=1_700_000_180.0,
        ),
    )


def test_build_local_lab_loss_surrogate_report_trains_and_ranks_the_riskiest_scope():
    report = build_local_lab_loss_surrogate_report(
        correlation_id="corr-surrogate",
        export_dir="E:/lab/export_dir",
        records=_records(),
    )

    assert report.status == "trained"
    assert report.ready is True
    assert report.scope_count == 2
    assert report.scored_scope_count == 2
    assert report.loss_count == 2
    assert report.non_loss_count == 2
    assert report.highest_risk_scope_slug == "btcusdt__engine_a"
    assert report.highest_risk_probability > 0.5
    assert report.model is not None
    assert report.model.no_lookahead_only is True
    assert report.scopes[0].scope_slug == "btcusdt__engine_a"
    assert report.scopes[0].mean_predicted_loss_probability is not None


def test_build_local_lab_loss_surrogate_report_fails_close_when_only_one_label_exists():
    profitable_records = tuple(
        record.model_copy(update={"gross_return": 0.01, "realized_cost": 0.001})
        for record in _records()
    )

    report = build_local_lab_loss_surrogate_report(
        correlation_id="corr-surrogate-single-class",
        export_dir="E:/lab/export_dir",
        records=profitable_records,
    )

    assert report.status == "single_class_only"
    assert report.ready is False
    assert report.highest_risk_scope_slug == ""
    assert report.highest_risk_probability == 0.0
    assert report.model is None
