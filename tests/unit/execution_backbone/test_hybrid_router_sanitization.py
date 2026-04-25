from __future__ import annotations

from execution_backbone.order_decider.hybrid_router_sanitization import (
    collect_reason_codes,
    sanitize_unit_interval,
    sanitize_vol_z,
)


def test_unit_interval_clamped_low_emits_action() -> None:
    field = sanitize_unit_interval("market_toxicity_score", -0.1)

    assert field.sanitized_value == 0.0
    assert field.sanitization_action == "clamped_low"


def test_unit_interval_clamped_high_emits_action() -> None:
    field = sanitize_unit_interval("market_toxicity_score", 1.1)

    assert field.sanitized_value == 1.0
    assert field.sanitization_action == "clamped_high"


def test_unit_interval_nan_emits_fallback_missing() -> None:
    field = sanitize_unit_interval("market_toxicity_score", float("nan"))

    assert field.sanitized_value == 0.5
    assert field.sanitization_action == "fallback_missing"


def test_vol_z_clip_high_emits_clamped_high() -> None:
    field = sanitize_vol_z(7.0, clip=5.0)

    assert field.sanitized_value == 5.0
    assert field.sanitization_action == "clamped_high"


def test_vol_z_inf_emits_fallback_missing() -> None:
    field = sanitize_vol_z(float("inf"), clip=5.0)

    assert field.sanitized_value == 0.0
    assert field.sanitization_action == "fallback_missing"


def test_sanitized_field_preserves_raw_value() -> None:
    field = sanitize_unit_interval("market_toxicity_score", 2.0)

    assert field.raw_value == 2.0


def test_reason_codes_format_matches_field_action() -> None:
    reason_codes = collect_reason_codes(
        {
            "market_toxicity_score": sanitize_unit_interval("market_toxicity_score", 2.0),
            "short_window_volatility_z": sanitize_vol_z(float("nan"), clip=5.0),
        }
    )

    assert "regime_input_clamped:market_toxicity_score:clamped_high" in reason_codes
    assert "short_window_volatility_z:fallback_missing" in reason_codes
