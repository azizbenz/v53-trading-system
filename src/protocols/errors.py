"""Dedicated errors for the minimal real Build-11/12 protocol runtimes."""

from __future__ import annotations


class ShadowProtocolError(RuntimeError):
    """Base error for governed Shadow runtime failures."""


class ShadowInputError(ShadowProtocolError):
    """Raised when Shadow input is structurally invalid."""


class ShadowLineageError(ShadowProtocolError):
    """Raised when Shadow lineage or import refs are not coherent."""


class ShadowGateError(ShadowProtocolError):
    """Raised when Shadow gates are bypassed or implicitly promoted."""


class MicroLiveProtocolError(RuntimeError):
    """Base error for governed Build-12 Micro-live failures."""


class MicroLiveInputError(MicroLiveProtocolError):
    """Raised when Micro-live input is structurally invalid."""


class MicroLiveGateError(MicroLiveProtocolError):
    """Raised when Shadow -> Micro-live gates are bypassed."""


class MicroLiveBudgetError(MicroLiveProtocolError):
    """Raised when a micro-live exposure request exceeds the governed budget."""


__all__ = [
    "ShadowProtocolError",
    "ShadowInputError",
    "ShadowLineageError",
    "ShadowGateError",
    "MicroLiveProtocolError",
    "MicroLiveInputError",
    "MicroLiveGateError",
    "MicroLiveBudgetError",
]
