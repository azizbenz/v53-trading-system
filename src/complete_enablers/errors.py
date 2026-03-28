"""Errors for Build-14 enabler guardrails."""

from __future__ import annotations

from interface_contracts import V53BaseError


class Build14GuardrailError(V53BaseError):
    """Raised when a Build-14 enabler violates its guardrails."""

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(
            message=message,
            code="ERR_BUILD14_GUARDRAIL",
            module="complete_enablers",
            details=details,
        )


__all__ = [
    "Build14GuardrailError",
]
