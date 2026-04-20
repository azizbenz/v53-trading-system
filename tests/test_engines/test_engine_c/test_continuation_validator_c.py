from __future__ import annotations

from engines.engine_c import (
    ENGINE_C_CONTINUATION_CALLER_THRESHOLDS_TO_CALIBRATE,
    ENGINE_C_KYLE_LAMBDA_REASON,
    ENGINE_C_OFI_MIN_THRESHOLD_ID,
    ENGINE_C_OFI_PERSISTENCE_REASON,
    ENGINE_C_QUEUE_MIN_THRESHOLD_ID,
    ENGINE_C_QUEUE_PRESSURE_REASON,
    ENGINE_C_VPIN_MAX_THRESHOLD_ID,
    ENGINE_C_VPIN_TOXIC_REASON,
    EngineCContinuationValidationInput,
    validate_continuation_c,
)


def _good_input(**overrides: object) -> EngineCContinuationValidationInput:
    defaults = dict(
        followthrough_room=0.76,
        extension_pct=0.24,
        context_score=0.82,
        cumulative_ofi=18.0,
        queue_pressure=0.31,
        vpin=0.24,
        kyle_lambda=0.001,
        ofi_min=0.0,
        queue_min=0.0,
        vpin_max=0.35,
        kyle_lambda_max=0.01,
    )
    defaults.update(overrides)
    return EngineCContinuationValidationInput(**defaults)


def test_continuation_viable_without_microstructure_when_allowed() -> None:
    result = validate_continuation_c(
        _good_input(
            cumulative_ofi=None,
            queue_pressure=None,
            vpin=None,
            vpin_max=None,
            kyle_lambda=None,
            kyle_lambda_max=None,
        )
    )

    assert result.accepted is True
    assert result.microstructure_gate_applied is False
    assert result.microstructure_missing is False


def test_ofi_below_threshold_rejects_with_reason() -> None:
    result = validate_continuation_c(_good_input(cumulative_ofi=-1.0))
    assert result.accepted is False
    assert ENGINE_C_OFI_PERSISTENCE_REASON in result.reason_codes


def test_queue_pressure_below_threshold_rejects_with_reason() -> None:
    result = validate_continuation_c(_good_input(queue_pressure=-0.2))
    assert result.accepted is False
    assert ENGINE_C_QUEUE_PRESSURE_REASON in result.reason_codes


def test_vpin_above_threshold_rejects_with_reason() -> None:
    result = validate_continuation_c(_good_input(vpin=0.51, vpin_max=0.35))
    assert result.accepted is False
    assert ENGINE_C_VPIN_TOXIC_REASON in result.reason_codes


def test_kyle_lambda_policy_is_real() -> None:
    """Fail-first: pre-patch kyle_lambda was copied through but ignored."""
    accepted = validate_continuation_c(_good_input(kyle_lambda=0.001, kyle_lambda_max=0.01))
    blocked = validate_continuation_c(_good_input(kyle_lambda=0.5, kyle_lambda_max=0.01))

    assert accepted.accepted is True
    assert blocked.accepted is False
    assert ENGINE_C_KYLE_LAMBDA_REASON in blocked.reason_codes


def test_continuation_threshold_boundary() -> None:
    below = validate_continuation_c(_good_input(followthrough_room=0.45, extension_pct=0.72, context_score=0.45))
    at_boundary = validate_continuation_c(_good_input(followthrough_room=0.60, extension_pct=0.72, context_score=1.0))
    above = validate_continuation_c(_good_input(followthrough_room=0.80, extension_pct=0.20, context_score=0.80))

    assert below.continuation_viable is False
    assert at_boundary.continuation_viable is True
    assert above.continuation_viable is True


def test_continuation_caller_threshold_ownership_is_explicit() -> None:
    thresholds = ENGINE_C_CONTINUATION_CALLER_THRESHOLDS_TO_CALIBRATE

    assert thresholds.ofi_min_threshold_id == ENGINE_C_OFI_MIN_THRESHOLD_ID
    assert thresholds.queue_min_threshold_id == ENGINE_C_QUEUE_MIN_THRESHOLD_ID
    assert thresholds.vpin_max_threshold_id == ENGINE_C_VPIN_MAX_THRESHOLD_ID
    assert thresholds.kyle_lambda_max_threshold_id is None
    assert EngineCContinuationValidationInput.model_fields["ofi_min"].default == thresholds.ofi_min
    assert EngineCContinuationValidationInput.model_fields["queue_min"].default == thresholds.queue_min
    assert EngineCContinuationValidationInput.model_fields["vpin_max"].default == thresholds.vpin_max
    assert (
        EngineCContinuationValidationInput.model_fields["kyle_lambda_max"].default
        == thresholds.kyle_lambda_max
    )
