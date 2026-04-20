from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from calibration_loader import CalibrationArtifact
from calibration_loader.loader import CalibrationArtifactValidationError
from scoring_backbone import (
    EngineBInvalidationThresholdResolverConfig,
    build_engine_b_invalidation_threshold_updates,
    resolve_engine_b_invalidation_thresholds,
)


def _write_signed_yaml(
    path: Path,
    *,
    thresholds: tuple[tuple[str, int | float], ...],
) -> None:
    payload = {
        "artifact_id": "engine-b-invalidation-thresholds",
        "version": "v1",
        "produced_by": "local_ia_lab",
        "generated_at": "2026-04-19T19:45:00Z",
        "thresholds": [
            {
                "threshold_id": threshold_id,
                "value": value,
                "source_module": "src/scoring_backbone/engine_b_invalidation_thresholds.py",
                "calibration_artifact": "config/calibration/v1/engine_b_invalidation.yml",
            }
            for threshold_id, value in thresholds
        ],
        "signature": {
            "signed_by": "operator.aziz",
            "signed_at": "2026-04-19T19:50:00Z",
        },
    }
    artifact = CalibrationArtifact.model_validate(payload)
    payload["signature"]["payload_hash_sha256"] = artifact.payload_hash_sha256()
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def test_resolve_engine_b_invalidation_thresholds_loads_signed_values(
    repo_tmp_path: Path,
) -> None:
    calibration_tmpdir = repo_tmp_path / "engine_b_invalidation_thresholds_resolve"
    version_dir = calibration_tmpdir / "v1"
    version_dir.mkdir(parents=True, exist_ok=True)
    _write_signed_yaml(
        version_dir / "engine_b_invalidation.yml",
        thresholds=(("THR-B10", 8.0), ("THR-B11", 0.98), ("THR-B12", 1.5)),
    )

    resolved = resolve_engine_b_invalidation_thresholds(
        EngineBInvalidationThresholdResolverConfig(
            calibration_root=calibration_tmpdir,
            calibration_version="v1",
            max_holding_hours_threshold_id="THR-B10",
            fallback_stop_ratio_threshold_id="THR-B11",
            stop_multiplier_threshold_id="THR-B12",
        )
    )

    assert resolved.to_engine_b_invalidation_threshold_updates() == {
        "max_holding_hours": pytest.approx(8.0),
        "fallback_stop_ratio": pytest.approx(0.98),
        "stop_multiplier": pytest.approx(1.5),
    }


def test_build_engine_b_invalidation_threshold_updates_returns_invalidation_payload(
    repo_tmp_path: Path,
) -> None:
    calibration_tmpdir = repo_tmp_path / "engine_b_invalidation_thresholds_updates"
    version_dir = calibration_tmpdir / "v1"
    version_dir.mkdir(parents=True, exist_ok=True)
    _write_signed_yaml(
        version_dir / "engine_b_invalidation.yml",
        thresholds=(("THR-B10", 12.0), ("THR-B11", 0.97), ("THR-B12", 1.8)),
    )

    updates = build_engine_b_invalidation_threshold_updates(
        EngineBInvalidationThresholdResolverConfig(
            calibration_root=calibration_tmpdir,
            calibration_version="v1",
            max_holding_hours_threshold_id="THR-B10",
            fallback_stop_ratio_threshold_id="THR-B11",
            stop_multiplier_threshold_id="THR-B12",
        )
    )

    assert updates == {
        "max_holding_hours": pytest.approx(12.0),
        "fallback_stop_ratio": pytest.approx(0.97),
        "stop_multiplier": pytest.approx(1.8),
    }


def test_resolve_engine_b_invalidation_thresholds_rejects_invalid_fallback_stop_ratio(
    repo_tmp_path: Path,
) -> None:
    calibration_tmpdir = repo_tmp_path / "engine_b_invalidation_thresholds_ratio"
    version_dir = calibration_tmpdir / "v1"
    version_dir.mkdir(parents=True, exist_ok=True)
    _write_signed_yaml(
        version_dir / "engine_b_invalidation.yml",
        thresholds=(("THR-B10", 8.0), ("THR-B11", 1.0), ("THR-B12", 1.5)),
    )

    with pytest.raises(
        CalibrationArtifactValidationError,
        match="must be a finite float in \\(0, 1\\)",
    ):
        resolve_engine_b_invalidation_thresholds(
            EngineBInvalidationThresholdResolverConfig(
                calibration_root=calibration_tmpdir,
                calibration_version="v1",
                max_holding_hours_threshold_id="THR-B10",
                fallback_stop_ratio_threshold_id="THR-B11",
                stop_multiplier_threshold_id="THR-B12",
            )
        )
