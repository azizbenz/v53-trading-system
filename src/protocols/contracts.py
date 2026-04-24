"""Governed contracts for the minimal real Build-11/12/13 runtimes."""

from __future__ import annotations

from . import contracts_promotion as _promotion
from . import contracts_complete as _complete
from . import contracts_shadow as _shadow
from . import contracts_shared as _shared
from .contracts_complete import *
from .contracts_promotion import *
from .contracts_shadow import *
from .contracts_shared import *


__all__ = [
    *_shadow.__all__,
    *_shared.__all__,
    *_promotion.__all__,
    *_complete.__all__,
]
