from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import shutil
from uuid import uuid4

import pytest
import yaml

from calibration_loader import CalibrationArtifact
from local_replay_runtime import (
    EdgeGateCalibrationConfig,
    build_edge_gate_calibration_artifact,
    calibrate_edge_gate_thresholds,
)
from meta_minimal.dtr_core.decision_state_encoder import DecisionState
from meta_minimal.dtr_core.dtr_record_builder import build_dtr
from scoring_backbone import FeeAwareEdgeGateConfig, evaluate_fee_aware_edge


@pytest.fixture
def calibration_tmpdir() -> Path:
    root = Path("build/pytest-fee-aware-edge-gate") / uuid4().hex
    root.mkdir(parents=True, exist_ok=False)
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


def _record(
    *,
    dtr_id: str,
    expected_cost: float,
    realized_cost: float,
    gross_return: float,
) -> object:
    return build_dtr(
        dtr_id=dtr_id,
        pair="BTCUSDT",
        engine_id="engine_a",
        decision_state=DecisionState.EXECUTED,
        expected_cost=expected_cost,
        realized_cost=realized_cost,
        gross_return=gross_return,
        ce_expected=gross_return - expected_cost,
        runtime_mode="local_replay",
        input_source="local_replay",
        timestamp=1_700_000_000.0,
    )


def _write_edge_gate_artifact(root: Path) -> None:
    records = (
        _record(dtr_id="dtr-1", expected_cost=0.0010, realized_cost=0.0008, gross_return=0.0038),
        _record(dtr_id="dtr-2", expected_cost=0.0011, realized_cost=0.0009, gross_return=0.0041),
        _record(dtr_id="dtr-3", expected_cost=0.0012, realized_cost=0.0010, gross_return=0.0040),
        _record(dtr_id="dtr-4", expected_cost=0.0013, realized_cost=0.0011, gross_return=0.0047),
        _record(dtr_id="dtr-5", expected_cost=0.0014, realized_cost=0.0012, gross_return=0.0048),
        _record(dtr_id="dtr-6", expected_cost=0.0015, realized_cost=0.0013, gross_return=0.0050),
    )
    config = EdgeGateCalibrationConfig(
        min_positive_trades=5,
        min_cost_observations=6,
        bootstrap_samples=250,
        rng_seed=7,
    )
    report = calibrate_edge_gate_thresholds(
        records,
        config=config,
        generated_at=datetime(2026, 4, 10, 13, 0, tzinfo=timezone.utc),
    )
    artifact = build_edge_gate_calibration_artifact(
        report,
        signed_by="operator.aziz",
        config=config,
        signed_at=datetime(2026, 4, 10, 13, 5, tzinfo=timezone.utc),
    )
    version_dir = root / "v1"
    version_dir.mkdir(parents=True, exist_ok=True)
    payload = artifact.model_dump(mode="json")
    (version_dir / "edge_gate.yml").write_text(
        yaml.safe_dump(payload, sort_keys=False),
        encoding="utf-8",
    )


def test_fee_aware_edge_gate_blocks_when_edge_is_below_threshold(calibration_tmpdir: Path):
    _write_edge_gate_artifact(calibration_tmpdir)

    decision = evaluate_fee_aware_edge(
        expected_edge_bps=18.0,
        expected_cost=0.0010,
        config=FeeAwareEdgeGateConfig(calibration_root=calibration_tmpdir),
    )

    assert decision.allowed is False
    assert decision.reason_code == "EDGE_INSUFFICIENT_VS_FEES"
    assert decision.threshold_bps >= 20.0


def test_fee_aware_edge_gate_passes_when_edge_clears_threshold(calibration_tmpdir: Path):
    _write_edge_gate_artifact(calibration_tmpdir)

    decision = evaluate_fee_aware_edge(
        expected_edge_bps=30.0,
        expected_cost=0.0010,
        config=FeeAwareEdgeGateConfig(calibration_root=calibration_tmpdir),
    )

    assert decision.allowed is True
    assert decision.reason_code == ""
    assert decision.expected_cost_bps == pytest.approx(10.0)
    assert "threshold=" in decision.detail


def test_fee_aware_edge_gate_rejects_non_finite_inputs(calibration_tmpdir: Path):
    _write_edge_gate_artifact(calibration_tmpdir)

    with pytest.raises(ValueError):
        evaluate_fee_aware_edge(
            expected_edge_bps=float("nan"),
            expected_cost=0.0010,
            config=FeeAwareEdgeGateConfig(calibration_root=calibration_tmpdir),
        )


def test_generated_artifact_is_valid_shared_calibration_payload(calibration_tmpdir: Path):
    _write_edge_gate_artifact(calibration_tmpdir)

    payload = yaml.safe_load((calibration_tmpdir / "v1" / "edge_gate.yml").read_text(encoding="utf-8"))
    artifact = CalibrationArtifact.model_validate(payload)

    assert artifact.thresholds[0].threshold_id == "THR-E01"
    assert artifact.thresholds[1].threshold_id == "THR-E02"
    assert artifact.signature.payload_hash_sha256 == artifact.payload_hash_sha256()
