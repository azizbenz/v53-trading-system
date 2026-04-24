"""Dedicated errors for the minimal real Build-11/12/13 protocol runtimes."""

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


class LiveLightProtocolError(RuntimeError):
    """Base error for governed Build-13 Live-Light failures."""


class LiveLightInputError(LiveLightProtocolError):
    """Raised when Live-Light input is structurally invalid."""


class LiveLightGateError(LiveLightProtocolError):
    """Raised when Micro-live -> Live-Light gates are bypassed."""


class LiveLightBudgetError(LiveLightProtocolError):
    """Raised when a Live-Light execution request exceeds the governed budget."""


class LiveCompleteProtocolError(RuntimeError):
    """Base error for the governed Build-17 Complete control surface."""


class LiveCompleteInputError(LiveCompleteProtocolError):
    """Raised when Build-17 Complete input is structurally invalid."""


class LiveCompleteGateError(LiveCompleteProtocolError):
    """Raised when Build-17 Complete gates are bypassed."""


class LiveCompleteBudgetError(LiveCompleteProtocolError):
    """Raised when Build-17 Complete carries an incoherent governed envelope."""


LiveProtocolError = LiveCompleteProtocolError
LiveInputError = LiveCompleteInputError
LiveGateError = LiveCompleteGateError
LiveBudgetError = LiveCompleteBudgetError


__all__ = [
    "ShadowProtocolError",
    "ShadowInputError",
    "ShadowLineageError",
    "ShadowGateError",
    "MicroLiveProtocolError",
    "MicroLiveInputError",
    "MicroLiveGateError",
    "MicroLiveBudgetError",
    "LiveProtocolError",
    "LiveInputError",
    "LiveGateError",
    "LiveBudgetError",
    "LiveCompleteProtocolError",
    "LiveCompleteInputError",
    "LiveCompleteGateError",
    "LiveCompleteBudgetError",
    "LiveLightProtocolError",
    "LiveLightInputError",
    "LiveLightGateError",
    "LiveLightBudgetError",
]
