from __future__ import annotations

import pytest

from interface_contracts import (
    RegimeDetectorLabelConfig,
    RegimeToxicityBucket,
)


def test_regime_detector_label_config_hash_is_stable() -> None:
    config = RegimeDetectorLabelConfig()

    assert len(config.config_hash()) == 64
    assert config.config_hash() == RegimeDetectorLabelConfig().config_hash()


def test_regime_detector_label_config_rejects_invalid_threshold_ordering() -> None:
    with pytest.raises(ValueError, match="toxicity_critical_floor"):
        RegimeDetectorLabelConfig(
            toxicity_elevated_floor=0.70,
            toxicity_critical_floor=0.60,
        )


def test_regime_toxicity_bucket_values_are_stable() -> None:
    assert RegimeToxicityBucket.NOMINAL.value == "nominal"
    assert RegimeToxicityBucket.ELEVATED.value == "elevated"
    assert RegimeToxicityBucket.CRITICAL.value == "critical"
