from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from calibration_loader import CalibrationArtifact
from calibration_loader.loader import CalibrationArtifactValidationError
from scoring_backbone import (
    EngineCContinuationThresholdResolverConfig,
    build_engine_c_continuation_threshold_updates,
    resolve_engine_c_continuation_thresholds,
)


def _write_signed_yaml(
    path: Path,
    *,
    thresholds: tuple[tuple[str, int | float], ...],
) -> None:
    payload = {
        "artifact_id": "engine-c-continuation-thresholds",
        "version": "v1",
        "produced_by": "local_ia_lab",
        "generated_at": "2026-04-19T20:10:00Z",
        "thresholds": [
            {
                "threshold_id": threshold_id,
                "value": value,
                "source_module": "src/scoring_backbone/engine_c_continuation_thresholds.py",
                "calibration_artifact": "config/calibration/v1/engine_c_continuation.yml",
            }
            for threshold_id, value in thresholds
        ],
        "signature": {
            "signed_by": "operator.aziz",
            "signed_at": "2026-04-19T20:12:00Z",
        },
    }
    artifact = CalibrationArtifact.model_validate(payload)
    payload["signature"]["payload_hash_sha256"] = artifact.payload_hash_sha256()
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def test_resolve_engine_c_continuation_thresholds_loads_signed_values(
    repo_tmp_path: Path,
) -> None:
    calibration_tmpdir = repo_tmp_path / "engine_c_continuation_thresholds_resolve"
    version_dir = calibration_tmpdir / "v1"
    version_dir.mkdir(parents=True, exist_ok=True)
    _write_signed_yaml(
        version_dir / "engine_c_continuation.yml",
        thresholds=(
            ("THR-C_OFI_MIN", 6.0),
            ("THR-C_QUEUE_MIN", 0.20),
            ("THR-C_VPIN_MAX", 0.35),
            ("EC-KYLE-LAMBDA-MAX-01", 0.015),
        ),
    )

    resolved = resolve_engine_c_continuation_thresholds(
        EngineCContinuationThresholdResolverConfig(
            calibration_root=calibration_tmpdir,
            calibration_version="v1",
            ofi_min_threshold_id="THR-C_OFI_MIN",
            queue_min_threshold_id="THR-C_QUEUE_MIN",
            vpin_max_threshold_id="THR-C_VPIN_MAX",
            kyle_lambda_max_threshold_id="EC-KYLE-LAMBDA-MAX-01",
        )
    )

    assert resolved.to_engine_c_input_updates() == {
        "continuation_ofi_min": pytest.approx(6.0),
        "continuation_queue_min": pytest.approx(0.20),
        "continuation_vpin_max": pytest.approx(0.35),
        "continuation_kyle_lambda_max": pytest.approx(0.015),
    }


def test_build_engine_c_continuation_threshold_updates_returns_engine_c_payload(
    repo_tmp_path: Path,
) -> None:
    calibration_tmpdir = repo_tmp_path / "engine_c_continuation_thresholds_updates"
    version_dir = calibration_tmpdir / "v1"
    version_dir.mkdir(parents=True, exist_ok=True)
    _write_signed_yaml(
        version_dir / "engine_c_continuation.yml",
        thresholds=(
            ("THR-C_OFI_MIN", 5.5),
            ("THR-C_QUEUE_MIN", 0.15),
            ("THR-C_VPIN_MAX", 0.30),
        ),
    )

    updates = build_engine_c_continuation_threshold_updates(
        EngineCContinuationThresholdResolverConfig(
            calibration_root=calibration_tmpdir,
            calibration_version="v1",
            ofi_min_threshold_id="THR-C_OFI_MIN",
            queue_min_threshold_id="THR-C_QUEUE_MIN",
            vpin_max_threshold_id="THR-C_VPIN_MAX",
        )
    )

    assert updates == {
        "continuation_ofi_min": pytest.approx(5.5),
        "continuation_queue_min": pytest.approx(0.15),
        "continuation_vpin_max": pytest.approx(0.30),
    }


def test_build_engine_c_continuation_threshold_updates_optionally_adds_kyle_lambda_max(
    repo_tmp_path: Path,
) -> None:
    calibration_tmpdir = repo_tmp_path / "engine_c_continuation_thresholds_kyle_lambda"
    version_dir = calibration_tmpdir / "v1"
    version_dir.mkdir(parents=True, exist_ok=True)
    _write_signed_yaml(
        version_dir / "engine_c_continuation.yml",
        thresholds=(
            ("THR-C_OFI_MIN", 5.5),
            ("THR-C_QUEUE_MIN", 0.15),
            ("THR-C_VPIN_MAX", 0.30),
            ("EC-KYLE-LAMBDA-MAX-01", 0.025),
        ),
    )

    updates = build_engine_c_continuation_threshold_updates(
        EngineCContinuationThresholdResolverConfig(
            calibration_root=calibration_tmpdir,
            calibration_version="v1",
            ofi_min_threshold_id="THR-C_OFI_MIN",
            queue_min_threshold_id="THR-C_QUEUE_MIN",
            vpin_max_threshold_id="THR-C_VPIN_MAX",
            kyle_lambda_max_threshold_id="EC-KYLE-LAMBDA-MAX-01",
        )
    )

    assert updates == {
        "continuation_ofi_min": pytest.approx(5.5),
        "continuation_queue_min": pytest.approx(0.15),
        "continuation_vpin_max": pytest.approx(0.30),
        "continuation_kyle_lambda_max": pytest.approx(0.025),
    }


def test_resolve_engine_c_continuation_thresholds_rejects_vpin_above_doc_cap(
    repo_tmp_path: Path,
) -> None:
    calibration_tmpdir = repo_tmp_path / "engine_c_continuation_thresholds_vpin_cap"
    version_dir = calibration_tmpdir / "v1"
    version_dir.mkdir(parents=True, exist_ok=True)
    _write_signed_yaml(
        version_dir / "engine_c_continuation.yml",
        thresholds=(
            ("THR-C_OFI_MIN", 6.0),
            ("THR-C_QUEUE_MIN", 0.20),
            ("THR-C_VPIN_MAX", 0.55),
        ),
    )

    with pytest.raises(
        CalibrationArtifactValidationError,
        match="Engine C vpin_max hard cap",
    ):
        resolve_engine_c_continuation_thresholds(
            EngineCContinuationThresholdResolverConfig(
                calibration_root=calibration_tmpdir,
                calibration_version="v1",
                ofi_min_threshold_id="THR-C_OFI_MIN",
                queue_min_threshold_id="THR-C_QUEUE_MIN",
                vpin_max_threshold_id="THR-C_VPIN_MAX",
            )
        )


def test_resolve_engine_c_continuation_thresholds_rejects_kyle_lambda_above_sanity_cap(
    repo_tmp_path: Path,
) -> None:
    calibration_tmpdir = repo_tmp_path / "engine_c_continuation_thresholds_kyle_lambda_cap"
    version_dir = calibration_tmpdir / "v1"
    version_dir.mkdir(parents=True, exist_ok=True)
    _write_signed_yaml(
        version_dir / "engine_c_continuation.yml",
        thresholds=(
            ("THR-C_OFI_MIN", 6.0),
            ("THR-C_QUEUE_MIN", 0.20),
            ("THR-C_VPIN_MAX", 0.35),
            ("EC-KYLE-LAMBDA-MAX-01", 5.0),
        ),
    )

    with pytest.raises(
        CalibrationArtifactValidationError,
        match="Engine C kyle_lambda_max hard cap",
    ):
        resolve_engine_c_continuation_thresholds(
            EngineCContinuationThresholdResolverConfig(
                calibration_root=calibration_tmpdir,
                calibration_version="v1",
                ofi_min_threshold_id="THR-C_OFI_MIN",
                queue_min_threshold_id="THR-C_QUEUE_MIN",
                vpin_max_threshold_id="THR-C_VPIN_MAX",
                kyle_lambda_max_threshold_id="EC-KYLE-LAMBDA-MAX-01",
                kyle_lambda_max_hard_cap=1.0,
            )
        )
