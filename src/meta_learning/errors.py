"""Errors for the governed Build-9X meta-learning layer."""

from __future__ import annotations

from interface_contracts import V53BaseError


class MetaLearningError(V53BaseError):
    """Base error for the meta_learning module."""

    def __init__(
        self,
        message: str,
        code: str = "ERR_META_LEARNING",
        details: dict[str, object] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code=code,
            module="meta_learning",
            details=details,
        )


class LiveMutationForbiddenError(MetaLearningError):
    """Raised when Build-9X attempts to touch the live path."""

    def __init__(self, correlation_id: str) -> None:
        super().__init__(
            message=f"Live mutation forbidden for learning correlation_id={correlation_id}",
            code="ERR_META_LEARNING_LIVE_MUTATION",
            details={"correlation_id": correlation_id},
        )


class ImplicitPromotionForbiddenError(MetaLearningError):
    """Raised when Build-9X attempts implicit promotion."""

    def __init__(self, correlation_id: str) -> None:
        super().__init__(
            message=f"Implicit promotion forbidden for learning correlation_id={correlation_id}",
            code="ERR_META_LEARNING_IMPLICIT_PROMOTION",
            details={"correlation_id": correlation_id},
        )


__all__ = [
    "MetaLearningError",
    "LiveMutationForbiddenError",
    "ImplicitPromotionForbiddenError",
]
