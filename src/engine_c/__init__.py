"""V5.3 - Canonical Engine C facade.

The manifest module name is `engine_c`. The implementation remains spec-only
for now and is hosted under `engines.engine_c`.
"""

from engines.engine_c import (
    ENGINE_C_BUILD_STAGE,
    ENGINE_C_IMPLEMENTATION_STATUS,
    ENGINE_C_NOT_IMPLEMENTED_REASON,
    EngineCNotImplementedError,
    raise_engine_c_not_implemented,
)

__all__ = [
    "ENGINE_C_BUILD_STAGE",
    "ENGINE_C_IMPLEMENTATION_STATUS",
    "ENGINE_C_NOT_IMPLEMENTED_REASON",
    "EngineCNotImplementedError",
    "raise_engine_c_not_implemented",
]
