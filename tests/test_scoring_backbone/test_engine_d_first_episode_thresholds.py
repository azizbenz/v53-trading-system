from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from calibration_loader import CalibrationArtifact
from calibration_loader.loader import CalibrationArtifactValidationError
from scoring_backbone import (
    EngineDFirstEpisodeThresholdResolverConfig,
    build_engine_d_first_episode_threshold_updates,
    resolve_engine_d_first_episode_thresholds,
)


_NS_PER_HOUR = 3_600_000_000_000


def _write_signed_yaml(
    path: Path,
    *,
    thresholds: tuple[tuple[str, int | float], ...],
) -> None:
    payload = {
        "artifact_id": "engine-d-first-episode-thresholds",
        "version": "v1",
        "produced_by": "local_ia_lab",
        "generated_at": "2026-04-19T23:20:00Z",
        "thresholds": [
            {
                "threshold_id": threshold_id,
                "value": value,
                "source_module": "src/scoring_backbone/engine_d_first_episode_thresholds.py",
                "calibration_artifact": "config/calibration/v1/engine_d_first_episode.yml",
            }
            for threshold_id, value in thresholds
        ],
        "signature": {
            "signed_by": "operator.aziz",
            "signed_at": "2026-04-19T23:21:00Z",
        },
    }
    artifact = CalibrationArtifact.model_validate(payload)
    payload["signature"]["payload_hash_sha256"] = artifact.payload_hash_sha256()
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def test_resolve_engine_d_first_episode_thresholds_loads_signed_values(
    repo_tmp_path: Path,
) -> None:
    calibration_tmpdir = repo_tmp_path / "engine_d_first_episode_thresholds_resolve"
    version_dir = calibration_tmpdir / "v1"
    version_dir.mkdir(parents=True, exist_ok=True)
    _write_signed_yaml(
        version_dir / "engine_d_first_episode.yml",
        thresholds=(("THR-D_LOOKBACK", 12.0), ("THR-D_MIN_GAP", 15.0)),
    )

    resolved = resolve_engine_d_first_episode_thresholds(
        EngineDFirstEpisodeThresholdResolverConfig(
            calibration_root=calibration_tmpdir,
            calibration_version="v1",
            lookback_threshold_id="THR-D_LOOKBACK",
            min_gap_threshold_id="THR-D_MIN_GAP",
        )
    )

    assert resolved.lookback_hours == pytest.approx(12.0)
    assert resolved.lookback_ns == 12 * _NS_PER_HOUR
    assert resolved.min_gap_minutes == pytest.approx(15.0)
    assert resolved.min_gap_ns == 15 * 60_000_000_000
    assert resolved.to_engine_d_first_episode_updates() == {
        "lookback_ns": 12 * _NS_PER_HOUR,
        "min_gap_ns": 15 * 60_000_000_000,
    }


def test_build_engine_d_first_episode_threshold_updates_returns_runtime_payload(
    repo_tmp_path: Path,
) -> None:
    calibration_tmpdir = repo_tmp_path / "engine_d_first_episode_thresholds_updates"
    version_dir = calibration_tmpdir / "v1"
    version_dir.mkdir(parents=True, exist_ok=True)
    _write_signed_yaml(
        version_dir / "engine_d_first_episode.yml",
        thresholds=(("THR-D_LOOKBACK", 8.0),),
    )

    updates = build_engine_d_first_episode_threshold_updates(
        EngineDFirstEpisodeThresholdResolverConfig(
            calibration_root=calibration_tmpdir,
            calibration_version="v1",
            lookback_threshold_id="THR-D_LOOKBACK",
        )
    )

    assert updates == {"lookback_ns": 8 * _NS_PER_HOUR}


def test_build_engine_d_first_episode_threshold_updates_optionally_adds_min_gap(
    repo_tmp_path: Path,
) -> None:
    calibration_tmpdir = repo_tmp_path / "engine_d_first_episode_thresholds_min_gap_updates"
    version_dir = calibration_tmpdir / "v1"
    version_dir.mkdir(parents=True, exist_ok=True)
    _write_signed_yaml(
        version_dir / "engine_d_first_episode.yml",
        thresholds=(("THR-D_LOOKBACK", 8.0), ("THR-D_MIN_GAP", 20.0)),
    )

    updates = build_engine_d_first_episode_threshold_updates(
        EngineDFirstEpisodeThresholdResolverConfig(
            calibration_root=calibration_tmpdir,
            calibration_version="v1",
            lookback_threshold_id="THR-D_LOOKBACK",
            min_gap_threshold_id="THR-D_MIN_GAP",
        )
    )

    assert updates == {
        "lookback_ns": 8 * _NS_PER_HOUR,
        "min_gap_ns": 20 * 60_000_000_000,
    }


def test_resolve_engine_d_first_episode_thresholds_rejects_values_above_hard_cap(
    repo_tmp_path: Path,
) -> None:
    calibration_tmpdir = repo_tmp_path / "engine_d_first_episode_thresholds_cap"
    version_dir = calibration_tmpdir / "v1"
    version_dir.mkdir(parents=True, exist_ok=True)
    _write_signed_yaml(
        version_dir / "engine_d_first_episode.yml",
        thresholds=(("THR-D_LOOKBACK", 72.0),),
    )

    with pytest.raises(
        CalibrationArtifactValidationError,
        match="Engine D lookback hard cap",
    ):
        resolve_engine_d_first_episode_thresholds(
            EngineDFirstEpisodeThresholdResolverConfig(
                calibration_root=calibration_tmpdir,
                calibration_version="v1",
                lookback_threshold_id="THR-D_LOOKBACK",
            )
        )


def test_resolve_engine_d_first_episode_thresholds_rejects_min_gap_above_hard_cap(
    repo_tmp_path: Path,
) -> None:
    calibration_tmpdir = repo_tmp_path / "engine_d_first_episode_thresholds_min_gap_cap"
    version_dir = calibration_tmpdir / "v1"
    version_dir.mkdir(parents=True, exist_ok=True)
    _write_signed_yaml(
        version_dir / "engine_d_first_episode.yml",
        thresholds=(("THR-D_LOOKBACK", 12.0), ("THR-D_MIN_GAP", 180.0)),
    )

    with pytest.raises(
        CalibrationArtifactValidationError,
        match="Engine D min-gap hard cap",
    ):
        resolve_engine_d_first_episode_thresholds(
            EngineDFirstEpisodeThresholdResolverConfig(
                calibration_root=calibration_tmpdir,
                calibration_version="v1",
                lookback_threshold_id="THR-D_LOOKBACK",
                min_gap_threshold_id="THR-D_MIN_GAP",
            )
        )
