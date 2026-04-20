from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from calibration_loader import CalibrationArtifact
from calibration_loader.loader import CalibrationArtifactValidationError
from scoring_backbone import (
    ENGINE_SHARED_EV_NET_FLOOR_THRESHOLD_ID,
    EvNetFloorThresholdResolverConfig,
    build_ev_net_floor_threshold_updates,
    resolve_ev_net_floor_threshold,
)


def _write_signed_yaml(
    path: Path,
    *,
    thresholds: tuple[tuple[str, int | float], ...],
) -> None:
    payload = {
        "artifact_id": "shared-ev-net-floor-thresholds",
        "version": "v1",
        "produced_by": "local_ia_lab",
        "generated_at": "2026-04-20T08:10:00Z",
        "thresholds": [
            {
                "threshold_id": threshold_id,
                "value": value,
                "source_module": "src/scoring_backbone/ev_net_floor_thresholds.py",
                "calibration_artifact": "config/calibration/v1/ev_net_floor.yml",
            }
            for threshold_id, value in thresholds
        ],
        "signature": {
            "signed_by": "operator.aziz",
            "signed_at": "2026-04-20T08:11:00Z",
        },
    }
    artifact = CalibrationArtifact.model_validate(payload)
    payload["signature"]["payload_hash_sha256"] = artifact.payload_hash_sha256()
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def test_resolve_ev_net_floor_threshold_loads_signed_value(
    repo_tmp_path: Path,
) -> None:
    calibration_tmpdir = repo_tmp_path / "ev_net_floor_thresholds_resolve"
    version_dir = calibration_tmpdir / "v1"
    version_dir.mkdir(parents=True, exist_ok=True)
    _write_signed_yaml(
        version_dir / "ev_net_floor.yml",
        thresholds=((ENGINE_SHARED_EV_NET_FLOOR_THRESHOLD_ID, 0.05),),
    )

    resolved = resolve_ev_net_floor_threshold(
        EvNetFloorThresholdResolverConfig(
            calibration_root=calibration_tmpdir,
            calibration_version="v1",
        )
    )

    assert resolved.ev_net_floor_threshold_id == ENGINE_SHARED_EV_NET_FLOOR_THRESHOLD_ID
    assert resolved.to_break_even_filter_config_updates() == {
        "min_ev_net": pytest.approx(0.05),
    }


def test_build_ev_net_floor_threshold_updates_returns_break_even_payload(
    repo_tmp_path: Path,
) -> None:
    calibration_tmpdir = repo_tmp_path / "ev_net_floor_thresholds_updates"
    version_dir = calibration_tmpdir / "v1"
    version_dir.mkdir(parents=True, exist_ok=True)
    _write_signed_yaml(
        version_dir / "ev_net_floor.yml",
        thresholds=((ENGINE_SHARED_EV_NET_FLOOR_THRESHOLD_ID, 0.08),),
    )

    updates = build_ev_net_floor_threshold_updates(
        EvNetFloorThresholdResolverConfig(
            calibration_root=calibration_tmpdir,
            calibration_version="v1",
        )
    )

    assert updates == {"min_ev_net": pytest.approx(0.08)}


def test_resolve_ev_net_floor_threshold_rejects_negative_value(
    repo_tmp_path: Path,
) -> None:
    calibration_tmpdir = repo_tmp_path / "ev_net_floor_thresholds_negative"
    version_dir = calibration_tmpdir / "v1"
    version_dir.mkdir(parents=True, exist_ok=True)
    _write_signed_yaml(
        version_dir / "ev_net_floor.yml",
        thresholds=((ENGINE_SHARED_EV_NET_FLOOR_THRESHOLD_ID, -0.01),),
    )

    with pytest.raises(
        CalibrationArtifactValidationError,
        match=ENGINE_SHARED_EV_NET_FLOOR_THRESHOLD_ID,
    ):
        resolve_ev_net_floor_threshold(
            EvNetFloorThresholdResolverConfig(
                calibration_root=calibration_tmpdir,
                calibration_version="v1",
            )
        )
