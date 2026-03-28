"""Dedicated errors for the minimal Build-11 Shadow runtime."""

from __future__ import annotations


class ShadowProtocolError(RuntimeError):
    """Base error for governed Shadow runtime failures."""


class ShadowInputError(ShadowProtocolError):
    """Raised when Shadow input is structurally invalid."""


class ShadowLineageError(ShadowProtocolError):
    """Raised when Shadow lineage or import refs are not coherent."""


class ShadowGateError(ShadowProtocolError):
    """Raised when Shadow gates are bypassed or implicitly promoted."""


__all__ = [
    "ShadowProtocolError",
    "ShadowInputError",
    "ShadowLineageError",
    "ShadowGateError",
]
