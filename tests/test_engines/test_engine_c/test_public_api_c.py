from __future__ import annotations

from engines import engine_c
from engines.engine_c import EngineCRuntime, EngineCRuntimeInput, EngineCRuntimeStatus, run_engine_c


def test_public_imports_are_consistent() -> None:
    assert engine_c.ENGINE_C_IMPLEMENTATION_STATUS == "shadow_capable"
    assert callable(run_engine_c)
    assert EngineCRuntimeStatus.ACCEPTED.value == "accepted"


def test_no_export_break_after_patch() -> None:
    assert EngineCRuntime is not None
    assert EngineCRuntimeInput is not None
    assert hasattr(engine_c, "ENGINE_C_KYLE_LAMBDA_REASON")
