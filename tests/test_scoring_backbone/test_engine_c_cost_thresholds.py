from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from calibration_loader import CalibrationArtifact
from calibration_loader.loader import CalibrationArtifactValidationError
from scoring_backbone import (
    EngineCCostThresholdResolverConfig,
    build_engine_c_cost_threshold_updates,
    resolve_engine_c_cost_thresholds,
)


def _write_signed_yaml(
    path: Path,
    *,
    thresholds: tuple[tuple[str, int | float], ...],
) -> None:
    payload = {
        "artifact_id": "engine-c-cost-thresholds",
        "version": "v1",
        "produced_by": "local_ia_lab",
        "generated_at": "2026-04-19T20:35:00Z",
        "thresholds": [
            {
                "threshold_id": threshold_id,
                "value": value,
                "source_module": "src/scoring_backbone/engine_c_cost_thresholds.py",
                "calibration_artifact": "config/calibration/v1/engine_c_cost.yml",
            }
            for threshold_id, value in thresholds
        ],
        "signature": {
            "signed_by": "operator.aziz",
            "signed_at": "2026-04-19T20:36:00Z",
        },
    }
    artifact = CalibrationArtifact.model_validate(payload)
    payload["signature"]["payload_hash_sha256"] = artifact.payload_hash_sha256()
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def test_resolve_engine_c_cost_thresholds_loads_signed_values(
    repo_tmp_path: Path,
) -> None:
    calibration_tmpdir = repo_tmp_path / "engine_c_cost_thresholds_resolve"
    version_dir = calibration_tmpdir / "v1"
    version_dir.mkdir(parents=True, exist_ok=True)
    _write_signed_yaml(
        version_dir / "engine_c_cost.yml",
        thresholds=(
            ("delta_safe_C", 0.0005),
            ("ce_min_C", 0.00015),
        ),
    )

    resolved = resolve_engine_c_cost_thresholds(
        EngineCCostThresholdResolverConfig(
            calibration_root=calibration_tmpdir,
            calibration_version="v1",
            delta_safe_threshold_id="delta_safe_C",
            ce_min_threshold_id="ce_min_C",
        )
    )

    assert resolved.to_engine_c_input_updates() == {
        "delta_safe": pytest.approx(0.0005),
        "ce_min": pytest.approx(0.00015),
    }


def test_build_engine_c_cost_threshold_updates_returns_engine_c_payload(
    repo_tmp_path: Path,
) -> None:
    calibration_tmpdir = repo_tmp_path / "engine_c_cost_thresholds_updates"
    version_dir = calibration_tmpdir / "v1"
    version_dir.mkdir(parents=True, exist_ok=True)
    _write_signed_yaml(
        version_dir / "engine_c_cost.yml",
        thresholds=(
            ("delta_safe_C", 0.0007),
            ("ce_min_C", 0.0002),
        ),
    )

    updates = build_engine_c_cost_threshold_updates(
        EngineCCostThresholdResolverConfig(
            calibration_root=calibration_tmpdir,
            calibration_version="v1",
            delta_safe_threshold_id="delta_safe_C",
            ce_min_threshold_id="ce_min_C",
        )
    )

    assert updates == {
        "delta_safe": pytest.approx(0.0007),
        "ce_min": pytest.approx(0.0002),
    }


def test_resolve_engine_c_cost_thresholds_rejects_values_above_hard_cap(
    repo_tmp_path: Path,
) -> None:
    calibration_tmpdir = repo_tmp_path / "engine_c_cost_thresholds_cap"
    version_dir = calibration_tmpdir / "v1"
    version_dir.mkdir(parents=True, exist_ok=True)
    _write_signed_yaml(
        version_dir / "engine_c_cost.yml",
        thresholds=(
            ("delta_safe_C", 0.02),
            ("ce_min_C", 0.00015),
        ),
    )

    with pytest.raises(
        CalibrationArtifactValidationError,
        match="Engine C delta_safe hard cap",
    ):
        resolve_engine_c_cost_thresholds(
            EngineCCostThresholdResolverConfig(
                calibration_root=calibration_tmpdir,
                calibration_version="v1",
                delta_safe_threshold_id="delta_safe_C",
                ce_min_threshold_id="ce_min_C",
            )
        )
