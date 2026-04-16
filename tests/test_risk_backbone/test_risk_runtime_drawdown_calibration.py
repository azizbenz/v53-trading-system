"""Tests for the RiskLimits drawdown calibration seam (THR-W01 / THR-W02)."""

from __future__ import annotations

from pathlib import Path

import pytest

from risk_backbone.risk_runtime_drawdown_calibration import (
    RiskDrawdownCalibrationConfig,
    RiskDrawdownThresholds,
    resolve_risk_drawdown_thresholds,
)


def test_from_documented_defaults_returns_correct_values() -> None:
    thresholds = RiskDrawdownThresholds.from_documented_defaults()
    assert thresholds.drawdown_warning_threshold_pct == 0.02
    assert thresholds.drawdown_observe_threshold_pct == 0.04


def test_from_documented_defaults_warning_strictly_less_than_observe() -> None:
    thresholds = RiskDrawdownThresholds.from_documented_defaults()
    assert thresholds.drawdown_warning_threshold_pct < thresholds.drawdown_observe_threshold_pct


def test_calibration_config_defaults() -> None:
    config = RiskDrawdownCalibrationConfig()
    assert config.warning_threshold_id == "THR-W01"
    assert config.observe_threshold_id == "THR-W02"
    assert config.hard_cap_warning_pct == 0.05
    assert config.hard_cap_observe_pct == 0.10


def test_resolve_falls_back_to_defaults_when_artifact_missing(tmp_path: Path) -> None:
    """When calibration artifact is absent, documented defaults are used."""
    config = RiskDrawdownCalibrationConfig(
        calibration_root=str(tmp_path),
        calibration_version="v1",
    )
    thresholds = resolve_risk_drawdown_thresholds(config)
    assert thresholds.drawdown_warning_threshold_pct == 0.02
    assert thresholds.drawdown_observe_threshold_pct == 0.04


def test_thresholds_model_is_frozen() -> None:
    thresholds = RiskDrawdownThresholds.from_documented_defaults()
    with pytest.raises(Exception):
        thresholds.drawdown_warning_threshold_pct = 0.99  # type: ignore[misc]
