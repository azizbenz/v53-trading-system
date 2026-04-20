from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from calibration_loader import CalibrationArtifact
from calibration_loader.loader import CalibrationArtifactValidationError
from scoring_backbone import (
    EngineBBreakoutThresholdResolverConfig,
    build_engine_b_breakout_threshold_updates,
    resolve_engine_b_breakout_thresholds,
)


def _write_signed_yaml(
    path: Path,
    *,
    thresholds: tuple[tuple[str, int | float], ...],
) -> None:
    payload = {
        "artifact_id": "engine-b-breakout-thresholds",
        "version": "v1",
        "produced_by": "local_ia_lab",
        "generated_at": "2026-04-19T19:10:00Z",
        "thresholds": [
            {
                "threshold_id": threshold_id,
                "value": value,
                "source_module": "src/scoring_backbone/engine_b_breakout_thresholds.py",
                "calibration_artifact": "config/calibration/v1/engine_b_breakout.yml",
            }
            for threshold_id, value in thresholds
        ],
        "signature": {
            "signed_by": "operator.aziz",
            "signed_at": "2026-04-19T19:15:00Z",
        },
    }
    artifact = CalibrationArtifact.model_validate(payload)
    payload["signature"]["payload_hash_sha256"] = artifact.payload_hash_sha256()
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def test_resolve_engine_b_breakout_thresholds_loads_signed_values(
    repo_tmp_path: Path,
) -> None:
    calibration_tmpdir = repo_tmp_path / "engine_b_breakout_thresholds_resolve"
    version_dir = calibration_tmpdir / "v1"
    version_dir.mkdir(parents=True, exist_ok=True)
    _write_signed_yaml(
        version_dir / "engine_b_breakout.yml",
        thresholds=(("THR-B03", 0.35), ("THR-B04", 0.65)),
    )

    resolved = resolve_engine_b_breakout_thresholds(
        EngineBBreakoutThresholdResolverConfig(
            calibration_root=calibration_tmpdir,
            calibration_version="v1",
            warning_threshold_id="THR-B03",
            blocked_threshold_id="THR-B04",
        )
    )

    assert resolved.warning == pytest.approx(0.35)
    assert resolved.blocked == pytest.approx(0.65)
    assert resolved.to_engine_b_breakout_threshold_updates() == {
        "warning": pytest.approx(0.35),
        "blocked": pytest.approx(0.65),
    }


def test_build_engine_b_breakout_threshold_updates_returns_breakout_payload(
    repo_tmp_path: Path,
) -> None:
    calibration_tmpdir = repo_tmp_path / "engine_b_breakout_thresholds_updates"
    version_dir = calibration_tmpdir / "v1"
    version_dir.mkdir(parents=True, exist_ok=True)
    _write_signed_yaml(
        version_dir / "engine_b_breakout.yml",
        thresholds=(("THR-B03", 0.30), ("THR-B04", 0.60)),
    )

    updates = build_engine_b_breakout_threshold_updates(
        EngineBBreakoutThresholdResolverConfig(
            calibration_root=calibration_tmpdir,
            calibration_version="v1",
            warning_threshold_id="THR-B03",
            blocked_threshold_id="THR-B04",
        )
    )

    assert updates == {
        "warning": pytest.approx(0.30),
        "blocked": pytest.approx(0.60),
    }


def test_resolve_engine_b_breakout_thresholds_rejects_invalid_threshold_order(
    repo_tmp_path: Path,
) -> None:
    calibration_tmpdir = repo_tmp_path / "engine_b_breakout_thresholds_order"
    version_dir = calibration_tmpdir / "v1"
    version_dir.mkdir(parents=True, exist_ok=True)
    _write_signed_yaml(
        version_dir / "engine_b_breakout.yml",
        thresholds=(("THR-B03", 0.70), ("THR-B04", 0.65)),
    )

    with pytest.raises(
        CalibrationArtifactValidationError,
        match="warning threshold must be strictly below blocked threshold",
    ):
        resolve_engine_b_breakout_thresholds(
            EngineBBreakoutThresholdResolverConfig(
                calibration_root=calibration_tmpdir,
                calibration_version="v1",
                warning_threshold_id="THR-B03",
                blocked_threshold_id="THR-B04",
            )
        )
