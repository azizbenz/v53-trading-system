from __future__ import annotations

from local_replay_runtime import (
    build_local_lab_ablation_study,
    build_pending_local_lab_ablation_study,
)
from meta_minimal.dtr_core.decision_state_encoder import DecisionState
from meta_minimal.dtr_core.dtr_record_builder import build_dtr


def _baseline_records():
    return (
        build_dtr(
            dtr_id="dtr-1",
            pair="BTCUSDT",
            engine_id="engine_a",
            decision_state=DecisionState.EXECUTED,
            gross_return=0.0020,
            realized_cost=0.0010,
            ce_expected=0.0015,
            runtime_mode="local_replay",
            input_source="local_replay",
            timestamp=1_700_000_000.0,
        ),
        build_dtr(
            dtr_id="dtr-2",
            pair="BTCUSDT",
            engine_id="engine_a",
            decision_state=DecisionState.EXECUTED,
            gross_return=0.0022,
            realized_cost=0.0011,
            ce_expected=0.0016,
            runtime_mode="local_replay",
            input_source="local_replay",
            timestamp=1_700_000_060.0,
        ),
    )


def _candidate_records():
    return (
        build_dtr(
            dtr_id="dtr-1",
            pair="BTCUSDT",
            engine_id="engine_a",
            decision_state=DecisionState.EXECUTED,
            gross_return=0.0040,
            realized_cost=0.0010,
            ce_expected=0.0030,
            runtime_mode="local_replay",
            input_source="local_replay",
            timestamp=1_700_000_000.0,
        ),
        build_dtr(
            dtr_id="dtr-2",
            pair="BTCUSDT",
            engine_id="engine_a",
            decision_state=DecisionState.EXECUTED,
            gross_return=0.0044,
            realized_cost=0.0011,
            ce_expected=0.0032,
            runtime_mode="local_replay",
            input_source="local_replay",
            timestamp=1_700_000_060.0,
        ),
    )


def test_pending_local_lab_ablation_study_requires_baseline():
    study = build_pending_local_lab_ablation_study(
        correlation_id="corr-ablation",
        candidate_export_dir="E:/lab/candidate",
        candidate_run_id="run-candidate",
        candidate_dataset_manifest_id="dataset-1",
        selected_pair="BTCUSDT",
        selected_engine_id="engine_a",
    )

    assert study.study_ready is False
    assert study.blocking_reasons == ("ABLATION_BASELINE_EXPORT_DIR_REQUIRED",)


def test_local_lab_ablation_study_builds_positive_candidate_delta():
    study = build_local_lab_ablation_study(
        correlation_id="corr-ablation",
        candidate_export_dir="E:/lab/candidate",
        baseline_export_dir="E:/lab/baseline",
        candidate_run_id="run-candidate",
        baseline_run_id="run-baseline",
        candidate_dataset_manifest_id="dataset-1",
        baseline_dataset_manifest_id="dataset-1",
        candidate_records=_candidate_records(),
        baseline_records=_baseline_records(),
        selected_pair="BTCUSDT",
        selected_engine_id="engine_a",
    )

    assert study.study_ready is True
    assert study.aligned_record_count == 2
    assert study.ablation_delta_net_pnl > 0.0
    assert study.ablation_delta_ce is not None
    assert study.ablation_delta_ce > 0.0
    assert study.block_rate_delta == 0.0


def test_local_lab_ablation_study_rejects_misaligned_dtr_ids():
    bad_baseline = (
        build_dtr(
            dtr_id="other-id",
            pair="BTCUSDT",
            engine_id="engine_a",
            decision_state=DecisionState.EXECUTED,
            gross_return=0.0020,
            realized_cost=0.0010,
            ce_expected=0.0015,
            runtime_mode="local_replay",
            input_source="local_replay",
            timestamp=1_700_000_000.0,
        ),
    )

    study = build_local_lab_ablation_study(
        correlation_id="corr-ablation",
        candidate_export_dir="E:/lab/candidate",
        baseline_export_dir="E:/lab/baseline",
        candidate_run_id="run-candidate",
        baseline_run_id="run-baseline",
        candidate_dataset_manifest_id="dataset-1",
        baseline_dataset_manifest_id="dataset-1",
        candidate_records=_candidate_records(),
        baseline_records=bad_baseline,
        selected_pair="BTCUSDT",
        selected_engine_id="engine_a",
    )

    assert study.study_ready is False
    assert "ABLATION_DTR_ID_MISMATCH" in study.blocking_reasons
