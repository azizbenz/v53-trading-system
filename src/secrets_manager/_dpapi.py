"""Platform dispatch for bounded secret protection backends."""

from __future__ import annotations

import sys

if sys.platform == "win32":
    from secrets_manager._dpapi_windows import (  # noqa: F401
        DpapiError,
        protect_bytes,
        unprotect_bytes,
    )
else:
    from secrets_manager._dpapi_posix import (  # noqa: F401
        DpapiError,
        protect_bytes,
        unprotect_bytes,
    )


__all__ = ["DpapiError", "protect_bytes", "unprotect_bytes"]
