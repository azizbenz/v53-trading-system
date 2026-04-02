"""Build-15 / engine_c package surface.

This package is intentionally importable even though the actual Engine C
breakout-continuation logic is not implemented yet. The goal is to keep the
canonical inventory and bootstrap surface truthful without pretending that the
motor is production-ready.
"""

ENGINE_C_BUILD_STAGE = 15
ENGINE_C_IMPLEMENTATION_STATUS = "spec_only"
ENGINE_C_NOT_IMPLEMENTED_REASON = (
    "Build-15 Engine C breakout-continuation logic is not implemented yet."
)


class EngineCNotImplementedError(NotImplementedError):
    """Raised when runtime code tries to use the planned Engine C package."""


def raise_engine_c_not_implemented() -> None:
    """Fail explicitly when a caller tries to execute the planned Engine C."""

    raise EngineCNotImplementedError(ENGINE_C_NOT_IMPLEMENTED_REASON)


__all__ = [
    "ENGINE_C_BUILD_STAGE",
    "ENGINE_C_IMPLEMENTATION_STATUS",
    "ENGINE_C_NOT_IMPLEMENTED_REASON",
    "EngineCNotImplementedError",
    "raise_engine_c_not_implemented",
]
