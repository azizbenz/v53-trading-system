"""Contracts for the real Build-10 monitoring backend."""

from __future__ import annotations

from . import contracts_core as _core
from . import contracts_dashboard as _dashboard
from . import contracts_vps as _vps
from .contracts_core import *
from .contracts_dashboard import *
from .contracts_vps import *


__all__ = [
    *_core.__all__,
    *_dashboard.__all__,
    *_vps.__all__,
]
