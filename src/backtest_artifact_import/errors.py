"""Errors for the controlled artifact import scaffold."""

from __future__ import annotations

from interface_contracts import V53BaseError


class ArtifactImportError(V53BaseError):
    """Base error for backtest_artifact_import."""

    def __init__(self, message: str, code: str, details: dict | None = None):
        super().__init__(
            message=message,
            code=code,
            module="backtest_artifact_import",
            details=details,
        )


class ImplicitPromotionForbiddenError(ArtifactImportError):
    """Raised when an import attempts to jump promotion gates."""

    def __init__(self, requested_state: str):
        super().__init__(
            message=f"Implicit promotion forbidden during artifact import: {requested_state}",
            code="ERR_ARTIFACT_IMPORT_IMPLICIT_PROMOTION",
            details={"requested_state": requested_state},
        )


__all__ = [
    "ArtifactImportError",
    "ImplicitPromotionForbiddenError",
]
