"""V5.3 - Canonical Engine D facade.

The manifest module name is `engine_d`. The implementation remains spec-only
for now and is hosted under `engines.engine_d`.
"""

from engines.engine_d import (
    ENGINE_D_BUILD_STAGE,
    ENGINE_D_IMPLEMENTATION_STATUS,
    ENGINE_D_NOT_IMPLEMENTED_REASON,
    EngineDNotImplementedError,
    raise_engine_d_not_implemented,
)

__all__ = [
    "ENGINE_D_BUILD_STAGE",
    "ENGINE_D_IMPLEMENTATION_STATUS",
    "ENGINE_D_NOT_IMPLEMENTED_REASON",
    "EngineDNotImplementedError",
    "raise_engine_d_not_implemented",
]
