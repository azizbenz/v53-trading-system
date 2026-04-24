from __future__ import annotations

from pathlib import Path
import shutil

import pytest
import yaml

from calibration_loader import (
    CalibrationArtifact,
    CalibrationArtifactNotFoundError,
    CalibrationArtifactSignatureError,
    CalibrationArtifactValidationError,
    CalibrationLoader,
    CalibrationThresholdNotFoundError,
    load_calibration_artifact,
    load_calibration_collection,
)
from tests.support_paths import make_repo_scratch_dir


@pytest.fixture
def calibration_tmpdir() -> Path:
    root = make_repo_scratch_dir("pytest-calibration-loader-fixtures")
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


def _payload(*, threshold_id: str, value: int | float) -> dict[str, object]:
    return {
        "artifact_id": f"{threshold_id.lower()}-artifact",
        "version": "v1",
        "produced_by": "local_ia_lab",
        "generated_at": "2026-04-09T10:15:00Z",
        "thresholds": (
            {
                "threshold_id": threshold_id,
                "value": value,
                "source_module": "src/example/module.py",
                "calibration_artifact": "config/calibration/v1/example.yml",
            },
        ),
        "signature": {
            "signed_by": "operator.aziz",
            "signed_at": "2026-04-09T12:00:00Z",
        },
    }


def _write_signed_yaml(path: Path, *, threshold_id: str, value: int | float) -> None:
    payload = _payload(threshold_id=threshold_id, value=value)
    artifact = CalibrationArtifact.model_validate(payload)
    payload["signature"]["payload_hash_sha256"] = artifact.payload_hash_sha256()
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def test_load_calibration_artifact_reads_signed_yaml(calibration_tmpdir: Path) -> None:
    artifact_path = calibration_tmpdir / "edge_gate.yml"
    _write_signed_yaml(artifact_path, threshold_id="THR-E01", value=2.0)

    artifact = load_calibration_artifact(artifact_path)

    assert artifact.artifact_id == "thr-e01-artifact"
    assert artifact.thresholds[0].threshold_id == "THR-E01"
    assert artifact.thresholds[0].value == 2.0


def test_load_calibration_artifact_rejects_missing_signature(calibration_tmpdir: Path) -> None:
    artifact_path = calibration_tmpdir / "unsigned.yml"
    payload = _payload(threshold_id="THR-E01", value=2.0)
    del payload["signature"]
    artifact_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    with pytest.raises(CalibrationArtifactSignatureError):
        load_calibration_artifact(artifact_path)


def test_load_calibration_artifact_rejects_invalid_hash(calibration_tmpdir: Path) -> None:
    artifact_path = calibration_tmpdir / "tampered.yml"
    payload = _payload(threshold_id="THR-E01", value=2.0)
    payload["signature"]["payload_hash_sha256"] = "0" * 64
    artifact_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    with pytest.raises(CalibrationArtifactValidationError):
        load_calibration_artifact(artifact_path)


def test_load_calibration_collection_rejects_duplicate_threshold_ids(
    calibration_tmpdir: Path,
) -> None:
    _write_signed_yaml(calibration_tmpdir / "one.yml", threshold_id="THR-E01", value=2.0)
    _write_signed_yaml(calibration_tmpdir / "two.yml", threshold_id="THR-E01", value=3.0)

    with pytest.raises(CalibrationArtifactValidationError):
        load_calibration_collection(calibration_tmpdir)


def test_calibration_loader_loads_versioned_directory_and_exposes_values(
    calibration_tmpdir: Path,
) -> None:
    version_dir = calibration_tmpdir / "v1"
    version_dir.mkdir()
    _write_signed_yaml(version_dir / "edge_gate.yml", threshold_id="THR-E01", value=2.0)
    _write_signed_yaml(version_dir / "shadow.yml", threshold_id="THR-S01", value=30)

    loader = CalibrationLoader(calibration_tmpdir)
    collection = loader.load(version="v1")

    assert CalibrationLoader.get_value(collection, "THR-E01") == 2.0
    assert CalibrationLoader.get_value(collection, "THR-S01") == 30
    with pytest.raises(CalibrationThresholdNotFoundError):
        CalibrationLoader.get_value(collection, "THR-MISSING")


def test_calibration_loader_rejects_missing_version_directory(calibration_tmpdir: Path) -> None:
    loader = CalibrationLoader(calibration_tmpdir)

    with pytest.raises(CalibrationArtifactNotFoundError):
        loader.load(version="v1")
