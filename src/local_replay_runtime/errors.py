"""Errors for the LOCAL_REPLAY scaffold."""

from __future__ import annotations

from interface_contracts import V53BaseError


class LocalReplayRuntimeError(V53BaseError):
    """Base error for local_replay_runtime."""

    def __init__(
        self,
        message: str,
        code: str,
        details: dict[str, object] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code=code,
            module="local_replay_runtime",
            details=details,
        )


class RuntimeModeViolationError(LocalReplayRuntimeError):
    """Raised when a non-canonical runtime mode is requested."""

    def __init__(self, runtime_mode: str) -> None:
        super().__init__(
            message=f"LOCAL_REPLAY scaffold requires runtime_mode=local_replay, got {runtime_mode}",
            code="ERR_RUNTIME_MODE_VIOLATION",
            details={"runtime_mode": runtime_mode},
        )


class BacktestProfileForbiddenError(LocalReplayRuntimeError):
    """Raised when a forbidden backtest profile is provided."""

    def __init__(self, profile_name: str) -> None:
        super().__init__(
            message=f"BACKTEST_PROFILE is forbidden in V5.3: {profile_name}",
            code="ERR_BACKTEST_PROFILE_FORBIDDEN",
            details={"profile_name": profile_name},
        )


class ProfileForkForbiddenError(LocalReplayRuntimeError):
    """Raised when local/VPS fork semantics are requested."""

    def __init__(self) -> None:
        super().__init__(
            message="Local/VPS profile forks are forbidden in the unified V5.3",
            code="ERR_PROFILE_FORK_FORBIDDEN",
        )


__all__ = [
    "LocalReplayRuntimeError",
    "RuntimeModeViolationError",
    "BacktestProfileForbiddenError",
    "ProfileForkForbiddenError",
]
