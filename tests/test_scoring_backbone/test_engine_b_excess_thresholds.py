from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from calibration_loader import CalibrationArtifact
from calibration_loader.loader import CalibrationArtifactValidationError
from scoring_backbone import (
    EngineBExcessThresholdResolverConfig,
    build_engine_b_excess_threshold_updates,
    resolve_engine_b_excess_thresholds,
)


def _write_signed_yaml(
    path: Path,
    *,
    thresholds: tuple[tuple[str, int | float], ...],
) -> None:
    payload = {
        "artifact_id": "engine-b-excess-thresholds",
        "version": "v1",
        "produced_by": "local_ia_lab",
        "generated_at": "2026-04-19T19:25:00Z",
        "thresholds": [
            {
                "threshold_id": threshold_id,
                "value": value,
                "source_module": "src/scoring_backbone/engine_b_excess_thresholds.py",
                "calibration_artifact": "config/calibration/v1/engine_b_excess.yml",
            }
            for threshold_id, value in thresholds
        ],
        "signature": {
            "signed_by": "operator.aziz",
            "signed_at": "2026-04-19T19:30:00Z",
        },
    }
    artifact = CalibrationArtifact.model_validate(payload)
    payload["signature"]["payload_hash_sha256"] = artifact.payload_hash_sha256()
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def test_resolve_engine_b_excess_thresholds_loads_signed_values(
    repo_tmp_path: Path,
) -> None:
    calibration_tmpdir = repo_tmp_path / "engine_b_excess_thresholds_resolve"
    version_dir = calibration_tmpdir / "v1"
    version_dir.mkdir(parents=True, exist_ok=True)
    _write_signed_yaml(
        version_dir / "engine_b_excess.yml",
        thresholds=(
            ("THR-B05", 1.0),
            ("THR-B06", 1.5),
            ("THR-B07", 4.0),
            ("THR-B08", 0.35),
            ("THR-B09", 0.70),
        ),
    )

    resolved = resolve_engine_b_excess_thresholds(
        EngineBExcessThresholdResolverConfig(
            calibration_root=calibration_tmpdir,
            calibration_version="v1",
            z_marginal_threshold_id="THR-B05",
            z_star_threshold_id="THR-B06",
            z_max_threshold_id="THR-B07",
            vpin_toxic_threshold_id="THR-B08",
            max_intra_family_correlation_threshold_id="THR-B09",
        )
    )

    assert resolved.to_engine_b_excess_threshold_updates() == {
        "z_marginal": pytest.approx(1.0),
        "z_star": pytest.approx(1.5),
        "z_max": pytest.approx(4.0),
        "vpin_toxic": pytest.approx(0.35),
        "max_intra_family_correlation": pytest.approx(0.70),
    }


def test_build_engine_b_excess_threshold_updates_returns_excess_payload(
    repo_tmp_path: Path,
) -> None:
    calibration_tmpdir = repo_tmp_path / "engine_b_excess_thresholds_updates"
    version_dir = calibration_tmpdir / "v1"
    version_dir.mkdir(parents=True, exist_ok=True)
    _write_signed_yaml(
        version_dir / "engine_b_excess.yml",
        thresholds=(
            ("THR-B05", 0.9),
            ("THR-B06", 1.4),
            ("THR-B07", 3.8),
            ("THR-B08", 0.30),
            ("THR-B09", 0.65),
        ),
    )

    updates = build_engine_b_excess_threshold_updates(
        EngineBExcessThresholdResolverConfig(
            calibration_root=calibration_tmpdir,
            calibration_version="v1",
            z_marginal_threshold_id="THR-B05",
            z_star_threshold_id="THR-B06",
            z_max_threshold_id="THR-B07",
            vpin_toxic_threshold_id="THR-B08",
            max_intra_family_correlation_threshold_id="THR-B09",
        )
    )

    assert updates == {
        "z_marginal": pytest.approx(0.9),
        "z_star": pytest.approx(1.4),
        "z_max": pytest.approx(3.8),
        "vpin_toxic": pytest.approx(0.30),
        "max_intra_family_correlation": pytest.approx(0.65),
    }


def test_resolve_engine_b_excess_thresholds_rejects_invalid_z_order(
    repo_tmp_path: Path,
) -> None:
    calibration_tmpdir = repo_tmp_path / "engine_b_excess_thresholds_order"
    version_dir = calibration_tmpdir / "v1"
    version_dir.mkdir(parents=True, exist_ok=True)
    _write_signed_yaml(
        version_dir / "engine_b_excess.yml",
        thresholds=(
            ("THR-B05", 1.5),
            ("THR-B06", 1.2),
            ("THR-B07", 4.0),
            ("THR-B08", 0.35),
            ("THR-B09", 0.70),
        ),
    )

    with pytest.raises(
        CalibrationArtifactValidationError,
        match="z_marginal < z_star < z_max",
    ):
        resolve_engine_b_excess_thresholds(
            EngineBExcessThresholdResolverConfig(
                calibration_root=calibration_tmpdir,
                calibration_version="v1",
                z_marginal_threshold_id="THR-B05",
                z_star_threshold_id="THR-B06",
                z_max_threshold_id="THR-B07",
                vpin_toxic_threshold_id="THR-B08",
                max_intra_family_correlation_threshold_id="THR-B09",
            )
        )
