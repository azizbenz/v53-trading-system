from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from calibration_loader import CalibrationArtifact
from calibration_loader.loader import CalibrationArtifactValidationError
from scoring_backbone import (
    EngineBCostThresholdResolverConfig,
    build_engine_b_cost_threshold_updates,
    resolve_engine_b_cost_thresholds,
)


def _write_signed_yaml(
    path: Path,
    *,
    thresholds: tuple[tuple[str, int | float], ...],
) -> None:
    payload = {
        "artifact_id": "engine-b-cost-thresholds",
        "version": "v1",
        "produced_by": "local_ia_lab",
        "generated_at": "2026-04-19T18:30:00Z",
        "thresholds": [
            {
                "threshold_id": threshold_id,
                "value": value,
                "source_module": "src/scoring_backbone/engine_b_cost_thresholds.py",
                "calibration_artifact": "config/calibration/v1/engine_b_cost.yml",
            }
            for threshold_id, value in thresholds
        ],
        "signature": {
            "signed_by": "operator.aziz",
            "signed_at": "2026-04-19T18:35:00Z",
        },
    }
    artifact = CalibrationArtifact.model_validate(payload)
    payload["signature"]["payload_hash_sha256"] = artifact.payload_hash_sha256()
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def test_resolve_engine_b_cost_thresholds_loads_signed_values(repo_tmp_path: Path) -> None:
    calibration_tmpdir = repo_tmp_path / "engine_b_cost_thresholds_resolve"
    version_dir = calibration_tmpdir / "v1"
    version_dir.mkdir(parents=True, exist_ok=True)
    _write_signed_yaml(
        version_dir / "engine_b_cost.yml",
        thresholds=(("THR-B01", 0.0009), ("THR-B02", 0.0003)),
    )

    resolved = resolve_engine_b_cost_thresholds(
        EngineBCostThresholdResolverConfig(
            calibration_root=calibration_tmpdir,
            calibration_version="v1",
            delta_safe_threshold_id="THR-B01",
            ce_min_threshold_id="THR-B02",
        )
    )

    assert resolved.delta_safe == pytest.approx(0.0009)
    assert resolved.ce_min == pytest.approx(0.0003)
    assert resolved.to_engine_b_input_updates() == {
        "delta_safe": pytest.approx(0.0009),
        "ce_min": pytest.approx(0.0003),
    }


def test_build_engine_b_cost_threshold_updates_returns_engine_b_payload(repo_tmp_path: Path) -> None:
    calibration_tmpdir = repo_tmp_path / "engine_b_cost_thresholds_updates"
    version_dir = calibration_tmpdir / "v1"
    version_dir.mkdir(parents=True, exist_ok=True)
    _write_signed_yaml(
        version_dir / "engine_b_cost.yml",
        thresholds=(("THR-B01", 0.0008), ("THR-B02", 0.0002)),
    )

    updates = build_engine_b_cost_threshold_updates(
        EngineBCostThresholdResolverConfig(
            calibration_root=calibration_tmpdir,
            calibration_version="v1",
            delta_safe_threshold_id="THR-B01",
            ce_min_threshold_id="THR-B02",
        )
    )

    assert updates == {
        "delta_safe": pytest.approx(0.0008),
        "ce_min": pytest.approx(0.0002),
    }


def test_resolve_engine_b_cost_thresholds_rejects_relaxed_values_above_hard_cap(
    repo_tmp_path: Path,
) -> None:
    calibration_tmpdir = repo_tmp_path / "engine_b_cost_thresholds_hard_cap"
    version_dir = calibration_tmpdir / "v1"
    version_dir.mkdir(parents=True, exist_ok=True)
    _write_signed_yaml(
        version_dir / "engine_b_cost.yml",
        thresholds=(("THR-B01", 0.03), ("THR-B02", 0.0003)),
    )

    with pytest.raises(CalibrationArtifactValidationError, match="THR-B01"):
        resolve_engine_b_cost_thresholds(
            EngineBCostThresholdResolverConfig(
                calibration_root=calibration_tmpdir,
                calibration_version="v1",
                delta_safe_threshold_id="THR-B01",
                ce_min_threshold_id="THR-B02",
            )
        )
