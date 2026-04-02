"""Build-16 / engine_d package surface.

This package is intentionally importable even though the actual Engine D
re-entry logic is not implemented yet. The goal is to keep the canonical
inventory and bootstrap surface truthful without pretending that the motor is
production-ready.
"""

ENGINE_D_BUILD_STAGE = 16
ENGINE_D_IMPLEMENTATION_STATUS = "spec_only"
ENGINE_D_NOT_IMPLEMENTED_REASON = (
    "Build-16 Engine D re-entry logic is not implemented yet."
)


class EngineDNotImplementedError(NotImplementedError):
    """Raised when runtime code tries to use the planned Engine D package."""


def raise_engine_d_not_implemented() -> None:
    """Fail explicitly when a caller tries to execute the planned Engine D."""

    raise EngineDNotImplementedError(ENGINE_D_NOT_IMPLEMENTED_REASON)


__all__ = [
    "ENGINE_D_BUILD_STAGE",
    "ENGINE_D_IMPLEMENTATION_STATUS",
    "ENGINE_D_NOT_IMPLEMENTED_REASON",
    "EngineDNotImplementedError",
    "raise_engine_d_not_implemented",
]
