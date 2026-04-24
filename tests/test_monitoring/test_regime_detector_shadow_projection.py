from __future__ import annotations

from complete_enablers import RegimeDetectorSignal, RegimeDetectorSignalStatus
from interface_contracts import RegimeDurationBucket
from monitoring import build_regime_detector_shadow_projection


def test_regime_detector_shadow_projection_exposes_active_signal() -> None:
    signal = RegimeDetectorSignal(
        status=RegimeDetectorSignalStatus.ACTIVE,
        pair="BTCUSDT",
        computed_at_ns=1_700_000_000,
        artifact_hash="a" * 64,
        feature_hash="b" * 64,
        regime_transition_risk=0.82,
        regime_stability_score=0.24,
        market_toxicity_score=0.67,
        expected_duration_bucket=RegimeDurationBucket.SHORT,
        reason_codes=("REGIME_DETECTOR_SHADOW_ACTIVE",),
    )

    projection = build_regime_detector_shadow_projection(
        correlation_id="corr-regime-shadow-1",
        artifact_status="loaded",
        signal_payload=signal.model_dump(mode="python"),
    )

    assert projection.status == "healthy"
    assert projection.shadow_only is True
    assert projection.pair == "BTCUSDT"
    assert projection.regime_transition_risk == 0.82
    assert projection.expected_duration_bucket == "short"


def test_regime_detector_shadow_projection_stays_info_when_neutral() -> None:
    projection = build_regime_detector_shadow_projection(
        correlation_id="corr-regime-shadow-2",
        artifact_status="missing_supplementary_refs",
        signal_payload={
            "status": "neutral",
            "reason_codes": ("REGIME_DETECTOR_ARTIFACT_MISSING",),
        },
    )

    assert projection.status == "info"
    assert projection.signal_status == "neutral"
    assert projection.regime_transition_risk == 0.0
    assert projection.shadow_only is True
