from __future__ import annotations

from datetime import datetime, timezone

from calibration_methods import PotGpdConfig
from local_replay_runtime import (
    EdgeGateCalibrationConfig,
    build_local_lab_calibration_methods_review,
    build_local_lab_multiple_testing_review,
    build_local_lab_calibration_normalized_report,
    build_local_lab_tail_risk_review,
    calibrate_edge_gate_thresholds,
)
from meta_minimal.dtr_core.decision_state_encoder import DecisionState
from meta_minimal.dtr_core.dtr_record_builder import build_dtr


def _records():
    base_timestamp = 1_700_000_000.0
    return tuple(
        build_dtr(
            dtr_id=f"dtr-norm-{index}",
            pair="BTCUSDT" if index % 2 == 0 else "ETHUSDT",
            engine_id="engine_a",
            decision_state=DecisionState.EXECUTED,
            expected_cost=0.0010 + (index * 0.00001),
            realized_cost=0.0008 + (index * 0.00001),
            gross_return=0.0040 + ((index % 5) * 0.0002),
            ce_expected=0.0025,
            regime="trend" if index % 2 == 0 else "range",
            runtime_mode="local_replay",
            input_source="local_replay",
            path_complete=True,
            candidate_size=1.0,
            final_size=1.0,
            timestamp=base_timestamp + (index * 86_400.0),
        )
        for index in range(40)
    )


def test_build_local_lab_calibration_normalized_report_merges_edge_and_tail_evidence():
    records = _records()
    edge_config = EdgeGateCalibrationConfig(
        min_positive_trades=10,
        min_cost_observations=20,
        bootstrap_samples=120,
        rng_seed=17,
    )
    edge_report = calibrate_edge_gate_thresholds(
        records,
        config=edge_config,
        generated_at=datetime(2026, 4, 10, 14, 0, tzinfo=timezone.utc),
    )
    calibration_methods_review = build_local_lab_calibration_methods_review(
        correlation_id="corr-norm",
        export_dir="E:/lab/export",
        run_id="run-norm",
        records=records,
    )
    tail_risk_review = build_local_lab_tail_risk_review(
        correlation_id="corr-norm",
        export_dir="E:/lab/export",
        run_id="run-norm",
        records=records,
        config=PotGpdConfig(min_exceedances=3, bootstrap_samples=20),
    )
    multiple_testing_review = build_local_lab_multiple_testing_review(
        correlation_id="corr-norm",
        export_dir="E:/lab/export",
        run_id="run-norm",
        edge_report=edge_report,
        tail_risk_review=tail_risk_review,
    )

    report = build_local_lab_calibration_normalized_report(
        correlation_id="corr-norm",
        export_dir="E:/lab/export",
        run_id="run-norm",
        records=records,
        edge_report=edge_report,
        edge_config=edge_config,
        calibration_methods_review=calibration_methods_review,
        multiple_testing_review=multiple_testing_review,
        tail_risk_review=tail_risk_review,
    )

    assert report.correlation_id == "corr-norm"
    assert report.review_status == "partial"
    assert report.review_ready is False
    assert report.threshold_count == 5
    assert report.global_dsr is not None
    assert report.multi_test_correction == "not_required_interval_publication"
    assert report.data_window.start is not None
    assert report.data_window.end is not None
    assert len(report.reproducibility.data_hash_sha256) == 64
    assert report.reproducibility.rng_seed == 17

    e01 = report.method_per_threshold["THR-E01"]
    r01 = report.method_per_threshold["THR-R01"]

    assert e01.method == "stationary_block_bootstrap"
    assert e01.bootstrap_block_length is not None
    assert e01.hard_cap_human == edge_config.human_multiplier_floor
    assert e01.stationarity_status == calibration_methods_review.stationarity_status
    assert e01.hard_cap_satisfied is True
    assert e01.hard_cap_binding is False
    assert e01.dsr_check == calibration_methods_review.dsr_status
    assert e01.review_status == calibration_methods_review.review_status.value

    assert r01.method == "POT_GPD_UNAVAILABLE"
    assert r01.stationarity_status == calibration_methods_review.stationarity_status
    assert r01.review_status == "partial"
    assert r01.published_value is None
