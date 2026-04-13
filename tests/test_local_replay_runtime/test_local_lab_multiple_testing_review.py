from __future__ import annotations

from datetime import datetime, timezone

from calibration_methods import PotGpdConfig
from local_replay_runtime import (
    EdgeGateCalibrationConfig,
    build_hypothesis_test_family_review,
    build_local_lab_multiple_testing_review,
    build_local_lab_tail_risk_review,
    calibrate_edge_gate_thresholds,
)
from meta_minimal.dtr_core.decision_state_encoder import DecisionState
from meta_minimal.dtr_core.dtr_record_builder import build_dtr


def _records():
    base_timestamp = 1_700_000_000.0
    return tuple(
        build_dtr(
            dtr_id=f"dtr-multi-{index}",
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


def test_local_lab_multiple_testing_review_marks_interval_publication_as_not_required():
    records = _records()
    edge_report = calibrate_edge_gate_thresholds(
        records,
        config=EdgeGateCalibrationConfig(
            min_positive_trades=10,
            min_cost_observations=20,
            bootstrap_samples=120,
            rng_seed=17,
        ),
        generated_at=datetime(2026, 4, 10, 14, 0, tzinfo=timezone.utc),
    )
    tail_risk_review = build_local_lab_tail_risk_review(
        correlation_id="corr-multi",
        export_dir="E:/lab/export",
        run_id="run-multi",
        records=records,
        config=PotGpdConfig(min_exceedances=3, bootstrap_samples=20),
    )

    review = build_local_lab_multiple_testing_review(
        correlation_id="corr-multi",
        export_dir="E:/lab/export",
        run_id="run-multi",
        edge_report=edge_report,
        tail_risk_review=tail_risk_review,
    )

    assert review.review_status.value == "ready"
    assert review.review_ready is True
    assert review.multi_test_correction == "not_required_interval_publication"
    assert review.correction_required is False
    assert review.family_count == 2
    assert review.ready_family_count == 2
    assert review.corrected_family_count == 0
    assert review.families[0].correction_status == "not_required_interval_publication"


def test_build_hypothesis_test_family_review_applies_holm_bonferroni():
    family = build_hypothesis_test_family_review(
        family_id="edge_hypothesis_family",
        hypotheses=(
            ("THR-E01", 0.01),
            ("THR-E02", 0.06),
        ),
        family_alpha=0.05,
    )

    assert family.correction_required is True
    assert family.correction_status == "holm_bonferroni_applied"
    assert family.comparable_p_value_count == 2
    assert family.corrected_rejection_count == 1
    assert family.holm_bonferroni_result is not None
