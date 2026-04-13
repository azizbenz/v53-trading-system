from pathlib import Path
import shutil
from uuid import uuid4

import pytest
import yaml

from calibration_loader import CalibrationArtifact
from regime_classifier import (
    RegimeLiteCalibrationConfig,
    RegimeLiteInput,
    RegimeLiteMemory,
    RegimeLiteState,
    RegimeLiteThresholds,
    classify_regime_lite,
    resolve_regime_lite_thresholds,
)
from calibration_loader.loader import CalibrationArtifactValidationError


@pytest.fixture
def calibration_tmpdir() -> Path:
    root = Path("build/pytest-regime-lite-calibration") / uuid4().hex
    root.mkdir(parents=True, exist_ok=False)
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


def _payload(*, threshold_id: str, value: int | float) -> dict[str, object]:
    return {
        "artifact_id": f"{threshold_id.lower()}-artifact",
        "version": "v1",
        "produced_by": "local_ia_lab",
        "generated_at": "2026-04-12T09:15:00Z",
        "thresholds": (
            {
                "threshold_id": threshold_id,
                "value": value,
                "source_module": "src/regime_classifier/regime_lite.py",
                "calibration_artifact": "config/calibration/v1/regime_lite.yml",
            },
        ),
        "signature": {
            "signed_by": "operator.aziz",
            "signed_at": "2026-04-12T10:00:00Z",
        },
    }


def _write_signed_yaml(path: Path, *, threshold_id: str, value: int | float) -> None:
    payload = _payload(threshold_id=threshold_id, value=value)
    artifact = CalibrationArtifact.model_validate(payload)
    payload["signature"]["payload_hash_sha256"] = artifact.payload_hash_sha256()
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def test_documented_defaults_validate_threshold_ordering():
    thresholds = RegimeLiteThresholds.from_documented_defaults()

    assert thresholds.btc_realized_vol_24h_extreme >= thresholds.btc_realized_vol_24h_stressed
    assert thresholds.intraday_drawdown_extreme >= thresholds.intraday_drawdown_stressed
    assert thresholds.engine_return_dispersion_extreme >= thresholds.engine_return_dispersion_stressed


def test_resolve_regime_lite_thresholds_loads_calibrated_thr_rg01_to_rg04(
    calibration_tmpdir: Path,
):
    version_dir = calibration_tmpdir / "v1"
    version_dir.mkdir()
    _write_signed_yaml(version_dir / "rg01.yml", threshold_id="THR-RG01", value=0.045)
    _write_signed_yaml(version_dir / "rg02.yml", threshold_id="THR-RG02", value=0.055)
    _write_signed_yaml(version_dir / "rg03.yml", threshold_id="THR-RG03", value=10_800)
    _write_signed_yaml(version_dir / "rg04.yml", threshold_id="THR-RG04", value=172_800)

    thresholds = resolve_regime_lite_thresholds(
        RegimeLiteCalibrationConfig(
            calibration_root=calibration_tmpdir,
            calibration_version="v1",
        )
    )

    assert thresholds.btc_realized_vol_24h_stressed == 0.045
    assert thresholds.btc_drop_1h_extreme == 0.055
    assert thresholds.downgrade_hysteresis_s == 10_800
    assert thresholds.extreme_cooldown_s == 172_800
    assert thresholds.intraday_drawdown_stressed == 0.01
    assert thresholds.engine_return_dispersion_extreme == 0.05


def test_resolve_regime_lite_thresholds_rejects_non_integral_seconds(
    calibration_tmpdir: Path,
):
    version_dir = calibration_tmpdir / "v1"
    version_dir.mkdir()
    _write_signed_yaml(version_dir / "rg01.yml", threshold_id="THR-RG01", value=0.04)
    _write_signed_yaml(version_dir / "rg02.yml", threshold_id="THR-RG02", value=0.05)
    _write_signed_yaml(version_dir / "rg03.yml", threshold_id="THR-RG03", value=7200.5)
    _write_signed_yaml(version_dir / "rg04.yml", threshold_id="THR-RG04", value=86_400)

    with pytest.raises(CalibrationArtifactValidationError):
        resolve_regime_lite_thresholds(
            RegimeLiteCalibrationConfig(
                calibration_root=calibration_tmpdir,
                calibration_version="v1",
            )
        )


def test_resolve_regime_lite_thresholds_rejects_stressed_vol_above_bounded_extreme(
    calibration_tmpdir: Path,
):
    version_dir = calibration_tmpdir / "v1"
    version_dir.mkdir()
    _write_signed_yaml(version_dir / "rg01.yml", threshold_id="THR-RG01", value=0.09)
    _write_signed_yaml(version_dir / "rg02.yml", threshold_id="THR-RG02", value=0.05)
    _write_signed_yaml(version_dir / "rg03.yml", threshold_id="THR-RG03", value=7200)
    _write_signed_yaml(version_dir / "rg04.yml", threshold_id="THR-RG04", value=86_400)

    with pytest.raises(CalibrationArtifactValidationError):
        resolve_regime_lite_thresholds(
            RegimeLiteCalibrationConfig(
                calibration_root=calibration_tmpdir,
                calibration_version="v1",
            )
        )


def test_classify_regime_lite_returns_calm_without_stress_markers():
    assessment = classify_regime_lite(
        RegimeLiteInput(as_of_ts=10_000, btc_realized_vol_24h=0.02),
        RegimeLiteThresholds.from_documented_defaults(),
    )

    assert assessment.state == RegimeLiteState.CALM
    assert assessment.candidate_state == RegimeLiteState.CALM
    assert assessment.reason_codes == ("RG_CALM_BASELINE",)
    assert assessment.entries_blocked is False


def test_classify_regime_lite_marks_stressed_on_vol_signal():
    assessment = classify_regime_lite(
        RegimeLiteInput(as_of_ts=10_000, btc_realized_vol_24h=0.05),
        RegimeLiteThresholds.from_documented_defaults(),
    )

    assert assessment.state == RegimeLiteState.STRESSED
    assert "RG_STRESSED_VOL_24H" in assessment.reason_codes


def test_classify_regime_lite_direct_extreme_on_sudden_drop_sets_cooldown():
    thresholds = RegimeLiteThresholds.from_documented_defaults()

    assessment = classify_regime_lite(
        RegimeLiteInput(as_of_ts=50_000, btc_drop_1h=-0.08),
        thresholds,
        previous=RegimeLiteMemory(state=RegimeLiteState.CALM, state_entered_ts=1_000),
    )

    assert assessment.state == RegimeLiteState.EXTREME
    assert assessment.sudden_event is True
    assert assessment.transition_path == (
        RegimeLiteState.CALM,
        RegimeLiteState.EXTREME,
    )
    assert "RG_DIRECT_EXTREME_EVENT" in assessment.reason_codes
    assert assessment.entries_blocked_until_ts == 50_000 + thresholds.extreme_cooldown_s


def test_classify_regime_lite_prevents_non_sudden_calm_to_extreme_skip():
    assessment = classify_regime_lite(
        RegimeLiteInput(
            as_of_ts=50_000,
            btc_realized_vol_24h=0.09,
            engine_return_dispersion=0.055,
        ),
        RegimeLiteThresholds.from_documented_defaults(),
        previous=RegimeLiteMemory(state=RegimeLiteState.CALM, state_entered_ts=1_000),
    )

    assert assessment.candidate_state == RegimeLiteState.EXTREME
    assert assessment.state == RegimeLiteState.STRESSED
    assert assessment.transition_path == (
        RegimeLiteState.CALM,
        RegimeLiteState.STRESSED,
    )
    assert "RG_NO_STATE_SKIP" in assessment.reason_codes


def test_classify_regime_lite_requires_hysteresis_before_downgrade():
    assessment = classify_regime_lite(
        RegimeLiteInput(as_of_ts=5_000, btc_realized_vol_24h=0.01),
        RegimeLiteThresholds.from_documented_defaults(),
        previous=RegimeLiteMemory(state=RegimeLiteState.STRESSED, state_entered_ts=1_000),
    )

    assert assessment.state == RegimeLiteState.STRESSED
    assert assessment.state_changed is False
    assert "RG_DOWNGRADE_HYSTERESIS_ACTIVE" in assessment.reason_codes


def test_classify_regime_lite_steps_down_one_state_after_hysteresis():
    assessment = classify_regime_lite(
        RegimeLiteInput(as_of_ts=20_000, btc_realized_vol_24h=0.01),
        RegimeLiteThresholds.from_documented_defaults(),
        previous=RegimeLiteMemory(
            state=RegimeLiteState.EXTREME,
            state_entered_ts=1_000,
            entries_blocked_until_ts=90_000,
        ),
    )

    assert assessment.candidate_state == RegimeLiteState.CALM
    assert assessment.state == RegimeLiteState.STRESSED
    assert assessment.entries_blocked is True
    assert assessment.transition_path == (
        RegimeLiteState.EXTREME,
        RegimeLiteState.STRESSED,
    )
    assert "RG_STEP_DOWN_ONE_STATE" in assessment.reason_codes
