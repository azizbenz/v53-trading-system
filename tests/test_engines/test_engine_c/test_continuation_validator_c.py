from __future__ import annotations

from engines.engine_c import (
    ENGINE_C_OFI_PERSISTENCE_REASON,
    ENGINE_C_QUEUE_PRESSURE_REASON,
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
    )
    defaults.update(overrides)
    return EngineCContinuationValidationInput(**defaults)


def test_validator_accepts_with_confirmed_microstructure() -> None:
    result = validate_continuation_c(_good_input())
    assert result.accepted is True
    assert result.continuation_viable is True
    assert result.microstructure_confirmed is True
    assert result.microstructure_gate_applied is True
    assert result.continuation_score > 0.58


def test_validator_rejects_negative_ofi_persistence() -> None:
    result = validate_continuation_c(_good_input(cumulative_ofi=-1.0))
    assert result.accepted is False
    assert result.microstructure_confirmed is False
    assert ENGINE_C_OFI_PERSISTENCE_REASON in result.reason_codes


def test_validator_rejects_negative_queue_pressure() -> None:
    result = validate_continuation_c(_good_input(queue_pressure=-0.2))
    assert result.accepted is False
    assert ENGINE_C_QUEUE_PRESSURE_REASON in result.reason_codes


def test_validator_rejects_toxic_vpin_when_threshold_is_bound() -> None:
    result = validate_continuation_c(_good_input(vpin=0.51, vpin_max=0.35))
    assert result.accepted is False
    assert ENGINE_C_VPIN_TOXIC_REASON in result.reason_codes


def test_validator_keeps_legacy_path_when_microstructure_is_not_provided() -> None:
    result = validate_continuation_c(
        _good_input(cumulative_ofi=None, queue_pressure=None, vpin=None, vpin_max=None)
    )
    assert result.accepted is True
    assert result.microstructure_gate_applied is False
    assert result.reason_codes == ()


def test_validator_rejects_mature_continuation_even_with_good_microstructure() -> None:
    result = validate_continuation_c(_good_input(extension_pct=0.9))
    assert result.accepted is False
    assert result.continuation_viable is False
    assert any(reason.startswith("engine_internal.c.continuation") for reason in result.reason_codes)
