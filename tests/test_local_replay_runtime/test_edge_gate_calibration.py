from __future__ import annotations

from datetime import datetime, timezone

import pytest

from local_replay_runtime import (
    EdgeGateCalibrationConfig,
    EdgeGateCalibrationInsufficientDataError,
    build_edge_gate_calibration_artifact,
    calibrate_edge_gate_thresholds,
)
from meta_minimal.dtr_core.decision_state_encoder import DecisionState
from meta_minimal.dtr_core.dtr_record_builder import build_dtr


def _executed_record(
    *,
    dtr_id: str,
    pair: str,
    engine_id: str,
    expected_cost: float,
    realized_cost: float,
    gross_return: float,
) -> object:
    return build_dtr(
        dtr_id=dtr_id,
        pair=pair,
        engine_id=engine_id,
        decision_state=DecisionState.EXECUTED,
        expected_cost=expected_cost,
        realized_cost=realized_cost,
        gross_return=gross_return,
        ce_expected=gross_return - expected_cost,
        runtime_mode="local_replay",
        input_source="local_replay",
        timestamp=1_700_000_000.0,
    )


def test_calibrate_edge_gate_thresholds_builds_conservative_report_and_artifact():
    records = (
        _executed_record(
            dtr_id="dtr-1",
            pair="BTCUSDT",
            engine_id="engine_a",
            expected_cost=0.0010,
            realized_cost=0.0009,
            gross_return=0.0042,
        ),
        _executed_record(
            dtr_id="dtr-2",
            pair="BTCUSDT",
            engine_id="engine_a",
            expected_cost=0.0011,
            realized_cost=0.0010,
            gross_return=0.0045,
        ),
        _executed_record(
            dtr_id="dtr-3",
            pair="ETHUSDT",
            engine_id="engine_b",
            expected_cost=0.0013,
            realized_cost=0.0012,
            gross_return=0.0048,
        ),
        _executed_record(
            dtr_id="dtr-4",
            pair="ETHUSDT",
            engine_id="engine_b",
            expected_cost=0.0014,
            realized_cost=0.0011,
            gross_return=0.0050,
        ),
        _executed_record(
            dtr_id="dtr-5",
            pair="SOLUSDT",
            engine_id="engine_c",
            expected_cost=0.0015,
            realized_cost=0.0013,
            gross_return=0.0010,
        ),
        _executed_record(
            dtr_id="dtr-6",
            pair="SOLUSDT",
            engine_id="engine_c",
            expected_cost=0.0016,
            realized_cost=0.0014,
            gross_return=0.0055,
        ),
    )
    config = EdgeGateCalibrationConfig(
        min_positive_trades=4,
        min_cost_observations=6,
        bootstrap_samples=300,
        rng_seed=11,
    )

    report = calibrate_edge_gate_thresholds(
        records,
        config=config,
        generated_at=datetime(2026, 4, 10, 12, 0, tzinfo=timezone.utc),
    )
    artifact = build_edge_gate_calibration_artifact(
        report,
        signed_by="operator.aziz",
        config=config,
        signed_at=datetime(2026, 4, 10, 12, 5, tzinfo=timezone.utc),
    )

    e01 = report.get_threshold("THR-E01")
    e02 = report.get_threshold("THR-E02")

    assert report.executed_record_count == 6
    assert report.positive_trade_count == 5
    assert report.cost_observation_count == 6
    assert e01.published_value >= 2.0
    assert e02.published_value >= 15.0
    assert e01.method_version == "stationary_block_bootstrap_v1"
    assert e01.bootstrap_block_length >= 1
    assert e01.hard_cap_human == config.human_multiplier_floor
    assert e01.hard_cap_satisfied is True
    assert e01.hard_cap_binding is False
    assert e02.method_version == "stationary_block_bootstrap_v1"
    assert e02.bootstrap_block_length >= 1
    assert e02.hard_cap_human == config.human_absolute_floor_bps
    assert e02.hard_cap_satisfied is True
    assert e02.hard_cap_binding is False
    assert any(note.startswith("hard_cap_binding=") for note in e01.notes)
    assert any(note.startswith("hard_cap_binding=") for note in e02.notes)
    assert any(note.startswith("bootstrap_block_length=") for note in e01.notes)
    assert any(note.startswith("bootstrap_block_length=") for note in e02.notes)
    assert artifact.thresholds[0].threshold_id == "THR-E01"
    assert artifact.thresholds[1].threshold_id == "THR-E02"
    assert artifact.thresholds[0].source_module == "src/scoring_backbone/fee_aware_edge_gate.py"
    assert artifact.signature.payload_hash_sha256 == artifact.payload_hash_sha256()


def test_calibrate_edge_gate_thresholds_rejects_weak_positive_sample():
    records = (
        _executed_record(
            dtr_id="dtr-1",
            pair="BTCUSDT",
            engine_id="engine_a",
            expected_cost=0.0010,
            realized_cost=0.0010,
            gross_return=0.0005,
        ),
        _executed_record(
            dtr_id="dtr-2",
            pair="BTCUSDT",
            engine_id="engine_a",
            expected_cost=0.0010,
            realized_cost=0.0011,
            gross_return=0.0007,
        ),
        _executed_record(
            dtr_id="dtr-3",
            pair="BTCUSDT",
            engine_id="engine_a",
            expected_cost=0.0010,
            realized_cost=0.0012,
            gross_return=0.0011,
        ),
    )
    config = EdgeGateCalibrationConfig(
        min_positive_trades=2,
        min_cost_observations=3,
        bootstrap_samples=200,
    )

    with pytest.raises(EdgeGateCalibrationInsufficientDataError):
        calibrate_edge_gate_thresholds(records, config=config)


def test_documented_floor_edge_gate_artifact_uses_human_floors() -> None:
    """Floor artifact ships the documented human floors (THR-E01=2.0/THR-E02=15.0)
    sourced from EdgeGateCalibrationConfig — no hand-typed magic numbers — and is a
    valid signed/hashed artifact resolvable by the fee-aware edge gate."""
    from local_replay_runtime import build_documented_floor_edge_gate_artifact

    cfg = EdgeGateCalibrationConfig()
    ts = datetime(2026, 6, 2, tzinfo=timezone.utc)
    artifact = build_documented_floor_edge_gate_artifact(
        signed_by="tester", config=cfg, generated_at=ts, signed_at=ts
    )

    e01 = next(
        t for t in artifact.thresholds if t.threshold_id == cfg.edge_multiplier_threshold_id
    )
    e02 = next(
        t for t in artifact.thresholds if t.threshold_id == cfg.min_absolute_edge_threshold_id
    )
    assert e01.value == cfg.human_multiplier_floor == 2.0
    assert e02.value == cfg.human_absolute_floor_bps == 15.0
    # valid signed artifact (hash attestation matches canonical payload)
    assert artifact.signature.payload_hash_sha256 == artifact.payload_hash_sha256()
    assert "DOCUMENTED CONSERVATIVE FLOOR" in e01.notes


def test_committed_edge_gate_artifact_resolves_fee_aware_thresholds() -> None:
    """The committed config/calibration/v1/edge_gate.yml resolves through the
    canonical fee-aware edge-gate loader to the documented floors."""
    from execution_backbone.fee_aware_edge_gate import resolve_fee_aware_edge_thresholds

    thresholds = resolve_fee_aware_edge_thresholds()
    assert thresholds.edge_multiplier == 2.0
    assert thresholds.min_absolute_edge_bps == 15.0
